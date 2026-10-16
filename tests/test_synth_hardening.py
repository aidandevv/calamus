"""Regression tests for the final-review findings: bad input never reaches a traceback,
snapshots do not leak across runs, secrets and non-files are refused, journal order holds,
and embed never touches a journal."""
import copy
import json
import os
import subprocess
import tempfile
import unittest

import helpers  # noqa: F401
import synth_fixture as fx
from test_synth_excerpt import E1, PARSE_V1, commit, git

import analysis
import base
import excerpt
import facts

CONF = base.default_conf("synth.conf")
STYLE = base.default_conf("style.conf")
SYN = os.path.join(helpers.SYNTH, "scripts", "calamus-synth")


def run(*args, cwd=None):
    return subprocess.run([SYN] + list(args), capture_output=True, text=True, cwd=cwd)


def built():
    root = tempfile.mkdtemp()
    eng = fx.engineering()
    fx.write(root, "jsonl", eng, fx.product(eng))
    f = facts.build(root, CONF)
    return f, fx.sample_analysis(f)


class AnalysisShapeTests(unittest.TestCase):
    """Important 1: realistic model mistakes are listed, not raised."""

    def test_broken_shapes_are_listed_problems(self):
        f, good = built()
        cases = [
            lambda a: a["pivots"][0].pop("rank"),
            lambda a: a["pivots"].append(dict(a["pivots"][0], id=f["sequence"][8], rank="2")),
            lambda a: a["phases"][0].update(first=[1]),
            lambda a: a["phases"][0].update(key=["p1"]),
            lambda a: a["epochs"][0].pop("name"),
            lambda a: a["pivots"][0].update(before=None),
            lambda a: a["phases"][1].pop("goal"),
        ]
        for i, mutate in enumerate(cases):
            a = copy.deepcopy(good)
            mutate(a)
            errs = analysis.validate(a, f)
            self.assertTrue(errs, i)

    def test_facts_without_required_keys_is_a_listed_problem(self):
        _, a = built()
        self.assertTrue(analysis.validate(a, {}))

    def test_cli_exits_2_without_traceback(self):
        f, good = built()
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "facts.json"), "w") as fh:
            json.dump(f, fh)
        a = copy.deepcopy(good)
        a["pivots"][0].pop("rank")
        with open(os.path.join(d, "analysis.json"), "w") as fh:
            json.dump(a, fh)
        p = run("diagrams", d)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertNotIn("Traceback", p.stderr)
        self.assertIn("rank", p.stderr)


class Repo(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp())
        git(self.root, "init", "-q")


class NoTracebackTests(Repo):
    """Important 2: bad input exits 2 with a message."""

    def test_unparseable_python_symbol(self):
        commit(self.root, {"core/parse.py": "def broken(:\n"}, "2026-01-05T09:00:00")
        fx.write(self.root, "jsonl", [E1], [])
        p = run("excerpt", "--root", self.root, "--id", E1["id"], "--path", "core/parse.py", "--symbol", "broken")
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_extract_out_is_a_file(self):
        fx.write(self.root, "jsonl", [E1], [])
        target = os.path.join(self.root, "taken")
        open(target, "w").close()
        p = run("extract", "--root", self.root, "--out", target)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_check_on_non_utf8_markdown(self):
        fx.write(self.root, "jsonl", [E1], [])
        d = os.path.join(self.root, "docs", "writeups", "w")
        os.makedirs(d)
        with open(os.path.join(d, "overview.md"), "wb") as fh:
            fh.write(b"# Overview\n\n\xff\xfe broken\n")
        p = run("check", d, "--root", self.root)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertNotIn("Traceback", p.stderr)


class StaleSnapshotTests(Repo):
    """Important 3: a new extract into the same directory clears the old snapshot."""

    def test_rerun_same_day_does_not_compare_against_old_draft(self):
        fx.write(self.root, "jsonl", [E1], [])
        d = os.path.join(self.root, "docs", "writeups", "w")
        os.makedirs(d)
        with open(os.path.join(d, "overview.md"), "w") as fh:
            fh.write("# Overview\n\nOld draft on 2026-01-05 [20260105-1000-0001].\n")
        self.assertEqual(run("snapshot", d, "--root", self.root).returncode, 0)
        self.assertEqual(run("extract", "--root", self.root, "--out", d).returncode, 0)
        with open(os.path.join(d, "overview.md"), "w") as fh:
            fh.write("# Overview\n\nNew draft on 2026-01-06.\n")
        p = run("check", d, "--root", self.root)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertNotIn("fidelity", p.stdout)


class SecretAndFileGuardTests(Repo):
    """Important 4 and re-graded Minor 1: secrets, key files, directories, and links are refused."""

    def setUp(self):
        super().setUp()
        pem_body = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7\n" * 3
        commit(self.root, {
            "core/conf.yml": "region: us-east-1\nAWS_SECRET_ACCESS_KEY=" + "wJalr" + "X" * 30 + "\n",
            "core/db.yml": "user: app\npassword: " + "hunter2" * 2 + "\n",
            "core/server.txt": "-----BEGIN " + "PRIVATE KEY-----\n" + pem_body + "-----END PRIVATE KEY-----\n",
            "keys/site.pem": "certificate text\n",
            ".env.local": "DEBUG=1\n",
            "core/parse.py": PARSE_V1,
        }, "2026-01-05T09:00:00")
        os.symlink("/etc/hosts", os.path.join(self.root, "core", "link"))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "link", date="2026-01-05T09:30:00")

    def refused(self, path, lines=(1, 2), at=None):
        with self.assertRaises(excerpt.Refused):
            excerpt.excerpt(self.root, E1, CONF, STYLE, path=path, lines=lines, at=at)

    def test_unquoted_env_and_yaml_secrets(self):
        self.refused("core/conf.yml")
        self.refused("core/db.yml")

    def test_private_key_body_without_header_line(self):
        self.refused("core/server.txt", lines=(2, 3))

    def test_key_and_env_files_by_name(self):
        self.refused("keys/site.pem", lines=(1, 1))
        self.refused(".env.local", lines=(1, 1))

    def test_directory_and_symlink(self):
        self.refused("core", at="HEAD")
        self.refused("core/link", lines=(1, 1), at="HEAD")

    def test_ordinary_code_still_excerpts(self):
        out = excerpt.excerpt(self.root, E1, CONF, STYLE, path="core/parse.py", symbol="parse")
        self.assertIn("def parse(text):", out)


class LegacyOrderTests(unittest.TestCase):
    """Important 5: same-day legacy entries keep journal order."""

    def test_same_day_legacy_entries_keep_file_order(self):
        root = tempfile.mkdtemp()
        fx.write(root, "md", [], None)
        titles = ["Zeta first", "Alpha second", "Mid third", "Beta fourth"]
        with open(os.path.join(root, "docs", "dev_journal.md"), "a") as fh:
            for t in titles:
                fh.write("\n### [CP-DEBUG] | 2026-03-01: %s\n\nHand-written note about %s.\n" % (t, t))
        f = facts.build(root, CONF)
        self.assertEqual([r["title"] for r in f["records"]], titles)


class EmbedJournalGuardTests(unittest.TestCase):
    """Important 6: embed never rewrites a journal."""

    def test_embed_on_docs_leaves_journals_untouched(self):
        root = tempfile.mkdtemp()
        fx.write(root, "md", [E1], [])
        docs = os.path.join(root, "docs")
        jpath = os.path.join(docs, "dev_journal.md")
        with open(jpath, "a") as fh:
            fh.write("\n<!-- diagram: x.mmd -->\n")
        with open(os.path.join(docs, "x.mmd"), "w") as fh:
            fh.write("%% sources: 20260105-1000-0001\ntimeline\n    title T\n")
        before = open(jpath, "rb").read()
        p = run("embed", docs)
        self.assertEqual(open(jpath, "rb").read(), before)
        self.assertNotEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
