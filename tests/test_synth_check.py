import os
import shutil
import subprocess
import tempfile
import unittest

import helpers  # noqa: F401
import synth_fixture as fx
from test_synth_excerpt import E1, PARSE_V1, commit, git

import base
import excerpt

CONF = base.default_conf("synth.conf")
STYLE = base.default_conf("style.conf")
SYN = os.path.join(helpers.SYNTH, "scripts", "calamus-synth")
TIMELINE = "%% sources: 20260105-1000-0001\ntimeline\n    title Project timeline\n    2026-01-05 : start\n"


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp())
        git(self.root, "init", "-q")
        commit(self.root, {"core/parse.py": PARSE_V1}, "2026-01-05T09:00:00")
        fx.write(self.root, "jsonl", [E1], [])
        self.dir = os.path.join(self.root, "docs", "writeups", "w")
        os.makedirs(self.dir)
        with open(os.path.join(self.dir, "timeline.mmd"), "w") as f:
            f.write(TIMELINE)
        block = excerpt.excerpt(self.root, E1, CONF, STYLE, path="core/parse.py", symbol="parse")
        self.md = ("# Overview\n\nThe parser gained a cache on 2026-01-05 [20260105-1000-0001].\n\n"
                   "<!-- diagram: timeline.mmd -->\n```mermaid\n" + TIMELINE.rstrip("\n") + "\n```\n\n"
                   "The decorator below is the whole change.\n\n" + block)
        self.write(self.md)

    def write(self, text, name="overview.md"):
        with open(os.path.join(self.dir, name), "w") as f:
            f.write(text)

    def run_cmd(self, *args):
        return subprocess.run([SYN] + list(args) + ["--root", self.root], capture_output=True, text=True)

    def check(self):
        return self.run_cmd("check", self.dir)

    def test_clean_draft_passes_without_snapshot(self):  # Review Focus 5
        p = self.check()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("fidelity", p.stdout)
        self.assertIn("check: 0 failures", p.stdout)

    def test_absolute_path_fails(self):
        self.write(self.md + "\nSee /Users/someone/notes.md.\n")
        p = self.check()
        self.assertEqual(p.returncode, 3)
        self.assertIn("abs-path", p.stdout)

    def test_mutated_excerpt_fails(self):
        self.write(self.md.replace("return tuple(text.split())", "return list(text.split())"))
        self.assertIn("FAIL overview.md", self.check().stdout)

    def test_stale_diagram_fails(self):
        with open(os.path.join(self.dir, "timeline.mmd"), "a") as f:
            f.write("    2026-01-06 : more\n")
        p = self.check()
        self.assertEqual(p.returncode, 3)
        self.assertIn("diagram", p.stdout)

    def test_broken_mmd_fails(self):
        with open(os.path.join(self.dir, "extra-flow.mmd"), "w") as f:
            f.write("%% sources: 20260105-1000-0001\nflowchart LR\n    n1[\"a\"] --> n9\n")
        p = self.check()
        self.assertEqual(p.returncode, 3)
        self.assertIn("undeclared node n9", p.stdout)

    def test_snapshot_then_voice_pass(self):
        self.assertEqual(self.run_cmd("snapshot", self.dir).returncode, 0)
        snap = os.path.join(self.root, ".calamus", "state", "synth", "w", "overview.md")
        self.assertTrue(os.path.isfile(snap))
        self.write(self.md.replace("The parser gained a cache", "A cache was added to the parser"))
        self.assertEqual(self.check().returncode, 0)
        self.write(self.md.replace("2026-01-05 [", "2026-01-06 ["))
        p = self.check()
        self.assertEqual(p.returncode, 3)
        self.assertIn("fidelity", p.stdout)

    def test_lint_findings_are_warnings(self):
        self.write(self.md + "\nAdditionally, the cache is robust.\n")
        p = self.check()
        self.assertEqual(p.returncode, 0)
        self.assertIn("WARN overview.md", p.stdout)
        self.assertIn("stock-phrase", p.stdout)


if __name__ == "__main__":
    unittest.main()
