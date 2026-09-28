#!/usr/bin/env bash
# Layout and pin-location checks.
. "$(dirname "$0")/lib.sh"

for f in references/engineering-journal.md references/product-insights.md \
  evals/rubric.md evals/eval-score.sh evals/level-4-plan.md \
  assets/examples/example-entries.md scripts/calamus-init; do
  assert_file "$SKILL_DIR/$f" "moved file"
done
assert_file "$REPO_ROOT/docs/design-rationale.md" "design rationale"

# Model strings may appear only in assets/calamus.env (spec goal 4).
offenders="$(grep -rlE 'haiku|gpt-5|sonnet|opus' "$SKILL_DIR" 2>/dev/null \
  | sed "s|$SKILL_DIR/||" | grep -v '^assets/calamus.env$' \
  | sort | tr '\n' ' ')"
assert_eq "" "$offenders" "model strings outside assets/calamus.env"

finish
