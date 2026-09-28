# Engineering Journal

Maintain `./docs/dev_journal.md` (or `.xml` / `.jsonl`) — a chronological,
technically precise log of engineering decisions, implementation pivots,
debugging lessons, constraint discoveries, and milestone completions. Write
entries that will still be useful six months from now to a reader who was not
present. Do not fabricate details.

---

## Journal Header

A new Markdown journal starts with:

```markdown
# Engineering Development Journal
> Chronological log of architecture decisions, implementation pivots,
> constraint discoveries, verification results, and engineering milestones.

---
```

---

## When to Write — Checkpoint Triggers

Write an entry when the session includes any of:

- New architecture, data model, service boundary, framework choice, or
  major abstraction introduced.
- Implementation pivot caused by a failed assumption, API limitation,
  performance issue, integration failure, or tool constraint.
- Refactor that changes structure, separation of concerns, maintainability,
  performance, or extensibility.
- Major feature, workflow, or integration that is implemented and verified.
- Non-obvious bug diagnosed and fixed.
- Testing or validation strategy that materially increases confidence.
- Security, privacy, reliability, cost, or operational constraint that
  shaped the design.
- Dependency or runtime decision that shapes the project.
- Any decision worth explaining in a post-mortem or portfolio write-up.

Do not write entries for trivial edits, cosmetic changes, typo fixes, or
implementation details that don't affect the engineering narrative.

**Noise gate — quality bar:** Before writing, verify the interaction answers
at least four of these eight:

1. What decision did we make?
2. Why did we make it?
3. What did we reject?
4. What constraint shaped the decision?
5. What changed during implementation?
6. What evidence showed the solution worked?
7. What files or components were affected?
8. What should we revisit later?

If fewer than four can be answered, use the Lightweight schema or ask the
user whether to wait.

---

## Checkpoint Types

| Tag | Use for |
|---|---|
| `[CP-ARCHITECTURE]` | System design, data modeling, service boundaries, framework choices |
| `[CP-PIVOT]` | Strategy change after a failed assumption or discovered constraint |
| `[CP-REFACTOR]` | Structural improvement to working code |
| `[CP-MILESTONE]` | Significant feature or integration implemented, tested, and verified |
| `[CP-CONSTRAINT]` | Discovered limitation: API, rate limits, deployment, auth, security, cost |
| `[CP-DEBUG]` | Non-obvious bug, root cause, and fix with a useful engineering lesson |
| `[CP-TESTING]` | Meaningful validation strategy, test harness, or verification result |
| `[CP-INTEGRATION]` | Boundary between systems, services, agents, databases, or APIs |
| `[CP-COMPACT-SNAPSHOT]` | Pre-compaction state; written by the hook, or manually when no hooks are installed |

If multiple types apply, choose the one that best captures the main story.

---

## Cross-Log Coordination

| Observation type | Target journal |
|---|---|
| Architecture, implementation, debugging, testing, constraints, refactors, integrations | engineering |
| User pain, UX friction, activation, retention, positioning, product hypotheses, roadmap | product |
| Both — technical constraint that directly changes user experience | **both**, linked by `[CROSS-LOG]` |

With `calamus-append`, link an entry with a `crosslog` object:
`{"journal": "product", "tag": "PI-UX-FRICTION", "date": "YYYY-MM-DD", "title": "...", "note": "Product impact"}`.
In Markdown it renders as the blockquote shown at the end of each template.

---

## Lightweight Entry Schema

Use this when the observation is real but small, or when writing in a
compressed context near session end. Prefer this over silence.

<!-- BEGIN GENERATED: eng-lightweight -->
```markdown
### [TAG] | YYYY-MM-DD: [Title]

**Summary:** [1-2 sentences: decision made and why]

**Files/Modules Affected:** `item`, `item` ... or `None identified.`

**Key Trade-off:** [What was accepted or rejected and why]

**Evidence:** [How we know this worked; status unverified if not yet verified] or `Not yet verified.`

**Follow-ups:** item; item ... or `None identified.`

> **[CROSS-LOG]** Product impact logged in `./docs/product_insights.md`
> — see [TAG] | YYYY-MM-DD: [title].

---
```
<!-- END GENERATED: eng-lightweight -->

---

## Full Entry Schema

Use for decisions that materially affect architecture, major milestones,
non-obvious bugs, or anything you would explain in a post-mortem.

<!-- BEGIN GENERATED: eng-full -->
````markdown
### [TAG] | YYYY-MM-DD: [Title]

**The Context & Problem:**
- [Concrete technical goal, problem, or question]

**Design Decisions & Trade-offs:**
- **Choice:** [The design, library, pattern, or workflow selected]
- **Alternatives Considered:** [Serious alternatives, or state none were evaluated]
- **Why:** [Technical justification and constraints weighed]

**The Pivot/Revision:**
- [What changed during implementation; if the plan held, why]

**Implementation Notes:**
- **Files/Modules Affected:** `item`, `item` ... or `None identified.`
- **Core Pattern Introduced:** [The implementation pattern or mechanism] (optional)

**Verification & Evidence:**
- [Tests, builds, logs, manual checks] or `Not yet verified.`

**Documentation & References Utilized:** (optional)
- [Only references actually consulted: [Name](URL) - takeaway]

**Code Snapshot/Diff Concept:** (optional)
```
[Pseudocode, diff concept, schema, or snippet]
```

**Cross-Log:**
- [Related product entry, if any] or `None.`

**Open Questions / Follow-ups:**
- [Unresolved risks, deferred work, edge cases] or `None identified.`

> **[CROSS-LOG]** Product impact logged in `./docs/product_insights.md`
> — see [TAG] | YYYY-MM-DD: [title].

---
````
<!-- END GENERATED: eng-full -->

---

## Compaction Snapshot

Written by the `pre-compact` hook. Without hooks, write one manually before
compacting.

<!-- BEGIN GENERATED: eng-snapshot -->
```markdown
### [CP-COMPACT-SNAPSHOT] | YYYY-MM-DD: Pre-compaction state — [Title]

**Summary:** [What is in progress, 1-2 sentences]

**Files in progress:** `item`, `item` ... or `None identified.`

**Decisions made this context window:**
- [Key choices, at most 3] or `None identified.`

**Immediate next step:** [Exactly what to do right after compaction]

**Open questions:**
- [Unresolved risks or blockers] or `None identified.`

> **[CROSS-LOG]** Product impact logged in `./docs/product_insights.md`
> — see [TAG] | YYYY-MM-DD: [title].

---
```
<!-- END GENERATED: eng-snapshot -->

---

## JSON Fields for `calamus-append`

`scripts/calamus-append --journal engineering` takes one object (or
`{"entries": [...]}`) with these fields. `journal` and `id` are filled in.
Empty lists render as the `None identified.`-style text shown above.

<!-- BEGIN GENERATED: eng-fields -->
```text
Lightweight:
- "variant": "lightweight"
- "tag": string, one of "CP-ARCHITECTURE" | "CP-PIVOT" | "CP-REFACTOR" | "CP-MILESTONE" | "CP-CONSTRAINT" | "CP-DEBUG" | "CP-TESTING" | "CP-INTEGRATION"
- "date": string, YYYY-MM-DD
- "title": string, short and specific
- "summary": string (required) — 1-2 sentences: decision made and why.
- "files": array of strings (may be empty, no backticks) — Files, modules, or components affected.
- "tradeoff": string (required) — What was accepted or rejected and why.
- "evidence": object {"status": "verified" | "unverified", "text": string} (required) — How we know this worked; status unverified if not yet verified.
- "followups": array of strings (may be empty, no semicolons inside an item) — Open questions.

Full:
- "variant": "full"
- "tag": string, one of "CP-ARCHITECTURE" | "CP-PIVOT" | "CP-REFACTOR" | "CP-MILESTONE" | "CP-CONSTRAINT" | "CP-DEBUG" | "CP-TESTING" | "CP-INTEGRATION"
- "date": string, YYYY-MM-DD
- "title": string, short and specific
- "context": array of strings (required) — Concrete technical goal, problem, or question.
- "design": object — Design Decisions & Trade-offs, with:
  - "choice": string (required) — The design, library, pattern, or workflow selected.
  - "alternatives": string (required) — Serious alternatives, or state none were evaluated.
  - "why": string (required) — Technical justification and constraints weighed.
- "pivot": array of strings (required) — What changed during implementation; if the plan held, why.
- "impl": object — Implementation Notes, with:
  - "files": array of strings (may be empty, no backticks) — Files, modules, functions, components.
  - "pattern": string (optional) — The implementation pattern or mechanism.
- "verification": array of strings (may be empty) — Tests, builds, logs, manual checks.
- "references": array of strings (optional) — Only references actually consulted: [Name](URL) - takeaway.
- "code": string (may span lines) (optional) — Pseudocode, diff concept, schema, or snippet.
- "crosslog_notes": array of strings (may be empty) — Related product entry, if any.
- "followups": array of strings (may be empty) — Unresolved risks, deferred work, edge cases.
```
<!-- END GENERATED: eng-fields -->

---

## Archiving

Archive the journal to `dev_journal_archive_YYYY-MM.md` (same extension as
the journal) when it exceeds roughly 500 entries.
