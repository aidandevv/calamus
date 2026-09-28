# Shared helpers for shell tests. Source this file; do not execute it.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="$REPO_ROOT/skills/calamus"
FAILS=0
TESTS=0

_fail() {
  FAILS=$((FAILS + 1))
  printf '  FAIL: %s\n' "$*" >&2
}

assert_eq() { # expected actual message
  TESTS=$((TESTS + 1))
  [ "$1" = "$2" ] || _fail "$3 (expected [$1], got [$2])"
}

assert_contains() { # haystack needle message
  TESTS=$((TESTS + 1))
  case "$1" in *"$2"*) ;; *) _fail "$3 (missing [$2])" ;; esac
}

assert_not_contains() { # haystack needle message
  TESTS=$((TESTS + 1))
  case "$1" in *"$2"*) _fail "$3 (unexpected [$2])" ;; *) ;; esac
}

assert_file() { TESTS=$((TESTS + 1)); [ -e "$1" ] || _fail "$2 (missing $1)"; }
assert_file_absent() { TESTS=$((TESTS + 1)); [ ! -e "$1" ] || _fail "$2 (unexpected $1)"; }

# Creates an empty git repository in a temp dir and prints its path.
mk_repo() {
  local d
  d="$(mktemp -d "${TMPDIR:-/tmp}/calamus-test.XXXXXX")"
  d="$(cd "$d" && pwd -P)"
  git -C "$d" init -q
  printf '%s\n' "$d"
}

# Ends a test file: prints a summary and exits non-zero on failure.
finish() {
  if [ "$FAILS" -gt 0 ]; then
    printf '%s: %d of %d assertions failed\n' "$(basename "$0")" "$FAILS" "$TESTS" >&2
    exit 1
  fi
  printf '%s: %d assertions passed\n' "$(basename "$0")" "$TESTS"
}
