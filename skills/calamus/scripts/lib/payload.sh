# Hook payload normalizer. Source this file; it defines functions only.

# calamus_payload <host> — reads the hook payload on stdin and sets
# CAL_SESSION, CAL_CWD, CAL_TRANSCRIPT. Missing or invalid JSON yields empty
# fields (session "unknown"), never an error.
calamus_payload() {
  local host="$1" raw fields
  raw="$(cat 2>/dev/null || true)"
  fields="$(CALAMUS_HOST="$host" CALAMUS_RAW="$raw" python3 - <<'PY' 2>/dev/null
import json, os, re

host = os.environ.get("CALAMUS_HOST", "")
try:
    d = json.loads(os.environ.get("CALAMUS_RAW", ""))
    if not isinstance(d, dict):
        d = {}
except ValueError:
    d = {}
env = os.environ.get


def s(v):
    return v if isinstance(v, str) else ""


def first(*vals):
    for v in vals:
        if s(v):
            return v
    return ""


if host == "cursor":
    roots = d.get("workspace_roots")
    root = roots[0] if isinstance(roots, list) and roots and isinstance(roots[0], str) else ""
    session = first(d.get("conversation_id"), d.get("session_id"))
    cwd = first(root, env("CURSOR_PROJECT_DIR"))
    transcript = first(d.get("transcript_path"), env("CURSOR_TRANSCRIPT_PATH"))
elif host == "generic":
    session = first(d.get("session_id"), env("CALAMUS_SESSION_ID"))
    cwd = first(d.get("cwd"), env("CALAMUS_CWD"))
    transcript = first(d.get("transcript_path"), env("CALAMUS_TRANSCRIPT"))
elif host == "claude-code":
    session = first(d.get("session_id"), d.get("conversation_id"))
    cwd = s(d.get("cwd"))
    transcript = s(d.get("transcript_path"))
else:
    session = s(d.get("session_id"))
    cwd = s(d.get("cwd"))
    transcript = s(d.get("transcript_path"))

session = re.sub(r"[^A-Za-z0-9._-]", "-", session)[:64] or "unknown"
clean = lambda v: v.replace("\n", " ").replace("\r", " ")
print(session)
print(clean(cwd))
print(clean(transcript))
PY
)"
  CAL_SESSION="unknown"; CAL_CWD=""; CAL_TRANSCRIPT=""
  if [ -n "$fields" ]; then
    { IFS= read -r CAL_SESSION; IFS= read -r CAL_CWD; IFS= read -r CAL_TRANSCRIPT; } <<EOF
$fields
EOF
  fi
  [ -n "$CAL_SESSION" ] || CAL_SESSION="unknown"
}
