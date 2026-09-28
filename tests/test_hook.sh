#!/usr/bin/env bash
# Hook engine: every host × event, gates, failure paths, Level 1, no stdout.
. "$(dirname "$0")/lib.sh"
HOOK="$SKILL_DIR/scripts/hook.sh"

SWEEP='{"entries":[{"tag":"CP-DEBUG","date":"2026-09-27","title":"Entry __N__","summary":"S.","files":["a.py"],"tradeoff":"T.","evidence":{"status":"unverified","text":""},"followups":[]}]}'
SNAP='{"entries":[{"date":"2026-09-27","title":"snap __N__","summary":"S.","files":[],"decisions":[],"next_step":"N.","open_questions":[]}]}'

# new_env: fresh repo, transcript, and fake backend. Sets R, T, F.
new_env() {
  R="$(mk_repo)"; T="$R/transcript.jsonl"; F="$R/fake"
  mkdir -p "$F/calls" "$R/home"
  printf '%s' "$SWEEP" > "$F/reply"; printf '%s' "$SNAP" > "$F/snap"
  printf 'YES\nFine.\n' > "$F/judge"; echo 0 > "$F/exit"; echo 0 > "$F/judge-exit"
  cat > "$F/backend.sh" <<'EOF'
#!/bin/sh
n=$(( $(ls "$FAKE/calls" | wc -l) + 1 ))
cat > "$FAKE/calls/$n.txt"
[ -f "$FAKE/sleep" ] && sleep "$(cat "$FAKE/sleep")"
if grep -q "quality gate for an engineering journal" "$FAKE/calls/$n.txt"; then
  cat "$FAKE/judge"; exit "$(cat "$FAKE/judge-exit")"
fi
if grep -q "context compaction is about to occur" "$FAKE/calls/$n.txt"; then
  sed "s/__N__/$n/" "$FAKE/snap"
else
  sed "s/__N__/$n/" "$FAKE/reply"
fi
exit "$(cat "$FAKE/exit")"
EOF
  chmod +x "$F/backend.sh"
  : > "$T"
  add_turns 5
}

# add_turns N — appends N user/assistant pairs (~300 extracted chars each).
add_turns() {
  local i
  for i in $(seq 1 "$1"); do
    printf '{"type":"user","message":{"content":"Question %s-%s: please adjust the offset handling in the hook engine and explain the trade-off in detail."}}\n' "$RANDOM" "$i" >> "$T"
    printf '{"type":"assistant","message":{"content":[{"type":"text","text":"Answer %s-%s: changed hook.sh so the offset only advances after a verdict, keeping retries safe."}]}}\n' "$RANDOM" "$i" >> "$T"
  done
}

payload() { printf '{"session_id":"%s","conversation_id":"%s","cwd":"%s","workspace_roots":["%s"],"transcript_path":"%s"}' \
  "${2:-s1}" "${2:-s1}" "$R" "$R" "${1:-$T}"; }

# run_hook host event [VAR=value...] — payload from $PAYLOAD or default. Sets OUT and RC.
run_hook() {
  local host="$1" event="$2"; shift 2
  OUT="$( (printf '%s' "${PAYLOAD:-$(payload)}" | env -i PATH="$PATH" HOME="$R/home" XDG_CONFIG_HOME="$R/home/.config" \
    TMPDIR="${TMPDIR:-/tmp}" FAKE="$F" CALAMUS_BACKEND=generic CALAMUS_LLM_CMD="$F/backend.sh" \
    CALAMUS_DEDUPE_SECS=0 CALAMUS_LEVEL1_GATE=off CALAMUS_MIN_TEXT=100 "$@" \
    bash "$HOOK" --host "$host" --event "$event") 2>&1)"
  RC=$?
}

J() { cat "$R/docs/dev_journal.md" 2>/dev/null; }
calls() { ls "$F/calls" | wc -l | tr -d ' '; }
check_quiet() { assert_eq "0|" "$RC|$OUT" "$1: exit 0 and no output"; }

# ── Every host × event ───────────────────────────────────────────────────────
for host in claude-code codex cursor generic; do
  new_env
  run_hook "$host" pre-compact; check_quiet "$host pre-compact"
  assert_contains "$(J)" "<!-- COMPACT: " "$host pre-compact marker"
  assert_contains "$(J)" "### [CP-COMPACT-SNAPSHOT] | 2026-09-27: Pre-compaction state — snap 1" "$host snapshot entry"
  run_hook "$host" post-compact; check_quiet "$host post-compact"
  snap_id="$(cat "$R/.calamus/state/last-snapshot")"
  assert_contains "$(J)" "<!-- POST-COMPACT RESUME: " "$host resume marker"
  assert_contains "$(J)" "| snapshot:$snap_id -->" "$host resume carries snapshot id"
  run_hook "$host" turn-stop; check_quiet "$host turn-stop"
  assert_contains "$(J)" "(hook:turn-stop) -->" "$host turn-stop marker"
  add_turns 5
  run_hook "$host" session-end; check_quiet "$host session-end"
  case "$host" in
    codex|cursor) assert_contains "$(J)" "<!-- CALAMUS-PENDING: " "$host session-end stub" ;;
    *) assert_contains "$(J)" "(hook:session-end) -->" "$host session-end sweep" ;;
  esac
  assert_not_contains "$(J)" "$R" "$host journal has no absolute path"
done

# ── No checkpoint: nothing written, offset advances ─────────────────────────
new_env; echo NO_CHECKPOINT > "$F/reply"
run_hook codex turn-stop; check_quiet "no checkpoint"
assert_file_absent "$R/docs/dev_journal.md" "no checkpoint writes nothing"
assert_eq "$(wc -c < "$T" | tr -d ' ')" "$(cat "$R/.calamus/state/offset-s1")" "offset advanced on no checkpoint"

# ── Incremental window: second sweep sends only new text ────────────────────
new_env
run_hook codex turn-stop
first_q="$(grep -o 'Question [0-9]*-1' "$F/calls/1.txt" | head -1)"
add_turns 3
run_hook codex turn-stop
assert_eq 2 "$(calls)" "two sweeps"
assert_not_contains "$(cat "$F/calls/2.txt")" "$first_q" "second sweep has no overlap"
assert_eq 3 "$(grep -c '^Question ' "$F/calls/2.txt")" "second sweep has only new turns"

# ── Skips: missing, tiny, null transcript; small growth; empty/malformed stdin
new_env; PAYLOAD="$(payload "$R/missing.jsonl")" run_hook claude-code session-end; check_quiet "missing transcript"
assert_eq 0 "$(calls)" "missing transcript: no call"
printf 'x\n' > "$R/tiny.jsonl"; PAYLOAD="$(payload "$R/tiny.jsonl")" run_hook claude-code session-end
assert_eq 0 "$(calls)" "tiny transcript: no call"
PAYLOAD="{\"session_id\":\"s1\",\"cwd\":\"$R\",\"transcript_path\":null}" run_hook codex turn-stop
assert_eq 0 "$(calls)" "null transcript: no call"
run_hook codex turn-stop CALAMUS_MIN_TEXT=8000; check_quiet "small growth"
assert_eq 0 "$(calls)" "small turn-stop growth skipped"
assert_contains "$(cat "$R/.calamus/logs/hook.log")" "below 8000" "small growth logged"
PAYLOAD=" " run_hook claude-code session-end; check_quiet "empty stdin"
PAYLOAD="{not json" run_hook claude-code pre-compact; check_quiet "malformed json"
run_hook claude-code session-end; check_quiet "bogus flags baseline"
OUT="$(printf '%s' "$(payload)" | bash "$HOOK" --host nope --event session-end 2>&1)"; assert_eq "0|" "$?|$OUT" "unknown host"

# ── Short claude-code session-end still captures (no MIN_TEXT at session end)
new_env; : > "$T"; add_turns 3
run_hook claude-code session-end CALAMUS_MIN_TEXT=8000
assert_contains "$(J)" "### [CP-DEBUG]" "short session-end sweep captures"

# ── Backend failure and hang: pending stub, offset unchanged ─────────────────
new_env; echo 1 > "$F/exit"
run_hook claude-code session-end; check_quiet "failing backend"
assert_contains "$(J)" "<!-- CALAMUS-PENDING: " "failing backend: pending marker"
assert_eq "$T" "$(cat "$R/.calamus/state/pending/s1")" "pending state holds transcript path"
assert_file_absent "$R/.calamus/state/offset-s1" "offset unchanged on failure"
assert_not_contains "$(J)" "$R" "pending marker has no absolute path"
new_env; echo 1 > "$F/exit"
run_hook codex turn-stop
assert_file_absent "$R/docs/dev_journal.md" "turn-stop failure: log only"
new_env; echo 10 > "$F/sleep"
start=$(date +%s); run_hook codex pre-compact CALAMUS_BACKEND_TIMEOUT=1; elapsed=$(( $(date +%s) - start ))
check_quiet "hanging backend"
assert_contains "$(J)" "<!-- CALAMUS-PENDING: " "hanging backend: pending marker"
[ "$elapsed" -lt 8 ] || _fail "hanging backend took ${elapsed}s"
new_env; run_hook generic session-end CALAMUS_BACKEND=auto CALAMUS_LLM_CMD=
assert_contains "$(J)" "<!-- CALAMUS-PENDING: " "generic auto without LLM_CMD: pending"
new_env; run_hook generic session-end CALAMUS_BACKEND=auto
assert_contains "$(J)" "### [CP-DEBUG]" "generic auto with LLM_CMD: captured"
new_env; PAYLOAD=" " run_hook generic turn-stop CALAMUS_SESSION_ID=envsess CALAMUS_CWD="$R" CALAMUS_TRANSCRIPT="$T"
assert_contains "$(J)" "id:envsess (hook:turn-stop)" "generic payload from env vars"

# ── Invalid reply: rejected payload saved, nothing appended (xml, jsonl) ─────
for fmt in xml jsonl; do
  new_env; (cd "$R" && "$SKILL_DIR/scripts/calamus-init" --format "$fmt" >/dev/null)
  before="$(shasum < "$R/docs/dev_journal.$fmt")"
  echo '{"entries":[{"tag":"CP-NOPE"}]}' > "$F/reply"
  run_hook codex turn-stop; check_quiet "invalid reply $fmt"
  assert_eq "$before" "$(shasum < "$R/docs/dev_journal.$fmt")" "invalid reply appends nothing ($fmt)"
  assert_eq 1 "$(ls "$R/.calamus/state/rejected" | wc -l | tr -d ' ')" "rejected payload saved ($fmt)"
done

# ── Guards: recursion, dedupe across hosts, held lock, read-only docs ────────
new_env; run_hook claude-code session-end CALAMUS_ACTIVE=1
assert_file_absent "$R/.calamus" "CALAMUS_ACTIVE=1 is a no-op"
new_env
run_hook claude-code pre-compact CALAMUS_DEDUPE_SECS=30
run_hook cursor pre-compact CALAMUS_DEDUPE_SECS=30
assert_eq 1 "$(J | grep -c '<!-- COMPACT: ')" "same session under two hosts captured once"
new_env; mkdir -p "$R/.calamus/state/lock-s1"
run_hook claude-code session-end; check_quiet "held lock"
assert_eq 0 "$(calls)" "held lock skips"
new_env; mkdir -p "$R/docs"; chmod 555 "$R/docs"
run_hook claude-code session-end; check_quiet "read-only docs"
chmod 755 "$R/docs"

# ── Level 1 gate ─────────────────────────────────────────────────────────────
new_env; printf 'NO\nMissing why.\n' > "$F/judge"
run_hook claude-code session-end CALAMUS_LEVEL1_GATE=full
assert_contains "$(J)" "> ⚠ **EVAL-FAIL** (generic/custom) — Missing why." "NO appends eval-fail"
new_env; echo 1 > "$F/judge-exit"
run_hook claude-code session-end CALAMUS_LEVEL1_GATE=full
assert_not_contains "$(J)" "EVAL-FAIL" "failed judge appends nothing"
assert_contains "$(cat "$R/.calamus/logs/hook.log")" "unjudged (judge call failed)" "failed judge is unjudged"
new_env; printf 'MAYBE\n' > "$F/judge"
run_hook claude-code session-end CALAMUS_LEVEL1_GATE=full
assert_contains "$(cat "$R/.calamus/logs/hook.log")" "unjudged (unparseable verdict)" "unparseable verdict"
assert_not_contains "$(J)" "EVAL-FAIL" "unparseable verdict appends nothing"
new_env
for i in 1 2 3 4; do add_turns 2; run_hook codex turn-stop CALAMUS_LEVEL1_GATE=sampled CALAMUS_LEVEL1_SAMPLE=4; done
assert_eq 1 "$(grep -l 'quality gate for an engineering journal' "$F"/calls/* | wc -l | tr -d ' ')" "sampled: 1 judge call in 4 captures"
new_env; run_hook claude-code pre-compact CALAMUS_LEVEL1_GATE=full
assert_eq 1 "$(calls)" "pre-compact never calls the judge"

# ── Extraction fallback: empty extraction or EXTRACT=off sends the raw tail ──
new_env; : > "$T"
for i in 1 2 3 4 5 6; do
  printf '{"type":"assistant","message":{"content":[{"type":"thinking","thinking":"RAWMARK only reasoning here, nothing extractable at all in this line %s"}]}}\n' "$i" >> "$T"
done
run_hook claude-code session-end
assert_contains "$(cat "$F/calls/1.txt")" "RAWMARK" "empty extraction falls back to raw tail"
assert_contains "$(cat "$R/.calamus/logs/hook.log")" "extract-fallback" "fallback logged"
new_env; run_hook claude-code session-end CALAMUS_EXTRACT=off
assert_contains "$(cat "$F/calls/1.txt")" '{"type":"user"' "EXTRACT=off sends raw transcript"

finish
