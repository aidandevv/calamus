---
name: calamus
description: >-
  Live project memory for agent sessions. Maintains an engineering decision
  journal (docs/dev_journal.md) and a product insight journal
  (docs/product_insights.md). Use when making architecture or implementation
  decisions, pivoting, fixing a non-obvious bug, hitting a constraint, or
  finishing a verified milestone, and when observing user pain, UX friction,
  positioning, roadmap trade-offs, or growth signals worth recalling later.
  Also use to recall earlier decisions and to resolve CALAMUS-PENDING
  markers. Append-only.
compatibility: Any Agent Skills-compatible agent. Optional lifecycle hooks need bash and python3.
metadata:
  version: "3.0.0"
---

# Calamus

Two append-only journals in `./docs/`: an engineering journal and a product
insight journal. Paths below are relative to this skill's directory unless
they start with `./docs/`.

## 1. Pick the journal

| Signal | Journal | Read first |
|---|---|---|
| Architecture, pivot, refactor, verified milestone, constraint, non-obvious bug, testing strategy, integration | engineering (`./docs/dev_journal.*`) | `references/engineering-journal.md` |
| User pain, UX friction, onboarding, retention, positioning, roadmap, pricing, trust, growth | product (`./docs/product_insights.*`) | `references/product-insights.md` |
| A technical constraint that changes the user experience | both | both references, then rule 6 |

Read the reference before writing an entry in that journal.

## 2. Initialize

If the journals do not exist, run `scripts/calamus-init` from the project
root (`--format md|xml|jsonl`; default `md`). If scripts cannot run, create
the file with the header shown in the relevant reference.

## 3. Noise gate

The entry must answer at least four of the questions listed in the
relevant reference. Otherwise use the Lightweight schema, or ask the user
whether to wait.

## 4. Append safety

- Always append. Never overwrite, rewrite, or delete an entry.
- Check recent entries first (`scripts/calamus-query --brief --last 5`) so
  you do not log the same checkpoint twice.
- If a decision changes, append a new entry that describes the revision.
- If the file cannot be written, output the entry in a copyable code fence,
  name the file it belongs in, and say the file was not modified.

## 5. Compaction

If Calamus hooks are installed, do not log manually before `/compact`; the
`pre-compact` hook writes a `[CP-COMPACT-SNAPSHOT]` entry. Without hooks,
append a snapshot entry first (template in
`references/engineering-journal.md`).

## 6. Cross-log

When one observation has both an engineering and a product dimension worth
keeping, write separate entries in both journals and link each to the other
with a `[CROSS-LOG]` reference (`crosslog` field with `calamus-append`). The
Markdown form is at the end of each template in the references.

## 7. Pending markers

A pending marker means a hook could not reach a model:
`<!-- CALAMUS-PENDING: <date> | id:<session> | host:<host> | event:<event> -->`
in Markdown, or a `marker` record of kind `pending` in `xml` and `jsonl`
journals. Find them with `scripts/calamus-query --type marker --brief`.

At a natural boundary, offer to resolve one:
1. Draft the entry from what you know of that session and the current work.
   Do not invent details you cannot support.
2. With the user's agreement, append the entry, then append a resolved
   marker for the same session:
   `{"record": "marker", "kind": "resolved", "date": "YYYY-MM-DD", "session": "<id>", "entry": "<new entry id>"}`.
3. Never delete or edit the pending marker.

## 8. Format and writing

The journal's file extension sets the format: `.md`, `.xml`, or `.jsonl`.

- If scripts can run, write with
  `scripts/calamus-append --journal engineering|product`, passing a JSON
  object (or `{"entries": [...]}`) on stdin. Fields are listed in each
  reference under "JSON Fields". It validates, renders in the project's
  format, appends, and prints `ok <id>`. On errors it prints the fields to
  fix and writes nothing; fix them and run it again.
- If scripts cannot run, write the entry directly using the template in
  the matching reference: the journal references for Markdown,
  `references/format-xml.md` for `.xml`, `references/format-jsonl.md` for
  `.jsonl`. Append at the end of the file.

## 9. Recall

To resume work or check an earlier decision, query instead of reading a
journal whole:

- `scripts/calamus-query --brief` lists entries (id, journal, tag, date,
  title). Narrow with `--last N`, `--tag CP-DEBUG`, `--since YYYY-MM-DD`,
  `--file path/fragment`, or `--journal engineering|product`.
- `scripts/calamus-query --id <id>` prints one entry in full.
- After a compaction:
  `scripts/calamus-query --tag CP-COMPACT-SNAPSHOT --last 1`.

Read a journal file directly only if scripts cannot run.
