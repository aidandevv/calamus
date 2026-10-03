import json
import os
import sys
import unittest

from helpers import REPO

ACT = os.path.join(REPO, "skills", "calamus", "evals", "activation")
sys.path.insert(0, ACT)

import activation  # noqa: E402


def tool_use(name, **inp):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": name, "input": inp}]}}


def results(variant, pairs):
    return [{"id": i, "variant": variant, "activated": a, "reference": None} for i, a in pairs]


class ClassifyTests(unittest.TestCase):
    def test_skill_tool_call_activates(self):
        r = activation.classify([tool_use("Skill", skill="calamus")])
        self.assertTrue(r["activated"])

    def test_reading_skill_md_activates(self):
        r = activation.classify([tool_use("Read", file_path="/x/.claude/skills/calamus/SKILL.md")])
        self.assertTrue(r["activated"])

    def test_reference_read_is_recorded(self):
        r = activation.classify([
            tool_use("Skill", skill="calamus"),
            tool_use("Read", file_path="/x/skills/calamus/references/product-insights.md")])
        self.assertEqual("product-insights.md", r["reference"])

    def test_other_skill_or_text_does_not_activate(self):
        r = activation.classify([
            tool_use("Skill", skill="other"),
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "calamus"}]}}])
        self.assertFalse(r["activated"])
        self.assertIsNone(r["reference"])


class ScoreTests(unittest.TestCase):
    PROMPTS = [{"id": "a", "expect": "activate"}, {"id": "b", "expect": "activate"},
               {"id": "c", "expect": "skip"}, {"id": "d", "expect": "skip"}]

    def test_recall_and_precision(self):
        m = activation.metrics(self.PROMPTS, results("shared", [("a", True), ("b", False), ("c", True), ("d", False)]))
        self.assertEqual(50.0, m["recall"])
        self.assertEqual(50.0, m["precision"])

    def test_no_activations_gives_zero_precision(self):
        m = activation.metrics(self.PROMPTS, results("shared", [("a", False), ("b", False), ("c", False), ("d", False)]))
        self.assertEqual(0.0, m["precision"])

    def test_decision_rule_thresholds(self):
        base = {"recall": 50.0, "precision": 80.0}
        self.assertEqual("tuned", activation.decide(base, {"recall": 60.0, "precision": 80.0}))
        self.assertEqual("shared", activation.decide(base, {"recall": 59.9, "precision": 84.9}))
        self.assertEqual("tuned", activation.decide(base, {"recall": 50.0, "precision": 85.0}))


class AssetTests(unittest.TestCase):
    def test_prompt_set_is_balanced_and_labeled(self):
        with open(os.path.join(ACT, "prompts.jsonl"), encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        kinds = {}
        for r in rows:
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
            want = "skip" if r["kind"] == "near-miss" else "activate"
            self.assertEqual(want, r["expect"], r["id"])
            self.assertTrue(r["prompt"].strip())
        self.assertEqual(len(rows), len({r["id"] for r in rows}))
        for k in ("direct", "indirect", "near-miss"):
            self.assertTrue(8 <= kinds.get(k, 0) <= 12, (k, kinds))

    def test_tuned_variant_differs_and_fits(self):
        shared = activation.shared_description(os.path.join(REPO, "skills", "calamus", "SKILL.md"))
        with open(os.path.join(ACT, "variants", "tuned.txt"), encoding="utf-8") as f:
            tuned = f.read().strip()
        self.assertTrue(shared)
        self.assertNotEqual(shared, tuned)
        self.assertLessEqual(len(tuned), 1024)

    def test_with_description_rewrites_only_frontmatter(self):
        with open(os.path.join(REPO, "skills", "calamus", "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
        out = activation.with_description(text, "New words.")
        self.assertIn("description: >-\n  New words.\n", out)
        self.assertEqual(text.split("\n---\n", 1)[1], out.split("\n---\n", 1)[1])


if __name__ == "__main__":
    unittest.main()
