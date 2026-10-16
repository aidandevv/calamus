"""Copy .mmd files into marked fenced blocks in writeups (spec 7.4)."""
import os
import re

MARK_RE = re.compile(r"^<!-- diagram: ([A-Za-z0-9._-]+\.mmd) -->$")


def embed(md, dirpath):
    lines, out, errs, i = md.split("\n"), [], [], 0
    while i < len(lines):
        out.append(lines[i])
        m = MARK_RE.match(lines[i])
        i += 1
        if not m:
            continue
        src = os.path.join(dirpath, m.group(1))
        if not os.path.isfile(src):
            errs.append((len(out), "diagram %s does not exist" % m.group(1)))
            continue
        if i < len(lines) and lines[i] == "```mermaid":
            j = i + 1
            while j < len(lines) and lines[j] != "```":
                j += 1
            if j == len(lines):
                errs.append((len(out), "unterminated mermaid block after the marker"))
                continue
            i = j + 1
        with open(src, encoding="utf-8") as f:
            body = f.read().rstrip("\n")
        out += ["```mermaid"] + body.split("\n") + ["```"]
    return "\n".join(out), errs


def check(md, dirpath):
    new, errs = embed(md, dirpath)
    if not errs and new != md:
        old_lines, new_lines = md.split("\n"), new.split("\n")
        n = next((k for k, (x, y) in enumerate(zip(old_lines, new_lines)) if x != y), len(old_lines))
        errs.append((n + 1, "embedded diagram differs from its .mmd; run calamus-synth embed"))
    return errs
