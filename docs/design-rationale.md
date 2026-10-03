# Calamus — Design Rationale

> Why Calamus is built the way it is. Agents never load this file; the
> skill itself is `skills/calamus/`. The full design spec is
> `docs/superpowers/specs/2026-09-26-calamus-design.md`.

Calamus keeps two append-only journals — engineering decisions and product
insights — as live project memory for agent sessions. It has three layers:

| Layer | Where | Loaded |
|---|---|---|
| Skill | `SKILL.md` (router) + `references/` | Router on activation; one reference per journal written |
| Engine | `scripts/hook.sh`, `scripts/lib/`, `scripts/backends/`, `assets/hosts/` | Never in the working agent's context; runs as lifecycle hooks |
| Adapter | `assets/adapter.md` | Every session, so it stays under 15 lines |

---

## Eval Stack

| Level | What it measures | Runs |
|---|---|---|
| 1 — Capture gate | Structural validity of every capture (free), plus a model-judged 4-of-8 check | Automatic on sweep captures; model judge sampled 1 in `CALAMUS_LEVEL1_SAMPLE` by default |
| 2 — Rubric scorer | 5-dimension analytic score on the last N entries | Manual: `skills/calamus/evals/eval-score.sh` |
| 3 — Drift detection | Trend across session scores | Not implemented |
| 4 — Behavioral evals | Checkpoint detection and classification against a golden set | Planned — `skills/calamus/evals/level-4-plan.md` |

Level 1's structural check is the schema validator: a capture that does not
validate is never written. The model-judged check fails closed — only an
exact `YES` passes; a judge that cannot run is logged as `unjudged`, never
as a pass. A `NO` appends an `EVAL-FAIL` marker naming the backend and model.

Level 2 judges entries in their Markdown rendering whatever the journal
format, so scores stay comparable across `md`, `xml`, and `jsonl`. The
report header records the backend and model; scores are comparable only
across runs with the same pair.

These evals are measurement, not ground truth: the judge shares a model
family with the capture backend, and the rubric has not been calibrated
against human labels. The Level 4 golden set is what would change that.

---

## Design Decisions and Why

### Why strip citations from SKILL.md?

SKILL.md files load on every activation under the Agent Skills progressive
disclosure model. Research bibliography content burns context budget and the
agent doesn't need it to do the job. Citations live here and in the
repo-level README. The SKILL.md contains only procedural instructions.

Research basis: *Knowledge Activation: AI Skills as the Institutional
Knowledge Primitive* (2026) documents the three constraints defining the
context window economy — token budget, attention decay, and latency cost.
Every token in the SKILL.md that isn't procedural instruction is waste.

### Why hooks instead of prompt-level journaling?

Prompt-level journaling ("after each feature, write a journal entry") costs
context budget on every turn and competes with engineering work for attention.
Near context limits — exactly when journaling matters most — the model's
adherence to such instructions degrades. Hooks are deterministic shell
commands. They fire on every qualifying lifecycle event with zero context cost.

Research basis: *Claude Code Compaction Kept Destroying My Work* (DEV, 2026)
and *PreCompact and PostCompact Hooks* (Developers Digest, 2026) document
patterns for reliable state persistence across the compaction boundary.

### Why two journals instead of one?

Engineering decisions and product decisions answer different questions for
different audiences. Merging them into one file produces entries that are
too technical for product retrospectives and too vague for engineering
post-mortems. The `[CROSS-LOG]` marker connects entries that span both without
duplicating content across files.

Research basis: *Feature Documentation Research* (arXiv:2208.01317) finds
that product-feature knowledge in GitHub projects is often fragmented and
weakly linked to implementation context — a dual-journal system with explicit
cross-referencing addresses this directly.

### Why LLM-as-judge for evals?

Human review of journal entries doesn't scale across sessions. Code-based
evals can check structure but miss semantic quality — whether a decision was
actually explained, whether reasoning was present, whether evidence was
cited. LLM-as-judge applies a written rubric consistently across all entries.

Research basis: *Rubric-Based Evals & LLM-as-a-Judge* (Medium, 2026)
establishes that analytic rubrics (criterion-by-criterion scoring) enable
regression root-cause analysis in a way that holistic single-score approaches
cannot. *Arize AI — LLM as a Judge Primer* (2026) documents the pattern.

### Why Lightweight schema as a first-class option?

The full entry schema requires nine sections and non-trivial reasoning. At the
end of a long session when the model's context is most compressed, requiring
the full schema produces either forced entries or no entry at all. The
Lightweight schema (five fields) is good enough to reconstruct the engineering
story and can be completed reliably even in compressed contexts.

Research basis: *Lost in the Middle* (Liu et al., 2023) demonstrates U-shaped
positional attention bias — model attention to instructions degrades in long
contexts. *Context Rot* (Chroma, 2025) confirms every frontier model degrades
as context fills. Lightweight schema is the graceful degradation path.

### Why PreCompact for Claude Code but not mid-session prompting?

For the long-session Claude Code usage pattern, the only real gap in
SessionEnd-only coverage is context compaction — the model's context is
erased and SessionEnd doesn't fire until the session actually terminates.
PreCompact fires synchronously before every compaction and can write a
snapshot entry. This closes the gap without any mid-session prompt overhead.

Research basis: *Claude Code Compaction and Long-Session Operations Guide*
(Konishi, 2026) documents PreCompact as the correct hook point for
state-preservation before compaction, with the matcher distinguishing manual
(`/compact`) from automatic (context pressure) triggers.

### Why growth-gated `Stop` for Codex and Cursor?

Codex has no `TaskCompleted` event (its hooks documentation lists
`SessionStart`, `SessionEnd`, `PreToolUse`, `PostToolUse`,
`PermissionRequest`, `PreCompact`, `PostCompact`, `UserPromptSubmit`,
`SubagentStart`, `SubagentStop`, `Stop`, and `Interrupt`), so the old
per-task mode was dead code. Codex and Cursor also give `SessionEnd` a
budget of a few seconds — too short for a model call. So they capture at
turn boundaries instead: `Stop` runs a sweep only once at least
`CALAMUS_MIN_TEXT` characters of new, extracted text have accumulated since
the last sweep, which amortizes the fixed per-call overhead. Their
`SessionEnd` only leaves a pending marker for the skill to resolve.

### Why one engine with host flags instead of per-host scripts?

The previous hooks duplicated payload parsing, journal creation, and the
Level 1 gate across four scripts, and hardcoded model names in each.
`hook.sh --host <h> --event <e>` normalizes each host's payload into the
same fields and runs one pipeline. Hosts differ only in registration
templates and payload field names.

### Why one skill with per-host packages instead of per-host skills?

Claude Code, Codex, and Cursor differ in how hooks register, how long
`SessionEnd` may run, which hooks need trust review, and how a skill is
installed. They do not differ in what a good journal entry is or when to
write one. Separate skills per host would fork `SKILL.md` and `references/`
over differences that live outside them, and every procedure fix would
need three edits. So there is one canonical skill, and `packaging/<host>/`
adds only what each host needs to load it: a plugin manifest and a hooks
file built from `assets/hosts/<host>/hooks.json`. Each package links to the
canonical skill rather than copying it, and a layout test fails if a
package's hooks drift from the template or its skill differs from the
source. Per-host descriptions stay out until the activation experiment
shows they earn at least 10 points of recall or 5 of precision.

### Why no package generator yet?

Three hand-written packages are small: a manifest and a hooks file each.
The layout test already catches the one failure a generator would prevent,
a package whose hooks no longer match the host template. A build step adds
a tool to maintain and a regenerate-then-diff CI check. It becomes worth
that cost when two or more packages drift from `assets/hosts/` in review.

### Why is the model configuration, not code?

Every model string lives in `assets/calamus.env`. A backend never falls
back to another backend or model: an unavailable backend means a pending
marker for capture and a clear error for scoring. Silent substitution
would make eval scores incomparable without anyone noticing.

### Why a schema, and why do backends return JSON?

One schema drives validation, three renderers (`md`, `xml`, `jsonl`), the
parser, the prompt's field list, and the templates in the references, so
none of them can drift. Backends return JSON fields and code renders them,
which removes escaping errors and lets one prompt and one eval baseline
serve every format. Model-optimized formats do not make entries smaller;
they save tokens through recall by query instead of whole-file reads.

### Why extract transcripts before sending them?

The old hooks resent a raw 28 KB transcript tail on every qualifying event,
full of tool output and reasoning blocks. The extractor keeps user and
assistant text, one-line tool summaries, and the start of each tool result,
and sends only text added since the last sweep. If extraction fails or
returns nothing, the raw tail is sent instead, so extraction can never stop
a capture.

---

## Extending Calamus

To support another host:

1. Add its payload field names to `scripts/lib/payload.sh`.
2. Add a registration template in `assets/hosts/<host>/hooks.json`.
3. Until then, any runtime that can shell out can use `--host generic`,
   passing `session_id`, `cwd`, and `transcript_path` as JSON on stdin or
   as `CALAMUS_SESSION_ID`, `CALAMUS_CWD`, and `CALAMUS_TRANSCRIPT`.

To support another model, point the `generic` backend at it with
`CALAMUS_LLM_CMD` (environment or user-level config only).
