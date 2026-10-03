#!/usr/bin/env bash
# Host templates, adapter, and installer.
. "$(dirname "$0")/lib.sh"
A="$SKILL_DIR/assets"

# Templates match the spec 4.5 host matrix.
check_tpl() { # host python-expr expected
  assert_eq "$3" "$(python3 -c "import json; d=json.load(open('$A/hosts/$1/hooks.json')); print($2)")" "$1 template: $2"
}
check_tpl claude-code "sorted(d['hooks'])" "['PostCompact', 'PreCompact', 'SessionEnd']"
check_tpl claude-code "[d['hooks'][e][0]['hooks'][0]['timeout'] for e in ('PreCompact','PostCompact','SessionEnd')]" "[45, 10, 60]"
check_tpl codex "sorted(d['hooks'])" "['PostCompact', 'PreCompact', 'SessionEnd', 'Stop']"
check_tpl codex "[d['hooks'][e][0]['hooks'][0]['timeout'] for e in ('PreCompact','PostCompact','Stop','SessionEnd')]" "[45, 10, 90, 3]"
check_tpl cursor "(d['version'], sorted(d['hooks']))" "(1, ['preCompact', 'sessionEnd', 'stop'])"
check_tpl cursor "[d['hooks'][e][0]['timeout'] for e in ('preCompact','stop','sessionEnd')]" "[45, 90, 5]"
for h in claude-code codex cursor; do
  bad="$(grep -o '"command": "[^"]*"' "$A/hosts/$h/hooks.json" | grep -vE "\"__CALAMUS_DIR__/scripts/hook.sh --host $h --event (pre-compact|post-compact|turn-stop|session-end)\"" || true)"
  assert_eq "" "$bad" "$h command form"
done

# Adapter: at most 15 lines, no filesystem paths beyond ./docs.
assert_eq 1 "$([ "$(wc -l < "$A/adapter.md")" -le 15 ] && echo 1)" "adapter <= 15 lines"
assert_eq "" "$(grep -oE '(~|/Users|/home|\.claude/|\.codex/|\.agents/)[^ ]*' "$A/adapter.md" || true)" "adapter has no paths"

# Installer with a throwaway HOME.
R="$(mk_repo)"; H="$R/home"; mkdir -p "$H"
out="$(HOME="$H" "$SKILL_DIR/scripts/calamus-install" --host claude-code)"
assert_eq "$SKILL_DIR" "$(cd "$H/.claude/skills/calamus" && pwd -P)" "claude-code symlink target"
assert_contains "$out" "\"command\": \"$H/.claude/skills/calamus/scripts/hook.sh --host claude-code --event session-end\"" "resolved command"
assert_not_contains "$out" "__CALAMUS_DIR__" "placeholder resolved"
assert_contains "$out" "Use the \`calamus\` skill" "adapter printed"
HOME="$H" "$SKILL_DIR/scripts/calamus-install" --host claude-code >/dev/null 2>&1; assert_eq 1 "$?" "refuses existing destination"
HOME="$H" "$SKILL_DIR/scripts/calamus-install" --host codex >/dev/null
assert_eq 1 "$([ -L "$H/.agents/skills/calamus" ] && echo 1)" "codex installs to ~/.agents/skills"
H2="$R/home two"; mkdir -p "$H2"
out="$(HOME="$H2" "$SKILL_DIR/scripts/calamus-install" --host cursor --copy)"
assert_eq 1 "$([ -d "$H2/.agents/skills/calamus" ] && [ ! -L "$H2/.agents/skills/calamus" ] && echo 1)" "--copy copies"
assert_file "$H2/.agents/skills/calamus/scripts/hook.sh" "copied engine"
assert_contains "$out" "'$H2/.agents/skills/calamus/scripts/hook.sh' --host cursor" "path with space is quoted"
assert_eq "" "$(ls -A "$H" | grep -vE '^\.(claude|agents)$' || true)" "no settings files written"
# Notes separate platform defaults from Calamus's configured timeouts.
assert_contains "$out" "documents no default or maximum hook timeout" "cursor timeout note"
assert_contains "$out" ".claude/settings.local.json" "cursor import note names all Claude files"
H3="$R/home3"; mkdir -p "$H3"
out="$(HOME="$H3" "$SKILL_DIR/scripts/calamus-install" --host claude-code)"
assert_contains "$out" "1.5 s by default" "claude-code SessionEnd default"
assert_contains "$out" "claude plugin marketplace add '$REPO_ROOT'" "claude-code prints marketplace add"
assert_contains "$out" "claude plugin install calamus@calamus" "claude-code prints plugin install"
assert_contains "$out" "do not also merge the hooks below" "claude-code warns against double registration"
H4="$R/home4"; mkdir -p "$H4"
out="$(HOME="$H4" "$SKILL_DIR/scripts/calamus-install" --host codex)"
assert_contains "$out" "trust it with /hooks" "codex trust review note"
assert_contains "$out" "1 s by default and 3 s at most" "codex SessionEnd limits"
"$SKILL_DIR/scripts/calamus-install" --host nope >/dev/null 2>&1; assert_eq 2 "$?" "bad host"

finish
