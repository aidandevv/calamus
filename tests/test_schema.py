import json
import os
import unittest
import xml.etree.ElementTree as ET

from helpers import ENG_LIGHT, FIXTURES, HOSTILE, sample_records

import render
import schema


class SchemaTests(unittest.TestCase):
    def all_records(self):
        eng, prod, markers = sample_records()
        return eng + prod + markers

    def test_samples_validate(self):
        for rec in self.all_records():
            self.assertEqual(schema.validate(schema.normalize(rec)), [], rec.get("variant", rec.get("kind")))

    def test_md_golden_lightweight(self):
        with open(os.path.join(FIXTURES, "golden", "eng-lightweight.md"), encoding="utf-8") as f:
            golden = f.read()
        self.assertEqual(render.render(schema.normalize(ENG_LIGHT), "md"), golden)

    def test_missing_required_field(self):
        rec = dict(ENG_LIGHT)
        del rec["summary"]
        errs = schema.validate(schema.normalize(rec))
        self.assertTrue(any("summary" in e for e in errs), errs)

    def test_bad_tag_and_enum(self):
        rec = dict(ENG_LIGHT, tag="CP-NOPE")
        self.assertTrue(any("tag" in e for e in schema.validate(schema.normalize(rec))))
        _, prod, _ = sample_records()
        bad = dict(prod[0], evidence={"source": "x", "strength": "Maybe"})
        self.assertTrue(any("strength" in e for e in schema.validate(schema.normalize(bad))))

    def test_snapshot_tag_fixed(self):
        eng, _, _ = sample_records()
        bad = dict(eng[2], tag="CP-DEBUG")
        self.assertTrue(schema.validate(schema.normalize(bad)))

    def test_inline_list_separator_rejected(self):
        rec = dict(ENG_LIGHT, files=["a`b"], followups=["x; y"])
        errs = schema.validate(schema.normalize(rec))
        self.assertTrue(any("files" in e for e in errs), errs)
        self.assertTrue(any("followups" in e for e in errs), errs)

    def test_bad_id_and_date(self):
        errs = schema.validate(schema.normalize(dict(ENG_LIGHT, id="x", date="27/09/2026")))
        self.assertTrue(any("id" in e for e in errs) and any("date" in e for e in errs), errs)

    def test_normalize_collapses_whitespace(self):
        rec = schema.normalize(dict(ENG_LIGHT, title="  a\r\n  b\tc  ", followups=[" x\n y "]))
        self.assertEqual(rec["title"], "a b c")
        self.assertEqual(rec["followups"], ["x y"])

    def test_normalize_fills_missing_fields(self):
        rec = dict(ENG_LIGHT)
        del rec["followups"]
        self.assertEqual(schema.normalize(rec)["followups"], [])

    def test_xml_parses_and_escapes(self):
        body = "".join(render.render(schema.normalize(r), "xml") for r in self.all_records())
        root = ET.fromstring("<j>" + body + "</j>")
        self.assertEqual(len(root), len(self.all_records()))
        self.assertIn(HOSTILE, ET.tostring(root, encoding="unicode").replace("&lt;", "<").replace("&amp;", "&").replace("&gt;", ">").replace("&quot;", '"'))

    def test_jsonl_lines_parse(self):
        for r in self.all_records():
            out = render.render(schema.normalize(r), "jsonl")
            self.assertTrue(out.endswith("\n"))
            self.assertEqual(out.count("\n"), 1)
            json.loads(out)

    def test_md_comment_never_closed_early(self):
        for r in self.all_records():
            md = render.render(schema.normalize(r), "md")
            for line in md.splitlines():
                if line.startswith("<!--"):
                    self.assertEqual(line.count("-->"), 1, line)
                    self.assertTrue(line.endswith("-->"), line)

    def test_content_hash_ignores_id(self):
        a = schema.normalize(ENG_LIGHT)
        b = dict(a, id="20990101-0000-ffff")
        self.assertEqual(schema.content_hash(a), schema.content_hash(b))
        self.assertNotEqual(schema.content_hash(a), schema.content_hash(dict(a, title="other")))

    def test_make_id(self):
        import datetime
        rid = schema.make_id(schema.normalize(ENG_LIGHT), datetime.datetime(2026, 9, 27, 16, 30))
        self.assertRegex(rid, r"^20260927-1630-[0-9a-f]{4}$")
        self.assertEqual(rid[-4:], schema.content_hash(schema.normalize(ENG_LIGHT))[:4])

    def test_headers(self):
        self.assertTrue(render.header("engineering", "md").startswith("# Engineering Development Journal\n"))
        json.loads(render.header("product", "jsonl"))
        self.assertTrue(render.header("engineering", "xml").startswith("<!--"))


if __name__ == "__main__":
    unittest.main()
