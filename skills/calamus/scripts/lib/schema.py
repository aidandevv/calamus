"""Entry schema: load, normalize, validate, hash, and id records.

Records are plain dicts:
  entry:  {"record": "entry", "journal", "variant", "schema", "id", "tag",
           "date", "title", <variant fields>, "crosslog"?: {...}}
  marker: {"record": "marker", "kind", <marker fields>}
"""
import hashlib
import json
import os
import re

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "schema", "entry.schema.json"
)
SCHEMA_VERSION = "1"
ID_RE = re.compile(r"^\d{8}-\d{4}-[0-9a-f]{4}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SESSION_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
CROSSLOG_KEYS = ("journal", "tag", "date", "title", "note")

_cache = None


def load():
    global _cache
    if _cache is None:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def variant_spec(journal, variant):
    return load()["variants"].get("%s.%s" % (journal, variant))


def tags_for(journal, variant):
    spec = variant_spec(journal, variant) or {}
    if "tags" in spec:
        return spec["tags"]
    return load()["journals"].get(journal, {}).get("tags", [])


def inline_sep(field):
    return field.get("sep", ", ")


def _text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _code(value):
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def empty_value(field):
    shape = field["shape"]
    if shape == "list":
        return []
    if shape == "group":
        return {s["key"]: empty_value(s) for s in field["sub"]}
    if shape == "evidence":
        return {"status": "unverified", "text": ""}
    return ""


def _norm_field(field, value):
    shape = field["shape"]
    if shape == "list":
        if isinstance(value, str):
            value = [value]
        items = [_text(v) for v in (value or [])]
        return [v for v in items if v]
    if shape == "group":
        value = value if isinstance(value, dict) else {}
        return {s["key"]: _norm_field(s, value.get(s["key"])) for s in field["sub"]}
    if shape == "evidence":
        if isinstance(value, str):
            value = {"status": "verified" if _text(value) else "unverified", "text": value}
        value = value if isinstance(value, dict) else {}
        status = _text(value.get("status")) or ("verified" if _text(value.get("text")) else "unverified")
        return {"status": status.lower(), "text": _text(value.get("text"))}
    if shape == "code":
        return _code(value)
    return _text(value)


def normalize(rec):
    """Return a canonical copy: whitespace collapsed, every field present."""
    rec = dict(rec)
    if rec.get("record") == "marker":
        spec = load()["markers"].get(rec.get("kind"), {"fields": []})
        out = {"record": "marker", "kind": rec.get("kind")}
        for key in spec["fields"]:
            if _text(rec.get(key)):
                out[key] = _text(rec.get(key))
        return out
    out = {
        "record": "entry",
        "journal": _text(rec.get("journal")),
        "variant": _text(rec.get("variant")),
        "schema": SCHEMA_VERSION,
    }
    for key in ("id", "tag", "date", "title"):
        out[key] = _text(rec.get(key))
    out["tag"] = out["tag"].strip("[]")
    spec = variant_spec(out["journal"], out["variant"])
    if spec:
        prefix = spec.get("title_prefix", "")
        if prefix and out["title"].startswith(prefix.strip()):
            out["title"] = out["title"][len(prefix.strip()):].strip()
        for field in spec["fields"]:
            out[field["key"]] = _norm_field(field, rec.get(field["key"]))
    if rec.get("legacy"):
        out["legacy"] = True
        out["body"] = _code(rec.get("body"))
        if rec.get("raw"):
            out["raw"] = rec["raw"]
    cl = rec.get("crosslog")
    if isinstance(cl, dict) and any(_text(cl.get(k)) for k in CROSSLOG_KEYS):
        c = {k: _text(cl.get(k)) for k in CROSSLOG_KEYS}
        c["tag"] = c["tag"].strip("[]")
        c["title"] = c["title"].rstrip(".").strip()
        if not c["note"]:
            c["note"] = load()["journals"].get(out["journal"], {}).get("crosslog_note", "Related entry")
        out["crosslog"] = c
    return out


def _check_field(field, value, path, errs):
    shape = field["shape"]
    name = path + field["key"]
    if shape == "group":
        for s in field["sub"]:
            _check_field(s, value.get(s["key"]), name + ".", errs)
        return
    if shape == "evidence":
        if value["status"] not in ("verified", "unverified"):
            errs.append("%s.status: must be verified or unverified" % name)
        if value["status"] == "verified" and not value["text"]:
            errs.append("%s.text: required when status is verified" % name)
        return
    empty = value == [] or value == ""
    if field.get("required") and empty:
        errs.append("%s: required" % name)
        return
    if shape == "enum" and value and value not in field["enum"]:
        errs.append("%s: %r is not one of %s" % (name, value, ", ".join(field["enum"])))
    if shape == "list":
        if field.get("max") and len(value) > field["max"]:
            errs.append("%s: at most %d items" % (name, field["max"]))
        if field.get("layout") == "inline":
            sep = inline_sep(field)
            for item in value:
                if sep.strip() and sep.strip() in item and not field.get("code"):
                    errs.append("%s: item contains %r; split it into separate items" % (name, sep.strip()))
                if field.get("code") and "`" in item:
                    errs.append("%s: item contains '`'; remove backticks" % name)
                if field.get("empty") and item == field["empty"]:
                    errs.append("%s: leave the list empty instead of writing %r" % (name, item))


def validate(rec):
    """Return a list of human-readable errors; empty means valid."""
    errs = []
    if rec.get("record") == "marker":
        spec = load()["markers"].get(rec.get("kind"))
        if not spec:
            return ["kind: unknown marker kind %r" % rec.get("kind")]
        for key in spec["required"]:
            if not rec.get(key):
                errs.append("%s: required" % key)
        if rec.get("session") and not SESSION_RE.match(rec["session"]):
            errs.append("session: only letters, digits, '.', '_', '-' (max 64)")
        return errs
    if rec.get("record") != "entry":
        return ["record: must be 'entry' or 'marker'"]
    journals = load()["journals"]
    if rec.get("journal") not in journals:
        return ["journal: must be one of %s" % ", ".join(journals)]
    spec = variant_spec(rec["journal"], rec.get("variant"))
    if not spec:
        return ["variant: must be one of %s" % ", ".join(journals[rec["journal"]]["variants"])]
    if rec.get("id") and not ID_RE.match(rec["id"]):
        errs.append("id: must look like YYYYMMDD-HHMM-abcd")
    if not DATE_RE.match(rec.get("date", "")):
        errs.append("date: must be YYYY-MM-DD")
    if not rec.get("title"):
        errs.append("title: required")
    tags = tags_for(rec["journal"], rec["variant"])
    if rec.get("tag") not in tags:
        errs.append("tag: %r is not one of %s" % (rec.get("tag"), ", ".join(tags)))
    for field in spec["fields"]:
        _check_field(field, rec.get(field["key"], empty_value(field)), "", errs)
    cl = rec.get("crosslog")
    if cl:
        if cl["journal"] not in journals or cl["journal"] == rec["journal"]:
            errs.append("crosslog.journal: must name the other journal")
        elif cl["tag"] not in journals[cl["journal"]]["tags"]:
            errs.append("crosslog.tag: %r is not a %s tag" % (cl["tag"], cl["journal"]))
        if not DATE_RE.match(cl["date"]):
            errs.append("crosslog.date: must be YYYY-MM-DD")
        if not cl["title"]:
            errs.append("crosslog.title: required")
    return errs


def content_hash(rec):
    body = {k: v for k, v in rec.items() if k not in ("id", "raw")}
    blob = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def make_id(rec, now):
    return "%s-%s" % (now.strftime("%Y%m%d-%H%M"), content_hash(rec)[:4])
