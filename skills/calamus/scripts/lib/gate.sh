# Calamus gates. Source this file; it defines functions only.
# Expects: STATE (state dir), CALAMUS_LIB_DIR, calamus_log, and loaded config.

# calamus_dedupe <session> <event> — returns 1 if the same session and event
# ran within CALAMUS_DEDUPE_SECS; otherwise records this run and returns 0.
# The host is not part of the key, so a double registration runs once.
calamus_dedupe() {
  local f="$STATE/dedupe-$1-$2" now last
  now="$(date +%s)"
  last="$(cat "$f" 2>/dev/null || echo 0)"
  case "$last" in ''|*[!0-9]*) last=0 ;; esac
  if [ $((now - last)) -lt "${CALAMUS_DEDUPE_SECS:-30}" ]; then
    return 1
  fi
  echo "$now" > "$f"
  return 0
}

# calamus_lock <session> — takes the per-session lock or returns 1.
# A lock left by a crashed run is reclaimed after 10 minutes.
calamus_lock() {
  CALAMUS_LOCK="$STATE/lock-$1"
  if [ -d "$CALAMUS_LOCK" ] && [ -n "$(find "$CALAMUS_LOCK" -maxdepth 0 -mmin +10 2>/dev/null)" ]; then
    rmdir "$CALAMUS_LOCK" 2>/dev/null || true
  fi
  mkdir "$CALAMUS_LOCK" 2>/dev/null || { CALAMUS_LOCK=""; return 1; }
  return 0
}

calamus_unlock() {
  [ -n "${CALAMUS_LOCK:-}" ] && rmdir "$CALAMUS_LOCK" 2>/dev/null
  CALAMUS_LOCK=""
}

# calamus_model_name <backend> — the configured model string, for reports.
calamus_model_name() {
  case "$1" in
    claude) printf '%s' "${CALAMUS_CLAUDE_MODEL:-}" ;;
    codex) printf '%s' "${CALAMUS_CODEX_MODEL:-}" ;;
    cursor) printf '%s' "${CALAMUS_CURSOR_MODEL:-}" ;;
    *) printf 'custom' ;;
  esac
}

# calamus_should_judge — applies CALAMUS_LEVEL1_GATE and the sample counter.
calamus_should_judge() {
  local n c f="$STATE/gate-counter"
  case "${CALAMUS_LEVEL1_GATE:-sampled}" in
    full) return 0 ;;
    sampled)
      n="${CALAMUS_LEVEL1_SAMPLE:-4}"
      case "$n" in ''|*[!0-9]*|0) n=4 ;; esac
      c="$(cat "$f" 2>/dev/null || echo 0)"
      case "$c" in ''|*[!0-9]*) c=0 ;; esac
      c=$((c + 1))
      if [ "$c" -ge "$n" ]; then echo 0 > "$f"; return 0; fi
      echo "$c" > "$f"
      return 1 ;;
    *) return 1 ;;
  esac
}

# calamus_level1 <root> <backend> <tmpdir> — model-judged gate on the entries
# just written. Fails closed: only an exact YES passes; anything but YES/NO
# is logged as unjudged and never counted as a pass.
calamus_level1() {
  local root="$1" backend="$2" tmp="$3" verdict reason model
  calamus_should_judge || { calamus_log "level1: not sampled"; return 0; }
  python3 "$CALAMUS_LIB_DIR/capture.py" judge-prompt --state "$STATE" > "$tmp/judge-prompt" 2>/dev/null \
    || { calamus_log "level1: unjudged (no entries to judge)"; return 0; }
  if ! python3 "$CALAMUS_LIB_DIR/timeout.py" "${CALAMUS_BACKEND_TIMEOUT:-25}" -- \
      "$CALAMUS_SKILL_DIR/scripts/backends/$backend.sh" < "$tmp/judge-prompt" > "$tmp/judge-reply" 2>>"$CALAMUS_LOG"; then
    calamus_log "level1: unjudged (judge call failed)"
    return 0
  fi
  verdict="$(head -n 1 "$tmp/judge-reply" | tr -d '[:space:]')"
  model="$(calamus_model_name "$backend")"
  case "$verdict" in
    YES) calamus_log "level1: pass" ;;
    NO)
      reason="$(sed -n '2p' "$tmp/judge-reply" | tr -s '[:space:]' ' ')"
      [ -n "$reason" ] || reason="No reason given."
      python3 "$CALAMUS_LIB_DIR/capture.py" marker --root "$root" --kind eval-fail \
        "backend=$backend" "model=$model" "reason=$reason" 2>>"$CALAMUS_LOG"
      calamus_log "level1: EVAL-FAIL" ;;
    *) calamus_log "level1: unjudged (unparseable verdict)" ;;
  esac
}
