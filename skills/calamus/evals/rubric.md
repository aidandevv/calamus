# Engineering Journal — Eval Rubric
# Used by eval-score.sh (Level 2) and the Level 4 golden-set evaluation.
# Each dimension is scored 1–3. Passing threshold: average ≥ 2.0.
#
# Research basis:
#   Analytic rubrics score criterion-by-criterion rather than a single
#   opaque score, enabling regression root-cause analysis when quality
#   shifts across sessions or after skill updates.
#   Source: Rubric-Based Evals & LLM-as-a-Judge (Medium, 2026)
#
#   LLM-as-judge applies a written rubric consistently across entries,
#   replacing human review bottlenecks at scale.
#   Source: Arize AI — LLM as a Judge Primer (2026)

---

## Dimension 1: Decision Specificity

Does the entry clearly state WHAT decision was made?

- **3 — Specific:** Names a concrete choice (library, pattern, architecture,
  approach). A reader unfamiliar with the session would know exactly what
  was selected.
- **2 — Partial:** A decision is implied but vague ("we changed the approach"
  without specifying what).
- **1 — Missing:** No clear decision stated. Entry reads as a summary of
  activity rather than a decision record.

---

## Dimension 2: Reasoning Quality

Does the entry explain WHY this decision was made?

- **3 — Justified:** States technical reason, constraint, trade-off, or
  product requirement that drove the choice. Alternatives considered or
  explicitly noted as not evaluated.
- **2 — Partial:** Some reasoning present but incomplete. "We chose X because
  it was simpler" without explaining simpler than what or why simplicity
  mattered here.
- **1 — Missing:** No reasoning. Entry states outcome only.

---

## Dimension 3: Evidence / Verification

Does the entry include evidence that the decision worked?

- **3 — Verified:** Cites test output, build result, manual walkthrough,
  observed behavior, log output, or other concrete verification. Or
  explicitly states "Not yet verified" as a deliberate note.
- **2 — Implied:** Language suggests the implementation worked ("we
  successfully integrated...") without stating what evidence confirmed it.
- **1 — Absent:** No mention of verification. Reader cannot tell if this
  decision was validated.

---

## Dimension 4: Scope Identification

Does the entry name affected files, modules, components, or systems?

- **3 — Named:** Specific files, modules, functions, services, routes, or
  schemas listed.
- **2 — Partial:** Mentions an area ("the auth layer") without specific
  files or components.
- **1 — Missing:** No scope information. Cannot reconstruct what was touched.

---

## Dimension 5: Follow-up Signal

Does the entry capture what remains open or what to do next?

- **3 — Actionable:** Names specific open questions, risks, deferred items,
  or next steps. Another engineer could act on this.
- **2 — Present but vague:** Acknowledges something is open without
  specifying what. "More work needed here."
- **1 — Missing:** No follow-ups or "None identified." (Note: "None
  identified." is valid and scores 3 if the entry is clearly complete.)

---

## Scoring

| Average | Interpretation |
|---|---|
| 2.6 – 3.0 | High quality — entry will serve well in post-mortems and write-ups |
| 2.0 – 2.5 | Acceptable — usable but missing some detail worth adding |
| 1.5 – 1.9 | Weak — entry captures activity but not decision reasoning |
| 1.0 – 1.4 | Fail — entry does not meet the journal's purpose |

Failing entries (average < 2.0) should be flagged for manual review.
The eval-score.sh script appends scores as HTML comments in the journal.
