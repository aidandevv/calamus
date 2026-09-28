#!/usr/bin/env bash
# Offline test suite: Python unit tests, then every tests/test_*.sh.
set -u
cd "$(dirname "$0")/.."
status=0

python3 -m unittest discover -s tests -p 'test_*.py' 2>&1 | tail -n 3
py=${PIPESTATUS[0]}
# Exit 5 means no tests were collected, which is not a failure.
[ "$py" -eq 0 ] || [ "$py" -eq 5 ] || status=1

for t in tests/test_*.sh; do
  [ -e "$t" ] || continue
  bash "$t" || status=1
done

[ "$status" -eq 0 ] && echo "ALL PASSED" || echo "FAILURES"
exit "$status"
