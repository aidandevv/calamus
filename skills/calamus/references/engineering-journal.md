---
name: engineering-journal
description: >-
  Maintain a running engineering development journal. Use when implementing
  architecture, pivoting on an approach, completing a feature, fixing a
  non-obvious bug, integrating systems, discovering constraints, or making
  any engineering decision worth explaining later. Appends entries to
  ./docs/dev_journal.md. Evaluates at end of every meaningful dev interaction.
---

# Engineering Journal — Skill Instructions

A model-agnostic agent instruction for maintaining a chronological engineering
journal across agentic coding sessions. Works with Claude Code, Codex CLI,
Cursor, Gemini CLI, and any Agent Skills-compatible runtime.

Design rationale, research citations, and version history live in
`../../README.md` (skill-level) and the repo-level `README.md`. This file
contains only what the agent needs to do the job.

---

## Core Objective

Maintain `./docs/dev_journal.md` — a chronological, technically precise log of
engineering decisions, implementation pivots, debugging lessons, constraint
discoveries, and milestone completions. Write entries that will still be useful
six months from now to a reader who was not present.

If the environment supports file writes, append directly. If not, output the
exact Markdown inside a copyable code fence and tell the user to append it.

Do not overwrite existing content. Do not fabricate details.

---

## Initialization

If `./docs/dev_journal.md` does not exist:

```bash
mkdir -p docs
cat > docs/dev_journal.md << 'EOF'
# Engineering Development Journal
> Chronological log of architecture decisions, implementation pivots,
> constraint discoveries, verification results, and engineering milestones.

---
EOF
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
| `[CP-COMPACT-SNAPSHOT]` | Auto-written by PreCompact hook before context compaction |

If multiple types apply, choose the one that best captures the main story.

---

## Compaction Awareness

Do not manually log before running `/compact`. The `PreCompact` hook handles
this automatically — it fires before every compaction (manual or auto) and
writes a `[CP-COMPACT-SNAPSHOT]` entry capturing current progress. After
compaction, the `PostCompact` hook appends a resume marker so the next context
window knows where to pick up.

If hooks are not installed, add a note manually before compacting:

```markdown
### [CP-COMPACT-SNAPSHOT] | YYYY-MM-DD: Pre-compaction state
**Summary:** [What we are in the middle of.]
**Files in progress:** [List.]
**Next step:** [What to do immediately after compaction.]
---
```

---

## Cross-Log Coordination

| Observation type | Target file |
|---|---|
| Architecture, implementation, debugging, testing, constraints, refactors, integrations | `dev_journal.md` |
| User pain, UX friction, activation, retention, positioning, product hypotheses, roadmap | `product_insights.md` |
| Both — technical constraint that directly changes user experience | **Both files** |

When writing to both, add a `[CROSS-LOG]` marker in each entry:

```markdown
> **[CROSS-LOG]** Product impact logged in `./docs/product_insights.md`
> — see [PI-UX-FRICTION] | YYYY-MM-DD: [title].
```

---

## Lightweight Entry Schema

Use this when the observation is real but small, or when writing in a
compressed context near session end. Prefer this over silence.

```markdown
### [TAG] | YYYY-MM-DD: [Short Title]

**Summary:** [1–2 sentences: decision made and why.]

**Files/Modules Affected:** [List or `None identified.`]

**Key Trade-off:** [What was accepted or rejected and why.]

**Evidence:** [How we know this worked, or `Not yet verified.`]

**Follow-ups:** [Open questions, or `None identified.`]

---
```

---

## Full Entry Schema

Use for decisions that materially affect architecture, major milestones,
non-obvious bugs, or anything you would explain in a post-mortem.

```markdown
### [TAG] | YYYY-MM-DD: [Descriptive Component/Feature Name]

**The Context & Problem:**
- [Concrete technical goal, implementation problem, or architectural question.]

**Design Decisions & Trade-offs:**
- **Choice:** [The specific design, library, pattern, or workflow selected.]
- **Alternatives Considered:** [Serious alternatives, or state none were evaluated.]
- **Why:** [Technical justification, constraints weighed, performance implications.]

**The Pivot/Revision:**
- [What changed during implementation. If the plan held, state why.]

**Implementation Notes:**
- **Files/Modules Affected:** [Relevant files, modules, functions, components.]
- **Core Pattern Introduced:** [The implementation pattern or architectural mechanism.]

**Verification & Evidence:**
- [Tests run, manual validation, logs, type checks, builds, API responses.
  If not verified, state explicitly.]

**Documentation & References Utilized:**
- [Only if references were consulted: `- [Name](URL) - Key takeaway`]

**Code Snapshot/Diff Concept:**
- [Pseudocode, diff concept, schema, or concise snippet capturing the key idea.]

**Cross-Log:**
- [Related product entry in product_insights.md, or `None.`]

**Open Questions / Follow-ups:**
- [Unresolved risks, deferred improvements, edge cases. If none: `None identified.`]

---
```

---

## Session Boundary Markers

Add this at the start of each new session's first entry to keep the flat
file navigable as it grows:

```markdown
<!-- SESSION: YYYY-MM-DD HH:MM | [brief context, e.g. "auth refactor"] -->
```

---

## Append Safety

- Always append. Never overwrite. Never delete previous entries unless
  explicitly asked.
- Before appending, check recent entries to avoid duplicating the same
  checkpoint, decision, and moment.
- If a prior decision changed, append a new entry explaining the revision.
  Do not rewrite history.
- Archive `dev_journal.md` to `dev_journal_archive_YYYY-MM.md` when it
  exceeds roughly 500 entries.

---

## File-Writing Behavior

**File access available:** Ensure `./docs/` and `./docs/dev_journal.md` exist,
append entry, preserve all existing content, confirm briefly.

**File access unavailable:** Output entry in a copyable code fence, tell the
user to append to `./docs/dev_journal.md`, do not claim the file was modified.

---

## Relationship to Product Insight Journal

Engineering decisions → `dev_journal.md`
Product decisions → `product_insights.md`
Both → separate entries with `[CROSS-LOG]` markers linking them.

Product insight skill: `../product-insight-journal/SKILL.md`

---

## Global Adapter (paste into CLAUDE.md / AGENTS.md)

```
Follow engineering-journal skill at:
  ~/.claude/skills/journaling/engineering-journal/SKILL.md

Maintain: ./docs/dev_journal.md

At the end of meaningful engineering work, evaluate whether a checkpoint
should be logged. Prefer Lightweight schema in long or compressed sessions.
Never overwrite. Never fabricate.
```
