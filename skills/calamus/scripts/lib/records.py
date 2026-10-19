"""Parse journals in md, xml, or jsonl into record dicts.

Markdown parsing is label-driven. Entries written by Calamus carry an id
comment and round-trip exactly; older hand-written entries are parsed
best-effort, marked legacy, keep their original text in `raw`, and keep any
unrecognized lines in `body`.
"""
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET

import schema

HEADING_RE = re.compile(r"^### \[([A-Z][A-Z0-9-]*)\] \| (\d{4}-\d{2}-\d{2}): (.*)$")
ID_COMMENT_RE = re.compile(r"^<!-- calamus id:(\S+) schema:(\S+) variant:(\S+) -->$")
FENCE_RE = re.compile(r"^(`{3,})")
LABEL_RE = re.compile(r"^\*\*(.+?):\*\*\s?(.*)$")
SUB_RE = re.compile(r"^- \*\*(.+?):\*\*\s?(.*)$")
CROSSLOG_RE = re.compile(
    r"^> \*\*\[CROSS-LOG\]\*\* (.*?) logged in `\./docs/([A-Za-z_]+)\.\w+`\s*\n"
    r"> — see \[([A-Z0-9-]+)\] \| (\S+): (.*)$", re.M)
MARKER_RES = [
    ("session", re.compile(r"^<!-- SESSION: (?P<when>.+?) \| id:(?P<session>\S+) \(hook:(?P<event>[^)]*)\) -->$")),
    ("session", re.compile(r"^<!-- SESSION: (?P<when>.+?) \| (?P<note>.*) -->$")),
    ("session", re.compile(r"^<!-- SESSION: (?P<when>.+?) -->$")),
    ("compact", re.compile(r"^<!-- COMPACT: (?P<when>.+?) \| id:(?P<session>\S+) -->$")),
    ("resume", re.compile(r"^<!-- POST-COMPACT RESUME: (?P<when>.+?) \| id:(?P<session>\S+?)(?: \| snapshot:(?P<snapshot>\S+))? -->$")),
    ("pending", re.compile(r"^<!-- CALAMUS-PENDING: (?P<date>\S+) \| id:(?P<session>\S+) \| host:(?P<host>\S+) \| event:(?P<event>\S+) -->$")),
    ("resolved", re.compile(r"^<!-- CALAMUS-RESOLVED: (?P<date>\S+) \| id:(?P<session>\S+?)(?: \| entry:(?P<entry>\S+))? -->$")),
    ("eval-fail", re.compile(r"^> ⚠ \*\*EVAL-FAIL\*\* \((?P<who>.*?)\) — (?P<reason>.*)$")),
]
BLOCK_START_RE = re.compile(
    r"^(### \[|<!-- (SESSION|COMPACT|POST-COMPACT RESUME|CALAMUS-PENDING|CALAMUS-RESOLVED):|> ⚠ \*\*EVAL-FAIL\*\*)")


def detect_format(path):
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext not in ("md", "xml", "jsonl"):
        raise ValueError("unknown journal format for %s" % path)
    return ext


def parse(path):
    fmt = detect_format(path)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return {"md": parse_md, "xml": parse_xml, "jsonl": parse_jsonl}[fmt](text)


def journal_for_tag(tag):
    return "product" if tag.startswith("PI-") else "engineering"


def journal_for_stem(stem):
    for name, spec in schema.load()["journals"].items():
        if spec["stem"] == stem:
            return name
    return ""


# ── Markdown ────────────────────────────────────────────────────────────────

def _blocks(text):
    """Split md text into blocks at entry headings and marker lines, respecting code fences."""
    blocks, current, fence = [], None, None
    for line in text.split("\n"):
        if fence:
            if current is not None:
                current.append(line)
            if line.strip() == fence:
                fence = None
            continue
        m = FENCE_RE.match(line)
        if m:
            fence = m.group(1)
            if current is not None:
                current.append(line)
            continue
        if BLOCK_START_RE.match(line):
            if current is not None:
                blocks.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        blocks.append(current)
    return blocks


def _unescape_comment(value):
    return value.replace("--&gt;", "-->")


def _parse_marker(line):
    for kind, rx in MARKER_RES:
        m = rx.match(line)
        if not m:
            continue
        rec = {"record": "marker", "kind": kind}
        for k, v in m.groupdict().items():
            if v:
                rec[k] = _unescape_comment(v) if kind != "eval-fail" else v
        if kind == "eval-fail":
            who = rec.pop("who", "")
            if "/" in who:
                rec["backend"], rec["model"] = who.split("/", 1)
        return rec
    return None


def _strip_block(lines):
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and lines[-1].strip() == "---":
        lines.pop()
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _parse_inline_list(field, text):
    if not text or text == field.get("empty"):
        return []
    if field.get("code"):
        items = re.findall(r"`([^`]*)`", text)
        return items if items else [text]
    return [i for i in text.split(schema.inline_sep(field)) if i.strip()]


def _parse_scalar(field, text):
    text = text.strip()
    if field["shape"] == "list":
        return _parse_inline_list(field, text)
    if field["shape"] == "evidence":
        if text.startswith("Not yet verified."):
            return {"status": "unverified", "text": text[len("Not yet verified."):].strip()}
        return {"status": "verified" if text else "unverified", "text": text}
    return "" if text == field.get("empty") else text


def _parse_section(field, first, lines, leftovers):
    shape = field["shape"]
    if shape == "code":
        body = [l for l in lines]
        while body and not body[0].strip():
            body.pop(0)
        if body and FENCE_RE.match(body[0]):
            fence = FENCE_RE.match(body[0]).group(1)
            inner = []
            for l in body[1:]:
                if l.strip() == fence:
                    break
                inner.append(l)
            return "\n".join(inner)
        return "\n".join(body).strip()
    if shape == "group":
        value = {s["key"]: schema.empty_value(s) for s in field["sub"]}
        by_label = {s["label"]: s for s in field["sub"]}
        last = None
        for l in lines:
            m = SUB_RE.match(l)
            if m and m.group(1) in by_label:
                last = by_label[m.group(1)]
                value[last["key"]] = _parse_scalar(last, m.group(2))
            elif l.strip() and last and last["shape"] in ("text", "enum") and l.startswith("  "):
                value[last["key"]] = (value[last["key"]] + " " + l.strip()).strip()
            elif l.strip():
                leftovers.append(l)
        return value
    if shape == "list" and field.get("layout") == "bullets":
        items = []
        for l in lines:
            if l.startswith("- "):
                items.append(l[2:].strip())
            elif l.strip() and items and l.startswith(" "):
                items[-1] += " " + l.strip()
            elif l.strip():
                leftovers.append(l)
        if first.strip():
            items.insert(0, first.strip())
        if field.get("empty") and items == [field["empty"]]:
            return []
        return items
    extra = [l.strip() for l in lines if l.strip()]
    return _parse_scalar(field, " ".join([first] + extra))


def _guess_variant(journal, labels):
    best, best_score = "lightweight", 0
    for variant in schema.load()["journals"][journal]["variants"]:
        spec = schema.variant_spec(journal, variant)
        score = len(labels & {f["label"] for f in spec["fields"]})
        if score > best_score:
            best, best_score = variant, score
    return best


def _parse_entry(lines):
    m = HEADING_RE.match(lines[0])
    tag, date, title = m.group(1), m.group(2), m.group(3).strip()
    jname = journal_for_tag(tag)
    raw = "\n".join(lines) + "\n"
    body = lines[1:]
    rec = {"record": "entry", "journal": jname, "tag": tag, "date": date, "title": title}
    idx = next((i for i, l in enumerate(body) if l.strip()), None)
    idm = ID_COMMENT_RE.match(body[idx]) if idx is not None else None
    if idm:
        rec["id"], rec["variant"] = idm.group(1), idm.group(3)
        body = body[idx + 1:]
    text = "\n".join(body)
    cm = CROSSLOG_RE.search(text)
    if cm:
        rec["crosslog"] = {"note": cm.group(1), "journal": journal_for_stem(cm.group(2)),
                           "tag": cm.group(3), "date": cm.group(4), "title": cm.group(5)}
        text = text[:cm.start()] + text[cm.end():]
        body = text.split("\n")
    labels = {LABEL_RE.match(l).group(1) for l in body if LABEL_RE.match(l)}
    if not idm:
        rec["variant"] = _guess_variant(jname, labels)
        rec["legacy"] = True
        rec["raw"] = raw
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:4]
        rec["id"] = "%s-0000-%s" % (date.replace("-", ""), digest)
    spec = schema.variant_spec(jname, rec["variant"]) or {"fields": []}
    by_label = {f["label"]: f for f in spec["fields"]}
    leftovers, current, first, section = [], None, "", []

    def flush():
        if current is not None:
            rec[current["key"]] = _parse_section(current, first, section, leftovers)

    fence = None
    for l in body:
        if fence:
            section.append(l)
            if l.strip() == fence:
                fence = None
            continue
        fm = FENCE_RE.match(l)
        if fm and current is not None:
            fence = fm.group(1)
            section.append(l)
            continue
        lm = LABEL_RE.match(l)
        if lm and lm.group(1) in by_label:
            flush()
            current, first, section = by_label[lm.group(1)], lm.group(2), []
        elif current is not None:
            section.append(l)
        elif l.strip():
            leftovers.append(l)
    flush()
    if spec.get("title_prefix") and rec["title"].startswith(spec["title_prefix"]):
        rec["title"] = rec["title"][len(spec["title_prefix"]):]
    if rec.get("legacy"):
        rec["body"] = "\n".join(leftovers)
    return rec


def parse_md(text):
    out = []
    for lines in _blocks(text):
        lines = _strip_block(lines)
        if not lines:
            continue
        if lines[0].startswith("### ["):
            if HEADING_RE.match(lines[0]):
                out.append(_parse_entry(lines))
            continue
        marker = _parse_marker(lines[0])
        if marker:
            out.append(marker)
    return out


# ── XML ─────────────────────────────────────────────────────────────────────

def _xml_value(field, el):
    shape = field["shape"]
    if el is None:
        return schema.empty_value(field)
    if shape == "group":
        return {s["key"]: _xml_value(s, el.find(s["key"])) for s in field["sub"]}
    if shape == "evidence":
        return {"status": el.get("status", "unverified"), "text": el.text or ""}
    if shape == "list":
        return [c.text or "" for c in el]
    return el.text or ""


def parse_xml(text):
    if re.search(r"<!DOCTYPE|<!ENTITY", text, flags=re.I):
        raise ValueError("xml journal must not contain DOCTYPE or ENTITY declarations")
    root = ET.fromstring("<journal>" + text + "</journal>")
    out = []
    for el in root:
        if el.tag == "marker":
            out.append(dict({"record": "marker"}, **el.attrib))
            continue
        if el.tag != "entry":
            continue
        rec = {"record": "entry", "journal": el.get("type"), "variant": el.get("variant"),
               "schema": el.get("schema"), "id": el.get("id"), "tag": el.get("tag"),
               "date": el.get("date"), "title": el.findtext("title") or ""}
        spec = schema.variant_spec(rec["journal"], rec["variant"]) or {"fields": []}
        for field in spec["fields"]:
            rec[field["key"]] = _xml_value(field, el.find(field["key"]))
        if el.get("legacy") == "true":
            rec["legacy"] = True
            rec["body"] = el.findtext("body") or ""
        cl = el.find("crosslog")
        if cl is not None:
            rec["crosslog"] = {"journal": cl.get("journal"), "tag": cl.get("tag"), "date": cl.get("date"),
                               "note": cl.get("note"), "title": cl.text or ""}
        out.append(rec)
    return out


# ── JSONL ───────────────────────────────────────────────────────────────────

def parse_jsonl(text):
    out = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("record") in ("entry", "marker"):
            out.append(rec)
    return out
