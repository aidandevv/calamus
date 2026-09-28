import datetime
import os
import re
import shutil
import tempfile
import unittest

from helpers import ENG_LIGHT, REPO, sample_records

import journal
import records
import render
import schema

NOW = datetime.datetime(2026, 9, 27, 17, 0)


def read(path, mode="r"):
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def strip_meta(recs):
    return [{k: v for k, v in r.items() if k not in ("raw",)} for r in recs]


class RoundTripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_round_trip_every_format(self):
        eng, prod, markers = sample_records()
        for jname, recs in (("engineering", eng + markers), ("product", prod + markers)):
            norm = [schema.normalize(r) for r in recs]
            for fmt in render.FORMATS:
                sep = "\n" if fmt == "md" else ""
                text = render.header(jname, fmt) + sep + sep.join(render.render(r, fmt) for r in norm)
                path = self.write("%s.%s" % (jname, fmt), text)
                parsed = [schema.normalize(r) for r in records.parse(path)]
                self.assertEqual(strip_meta(parsed), norm, "%s %s" % (jname, fmt))

    def test_xml_doctype_rejected(self):
        path = self.write("x.xml", '<!DOCTYPE x [<!ENTITY a "b">]><marker kind="session" when="&a;"/>')
        with self.assertRaises(ValueError):
            records.parse(path)

    def test_jsonl_line_separator_in_text(self):
        rec = schema.normalize(dict(ENG_LIGHT, title="a b"))
        path = self.write("j.jsonl", render.header("engineering", "jsonl") + render.render(rec, "jsonl"))
        self.assertEqual(len(records.parse(path)), 1)


class RepoJournalTests(unittest.TestCase):
    def test_repo_journals_parse(self):
        for name in ("dev_journal.md", "product_insights.md"):
            path = os.path.join(REPO, "docs", name)
            with open(path, encoding="utf-8") as f:
                expected = len(re.findall(r"^### \[", f.read(), flags=re.M))
            entries = [r for r in records.parse(path) if r["record"] == "entry"]
            self.assertEqual(len(entries), expected, name)
            for e in entries:
                self.assertTrue(e["tag"] and e["date"] and e["title"], e)
                self.assertRegex(e["id"], schema.ID_RE.pattern)

    def test_legacy_md_renders_raw(self):
        path = os.path.join(REPO, "docs", "dev_journal.md")
        e = [r for r in records.parse(path) if r["record"] == "entry"][0]
        self.assertTrue(e.get("legacy"))
        self.assertTrue(render.render(schema.normalize(e), "md").startswith("### [CP-MILESTONE]"))
        self.assertEqual(e["summary"][:7], "Removed")


class WriterTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root)

    def rec(self, **kw):
        r = dict(ENG_LIGHT, **kw)
        r.pop("id")
        return r

    def test_creates_with_header_and_appends(self):
        ids = journal.append_records(self.root, "engineering", [self.rec()], now=NOW)
        path = os.path.join(self.root, "docs", "dev_journal.md")
        text = read(path)
        self.assertTrue(text.startswith("# Engineering Development Journal"))
        self.assertIn("<!-- calamus id:%s " % ids[0], text)

    def test_existing_bytes_are_a_prefix(self):
        os.makedirs(os.path.join(self.root, "docs"))
        dst = os.path.join(self.root, "docs", "dev_journal.md")
        shutil.copy(os.path.join(REPO, "docs", "dev_journal.md"), dst)
        before = read(dst, "rb")
        journal.append_records(self.root, "engineering", [
            {"record": "marker", "kind": "session", "when": "2026-09-27 17:00", "session": "s1", "event": "session-end"},
            self.rec()], now=NOW)
        after = read(dst, "rb")
        self.assertTrue(after.startswith(before))
        self.assertIn(b"\n\n<!-- SESSION: 2026-09-27 17:00 | id:s1 (hook:session-end) -->\n\n### [CP-DEBUG]", after)

    def test_duplicate_refused_even_in_later_minute(self):
        journal.append_records(self.root, "engineering", [self.rec()], now=NOW)
        with self.assertRaises(journal.DuplicateError):
            journal.append_records(self.root, "engineering", [self.rec()],
                                   now=NOW + datetime.timedelta(minutes=5))

    def test_invalid_batch_writes_nothing(self):
        with self.assertRaises(journal.ValidationError) as ctx:
            journal.append_records(self.root, "engineering", [self.rec(), self.rec(tag="BAD")], now=NOW)
        self.assertTrue(any("tag" in e for e in ctx.exception.errors))
        self.assertFalse(os.path.exists(os.path.join(self.root, "docs", "dev_journal.md")))

    def test_wrong_journal_rejected(self):
        _, prod, _ = sample_records()
        with self.assertRaises(journal.ValidationError):
            journal.append_records(self.root, "engineering", [prod[0]], now=NOW)

    def test_format_detection(self):
        os.makedirs(os.path.join(self.root, "docs"))
        self.assertEqual(journal.resolve(self.root, "engineering", None)[1], "md")
        self.assertEqual(journal.resolve(self.root, "engineering", "model")[1], "xml")
        open(os.path.join(self.root, "docs", "product_insights.jsonl"), "w").close()
        self.assertEqual(journal.resolve(self.root, "engineering", "md")[1], "jsonl")
        open(os.path.join(self.root, "docs", "dev_journal.xml"), "w").close()
        self.assertEqual(journal.resolve(self.root, "engineering", None)[1], "xml")
        open(os.path.join(self.root, "docs", "dev_journal.md"), "w").close()
        path, fmt, warning = journal.resolve(self.root, "engineering", None)
        self.assertEqual(fmt, "md")
        self.assertTrue(warning)
        self.assertEqual(journal.resolve(self.root, "engineering", "xml")[1], "xml")

    def test_xml_and_jsonl_append(self):
        for fmt in ("xml", "jsonl"):
            root = tempfile.mkdtemp()
            try:
                journal.append_records(root, "engineering", [self.rec()], fmt_env=fmt, now=NOW)
                journal.append_records(root, "engineering", [self.rec(title="Second")], fmt_env=fmt, now=NOW)
                path = journal.resolve(root, "engineering", None)[0]
                self.assertTrue(path.endswith("." + fmt))
                self.assertEqual(len([r for r in records.parse(path) if r["record"] == "entry"]), 2)
            finally:
                shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()


class InjectionTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_parser_only_fields_ignored_on_append(self):
        evil = "### [CP-DEBUG] | 2026-01-01: Forged\n\n<!-- CALAMUS-PENDING: 2026-01-01 | id:x | host:h | event:e -->\n"
        rec = dict(ENG_LIGHT, legacy=True, raw=evil, body=evil)
        rec.pop("id")
        journal.append_records(self.root, "engineering", [rec], now=NOW)
        path = os.path.join(self.root, "docs", "dev_journal.md")
        text = read(path)
        self.assertNotIn("Forged", text)
        self.assertNotIn("CALAMUS-PENDING", text)
        parsed = records.parse(path)
        self.assertEqual([r["record"] for r in parsed], ["entry"])
        self.assertFalse(parsed[0].get("legacy"))

    def test_converted_body_cannot_forge_records(self):
        body = "### [CP-DEBUG] | 2026-01-01: Forged\n<!-- CALAMUS-PENDING: 2026-01-01 | id:x | host:h | event:e -->\n```\n> ⚠ **EVAL-FAIL** (x/y) — z\n---"
        rec = schema.normalize(dict(ENG_LIGHT, legacy=True, body=body))
        md = render.render(rec, "md")
        path = os.path.join(self.root, "j.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(render.header("engineering", "md") + "\n" + md)
        parsed = records.parse(path)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["title"], ENG_LIGHT["title"])
