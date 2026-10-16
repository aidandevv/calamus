"""Structural checks for Mermaid source (spec 7.6). Catches the faults that most often break rendering."""
import re
import shutil
import subprocess
import tempfile

import base

DECLS = ("timeline", "mindmap", "flowchart", "graph", "sequenceDiagram", "stateDiagram-v2")
QUOTED = re.compile(r'"[^"]*"')
LABEL_PAIRS = (('["', '"]'), ('("', '")'), ('{"', '"}'), ('|"', '"|'))
ARROW = re.compile(r"\s*(?:<-->|-->|---|-\.->|==>|--o|--x)\s*")
DECL_ID = re.compile(r"(?:^|\s|&)([A-Za-z_]\w*)\s*(?=[\[\(\{>])")
EDGE_LABEL = re.compile(r"\|[^|]*\|")
SKIP = ("accTitle", "accDescr", "classDef", "class ", "style ", "linkStyle", "direction", "click ")
SEQ_DECL = re.compile(r"^(?:participant|actor)\s+(\w+)")
SEQ_MSG = re.compile(r"^(\w+)\s*(?:-->>|->>|-->|->|--x|-x|--\)|-\))\s*(\w+)\s*:")
SEQ_BLOCK = re.compile(r"^(loop|alt|opt|par|critical|break|rect)\b")
SEQ_OK = ("Note ", "note ", "autonumber", "activate ", "deactivate ", "accTitle", "accDescr",
          "else", "and ", "option ", "title ")


def _labels(n, line):
    errs = []
    for opener, closer in LABEL_PAIRS:
        start = 0
        while True:
            i = line.find(opener, start)
            if i < 0:
                break
            j = line.find(closer, i + len(opener))
            if j < 0:
                errs.append((n, "unterminated quoted label"))
                break
            if '"' in line[i + len(opener):j]:
                errs.append((n, "raw quote inside a label; use #34;"))
            start = j + len(closer)
    return errs


def _flow(body, conf, kind):
    errs, depth, declared, referenced = [], 0, set(), []
    for n, line in body:
        s = line.strip()
        outside = QUOTED.sub('""', s)
        if outside.count('"') % 2:
            errs.append((n, "unbalanced quote"))
        for o, c in ("[]", "()", "{}"):
            if outside.count(o) != outside.count(c):
                errs.append((n, "unbalanced %s%s" % (o, c)))
        if s.startswith(SKIP) or kind == "stateDiagram-v2":
            continue
        if s.split()[0] == "subgraph":
            depth += 1
        elif s == "end":
            depth -= 1
            if depth < 0:
                errs.append((n, "end without subgraph"))
                depth = 0
            continue
        declared.update(DECL_ID.findall(" " + outside))
        if ARROW.search(outside):
            for part in ARROW.split(EDGE_LABEL.sub("", outside)):
                m = re.match(r"^([A-Za-z_]\w*)", part.strip())
                if m:
                    referenced.append((n, m.group(1)))
    if depth > 0:
        errs.append((body[-1][0], "subgraph without end"))
    errs += [(n, "edge refers to undeclared node %s" % i) for n, i in referenced if i not in declared]
    if len(declared) > int(base.num(conf, "max_nodes")):
        errs.append((1, "%d nodes exceed max_nodes" % len(declared)))
    return errs


def _sequence(body):
    errs, declared, depth = [], set(), 0
    for n, line in body:
        s = line.strip()
        m = SEQ_DECL.match(s)
        if m:
            declared.add(m.group(1))
        elif SEQ_BLOCK.match(s):
            depth += 1
        elif s == "end":
            depth -= 1
            if depth < 0:
                errs.append((n, "end without block"))
                depth = 0
        elif SEQ_MSG.match(s):
            errs += [(n, "message uses undeclared participant %s" % p)
                     for p in SEQ_MSG.match(s).groups() if p not in declared]
        elif not s.startswith(SEQ_OK):
            errs.append((n, "unrecognized sequence line"))
    if depth > 0:
        errs.append((body[-1][0], "block without end"))
    return errs


def _timeline(body):
    return [(n, "timeline line is neither a section nor 'period : event'") for n, line in body
            if not line.strip().startswith(("title ", "section ", "accTitle", "accDescr"))
            and " : " not in line]


def _mindmap(body, conf):
    errs, parents, counts, roots = [], [], {}, 0
    cap = int(base.num(conf, "max_leaves")) + 1
    for n, line in body:
        lead = line[:len(line) - len(line.lstrip())]
        if "\t" in lead:
            errs.append((n, "use spaces, not tabs, for mindmap indentation"))
        while parents and parents[-1][0] >= len(lead):
            parents.pop()
        if parents:
            counts[parents[-1][1]] = counts.get(parents[-1][1], 0) + 1
        else:
            roots += 1
            if roots > 1:
                errs.append((n, "mindmap has more than one root"))
        parents.append((len(lead), n))
    return errs + [(n, "%d children exceed max_leaves" % c) for n, c in sorted(counts.items()) if c > cap]


def lint(text, conf):
    lines = text.split("\n")
    errs = []
    if not any(l.startswith("%% sources:") and l[len("%% sources:"):].strip() for l in lines):
        errs.append((1, "missing or empty %% sources: comment"))
    body = [(n, l) for n, l in enumerate(lines, 1) if l.strip() and not l.strip().startswith("%%")]
    if not body:
        return errs + [(1, "no diagram")]
    kind = body[0][1].split()[0]
    if kind not in DECLS:
        return errs + [(body[0][0], "unsupported declaration %s" % kind)]
    for n, line in body:
        errs += _labels(n, line)
    rest = body[1:] or [(body[0][0], "")]
    if kind in ("flowchart", "graph", "stateDiagram-v2"):
        errs += _flow([b for b in rest if b[1].strip()], conf, kind)
    elif kind == "sequenceDiagram":
        errs += _sequence([b for b in rest if b[1].strip()])
    elif kind == "timeline":
        errs += _timeline(rest)
    else:
        errs += _mindmap(rest, conf)
    return errs


def mmdc(path):
    """Parse with the Mermaid CLI when installed. Returns error text, or None."""
    exe = shutil.which("mmdc")
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run([exe, "-q", "-i", path, "-o", d + "/out.svg"], capture_output=True, text=True, timeout=120)
    return None if p.returncode == 0 else (p.stderr.strip() or "mmdc failed")
