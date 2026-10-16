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

# extract: writes facts.json, stays read-only, and is deterministic.
R="$(mk_repo)"
python3 - "$R" "$REPO_ROOT/tests" <<'PY'
import sys
sys.path.insert(0, sys.argv[2])
import synth_fixture as fx
eng = fx.engineering()
fx.write(sys.argv[1], "md", eng, fx.product(eng))
PY
before="$(cat "$R/docs/dev_journal.md" "$R/docs/product_insights.md" | shasum)"
(cd "$R" && "$SYN" extract --out docs/writeups/t >/dev/null); assert_eq 0 "$?" "extract exits 0"
assert_file "$R/docs/writeups/t/facts.json" "facts.json written"
one="$(cat "$R/docs/writeups/t/facts.json")"
two="$(cd "$R" && "$SYN" extract)"
assert_eq "$one" "$two" "extract is deterministic"
assert_not_contains "$one" "$R" "facts.json has no absolute paths"
after="$(cat "$R/docs/dev_journal.md" "$R/docs/product_insights.md" | shasum)"
assert_eq "$before" "$after" "extract leaves journals byte-identical"
(cd "$R" && "$SYN" extract --since 2026-13-45 >/dev/null 2>&1); assert_eq 2 "$?" "bad --since exits 2"

finish
