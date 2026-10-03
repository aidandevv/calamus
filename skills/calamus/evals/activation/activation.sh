#!/usr/bin/env bash
# Activation experiment runner. Makes one model call per prompt per variant,
# so run it only on request.
#
# Usage: activation.sh [--host claude-code] [--out DIR]
# For each description variant (shared from SKILL.md, tuned from
# variants/tuned.txt) it builds a scratch project holding a copy of the skill
# with that description, runs every prompt in prompts.jsonl through the host
# CLI with the pinned model, records whether the skill activated and which
# reference it read, then scores both variants and applies the decision rule.
# A personal install of the skill (for example ~/.claude/skills/calamus)
# competes with the scratch copy; remove it before running.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CALAMUS_SKILL_DIR="$(cd "$HERE/../.." && pwd)"
CALAMUS_LIB_DIR="$CALAMUS_SKILL_DIR/scripts/lib"
export CALAMUS_SKILL_DIR CALAMUS_LIB_DIR

host=claude-code; out=""
while [ $# -gt 0 ]; do
  case "$1" in
    --host) host="${2:-}"; shift 2 ;;
    --out) out="${2:-}"; shift 2 ;;
    *) echo "usage: activation.sh [--host claude-code] [--out DIR]" >&2; exit 2 ;;
  esac
done
case "$host" in
  claude-code) ;;
  *) echo "no activation runner for host: $host (only claude-code is verified)" >&2; exit 2 ;;
esac

. "$CALAMUS_LIB_DIR/config.sh"
. "$CALAMUS_LIB_DIR/gate.sh"
calamus_load_config "$(pwd)" none
model="$(calamus_model_name claude)"
[ -n "$model" ] || { echo "CALAMUS_CLAUDE_MODEL is empty; no fallback model" >&2; exit 1; }
command -v claude >/dev/null 2>&1 || { echo "claude not found on PATH" >&2; exit 127; }

[ -n "$out" ] || out="$(mktemp -d "${TMPDIR:-/tmp}/calamus-activation.XXXXXX")"
mkdir -p "$out"
: > "$out/results.jsonl"
py="$HERE/activation.py"

for variant in shared tuned; do
  proj="$out/project-$variant"
  rm -rf "$proj"; mkdir -p "$proj/.claude/skills" "$proj/docs"
  cp -R "$CALAMUS_SKILL_DIR" "$proj/.claude/skills/calamus"
  rm -rf "$proj/.claude/skills/calamus/evals"
  if [ "$variant" = tuned ]; then
    python3 "$py" skill "$CALAMUS_SKILL_DIR/SKILL.md" "$HERE/variants/tuned.txt" > "$proj/.claude/skills/calamus/SKILL.md"
  fi
  while IFS= read -r row; do
    [ -n "$row" ] || continue
    id="$(printf '%s' "$row" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
    prompt="$(printf '%s' "$row" | python3 -c 'import json,sys; print(json.load(sys.stdin)["prompt"])')"
    log="$out/$variant-$id.jsonl"
    (cd "$proj" && claude -p "$prompt" --output-format stream-json --verbose \
      --model "$model" --setting-sources project --allowedTools Skill,Read \
      --max-turns 3) > "$log" 2>/dev/null || true
    python3 - "$py" "$log" "$id" "$variant" >> "$out/results.jsonl" <<'PY'
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("activation", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
r = m.classify(m._read_jsonl(sys.argv[2]))
r.update(id=sys.argv[3], variant=sys.argv[4])
print(json.dumps(r))
PY
  done < "$HERE/prompts.jsonl"
done

python3 "$py" score "$HERE/prompts.jsonl" "$out/results.jsonl" | tee "$out/report.json"
echo "Results: $out (model: $model)"
