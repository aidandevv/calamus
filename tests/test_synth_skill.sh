#!/usr/bin/env bash
# Agent Skills checks for skills/calamus-synthesis, mirroring test_skill.sh and test_docs.sh.
. "$(dirname "$0")/lib.sh"
SK="$SYNTH_DIR/SKILL.md"

fm() { python3 - "$SK" "$1" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
out, grab = [], False
for l in m.group(1).split("\n"):
    if grab:
        if l.startswith("  "):
            out.append(l.strip()); continue
        break
    if l.startswith(sys.argv[2] + ":"):
        val = l[len(sys.argv[2]) + 1:].strip()
        if val in (">-", ">", "|"):
            grab = True
        else:
            out.append(val.strip('"'))
print(" ".join(out))
PY
}

assert_eq "calamus-synthesis" "$(fm name)" "name"
assert_eq "calamus-synthesis" "$(basename "$SYNTH_DIR")" "directory matches name"
desc="$(fm description)"
assert_eq 1 "$([ "${#desc}" -ge 1 ] && [ "${#desc}" -le 1024 ] && echo 1)" "description length ${#desc}"
assert_eq 1 "$([ "$(wc -l < "$SK")" -le 150 ] && echo 1)" "SKILL.md <= 150 lines"

for p in $(grep -oE '(references|scripts|agents|assets)/[A-Za-z0-9_./-]+' "$SK" | sed 's/[.,)]*$//' | sort -u); do
  assert_file "$SYNTH_DIR/$p" "SKILL.md reference $p"
done
for f in procedure outputs whitepaper style voice; do
  assert_file "$SYNTH_DIR/references/$f.md" "reference $f.md"
done
assert_eq "" "$(find "$SYNTH_DIR/references" -mindepth 2 -type f)" "references one level deep"
for f in "$SYNTH_DIR"/references/*.md; do
  n="$(wc -l < "$f" | tr -d ' ')"
  assert_eq 1 "$([ "$n" -le 300 ] && echo 1)" "$(basename "$f") has $n lines (max 300)"
  assert_eq "" "$(grep -nE '~/\.(claude|codex)|SKILL\.md|/Users/|/home/' "$f" || true)" "stale or local path in $(basename "$f")"
done

assert_eq "" "$(grep -nE '^model:' "$SYNTH_DIR/agents/journal-analyst.md" || true)" "analyst brief names no model"

# Every lint rule is explained in references/style.md.
for rule in $(python3 -c "
import re
src = open('$SYNTH_DIR/scripts/lib/lint.py').read()
print(' '.join(sorted(set(re.findall(r'\"((?:band|stock|filler|stacked|repeated|vague|contrast|empty|tag|citation|bullet)-[a-z-]+)\"', src)))))"); do
  assert_contains "$(cat "$SYNTH_DIR/references/style.md")" "\`$rule\`" "style.md explains $rule"
done

# Schemas parse and agree with the engine.
out="$(python3 - "$SYNTH_DIR" "$REPO_ROOT/tests" <<'PY'
import json, os, sys, tempfile
sys.path.insert(0, sys.argv[2])
import synth_fixture as fx
import base, facts
fs = json.load(open(os.path.join(sys.argv[1], "assets", "facts.schema.json")))
an = json.load(open(os.path.join(sys.argv[1], "assets", "analysis.schema.json")))
root = tempfile.mkdtemp()
eng = fx.engineering()
fx.write(root, "jsonl", eng, fx.product(eng))
f = facts.build(root, base.default_conf("synth.conf"))
missing = [k for k in fs["required"] if k not in f]
rec_missing = [k for k in fs["properties"]["records"]["items"]["required"] if k not in f["records"][0]]
a = fx.sample_analysis(f)
an_missing = [k for k in an["required"] if k not in a]
print(" ".join(missing + rec_missing + an_missing))
PY
)"
assert_eq "" "$out" "schemas list only keys the engine and sample analysis carry"

finish
