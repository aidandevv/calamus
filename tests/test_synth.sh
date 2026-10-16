#!/usr/bin/env bash
# calamus-synth command-line behavior.
. "$(dirname "$0")/lib.sh"
SYN_DIR="$REPO_ROOT/skills/calamus-synthesis"
SYN="$SYN_DIR/scripts/calamus-synth"

"$SYN" >/dev/null 2>&1; assert_eq 2 "$?" "no command is a usage error"
"$SYN" bogus >/dev/null 2>&1; assert_eq 2 "$?" "unknown command is a usage error"
err="$("$SYN" 2>&1 >/dev/null)"; assert_contains "$err" "usage: calamus-synth" "usage printed to stderr"

# Missing sibling: a lone copy of the skill exits 2 and names calamus.
T="$(mktemp -d "${TMPDIR:-/tmp}/synth-alone.XXXXXX")"
cp -R "$SYN_DIR" "$T/calamus-synthesis"
err="$("$T/calamus-synthesis/scripts/calamus-synth" extract 2>&1 >/dev/null)"; rc=$?
assert_eq 2 "$rc" "missing sibling exits 2"
assert_contains "$err" "calamus skill is missing" "missing sibling named"

finish
