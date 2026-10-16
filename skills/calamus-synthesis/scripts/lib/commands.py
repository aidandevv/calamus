"""Subcommands for calamus-synth. Each cmd_<name>(argv) returns an exit code."""
import argparse
import os
import re
import sys

import base
import cli  # calamus sibling, on sys.path via base.use_calamus()
import analysis
import excerpt
import facts
import mermaid

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
