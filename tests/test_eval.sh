#!/usr/bin/env bash
# Level 2 scorer: backend routing, report header, rubric location, failures.
. "$(dirname "$0")/lib.sh"
EV="$SKILL_DIR/evals/eval-score.sh"
S="$SKILL_DIR/scripts"

entry() { printf '{"variant":"lightweight","tag":"CP-DEBUG","date":"2026-09-27","title":"%s","summary":"S.","files":["a.py"],"tradeoff":"T.","evidence":{"status":"verified","text":"ok"},"followups":[]}' "$1"; }
SCORES='[{"entry_title":"### [CP-DEBUG] | 2026-09-27: One","scores":{"decision_specificity":3,"reasoning_quality":2,"evidence_verification":3,"scope_identification":2,"followup_signal":1},"average":2.2,"pass":true,"notes":"n"}]'

R="$(mk_repo)"
(cd "$R" && "$S/calamus-init" --format xml >/dev/null && printf '[%s,%s]' "$(entry One)" "$(entry Two)" | "$S/calamus-append" --journal engineering >/dev/null)
mkdir -p "$R/evals"; echo "DECOY RUBRIC" > "$R/evals/rubric.md"
printf '%s' "$SCORES" > "$R/scores.json"

run_eval() { # extra env..., then args after --
  local envs=()
  while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  (cd "$R" && env -i PATH="$PATH" HOME="$R/home" XDG_CONFIG_HOME="$R/home/.config" TMPDIR="${TMPDIR:-/tmp}" \
    CALAMUS_EVAL_BACKEND=generic "${envs[@]}" bash "$EV" "$@")
}

out="$(run_eval CALAMUS_LLM_CMD="cat > '$R/prompt.txt'; cat '$R/scores.json'" -- 1 2>&1)"; rc=$?
assert_eq 0 "$rc" "scorer succeeds with fake judge"
assert_contains "$out" "Backend: generic" "console names backend"
report="$(cat "$R/docs/eval_report.md")"
assert_contains "$report" "> Backend: generic | Model: custom" "report header names backend and model"
assert_contains "$(cat "$R/prompt.txt")" "Two" "last entry sent (xml journal via records)"
assert_not_contains "$(cat "$R/prompt.txt")" "One" "only last 1 entry sent"
assert_not_contains "$(cat "$R/prompt.txt")" "DECOY RUBRIC" "rubric next to script wins"
assert_contains "$(cat "$R/prompt.txt")" "Decision Specificity" "real rubric used"

run_eval CALAMUS_LLM_CMD="exit 1" -- >/dev/null 2>&1; assert_eq 1 "$?" "failed judge exits non-zero"
run_eval CALAMUS_LLM_CMD="echo not json" -- >/dev/null 2>&1; assert_eq 1 "$?" "unparseable judge exits non-zero"
run_eval CALAMUS_LLM_CMD="echo '[]'" -- >/dev/null 2>&1; assert_eq 1 "$?" "empty result exits non-zero"
run_eval -- >/dev/null 2>&1; assert_eq 1 "$?" "missing LLM_CMD exits non-zero"
run_eval CALAMUS_EVAL_BACKEND=bogus -- >/dev/null 2>&1; assert_eq 2 "$?" "unknown eval backend"

finish
