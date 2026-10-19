# Analyst procedure

Input: `facts.json` and a mode. Output: `analysis.json` and a list of the
entries each later section will cite. Work from `facts.json`; open a full
entry only with `calamus-query --id <id>`.

## 1. Read the facts

1. `stats`: entry counts, date range, tag histogram.
2. `warnings`: skipped entries, unmatched cross-logs, omitted signals.
   Each becomes a gap in `insights.md`.
3. `sequence`: the ordered ids that signals were computed over.
4. `candidates`: positions where signals agree. For each, read the
   candidate entry and its neighbors with `calamus-query --id`.
5. `signals` without a position: `open_followup`, `unverified_evidence`,
   `crosslog_pair`. These feed insights.

If `warnings` says the journal has fewer entries than `min_entries`, skip
steps 2 to 4 below. Write `analysis.json` with empty `phases`, `epochs`,
and `pivots`, and produce a timeline and a gap report only.

## 2. Name phases

A phase is a stretch of the sequence with one stable goal.

1. Start with one phase boundary per candidate.
2. Read the entries on both sides. Keep the boundary only if the goal
   changed: different problem, different component, different user. Drop
   it if only the tag mix or the files changed.
3. Name each phase by its goal in three to six words ("Streaming parser",
   not "Phase 2").
4. Record `first` and `last` as sequence ids. Phases must not overlap and
   must follow sequence order.

## 3. Group epochs

An epoch ends when a pivot changes the premise: what the project is, who
it serves, or a constraint everything else rests on. A change of plan
inside the same premise is a phase boundary, not an epoch boundary.
Candidates with `explicit_pivot: true` are the usual epoch boundaries;
confirm each by reading it. Set `ended_by` to the pivot's id, or `null`
for the last epoch.

## 4. Rank pivots

For each pivot record `before`, `trigger`, `after`, and a one-sentence
`rationale` for its rank. Rank by effect on later work: count the later
entries that build on or work around it. Rank 1 is the largest effect.

Set `"origin": "engine"` for a candidate. To add a pivot the engine did
not surface, cite at least one entry in `sources` and set
`"origin": "analyst-added"`. Do not add a pivot to make the story tidier.

## 5. Draw insights

Look for each of these and cite every instance:

- Constraints that recur across phases.
- Decisions later reversed, and what the reversal cost.
- Rejected alternatives that came back.
- Product findings with no engineering follow-through, and engineering
  work with no product reason recorded.
- `open_followup` and `unverified_evidence` signals still standing.
- Thin spots: long gaps, phases with one entry, missing evidence.

## 6. Write analysis.json

Shape (full rules in `assets/analysis.schema.json`):

```json
{"version": 1, "mode": "full",
 "phases": [{"key": "p1", "name": "...", "goal": "...", "first": "<id>", "last": "<id>"}],
 "epochs": [{"key": "e1", "name": "...", "phases": ["p1"], "ended_by": null}],
 "pivots": [{"id": "<id>", "rank": 1, "label": "...", "before": "...", "trigger": "...",
             "after": "...", "rationale": "...", "origin": "engine", "sources": ["<id>"]}]}
```

Keep `label` under six words; it becomes a diagram edge. Run
`calamus-synth diagrams` and fix every problem it lists.

## 7. Choose excerpts and mechanism diagrams

Use `references/style.md`. Run `calamus-synth excerpt` for each chosen
excerpt and keep its output as is. Prefer, in order:

1. `--journaled` when the entry carries a code field.
2. `--symbol` for the function, class, or guard the decision changed.
3. `--diff` for a pivot whose point is the change itself.
4. `--lines` when nothing else isolates the construct.

A refusal (exit 4) means those lines cannot be shown. Pick other lines or
report the gap; never work around a secret refusal.

## 8. Grounding rules for the draft

- Every claim carries `[<id>]`. Put the citation at the end of the
  sentence it supports.
- Label anything inferred and not read `(inferred)`.
- Mark missing evidence `<!-- gap: what is missing -->` and say so in the
  text. Never fill a gap from general knowledge.
- Product material keeps product vocabulary (segment, evidence strength);
  engineering material keeps engineering vocabulary.

## Focus mode

`focus <id or topic>` produces `brief.md` and `brief.mmd` only.

1. Resolve a topic to entries with `calamus-query --brief` and pick the
   entry the request is about. If two are plausible, ask.
2. `analysis.json` holds that one pivot (rank 1) and no phases.
3. The brief covers: the decision, the options considered, the trade-off,
   what changed afterward (later entries that cite or depend on it), and
   at most two excerpts.

## Since mode

`since <date>` is `full` limited to entries on or after the date. Say in
the overview that earlier history is out of scope.

## Returning from a subagent

Return the path of `analysis.json`, the phase and pivot names, and the
list of gaps. Do not return the drafts' text.
