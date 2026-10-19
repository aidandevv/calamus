import json
import os
import shutil
import subprocess
import tempfile
import unittest

from helpers import LIB

EXTRACT = os.path.join(LIB, "extract.py")


def claude_lines():
    return [
        {"type": "user", "message": {"role": "user", "content": "Fix the offset bug <system-reminder>noise</system-reminder>"}},
        {"type": "assistant", "message": {"content": [
            {"type": "thinking", "thinking": "SECRET-THOUGHT", "signature": "SIG"},
            {"type": "text", "text": "Looking at hook.sh"},
            {"type": "tool_use", "name": "Bash", "input": {"command": "x" * 500}},
        ]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "content": "R" * 1000 + "TAIL-OF-RESULT"}]}},
        {"type": "user", "isMeta": True, "message": {"content": "META-TEXT"}},
        {"type": "assistant", "isSidechain": True, "message": {"content": [{"type": "text", "text": "SIDECHAIN"}]}},
        {"type": "attachment", "attachment": {"content": "ATTACHMENT"}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": [
            {"type": "text", "text": "12 passed"}, {"type": "image", "source": "BINARY"}]}]}},
    ]


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, lines, name="t.jsonl"):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            for l in lines:
                f.write((l if isinstance(l, str) else json.dumps(l)) + "\n")
        return path

    def run_x(self, host, path, start=0, window=1 << 20, cap=0):
        out = subprocess.run(["python3", EXTRACT, host, path, str(start), str(window), str(cap)],
                             capture_output=True, text=True, check=True).stdout
        return json.loads(out)

    def test_claude_keeps_and_drops(self):
        path = self.write(claude_lines())
        res = self.run_x("claude-code", path)
        text = res["text"]
        self.assertEqual(res["eof"], os.path.getsize(path))
        self.assertIn("USER: Fix the offset bug", text)
        self.assertIn("ASSISTANT: Looking at hook.sh", text)
        self.assertIn("[tool] Bash: ", text)
        self.assertIn("[result] 12 passed", text)
        for gone in ("SECRET-THOUGHT", "SIG", "noise", "META-TEXT", "SIDECHAIN", "ATTACHMENT", "BINARY", "TAIL-OF-RESULT"):
            self.assertNotIn(gone, text)
        tool_line = [l for l in text.split("\n") if l.startswith("[tool]")][0]
        self.assertLessEqual(len(tool_line), len("[tool] Bash: ") + 120)
        result_line = [l for l in text.split("\n") if l.startswith("[result] R")][0]
        self.assertEqual(len(result_line), len("[result] ") + 200)

    def test_partial_leading_line_dropped(self):
        path = self.write([{"type": "user", "message": {"content": "FIRST"}},
                           {"type": "user", "message": {"content": "SECOND"}}])
        res = self.run_x("claude-code", path, start=5)
        self.assertNotIn("FIRST", res["text"])
        self.assertIn("SECOND", res["text"])
        with open(path, "rb") as f:
            first_len = len(f.readline())
        res = self.run_x("claude-code", path, start=first_len)
        self.assertEqual(res["text"], "USER: SECOND")

    def test_raw_window_and_cap(self):
        path = self.write([{"type": "user", "message": {"content": "OLD" * 100}},
                           {"type": "user", "message": {"content": "NEW"}}])
        res = self.run_x("claude-code", path, window=60)
        self.assertEqual(res["text"], "USER: NEW")
        res = self.run_x("claude-code", path, cap=5)
        self.assertEqual(res["text"], ": NEW")

    def test_start_past_eof_resets(self):
        path = self.write([{"type": "user", "message": {"content": "ONLY"}}])
        self.assertIn("ONLY", self.run_x("claude-code", path, start=10 ** 9)["text"])

    def test_generic_harvester(self):
        path = self.write([
            {"payload": {"role": "assistant", "content": [{"type": "output_text", "text": "Did X"}],
                         "reasoning": {"text": "HIDDEN"}, "encrypted_content": "ENC"}},
            {"role": "user", "message": "Please do Y", "id": 7},
            "plain log line",
            {"meta": {"model": "m"}},
        ])
        text = self.run_x("codex", path)["text"]
        self.assertEqual(text, "ASSISTANT: Did X\nUSER: Please do Y\nplain log line")


if __name__ == "__main__":
    unittest.main()
