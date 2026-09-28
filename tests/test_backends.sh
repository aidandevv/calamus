#!/usr/bin/env bash
# Backend contract: stdin prompt, stdout text, CALAMUS_ACTIVE exported, no fallback.
. "$(dirname "$0")/lib.sh"
B="$SKILL_DIR/scripts/backends"
R="$(mk_repo)"

out="$(echo "PROMPT" | env CALAMUS_LLM_CMD='printf "%s|" "$CALAMUS_ACTIVE"; cat' "$B/generic.sh")"
assert_eq "1|PROMPT" "$out" "generic: prompt on stdin, CALAMUS_ACTIVE=1"
echo x | env -u CALAMUS_LLM_CMD "$B/generic.sh" 2>/dev/null; assert_eq 127 "$?" "generic: empty command"

# PATH without claude/codex: binaries missing → 127, never another backend.
mkdir -p "$R/bin"; ln -s "$(command -v python3)" "$R/bin/python3"
echo x | env PATH="$R/bin:/usr/bin:/bin" CALAMUS_CLAUDE_MODEL=m "$B/claude.sh" 2>/dev/null
assert_eq 127 "$?" "claude: missing binary"
echo x | env PATH="$R/bin:/usr/bin:/bin" CALAMUS_CODEX_BIN="$R/nope" CALAMUS_CODEX_MODEL=m "$B/codex.sh" 2>/dev/null
rc=$?
if [ -x /Applications/Codex.app/Contents/Resources/codex ]; then :; else assert_eq 127 "$rc" "codex: missing binary"; fi

# Empty model pin fails instead of using a CLI default.
printf '#!/bin/sh\necho SHOULD-NOT-RUN\n' > "$R/bin/claude"; chmod +x "$R/bin/claude"
out="$(echo x | env PATH="$R/bin:/usr/bin:/bin" CALAMUS_CLAUDE_MODEL= "$B/claude.sh" 2>/dev/null)"; rc=$?
assert_eq "2:" "$rc:$out" "claude: empty model pin"

# Fake claude receives the pinned model and the safety flags.
printf '#!/bin/sh\necho "$@"; cat\n' > "$R/bin/claude"
out="$(echo PROMPT | env PATH="$R/bin:/usr/bin:/bin" CALAMUS_CLAUDE_MODEL=pinned "$B/claude.sh")"
assert_contains "$out" "--print --safe-mode --tools  --model pinned" "claude flags"
assert_contains "$out" "PROMPT" "claude stdin"

# Fake codex writes the final message to -o.
printf '#!/bin/sh\nwhile [ $# -gt 0 ]; do [ "$1" = -o ] && o="$2"; shift; done\ncat > "$o"\n' > "$R/bin/codex"; chmod +x "$R/bin/codex"
out="$(echo REPLY | env PATH="$R/bin:/usr/bin:/bin" CALAMUS_CODEX_MODEL=m "$B/codex.sh")"
assert_eq "REPLY" "$out" "codex: output from -o file"

echo x | "$B/cursor.sh" 2>/dev/null; assert_eq 2 "$?" "cursor: unverified stub fails"

finish
