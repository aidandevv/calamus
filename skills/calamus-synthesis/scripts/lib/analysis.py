"""Load and validate analysis.json against facts.json (spec 4.4)."""
import json
import os

import base

MODES = ("full", "focus", "since")
FACT_KEYS = ("records", "sequence", "candidates")
REQUIRED = {"phases": ("key", "name", "goal", "first", "last"),
            "epochs": ("key", "name", "phases", "ended_by"),
            "pivots": ("id", "rank", "label", "before", "trigger", "after", "rationale", "origin", "sources")}
STRINGS = {"phases": ("key", "name", "goal", "first", "last"), "epochs": ("key", "name"),
           "pivots": ("id", "label", "before", "trigger", "after", "rationale", "origin")}


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise base.UsageError("cannot read %s: %s" % (os.path.basename(path), e))
    if not isinstance(data, dict):
        raise base.UsageError("%s must hold a JSON object" % os.path.basename(path))
    return data


def _objects(a, key, errs):
    value = a.get(key) or []
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        errs.append("%s: must be a list of objects" % key)
        return []
    return value


def _str_list(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _shape(a, f):
    """Required keys and types, checked before any value is hashed or compared."""
    errs = ["facts.json: missing %s" % k for k in FACT_KEYS if k not in f]
    for kind, keys in REQUIRED.items():
        items = a.get(kind)
        if items is None:
            errs.append("%s: required" % kind)
            continue
        if not isinstance(items, list) or not all(isinstance(v, dict) for v in items):
            errs.append("%s: must be a list of objects" % kind)
            continue
        for n, item in enumerate(items, 1):
            where = "%s[%d]" % (kind, n)
            errs += ["%s: %s is required" % (where, k) for k in keys if k not in item]
            errs += ["%s: %s must be a string" % (where, k) for k in STRINGS[kind]
                     if k in item and not isinstance(item[k], str)]
        for n, item in enumerate(items, 1):
            if kind == "pivots" and "rank" in item and (isinstance(item["rank"], bool)
                                                        or not isinstance(item["rank"], int)):
                errs.append("pivots[%d]: rank must be an integer" % n)
            if kind == "pivots" and "sources" in item and not _str_list(item["sources"]):
                errs.append("pivots[%d]: sources must be a list of ids" % n)
            if kind == "epochs" and "phases" in item and not _str_list(item["phases"]):
                errs.append("epochs[%d]: phases must be a list of phase keys" % n)
            if kind == "epochs" and item.get("ended_by") is not None and not isinstance(item["ended_by"], str):
                errs.append("epochs[%d]: ended_by must be an id or null" % n)
    return errs


def validate(a, f):
    errs = _shape(a, f)
    if errs:
        return errs
    if a.get("version") != 1:
        errs.append("version: must be 1")
    if a.get("mode") not in MODES:
        errs.append("mode: must be one of %s" % ", ".join(MODES))
    ids = {r["id"] for r in f["records"]}
    order = {rid: n for n, rid in enumerate(f["sequence"])}
    cands = {c["id"] for c in f["candidates"]}
    phases = _objects(a, "phases", errs)
    epochs = _objects(a, "epochs", errs)
    pivots = _objects(a, "pivots", errs)
    keys = [p.get("key") for p in phases]
    if len(set(keys)) != len(keys):
        errs.append("phases: keys repeat")
    prev = -1
    for p in phases:
        k = p.get("key")
        if not p.get("name"):
            errs.append("phase %s: name is required" % k)
        first, last = p.get("first"), p.get("last")
        if first not in order or last not in order:
            errs.append("phase %s: first and last must be ids in the sequence" % k)
            continue
        if order[first] > order[last]:
            errs.append("phase %s: first comes after last" % k)
        if order[first] <= prev:
            errs.append("phase %s: overlaps or precedes the previous phase" % k)
        prev = max(prev, order[last])
    pivot_ids = {p.get("id") for p in pivots}
    for e in epochs:
        for k in e.get("phases") or []:
            if k not in keys:
                errs.append("epoch %s: unknown phase %s" % (e.get("key"), k))
        if e.get("ended_by") is not None and e.get("ended_by") not in pivot_ids:
            errs.append("epoch %s: ended_by must be a pivot id or null" % e.get("key"))
    ranks = [p.get("rank") for p in pivots]
    if len(set(ranks)) != len(ranks):
        errs.append("pivots: ranks repeat")
    for p in pivots:
        pid, srcs = p.get("id"), p.get("sources") or []
        if pid not in ids:
            errs.append("pivot %s: unknown id" % pid)
            continue
        for s in srcs:
            if s not in ids:
                errs.append("pivot %s: unknown source %s" % (pid, s))
        if pid not in cands and (p.get("origin") != "analyst-added" or not [s for s in srcs if s in ids]):
            errs.append("pivot %s: not an engine candidate; set origin to analyst-added and cite sources" % pid)
    return errs
