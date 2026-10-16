"""Score boundary signals into phase and pivot candidates."""
import base

WEIGHTS = {"gap": "weight_gap", "tag_shift": "weight_tag_shift", "file_turnover": "weight_file_turnover",
           "explicit_pivot": "weight_explicit_pivot", "architecture": "weight_architecture"}


def candidates(signals, seq, conf):
    tol = int(base.num(conf, "tolerance"))
    need = base.num(conf, "phase_threshold")
    bsig = [s for s in signals if s["kind"] in WEIGHTS]
    scored = []
    for pos in sorted({s["pos"] for s in bsig}):
        near = [s for s in bsig if abs(s["pos"] - pos) <= tol]
        score = round(sum(base.num(conf, WEIGHTS[s["kind"]]) for s in near), 3)
        explicit = any(s["kind"] == "explicit_pivot" and s["pos"] == pos for s in bsig)
        if score >= need or explicit:
            scored.append({"pos": pos, "id": seq[pos]["id"], "score": score, "explicit_pivot": explicit,
                           "signals": sorted({s["kind"] for s in near})})
    kept = []
    for c in sorted(scored, key=lambda c: (-c["score"], not c["explicit_pivot"], c["pos"])):
        if all(abs(c["pos"] - k["pos"]) > tol for k in kept):
            kept.append(c)
    return sorted(kept, key=lambda c: c["pos"])
