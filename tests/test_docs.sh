#!/usr/bin/env bash
# Reference docs: generated blocks current, size limits, no stale paths.
. "$(dirname "$0")/lib.sh"
REFS="$SKILL_DIR/references"

python3 "$SKILL_DIR/scripts/lib/gendocs.py" --check 2>/dev/null
assert_eq 0 "$?" "generated blocks match the schema (run gendocs.py --write)"

for f in "$REFS"/*.md; do
  n="$(wc -l < "$f" | tr -d ' ')"
  [ "$n" -le 300 ] || _fail "$(basename "$f") has $n lines (max 300)"
  TESTS=$((TESTS + 1))
  assert_eq "" "$(grep -nE '~/\.(claude|codex)|SKILL\.md|journaling/|\.\./' "$f" || true)" "stale path in $(basename "$f")"
done
for f in engineering-journal.md product-insights.md format-xml.md format-jsonl.md; do
  assert_file "$REFS/$f" "reference $f"
done

# Header shown in each journal reference equals the schema's header.
for pair in "engineering engineering-journal.md" "product product-insights.md"; do
  set -- $pair
  hdr="$(python3 -c "import json,sys; print(json.load(open('$SKILL_DIR/assets/schema/entry.schema.json'))['journals']['$1']['md_header'], end='')")"
  assert_contains "$(cat "$REFS/$2")" "$hdr" "$2 header matches schema"
done

# Host facts: every row carries a status; verified rows cite a URL and date.
HF="$REPO_ROOT/docs/host-facts.md"
assert_file "$HF" "host facts"
if [ -f "$HF" ]; then
  rows="$(grep -E '^\| [^-]' "$HF" | tail -n +2)"
  assert_eq "" "$(printf '%s\n' "$rows" | grep -vE '\| (verified|unverified) \|$' || true)" "host fact rows have a status"
  assert_eq "" "$(printf '%s\n' "$rows" | grep -E '\| verified \|$' | grep -vE 'https://[^ ]+ \| 20[0-9]{2}-[0-9]{2}-[0-9]{2} \|' || true)" "verified rows cite source and date"
fi

finish
