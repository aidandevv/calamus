#!/usr/bin/env bash
# Calamus hook entry point.
#   hook.sh --host <claude-code|codex|cursor|generic> --event <pre-compact|post-compact|turn-stop|session-end>
# Reads the host's payload on stdin. Always exits 0 and prints nothing:
# a non-zero PreCompact exit can block compaction, and stdout may be parsed
# as host directives. All output goes to <root>/.calamus/logs/hook.log.

[ "${CALAMUS_ACTIVE:-}" = "1" ] && exit 0

CALAMUS_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CALAMUS_LIB_DIR="$CALAMUS_SKILL_DIR/scripts/lib"
export CALAMUS_SKILL_DIR CALAMUS_LIB_DIR

calamus_main() {
  local host="" event=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --host) host="${2:-}"; shift 2 ;;
      --event) event="${2:-}"; shift 2 ;;
      *) shift ;;
    esac
  done
  case "$host" in claude-code|codex|cursor|generic) ;; *) return 0 ;; esac
  case "$event" in pre-compact|post-compact|turn-stop|session-end) ;; *) return 0 ;; esac

  . "$CALAMUS_LIB_DIR/config.sh"
  . "$CALAMUS_LIB_DIR/payload.sh"
  . "$CALAMUS_LIB_DIR/gate.sh"
  calamus_payload "$host"

  local cwd="${CAL_CWD:-$PWD}" root
  [ -d "$cwd" ] || return 0
  root="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || (cd "$cwd" && pwd))"
  STATE="$root/.calamus/state"
  CALAMUS_LOG="$root/.calamus/logs/hook.log"
  mkdir -p "$STATE/pending" "$root/.calamus/logs" 2>/dev/null || return 0
  calamus_log() { printf '[%s] %s %s %s: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$host" "$event" "$CAL_SESSION" "$*" >> "$CALAMUS_LOG"; }

  calamus_load_config "$root" "$host"
  local backend="$CALAMUS_BACKEND_RESOLVED" session="$CAL_SESSION" transcript="$CAL_TRANSCRIPT"

  if [ "$event" = "post-compact" ]; then
    calamus_dedupe "$session" "$event" || { calamus_log "skip: duplicate"; return 0; }
    ls "$root"/docs/dev_journal.* >/dev/null 2>&1 || { calamus_log "skip: no journal"; return 0; }
    local snap
    snap="$(head -n 1 "$STATE/last-snapshot" 2>/dev/null)"
    python3 "$CALAMUS_LIB_DIR/capture.py" marker --root "$root" --kind resume \
      "when=$(date '+%Y-%m-%d %H:%M')" "session=$session" "snapshot=$snap" 2>>"$CALAMUS_LOG" \
      && calamus_log "resume marker written"
    return 0
  fi

  # Mode: snapshot (pre-compact), sweep, or stub.
  local mode kind min_bytes tail
  case "$event" in
    pre-compact) mode=snapshot ;;
    turn-stop) mode=sweep ;;
    session-end)
      mode="${CALAMUS_SESSION_END_MODE:-auto}"
      if [ "$mode" = "auto" ]; then
        case "$host" in codex|cursor) mode=stub ;; *) mode=sweep ;; esac
      fi
      case "$mode" in sweep|stub) ;; *) mode=sweep ;; esac ;;
  esac
  if [ "$mode" = "snapshot" ]; then
    kind=snapshot; min_bytes="${CALAMUS_MIN_BYTES_SNAPSHOT:-500}"; tail="${CALAMUS_TAIL_SNAPSHOT:-20000}"
  else
    kind=sweep; min_bytes="${CALAMUS_MIN_BYTES_SWEEP:-800}"; tail="${CALAMUS_TAIL_SWEEP:-28000}"
  fi

  if [ -z "$transcript" ] || [ ! -f "$transcript" ]; then
    calamus_log "skip: no transcript"
    return 0
  fi
  local size
  size="$(wc -c < "$transcript" | tr -d ' ')"
  if [ "$size" -lt "$min_bytes" ]; then
    calamus_log "skip: transcript ${size}B below ${min_bytes}B"
    return 0
  fi
  calamus_dedupe "$session" "$event" || { calamus_log "skip: duplicate within ${CALAMUS_DEDUPE_SECS}s"; return 0; }
  calamus_lock "$session" || { calamus_log "skip: another capture holds the session lock"; return 0; }

  CAL_TMP="$(mktemp -d "${TMPDIR:-/tmp}/calamus.XXXXXX")" || { calamus_unlock; return 0; }
  trap 'calamus_unlock; rm -rf "$CAL_TMP"' EXIT
  calamus_capture "$root" "$host" "$event" "$session" "$transcript" "$backend" "$mode" "$kind" "$tail" "$CAL_TMP"
  return 0
}

calamus_capture() {
  local root="$1" host="$2" event="$3" session="$4" transcript="$5" backend="$6" mode="$7" kind="$8" tail="$9" tmp="${10}"
  local offset_file="$STATE/offset-$session" start=0 eof chars rc

  if [ "$kind" = "sweep" ]; then
    start="$(cat "$offset_file" 2>/dev/null || echo 0)"
    case "$start" in ''|*[!0-9]*) start=0 ;; esac
  fi

  # Window: extracted text, falling back to the raw tail.
  eof=""
  if [ "${CALAMUS_EXTRACT:-on}" = "on" ] && python3 "$CALAMUS_LIB_DIR/timeout.py" 20 -- \
      python3 "$CALAMUS_LIB_DIR/extract.py" "$host" "$transcript" "$start" "${CALAMUS_RAW_WINDOW:-262144}" "$tail" \
      > "$tmp/extract.json" 2>>"$CALAMUS_LOG"; then
    eof="$(python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
open(sys.argv[2], "w").write(d["text"])
print(d["eof"])' "$tmp/extract.json" "$tmp/text" 2>>"$CALAMUS_LOG")"
  fi
  if [ -z "$eof" ] || { [ ! -s "$tmp/text" ] && [ "$(wc -c < "$transcript" | tr -d ' ')" -gt "$start" ]; }; then
    [ "${CALAMUS_EXTRACT:-on}" = "on" ] && calamus_log "extract-fallback: sending raw tail"
    eof="$(wc -c < "$transcript" | tr -d ' ')"
    [ "$start" -gt "$eof" ] && start=0
    local avail=$((eof - start))
    [ "$avail" -gt "$tail" ] && avail="$tail"
    tail -c "$avail" "$transcript" > "$tmp/text" 2>/dev/null
  fi
  chars="$(wc -m < "$tmp/text" | tr -d ' ')"

  if [ "$mode" = "stub" ]; then
    if [ "$chars" -ge "${CALAMUS_MIN_TEXT:-8000}" ]; then
      calamus_pending "$root" "$host" "$event" "$session" "$transcript"
    else
      calamus_log "skip: ${chars} new chars below stub threshold"
    fi
    return 0
  fi
  if [ "$event" = "turn-stop" ] && [ "$chars" -lt "${CALAMUS_MIN_TEXT:-8000}" ]; then
    calamus_log "skip: ${chars} new chars below ${CALAMUS_MIN_TEXT:-8000}"
    return 0
  fi
  if [ "$chars" -eq 0 ]; then
    calamus_log "skip: no new text"
    return 0
  fi

  python3 "$CALAMUS_LIB_DIR/capture.py" build "$kind" < "$tmp/text" > "$tmp/prompt" 2>>"$CALAMUS_LOG" || return 0

  if [ -z "$backend" ]; then
    calamus_log "backend: none resolved (set CALAMUS_BACKEND or CALAMUS_LLM_CMD)"
    calamus_failure "$root" "$host" "$event" "$session" "$transcript"
    return 0
  fi
  python3 "$CALAMUS_LIB_DIR/timeout.py" "${CALAMUS_BACKEND_TIMEOUT:-25}" -- \
    "$CALAMUS_SKILL_DIR/scripts/backends/$backend.sh" < "$tmp/prompt" > "$tmp/reply" 2>>"$CALAMUS_LOG"
  rc=$?
  if [ "$rc" -ne 0 ] || [ ! -s "$tmp/reply" ]; then
    calamus_log "backend $backend failed (exit $rc)"
    calamus_failure "$root" "$host" "$event" "$session" "$transcript"
    return 0
  fi

  python3 "$CALAMUS_LIB_DIR/capture.py" commit "$kind" --root "$root" --reply "$tmp/reply" \
    --session "$session" --host "$host" --event "$event" --state "$STATE" > "$tmp/ids" 2>>"$CALAMUS_LOG"
  rc=$?
  case "$rc" in
    0)
      calamus_log "wrote $(wc -l < "$tmp/ids" | tr -d ' ') entr(y/ies) via $backend"
      [ "$kind" = "sweep" ] && echo "$eof" > "$offset_file"
      [ "$kind" = "sweep" ] && calamus_level1 "$root" "$backend" "$tmp" ;;
    3)
      calamus_log "no checkpoint"
      [ "$kind" = "sweep" ] && echo "$eof" > "$offset_file" ;;
    4)
      calamus_log "backend $backend returned invalid output; saved under .calamus/state/rejected/"
      calamus_failure "$root" "$host" "$event" "$session" "$transcript" ;;
    *)
      calamus_log "journal write failed (exit $rc)" ;;
  esac
  return 0
}

# Failure path: turn-stop only logs (the offset stays, so the next event
# retries the same text); pre-compact and session-end leave a pending marker.
calamus_failure() {
  local root="$1" host="$2" event="$3" session="$4" transcript="$5"
  [ "$event" = "turn-stop" ] && return 0
  calamus_pending "$root" "$host" "$event" "$session" "$transcript"
}

calamus_pending() {
  local root="$1" host="$2" event="$3" session="$4" transcript="$5"
  printf '%s\n' "$transcript" > "$STATE/pending/$session"
  python3 "$CALAMUS_LIB_DIR/capture.py" marker --root "$root" --kind pending \
    "date=$(date '+%Y-%m-%d')" "session=$session" "host=$host" "event=$event" 2>>"$CALAMUS_LOG" \
    && calamus_log "pending marker written"
}

( calamus_main "$@" ) >/dev/null 2>&1 || true
exit 0
