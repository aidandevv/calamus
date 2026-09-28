#!/usr/bin/env bash
# calamus-init, -append, -query, -convert.
. "$(dirname "$0")/lib.sh"
S="$SKILL_DIR/scripts"

entry() { # tag title [files]
  printf '{"variant":"lightweight","tag":"%s","date":"2026-09-27","title":"%s","summary":"Did a thing.","files":["%s"],"tradeoff":"Chose A over B.","evidence":{"status":"verified","text":"Tests pass."},"followups":[]}' \
    "$1" "$2" "${3:-a.py}"
}

# init: per format, idempotent
for fmt in md xml jsonl; do
  R="$(mk_repo)"
  out="$(cd "$R" && "$S/calamus-init" --format "$fmt")"
  assert_file "$R/docs/dev_journal.$fmt" "init $fmt eng"
  assert_file "$R/docs/product_insights.$fmt" "init $fmt product"
  assert_contains "$out" ".calamus/" "init prints ignore reminder"
  out="$(cd "$R" && "$S/calamus-init" --format "$fmt")"
  assert_contains "$out" "already exists" "init idempotent $fmt"
done
R="$(mk_repo)"; (cd "$R" && "$S/calamus-init" --format model >/dev/null)
assert_file "$R/docs/dev_journal.xml" "model alias is xml"
R="$(mk_repo)"; (cd "$R" && "$S/calamus-init" --format bogus >/dev/null 2>&1); assert_eq 2 "$?" "bad format exit"

# append + query on each format
for fmt in md xml jsonl; do
  R="$(mk_repo)"; (cd "$R" && "$S/calamus-init" --format "$fmt" >/dev/null)
  out="$(cd "$R" && entry CP-DEBUG "First" src/x.py | "$S/calamus-append" --journal engineering)"
  assert_contains "$out" "ok 2026" "append ok $fmt"
  id1="${out#ok }"
  (cd "$R" && printf '{"entries":[%s,%s]}' "$(entry CP-MILESTONE Second)" "$(entry CP-DEBUG Third)" \
    | "$S/calamus-append" --journal engineering >/dev/null)
  err="$(cd "$R" && entry CP-DEBUG "First" src/x.py | "$S/calamus-append" --journal engineering 2>&1)"; rc=$?
  assert_eq 1 "$rc" "duplicate exit $fmt"
  assert_contains "$err" "duplicate" "duplicate message $fmt"
  err="$(cd "$R" && echo '{"variant":"lightweight","tag":"CP-NOPE"}' | "$S/calamus-append" --journal engineering 2>&1)"; rc=$?
  assert_eq 1 "$rc" "invalid exit $fmt"
  assert_contains "$err" "summary: required" "field error listed $fmt"
  err="$(cd "$R" && echo 'not json' | "$S/calamus-append" --journal engineering 2>&1)"
  assert_contains "$err" "not valid JSON" "bad json $fmt"

  b="$(cd "$R" && "$S/calamus-query" --brief)"
  assert_eq 3 "$(printf '%s\n' "$b" | grep -c '\[CP-')" "brief count $fmt"
  assert_eq 1 "$(cd "$R" && "$S/calamus-query" --brief --last 1 | grep -c Third)" "last $fmt"
  assert_eq 2 "$(cd "$R" && "$S/calamus-query" --brief --tag '[CP-DEBUG]' | wc -l | tr -d ' ')" "tag $fmt"
  assert_eq 1 "$(cd "$R" && "$S/calamus-query" --brief --file src/x.py | wc -l | tr -d ' ')" "file $fmt"
  full="$(cd "$R" && "$S/calamus-query" --id "$id1" --out md)"
  assert_contains "$full" "### [CP-DEBUG] | 2026-09-27: First" "id fetch $fmt"
  assert_not_contains "$full" "Second" "id fetch only one $fmt"
  assert_eq "" "$(cd "$R" && "$S/calamus-query" --since 2027-01-01 2>/dev/null)" "since $fmt"
done

# query on this repository's own journals
b="$("$S/calamus-query" --root "$REPO_ROOT" --brief)"
assert_eq "$(cat "$REPO_ROOT"/docs/dev_journal.md "$REPO_ROOT"/docs/product_insights.md | grep -c '^### \[')" "$(printf '%s\n' "$b" | wc -l | tr -d ' ')" "repo journals brief"
assert_contains "$("$S/calamus-query" --root "$REPO_ROOT" --type marker --brief)" "marker:session" "repo markers"

# convert: md -> xml -> jsonl -> md round trip, refuse overwrite, original untouched
R="$(mk_repo)"; (cd "$R" && "$S/calamus-init" >/dev/null)
(cd "$R" && printf '[%s,%s,{"record":"marker","kind":"session","when":"2026-09-27 10:00","session":"s1","event":"turn-stop"}]' \
  "$(entry CP-DEBUG One)" "$(entry CP-PIVOT 'Two <&> ]]>')" | "$S/calamus-append" --journal engineering >/dev/null)
orig="$(shasum "$R/docs/dev_journal.md")"
cp "$R/docs/dev_journal.md" "$R/orig.md"
(cd "$R" && "$S/calamus-convert" --to xml --journal engineering >/dev/null)
assert_eq "$orig" "$(shasum "$R/docs/dev_journal.md")" "original untouched"
(cd "$R" && "$S/calamus-convert" --to xml --journal engineering >/dev/null 2>&1); assert_eq 1 "$?" "refuses overwrite"
mv "$R/docs/dev_journal.md" "$R/aside.md"
(cd "$R" && "$S/calamus-convert" --to jsonl --journal engineering >/dev/null)
mv "$R/docs/dev_journal.xml" "$R/aside.xml"
(cd "$R" && "$S/calamus-convert" --to md --journal engineering >/dev/null)
assert_eq "$(shasum < "$R/orig.md")" "$(shasum < "$R/docs/dev_journal.md")" "md->xml->jsonl->md byte round trip"

finish
