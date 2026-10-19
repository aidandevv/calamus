# Calamus Synthesis — Design Spec

> Status: beta (shipped beside the core calamus skill), amended 2026-10-15 (code excerpts, prose
> quality, diagram robustness). Branch: `refactor/calamus`.
> Scope: a second skill, `calamus-synthesis` (name provisional), that reads
> the two Calamus journals and produces human-readable writeups, diagrams,
> code excerpts, and decision briefs. It never writes to the journals.

## 1. Goals and non-goals

**Goals**

1. Translate the model-oriented journals into documents a human can read
   cold: an overview, a phase and epoch history, a pivot analysis, a
   condensed decision log, an insights report, and a white-paper scaffold.
2. Identify structure the journals do not state: phases, epochs, and the
   pivots that separate them, from deterministic signals first and model
   judgment second.
3. Produce diagrams (timeline, phase flow, pivot flowchart, mind map, and
   analyst-authored mechanism diagrams) as Mermaid source that is escaped,
   size-capped, validated, and embedded in the writeups. Mermaid is the
   source of truth.
4. Show the code behind a decision: excerpts taken verbatim from the
   repository as it stood when the decision was logged, or from the
   journal's own code field, with provenance a reader can check.
5. Write prose that reads as written by a careful engineer: claim first,
   specific, causal, and free of stock phrasing. Prose quality is supported
   by explicit craft rules, an advisory style lint, and a bounded revision
   pass.
6. Support two uses: a full retrospective at project end, and a focused
   brief on one decision or pivot mid-project.
7. Write in a configurable voice. The default is impersonal third person in
   a white-paper register. Style never alters a fact or an excerpt.
8. Run on the same hosts as Calamus (Claude Code, Codex CLI, Cursor) from one
   source, with no model call inside any script.

**Non-goals**

- Writing to `docs/dev_journal.md` or `docs/product_insights.md`. The
  append-only rule is untouched; this skill is read-only with respect to
  journals.
- Replacing `calamus-query`. Recall stays there; synthesis consumes the same
  parsed records.
- Hook registration. The skill is invoked on request and has no hooks.
- Spoken-word output (talk outlines, speaker notes) in v1. The voice profile
  reserves a section for it (section 9.2).
- Publishing. Output is files in the repository; sharing is a separate act.
- Language-aware parsing beyond Python. Symbol lookup for other languages
  is heuristic (section 8.3).

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
- **Excerpt**: a bounded, verbatim span of code with a provenance marker
  naming its path, commit, line range, and the entry it supports.
- **Tell**: a phrase or construction that marks prose as generic or
  machine-written. The style lint flags tells; it never rewrites them.

## 3. Architecture

Three layers, mirroring Calamus.

1. **Skill**: `SKILL.md` is a router of at most 150 lines. Procedure lives in
   `references/`, each file at most 300 lines.
2. **Engine**: `scripts/calamus-synth` and `scripts/lib/`. Deterministic,
   Python 3 stdlib and bash 3.2, no network, no model call. Git is read
   through the `git` command when the project is a repository.
3. **Analyst**: the model step, run inline in the host session or in an
   optional bundled subagent that reads the journals in an isolated context
   and returns the structured result.

```
journals (md | xml | jsonl)
  -> calamus-synth extract    facts.json: records, signals, candidates, code refs
  -> analyst                  analysis.json: phases, epochs, ranked pivots
  -> calamus-synth diagrams   facts + analysis -> .mmd files
  -> analyst                  neutral cited draft; excerpts via calamus-synth excerpt
  -> calamus-synth embed      copy each .mmd into its marked block in the drafts
  -> calamus-synth check      fidelity, excerpt and diagram verification, style lint
  -> analyst                  at most two revision passes on lint findings
  -> calamus-synth snapshot   keep the pre-voice draft under .calamus/state/
  -> analyst (voice pass)     prose only; check runs again against the snapshot
  -> calamus-synth render     only on explicit request: .mmd -> HTML
```

### 3.1 Layout

```
skills/calamus-synthesis/
  SKILL.md
  references/
    procedure.md       analyst steps and grounding rules
    outputs.md         contract for each output file and analysis.json
    whitepaper.md      section structure and register rules
    style.md           craft rules, excerpt and diagram placement, exemplars
    voice.md           how a profile is located and applied (no voice in it)
  agents/
    journal-analyst.md optional subagent definition
  assets/
    facts.schema.json
    analysis.schema.json
    synth.conf         signal weights, thresholds, caps (data, parsed not sourced)
    style.conf         tell lists and secret patterns (data, parsed not sourced)
    voice.template.md  profile format with default bands
  scripts/
    calamus-synth
    lib/               base.py, facts.py, signals.py, boundaries.py,
                       analysis.py, excerpt.py, mermaid.py, mmdlint.py,
                       embed.py, lint.py, voice.py, fidelity.py,
                       render_html.py, commands.py
```

### 3.2 Dependency on Calamus

Parsing is not reimplemented. `calamus-synth` imports `records.py`,
`schema.py`, `journal.py`, and `cli.py` from the sibling
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
| `records` | Normalized entries: `id`, `journal`, `variant`, `date`, `time`, `tag`, `title`, `files`, `summary`, evidence status, `followups`, `pivot_text`, `has_code`, cross-log id, `code_refs` |
| `sequence` | Ids of the records signals are computed over (4.2), in order |
| `sessions` | Session boundaries from markers |
| `signals` | Computed observations (4.2) |
| `candidates` | Phase-boundary and pivot candidates with their contributing signals |
| `stats` | Counts, date range, tag histogram |
| `warnings` | Skipped or malformed records, unmatched cross-logs, omitted signals |

Engineering snapshot entries and markers are used for session boundaries
and excluded from the decision set. Output is deterministic: sorted keys,
two-space indent, UTF-8, trailing newline. `time` comes from the entry id
(`YYYYMMDD-HHMM-xxxx`); legacy ids carry `0000` and their `time` is empty.

`code_refs` is present only when the project is a Git repository. For each
file a record names, it holds the resolved commit (section 8.2) or
`"missing": true` when no commit touches that path.

### 4.2 Signals

Signals are computed over one sequence: engineering decision entries when
there are at least `min_entries` of them, otherwise all entries, ordered by
date, then the time in the id, then journal order. Legacy ids end in a
content hash, so they are never used to break a tie. Product entries are placed into phases by date during
analysis.

- **Time gaps**: an inter-entry gap greater than `gap_factor` times the
  median gap and at least `gap_min_days`.
- **Tag-mix shift**: Jensen-Shannon divergence (base 2) between tag
  distributions of the `window` records before and after each position;
  a signal at each plateau-first local maximum at or above `jsd_min`.
- **File-set turnover**: Jaccard distance between the files touched in the
  same windows; a signal at each plateau-first local maximum at or above
  `jaccard_min`.
- **Explicit pivots**: entries tagged `CP-PIVOT`, and full-variant entries
  whose pivot field records a change rather than a statement that the plan
  held. `CP-ARCHITECTURE` entries emit a weaker `architecture` signal that
  cannot nominate a candidate alone.
- **Cross-log pairs**: entries linked across the two journals, matched on
  journal, tag, date, and title. Unmatched links go to `warnings`.
- **Open follow-ups**: follow-ups with no later entry whose text shares at
  least `followup_overlap` of the follow-up's significant words.
- **Unverified evidence**: engineering evidence marked unverified with no
  later verified entry sharing a file, and product evidence rated Weak with
  no later Medium or Strong entry carrying the same tag.
- **Supersession chains**: omitted in v1. The entry schema has no supersede
  or revert field; `extract` states the omission in `warnings`.

### 4.3 Candidates

Every position carrying a boundary signal (gap, tag shift, file turnover,
explicit pivot, architecture) is scored as the weighted sum of boundary
signals within `tolerance` records of it. A position becomes a candidate
when its score reaches `phase_threshold` or it carries an explicit pivot.
Non-maximum suppression then keeps one candidate per neighborhood: the
higher score wins, an explicit pivot wins a tie, then the earlier position.
Whether a boundary is an epoch boundary is not computable; the engine marks
which candidates carry an explicit pivot and leaves the premise judgment to
the analyst.

All weights, thresholds, and caps live in `assets/synth.conf` and are tuned
against the fixtures in section 12. Defaults: `window=4`, `gap_factor=3`,
`gap_min_days=7`, `jsd_min=0.6`, `jaccard_min=0.7`, `tolerance=1`,
`phase_threshold=2`, weights `gap=1`, `tag_shift=1`, `file_turnover=1`,
`explicit_pivot=2`, `architecture=0.5`.

### 4.4 `analysis.json`

The analyst's structured result, validated by `calamus-synth diagrams`
against `assets/analysis.schema.json` and `facts.json`:

```json
{
  "version": 1,
  "mode": "full",
  "phases": [{"key": "p1", "name": "...", "goal": "...", "first": "<id>", "last": "<id>"}],
  "epochs": [{"key": "e1", "name": "...", "phases": ["p1"], "ended_by": "<pivot id or null>"}],
  "pivots": [{"id": "<id>", "rank": 1, "label": "...", "before": "...", "trigger": "...",
              "after": "...", "rationale": "...", "origin": "engine", "sources": ["<id>"]}]
}
```

Validation fails (exit 2, with every problem listed) when an id is not in
`facts.json`, phases overlap or run out of sequence order, an epoch names
an unknown phase, ranks repeat, or a pivot that is not a candidate lacks
`"origin": "analyst-added"` and at least one source.

## 5. Analyst procedure

`references/procedure.md` holds the steps. The analyst receives `facts.json`
and reads full record text only through `calamus-query --id`, so a large
journal never has to enter context whole.

### 5.1 Modes

- `full`: whole-project retrospective. Produces every output in section 6.
- `focus <entry-id | topic>`: a decision brief for one decision or pivot:
  options considered, trade-offs, what changed afterward, a scoped diagram,
  and at most two excerpts. Intended for use mid-project.
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
5. Choose excerpts and mechanism diagrams (sections 7.5 and 8.6), then
   draft.

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
- Code shown to the reader comes only from `calamus-synth excerpt`. The
  analyst never types, paraphrases, or "cleans up" code in a fenced block.

## 6. Outputs

Written to `docs/writeups/<slug>/`, where `<slug>` is
`YYYY-MM-DD-<mode>`. Outputs contain repository-relative paths only.

| File | Content | Register |
|---|---|---|
| `facts.json` | The engine output, kept for audit | none |
| `analysis.json` | The analyst's structured result (4.4) | none |
| `overview.md` | One page: thesis paragraph, what was built, why, where it ended; embeds `timeline.mmd` | engineering |
| `phases.md` | Each epoch and phase: dates, goal, key decisions, what ended it; embeds `phases.mmd` | engineering |
| `pivots.md` | Per pivot: state before, trigger, decision, consequence, optional excerpt; closes with Cost, Complexity, Risk; embeds `pivots.mmd` | engineering |
| `decisions.md` | Condensed decision table: choice, options, rationale, evidence | engineering |
| `insights.md` | Patterns, open threads, unverified claims, gaps; embeds `mindmap.mmd` | product for product-derived sections |
| `writeup-scaffold.md` | White-paper outline with cited material and marked gaps (6.1) | per section |
| `timeline.mmd`, `phases.mmd`, `pivots.mmd`, `mindmap.mmd` | Generated diagrams (7.1) | none |
| `extra-<name>.mmd` | Analyst-authored mechanism diagrams (7.5), at most `max_extra_diagrams` | none |
| `*.html` | Rendered diagrams; only when requested (7.7) | none |

### 6.1 White-paper scaffold

Sections: Abstract, Problem, Background, Approach, Findings, Discussion,
Limitations, Conclusion, Evidence appendix. Each Findings subsection ends
its prose with the consequence of the finding, then closes with Cost,
Complexity, Risk. Gaps are marked `<!-- gap: ... -->` and listed in the
Limitations section. Excerpts may appear in Approach and Findings only.

### 6.2 Focus brief

`focus` mode writes `brief.md` and `brief.mmd` in place of the full set.

## 7. Diagrams

### 7.1 Generated diagrams

`calamus-synth diagrams` generates `.mmd` files deterministically from
`facts.json` plus `analysis.json`:

- `timeline.mmd`: Mermaid `timeline`, one section per phase.
- `phases.mmd`: flowchart of epochs (subgraphs) containing phases.
- `pivots.mmd`: flowchart of before, trigger, and after per pivot.
- `mindmap.mmd`: Mermaid `mindmap`, clustered by tag family and cross-log
  links.

Every generated file starts with a `%% sources:` comment listing the entry
ids it draws on. Flowcharts carry `accTitle` and `accDescr` lines; the
timeline carries a `title`. Node ids are generated (`n1`, `n2`, ...) and
never derived from text, so no label can collide with a Mermaid keyword.
The same inputs produce byte-identical files.

### 7.2 Label safety

Every label passes through one function, `mermaid.label`, which collapses
whitespace, truncates at a word boundary to `label_max_chars` (default 48)
with a trailing ellipsis, and replaces characters that Mermaid treats as
syntax with decimal entity codes (`"` as `#34;`, `:` as `#58;` in timeline
events, `;` as `#59;`, `#` as `#35;`, and `<`, `>` as `#60;`, `#62;`).
Mermaid decodes entities before it applies Markdown to flowchart labels,
so Markdown is defused in the text itself: a backtick becomes an
apostrophe, and a leading list or heading marker (`1.`, `-`, `#`) is
followed by a no-break space instead of a space. Flowchart and mind-map
labels are always quoted (`n1["..."]`).

### 7.3 Size caps

A diagram that cannot be read is worse than none. Caps live in
`synth.conf`:

- `max_nodes` (default 30) per flowchart. Phases beyond the cap collapse
  into one node per epoch stating the phase count.
- `timeline_max_events` (default 4) per phase section; the rest are
  summarized as one event, "and N more".
- `max_pivots` (default 7) in `pivots.mmd`, taken by rank.
- `max_leaves` (default 6) per mind-map branch, with a "+N more" leaf.

### 7.4 Embedding

Writeups embed diagrams so they render on Git hosts without a separate
file open:

````
<!-- diagram: timeline.mmd -->
```mermaid
...
```
````

`calamus-synth embed <dir>` replaces the fenced block after each marker with
the named file's bytes, inserting the block if absent. Running it twice
changes nothing. `check` fails when an embedded block differs from its
source file or names a missing file.

### 7.5 Mechanism diagrams

Where a decision is easier to see than to read (an event sequence, a data
flow, a state machine), the analyst may write `extra-<name>.mmd` using
`flowchart`, `sequenceDiagram`, or `stateDiagram-v2`. Each starts with a
`%% sources:` comment naming the entries it depicts and shows only
components and steps those entries name. At most `max_extra_diagrams`
(default 3) per writeup; `references/style.md` states when one earns its
place.

### 7.6 Validation

`mmdlint` checks every `.mmd` structurally: the first non-comment line is a
supported declaration; brackets, parentheses, braces, and quotes balance on
each line; `subgraph` and `end` balance; flowchart edges refer only to
declared node ids; labels contain no raw `"`; a `%% sources:` comment is
present; and node counts respect the caps. When a Mermaid CLI (`mmdc`) is
on `PATH`, `check --mmdc` also parses each file with it. `check` fails on
any structural error.

### 7.7 HTML render

`calamus-synth render --html` converts the `.mmd` files to a standalone
page. Rendering happens only when the request names it ("as HTML", "render
it"). `SKILL.md` states the rule, and the script offers no other path to
HTML. The page loads Mermaid from a CDN at a pinned version, which is the
only network dependency anywhere in the skill; the `.mmd` files remain the
offline fallback.

## 8. Code excerpts

### 8.1 Sources

In priority order:

1. The journal's own `code` field on a full engineering entry, quoted
   verbatim and cited to that entry.
2. The repository at the commit resolved for the entry (8.2).
3. None: the writeup reports a gap. The analyst does not substitute the
   current working tree.

When the project is not a Git repository, source 2 falls back to the
working tree, the caption says "working tree", and `check` warns.

### 8.2 Commit resolution

The entry's time comes from its id; a legacy id resolves to the end of its
date. The resolved commit for a path is the latest commit reachable from
`HEAD` that touches the path at or before the entry time plus
`excerpt_grace_hours` (default 12), because entries are often logged just
before the commit lands. The analyst may override it with `--at <rev>`.
The caption always shows the commit, so a reader can see which state was
quoted.

### 8.3 Selection

```
calamus-synth excerpt --id ID (--journaled | --path P (--symbol NAME | --lines A-B))
                      [--at REV] [--diff [--from REV]] [--max-lines N] [--root DIR]
```

- `--symbol` in a `.py` file uses `ast` and includes decorators. Elsewhere it
  matches a definition line (`def`, `class`, `function`, `func`, `fn`,
  `struct`, `interface`, `type`, or shell `name() {`) and extends to the
  balancing brace or the end of the indented block.
- `--diff` prints the unified diff for the path from `--from` (default the
  resolved commit's first parent) to the resolved commit.
- Excerpts longer than `--max-lines` (default `excerpt_max_lines`, 25) keep
  the head and tail and replace the middle with one elision line in the
  file's comment syntax, stating how many lines were omitted.

The command prints a ready-to-paste block:

````
<!-- excerpt: scripts/hook.sh@1a2b3c4d5e6f:L12-L30:max25 [20260927-1630-a1b2] -->
`scripts/hook.sh` at `1a2b3c4`, lines 12-30 [20260927-1630-a1b2]

```bash
...
```
````

The marker carries everything needed to extract the block again: path,
commit (12 hex digits), span, and line cap. Journaled excerpts use
`journal:max<N>`; diffs use `<path>@<from>..<to>:diff:max<N>`; working-tree
excerpts use `working-tree` in place of the commit. Paths containing
whitespace are refused.

### 8.4 Guards

Exit 4 refuses an excerpt when the path is absolute, contains `..`, uses
glob or pathspec syntax (Git always receives paths literally), or leaves
the repository; the path does not exist at the commit or is not a
regular file there (a directory or a symlink); the content is binary; the
file name matches a key or environment file (`*.pem`, `*.key`, `id_rsa*`,
`.env*`, and others in `assets/style.conf`); the file contains a private-key
header anywhere; or a selected line matches a secret pattern (common cloud
and forge token prefixes, and quoted or unquoted assignments to names
containing key, secret, token, or password). The refusal message names the
rule and never prints the matching line. A `--diff` applies the
file-name check first, requires a regular file (or none) at both commits,
and checks both commits' content for a private-key header.

### 8.5 Verification

`check` re-runs every excerpt marker and fails unless the fenced block that
follows is byte-identical to a fresh extraction. Voice and revision passes
never touch excerpt markers, captions, or fenced code.

### 8.6 Placement

Rules in `references/style.md`: an excerpt appears only where the
surrounding prose names a specific line or construct in it; a sentence
before it says what to look at and a sentence after it says what followed;
prefer the interface, guard, or configuration that embodies the decision
over a function body; one excerpt per pivot, or one diff; at most
`max_excerpts` (default 4) per file, which `check` warns beyond.

## 9. Voice and prose quality

### 9.1 Lookup

First match wins:

1. `--voice <path>`
2. `.calamus/voice.md` in the project (already ignored by the repository's
   `.gitignore`)
3. `$XDG_CONFIG_HOME/calamus/voice.md`, or `~/.config/calamus/voice.md`
4. None found: neutral plain prose, default bands, lint still runs

The skill ships only `voice.template.md` and the generic `references/voice.md`.
No personal voice is stored in the repository.

### 9.2 Profile format

Markdown with a small front-matter block parsed as data (key and value
lines; no YAML dependency). Sections:

- `bands`: numeric overrides for the lint (9.4).
- `Register: engineering` and `Register: product`: rules, vocabulary, and
  exemplars for each.
- `Spoken`: reserved; unused in v1.

Exemplars are the author's own text. Third-party text is never copied into a
profile or into the repository.

### 9.3 Application

1. The analyst writes a neutral, fully cited draft following the craft
   rules (9.5).
2. `calamus-synth check` runs fidelity, verification, and the style lint.
3. The analyst revises only the flagged sentences, at most twice. Findings
   that remain after the second pass are listed in the run summary, not
   chased further.
4. `calamus-synth snapshot <dir>` keeps the pre-voice draft under
   `.calamus/state/synth/<slug>/`, which is never committed. `extract
   --out <dir>` clears that snapshot, so a rerun never compares a new
   draft with an old one.
5. A voice pass rewrites prose only. Tables, citations, diagrams, excerpts,
   and `facts.json` are excluded.
6. `check` runs again and compares against the snapshot. On a fidelity
   failure the pre-voice draft ships and the failure is reported.

Each output file is tagged with a register (section 6). Engineering-journal
material uses the engineering register; product-journal material uses the
product register.

### 9.4 Default bands

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

Bands measure prose only: headings, tables, fenced blocks, comments, and
list markers are stripped first. The profile may override any band.

### 9.5 Craft rules

`references/style.md` holds these with one short before-and-after pair
each, written for this skill from a synthetic project:

1. Lead with the claim. The first sentence of a section or paragraph states
   what happened or what it means; evidence follows.
2. Narrate pivots in causal order: the state before, the trigger, the
   decision, the consequence.
3. Use the record's specifics: file names, numbers, the rejected
   alternative, the failing test. A sentence that would fit any project is
   cut or made specific.
4. One idea per paragraph. Transitions state the relation (because, so,
   but, which meant), not addition alone.
5. Prose carries argument; tables carry comparison; bullets carry three or
   more parallel items that need no connective.
6. Citations go at the end of the sentence they support, at most three ids
   per sentence.
7. No journal mechanics in prose: no tag names, no "the journal records".
   Say what happened.
8. Define a term at first use. Expand an acronym once.
9. The overview opens with a three-sentence thesis: what was built, the
   decision that shaped it, and where it ended.
10. Before shipping, a reader test: from the first paragraph of each file
    alone, a reader who has not seen the journals can say what changed and
    why.

### 9.6 Style lint

Advisory findings, each reported with file, line, rule, and the matched
text. Lists live in `assets/style.conf` and the profile may extend them.

| Rule | Flags |
|---|---|
| `stock-phrase` | Stock phrasing such as "it is worth noting", "plays a crucial role", "a testament to", "delve", "leverage" as a verb, "seamless", "robust", "navigate the complexities", "in today's" |
| `filler-transition` | Sentence-initial "Additionally", "Furthermore", "Moreover", "In conclusion", "Overall" |
| `stacked-hedge` | Two or more of may, might, could, possibly, potentially, perhaps, arguably in one sentence |
| `repeated-opener` | Three consecutive sentences starting with the same word |
| `vague-referent` | A sentence starting "This" or "It" followed directly by a verb |
| `contrast-frame` | "not only ... but also", "not just X, but Y", "it's not X, it's Y" |
| `empty-intensifier` | very, really, extremely, significantly, without a number in the sentence |
| `tag-leak` | A `CP-` or `PI-` tag name in prose outside tables and citations |
| `citation-clutter` | More than three ids in one sentence |
| `bullet-heavy` | List lines above 40% of prose lines in `overview.md`, `phases.md`, `pivots.md`, or `insights.md` |
| band rules | Each band in 9.4 |

Lint findings are advisory warnings, never failures, so the prose is not
fitted to the numbers or lists at the expense of meaning.

### 9.7 Fidelity check

The multiset of cited ids, ISO dates, numerals with units, and backticked
paths in the voiced draft must equal that of the pre-voice draft. Fenced
blocks and excerpt captions are excluded from the multiset and verified by
8.5 instead. Any difference fails the check. The check also fails on
absolute local paths, and warns on Findings paragraphs that carry neither a
citation nor an `(inferred)` label.

## 10. Packaging and hosts

- Each `packaging/<host>/skills/` gains a `calamus-synthesis` symlink to the
  canonical skill, with the same no-fork rule as `calamus`.
- `tests/test_packaging.sh` currently allows exactly one skill path in a
  package; `check_no_fork` is extended to allow both, and a new assertion
  covers the second symlink.
- `calamus-install` links both skills for the selected host.
- `agents/journal-analyst.md` is a portable brief, not a host-registered
  agent: where the host offers a general subagent tool, `SKILL.md` has the
  model pass the brief as the subagent's task, so no package needs an
  `agents/` directory and the no-fork rule holds. Otherwise the procedure
  runs inline. Subagent tools on Codex CLI and Cursor are recorded as
  unverified in `docs/host-facts.md` until checked.
- The Calamus adapter is unchanged. Discovery relies on the skill
  description.

## 11. Constraint compliance

| Constraint | How it holds |
|---|---|
| Hooks exit 0, print nothing | No hooks are added |
| Journals append-only | The skill never writes to them; a test runs every command and compares journal bytes |
| Model strings only in `calamus.env` | No script or agent file names a model; `test_layout.sh` scans both skills |
| Config is data | `synth.conf`, `style.conf`, and the voice front matter are parsed, never sourced |
| No absolute local paths | Outputs use repository-relative paths; `check` scans for violations; excerpts refuse absolute paths |
| bash 3.2 and Python 3 stdlib | Same toolchain as Calamus; `git` is the only external command, and only when present |
| `SKILL.md` at most 150 lines, references at most 300 | Enforced by extending `tests/test_skill.sh` and `tests/test_docs.sh` |

## 12. Failure handling and testing

### 12.1 Failure handling

These are CLIs, not hooks, so nonzero exits are allowed. Exit 2: usage
error, unreadable or invalid input (including an `analysis.json` missing a
required field or holding a wrong type), or missing sibling skill or
journal. No command prints a traceback for bad input. Exit 3:
`check` found a fidelity, excerpt, or diagram failure. Exit 4: an excerpt
was refused (8.4). Malformed records are skipped and recorded in
`warnings`. A thin journal produces a timeline and a gap report.

### 12.2 Tests

All offline, added to `tests/run.sh`.

- **Fixtures**: a deterministic generator for synthetic journals with
  planted phases, epochs, and pivots, rendered to md, xml, and jsonl.
- **Engine**: precision and recall of candidates against the planted
  boundaries; format parity (the three formats yield the same facts);
  determinism; thin-journal behavior.
- **Analysis**: each validation rule in 4.4 has a failing case.
- **Diagrams**: byte-identical regeneration; hostile labels (quotes,
  colons, brackets, `end`, emoji) produce files that pass `mmdlint`; caps
  hold on an oversized fixture; `mmdlint` rejects each structural fault it
  claims to catch. If `mmdc` is installed, parse with it as well.
- **Embedding**: idempotent; a stale block fails `check`.
- **Excerpts**: commit resolution with grace; Python symbol with
  decorators; shell function; line range; elision; diff; journaled code;
  each guard in 8.4 refuses with exit 4; a mutated excerpt fails `check`.
- **Style lint**: one flagged and one clean passage per rule and band.
- **Fidelity**: mutating a cited id, date, number, or path in a voiced draft
  fails; an absolute path fails.
- **HTML gating**: no `.html` is produced unless `render --html` runs.
- **Packaging and layout**: the extended assertions in section 10 and line
  caps in section 11.
- **Read-only**: running every command leaves both journals byte-identical.

Live checks, made only on request: run the analyst over this repository's
journals and review the phases, pivots, excerpts, and prose against the
history by hand.

## 13. Open questions

1. Final skill name. `calamus-synthesis` is provisional.
2. Whether `docs/writeups/` is committed or ignored. Default: not ignored.
3. Subagent support on Codex CLI and Cursor (section 10).
4. Spoken-word output (talk outline, speaker notes) as a follow-on, using
   the reserved profile section.
5. Whether the entry schema should gain a supersede or revert field so the
   omitted signal in 4.2 can be computed. That is a Calamus schema change
   and out of scope here.

## 14. Decisions recorded

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Packaging unit | Sibling skill plus optional subagent | Standalone agent; extension of `calamus` | Smallest unit that fits; `calamus` router and adapter are size-capped and always-loaded |
| Diagram source | Mermaid, HTML opt-in | HTML-first | Portable, diffable, renders on common Git hosts |
| Diagram delivery | Embedded copies verified against `.mmd` files | Separate files only | Writeups render in place; the `.mmd` stays the single source |
| Mechanism diagrams | Analyst-authored, linted, capped, sourced | Generated only; free-form | Some decisions need a sequence or state view the engine cannot derive |
| Model use | None in scripts | Backend call in `extract` | Offline tests; pins untouched |
| Code shown | Verbatim excerpts from the resolved commit or journal | Current working tree; model-written code | The code must be what existed when the decision was made |
| Commit resolution | Latest commit touching the path by entry time plus grace | Exact timestamp; commit hash in the entry | Entries precede commits; the schema has no commit field |
| Prose quality | Craft rules, advisory tell lint, two revision passes | Blocking lint; unbounded revision | Specific, causal prose without fitting text to a checklist |
| Signal sequence | Engineering decisions, else all entries | Merged journals | Product tags add noise to tag-shift signals |
| Voice storage | User-side profile file | Bundled in the skill | The repository is public; the voice is personal |
| Voice safety | Fidelity check on facts | Trust the rewrite | Style must not alter evidence |
| Lint strictness | Advisory | Blocking | Avoid prose fitted to numbers |
| Point of view | Impersonal third person | First person; second person | Matches the target register |
