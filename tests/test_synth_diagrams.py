import copy
import json
import os
import tempfile
import unittest

import helpers  # noqa: F401
import synth_fixture as fx

import analysis
import base
import facts
import mermaid

CONF = base.default_conf("synth.conf")
HOSTILE = 'Fix "quoted" (paren] end: ; # <b> `tick` \U0001F642'


def build(eng=None):
    root = tempfile.mkdtemp()
    eng = fx.engineering() if eng is None else eng
    fx.write(root, "jsonl", eng, fx.product(fx.engineering()))
    f = facts.build(root, CONF)
    return f, fx.sample_analysis(f)


def conf(**over):
    c = dict(CONF)
    c.update({k: [str(v)] for k, v in over.items()})
    return c


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.f, self.a = build()

    def broken(self, mutate):
        a = copy.deepcopy(self.a)
        mutate(a)
        return analysis.validate(a, self.f)

    def test_sample_is_valid(self):
        self.assertEqual(analysis.validate(self.a, self.f), [])

    def test_each_rule_fails(self):
        seq = self.f["sequence"]
        cases = {
            "version": lambda a: a.update(version=2),
            "mode": lambda a: a.update(mode="weekly"),
            "first and last": lambda a: a["phases"][0].update(first="20990101-0000-ffff"),
            "overlaps": lambda a: a["phases"][1].update(first=seq[7]),
            "first comes after last": lambda a: a["phases"][2].update(first=seq[23], last=seq[16]),
            "unknown phase": lambda a: a["epochs"][0]["phases"].append("p9"),
            "ended_by": lambda a: a["epochs"][0].update(ended_by=seq[2]),
            "ranks repeat": lambda a: a["pivots"].append(dict(a["pivots"][0], id=seq[8])),
            "not an engine candidate": lambda a: a["pivots"][0].update(id=seq[3]),
        }
        for needle, mutate in cases.items():
            errs = self.broken(mutate)
            self.assertTrue(any(needle in e for e in errs), (needle, errs))

    def test_analyst_added_pivot_with_sources_is_valid(self):
        seq = self.f["sequence"]
        errs = self.broken(lambda a: a["pivots"].append(
            {"id": seq[3], "rank": 2, "label": "x", "before": "a", "trigger": "b", "after": "c",
             "rationale": "d", "origin": "analyst-added", "sources": [seq[3], seq[4]]}))
        self.assertEqual(errs, [])

    def test_non_object_entries_are_errors_not_crashes(self):
        self.assertTrue(self.broken(lambda a: a.update(phases=["p1"])))

    def test_malformed_json_is_usage_error(self):  # Review Focus 4
        d = tempfile.mkdtemp()
        for text in ("{not json", "[1, 2]"):
            with open(os.path.join(d, "analysis.json"), "w") as f:
                f.write(text)
            with self.assertRaises(base.UsageError):
                analysis.load(os.path.join(d, "analysis.json"))


class LabelTests(unittest.TestCase):
    def test_escapes_syntax_characters(self):
        out = mermaid.label(HOSTILE, 200)
        for raw in ('"', ";", "<", ">", "`"):
            self.assertNotIn(raw, out.replace("#34;", "").replace("#59;", "").replace("#35;", "")
                             .replace("#60;", "").replace("#62;", "").replace("#96;", ""))
        self.assertIn("#34;quoted#34;", out)

    def test_escapes_are_not_doubled(self):
        self.assertEqual(mermaid.label("#;", 10), "#35;#59;")

    def test_timeline_escapes_colon(self):
        self.assertIn("#58;", mermaid.label("a: b", 10, timeline=True))
        self.assertNotIn("#58;", mermaid.label("a: b", 10))

    def test_neutralizes_markdown_block_starts(self):
        # Mermaid decodes entities, then runs Markdown on flowchart labels:
        # list markers, headings, and backticks render as "Unsupported markdown".
        for text in ("1. First", "2) Second", "- dash", "* star", "+ plus", "# heading"):
            out = mermaid.label(text, 48).replace("#35;", "#")
            self.assertNotRegex(out, r"^([-*+#]|\d+[.)])[ \t]", text)
        self.assertNotIn("#96;", mermaid.label("a `tick` b", 48))
        self.assertNotIn("`", mermaid.label("a `tick` b", 48))

    def test_truncates_at_word_boundary(self):
        out = mermaid.label("alpha beta gamma delta", 12)
        self.assertEqual(out, "alpha beta…")


class GenerateTests(unittest.TestCase):
    def test_full_mode_files_and_determinism(self):
        f, a = build()
        one, two = mermaid.generate(f, a, CONF), mermaid.generate(f, a, CONF)
        self.assertEqual(sorted(one), ["mindmap.mmd", "phases.mmd", "pivots.mmd", "timeline.mmd"])
        self.assertEqual(one, two)
        for name, text in one.items():
            self.assertTrue(text.startswith("%% sources: "), name)
            self.assertTrue(text.endswith("\n"), name)

    def test_flowcharts_have_accessibility_lines(self):
        f, a = build()
        out = mermaid.generate(f, a, CONF)
        for name in ("phases.mmd", "pivots.mmd"):
            self.assertIn("    accTitle: ", out[name])
            self.assertIn("    accDescr: ", out[name])
        self.assertIn("    title ", out["timeline.mmd"])

    def test_phases_show_epochs_and_pivot_edge(self):
        f, a = build()
        text = mermaid.generate(f, a, CONF)["phases.mmd"]
        self.assertEqual(text.count("subgraph "), 2)
        self.assertIn('-->|"Move to the web"|', text)

    def test_hostile_titles_never_leak_raw_quotes(self):
        eng = fx.engineering()
        for r in eng:
            r["title"] = HOSTILE + " " + r["id"][-4:]
        f, a = build(eng)
        a["phases"][0]["name"] = HOSTILE
        a["pivots"][0]["label"] = HOSTILE
        for name, text in mermaid.generate(f, a, CONF).items():
            for line in text.split("\n"):
                inner = line.replace('["', "").replace('"]', "").replace('("', "").replace('")', "")
                inner = inner.replace('|"', "").replace('"|', "")
                self.assertNotIn('"', inner, (name, line))

    def test_pivot_titles_are_not_numbered_lists(self):
        f, a = build()
        text = mermaid.generate(f, a, CONF)["pivots.mmd"]
        self.assertIn('subgraph n1["Pivot 1: Move to the web"]', text)

    def test_node_cap_collapses_epochs(self):
        f, a = build()
        text = mermaid.generate(f, a, conf(max_nodes=3))["phases.mmd"]
        self.assertNotIn("subgraph", text)
        self.assertIn("(2 phases)", text)

    def test_timeline_cap(self):
        f, a = build()
        text = mermaid.generate(f, a, CONF)["timeline.mmd"]
        self.assertEqual(text.count(": and 4 more"), 3)

    def test_mindmap_leaf_cap(self):
        f, a = build()
        text = mermaid.generate(f, a, conf(max_leaves=2))["mindmap.mmd"]
        self.assertIn("more", text)

    def test_focus_mode_writes_brief_only(self):
        f, a = build()
        a["mode"] = "focus"
        self.assertEqual(sorted(mermaid.generate(f, a, CONF)), ["brief.mmd"])

    def test_thin_analysis_writes_timeline_and_mindmap(self):
        f, a = build()
        a.update(phases=[], epochs=[], pivots=[])
        self.assertEqual(sorted(mermaid.generate(f, a, CONF)), ["mindmap.mmd", "timeline.mmd"])


if __name__ == "__main__":
    unittest.main()
