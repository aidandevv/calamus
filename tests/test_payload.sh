#!/usr/bin/env bash
# Payload normalization per host.
. "$(dirname "$0")/lib.sh"

norm() { # host payload [env...]
  local host="$1" payload="$2"; shift 2
  printf '%s' "$payload" | env "$@" /bin/bash -c \
    ". '$SKILL_DIR/scripts/lib/payload.sh'; calamus_payload '$host'; printf '%s|%s|%s' \"\$CAL_SESSION\" \"\$CAL_CWD\" \"\$CAL_TRANSCRIPT\""
}

assert_eq "s1|/p|/t.jsonl" "$(norm claude-code '{"session_id":"s1","cwd":"/p","transcript_path":"/t.jsonl"}')" "claude-code"
assert_eq "c9|/p|" "$(norm claude-code '{"conversation_id":"c9","cwd":"/p"}')" "claude-code conversation_id fallback"
assert_eq "s1|/p|" "$(norm codex '{"session_id":"s1","cwd":"/p","transcript_path":null}')" "codex null transcript"
assert_eq "cv|/w1|/t" "$(norm cursor '{"conversation_id":"cv","session_id":"x","workspace_roots":["/w1","/w2"],"transcript_path":"/t"}')" "cursor"
assert_eq "x|/env-dir|/env-t" "$(norm cursor '{"session_id":"x"}' CURSOR_PROJECT_DIR=/env-dir CURSOR_TRANSCRIPT_PATH=/env-t)" "cursor env fallback"
assert_eq "g|/c|/t" "$(norm generic '' CALAMUS_SESSION_ID=g CALAMUS_CWD=/c CALAMUS_TRANSCRIPT=/t)" "generic env"
assert_eq "j|/c|/t" "$(norm generic '{"session_id":"j","cwd":"/c","transcript_path":"/t"}' CALAMUS_SESSION_ID=g)" "generic json wins"
assert_eq "unknown||" "$(norm claude-code 'not json {')" "malformed json"
assert_eq "unknown||" "$(norm claude-code '')" "empty stdin"
assert_eq "unknown||" "$(norm claude-code '[1,2]')" "non-object json"
assert_eq "..-..-etc-passwd|/p|" "$(norm codex '{"session_id":"../../etc/passwd","cwd":"/p"}')" "session sanitized"
long="$(printf 'a%.0s' $(seq 1 100))"
assert_eq 64 "$(norm codex "{\"session_id\":\"$long\"}" | cut -d'|' -f1 | tr -d '\n' | wc -c | tr -d ' ')" "session capped at 64"

finish
