#!/usr/bin/env bash
# Host packages: hook equivalence with assets/hosts/, no fork of the skill.
. "$(dirname "$0")/lib.sh"
P="$REPO_ROOT/packaging"

# check_hooks <host> <package hooks.json> <root expression in package commands>
check_hooks() {
  python3 - "$SKILL_DIR/assets/hosts/$1/hooks.json" "$2" "$3" <<'PY'
import json, sys
tpl, pkg, root = (json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3])
want = json.loads(json.dumps(tpl).replace("__CALAMUS_DIR__", root.replace('"', '\\"') + "/skills/calamus"))
if want != pkg:
    print("package hooks differ from template:\n%s\n%s" % (json.dumps(want, indent=1), json.dumps(pkg, indent=1)))
PY
}

# check_no_fork <package dir> <allowed manifest files...>: only manifests are
# package-specific, and the bundled skill resolves to the canonical one.
check_no_fork() {
  local pkg="$1"; shift
  local extra
  extra="$(cd "$pkg" && find . \( -type f -o -type l \) ! -path './skills/calamus' ! -path './skills/calamus/*' | sed 's|^\./||' | sort)"
  assert_eq "$(printf '%s\n' "$@" | sort)" "$extra" "$(basename "$pkg") holds only its manifests"
  assert_eq "$(cd "$SKILL_DIR" && pwd -P)" "$(cd "$pkg/skills/calamus" && pwd -P)" "$(basename "$pkg") skill is the canonical skill"
  assert_eq "" "$(diff -r "$SKILL_DIR" "$pkg/skills/calamus" 2>&1 || true)" "$(basename "$pkg") skill bytes equal canonical"
}

CC="$P/claude-code"
assert_file "$CC/.claude-plugin/plugin.json" "claude-code plugin manifest"
assert_eq "calamus" "$(python3 -c "import json; print(json.load(open('$CC/.claude-plugin/plugin.json'))['name'])" 2>/dev/null)" "claude-code plugin name"
assert_eq "" "$(check_hooks claude-code "$CC/hooks/hooks.json" '"${CLAUDE_PLUGIN_ROOT}"' 2>&1)" "claude-code plugin hooks equal template"
check_no_fork "$CC" .claude-plugin/plugin.json hooks/hooks.json
assert_eq "./packaging/claude-code" "$(python3 -c "import json; print([p['source'] for p in json.load(open('$REPO_ROOT/.claude-plugin/marketplace.json'))['plugins'] if p['name']=='calamus'][0])" 2>/dev/null)" "marketplace lists the claude-code plugin"

finish
