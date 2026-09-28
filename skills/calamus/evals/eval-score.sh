#!/usr/bin/env bash
# evals/eval-score.sh
# Level 2 — On-demand rubric scorer for dev_journal.md entries.
#
# Reads the N most recent journal entries (default: last 10), scores each
# on the five-dimension rubric, and writes a scorecard to
# docs/eval_report.md. Also prints a summary to stdout.
#
# Usage:
#   ./evals/eval-score.sh              # Score last 10 entries
#   ./evals/eval-score.sh 20           # Score last 20 entries
#   ./evals/eval-score.sh --all        # Score entire journal
#
# Model: claude-haiku-4-5 (cheap; ~500–800 tokens per batch of 10)
# Rubric: evals/rubric.md (five dimensions, 1–3 scale, pass threshold 2.0)

set -euo pipefail

# ── Args ─────────────────────────────────────────────────────────────────────
ENTRY_COUNT="${1:-10}"
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
DEV_JOURNAL="$GIT_ROOT/docs/dev_journal.md"
RUBRIC="$GIT_ROOT/evals/rubric.md"
EVAL_REPORT="$GIT_ROOT/docs/eval_report.md"

if [ ! -f "$DEV_JOURNAL" ]; then
  echo "No dev_journal.md found at $DEV_JOURNAL"
  exit 1
fi

if [ ! -f "$RUBRIC" ]; then
  # Fall back to relative path from script location
  RUBRIC="$(dirname "$0")/rubric.md"
fi

RUBRIC_CONTENT=$(cat "$RUBRIC" 2>/dev/null || echo "")

# ── Extract entries ───────────────────────────────────────────────────────────
if [ "$ENTRY_COUNT" = "--all" ]; then
  ENTRIES=$(grep -A 50 "^### \[CP" "$DEV_JOURNAL" | head -c 40000 || echo "")
  LABEL="all entries"
else
  # Extract last N entries by finding ### [ markers and taking the last N blocks
  ENTRIES=$(python3 - "$DEV_JOURNAL" "$ENTRY_COUNT" << 'PYEOF'
import sys, re

journal_path = sys.argv[1]
n = int(sys.argv[2])

with open(journal_path, 'r') as f:
    content = f.read()

# Split on checkpoint headers
blocks = re.split(r'(?=^### \[CP)', content, flags=re.MULTILINE)
# Filter to only checkpoint blocks
cp_blocks = [b for b in blocks if b.strip().startswith('### [CP')]
# Take last N
recent = cp_blocks[-n:] if len(cp_blocks) >= n else cp_blocks

print('\n---\n'.join(recent))
PYEOF
)
  LABEL="last $ENTRY_COUNT entries"
fi

if [ -z "$ENTRIES" ]; then
  echo "No [CP-*] entries found in $DEV_JOURNAL"
  exit 0
fi

echo "Scoring $LABEL from $DEV_JOURNAL..."
echo "Model: claude-haiku-4-5 | Rubric: 5 dimensions, 1–3 scale"
echo ""

# ── Build eval prompt ─────────────────────────────────────────────────────────
EVAL_PROMPT="You are an engineering journal quality evaluator.

Score each journal entry below on five dimensions using the rubric provided.
For each entry, output a JSON object with this exact structure:
{
  \"entry_title\": \"[the ### header line]\",
  \"scores\": {
    \"decision_specificity\": <1|2|3>,
    \"reasoning_quality\": <1|2|3>,
    \"evidence_verification\": <1|2|3>,
    \"scope_identification\": <1|2|3>,
    \"followup_signal\": <1|2|3>
  },
  \"average\": <float>,
  \"pass\": <true|false>,
  \"notes\": \"[one sentence: what would improve the weakest dimension]\"
}

Output a JSON array of these objects. Output ONLY valid JSON, no markdown fences,
no preamble. Passing threshold: average >= 2.0.

RUBRIC:
$RUBRIC_CONTENT

ENTRIES TO SCORE:
$ENTRIES"

SCORE_OUTPUT=$(echo "$EVAL_PROMPT" | \
  claude --print --safe-mode --tools "" --model claude-haiku-4-5 2>/dev/null || echo "[]")

# ── Parse and display results ─────────────────────────────────────────────────
python3 - "$SCORE_OUTPUT" "$EVAL_REPORT" "$LABEL" << 'PYEOF'
import sys, json, re
from datetime import datetime

raw = sys.argv[1]
report_path = sys.argv[2]
label = sys.argv[3]

# Models sometimes wrap JSON in markdown fences despite instructions not to.
raw = raw.strip()
raw = re.sub(r'^```(?:json)?\s*', '', raw)
raw = re.sub(r'\s*```$', '', raw)

try:
    results = json.loads(raw)
except json.JSONDecodeError:
    print("Could not parse eval output as JSON. Raw output:")
    print(raw[:500])
    sys.exit(1)

if not results:
    print("No results returned.")
    sys.exit(0)

# ── Console output ───────────────────────────────────────────────────────────
passes = sum(1 for r in results if r.get('pass', False))
total = len(results)
avg_scores = {}
for dim in ['decision_specificity','reasoning_quality','evidence_verification',
            'scope_identification','followup_signal']:
    vals = [r['scores'][dim] for r in results if dim in r.get('scores', {})]
    avg_scores[dim] = round(sum(vals)/len(vals), 2) if vals else 0

print(f"{'='*60}")
print(f"EVAL REPORT — {label}")
print(f"Scored: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'='*60}")
print(f"Pass rate:  {passes}/{total} ({int(passes/total*100)}%)")
print(f"")
print("Dimension averages:")
dim_labels = {
    'decision_specificity': 'Decision Specificity',
    'reasoning_quality':    'Reasoning Quality   ',
    'evidence_verification':'Evidence/Verify     ',
    'scope_identification': 'Scope Identification',
    'followup_signal':      'Follow-up Signal    ',
}
for dim, label_str in dim_labels.items():
    score = avg_scores.get(dim, 0)
    bar = '█' * int(score * 10) + '░' * (30 - int(score * 10))
    print(f"  {label_str}: {score:.2f} {bar}")
print()

for r in results:
    status = '✓' if r.get('pass') else '✗'
    avg = r.get('average', 0)
    title = r.get('entry_title', 'Unknown')[:60]
    notes = r.get('notes', '')
    print(f"{status} {avg:.1f} | {title}")
    if not r.get('pass'):
        print(f"       → {notes}")

print(f"{'='*60}")

# ── Write eval_report.md ─────────────────────────────────────────────────────
now = datetime.now().strftime('%Y-%m-%d %H:%M')
report_lines = [
    f"# Journal Eval Report",
    f"> Generated: {now} | Scope: {label}",
    f"> Model: claude-haiku-4-5 | Rubric: 5 dimensions, 1–3 scale, pass ≥ 2.0",
    f"",
    f"## Summary",
    f"",
    f"| Metric | Value |",
    f"|---|---|",
    f"| Entries scored | {total} |",
    f"| Pass rate | {passes}/{total} ({int(passes/total*100)}%) |",
]
for dim, label_str in dim_labels.items():
    report_lines.append(f"| {label_str.strip()} avg | {avg_scores.get(dim,0):.2f} / 3.0 |")

report_lines += [
    "",
    "## Entry Scores",
    "",
]
for r in results:
    status = '✅' if r.get('pass') else '❌'
    avg = r.get('average', 0)
    title = r.get('entry_title', 'Unknown')
    s = r.get('scores', {})
    report_lines += [
        f"### {status} {avg:.1f}/3.0 — {title}",
        f"",
        f"| Dimension | Score |",
        f"|---|---|",
        f"| Decision Specificity | {s.get('decision_specificity','?')} |",
        f"| Reasoning Quality | {s.get('reasoning_quality','?')} |",
        f"| Evidence/Verification | {s.get('evidence_verification','?')} |",
        f"| Scope Identification | {s.get('scope_identification','?')} |",
        f"| Follow-up Signal | {s.get('followup_signal','?')} |",
        f"",
    ]
    if not r.get('pass'):
        report_lines.append(f"**Improvement note:** {r.get('notes','')}")
        report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

report_lines += [
    "## Weakest Dimension This Run",
    "",
]
worst_dim = min(avg_scores.items(), key=lambda x: x[1])
report_lines.append(
    f"**{dim_labels[worst_dim[0]].strip()}** averaged {worst_dim[1]:.2f}. "
    f"Focus improvement here first."
)
report_lines.append("")

with open(report_path, 'w') as f:
    f.write('\n'.join(report_lines))

print(f"\nReport written to: {report_path}")
PYEOF
