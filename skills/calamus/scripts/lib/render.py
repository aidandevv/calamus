"""Render normalized records as md, xml, or jsonl text.

Every function returns text ending in a newline. Records must already be
normalized (schema.normalize) and, for entries, carry an id.
"""
import json
import re
from xml.sax.saxutils import escape, quoteattr

import schema

FORMATS = ("md", "xml", "jsonl")
EVAL_FAIL_HINT = "Re-review this session manually or run the Level 2 scorer."


def _comment_safe(value):
    return str(value).replace("-->", "--&gt;")


def journal_file(journal, fmt):
    return "%s.%s" % (schema.load()["journals"][journal]["stem"], fmt)


def header(journal, fmt):
    if fmt == "md":
        return schema.load()["journals"][journal]["md_header"]
    if fmt == "xml":
        return "<!-- calamus journal:%s schema:%s -->\n" % (journal, schema.SCHEMA_VERSION)
    return json.dumps({"record": "header", "journal": journal, "schema": schema.SCHEMA_VERSION}) + "\n"


def render(rec, fmt, ext=None):
    """Render one record. `ext` sets the journal extension used in md cross-log paths."""
    if fmt not in FORMATS:
        raise ValueError("unknown format %r" % fmt)
    if rec["record"] == "marker":
        return {"md": _md_marker, "xml": _xml_marker, "jsonl": _jsonl}[fmt](rec)
    return {"md": lambda r: _md_entry(r, ext or "md"), "xml": _xml_entry, "jsonl": _jsonl}[fmt](rec)


# ── Markdown ────────────────────────────────────────────────────────────────

def fence_for(code):
    runs = [len(m) for m in re.findall(r"`+", code)]
    return "`" * max(3, max(runs, default=0) + 1)


def _md_inline_list(field, items):
    if field.get("code"):
        items = ["`%s`" % i for i in items]
    return schema.inline_sep(field).join(items)


def _md_field(field, value, sub=False):
    """Return md lines for one field, or [] to omit it."""
    shape, label = field["shape"], field["label"]
    lead = "- **%s:**" % label if sub else "**%s:**" % label
    if shape == "group":
        lines = []
        for s in field["sub"]:
            lines += _md_field(s, value.get(s["key"], schema.empty_value(s)), sub=True)
        return ["**%s:**" % label] + lines if lines else []
    if shape == "evidence":
        if value["status"] == "verified":
            text = value["text"]
        else:
            text = ("Not yet verified. " + value["text"]).strip()
        return ["%s %s" % (lead, text)]
    if shape == "code":
        if not value:
            return []
        fence = fence_for(value)
        return [lead, fence, value, fence]
    if shape == "list" and field.get("layout") == "bullets":
        items = value or ([field["empty"]] if field.get("empty") else [])
        return [lead] + ["- %s" % i for i in items] if items else []
    if shape == "list":
        text = _md_inline_list(field, value) if value else field.get("empty", "")
    else:
        text = value or field.get("empty", "")
    return ["%s %s" % (lead, text)] if text else []


def _md_crosslog(rec, ext):
    cl = rec["crosslog"]
    return (
        "> **[CROSS-LOG]** %s logged in `./docs/%s`\n> — see [%s] | %s: %s."
        % (cl["note"], journal_file(cl["journal"], ext), cl["tag"], cl["date"], cl["title"])
    )


def _md_entry(rec, ext):
    spec = schema.variant_spec(rec["journal"], rec["variant"])
    prefix = (spec or {}).get("title_prefix", "")
    blocks = [
        "### [%s] | %s: %s%s" % (rec["tag"], rec["date"], prefix, rec["title"]),
        "<!-- calamus id:%s schema:%s variant:%s -->" % (rec["id"], rec["schema"], rec["variant"]),
    ]
    if rec.get("legacy"):
        if rec.get("raw"):
            return rec["raw"].rstrip("\n") + "\n"
        blocks.append(rec.get("body", ""))
    for field in (spec or {}).get("fields", []):
        lines = _md_field(field, rec.get(field["key"], schema.empty_value(field)))
        if lines:
            blocks.append("\n".join(lines))
    if rec.get("crosslog"):
        blocks.append(_md_crosslog(rec, ext))
    blocks.append("---")
    return "\n\n".join(b for b in blocks if b) + "\n"


def _md_marker(rec):
    k = rec["kind"]
    g = lambda key: _comment_safe(rec.get(key, ""))
    if k == "eval-fail":
        who = "%s/%s" % (g("backend"), g("model")) if rec.get("backend") else "gate"
        return "> ⚠ **EVAL-FAIL** (%s) — %s\n> %s\n" % (who, rec["reason"], EVAL_FAIL_HINT)
    if k == "session":
        if rec.get("session"):
            tail = "id:%s (hook:%s)" % (g("session"), g("event"))
        else:
            tail = g("note")
        return "<!-- SESSION: %s | %s -->\n" % (g("when"), tail) if tail else "<!-- SESSION: %s -->\n" % g("when")
    if k == "compact":
        return "<!-- COMPACT: %s | id:%s -->\n" % (g("when"), g("session"))
    if k == "resume":
        snap = " | snapshot:%s" % g("snapshot") if rec.get("snapshot") else ""
        return "<!-- POST-COMPACT RESUME: %s | id:%s%s -->\n" % (g("when"), g("session"), snap)
    if k == "pending":
        return "<!-- CALAMUS-PENDING: %s | id:%s | host:%s | event:%s -->\n" % (
            g("date"), g("session"), g("host"), g("event"))
    if k == "resolved":
        entry = " | entry:%s" % g("entry") if rec.get("entry") else ""
        return "<!-- CALAMUS-RESOLVED: %s | id:%s%s -->\n" % (g("date"), g("session"), entry)
    raise ValueError("unknown marker kind %r" % k)


# ── XML ─────────────────────────────────────────────────────────────────────

def _cdata(text):
    return "<![CDATA[%s]]>" % text.replace("]]>", "]]]]><![CDATA[>")


def _xml_field(field, value, indent):
    tag, pad = field["key"], "  " * indent
    shape = field["shape"]
    if shape == "group":
        inner = [_xml_field(s, value.get(s["key"], schema.empty_value(s)), indent + 1) for s in field["sub"]]
        return "%s<%s>\n%s\n%s</%s>" % (pad, tag, "\n".join(inner), pad, tag)
    if shape == "evidence":
        return "%s<%s status=%s>%s</%s>" % (pad, tag, quoteattr(value["status"]), escape(value["text"]), tag)
    if shape == "list":
        if not value:
            return "%s<%s/>" % (pad, tag)
        item = field.get("item", "item")
        return "%s<%s>%s</%s>" % (pad, tag, "".join("<%s>%s</%s>" % (item, escape(i), item) for i in value), tag)
    if shape == "code":
        return "%s<%s>%s</%s>" % (pad, tag, _cdata(value), tag) if value else "%s<%s/>" % (pad, tag)
    return "%s<%s>%s</%s>" % (pad, tag, escape(value), tag) if value else "%s<%s/>" % (pad, tag)


def _xml_entry(rec):
    spec = schema.variant_spec(rec["journal"], rec["variant"]) or {"fields": []}
    attrs = " ".join(
        "%s=%s" % (a, quoteattr(rec[k]))
        for a, k in (("type", "journal"), ("variant", "variant"), ("schema", "schema"),
                     ("id", "id"), ("tag", "tag"), ("date", "date"))
    )
    if rec.get("legacy"):
        attrs += ' legacy="true"'
    lines = ["<entry %s>" % attrs, "  <title>%s</title>" % escape(rec["title"])]
    for field in spec["fields"]:
        lines.append(_xml_field(field, rec.get(field["key"], schema.empty_value(field)), 1))
    if rec.get("legacy"):
        lines.append("  <body>%s</body>" % _cdata(rec.get("body", "")))
    cl = rec.get("crosslog")
    if cl:
        lines.append("  <crosslog journal=%s tag=%s date=%s note=%s>%s</crosslog>" % (
            quoteattr(cl["journal"]), quoteattr(cl["tag"]), quoteattr(cl["date"]),
            quoteattr(cl["note"]), escape(cl["title"])))
    lines.append("</entry>")
    return "\n".join(lines) + "\n"


def _xml_marker(rec):
    attrs = "".join(" %s=%s" % (k, quoteattr(v)) for k, v in rec.items() if k != "record")
    return "<marker%s/>\n" % attrs


# ── JSONL ───────────────────────────────────────────────────────────────────

def _jsonl(rec):
    body = {k: v for k, v in rec.items() if k != "raw"}
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n"
