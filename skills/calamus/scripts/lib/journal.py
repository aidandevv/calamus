"""Resolve journal paths and append records. This is the only journal writer."""
import datetime
import fcntl
import os

import records
import render
import schema

FORMAT_ALIASES = {"md": "md", "human": "md", "xml": "xml", "model": "xml", "jsonl": "jsonl"}


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


class DuplicateError(Exception):
    pass


def canonical_format(value):
    return FORMAT_ALIASES.get((value or "").strip().lower())


def _existing(root, journal):
    stem = schema.load()["journals"][journal]["stem"]
    return [f for f in render.FORMATS if os.path.exists(os.path.join(root, "docs", "%s.%s" % (stem, f)))]


def resolve(root, journal, fmt_env):
    """Return (path, format, warning). An existing journal's extension wins."""
    stem = schema.load()["journals"][journal]["stem"]
    wanted = canonical_format(fmt_env)
    found = _existing(root, journal)
    warning = ""
    if not found:
        other = [j for j in schema.load()["journals"] if j != journal]
        found = [f for j in other for f in _existing(root, j)]
    if len(set(found)) == 1:
        fmt = found[0]
    elif found:
        if wanted in found:
            fmt = wanted
        else:
            fmt = "md" if "md" in found else found[0]
            warning = "several journal formats exist (%s); using %s" % (", ".join(sorted(set(found))), fmt)
    else:
        fmt = wanted or "md"
    return os.path.join(root, "docs", "%s.%s" % (stem, fmt)), fmt, warning


def prepare(journal, recs, now=None):
    """Normalize, assign ids, and validate. Raises ValidationError; writes nothing."""
    now = now or datetime.datetime.now()
    out, errors = [], []
    for i, rec in enumerate(recs):
        if not isinstance(rec, dict):
            errors.append("entry %d: must be an object" % (i + 1))
            continue
        rec = dict(rec)
        rec.setdefault("record", "entry")
        if rec["record"] == "entry":
            rec.setdefault("journal", journal)
        norm = schema.normalize(rec)
        if norm["record"] == "entry" and not norm["id"]:
            norm["id"] = schema.make_id(norm, now)
        errs = schema.validate(norm)
        if norm["record"] == "entry" and norm["journal"] != journal:
            errs.append("journal: entry belongs to %r, not %r" % (norm["journal"], journal))
        errors += ["entry %d: %s" % (i + 1, e) for e in errs]
        out.append(norm)
    if errors:
        raise ValidationError(errors)
    return out


def _md_prefix(tail):
    if not tail:
        return ""
    if tail.endswith(b"\n\n"):
        return ""
    return "\n" if tail.endswith(b"\n") else "\n\n"


def append_records(root, journal, recs, fmt_env=None, now=None):
    """Validate every record, refuse duplicates, then append in one write. Returns entry ids."""
    prepared = prepare(journal, recs, now)
    path, fmt, _ = resolve(root, journal, fmt_env)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.seek(0)
            existing_text = f.read()
            existing = records.parse_md(existing_text) if fmt == "md" else (
                records.parse_xml(existing_text) if fmt == "xml" else records.parse_jsonl(existing_text))
            ids = {r.get("id") for r in existing if r.get("record") == "entry"}
            hashes = {schema.content_hash(schema.normalize(r)) for r in existing
                      if r.get("record") == "entry" and not r.get("legacy")}
            for rec in prepared:
                if rec["record"] != "entry":
                    continue
                h = schema.content_hash(rec)
                if rec["id"] in ids or h in hashes:
                    raise DuplicateError("entry already in journal: %s | %s" % (rec["tag"], rec["title"]))
                ids.add(rec["id"])
                hashes.add(h)
            chunks = []
            if not existing_text:
                chunks.append(render.header(journal, fmt))
            tail = (chunks[0] if chunks else existing_text)[-2:].encode("utf-8")
            body = [render.render(r, fmt, ext=fmt) for r in prepared]
            if fmt == "md":
                chunks.append(_md_prefix(tail) + "\n".join(body))
            else:
                if tail and not tail.endswith(b"\n"):
                    chunks.append("\n")
                chunks.append("".join(body))
            f.seek(0, os.SEEK_END)
            f.write("".join(chunks))
            f.flush()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return [r["id"] for r in prepared if r["record"] == "entry"]
