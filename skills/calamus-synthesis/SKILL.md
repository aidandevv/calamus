---
name: calamus-synthesis
description: >-
  Beta add-on to the calamus skill. Turns the Calamus engineering and product journals into writeups a person
  can read cold: a project overview, phase and pivot history, decision log,
  insights report, white-paper scaffold, or a focused brief on one decision.
  Adds Mermaid diagrams and verbatim code excerpts with provenance, and
  checks every claim against its source entry. Use when asked to summarize
  or retrospect on a project, explain why a decision or pivot happened,
  write up the work, or draw its history. Read-only on the journals.
metadata:
  tier: beta
---

# Calamus Synthesis (beta)

Beta: commands, output files, and marker formats may change between
releases. The core calamus skill does not depend on this one.

Reads `docs/dev_journal.*` and `docs/product_insights.*` and writes cited
documents under `docs/writeups/<YYYY-MM-DD>-<mode>/`. It never edits a
journal. The calamus skill must be installed next to this one.

## Pick the mode

| Request | Mode |
|---|---|
| Whole project, retrospective, white paper | `full` |
| One decision or pivot, "why did we ..." | `focus <entry-id or topic>` |
| Recent work, a window of dates | `since <YYYY-MM-DD>` |

## Run

Commands are in this skill's `scripts/` directory. Set `D` to
`docs/writeups/<today>-<mode>`.

1. **Facts.** `scripts/calamus-synth extract --out D` (add `--since` for
   `since` mode). Read `D/facts.json`; do not read whole journals.
2. **Analysis.** Follow `references/procedure.md` to write
   `D/analysis.json`. Where the host has a general subagent tool, give it
   `agents/journal-analyst.md` as its task, with the paths to
   `D/facts.json` and this skill, and the mode. Otherwise run the
   procedure here.
3. **Diagrams.** `scripts/calamus-synth diagrams D`. Fix any listed
   problem in `analysis.json` and run it again.
4. **Draft.** Write each file in `references/outputs.md`, in the order it
   gives, following `references/style.md`. Use `references/whitepaper.md`
   for the scaffold. Get every code block from
   `scripts/calamus-synth excerpt` and paste its output unchanged.
5. **Embed and check.** `scripts/calamus-synth embed D`, then
   `scripts/calamus-synth check D`. Fix every `FAIL`.
6. **Revise.** Rewrite only the sentences behind `WARN` lines, then check
   again. Stop after two passes; report what remains.
7. **Voice.** Locate a profile as `references/voice.md` describes. If one
   exists: `scripts/calamus-synth snapshot D`, rewrite prose in that
   voice, and `check` again. If fidelity fails, restore the snapshot
   draft from `.calamus/state/synth/` and report the failure.
8. **Report.** List the files written, failures fixed, warnings left, and
   every gap marked in the drafts.

## Rules

- Every claim cites at least one entry as `[<entry-id>]`. Label what is
  inferred, not read, `(inferred)`. Report missing evidence as a gap;
  never fill it in.
- Rank and name the engine's candidates. A pivot the engine did not
  surface needs cited sources and `"origin": "analyst-added"`.
- Read a full entry with the calamus skill's `calamus-query --id <id>`.
- Never type, paraphrase, or tidy code inside a fenced block.
- Write HTML only when the request asks for it ("as HTML", "render it"):
  `scripts/calamus-synth render D --html`. Otherwise the `.mmd` files and
  embedded diagrams are the output.
- Never write to a journal. Never put an absolute local path in a
  writeup.

## Exit codes

`0` ok. `2` usage error, invalid `analysis.json`, or missing journal or
sibling skill. `3` `check` found a failure. `4` an excerpt was refused
(path outside the repository, binary file, or secret); choose other lines
or report the gap.
