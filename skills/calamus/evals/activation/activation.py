#!/usr/bin/env python3
"""Activation experiment: classify transcripts, score variants, decide.

  activation.py classify TRANSCRIPT.jsonl         -> {"activated", "reference"}
  activation.py score PROMPTS.jsonl RESULTS.jsonl -> metrics per variant + decision
  activation.py skill SKILL.md DESCRIPTION_FILE   -> SKILL.md text with that description

Offline only. activation.sh makes the model calls and feeds this script.
"""
import json
import os
import re
import sys

RECALL_GAIN = 10.0
PRECISION_GAIN = 5.0


def _tool_uses(events):
    for ev in events:
        if ev.get("type") != "assistant":
            continue
        for block in (ev.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block.get("name"), block.get("input") or {}


def classify(events):
    """Whether the calamus skill activated, and the first reference it read."""
    activated, reference = False, None
    for name, inp in _tool_uses(events):
        if name == "Skill" and str(inp.get("skill", "")).split(":")[-1] == "calamus":
            activated = True
        path = str(inp.get("file_path", ""))
        if name == "Read" and path.endswith("calamus/SKILL.md"):
            activated = True
        if name == "Read" and "calamus/references/" in path and reference is None:
            reference = os.path.basename(path)
    return {"activated": activated, "reference": reference}


def _pct(num, den):
    return round(100.0 * num / den, 1) if den else 0.0


def metrics(prompts, rows):
    """Recall and precision of activation against each prompt's expect label."""
    expect = {p["id"]: p["expect"] == "activate" for p in prompts}
    tp = sum(1 for r in rows if r["activated"] and expect.get(r["id"]))
    fp = sum(1 for r in rows if r["activated"] and not expect.get(r["id"]))
    pos = sum(1 for r in rows if expect.get(r["id"]))
    return {"n": len(rows), "recall": _pct(tp, pos), "precision": _pct(tp, tp + fp)}


def decide(shared, tuned):
    """Adopt the tuned description only if it clears a gain threshold."""
    if tuned["recall"] - shared["recall"] >= RECALL_GAIN:
        return "tuned"
    if tuned["precision"] - shared["precision"] >= PRECISION_GAIN:
        return "tuned"
    return "shared"


def _split(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError("SKILL.md has no frontmatter")
    return m.group(1), text[m.end():]


def shared_description(skill_md):
    with open(skill_md, encoding="utf-8") as f:
        front, _ = _split(f.read())
    m = re.search(r"^description: >-\n((?:  .*\n?)+)", front + "\n", re.M)
    return " ".join(line.strip() for line in m.group(1).splitlines()) if m else ""


def with_description(text, description):
    front, body = _split(text)
    lines = ["  " + w for w in _wrap(description.strip())]
    block = "description: >-\n" + "\n".join(lines) + "\n"
    front = re.sub(r"^description: >-\n(?:  .*\n?)+", block, front + "\n", count=1, flags=re.M)
    return "---\n" + front.rstrip("\n") + "\n---\n" + body


def _wrap(text, width=74):
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    return out + ([line] if line else [])


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        rows = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        return rows


def main(argv):
    if len(argv) == 2 and argv[0] == "classify":
        print(json.dumps(classify(_read_jsonl(argv[1]))))
    elif len(argv) == 3 and argv[0] == "score":
        prompts, rows = _read_jsonl(argv[1]), _read_jsonl(argv[2])
        by = {}
        for r in rows:
            by.setdefault(r["variant"], []).append(r)
        report = {v: metrics(prompts, rs) for v, rs in sorted(by.items())}
        if "shared" in report and "tuned" in report:
            report["decision"] = decide(report["shared"], report["tuned"])
        print(json.dumps(report, indent=2))
    elif len(argv) == 3 and argv[0] == "skill":
        with open(argv[1], encoding="utf-8") as f, open(argv[2], encoding="utf-8") as d:
            sys.stdout.write(with_description(f.read(), d.read()))
    else:
        sys.stderr.write(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
