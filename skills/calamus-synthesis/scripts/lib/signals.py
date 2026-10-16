"""Deterministic observations over the record sequence. Signals propose; they never decide."""
import collections
import datetime
import math
import re
import statistics

import base

HELD_RE = re.compile(r"^\s*(the\s+)?(plan\s+held|no\s+change|unchanged|none)\b", re.I)
WORD_RE = re.compile(r"[a-z0-9]{4,}")


def _jsd(a, b):
    """Jensen-Shannon divergence, base 2, between two tag lists (0 to 1)."""
    if not a or not b:
        return 0.0
    ca, cb = collections.Counter(a), collections.Counter(b)
    na, nb = float(len(a)), float(len(b))
    out = 0.0
    for k in set(ca) | set(cb):
        p, q = ca[k] / na, cb[k] / nb
        m = (p + q) / 2
        if p:
            out += 0.5 * p * math.log(p / m, 2)
        if q:
            out += 0.5 * q * math.log(q / m, 2)
    return out


def _jaccard_distance(a, b):
    a, b = set(a), set(b)
    return 0.0 if not (a | b) else 1.0 - len(a & b) / float(len(a | b))


def _windows(seq, key, w, fn):
    vals = {}
    for i in range(w, len(seq) - w + 1):
        left = [x for r in seq[i - w:i] for x in key(r)]
        right = [x for r in seq[i:i + w] for x in key(r)]
        vals[i] = fn(left, right)
    return vals


def _peaks(vals, threshold):
    """Local maxima at or above threshold; on a plateau, the first position."""
    return [i for i in sorted(vals)
            if vals[i] >= threshold and vals[i] > vals.get(i - 1, -1.0) and vals[i] >= vals.get(i + 1, -1.0)]


def _sig(kind, pos, seq, value=None):
    s = {"kind": kind, "pos": pos, "id": seq[pos]["id"]}
    if value is not None:
        s["value"] = value
    return s


def boundary_signals(seq, conf):
    out = []
    dates = [datetime.date.fromisoformat(r["date"]) for r in seq]
    gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
    if gaps:
        med = statistics.median(gaps)
        for i in range(1, len(seq)):
            g = gaps[i - 1]
            if g > base.num(conf, "gap_factor") * med and g >= base.num(conf, "gap_min_days"):
                out.append(_sig("gap", i, seq, g))
    w = int(base.num(conf, "window"))
    for kind, key, fn, thr in (("tag_shift", lambda r: [r["tag"]], _jsd, "jsd_min"),
                               ("file_turnover", lambda r: r["files"], _jaccard_distance, "jaccard_min")):
        vals = _windows(seq, key, w, fn)
        out += [_sig(kind, i, seq, round(vals[i], 3)) for i in _peaks(vals, base.num(conf, thr))]
    for i, r in enumerate(seq):
        changed = r["variant"] == "full" and r["pivot_text"] and not HELD_RE.search(r["pivot_text"])
        if r["tag"] == "CP-PIVOT" or changed:
            out.append(_sig("explicit_pivot", i, seq))
        elif r["tag"] == "CP-ARCHITECTURE":
            out.append(_sig("architecture", i, seq))
    return sorted(out, key=lambda s: (s["pos"], s["kind"]))


def record_signals(slims, texts, conf):
    out = [{"kind": "crosslog_pair", "id": s["id"], "target": s["crosslog"]} for s in slims if s["crosslog"]]
    need = base.num(conf, "followup_overlap")
    for i, s in enumerate(slims):
        later = slims[i + 1:]
        for fu in s["followups"]:
            words = set(WORD_RE.findall(fu.lower()))
            if words and not any(sum(1 for w in words if w in texts[l["id"]]) / float(len(words)) >= need
                                 for l in later):
                out.append({"kind": "open_followup", "id": s["id"], "text": fu})
        if s["journal"] == "engineering" and s["evidence"] == "unverified":
            if not any(l["journal"] == "engineering" and l["evidence"] == "verified"
                       and set(l["files"]) & set(s["files"]) for l in later):
                out.append({"kind": "unverified_evidence", "id": s["id"]})
        if s["journal"] == "product" and s["evidence"] == "Weak":
            if not any(l["journal"] == "product" and l["tag"] == s["tag"]
                       and l["evidence"] in ("Medium", "Strong") for l in later):
                out.append({"kind": "unverified_evidence", "id": s["id"]})
    return out
