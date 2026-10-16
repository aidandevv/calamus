import unittest

import helpers  # noqa: F401

import fidelity

DRAFT = ("## Findings\n\n"
         "The reader moved to streaming on 2026-01-05, which cut runs to 9 s and memory to 50 MB "
         "in `core/parse.py` [20260105-1000-0001].\n\n"
         "```python\nprint('2027-01-01 99 ms /Users/x')\n```\n")


class TokenTests(unittest.TestCase):
    def test_counts_the_four_kinds(self):
        keys = set(fidelity.tokens(DRAFT))
        self.assertEqual(keys, {"id 20260105-1000-0001", "date 2026-01-05", "num 9s", "num 50MB",
                                "path core/parse.py"})

    def test_prose_rewrite_passes(self):
        voiced = DRAFT.replace("The reader moved to streaming", "Streaming replaced batch reads")
        self.assertEqual(fidelity.compare(DRAFT, voiced), [])

    def test_each_mutation_fails(self):
        for old, new in (("20260105-1000-0001", "20260105-1000-0002"), ("2026-01-05", "2026-01-06"),
                         ("9 s", "8 s"), ("`core/parse.py`", "`core/parser.py`")):
            self.assertTrue(fidelity.compare(DRAFT, DRAFT.replace(old, new)), old)

    def test_dropping_a_citation_fails(self):
        self.assertTrue(fidelity.compare(DRAFT, DRAFT.replace(" [20260105-1000-0001]", "")))


class PathTests(unittest.TestCase):
    def test_absolute_paths_flagged_outside_code(self):
        for bad in ("/Users/someone/x.py", "/home/a/b", "~/notes.md", "/private/tmp/x", "C:\\work\\x.py"):
            self.assertTrue(fidelity.abs_paths("See %s for details.\n" % bad), bad)
        self.assertEqual(fidelity.abs_paths(DRAFT), [])
        self.assertEqual(fidelity.abs_paths("See `docs/dev_journal.md` and https://example.com/a/b.\n"), [])


class FindingsTests(unittest.TestCase):
    def test_uncited_paragraph_in_findings_warns(self):
        md = ("## Background\n\nNo citation here is fine.\n\n## Findings\n\n### Memory\n\n"
              "Memory fell sharply.\n\nMemory fell to 50 MB [20260105-1000-0001].\n\n"
              "Latency probably tracked memory (inferred).\n\n**Cost:** Low.\n\n## Discussion\n\nFree text.\n")
        warns = fidelity.uncited_findings(md)
        self.assertEqual([n for n, _ in warns], [9])


if __name__ == "__main__":
    unittest.main()
