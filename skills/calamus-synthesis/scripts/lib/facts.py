"""Build facts.json from the journals. Read-only: journals are opened for reading only."""
import collections
import json
import os

import base

base.use_calamus()
import journal  # noqa: E402
import records  # noqa: E402
import schema  # noqa: E402

import boundaries  # noqa: E402
import excerpt  # noqa: E402
import signals  # noqa: E402

VERSION = 1
SUPERSESSION = "supersession signal omitted: the entry schema has no supersede or revert field"


def load(root):
    """Return (info, entries, markers, warnings); entries sorted by (date, id)."""
    info, entries, markers, warnings = {}, [], [], []
    for jname in ("engineering", "product"):
        path, fmt, warning = journal.resolve(root, jname, os.environ.get("CALAMUS_FORMAT"))
        if warning:
            warnings.append(warning)
        if not os.path.exists(path):
            continue
        info[jname] = {"path": os.path.relpath(path, root), "format": fmt}
        try:
            recs = records.parse(path)
        except (ValueError, OSError) as e:
            raise base.UsageError("cannot read %s: %s" % (os.path.relpath(path, root), e))
        for rec in recs:
            norm = schema.normalize(rec)
            if norm["record"] == "marker":
                markers.append(norm)
                continue
            errs = [] if norm.get("legacy") else schema.validate(norm)
            if errs:
                warnings.append("skipped %s: %s" % (norm.get("id") or "an entry", "; ".join(errs)))
                continue
            entries.append(norm)
    if not info:
        raise base.UsageError("no journals under docs/; run calamus-init first")
    entries.sort(key=lambda r: (r["date"], r["id"]))
    return info, entries, markers, warnings


def entry(root, rec_id):
    for rec in load(root)[1]:
        if rec["id"] == rec_id:
            return rec
    raise base.UsageError("no entry with id %s" % rec_id)


def _files(rec):
    return list(rec.get("files") or []) + list((rec.get("impl") or {}).get("files") or [])


def _summary(rec):
    text = rec.get("summary") or (rec.get("design") or {}).get("choice") or " ".join(rec.get("observation") or [])
    text = text or rec.get("body", "")
    return text if len(text) <= 240 else text[:239].rsplit(" ", 1)[0] + "…"


def _evidence(rec):
    ev = rec.get("evidence")
    if rec["journal"] == "product":
        return (ev or {}).get("strength", "") if isinstance(ev, dict) else ""
    if rec["variant"] == "full":
        return "verified" if rec.get("verification") else "unverified"
    return ev.get("status", "") if isinstance(ev, dict) else ""


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def full_text(rec):
    skip = ("record", "journal", "variant", "schema", "id", "raw")
    return " ".join(s for k, v in rec.items() if k not in skip for s in _strings(v)).lower()


def slim(rec):
    timeless = rec.get("legacy") or rec["id"][9:13] == "0000"
    when = base.entry_time(rec["id"], rec["date"], rec.get("legacy"))
    return {
        "id": rec["id"], "journal": rec["journal"], "variant": rec["variant"], "date": rec["date"],
        "time": "" if timeless else when.strftime("%H:%M"), "tag": rec["tag"], "title": rec["title"],
        "files": _files(rec), "summary": _summary(rec), "evidence": _evidence(rec),
        "followups": list(rec.get("followups") or []), "pivot_text": "; ".join(rec.get("pivot") or []),
        "has_code": bool(rec.get("code")), "legacy": bool(rec.get("legacy")), "crosslog": None,
    }


def _key(jname, tag, date, title):
    return (jname, tag, date, title.rstrip(".").strip().lower())


def build(root, conf, since=None):
    info, entries, markers, warnings = load(root)
    if since:
        entries = [r for r in entries if r["date"] >= since]
    decisions = [r for r in entries if r["variant"] != "snapshot"]
    slims = [slim(r) for r in decisions]
    by_key = {_key(s["journal"], s["tag"], s["date"], s["title"]): s["id"] for s in slims}
    for s, rec in zip(slims, decisions):
        cl = rec.get("crosslog")
        if cl:
            target = by_key.get(_key(cl["journal"], cl["tag"], cl["date"], cl["title"]))
            if target:
                s["crosslog"] = target
            else:
                warnings.append("unmatched cross-log on %s" % s["id"])
    if excerpt.is_repo(root):
        grace = base.num(conf, "excerpt_grace_hours")
        for s in slims:
            when = base.entry_time(s["id"], s["date"], s["legacy"])
            refs = []
            for p in s["files"]:
                try:
                    p = excerpt.safe_path(root, p)
                except excerpt.Refused:
                    continue
                found = excerpt.resolve_commit(root, p, when, grace)
                refs.append(dict(path=p, **found) if found else {"path": p, "missing": True})
            s["code_refs"] = refs
    sessions = [{"when": m["when"], "kind": m["kind"], "note": m.get("note", "")}
                for m in markers if m["kind"] in ("session", "resume", "compact") and m.get("when")]
    sessions += [{"when": r["date"], "kind": "snapshot", "note": r["id"]}
                 for r in entries if r["variant"] == "snapshot"]
    sessions.sort(key=lambda s: (s["when"], s["kind"], s["note"]))
    eng = [s for s in slims if s["journal"] == "engineering"]
    min_entries = int(base.num(conf, "min_entries"))
    seq = eng if len(eng) >= min_entries else slims
    seq_recs = seq
    texts = {r["id"]: full_text(r) for r in decisions}
    sigs = signals.record_signals(slims, texts, conf)
    cands = []
    if len(seq_recs) >= min_entries:
        sigs = signals.boundary_signals(seq_recs, conf) + sigs
        cands = boundaries.candidates(sigs, seq_recs, conf)
    else:
        warnings.append("fewer than %d entries; timeline and gap report only" % min_entries)
    tags = collections.Counter(s["tag"] for s in slims)
    warnings.append(SUPERSESSION)
    return {
        "version": VERSION,
        "journals": info,
        "records": slims,
        "sequence": [s["id"] for s in seq],
        "sessions": sessions,
        "signals": sigs,
        "candidates": cands,
        "stats": {
            "entries": {j: sum(1 for s in slims if s["journal"] == j) for j in info},
            "first": slims[0]["date"] if slims else "",
            "last": slims[-1]["date"] if slims else "",
            "tags": dict(sorted(tags.items())),
        },
        "warnings": warnings,
    }


def dump(f):
    return json.dumps(f, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
