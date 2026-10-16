import json
import os
import shutil
import tempfile
import unittest

import helpers  # noqa: F401
import synth_fixture as fx

import base
import facts

CONF = base.default_conf("synth.conf")


def tmp_root(fmt="jsonl", eng=None, prod=None):
    root = tempfile.mkdtemp()
    eng = fx.engineering() if eng is None else eng
    fx.write(root, fmt, eng, fx.product(fx.engineering()) if prod is None else prod)
    return root


class ExtractTests(unittest.TestCase):
    def test_records_are_slim_and_sorted(self):
        f = facts.build(tmp_root(), CONF)
        self.assertEqual(len(f["records"]), 30)
        dates = [(r["date"], r["id"]) for r in f["records"]]
        self.assertEqual(dates, sorted(dates))
        first = f["records"][0]
        self.assertEqual(sorted(first), sorted([
            "id", "journal", "variant", "date", "time", "tag", "title", "files", "summary",
            "evidence", "followups", "pivot_text", "has_code", "legacy", "crosslog"]))
        self.assertEqual(first["time"], "10:00")

    def test_sequence_is_engineering_when_enough(self):
        f = facts.build(tmp_root(), CONF)
        self.assertEqual(len(f["sequence"]), 24)
        eng_ids = [r["id"] for r in f["records"] if r["journal"] == "engineering"]
        self.assertEqual(f["sequence"], eng_ids)

    def test_sequence_falls_back_to_all_entries(self):
        f = facts.build(tmp_root(eng=fx.engineering()[:6]), CONF)
        self.assertEqual(len(f["sequence"]), 12)

    def test_crosslog_resolves_to_id(self):
        f = facts.build(tmp_root(), CONF)
        linked = [r for r in f["records"] if r["crosslog"]]
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]["crosslog"], fx.engineering()[fx.PIVOT_POS]["id"])

    def test_unmatched_crosslog_warns(self):
        prod = fx.product(fx.engineering())
        prod[3]["crosslog"]["title"] = "No such entry"
        f = facts.build(tmp_root(prod=prod), CONF)
        self.assertTrue(any("unmatched cross-log" in w for w in f["warnings"]))

    def test_stats_and_supersession_warning(self):
        f = facts.build(tmp_root(), CONF)
        self.assertEqual(f["stats"]["entries"], {"engineering": 24, "product": 6})
        self.assertEqual(f["stats"]["first"], "2026-01-05")
        self.assertEqual(f["stats"]["tags"]["CP-PIVOT"], 1)
        self.assertTrue(any("supersession" in w for w in f["warnings"]))

    def test_since_filters(self):
        f = facts.build(tmp_root(), CONF, since="2026-02-11")
        self.assertTrue(all(r["date"] >= "2026-02-11" for r in f["records"]))

    def test_format_parity(self):
        outs = []
        for fmt in ("md", "xml", "jsonl"):
            f = facts.build(tmp_root(fmt), CONF)
            f.pop("journals")
            outs.append(facts.dump(f))
        self.assertEqual(outs[0], outs[1])
        self.assertEqual(outs[1], outs[2])

    def test_dump_is_deterministic(self):
        root = tmp_root()
        self.assertEqual(facts.dump(facts.build(root, CONF)), facts.dump(facts.build(root, CONF)))
        self.assertTrue(facts.dump(facts.build(root, CONF)).endswith("}\n"))

    def test_legacy_md_entry_is_kept(self):  # Review Focus 1
        root = tmp_root("md")
        with open(os.path.join(root, "docs", "dev_journal.md"), "a", encoding="utf-8") as f:
            f.write("\n### [CP-DEBUG] | 2026-03-01: Hand-written note\n\nSomething broke and was fixed.\n")
        f = facts.build(root, CONF)
        legacy = [r for r in f["records"] if r["legacy"]]
        self.assertEqual(len(legacy), 1)
        self.assertEqual(legacy[0]["time"], "")

    def test_missing_journals_is_usage_error(self):
        with self.assertRaises(base.UsageError):
            facts.build(tempfile.mkdtemp(), CONF)

    def test_entry_lookup(self):
        root = tmp_root()
        eng = fx.engineering()
        self.assertEqual(facts.entry(root, eng[3]["id"])["title"], eng[3]["title"])
        with self.assertRaises(base.UsageError):
            facts.entry(root, "20990101-0000-ffff")


if __name__ == "__main__":
    unittest.main()
