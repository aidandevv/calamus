import os
import shutil
import subprocess
import tempfile
import unittest

import helpers  # noqa: F401
import synth_fixture as fx

import base
import embed
import facts
import mermaid
import mmdlint

CONF = base.default_conf("synth.conf")
HOSTILE = 'Fix "quoted" (paren] end: ; # <b> `tick` \U0001F642'
SRC = "%% sources: 20260105-1000-0001\n"


def generated(hostile=False):
    root = tempfile.mkdtemp()
    eng = fx.engineering()
    if hostile:
        for r in eng:
            r["title"] = HOSTILE + " " + r["id"][-4:]
    fx.write(root, "jsonl", eng, fx.product(fx.engineering()))
    f = facts.build(root, CONF)
    a = fx.sample_analysis(f)
    if hostile:
        a["phases"][0]["name"] = HOSTILE
        a["pivots"][0]["label"] = HOSTILE
    return mermaid.generate(f, a, CONF)


def rules(text, conf=CONF):
    return " | ".join(m for _, m in mmdlint.lint(text, conf))


class LintAcceptsTests(unittest.TestCase):
    def test_generated_diagrams_pass(self):
        for hostile in (False, True):
            for name, text in generated(hostile).items():
                self.assertEqual(mmdlint.lint(text, CONF), [], (hostile, name, text))

    def test_valid_sequence_and_state(self):
        seq = SRC + ("sequenceDiagram\n    participant H as Host\n    participant S as Script\n"
                     "    H->>S: pre-compact event\n    alt timeout\n        S-->>H: exit 0\n    end\n")
        state = SRC + "stateDiagram-v2\n    [*] --> Pending\n    Pending --> Resolved\n"
        self.assertEqual(mmdlint.lint(seq, CONF), [])
        self.assertEqual(mmdlint.lint(state, CONF), [])

    @unittest.skipUnless(shutil.which("mmdc"), "Mermaid CLI not installed")
    def test_mmdc_parses_generated(self):
        d = tempfile.mkdtemp()
        for name, text in generated(True).items():
            path = os.path.join(d, name)
            with open(path, "w") as f:
                f.write(text)
            self.assertIsNone(mmdlint.mmdc(path), name)


class LintRejectsTests(unittest.TestCase):
    def test_each_fault(self):
        cases = {
            "sources": "flowchart LR\n    n1[\"a\"]\n",
            "unsupported declaration": SRC + "pie\n    \"a\" : 1\n",
            "unbalanced []": SRC + "flowchart LR\n    n1[\"a\"] --> n2[b\n",
            "raw quote inside a label": SRC + "flowchart LR\n    n1[\"a \"b\" c\"]\n",
            "subgraph without end": SRC + "flowchart LR\n    subgraph n1[\"x\"]\n        n2[\"a\"]\n",
            "end without subgraph": SRC + "flowchart LR\n    n1[\"a\"]\n    end\n",
            "undeclared node n9": SRC + "flowchart LR\n    n1[\"a\"]\n    n1 --> n9\n",
            "undeclared participant": SRC + "sequenceDiagram\n    participant A\n    A->>B: hi\n",
            "block without end": SRC + "sequenceDiagram\n    participant A\n    loop retry\n        A->>A: x\n",
            "neither a section": SRC + "timeline\n    title T\n    just words\n",
            "tabs": SRC + "mindmap\n  n1((\"r\"))\n\tn2[\"a\"]\n",
        }
        for needle, text in cases.items():
            self.assertIn(needle, rules(text), needle)

    def test_node_cap(self):
        text = SRC + "flowchart LR\n    n1[\"a\"]\n    n2[\"b\"]\n    n3[\"c\"]\n"
        conf = dict(CONF, max_nodes=["2"])
        self.assertIn("exceed max_nodes", rules(text, conf))

    def test_mindmap_children_cap(self):
        kids = "".join('    n%d["k"]\n' % i for i in range(2, 10))
        text = SRC + 'mindmap\n  n1(("r"))\n' + kids
        self.assertIn("exceed max_leaves", rules(text, dict(CONF, max_leaves=["3"])))


class EmbedTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        with open(os.path.join(self.d, "timeline.mmd"), "w") as f:
            f.write(SRC + "timeline\n    title T\n    2026-01-05 : start\n")

    def test_inserts_then_is_idempotent(self):
        md = "# Overview\n\n<!-- diagram: timeline.mmd -->\n\nText.\n"
        once, errs = embed.embed(md, self.d)
        self.assertEqual(errs, [])
        self.assertIn("<!-- diagram: timeline.mmd -->\n```mermaid\n%% sources:", once)
        twice, _ = embed.embed(once, self.d)
        self.assertEqual(once, twice)
        self.assertEqual(embed.check(once, self.d), [])

    def test_stale_block_fails_check_and_is_replaced(self):
        md = "<!-- diagram: timeline.mmd -->\n```mermaid\nold\n```\n"
        self.assertTrue(embed.check(md, self.d))
        fixed, _ = embed.embed(md, self.d)
        self.assertNotIn("old", fixed)

    def test_missing_file_and_unterminated_block(self):
        _, errs = embed.embed("<!-- diagram: nope.mmd -->\n", self.d)
        self.assertIn("does not exist", errs[0][1])
        _, errs = embed.embed("<!-- diagram: timeline.mmd -->\n```mermaid\nnever closed\n", self.d)
        self.assertIn("unterminated", errs[0][1])


if __name__ == "__main__":
    unittest.main()
