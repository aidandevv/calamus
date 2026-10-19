#!/usr/bin/env python3
"""Distill a transcript window into plain text.

Usage: extract.py <host> <path> <start> <raw-window> <cap>

Reads from max(start, eof - raw-window) to eof, drops a partial leading
line, and prints {"eof": <offset>, "text": "<extracted>"}. Output lines:
  USER: <text> | ASSISTANT: <text> | [tool] <name>: <args> | [result] <start>
"""
import json
import os
import re
import sys

TOOL_ARGS = 120
RESULT_HEAD = 200
HARVEST = {"text", "content", "message", "output"}
SKIP = {"thinking", "reasoning", "encrypted_content", "signature", "redacted_thinking"}
REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def squash(text):
    return re.sub(r"\s+", " ", REMINDER_RE.sub(" ", text)).strip()


def read_window(path, start, window):
    eof = os.path.getsize(path)
    if start > eof:
        start = 0
    begin = max(start, eof - window, 0)
    with open(path, "rb") as f:
        partial = False
        if begin > 0:
            f.seek(begin - 1)
            partial = f.read(1) != b"\n"
        data = f.read(eof - begin)
    if partial:
        cut = data.find(b"\n")
        data = b"" if cut < 0 else data[cut + 1:]
    return eof, data.decode("utf-8", errors="replace")


def _result_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def claude_items(rec):
    if not isinstance(rec, dict) or rec.get("type") not in ("user", "assistant"):
        return []
    if rec.get("isMeta") or rec.get("isSidechain"):
        return []
    who = "USER" if rec["type"] == "user" else "ASSISTANT"
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        text = squash(content)
        return ["%s: %s" % (who, text)] if text else []
    items = []
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            text = squash(block.get("text", ""))
            if text:
                items.append("%s: %s" % (who, text))
        elif kind == "tool_use":
            args = json.dumps(block.get("input", {}), ensure_ascii=False)
            items.append("[tool] %s: %s" % (block.get("name", "?"), squash(args)[:TOOL_ARGS]))
        elif kind == "tool_result":
            head = squash(_result_text(block.get("content")))[:RESULT_HEAD]
            if head:
                items.append("[result] %s" % head)
    return items


def _harvest(node, key, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k not in SKIP:
                _harvest(v, k, out)
    elif isinstance(node, list):
        for v in node:
            _harvest(v, key, out)
    elif isinstance(node, str) and key in HARVEST:
        text = squash(node)
        if text:
            out.append(text)


def _role(node):
    if isinstance(node, dict):
        if node.get("role") in ("user", "assistant"):
            return node["role"]
        for k, v in node.items():
            if k not in SKIP:
                r = _role(v)
                if r:
                    return r
    elif isinstance(node, list):
        for v in node:
            r = _role(v)
            if r:
                return r
    return ""


def generic_items(rec):
    parts = []
    _harvest(rec, "", parts)
    if not parts:
        return []
    role = _role(rec)
    prefix = "%s: " % role.upper() if role else ""
    return [prefix + " ".join(parts)]


def extract(host, text):
    items = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            if host != "claude-code":
                items.append(squash(line))
            continue
        items += claude_items(rec) if host == "claude-code" else generic_items(rec)
    return "\n".join(i for i in items if i)


def main(argv):
    host, path, start, window, cap = argv[0], argv[1], int(argv[2]), int(argv[3]), int(argv[4])
    eof, raw = read_window(path, start, window)
    text = extract(host, raw)
    if cap > 0 and len(text) > cap:
        text = text[-cap:]
    sys.stdout.write(json.dumps({"eof": eof, "text": text}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
