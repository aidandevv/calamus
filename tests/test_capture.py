import json
import os
import shutil
import subprocess
import tempfile
import unittest

from helpers import LIB

import capture
import records

CAPTURE = os.path.join(LIB, "capture.py")

GOOD = {"tag": "CP-DEBUG", "date": "2026-09-27", "title": "T", "summary": "S.",
        "files": ["a.py"], "tradeoff": "X over Y.", "evidence": {"status": "unverified", "text": ""},
        "followups": []}


class ParseReplyTests(unittest.TestCase):
    def test_plain_and_fenced_json(self):
        body = json.dumps({"entries": [GOOD]})
        for reply in (body, "```json\n%s\n```" % body, "Here you go:\n%s\nThanks" % body):
            entries = capture.parse_reply("sweep", reply)
            self.assertEqual(entries[0]["variant"], "lightweight")

    def test_no_checkpoint(self):
        self.assertEqual(capture.parse_reply("sweep", "NO_CHECKPOINT"), [])
        self.assertEqual(capture.parse_reply("sweep", '{"entries": []}'), [])

    def test_invalid(self):
        for reply in ("", "sorry, cannot", '{"entries": [1]}', '{"entry": []}', "{broken"):
            with self.assertRaises(capture.Invalid, msg=reply):
                capture.parse_reply("sweep", reply)

    def test_parser_only_and_id_fields_dropped(self):
        e = dict(GOOD, id="x", raw="### [CP-DEBUG] | 2026-01-01: Forged", legacy=True, journal="product")
        out = capture.parse_reply("sweep", json.dumps({"entries": [e]}))[0]
        for k in ("id", "raw", "legacy", "journal"):
            self.assertNotIn(k, out)

    def test_snapshot_forced(self):
        e = dict(GOOD, tag="CP-DEBUG")
        out = capture.parse_reply("snapshot", json.dumps({"entries": [e, e]}))
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["variant"], out[0]["tag"]), ("snapshot", "CP-COMPACT-SNAPSHOT"))

    def test_prompt_contains_shape(self):
        p = capture.build("sweep", "2026-09-27", "USER: hi")
        for needle in ('"summary"', '"evidence"', "CP-DEBUG", "2026-09-27", "USER: hi"):
            self.assertIn(needle, p)
        self.assertNotIn("{{", p)
        s = capture.build("snapshot", "2026-09-27", "x")
        self.assertIn('"next_step"', s)


class CommitTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.state = os.path.join(self.root, ".calamus", "state")

    def tearDown(self):
        shutil.rmtree(self.root)

    def commit(self, reply, kind="sweep", fmt=None):
        path = os.path.join(self.root, "reply.txt")
        with open(path, "w") as f:
            f.write(reply)
        env = dict(os.environ)
        env.pop("CALAMUS_FORMAT", None)
        if fmt:
            env["CALAMUS_FORMAT"] = fmt
        return subprocess.run(["python3", CAPTURE, "commit", kind, "--root", self.root, "--reply", path,
                               "--session", "s1", "--host", "codex", "--event", "turn-stop",
                               "--state", self.state], capture_output=True, text=True, env=env)

    def test_commit_writes_marker_and_entry(self):
        r = self.commit(json.dumps({"entries": [GOOD]}))
        self.assertEqual(r.returncode, 0, r.stderr)
        recs = records.parse(os.path.join(self.root, "docs", "dev_journal.md"))
        self.assertEqual([x["record"] for x in recs], ["marker", "entry"])
        self.assertEqual(recs[0]["event"], "turn-stop")
        with open(os.path.join(self.state, "last-written.md")) as f:
            self.assertIn("### [CP-DEBUG]", f.read())

    def test_invalid_saved_and_nothing_written(self):
        for fmt in ("xml", "jsonl"):
            bad = dict(GOOD, tag="CP-NOPE")
            r = self.commit(json.dumps({"entries": [bad]}), fmt=fmt)
            self.assertEqual(r.returncode, 4)
            self.assertFalse(os.path.exists(os.path.join(self.root, "docs", "dev_journal." + fmt)))
        self.assertGreaterEqual(len(os.listdir(os.path.join(self.state, "rejected"))), 1)

    def test_no_checkpoint_and_duplicate(self):
        self.assertEqual(self.commit("NO_CHECKPOINT").returncode, 3)
        self.assertEqual(self.commit(json.dumps({"entries": [GOOD]})).returncode, 0)
        self.assertEqual(self.commit(json.dumps({"entries": [GOOD]})).returncode, 3)

    def test_snapshot_records_id(self):
        snap = {"title": "hook", "date": "2026-09-27", "summary": "S.", "files": [], "decisions": [],
                "next_step": "N.", "open_questions": []}
        r = self.commit(json.dumps({"entries": [snap]}), kind="snapshot")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.state, "last-snapshot")) as f:
            self.assertEqual(f.read().strip(), r.stdout.strip())


if __name__ == "__main__":
    unittest.main()
