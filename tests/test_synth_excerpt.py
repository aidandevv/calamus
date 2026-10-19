import os
import shutil
import subprocess
import tempfile
import unittest

import helpers  # noqa: F401
import synth_fixture as fx

import base
import excerpt
import facts

CONF = base.default_conf("synth.conf")
STYLE = base.default_conf("style.conf")
SYN = os.path.join(helpers.SYNTH, "scripts", "calamus-synth")

PARSE_V1 = ('import functools\n\n\n@functools.lru_cache(maxsize=None)\ndef parse(text):\n'
            '    """Split text into tokens."""\n    return tuple(text.split())\n\n\nclass Parser:\n    pass\n')
PARSE_V2 = PARSE_V1.replace("return tuple(text.split())", "return tuple(t for t in text.split() if t)")
RUN_SH = '#!/bin/sh\nrun() {\n  echo "running"\n}\nrun\n'
LONG = "".join("x%d = %d\n" % (i, i) for i in range(1, 41))


def entry(rid, date, files):
    return {"record": "entry", "journal": "engineering", "variant": "lightweight", "id": rid,
            "tag": "CP-REFACTOR", "date": date, "title": "Entry " + rid[-4:], "summary": "Changed code.",
            "files": files, "tradeoff": "Small change.",
            "evidence": {"status": "verified", "text": "Tests pass."}, "followups": []}


E1 = entry("20260105-1000-0001", "2026-01-05", ["core/parse.py"])
E2 = entry("20260106-0830-0002", "2026-01-06", ["core/parse.py"])
E3 = entry("20260109-1000-0003", "2026-01-09", ["tools/run.sh"])
FULL = {"record": "entry", "journal": "engineering", "variant": "full", "id": "20260107-1200-0004",
        "tag": "CP-ARCHITECTURE", "date": "2026-01-07", "title": "Parser contract",
        "context": ["Need a stable parser contract."],
        "design": {"choice": "A pure function", "alternatives": "A class", "why": "Easier to test"},
        "pivot": ["Plan held."], "impl": {"files": ["core/parse.py"], "pattern": "pure functions"},
        "verification": ["Unit tests pass."], "references": [],
        "code": "def parse(text):\n    return text.split()\n", "crosslog_notes": [], "followups": []}


def git(root, *args, date=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    return subprocess.run(["git", "-C", root, "-c", "commit.gpgsign=false"] + list(args), env=env,
                          check=True, capture_output=True, text=True).stdout.strip()


def commit(root, files, date):
    for path, text in files.items():
        full = os.path.join(root, path)
        if text is None:
            os.remove(full)
            continue
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb" if isinstance(text, bytes) else "w") as f:
            f.write(text)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change", date=date)
    return git(root, "rev-parse", "HEAD")[:12]


class Repo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.realpath(tempfile.mkdtemp())
        git(cls.root, "init", "-q")
        cls.c1 = commit(cls.root, {"core/parse.py": PARSE_V1, "tools/run.sh": RUN_SH, "core/long.py": LONG,
                                   "core/blob.bin": b"\x00\x01binary",
                                   "core/keys.py": 'API_KEY = "' + "a" * 12 + '"\n'}, "2026-01-05T09:00:00")
        cls.c2 = commit(cls.root, {"core/parse.py": PARSE_V2}, "2026-01-06T09:00:00")
        cls.c3 = commit(cls.root, {"tools/run.sh": None}, "2026-01-08T09:00:00")
        fx.write(cls.root, "jsonl", [E1, E2, FULL, E3], [])

    def ex(self, rec, **kw):
        return excerpt.excerpt(self.root, rec, CONF, STYLE, **kw)


class ResolveTests(Repo):
    def test_commit_by_entry_time(self):
        when = base.entry_time(E1["id"], E1["date"])
        self.assertEqual(excerpt.resolve_commit(self.root, "core/parse.py", when, 12)["commit"], self.c1)

    def test_grace_covers_commit_after_entry(self):
        when = base.entry_time(E2["id"], E2["date"])
        self.assertEqual(excerpt.resolve_commit(self.root, "core/parse.py", when, 12)["commit"], self.c2)
        self.assertEqual(excerpt.resolve_commit(self.root, "core/parse.py", when, 0)["commit"], self.c1)

    def test_code_refs_in_facts(self):
        f = facts.build(self.root, CONF)
        refs = {r["id"]: r.get("code_refs") for r in f["records"]}
        self.assertEqual(refs[E1["id"]], [{"path": "core/parse.py", "commit": self.c1, "date": "2026-01-05"}])
        self.assertEqual(refs[E3["id"]][0]["commit"], self.c3)


class SelectionTests(Repo):
    def test_python_symbol_includes_decorator(self):
        out = self.ex(E1, path="core/parse.py", symbol="parse")
        self.assertIn("<!-- excerpt: core/parse.py@%s:L4-L7:max25 [%s] -->" % (self.c1, E1["id"]), out)
        self.assertIn("`core/parse.py` at `%s`, lines 4-7 [%s]" % (self.c1[:7], E1["id"]), out)
        self.assertIn("```python\n@functools.lru_cache(maxsize=None)\ndef parse(text):", out)
        self.assertIn("return tuple(text.split())\n```\n", out)

    def test_shell_function(self):
        out = self.ex(E1, path="tools/run.sh", symbol="run")
        self.assertIn(":L2-L4:max25", out)
        self.assertIn('```bash\nrun() {\n  echo "running"\n}\n```', out)

    def test_unknown_symbol_is_usage_error(self):
        with self.assertRaises(base.UsageError):
            self.ex(E1, path="core/parse.py", symbol="missing")

    def test_line_range_with_elision(self):
        out = self.ex(E1, path="core/long.py", lines=(1, 40), max_lines=10)
        body = out.split("```python\n", 1)[1].split("\n```", 1)[0].split("\n")
        self.assertEqual(len(body), 10)
        self.assertEqual(body[5], "# ... 31 lines omitted ...")
        self.assertEqual((body[0], body[-1]), ("x1 = 1", "x40 = 40"))

    def test_diff(self):
        out = self.ex(E2, path="core/parse.py", diff=True)
        self.assertIn("core/parse.py@%s..%s:diff:max25" % (self.c1, self.c2), out)
        self.assertIn("-    return tuple(text.split())", out)
        self.assertIn("+    return tuple(t for t in text.split() if t)", out)
        self.assertIn("```diff\n@@", out)

    def test_journaled(self):
        out = self.ex(FULL, journaled=True)
        self.assertIn("<!-- excerpt: journal:max25 [%s] -->" % FULL["id"], out)
        self.assertIn("```python\ndef parse(text):\n    return text.split()\n```", out)

    def test_fence_grows_past_backticks_in_code(self):
        rec = dict(FULL, code='s = "```"\n')
        self.assertIn("````python\n", self.ex(rec, journaled=True))


class GuardTests(Repo):
    def test_absolute_and_parent_paths(self):
        for bad in ("/etc/passwd", "../outside.py", "core/../../x.py", "C:/x.py", "has space.py"):
            with self.assertRaises(excerpt.Refused):
                self.ex(E1, path=bad, lines=(1, 1))

    def test_path_deleted_before_commit(self):  # Review Focus 3
        with self.assertRaises(excerpt.Refused) as cm:
            self.ex(E3, path="tools/run.sh", lines=(1, 2))
        self.assertIn("not found at commit", str(cm.exception))

    def test_binary(self):
        with self.assertRaises(excerpt.Refused):
            self.ex(E1, path="core/blob.bin", lines=(1, 1))

    def test_secret_is_withheld_and_not_echoed(self):
        with self.assertRaises(excerpt.Refused) as cm:
            self.ex(E1, path="core/keys.py", lines=(1, 1))
        self.assertNotIn("a" * 12, str(cm.exception))

    def test_cli_exit_codes(self):
        run = lambda *a: subprocess.run([SYN, "excerpt", "--root", self.root] + list(a),
                                        capture_output=True, text=True)
        self.assertEqual(run("--id", E3["id"], "--path", "tools/run.sh", "--lines", "1-2").returncode, 4)
        self.assertEqual(run("--id", "20990101-0000-ffff", "--path", "a.py", "--lines", "1-2").returncode, 2)
        self.assertEqual(run("--id", E1["id"], "--path", "core/parse.py").returncode, 2)
        ok = run("--id", E1["id"], "--path", "core/parse.py", "--symbol", "parse")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertTrue(ok.stdout.startswith("<!-- excerpt: core/parse.py@"))


class VerifyTests(Repo):
    def lookup(self, rid):
        return facts.entry(self.root, rid)

    def test_fresh_block_verifies_and_mutation_fails(self):
        block = self.ex(E1, path="core/parse.py", symbol="parse")
        md = "The cache wraps the parser.\n\n" + block + "\nThat kept parsing pure.\n"
        self.assertEqual(excerpt.verify(md, self.root, CONF, STYLE, self.lookup), [])
        bad = md.replace("return tuple(text.split())", "return list(text.split())")
        self.assertEqual(len(excerpt.verify(bad, self.root, CONF, STYLE, self.lookup)), 1)

    def test_every_marker_kind_round_trips(self):
        for rec, kw in ((E2, {"path": "core/parse.py", "diff": True}), (FULL, {"journaled": True}),
                        (E1, {"path": "core/long.py", "lines": (1, 40), "max_lines": 10})):
            md = self.ex(rec, **kw)
            self.assertEqual(excerpt.verify(md, self.root, CONF, STYLE, self.lookup), [], kw)


class WorkingTreeTests(unittest.TestCase):
    def test_non_git_project_uses_working_tree(self):
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "core"))
        with open(os.path.join(root, "core", "parse.py"), "w") as f:
            f.write(PARSE_V1)
        fx.write(root, "jsonl", [E1], [])
        out = excerpt.excerpt(root, E1, CONF, STYLE, path="core/parse.py", lines=(5, 7))
        self.assertIn("core/parse.py@working-tree:L5-L7:max25", out)
        self.assertIn("in the working tree, lines 5-7", out)
        self.assertNotIn("code_refs", facts.build(root, CONF)["records"][0])


if __name__ == "__main__":
    unittest.main()
