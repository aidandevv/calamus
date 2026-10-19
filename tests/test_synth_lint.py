import os
import tempfile
import unittest

import helpers  # noqa: F401

import base
import lint
import voice

STYLE = base.default_conf("style.conf")

# Measured: 6 sentences, mean 16.8 words, 33% short, none long, 3 per paragraph.
CLEAN = (
    "The parser moved to a streaming design in early January, after a 2 GB log exhausted memory on the "
    "shared build server [20260105-1000-0001]. Batch parsing had been simpler to test. Streaming kept peak "
    "memory under 50 MB and cut the median run on the nightly fixture from 40 seconds to 9 "
    "[20260109-1000-0003].\n\n"
    "The change also moved error handling into the reader, so a single malformed line now fails on its own "
    "instead of aborting the whole file. Two follow-ups remain open. Neither the retry policy nor the "
    "progress reporting has yet been measured against inputs larger than the log that started the change.\n")

FLAGGED = {
    "stock-phrase": "The cache is a robust choice.",
    "filler-transition": "Additionally, the cache was removed.",
    "stacked-hedge": "The cache may possibly fail under load.",
    "vague-referent": "This is why the cache was removed.",
    "contrast-frame": "The change was not only faster but also smaller.",
    "empty-intensifier": "The cache was very slow.",
    "tag-leak": "The CP-PIVOT entry moved the project to the web.",
    "citation-clutter": "The cache moved [20260105-1000-0001, 20260105-1000-0002, 20260105-1000-0003, "
                        "20260105-1000-0004].",
    "repeated-opener": "The cache moved. The parser stayed. The tests passed.",
    "band-em-dash": "The cache moved — the parser stayed.",
    "band-exclamation": "The cache moved!",
    "band-first-person": "We moved the cache.",
    "band-contraction": "The cache didn't move.",
}
LONG = ("This sentence has exactly enough words to sit well above the thirty word line because it keeps going "
        "and going with more words added on purpose here, and then a few more words follow it "
        "[20260105-1000-0001]. ")


def rules(md, fname="notes.md", style=STYLE):
    return {f["rule"] for f in lint.lint(md, fname, style)}


class LintTests(unittest.TestCase):
    def test_clean_passage_has_no_findings(self):
        self.assertEqual(lint.lint("# Overview\n\n" + CLEAN, "overview.md", STYLE), [])

    def test_each_rule_flags_its_passage(self):
        for rule, text in FLAGGED.items():
            self.assertIn(rule, rules(text + "\n"), rule)

    def test_clean_passage_triggers_none_of_the_phrase_rules(self):
        self.assertFalse(rules(CLEAN) & set(FLAGGED))

    def test_bullet_heavy_only_in_narrative_files(self):
        md = "- one\n- two\n- three\n\nOne paragraph line.\n"
        self.assertIn("bullet-heavy", rules(md, "overview.md"))
        self.assertNotIn("bullet-heavy", rules(md, "decisions.md"))

    def test_length_bands(self):
        long_md = LONG * 3 + "\n\n" + LONG * 3 + "\n"
        self.assertIn("band-long-sentences", rules(long_md))
        self.assertIn("band-mean-length", rules(long_md))
        short_md = "Short one. Short two. Short three. Short four. Short five. Short six.\n"
        self.assertIn("band-short-sentences", rules(short_md))
        self.assertIn("band-paragraph-length", rules(short_md))

    def test_bands_skip_short_files(self):
        self.assertFalse({r for r in rules("Short one. Short two.\n") if r.startswith("band-mean")})

    def test_code_comments_tables_and_captions_are_ignored(self):
        md = ("```python\nx = 1  # we don't care!\n```\n"
              "<!-- excerpt: a.py@abc:L1-L2:max25 [20260105-1000-0001] -->\n"
              "`a.py` at `abc`, lines 1-2 [20260105-1000-0001]\n\n"
              "| Tag | Note |\n|---|---|\n| CP-PIVOT | We moved! |\n\n<!-- gap: we don't know -->\n")
        self.assertEqual(lint.lint(md, "notes.md", STYLE), [])

    def test_findings_carry_line_numbers(self):
        found = lint.lint("# Title\n\nThe cache is a robust choice.\n", "notes.md", STYLE)
        self.assertEqual([(f["line"], f["rule"]) for f in found], [(3, "stock-phrase")])


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.home = tempfile.mkdtemp()

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
        return path

    def test_lookup_order(self):
        env = {"HOME": self.home}
        self.assertIsNone(voice.locate(self.root, env=env))
        user = self.write(os.path.join(self.home, ".config", "calamus", "voice.md"), "---\n---\n")
        self.assertEqual(voice.locate(self.root, env=env), user)
        xdg = self.write(os.path.join(self.home, "xdg", "calamus", "voice.md"), "---\n---\n")
        self.assertEqual(voice.locate(self.root, env=dict(env, XDG_CONFIG_HOME=os.path.join(self.home, "xdg"))), xdg)
        proj = self.write(os.path.join(self.root, ".calamus", "voice.md"), "---\n---\n")
        self.assertEqual(voice.locate(self.root, env=env), proj)
        explicit = self.write(os.path.join(self.home, "mine.md"), "---\n---\n")
        self.assertEqual(voice.locate(self.root, explicit, env=env), explicit)
        with self.assertRaises(base.UsageError):
            voice.locate(self.root, os.path.join(self.home, "absent.md"), env=env)

    def test_profile_overrides_bands_and_extends_lists(self):
        path = self.write(os.path.join(self.home, "v.md"),
                          "---\nband_contraction_max: 5\nstock_phrase: synergy\nsecret_pattern: x\n---\n"
                          "## Register: engineering\nRules for the model.\n")
        style = voice.merged_style(STYLE, path)
        self.assertEqual(style["band_contraction_max"], ["5"])
        self.assertIn("synergy", style["stock_phrase"])
        self.assertIn("robust", style["stock_phrase"])
        self.assertEqual(style["secret_pattern"], STYLE["secret_pattern"])
        self.assertNotIn("band-contraction", rules("The cache didn't move.\n", style=style))

    def test_unclosed_front_matter_is_usage_error(self):
        path = self.write(os.path.join(self.home, "v.md"), "---\nband_contraction_max: 5\n")
        with self.assertRaises(base.UsageError):
            voice.front_matter(path)


if __name__ == "__main__":
    unittest.main()
