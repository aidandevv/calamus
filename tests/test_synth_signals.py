import tempfile
import unittest

import helpers  # noqa: F401
import synth_fixture as fx

import base
import boundaries
import facts
import signals

CONF = base.default_conf("synth.conf")


def build(eng=None, prod=None):
    root = tempfile.mkdtemp()
    eng = fx.engineering() if eng is None else eng
    fx.write(root, "jsonl", eng, fx.product(fx.engineering()) if prod is None else prod)
    return facts.build(root, CONF)


def kinds_at(f, kind):
    return [s["pos"] for s in f["signals"] if s["kind"] == kind]


class BoundarySignalTests(unittest.TestCase):
    def test_gap_at_planted_phase_two(self):
        self.assertEqual(kinds_at(build(), "gap"), [8])

    def test_tag_shift_plateau_reports_first_position(self):
        self.assertEqual(kinds_at(build(), "tag_shift"), [8, 16])

    def test_file_turnover_at_pivot(self):
        self.assertEqual(kinds_at(build(), "file_turnover"), [16])

    def test_explicit_pivot_and_architecture(self):
        f = build()
        self.assertEqual(kinds_at(f, "explicit_pivot"), [16])
        self.assertEqual(kinds_at(f, "architecture"), [0, 2, 4, 6])

    def test_full_variant_pivot_field(self):
        seq = [dict(r, variant="lightweight", pivot_text="") for r in facts_seq()]
        seq[3] = dict(seq[3], variant="full", pivot_text="Switched from polling to events")
        seq[5] = dict(seq[5], variant="full", pivot_text="Plan held.")
        found = [s["pos"] for s in signals.boundary_signals(seq, CONF) if s["kind"] == "explicit_pivot"]
        self.assertIn(3, found)
        self.assertNotIn(5, found)

    def test_same_day_burst_has_no_gap(self):  # Review Focus 2
        eng = fx.engineering()
        for r in eng:
            r["date"] = "2026-01-05"
        self.assertEqual(kinds_at(build(eng=eng), "gap"), [])


def facts_seq():
    f = build()
    by_id = {r["id"]: r for r in f["records"]}
    return [by_id[i] for i in f["sequence"]]


class RecordSignalTests(unittest.TestCase):
    def test_open_followup_only_when_unreferenced(self):
        f = build()
        opened = [s["text"] for s in f["signals"] if s["kind"] == "open_followup"]
        self.assertEqual(opened, ["Benchmark the tokenizer cache"])

    def test_unverified_evidence(self):
        f = build()
        flagged = sorted(s["id"] for s in f["signals"] if s["kind"] == "unverified_evidence")
        eng, prod = fx.engineering(), fx.product(fx.engineering())
        self.assertEqual(flagged, sorted([eng[-1]["id"], prod[5]["id"]]))

    def test_crosslog_pair(self):
        f = build()
        pairs = [s for s in f["signals"] if s["kind"] == "crosslog_pair"]
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["target"], fx.engineering()[fx.PIVOT_POS]["id"])


class CandidateTests(unittest.TestCase):
    def test_precision_and_recall_on_planted_boundaries(self):
        f = build()
        found = [c["pos"] for c in f["candidates"]]
        tol = int(base.num(CONF, "tolerance"))
        hits = [p for p in fx.PLANTED if any(abs(p - c) <= tol for c in found)]
        true_pos = [c for c in found if any(abs(p - c) <= tol for p in fx.PLANTED)]
        self.assertEqual(len(hits) / len(fx.PLANTED), 1.0, found)
        self.assertGreaterEqual(len(true_pos) / max(len(found), 1), 0.66, found)

    def test_pivot_candidate_is_marked(self):
        f = build()
        pivot = [c for c in f["candidates"] if c["explicit_pivot"]]
        self.assertEqual([c["pos"] for c in pivot], [fx.PIVOT_POS])
        self.assertIn("file_turnover", pivot[0]["signals"])

    def test_architecture_alone_does_not_nominate(self):
        f = build()
        self.assertFalse([c for c in f["candidates"] if c["pos"] in (0, 2, 4, 6)])

    def test_explicit_pivot_wins_a_tie(self):
        sigs = [{"kind": "explicit_pivot", "pos": 5, "id": "b"}, {"kind": "gap", "pos": 4, "id": "a"},
                {"kind": "tag_shift", "pos": 4, "id": "a"}]
        seq = [{"id": str(i)} for i in range(10)]
        found = boundaries.candidates(sigs, seq, CONF)
        self.assertEqual([c["pos"] for c in found], [5])

    def test_thin_journal_has_no_candidates(self):
        f = build(eng=fx.engineering()[:4], prod=[])
        self.assertEqual(f["candidates"], [])
        self.assertTrue(any("fewer than" in w for w in f["warnings"]))


if __name__ == "__main__":
    unittest.main()
