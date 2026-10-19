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

assert_contains "$report" '"pinned": true' "claude run is labeled pinned"

# Cursor: fake `agent` speaking Cursor's documented stream-json shapes.
cat > "$R/bin/agent" <<'FAKE'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_LOG"
for a in "$@"; do prompt="$a"; done
echo '{"type":"system","subtype":"init","model":"auto-fake"}'
if [ -f .agents/skills/calamus/SKILL.md ] && printf '%s' "$prompt" | grep -qi 'journal'; then
  echo "{\"type\":\"tool_call\",\"subtype\":\"started\",\"tool_call\":{\"readToolCall\":{\"args\":{\"path\":\"$PWD/.agents/skills/calamus/SKILL.md\"}}}}"
fi
echo '{"type":"result","duration_ms":1}'
FAKE
chmod +x "$R/bin/agent"
: > "$R/calls.log"
out="$(run bash "$RUN" --host cursor --out "$R/cur" 2>&1)"; rc=$?
assert_eq 0 "$rc" "cursor runner succeeds unpinned"
call="$(head -1 "$R/calls.log")"
assert_contains "$call" "-p --output-format stream-json --trust" "cursor headless stream-json call"
assert_not_contains "$call" "--model" "no model flag without a pin"
assert_not_contains "$call" "--force" "edits stay proposed, never applied"
report="$(cat "$R/cur/report.json")"
assert_contains "$report" '"pinned": false' "cursor run labeled unpinned"
assert_contains "$report" '"auto-fake"' "observed model recorded"
assert_contains "$out" "UNPINNED" "console warns the run is unpinned"
assert_contains "$report" '"recall": 40.0' "cursor activation classified"
: > "$R/calls.log"
run env CALAMUS_CURSOR_MODEL=pin-x bash "$RUN" --host cursor --out "$R/cur2" >/dev/null 2>&1
assert_contains "$(head -1 "$R/calls.log")" "--model pin-x" "cursor pin passed when set"
assert_contains "$(cat "$R/cur2/report.json")" '"pinned": true' "cursor run with a pin labeled pinned"

run bash "$RUN" --host codex --out "$R/out2" >/dev/null 2>&1; assert_eq 2 "$?" "unsupported host"
run env CALAMUS_CLAUDE_MODEL= bash "$RUN" --out "$R/out3" >/dev/null 2>&1
assert_eq 1 "$([ ! -s "$R/out3/results.jsonl" ] && echo 1)" "no results without a model pin"

finish
