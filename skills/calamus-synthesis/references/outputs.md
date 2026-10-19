# Outputs

All files go in `docs/writeups/<YYYY-MM-DD>-<mode>/`. Paths inside them
are repository-relative. Draft in the order of the table: later files
reuse names and citations from earlier ones.

| Order | File | Register |
|---|---|---|
| 1 | `overview.md` | engineering |
| 2 | `phases.md` | engineering |
| 3 | `pivots.md` | engineering |
| 4 | `decisions.md` | engineering |
| 5 | `insights.md` | product for product-derived sections |
| 6 | `writeup-scaffold.md` | per section |

`facts.json`, `analysis.json`, and the `.mmd` files are written by the
engine. Do not edit them by hand.

## overview.md

One page.

1. `# <Project> overview`.
2. A three-sentence thesis: what was built, the decision that shaped it,
   where it ended.
3. `<!-- diagram: timeline.mmd -->`.
4. One paragraph per epoch, two to four sentences each, naming its phases.
5. `## Where it stands`: the last state, open follow-ups, and the largest
   gap.

## phases.md

`# Phases`, then `<!-- diagram: phases.mmd -->`. For each epoch, a `##`
heading with its name and dates. For each phase, a `###` heading with its
name and dates, then: the goal in one sentence, the two or three decisions
that defined it, and what ended it.

## pivots.md

`# Pivots`, then `<!-- diagram: pivots.mmd -->`. One `##` section per
pivot, in rank order:

1. The state before, the trigger, the decision, the consequence: one
   paragraph each, in that order.
2. At most one excerpt or one diff, placed after the decision paragraph.
3. Closing lines, each one sentence:
   `**Cost:** ...`, `**Complexity:** ...`, `**Risk:** ...`.

## decisions.md

`# Decisions`, then one table:

| Decision | Chosen | Options considered | Rationale | Evidence |
|---|---|---|---|---|

One row per decision that a phase or pivot depends on. `Evidence` holds
the citation and its status (verified, unverified, or the product
strength). Cells stay under 25 words.

## insights.md

`# Insights`, then `<!-- diagram: mindmap.mmd -->` and these sections,
each omitted only when empty:

- `## Patterns`: recurring constraints, reversed decisions, returning
  alternatives.
- `## Product and engineering`: findings without follow-through, in both
  directions. Product register.
- `## Open threads`: open follow-ups and unverified evidence.
- `## Gaps in the record`: every engine warning and every gap marked in
  other files.

## writeup-scaffold.md

See `references/whitepaper.md`.

## Mechanism diagrams

Optional `extra-<topic>.mmd` files, embedded with
`<!-- diagram: extra-<topic>.mmd -->` where the text discusses them. Rules
in `references/style.md`.

## Focus mode

`brief.md` replaces the set above:

1. `# <Decision>`: one-sentence answer to "what was decided and why".
2. `<!-- diagram: brief.mmd -->`.
3. `## Options`, `## Trade-off`, `## What changed afterward`, each prose,
   with at most two excerpts in total.
4. `**Cost:**`, `**Complexity:**`, `**Risk:**` lines.

## Markers

| Marker | Meaning | Written by |
|---|---|---|
| `<!-- diagram: name.mmd -->` | Embed point for a diagram | You; `embed` fills the block |
| `<!-- excerpt: ... [id] -->` | Start of an excerpt block | `excerpt` |
| `<!-- gap: ... -->` | Missing evidence | You |
