#!/usr/bin/env bash
# Activation runner: drives a fake claude, classifies, scores, never calls a model.
. "$(dirname "$0")/lib.sh"
RUN="$SKILL_DIR/evals/activation/activation.sh"

R="$(mk_repo)"; mkdir -p "$R/bin" "$R/home"
cat > "$R/bin/claude" <<'FAKE'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_LOG"
prompt="$2"
case "$(cat .claude/skills/calamus/SKILL.md)" in *"release notes, commit messages"*) v=tuned ;; *) v=shared ;; esac
if printf '%s' "$prompt" | grep -qi 'journal' || { [ "$v" = tuned ] && printf '%s' "$prompt" | grep -qiE 'remember|forget'; }; then
  echo '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"calamus"}}]}}'
else
  echo '{"type":"assistant","message":{"content":[{"type":"text","text":"ok"}]}}'
fi
FAKE
chmod +x "$R/bin/claude"

run() { env -i PATH="$R/bin:$PATH" HOME="$R/home" XDG_CONFIG_HOME="$R/home/.config" TMPDIR="${TMPDIR:-/tmp}" FAKE_LOG="$R/calls.log" "$@"; }

out="$(run bash "$RUN" --out "$R/out" 2>&1)"; rc=$?
assert_eq 0 "$rc" "runner succeeds with fake claude"
n="$(wc -l < "$SKILL_DIR/evals/activation/prompts.jsonl" | tr -d ' ')"
assert_eq "$((n * 2))" "$(wc -l < "$R/out/results.jsonl" | tr -d ' ')" "one result per prompt per variant"
assert_eq "$((n * 2))" "$(wc -l < "$R/calls.log" | tr -d ' ')" "one model call per prompt per variant"
assert_contains "$(head -1 "$R/calls.log")" "--model $(sed -n 's/^CALAMUS_CLAUDE_MODEL=//p' "$SKILL_DIR/assets/calamus.env")" "pinned model passed"
assert_contains "$(head -1 "$R/calls.log")" "--allowedTools Skill,Read" "tools limited to Skill and Read"
report="$(cat "$R/out/report.json")"
assert_contains "$report" '"decision": "tuned"' "tuned recall gain triggers adoption"
assert_contains "$out" "decision" "report printed"

run bash "$RUN" --host codex --out "$R/out2" >/dev/null 2>&1; assert_eq 2 "$?" "unsupported host"
run env CALAMUS_CLAUDE_MODEL= bash "$RUN" --out "$R/out3" >/dev/null 2>&1
assert_eq 1 "$([ ! -s "$R/out3/results.jsonl" ] && echo 1)" "no results without a model pin"

finish
