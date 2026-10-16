"""Shared fixtures for Python tests."""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(REPO, "skills", "calamus", "scripts", "lib")
FIXTURES = os.path.join(REPO, "tests", "fixtures")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

ENG_LIGHT = {
    "record": "entry", "journal": "engineering", "variant": "lightweight",
    "schema": "1", "id": "20260927-1630-a1b2", "tag": "CP-DEBUG",
    "date": "2026-09-27", "title": "Offset Not Advanced on Timeout",
    "summary": "The sweep offset stayed put after a backend timeout, so the next event retried the same text.",
    "files": ["scripts/hook.sh", "scripts/lib/gate.sh"],
    "tradeoff": "Retrying costs one more call but never loses text.",
    "evidence": {"status": "verified", "text": "Covered by the hanging-backend test."},
    "followups": ["Measure retry frequency", "Tune the timeout"],
    "crosslog": {"journal": "product", "tag": "PI-TRUST", "date": "2026-09-27",
                 "title": "Lost Captures Erode Trust", "note": "Product impact"},
}

HOSTILE = 'a <b> & "c" ]]> d --> e ünï 🙂'


def sample_records():
    """One valid record of every entry variant and marker kind."""
    eng_full = {
        "record": "entry", "journal": "engineering", "variant": "full",
        "id": "20260927-1631-0001", "tag": "CP-ARCHITECTURE", "date": "2026-09-27",
        "title": "Schema " + HOSTILE,
        "context": ["Need one source of truth", HOSTILE],
        "design": {"choice": "JSON schema", "alternatives": "YAML", "why": "stdlib only"},
        "pivot": ["Plan held."],
        "impl": {"files": ["a.py", "b/c.sh"], "pattern": "schema-driven renderers"},
        "verification": [],
        "references": ["[Spec](https://agentskills.io/specification) - name rules"],
        "code": "def f(x):\n    return x < 1 and ']]>' != '```'\n```inner```\n",
        "crosslog_notes": [],
        "followups": ["Measure", "Tune"],
    }
    snap = {
        "record": "entry", "journal": "engineering", "variant": "snapshot",
        "id": "20260927-1632-0002", "tag": "CP-COMPACT-SNAPSHOT", "date": "2026-09-27",
        "title": "hook engine", "summary": "Writing hook.sh.", "files": ["scripts/hook.sh"],
        "decisions": ["Use mkdir locks"], "next_step": "Finish Level 1 gate.",
        "open_questions": [],
    }
    prod_light = {
        "record": "entry", "journal": "product", "variant": "lightweight",
        "id": "20260927-1633-0003", "tag": "PI-TRUST", "date": "2026-09-27",
        "title": "Lost Captures Erode Trust", "observation": ["Users " + HOSTILE],
        "why": ["Trust"], "evidence": {"source": "Founder observation", "strength": "Medium"},
        "next_step": ["Measure pending markers"],
    }
    prod_full = {
        "record": "entry", "journal": "product", "variant": "full",
        "id": "20260927-1634-0004", "tag": "PI-ONBOARDING", "date": "2026-09-27",
        "title": "Install Needs One Command", "observation": ["Three installs confused"],
        "context": {"segment": "", "stage": "Onboarding", "goal": "Install once"},
        "jtbd": {"functional": "Get journaling working", "emotional": ""},
        "evidence": {"source": "Walkthrough", "strength": "Weak", "notes": "One run", "counter": ""},
        "impact": ["Activation"], "risk": {"primary": "Usability", "why": "Setup friction"},
        "hypothesis": ["If one installer, then fewer failures"], "next_step": ["Ship installer"],
        "priority": {"reach": "Medium", "impact": "High", "confidence": "Low", "effort": "Low"},
        "content_angle": [], "crosslog_notes": ["See CP-ARCHITECTURE entry"],
        "open_questions": [],
    }
    markers = [
        {"record": "marker", "kind": "session", "when": "2026-09-27 16:30", "session": "abc-123", "event": "session-end"},
        {"record": "marker", "kind": "session", "when": "2026-09-27 16:30", "note": "calamus design"},
        {"record": "marker", "kind": "compact", "when": "2026-09-27 16:31", "session": "abc-123"},
        {"record": "marker", "kind": "resume", "when": "2026-09-27 16:32", "session": "abc-123", "snapshot": "20260927-1632-0002"},
        {"record": "marker", "kind": "pending", "date": "2026-09-27", "session": "abc-123", "host": "codex", "event": "session-end"},
        {"record": "marker", "kind": "resolved", "date": "2026-09-27", "session": "abc-123", "entry": "20260927-1630-a1b2"},
        {"record": "marker", "kind": "eval-fail", "backend": "claude", "model": "m-1", "reason": "Answers 2 of 8 --> weak."},
    ]
    return [dict(ENG_LIGHT), eng_full, snap], [prod_light, prod_full], markers


SYNTH = os.path.join(REPO, "skills", "calamus-synthesis")
SYNTH_LIB = os.path.join(SYNTH, "scripts", "lib")
if SYNTH_LIB not in sys.path:
    sys.path.insert(0, SYNTH_LIB)
