#!/usr/bin/env bash
# Portable timeout: exit codes, stdio passthrough, process-group kill.
. "$(dirname "$0")/lib.sh"
T="$SKILL_DIR/scripts/lib/timeout.py"

out="$(echo hi | python3 "$T" 5 -- cat)"; rc=$?
assert_eq "0 hi" "$rc $out" "passes stdin/stdout and exit 0"
python3 "$T" 5 -- sh -c 'exit 7'; assert_eq 7 "$?" "propagates exit code"
python3 "$T" 5 -- /nonexistent/cmd 2>/dev/null; assert_eq 127 "$?" "missing command"

# A child that ignores TERM and has its own child must still be killed.
R="$(mk_repo)"
start=$(date +%s)
python3 "$T" 1 -- sh -c "trap '' TERM; (trap '' TERM; sleep 30; touch '$R/grandchild-survived') & sleep 30" >/dev/null 2>&1
rc=$?
elapsed=$(( $(date +%s) - start ))
assert_eq 124 "$rc" "timeout exit code"
[ "$elapsed" -lt 6 ] || _fail "timeout took ${elapsed}s"
sleep 1
assert_eq "" "$(pgrep -f "grandchild-survived" || true)" "process group killed"

finish
