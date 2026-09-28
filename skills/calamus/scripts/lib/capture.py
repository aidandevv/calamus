#!/usr/bin/env python3
"""Hook-side capture steps that need the schema.

  capture.py build <sweep|snapshot> [--date D]           < text  → prompt
  capture.py commit <sweep|snapshot> --root R --reply F --session S --host H
             --event E --state DIR                             → exit 0 written,
             3 no checkpoint, 4 invalid reply (saved to DIR/rejected/), 5 write error
  capture.py marker --root R --kind K [key=value ...]          → append one marker
  capture.py judge-prompt --state DIR                          → Level 1 prompt
"""
import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gendocs  # noqa: E402
import journal  # noqa: E402
import render  # noqa: E402
import schema  # noqa: E402

PROMPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prompts")
VARIANT = {"sweep": "lightweight", "snapshot": "snapshot"}
EXIT_NONE, EXIT_INVALID, EXIT_WRITE = 3, 4, 5


class Invalid(Exception):
    pass


def prompt_text(name):
    with open(os.path.join(PROMPTS, name + ".txt"), encoding="utf-8") as f:
        return f.read()


def build(kind, date, text):
    tpl = prompt_text(kind)
    tpl = tpl.replace("{{SHAPE}}", gendocs.shape_block("engineering", VARIANT[kind]))
    return tpl.replace("{{DATE}}", date) + text.rstrip("\n") + "\n"


def parse_reply(kind, reply):
    """Return a list of entry dicts; [] for no checkpoint. Raises Invalid."""
    text = reply.strip()
    if not text or text == "NO_CHECKPOINT":
        if not text:
            raise Invalid("empty reply")
        return []
    fenced = re.match(r"^```[a-zA-Z]*\s*\n(.*)\n```$", text, re.S)
    if fenced:
        text = fenced.group(1).strip()
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            raise Invalid("reply is not JSON")
        text = text[start:end + 1]
    try:
        data = json.loads(text)
    except ValueError as e:
        raise Invalid("reply is not valid JSON: %s" % e)
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise Invalid('reply must be {"entries": [...]}')
    entries = []
    for e in data["entries"]:
        if not isinstance(e, dict):
            raise Invalid("each entry must be an object")
        e = {k: v for k, v in e.items() if k not in ("id", "record", "journal") + journal.PARSER_ONLY}
        e["variant"] = VARIANT[kind]
        if kind == "snapshot":
            e["tag"] = "CP-COMPACT-SNAPSHOT"
        entries.append(e)
    if kind == "snapshot":
        entries = entries[:1]
    return entries


def _save_rejected(state, session, reply, errors, now):
    d = os.path.join(state, "rejected")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "%s-%s.json" % (session, now.strftime("%Y%m%d%H%M%S")))
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"reply": reply, "errors": errors}, f, ensure_ascii=False, indent=1)


def commit(args):
    now = datetime.datetime.now()
    with open(args.reply, encoding="utf-8", errors="replace") as f:
        reply = f.read()
    try:
        entries = parse_reply(args.kind, reply)
    except Invalid as e:
        _save_rejected(args.state, args.session, reply, [str(e)], now)
        sys.stderr.write("invalid reply: %s\n" % e)
        return EXIT_INVALID
    if not entries:
        return EXIT_NONE
    when = now.strftime("%Y-%m-%d %H:%M")
    if args.kind == "sweep":
        marker = {"record": "marker", "kind": "session", "when": when, "session": args.session, "event": args.event}
    else:
        marker = {"record": "marker", "kind": "compact", "when": when, "session": args.session}
    fmt_env = os.environ.get("CALAMUS_FORMAT")
    try:
        prepared = journal.prepare("engineering", entries, now)
        journal.append_records(args.root, "engineering", [marker] + prepared, fmt_env=fmt_env, now=now)
    except journal.ValidationError as e:
        _save_rejected(args.state, args.session, reply, e.errors, now)
        sys.stderr.write("invalid reply:\n  %s\n" % "\n  ".join(e.errors))
        return EXIT_INVALID
    except journal.DuplicateError:
        return EXIT_NONE
    except (OSError, ValueError) as e:
        sys.stderr.write("write failed: %s\n" % e)
        return EXIT_WRITE
    os.makedirs(args.state, exist_ok=True)
    with open(os.path.join(args.state, "last-written.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(render.render(r, "md") for r in prepared))
    if args.kind == "snapshot":
        with open(os.path.join(args.state, "last-snapshot"), "w", encoding="utf-8") as f:
            f.write(prepared[0]["id"] + "\n")
    for r in prepared:
        print(r["id"])
    return 0


def marker(args):
    rec = {"record": "marker", "kind": args.kind}
    for pair in args.fields:
        key, _, value = pair.partition("=")
        rec[key] = value
    try:
        journal.append_records(args.root, "engineering", [rec], fmt_env=os.environ.get("CALAMUS_FORMAT"))
    except (journal.ValidationError, OSError, ValueError) as e:
        sys.stderr.write("marker not written: %s\n" % e)
        return 1
    return 0


def judge_prompt(args):
    with open(os.path.join(args.state, "last-written.md"), encoding="utf-8") as f:
        entries = f.read()
    sys.stdout.write(prompt_text("eval-gate") + entries)
    return 0


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("kind", choices=VARIANT)
    b.add_argument("--date", default=datetime.date.today().isoformat())
    c = sub.add_parser("commit")
    c.add_argument("kind", choices=VARIANT)
    for opt in ("--root", "--reply", "--session", "--host", "--event", "--state"):
        c.add_argument(opt, required=True)
    m = sub.add_parser("marker")
    m.add_argument("--root", required=True)
    m.add_argument("--kind", required=True)
    m.add_argument("fields", nargs="*")
    j = sub.add_parser("judge-prompt")
    j.add_argument("--state", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "build":
        sys.stdout.write(build(args.kind, args.date, sys.stdin.read()))
        return 0
    return {"commit": commit, "marker": marker, "judge-prompt": judge_prompt}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
