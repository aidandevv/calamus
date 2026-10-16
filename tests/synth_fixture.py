"""Deterministic synthetic journals with planted phases, one pivot, and known gaps.

Engineering: 24 entries in three phases of 8. Phase 2 starts after a 21-day
gap with a new tag mix; phase 3 starts with a CP-PIVOT entry and a new file
set. Planted phase starts are sequence positions 8 and 16.
"""
import datetime
import os

import helpers  # noqa: F401  (path setup)
import render
import schema

PHASES = [
    ("2026-01-05", 8, ["CP-ARCHITECTURE", "CP-TESTING"], ["core/parse.py", "core/model.py"]),
    ("2026-02-02", 8, ["CP-DEBUG", "CP-TESTING", "CP-REFACTOR"], ["core/parse.py", "cli/main.py"]),
    ("2026-02-11", 8, ["CP-INTEGRATION", "CP-MILESTONE"], ["web/app.ts", "web/routes.ts"]),
]
PLANTED = [8, 16]
PIVOT_POS = 16
STEMS = {"engineering": "dev_journal", "product": "product_insights"}


def engineering():
    out, n = [], 0
    for pi, (start, count, tags, files) in enumerate(PHASES):
        d0 = datetime.date.fromisoformat(start)
        for k in range(count):
            n += 1
            d = d0 + datetime.timedelta(days=k)
            path = files[k % len(files)]
            out.append({
                "record": "entry", "journal": "engineering", "variant": "lightweight",
                "id": "%s-1000-%04x" % (d.strftime("%Y%m%d"), n),
                "tag": "CP-PIVOT" if (pi == 2 and k == 0) else tags[k % len(tags)],
                "date": d.isoformat(), "title": "Phase %d step %d" % (pi + 1, k + 1),
                "summary": "Worked on %s." % path, "files": [path],
                "tradeoff": "Kept the change small.",
                "evidence": {"status": "verified", "text": "Tests pass."},
                "followups": [],
            })
    out[1]["followups"] = ["Measure parse latency"]           # closed by entry 9
    out[9]["summary"] = "Measured parse latency at 4 ms."
    out[5]["followups"] = ["Benchmark the tokenizer cache"]   # never closed
    out[-1]["evidence"] = {"status": "unverified", "text": "Not yet measured."}
    return out


def product(eng):
    rows = [("2026-01-07", "PI-USER-PAIN", "Strong"), ("2026-01-20", "PI-UX-FRICTION", "Weak"),
            ("2026-02-03", "PI-FEATURE-IDEA", "Medium"), ("2026-02-12", "PI-POSITIONING", "Strong"),
            ("2026-02-14", "PI-UX-FRICTION", "Medium"), ("2026-02-16", "PI-TRUST", "Weak")]
    out = []
    for i, (date, tag, strength) in enumerate(rows):
        out.append({
            "record": "entry", "journal": "product", "variant": "lightweight",
            "id": "%s-1100-%04x" % (date.replace("-", ""), 100 + i), "tag": tag, "date": date,
            "title": "Insight %d" % (i + 1), "observation": ["Users reported issue %d." % (i + 1)],
            "why": ["Reason %d." % (i + 1)],
            "evidence": {"source": "Interview notes", "strength": strength},
            "next_step": ["Follow up."],
        })
    pivot = eng[PIVOT_POS]
    out[3]["crosslog"] = {"journal": "engineering", "tag": pivot["tag"], "date": pivot["date"],
                          "title": pivot["title"], "note": "Engineering root cause"}
    return out


def write(root, fmt, eng, prod):
    """Write both journals in one format, the way calamus-convert renders them."""
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    for jname, recs in (("engineering", eng), ("product", prod)):
        if recs is None:
            continue
        body = [render.render(schema.normalize(r), fmt, ext=fmt) for r in recs]
        text = render.header(jname, fmt) + ("\n" + "\n".join(body) if fmt == "md" and body else "".join(body))
        with open(os.path.join(root, "docs", "%s.%s" % (STEMS[jname], fmt)), "w", encoding="utf-8") as f:
            f.write(text)
