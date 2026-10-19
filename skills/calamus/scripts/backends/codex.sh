#!/usr/bin/env bash
# Backend: Codex CLI. Prompt on stdin, final agent message on stdout.
# `codex exec` has no quiet mode; -o writes only the final message to a file.
export CALAMUS_ACTIVE=1
bin="$(command -v codex 2>/dev/null || true)"
[ -n "$bin" ] || bin="${CALAMUS_CODEX_BIN:-}"
[ -n "$bin" ] || bin="/Applications/Codex.app/Contents/Resources/codex"
[ -x "$bin" ] || { echo "codex backend: codex binary not found" >&2; exit 127; }
[ -n "${CALAMUS_CODEX_MODEL:-}" ] || { echo "codex backend: CALAMUS_CODEX_MODEL is empty" >&2; exit 2; }
out="$(mktemp "${TMPDIR:-/tmp}/calamus-codex.XXXXXX")" || exit 1
trap 'rm -f "$out"' EXIT
"$bin" exec --sandbox read-only --skip-git-repo-check \
  -c model_reasoning_effort=low --model "$CALAMUS_CODEX_MODEL" -o "$out" >/dev/null 2>&1 || exit 1
[ -s "$out" ] || exit 1
cat "$out"
