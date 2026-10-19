import datetime
import os
import tempfile
import unittest

import helpers  # noqa: F401  (path setup)
import base


class ConfTests(unittest.TestCase):
    def test_parses_repeated_keys_and_comments(self):
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as f:
            f.write("# comment\nwindow = 4\nphrase = a b\nphrase = c\n\n")
        conf = base.load_conf(f.name)
        self.assertEqual(conf, {"window": ["4"], "phrase": ["a b", "c"]})
        self.assertEqual(base.num(conf, "window"), 4.0)
        self.assertEqual(base.items(conf, "phrase"), ["a b", "c"])
        self.assertEqual(base.items(conf, "absent"), [])

    def test_rejects_lines_without_equals(self):
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as f:
            f.write("rm -rf /\n")
        with self.assertRaises(base.UsageError):
            base.load_conf(f.name)

    def test_shipped_conf_has_every_engine_key(self):
        conf = base.default_conf("synth.conf")
        for key in ("min_entries", "window", "gap_factor", "gap_min_days", "jsd_min", "jaccard_min",
                    "tolerance", "phase_threshold", "weight_gap", "weight_tag_shift",
                    "weight_file_turnover", "weight_explicit_pivot", "weight_architecture",
                    "followup_overlap", "excerpt_grace_hours", "excerpt_max_lines", "max_excerpts",
                    "label_max_chars", "max_nodes", "timeline_max_events", "max_pivots",
                    "max_leaves", "max_extra_diagrams", "mermaid_cdn"):
            self.assertIn(key, conf)


class EntryTimeTests(unittest.TestCase):
    def test_time_from_id(self):
        self.assertEqual(base.entry_time("20260105-1432-ab12", "2026-01-05"),
                         datetime.datetime(2026, 1, 5, 14, 32))

    def test_legacy_resolves_to_end_of_day(self):
        self.assertEqual(base.entry_time("20260105-0000-ab12", "2026-01-05", legacy=True),
                         datetime.datetime(2026, 1, 5, 23, 59))
        self.assertEqual(base.entry_time("", "2026-01-05"), datetime.datetime(2026, 1, 5, 23, 59))


class SiblingTests(unittest.TestCase):
    def test_sibling_lib_is_found(self):
        base.use_calamus()
        self.assertTrue(os.path.isfile(os.path.join(base.CALAMUS_LIB, "records.py")))


if __name__ == "__main__":
    unittest.main()
