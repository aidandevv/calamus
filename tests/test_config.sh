#!/usr/bin/env bash
# Config precedence, data-only parsing, and profile rules.
. "$(dirname "$0")/lib.sh"

# Runs config loading in a clean environment under macOS /bin/bash (3.2).
# Usage: load <root> <host> <skill-dir> <xdg> [VAR=value...] -- <expression to echo>
load() {
  local root="$1" host="$2" skill="$3" xdg="$4"; shift 4
  local envs=()
  while [ "$1" != "--" ]; do envs+=("$1"); shift; done
  shift
  env -i PATH="$PATH" HOME="$root" XDG_CONFIG_HOME="$xdg" CALAMUS_SKILL_DIR="$skill" "${envs[@]}" \
    /bin/bash -c ". '$REPO_ROOT/skills/calamus/scripts/lib/config.sh'; calamus_load_config '$root' '$host'; $1"
}

R="$(mk_repo)"
XDG="$R/xdg"; mkdir -p "$XDG/calamus" "$R/.calamus"
SK="$R/skill"; mkdir -p "$SK/assets/profiles"
printf 'CALAMUS_MIN_TEXT=1\nCALAMUS_TAIL_SWEEP=1\nCALAMUS_DEDUPE_SECS=1\nCALAMUS_FORMAT=md\nCALAMUS_BACKEND=auto\nCALAMUS_LEVEL1_SAMPLE=1\n' > "$SK/assets/calamus.env"
printf '# measured: x\nCALAMUS_MIN_TEXT=2\n# measured: x\nCALAMUS_TAIL_SWEEP=2\n# measured: x\nCALAMUS_DEDUPE_SECS=2\n' > "$SK/assets/profiles/claude.env"
printf 'CALAMUS_MIN_TEXT=3\nCALAMUS_TAIL_SWEEP=3\n' > "$XDG/calamus/calamus.env"
printf 'CALAMUS_MIN_TEXT=4\n' > "$R/.calamus/calamus.env"

out="$(load "$R" claude-code "$SK" "$XDG" CALAMUS_LEVEL1_SAMPLE=9 -- 'echo $CALAMUS_LEVEL1_SAMPLE $CALAMUS_MIN_TEXT $CALAMUS_TAIL_SWEEP $CALAMUS_DEDUPE_SECS $CALAMUS_FORMAT $CALAMUS_BACKEND_RESOLVED')"
assert_eq "9 4 3 2 md claude" "$out" "precedence env > project > user > profile > defaults"

# Project file cannot set command-bearing keys; user file can.
printf 'CALAMUS_LLM_CMD=touch %s/pwned-project\nCALAMUS_CODEX_BIN=/bin/evil\nCALAMUS_ACTIVE=1\n' "$R" >> "$R/.calamus/calamus.env"
out="$(load "$R" generic "$SK" "$XDG" -- 'echo "[${CALAMUS_LLM_CMD:-}][${CALAMUS_CODEX_BIN:-}][${CALAMUS_ACTIVE:-}][${CALAMUS_BACKEND_RESOLVED}]"')"
assert_eq "[][][][]" "$out" "project file ignored for LLM_CMD, *_BIN, ACTIVE; generic unresolved"
printf 'CALAMUS_LLM_CMD=cat\n' >> "$XDG/calamus/calamus.env"
out="$(load "$R" generic "$SK" "$XDG" -- 'echo "$CALAMUS_LLM_CMD/$CALAMUS_BACKEND_RESOLVED"')"
assert_eq "cat/generic" "$out" "user file may set LLM_CMD; generic resolves"

# Values are data, never executed.
printf 'CALAMUS_FORMAT=$(touch %s/pwned)\nCALAMUS_TAIL_SNAPSHOT=`touch %s/pwned2`\nCALAMUS_X="quoted value"\n' "$R" "$R" > "$R/.calamus/calamus.env"
out="$(load "$R" claude-code "$SK" "$XDG" -- 'echo "$CALAMUS_X"')"
assert_file_absent "$R/pwned" "command substitution not executed"
assert_file_absent "$R/pwned2" "backticks not executed"
assert_file_absent "$R/pwned-project" "LLM_CMD from project never run"
assert_eq "quoted value" "$out" "surrounding quotes stripped"

# Explicit backend overrides host; unknown backend resolves to nothing.
out="$(load "$R" codex "$SK" "$XDG" CALAMUS_BACKEND=claude -- 'echo $CALAMUS_BACKEND_RESOLVED')"
assert_eq "claude" "$out" "explicit backend"
out="$(load "$R" codex "$SK" "$XDG" CALAMUS_BACKEND=nope -- 'echo "[$CALAMUS_BACKEND_RESOLVED]"')"
assert_eq "[]" "$out" "unknown backend"

# Shipped profiles: every value line follows a measured comment; no model pins.
for p in "$SKILL_DIR"/assets/profiles/*.env; do
  bad="$(awk '/^CALAMUS_/ { if (prev !~ /^# measured:/) print FILENAME": "$0 } { prev=$0 }' "$p")"
  assert_eq "" "$bad" "unmeasured profile value in $(basename "$p")"
  assert_eq "0" "$(grep -c '_MODEL=' "$p")" "model pin in $(basename "$p")"
done
for b in claude codex cursor generic; do assert_file "$SKILL_DIR/assets/profiles/$b.env" "profile $b"; done

finish
