#!/usr/bin/env bash
# Agent Skills specification checks for skills/calamus.
. "$(dirname "$0")/lib.sh"
SK="$SKILL_DIR/SKILL.md"

fm() { # key → frontmatter value (folded scalars joined)
  python3 - "$SK" "$1" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
lines, key, out, grab = m.group(1).split("\n"), sys.argv[2], [], False
for l in lines:
    if grab:
        if l.startswith("  "):
            out.append(l.strip()); continue
        break
    if l.startswith(key + ":"):
        val = l[len(key) + 1:].strip()
        if val in (">-", ">", "|"):
            grab = True
        else:
            out.append(val.strip('"'))
print(" ".join(out))
PY
}

assert_eq "calamus" "$(fm name)" "name"
assert_eq "calamus" "$(basename "$SKILL_DIR")" "directory matches name"
assert_eq 1 "$([[ "$(fm name)" =~ ^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$ ]] && echo 1)" "name charset"
desc="$(fm description)"
assert_eq 1 "$([ "${#desc}" -ge 1 ] && [ "${#desc}" -le 1024 ] && echo 1)" "description length ${#desc}"
assert_eq 1 "$([ "$(wc -l < "$SK")" -le 150 ] && echo 1)" "SKILL.md <= 150 lines"

# Every referenced skill-relative path exists and references are one level deep.
for p in $(grep -oE '(references|scripts)/[A-Za-z0-9_./-]+' "$SK" | sed 's/[.,)]*$//' | sort -u); do
  assert_file "$SKILL_DIR/$p" "SKILL.md reference $p"
done
assert_eq "" "$(find "$SKILL_DIR/references" -mindepth 2 -type f)" "references one level deep"

if command -v skills-ref >/dev/null 2>&1; then
  skills-ref validate "$SKILL_DIR" >/dev/null; assert_eq 0 "$?" "skills-ref validate"
fi

finish
