# Level 4 — Behavioral Evals: Stretch Goal Plan

> Status: Planned. Levels 1 and 2 are implemented. This document specifies
> the Level 4 design for future implementation.
>
> What this demonstrates to recruiters and interviewers: end-to-end eval
> design thinking — golden dataset construction, rubric-grounded LLM-as-judge,
> regression testing on skill changes, and the ability to measure agent
> behavior at the step level, not just output quality.

---

## What Level 4 Is and Why It's Different

Levels 1 and 2 evaluate **journal output quality** — did the entries that
were written score well against the rubric? Level 4 evaluates **skill
behavior** — does the engineering-journal skill correctly identify and
classify checkpoints in the first place?

The distinction matters. A skill can produce high-quality entries on the
moments it decides to capture, while systematically missing an entire
category of checkpoint (e.g., always writing `[CP-MILESTONE]` and never
`[CP-CONSTRAINT]`). Level 2 wouldn't catch this. Level 4 would.

This is the same distinction between agent tracing (what happened) and
agent evaluation (whether the right decisions were made). Level 4 is
proper agent evaluation.

---

## Architecture

```
golden/
├── transcripts/          ← raw session transcripts (anonymized, ~15 examples)
│   ├── t01-auth-refactor.jsonl
│   ├── t02-api-rate-limit-discovery.jsonl
│   ├── t03-debug-session.jsonl
│   └── ...
├── labels/               ← hand-labeled expected outputs for each transcript
│   ├── t01-expected.md
│   ├── t02-expected.md
│   └── ...
└── golden-index.md       ← dataset manifest with checkpoint type distribution
```

```
evals/
├── eval-behavioral.sh    ← runs the skill against each transcript, scores output
└── eval-behavioral-report.md  ← generated on each run
```

---

## Golden Dataset Design

### Size target

15 transcripts, representing at least one example of each checkpoint type:

| Checkpoint type | Target examples |
|---|---|
| `[CP-ARCHITECTURE]` | 3 |
| `[CP-PIVOT]` | 2 |
| `[CP-REFACTOR]` | 2 |
| `[CP-MILESTONE]` | 2 |
| `[CP-CONSTRAINT]` | 2 |
| `[CP-DEBUG]` | 2 |
| `[CP-TESTING]` | 1 |
| `[CP-INTEGRATION]` | 1 |

Also include 3 "no checkpoint" transcripts — sessions where the correct
behavior is to write NO_CHECKPOINT (trivial edits, short Q&A).

### Labeling protocol

For each transcript, the hand-labeled expected output specifies:

1. **Should journal?** Yes / No
2. **Checkpoint type(s):** Which CP tags are expected
3. **Required content:** What the entry must mention (key decision, key
   files, key trade-off) — described as assertions, not exact text
4. **Forbidden content:** What the entry must NOT contain (fabricated
   details, hallucinated file names, invented API names)

Example label format:

```markdown
## t02-expected: API Rate Limit Discovery

**Should journal:** Yes
**Expected tag:** [CP-CONSTRAINT]

**Required assertions (entry must address all):**
- [ ] Names the specific rate limit (100 req/min or similar)
- [ ] Identifies which service imposed the limit
- [ ] States the workaround or design change made
- [ ] Names at least one affected file or component

**Forbidden content:**
- Do not invent a specific error code not in the transcript
- Do not claim the limit was resolved if the transcript shows it wasn't

**Acceptable evidence statements:**
- "Observed in load test" or "hit in production testing" or similar
```

---

## Evaluation Methodology

### Step 1: Run the skill against each transcript

Feed each transcript to the skill (via a `claude --print` call with the
skill's journal-capture prompt) and collect the output.

### Step 2: Score with LLM-as-judge

Use a judge model (pinned to a specific version to prevent temporal drift)
to evaluate each output against its label. The judge checks:

1. **Detection accuracy** — Did the skill correctly decide to journal or
   not journal?
2. **Tag accuracy** — Is the checkpoint type correct?
3. **Assertion coverage** — Does the entry satisfy all required assertions
   from the label?
4. **Hallucination check** — Does the entry contain anything forbidden?

Score each dimension 0 or 1 (pass/fail, not 1–3, because these are binary
correctness checks against ground truth).

### Step 3: Aggregate

Report:
- **Detection F1** — precision and recall on the journal/no-journal decision
- **Tag accuracy** — % of entries with correct CP tag
- **Assertion coverage** — average % of required assertions satisfied
- **Hallucination rate** — % of entries containing forbidden content

### Step 4: Regression gate

When `references/engineering-journal.md` is updated, re-run Level 4 evals.
If any metric drops more than 10 percentage points from the baseline, flag
the regression before committing the skill update.

---

## Judge Model Pinning

This is critical. As noted in the eval literature, a model provider quietly
updating the underlying LLM can change scoring without any alert. The judge
model must be pinned to a specific version in the eval config:

Pins live in `assets/calamus.env` with every other model string; Level 4
reads the judge and skill models from there (`CALAMUS_EVAL_BACKEND` and the
matching `CALAMUS_<BACKEND>_MODEL`) rather than defining its own. Use a
dated snapshot identifier, not an alias, for the Level 4 baseline.

When upgrading the judge model, re-score the entire golden set and update
the baseline before treating new scores as comparable to old ones.

---

## Implementation Estimate

| Task | Effort |
|---|---|
| Collect and anonymize 15 transcripts | 2–3 hours |
| Write labels for each transcript | 3–4 hours |
| Write `eval-behavioral.sh` | 2–3 hours |
| Baseline run and document results | 1 hour |
| **Total** | **~8–10 hours** |

---

## Why This Is Worth Building (Recruiting Signal)

The complete eval stack (Levels 1–4) demonstrates:

- **Level 1:** You know that agent output needs quality gates, not just
  prompt engineering. Passive, cheap, automatic.
- **Level 2:** You know how to design analytic rubrics and apply them via
  LLM-as-judge — a core skill in applied AI PM and engineering roles.
- **Level 3 (stretch):** You understand eval drift and longitudinal quality
  tracking as a system, not just a one-time check.
- **Level 4:** You can design golden datasets, specify behavioral assertions,
  build regression gates, and think about agent evaluation at the step level
  vs. output level. This is the eval literacy that separates PM candidates
  who understand agentic systems from those who don't.

For defense and government tech APM roles specifically, the rigor implied by
Level 4 — specifying what an agent must and must not output, regression
testing behavioral changes — maps directly to the kind of validation thinking
those domains require before deploying automated systems.
