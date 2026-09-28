# Calamus configuration loader. Source this file; it defines functions only.
# Files are read as data: only CALAMUS_[A-Z0-9_]+=value lines are used and
# nothing is sourced or evaluated. Compatible with bash 3.2.

CALAMUS_LIB_DIR="${CALAMUS_LIB_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
CALAMUS_SKILL_DIR="${CALAMUS_SKILL_DIR:-$(cd "$CALAMUS_LIB_DIR/../.." && pwd)}"

# _calamus_read_file <file> <trust: project|user|shipped> [only-key]
# Exports each key that is not already set, so earlier sources win.
_calamus_read_file() {
  local file="$1" trust="$2" only="${3:-}" line key val
  [ -f "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    [[ "$line" =~ ^CALAMUS_[A-Z0-9_]+= ]] || continue
    key="${line%%=*}"
    val="${line#*=}"
    [ -n "$only" ] && [ "$key" != "$only" ] && continue
    case "$key" in
      CALAMUS_ACTIVE|CALAMUS_BACKEND_RESOLVED) continue ;;
    esac
    if [ "$trust" = "project" ]; then
      case "$key" in
        CALAMUS_LLM_CMD|CALAMUS_*_BIN) continue ;;
      esac
    fi
    if [[ "$val" =~ ^\"(.*)\"$ ]] || [[ "$val" =~ ^\'(.*)\'$ ]]; then
      val="${BASH_REMATCH[1]}"
    fi
    [ -n "${!key+x}" ] && continue
    export "$key=$val"
  done < "$file"
}

# calamus_resolve_backend <host> — prints the backend name, or nothing.
calamus_resolve_backend() {
  local host="$1" b="${CALAMUS_BACKEND:-auto}"
  if [ "$b" = "auto" ]; then
    case "$host" in
      claude-code) b=claude ;;
      codex) b=codex ;;
      cursor) b=cursor ;;
      generic) if [ -n "${CALAMUS_LLM_CMD:-}" ]; then b=generic; else b=""; fi ;;
      *) b="" ;;
    esac
  fi
  case "$b" in
    claude|codex|cursor|generic) printf '%s\n' "$b" ;;
  esac
}

# calamus_load_config <root> <host>
# Precedence: environment, project file, user file, backend profile, defaults.
calamus_load_config() {
  local root="$1" host="$2" shipped="$CALAMUS_SKILL_DIR/assets/calamus.env"
  local user="${XDG_CONFIG_HOME:-$HOME/.config}/calamus/calamus.env"
  _calamus_read_file "$root/.calamus/calamus.env" project
  _calamus_read_file "$user" user
  _calamus_read_file "$shipped" shipped CALAMUS_BACKEND
  CALAMUS_BACKEND_RESOLVED="$(calamus_resolve_backend "$host")"
  export CALAMUS_BACKEND_RESOLVED
  if [ -n "$CALAMUS_BACKEND_RESOLVED" ]; then
    _calamus_read_file "$CALAMUS_SKILL_DIR/assets/profiles/$CALAMUS_BACKEND_RESOLVED.env" shipped
  fi
  _calamus_read_file "$shipped" shipped
}
