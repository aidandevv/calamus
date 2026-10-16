# Calamus Synthesis — Design Spec

> Status: draft for review. Date: 2026-10-15. Branch: `refactor/calamus`.
> Scope: a second skill, `calamus-synthesis` (name provisional), that reads
> the two Calamus journals and produces human-readable writeups, diagrams,
> and decision briefs. It never writes to the journals.

## 1. Goals and non-goals

**Goals**

1. Translate the model-oriented journals into documents a human can read
   cold: an overview, a phase and epoch history, a pivot analysis, a
   condensed decision log, an insights report, and a white-paper scaffold.
2. Identify structure the journals do not state: phases, epochs, and the
   pivots that separate them, from deterministic signals first and model
   judgment second.
3. Produce diagrams (timeline, phase flow, pivot flowchart, mind map) as
   Mermaid source. Mermaid is the source of truth.
4. Support two uses: a full retrospective at project end, and a focused
   brief on one decision or pivot mid-project.
5. Write in a configurable voice. The default is impersonal third person in
   a white-paper register. Style never alters a fact.
6. Run on the same hosts as Calamus (Claude Code, Codex CLI, Cursor) from one
   source, with no model call inside any script.

**Non-goals**

- Writing to `docs/dev_journal.md` or `docs/product_insights.md`. The
  append-only rule is untouched; this skill is read-only with respect to
  journals.
- Replacing `calamus-query`. Recall stays there; synthesis consumes the same
  parsed records.
- Hook registration. The skill is invoked on request and has no hooks.
- Spoken-word output (talk outlines, speaker notes) in v1. The voice profile
  reserves a section for it (section 8.2).
- Publishing. Output is files in the repository; sharing is a separate act.

## 2. Terms

- **Phase**: a contiguous stretch of entries with one stable goal.
- **Epoch**: a group of phases that ends at a pivot changing the premise of
  the work, not only the plan.
- **Pivot**: an entry or short run of entries after which the approach,
  scope, or constraint set differs materially from before.
- **Signal**: a deterministic, computed observation (a time gap, a tag-mix
  shift). Signals propose; they never decide.
- **Candidate**: a position in the record sequence where several signals
  agree. The analyst ranks candidates and names what they mean.

## 3. Architecture

Three layers, mirroring Calamus.

1. **Skill**: `SKILL.md` is a router of at most 150 lines. Procedure lives in
   `references/`, each file at most 300 lines.
2. **Engine**: `scripts/calamus-synth` and `scripts/lib/`. Deterministic,
   Python 3 stdlib and bash 3.2, no network, no model call.
3. **Analyst**: the model step, run inline in the host session or in an
   optional bundled subagent that reads the journals in an isolated context
   and returns the structured result.

```
journals (md | xml | jsonl)
  -> calamus-synth extract    facts.json: records, signals, candidates
  -> analyst                  names phases and epochs, ranks pivots, drafts prose
  -> calamus-synth diagrams   facts + analyst result -> .mmd files
  -> calamus-synth check      fidelity and voice lint
  -> calamus-synth render     only on explicit request: .mmd -> HTML
```

### 3.1 Layout

```
skills/calamus-synthesis/
  SKILL.md
  references/
    procedure.md       analyst steps and grounding rules
    outputs.md         contract for each output file
    whitepaper.md      section structure and register rules
    voice.md           how a profile is located and applied (no voice in it)
  agents/
    journal-analyst.md optional subagent definition
  assets/
    facts.schema.json
    synth.conf         signal weights and thresholds (data, parsed not sourced)
    voice.template.md  profile format with default bands
  scripts/
    calamus-synth
    lib/               signals.py, boundaries.py, mermaid.py, lint.py,
                       fidelity.py, render_html.py
```

### 3.2 Dependency on Calamus

Parsing is not reimplemented. `calamus-synth` imports `journal.py`,
`records.py`, `schema.py`, and the format parsers from the sibling
`skills/calamus/scripts/lib`, resolved relative to its own real path. The
two skills ship together in each host package. If the sibling is absent the
command exits 2 with a message naming the missing skill.

### 3.3 Model configuration

No script names a model. The subagent definition omits a model field and
inherits the session model. `calamus.env` pins are unchanged, so Level 1 and
Level 2 scores in Calamus stay comparable.

## 4. Engine

### 4.1 `calamus-synth extract`

Usage: `calamus-synth extract [--root DIR] [--since YYYY-MM-DD] [--out DIR]`

Reads both journals in whatever format is present, and emits
`facts.json` (schema in `assets/facts.schema.json`):

| Key | Content |
|---|---|
| `version` | Schema version |
| `journals` | Which journals and formats were read |
| `records` | Normalized entries: `id`, `journal`, `date`, `tag`, `title`, `files`, decision fields, evidence strength, follow-ups, cross-log ids |
| `sessions` | Session boundaries from markers |
| `signals` | Computed observations (4.2) |
| `candidates` | Phase-boundary and pivot candidates with their contributing signals |
| `stats` | Counts, date range, tag histogram |
| `warnings` | Skipped or malformed records, with ids where known |

Snapshot and other markers are used for session boundaries and excluded from
the decision set.

### 4.2 Signals

- **Time gaps**: an inter-entry gap greater than `gap_factor` times the
  median gap and at least `gap_min_days`.
- **Tag-mix shift**: Jensen-Shannon divergence between adjacent sliding
  windows of tags.
- **File-set turnover**: Jaccard distance between the files touched in
  adjacent windows.
- **Explicit pivots**: entries tagged `CP-PIVOT` or `CP-ARCHITECTURE`, and
  full-variant entries whose pivot field records a change and not a
  statement that the plan held.
- **Cross-log pairs**: entries linked across the two journals.
- **Open follow-ups**: follow-ups with no later entry that references them.
- **Unverified evidence**: engineering evidence marked unverified, and
  product evidence rated Weak, that no later entry confirms.
- **Supersession chains**: included where the record carries a supersede or
  revert reference. If the entry schema has no such field, v1 omits this
  signal and states so in `warnings`.

### 4.3 Candidates

A candidate is a position where the weighted count of signals within a
tolerance of one record reaches `phase_threshold` (default in `synth.conf`).
An explicit-pivot signal alone is enough to nominate a pivot candidate.
Whether a boundary is an epoch boundary is not computable; the engine marks
which candidates carry an explicit pivot and leaves the premise judgment to
the analyst.

All weights and thresholds live in `assets/synth.conf` and are tuned against
the fixtures in section 11.

## 5. Analyst procedure

`references/procedure.md` holds the steps. The analyst receives `facts.json`
and reads full record text only through `calamus-query --id`, so a large
journal never has to enter context whole.

### 5.1 Modes

- `full`: whole-project retrospective. Produces every output in section 6.
- `focus <entry-id | topic>`: a decision brief for one decision or pivot:
  options considered, trade-offs, what changed afterward, and a scoped
  diagram. Intended for use mid-project.
- `since <date>`: the same structure as `full`, limited to a window.

### 5.2 Judgment steps

1. Name phases from candidate boundaries; merge or drop candidates that do
   not correspond to a change in goal.
2. Group phases into epochs where a pivot changed the premise.
3. Rank pivots by effect on later work and write one sentence of rationale
   for each.
4. Draw insights: recurring constraints, reversed decisions and their cost,
   rejected alternatives that returned, product findings without engineering
   follow-through and the reverse, and thin spots in the record.

### 5.3 Grounding rules

- Every claim carries the id of at least one source entry, in the form
  `[<id>]`.
- A statement the analyst infers and does not read is labeled `(inferred)`.
- Missing evidence is reported as a gap. Nothing is filled in.
- The analyst may rank and name candidates but may not invent a pivot the
  engine did not surface. Adding one requires citing the entries that
  support it and labeling it `(analyst-added)`.
- A journal below `min_entries` (default 8) yields a timeline and a gap
  report, not phases.

## 6. Outputs

Written to `docs/writeups/<slug>/`, where `<slug>` is
`YYYY-MM-DD-<mode>`. Outputs contain repository-relative paths only.

| File | Content | Register |
|---|---|---|
| `facts.json` | The engine output, kept for audit | none |
| `overview.md` | One page: what was built, why, where it ended | engineering |
| `phases.md` | Each epoch and phase: dates, goal, key decisions, what ended it | engineering |
| `pivots.md` | Per pivot: state before, trigger, state after; closes with Cost, Complexity, Risk | engineering |
| `decisions.md` | Condensed decision table: choice, options, rationale, evidence | engineering |
| `insights.md` | Patterns, open threads, unverified claims, gaps | product for product-derived sections |
| `writeup-scaffold.md` | White-paper outline with cited material and marked gaps (6.1) | per section |
| `timeline.mmd`, `phases.mmd`, `pivots.mmd`, `mindmap.mmd` | Diagrams (section 7) | none |
| `*.html` | Rendered diagrams; only when requested (7.2) | none |

### 6.1 White-paper scaffold

Sections: Abstract, Problem, Background, Approach, Findings, Discussion,
Limitations, Conclusion, Evidence appendix. Findings subsections close with
Cost, Complexity, Risk. Gaps are marked `<!-- gap: ... -->` and listed in
the Limitations section.

### 6.2 Focus brief

`focus` mode writes `brief.md` and `brief.mmd` in place of the full set.

## 7. Diagrams

### 7.1 Mermaid

`calamus-synth diagrams` generates `.mmd` files deterministically from
`facts.json` plus the analyst result (phase and epoch names, pivot ranking):

- `timeline.mmd`: Mermaid `timeline`, grouped by phase.
- `phases.mmd`: flowchart of epochs containing phases.
- `pivots.mmd`: flowchart of decision, trigger, and outcome per pivot.
- `mindmap.mmd`: Mermaid `mindmap`, clustered by tag family and cross-log
  links.

The same inputs produce byte-identical files.

### 7.2 HTML render

`calamus-synth render --html` converts the `.mmd` files to a standalone
page. Rendering happens only when the request names it ("as HTML", "render
it"). `SKILL.md` states the rule, and the script offers no other path to
HTML. The page loads Mermaid from a CDN, which is the only network
dependency anywhere in the skill; the `.mmd` files remain the offline
fallback.

## 8. Voice

### 8.1 Lookup

First match wins:

1. `--voice <path>`
2. `.calamus/voice.md` in the project (already ignored by the repository's
   `.gitignore`)
3. `$XDG_CONFIG_HOME/calamus/voice.md`, or `~/.config/calamus/voice.md`
4. None found: neutral plain prose, default bands, lint still runs

The skill ships only `voice.template.md` and the generic `references/voice.md`.
No personal voice is stored in the repository.

### 8.2 Profile format

Markdown with a small front-matter block parsed as data (key and value
lines; no YAML dependency). Sections:

- `bands`: numeric overrides for the lint (8.4).
- `Register: engineering` and `Register: product`: rules, vocabulary, and
  exemplars for each.
- `Spoken`: reserved; unused in v1.

Exemplars are the author's own text. Third-party text is never copied into a
profile or into the repository.

### 8.3 Application

1. The analyst writes a neutral, fully cited draft.
2. A voice pass rewrites prose only. Tables, citations, diagrams, and
   `facts.json` are excluded.
3. `calamus-synth check` verifies fidelity (8.5). On failure the neutral
   draft ships and the failure is reported.

Each output file is tagged with a register (section 6). Engineering-journal
material uses the engineering register; product-journal material uses the
product register.

### 8.4 Default bands

Derived from measuring two reference documents in the target register
(approximate; sentence splitting is rough):

| Metric | Default band |
|---|---|
| Mean sentence length | 16 to 21 words |
| Sentences over 30 words | at most 15% |
| Sentences of 12 words or fewer | 25% to 35% |
| Sentences per paragraph | 2 to 3 on average |
| Em dashes, exclamation marks | 0 |
| First-person pronouns | 0 |
| Contractions | 0 (white-paper register) |

Lint findings are advisory warnings, never failures, so the prose is not
fitted to the numbers at the expense of meaning. The profile may override
any band.

### 8.5 Fidelity check

The multiset of cited ids, ISO dates, numerals with units, and
backticked paths in the voiced draft must equal that of the neutral draft.
Any difference fails the check. The check also fails on absolute local
paths, and warns on Findings paragraphs that carry neither a citation nor an
`(inferred)` label.

## 9. Packaging and hosts

- Each `packaging/<host>/skills/` gains a `calamus-synthesis` symlink to the
  canonical skill, with the same no-fork rule as `calamus`.
- `tests/test_packaging.sh` currently allows exactly one skill path in a
  package; `check_no_fork` is extended to allow both, and a new assertion
  covers the second symlink.
- `calamus-install` links both skills for the selected host.
- The optional subagent definition ships for Claude Code. On hosts without a
  subagent mechanism, `SKILL.md` instructs the model to run the procedure
  inline. Subagent support on Codex CLI and Cursor is unverified and is
  checked during planning, with results recorded in `docs/host-facts.md`.
- The Calamus adapter is unchanged. Discovery relies on the skill
  description.

## 10. Constraint compliance

| Constraint | How it holds |
|---|---|
| Hooks exit 0, print nothing | No hooks are added |
| Journals append-only | The skill never writes to them |
| Model strings only in `calamus.env` | No script or agent file names a model |
| Config is data | `synth.conf` and the voice front matter are parsed, never sourced |
| No absolute local paths | Outputs use repository-relative paths; `check` scans for violations |
| bash 3.2 and Python 3 stdlib | Same toolchain as Calamus |
| `SKILL.md` at most 150 lines, references at most 300 | Enforced by extending `tests/test_layout.sh` |

## 11. Failure handling and testing

### 11.1 Failure handling

These are CLIs, not hooks, so nonzero exits are allowed. Exit 2: usage error
or missing sibling skill or journal. Exit 3: `check` found a fidelity
failure. Malformed records are skipped and recorded in `warnings`. A thin
journal produces a timeline and a gap report.

### 11.2 Tests

All offline, added to `tests/run.sh`.

- **Fixtures**: synthetic journals in md, xml, and jsonl with planted
  phases, epochs, and pivots.
- **Engine**: golden `facts.json`; precision and recall of candidates
  against the planted boundaries; format parity (the three formats yield the
  same facts).
- **Diagrams**: byte-identical regeneration; structural validity of each
  `.mmd` (declaration line, balanced nodes and edges). If a Mermaid CLI is
  installed, parse with it as well.
- **Voice lint**: one passing and one failing passage per band.
- **Fidelity**: mutating a cited id, date, number, or path in a voiced draft
  fails; an absolute path fails.
- **HTML gating**: no `.html` is produced unless `render --html` runs.
- **Packaging and layout**: the extended assertions in section 9 and line
  caps in section 10.
- **Read-only**: running every command leaves both journals byte-identical.

Live checks, made only on request: run the analyst over this repository's
journals and review the phases, pivots, and insights against the history
by hand.

## 12. Open questions

1. Final skill name. `calamus-synthesis` is provisional.
2. Whether the entry schema carries supersede or revert references
   (4.2). If not, v1 omits that signal.
3. Whether `docs/writeups/` is committed or ignored. Default: not ignored.
4. Subagent support on Codex CLI and Cursor (section 9).
5. Spoken-word output (talk outline, speaker notes) as a follow-on, using
   the reserved profile section.

## 13. Decisions recorded

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Packaging unit | Sibling skill plus optional subagent | Standalone agent; extension of `calamus` | Smallest unit that fits; `calamus` router and adapter are size-capped and always-loaded |
| Diagram source | Mermaid, HTML opt-in | HTML-first | Portable, diffable, renders on common Git hosts |
| Model use | None in scripts | Backend call in `extract` | Offline tests; pins untouched |
| Voice storage | User-side profile file | Bundled in the skill | The repository is public; the voice is personal |
| Voice safety | Fidelity check on facts | Trust the rewrite | Style must not alter evidence |
| Lint strictness | Advisory | Blocking | Avoid prose fitted to numbers |
| Point of view | Impersonal third person | First person; second person | Matches the target register |
