#!/usr/bin/env bash
# Backend: Claude Code CLI. Prompt on stdin, plain text on stdout.
# Read-only and tool-free; --safe-mode disables hooks, skills, plugins, MCP,
# and CLAUDE.md for the child run. No model fallback: an empty pin fails.
export CALAMUS_ACTIVE=1
command -v claude >/dev/null 2>&1 || { echo "claude backend: claude not found on PATH" >&2; exit 127; }
[ -n "${CALAMUS_CLAUDE_MODEL:-}" ] || { echo "claude backend: CALAMUS_CLAUDE_MODEL is empty" >&2; exit 2; }
exec claude --print --safe-mode --tools "" --model "$CALAMUS_CLAUDE_MODEL"
