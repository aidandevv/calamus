"""Subcommands for calamus-synth. Each cmd_<name>(argv) returns an exit code."""
import argparse
import os
import re
import shutil
import sys

import base
import cli  # calamus sibling, on sys.path via base.use_calamus()
import schema  # calamus sibling
import analysis
import embed
import excerpt
import facts
import fidelity
import lint
import mermaid
import mmdlint
import render_html
import voice

DATE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


def cmd_extract(argv):
    ap = argparse.ArgumentParser(prog="calamus-synth extract")
    ap.add_argument("--root")
    ap.add_argument("--since")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.since and not DATE_RE.match(a.since):
        raise base.UsageError("--since must be YYYY-MM-DD")
    root = cli.project_root(a.root)
    text = facts.dump(facts.build(root, base.default_conf("synth.conf"), a.since))
    if not a.out:
        sys.stdout.write(text)
        return 0
    os.makedirs(a.out, exist_ok=True)
    # A new run starts a new draft; an old snapshot would fail fidelity on it.
    shutil.rmtree(snapshot_dir(root, a.out), ignore_errors=True)
    with open(os.path.join(a.out, "facts.json"), "w", encoding="utf-8") as f:
        f.write(text)
    print(os.path.join(a.out, "facts.json"))
    return 0


def cmd_excerpt(argv):
    ap = argparse.ArgumentParser(prog="calamus-synth excerpt")
    ap.add_argument("--id", required=True)
    ap.add_argument("--journaled", action="store_true")
    ap.add_argument("--path")
    ap.add_argument("--symbol")
    ap.add_argument("--lines")
    ap.add_argument("--at")
    ap.add_argument("--diff", action="store_true")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--max-lines", type=int)
    ap.add_argument("--root")
    a = ap.parse_args(argv)
    if a.journaled == bool(a.path):
        raise base.UsageError("give exactly one of --journaled or --path")
    if a.path and not a.diff and bool(a.symbol) == bool(a.lines):
        raise base.UsageError("give exactly one of --symbol or --lines")
    if a.frm and not a.diff:
        raise base.UsageError("--from needs --diff")
    span = None
    if a.lines:
        m = re.match(r"^(\d+)-(\d+)$", a.lines)
        if not m:
            raise base.UsageError("--lines must look like 12-30")
        span = (int(m.group(1)), int(m.group(2)))
    root = cli.project_root(a.root)
    rec = facts.entry(root, a.id)
    try:
        sys.stdout.write(excerpt.excerpt(
            root, rec, base.default_conf("synth.conf"), base.default_conf("style.conf"), path=a.path,
            symbol=a.symbol, lines=span, journaled=a.journaled, at=a.at, diff=a.diff, frm=a.frm,
            max_lines=a.max_lines))
    except excerpt.Refused as e:
        sys.stderr.write("calamus-synth: excerpt refused: %s\n" % e)
        return 4
    return 0


def cmd_diagrams(argv):
    ap = argparse.ArgumentParser(prog="calamus-synth diagrams")
    ap.add_argument("dir")
    a = ap.parse_args(argv)
    f = analysis.load(os.path.join(a.dir, "facts.json"))
    an = analysis.load(os.path.join(a.dir, "analysis.json"))
    errs = analysis.validate(an, f)
    for e in errs:
        sys.stderr.write("calamus-synth: analysis.json: %s\n" % e)
    if errs:
        return 2
    for name, text in sorted(mermaid.generate(f, an, base.default_conf("synth.conf")).items()):
        with open(os.path.join(a.dir, name), "w", encoding="utf-8") as fh:
            fh.write(text)
        print(name)
    return 0


def _md_files(d):
    if not os.path.isdir(d):
        raise base.UsageError("%s is not a directory" % d)
    return [os.path.join(d, n) for n in sorted(os.listdir(d)) if n.endswith(".md")]


def cmd_embed(argv):
    ap = argparse.ArgumentParser(prog="calamus-synth embed")
    ap.add_argument("dir")
    a = ap.parse_args(argv)
    status = 0
    stems = {j["stem"] for j in schema.load()["journals"].values()}
    for path in _md_files(a.dir):
        if os.path.splitext(os.path.basename(path))[0] in stems:
            sys.stderr.write("%s: refusing to modify a journal\n" % os.path.basename(path))
            status = 2
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        new, errs = embed.embed(text, a.dir)
        for n, msg in errs:
            sys.stderr.write("%s:%d: %s\n" % (os.path.basename(path), n, msg))
            status = 2
        if new != text:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            print(os.path.basename(path))
    return status


def snapshot_dir(root, d):
    return os.path.join(root, ".calamus", "state", "synth", os.path.basename(os.path.normpath(d)))


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def cmd_snapshot(argv):
    ap = argparse.ArgumentParser(prog="calamus-synth snapshot")
    ap.add_argument("dir")
    ap.add_argument("--root")
    a = ap.parse_args(argv)
    root = cli.project_root(a.root)
    dest = snapshot_dir(root, a.dir)
    os.makedirs(dest, exist_ok=True)
    for path in _md_files(a.dir):
        shutil.copyfile(path, os.path.join(dest, os.path.basename(path)))
    print(os.path.relpath(dest, root))
    return 0


def cmd_check(argv):
    ap = argparse.ArgumentParser(prog="calamus-synth check")
    ap.add_argument("dir")
    ap.add_argument("--root")
    ap.add_argument("--voice")
    ap.add_argument("--mmdc", action="store_true")
    a = ap.parse_args(argv)
    root = cli.project_root(a.root)
    conf = base.default_conf("synth.conf")
    style = voice.merged_style(base.default_conf("style.conf"), voice.locate(root, a.voice))
    snap = snapshot_dir(root, a.dir)
    fails, warns, records = [], [], {}

    def lookup(rid):
        if not records:
            records.update({r["id"]: r for r in facts.load(root)[1]})
        if rid not in records:
            raise base.UsageError("no entry with id %s" % rid)
        return records[rid]

    for path in _md_files(a.dir):
        name, text = os.path.basename(path), _read(path)
        fails += [(name, n, "abs-path", m) for n, m in fidelity.abs_paths(text)]
        fails += [(name, n, "diagram", m) for n, m in embed.check(text, a.dir)]
        fails += [(name, n, "excerpt", m) for n, m in excerpt.verify(text, root, conf, style, lookup)]
        found = excerpt.markers(text)
        if len(found) > base.num(conf, "max_excerpts"):
            warns.append((name, found[0][0], "excerpt-count", "%d excerpts in one file" % len(found)))
        warns += [(name, n, "working-tree", "excerpt quotes the working tree, not a commit")
                  for n, m in found if "@working-tree:" in m.group("spec")]
        if os.path.isfile(os.path.join(snap, name)):
            fails += [(name, n, "fidelity", m) for n, m in fidelity.compare(_read(os.path.join(snap, name)), text)]
        warns += [(name, n, "uncited", m) for n, m in fidelity.uncited_findings(text)]
        warns += [(name, f["line"], f["rule"], f["text"]) for f in lint.lint(text, name, style)]
    mmds = sorted(n for n in os.listdir(a.dir) if n.endswith(".mmd"))
    extras = [n for n in mmds if n.startswith("extra-")]
    if len(extras) > base.num(conf, "max_extra_diagrams"):
        warns.append((extras[0], 1, "extra-diagrams", "%d mechanism diagrams" % len(extras)))
    if a.mmdc and not shutil.which("mmdc"):
        warns.append(("-", 0, "mmdc", "Mermaid CLI not found; structural lint only"))
    for name in mmds:
        path = os.path.join(a.dir, name)
        fails += [(name, n, "mermaid", m) for n, m in mmdlint.lint(_read(path), conf)]
        if a.mmdc and shutil.which("mmdc"):
            err = mmdlint.mmdc(path)
            if err:
                fails.append((name, 1, "mmdc", err.splitlines()[0]))
    for kind, rows in (("FAIL", fails), ("WARN", warns)):
        for name, n, rule, msg in rows:
            print("%s %s:%d %s: %s" % (kind, name, n, rule, msg))
    print("check: %d failures, %d warnings" % (len(fails), len(warns)))
    return 3 if fails else 0


def cmd_render(argv):
    ap = argparse.ArgumentParser(prog="calamus-synth render")
    ap.add_argument("dir")
    ap.add_argument("--html", action="store_true")
    a = ap.parse_args(argv)
    if not a.html:
        raise base.UsageError("render writes HTML only when asked; pass --html")
    if not os.path.isdir(a.dir):
        raise base.UsageError("%s is not a directory" % a.dir)
    print(os.path.basename(render_html.render(a.dir, base.items(base.default_conf("synth.conf"), "mermaid_cdn")[-1])))
    return 0
