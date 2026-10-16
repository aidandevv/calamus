"""Subcommands for calamus-synth. Each cmd_<name>(argv) returns an exit code."""
import argparse
import os
import re
import sys

import base
import cli  # calamus sibling, on sys.path via base.use_calamus()
import facts

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
