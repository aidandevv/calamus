#!/usr/bin/env python3
"""Text derived from the entry schema: prompt shape blocks and reference docs."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema  # noqa: E402

SHAPES = {"text": "string", "code": "string (may span lines)", "list": "array of strings",
          "enum": "string", "evidence": 'object {"status": "verified" | "unverified", "text": string}'}


def _field_lines(field, indent=""):
    shape = field["shape"]
    if shape == "group":
        lines = ['%s- "%s": object — %s, with:' % (indent, field["key"], field["label"])]
        for sub in field["sub"]:
            lines += _field_lines(sub, indent + "  ")
        return lines
    kind = SHAPES[shape]
    if shape == "enum":
        kind += ", one of " + " | ".join('"%s"' % v for v in field["enum"])
    notes = []
    if field.get("required"):
        notes.append("required")
    elif field.get("empty"):
        notes.append("may be empty")
    else:
        notes.append("optional")
    if field.get("max"):
        notes.append("at most %d items" % field["max"])
    if field.get("layout") == "inline" and field.get("code"):
        notes.append("no backticks")
    elif field.get("layout") == "inline":
        notes.append("no semicolons inside an item")
    hint = field.get("hint", "")
    return ['%s- "%s": %s (%s)%s' % (indent, field["key"], kind, ", ".join(notes), " — " + hint if hint else "")]


def shape_block(journal, variant):
    spec = schema.variant_spec(journal, variant)
    tags = schema.tags_for(journal, variant)
    lines = [
        '- "variant": "%s"' % variant,
        '- "tag": string, one of %s' % " | ".join('"%s"' % t for t in tags),
        '- "date": string, YYYY-MM-DD',
        '- "title": string, short and specific',
    ]
    for field in spec["fields"]:
        lines += _field_lines(field)
    return "\n".join(lines)


# ── Templates ───────────────────────────────────────────────────────────────

def _ph(field):
    if field["shape"] == "enum":
        return " / ".join(field["enum"])
    return "[%s]" % field.get("hint", field["label"]).rstrip(".")


def _md_template_field(field, sub=False):
    shape, label = field["shape"], field["label"]
    lead = "- **%s:**" % label if sub else "**%s:**" % label
    if shape == "group":
        return ["**%s:**" % label] + [l for s in field["sub"] for l in _md_template_field(s, sub=True)]
    if shape == "evidence":
        return ["%s [%s] or `Not yet verified.`" % (lead, field["hint"].rstrip("."))]
    empty = " or `%s`" % field["empty"] if field.get("empty") else ""
    optional = "" if field.get("required") or field.get("empty") else " (optional)"
    if shape == "code":
        return [lead + optional, "```", _ph(field), "```"]
    if shape == "list" and field.get("layout") == "bullets":
        return [lead + optional, "- %s%s" % (_ph(field), empty)]
    if shape == "list":
        sep = schema.inline_sep(field).strip() or ","
        item = "`item`" if field.get("code") else "item"
        return ["%s %s%s %s ...%s%s" % (lead, item, sep, item, empty, optional)]
    return ["%s %s%s%s" % (lead, _ph(field), empty, optional)]


def md_template(journal, variant):
    spec = schema.variant_spec(journal, variant)
    tag = spec["tags"][0] if "tags" in spec else "TAG"
    blocks = ["### [%s] | YYYY-MM-DD: %s[Title]" % (tag, spec.get("title_prefix", ""))]
    for field in spec["fields"]:
        blocks.append("\n".join(_md_template_field(field)))
    other = "product" if journal == "engineering" else "engineering"
    note = schema.load()["journals"][journal]["crosslog_note"]
    blocks.append("> **[CROSS-LOG]** %s logged in `./docs/%s.md`\n> — see [TAG] | YYYY-MM-DD: [title]."
                  % (note, schema.load()["journals"][other]["stem"]))
    blocks.append("---")
    return "\n\n".join(blocks)


def _placeholder(field):
    shape = field["shape"]
    if shape == "group":
        return {s["key"]: _placeholder(s) for s in field["sub"]}
    if shape == "evidence":
        return {"status": "verified|unverified", "text": _ph(field)}
    if shape == "list":
        return [_ph(field)]
    if shape == "enum":
        return "|".join(field["enum"])
    return _ph(field)


def placeholder_record(journal, variant):
    spec = schema.variant_spec(journal, variant)
    rec = {"record": "entry", "journal": journal, "variant": variant, "schema": schema.SCHEMA_VERSION,
           "id": "YYYYMMDD-HHMM-abcd", "tag": spec["tags"][0] if "tags" in spec else "TAG",
           "date": "YYYY-MM-DD", "title": "[Title]"}
    for field in spec["fields"]:
        rec[field["key"]] = _placeholder(field)
    other = "product" if journal == "engineering" else "engineering"
    rec["crosslog"] = {"journal": other, "tag": "TAG", "date": "YYYY-MM-DD", "title": "[title]",
                       "note": schema.load()["journals"][journal]["crosslog_note"]}
    return rec


MARKER_SAMPLES = [
    {"record": "marker", "kind": "session", "when": "YYYY-MM-DD HH:MM", "session": "SESSION", "event": "EVENT"},
    {"record": "marker", "kind": "compact", "when": "YYYY-MM-DD HH:MM", "session": "SESSION"},
    {"record": "marker", "kind": "resume", "when": "YYYY-MM-DD HH:MM", "session": "SESSION", "snapshot": "ID"},
    {"record": "marker", "kind": "pending", "date": "YYYY-MM-DD", "session": "SESSION", "host": "HOST", "event": "EVENT"},
    {"record": "marker", "kind": "resolved", "date": "YYYY-MM-DD", "session": "SESSION", "entry": "ID"},
]


def format_templates(fmt):
    import render
    parts = []
    for jname, spec in schema.load()["journals"].items():
        parts.append(render.header(jname, fmt).rstrip("\n"))
        for variant in spec["variants"]:
            parts.append(render.render(placeholder_record(jname, variant), fmt).rstrip("\n"))
    for m in MARKER_SAMPLES:
        parts.append(render.render(m, fmt).rstrip("\n"))
    return "\n".join(parts)


def fenced(lang, text):
    import render
    fence = render.fence_for(text)
    return "%s%s\n%s\n%s" % (fence, lang, text, fence)


# ── Reference files ─────────────────────────────────────────────────────────

REFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "references")
BLOCK_RE = r"(<!-- BEGIN GENERATED: %s -->\n)(?:.*?\n)?(<!-- END GENERATED: %s -->)"


def blocks():
    return {
        "engineering-journal.md": {
            "eng-lightweight": fenced("markdown", md_template("engineering", "lightweight")),
            "eng-full": fenced("markdown", md_template("engineering", "full")),
            "eng-snapshot": fenced("markdown", md_template("engineering", "snapshot")),
            "eng-fields": fenced("text", "Lightweight:\n" + shape_block("engineering", "lightweight")
                                 + "\n\nFull:\n" + shape_block("engineering", "full")),
        },
        "product-insights.md": {
            "pi-lightweight": fenced("markdown", md_template("product", "lightweight")),
            "pi-full": fenced("markdown", md_template("product", "full")),
            "pi-fields": fenced("text", "Lightweight:\n" + shape_block("product", "lightweight")
                                + "\n\nFull:\n" + shape_block("product", "full")),
        },
        "format-xml.md": {"xml-templates": fenced("xml", format_templates("xml"))},
        "format-jsonl.md": {"jsonl-templates": fenced("json", format_templates("jsonl"))},
    }


def regenerate(text, named):
    import re
    for name, body in named.items():
        rx = re.compile(BLOCK_RE % (re.escape(name), re.escape(name)), re.S)
        if not rx.search(text):
            raise ValueError("missing generated block %r" % name)
        text = rx.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)
    return text


def main(argv):
    if len(argv) == 3 and argv[0] == "shape":
        print(shape_block(argv[1], argv[2]))
        return 0
    if len(argv) == 1 and argv[0] in ("--write", "--check"):
        drift = []
        for fname, named in blocks().items():
            path = os.path.join(REFS, fname)
            with open(path, encoding="utf-8") as f:
                old = f.read()
            new = regenerate(old, named)
            if new != old:
                drift.append(fname)
                if argv[0] == "--write":
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new)
        if drift and argv[0] == "--check":
            sys.stderr.write("generated blocks out of date: %s (run gendocs.py --write)\n" % ", ".join(drift))
            return 1
        for fname in drift:
            print("updated %s" % fname)
        return 0
    sys.stderr.write("usage: gendocs.py shape <journal> <variant> | --write | --check\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
