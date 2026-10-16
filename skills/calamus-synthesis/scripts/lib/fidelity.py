"""Facts a voice pass must not change (spec 9.7), plus absolute-path and citation checks."""
import collections
import re

from lint import outside_code

ID_RE = re.compile(r"\b\d{8}-\d{4}-[0-9a-z]{4,}\b")
DATE_RE = re.compile(r"(?<![\d-])\d{4}-\d{2}-\d{2}(?![\d-])")
NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s?(%|ms|s|sec|min|h|days?|weeks?|months?|KB|MB|GB|x|"
                    r"lines?|entries|files?|tests?|calls?|commits?)(?![A-Za-z])")
PATH_RE = re.compile(r"`([^`\s]*(?:/[^`\s]*|\.[A-Za-z0-9]{1,5}))`")
ABS_RE = re.compile(r"(?:(?<![\w./:-])(?:/Users/|/home/|/private/|/var/folders/|/tmp/|/root/)|"
                    r"(?<![\w/])~/|\b[A-Za-z]:\\)\S*")
COST_RE = re.compile(r"^\**(Cost|Complexity|Risk)\b")


def tokens(md):
    c = collections.Counter()
    for _, line in outside_code(md):
        for m in ID_RE.findall(line):
            c["id " + m] += 1
        rest = ID_RE.sub(" ", line)
        for m in DATE_RE.findall(rest):
            c["date " + m] += 1
        for value, unit in NUM_RE.findall(rest):
            c["num %s%s" % (value, unit)] += 1
        for p in PATH_RE.findall(line):
            c["path " + p] += 1
    return c


def compare(before, after):
    b, a = tokens(before), tokens(after)
    return ([(1, "voice pass dropped %s" % k) for k in sorted(b - a)] +
            [(1, "voice pass added %s" % k) for k in sorted(a - b)])


def abs_paths(md):
    return [(n, "absolute local path %s" % m.group(0)) for n, line in outside_code(md)
            for m in [ABS_RE.search(line)] if m]


def uncited_findings(md):
    out, in_findings, para = [], False, []

    def flush():
        if para and not COST_RE.match(para[0][1].strip()):
            text = " ".join(l for _, l in para)
            if not ID_RE.search(text) and "(inferred)" not in text:
                out.append((para[0][0], "Findings paragraph has no citation or (inferred) label"))
        del para[:]

    for n, line in outside_code(md) + [(0, "")]:
        s = line.strip()
        if s.startswith("#"):
            flush()
            level = len(s) - len(s.lstrip("#"))
            if level <= 2:
                in_findings = s.lstrip("#").strip().startswith("Findings")
            continue
        if not s or s.startswith(("|", "<!--")):
            flush()
            continue
        if in_findings:
            para.append((n, s))
    return out
