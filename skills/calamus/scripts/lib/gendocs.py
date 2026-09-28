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


def main(argv):
    if len(argv) == 3 and argv[0] == "shape":
        print(shape_block(argv[1], argv[2]))
        return 0
    sys.stderr.write("usage: gendocs.py shape <journal> <variant>\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
