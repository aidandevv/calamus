# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Calamus is a core Agent Skill, `skills/calamus/`, that maintains two
append-only journals as live project memory: an engineering decision journal
(`docs/dev_journal.md`) and a product insight journal
(`docs/product_insights.md`), in `md`, `xml`, or `jsonl`. It installs on
Claude Code, Codex CLI, and Cursor from one source. The repository root
holds development files; `skills/calamus/` is what gets installed.
A beta sibling skill, `skills/calamus-synthesis/`, turns the journals into
cited writeups, Mermaid diagrams, and code excerpts. It is read-only on the
journals, ships beside the core in every package, and the core never
depends on it; its interfaces may change between releases.
`packaging/<host>/` wraps it as a plugin per host: a manifest plus hooks
built from `assets/hosts/<host>/hooks.json`, with `skills/calamus` a symlink
to the canonical skill — never a copy or an edited fork.
`tests/test_packaging.sh` enforces both. Host facts the templates rely on
are tracked, with sources, in `docs/host-facts.md`.

The design spec is `docs/superpowers/specs/2026-09-26-calamus-design.md`
and the implementation plan is `docs/superpowers/plans/2026-09-27-calamus.md`.
Where they disagree with the code, the code and tests are authoritative.

## Three layers

1. **Skill** — `SKILL.md` is a router (≤ 150 lines); per-journal procedure
   and schemas live in `references/` (≤ 300 lines each). Procedure only: no
   citations or design rationale — that belongs in `docs/design-rationale.md`
   or the README. Schema blocks in references are generated; edit
   `assets/schema/entry.schema.json`, then run
   `python3 skills/calamus/scripts/lib/gendocs.py --write`.
2. **Engine** — `scripts/hook.sh --host <h> --event <e>` plus `scripts/lib/`
   (payload, config, extractor, gates, schema, renderers, parser, the single
   journal writer), `scripts/backends/`, and host registration templates in
   `assets/hosts/`. Hooks exist because model-driven journaling is
   probabilistic and degrades near context limits.
3. **Adapter** — `assets/adapter.md`, pasted into a project or global
   `CLAUDE.md`/`AGENTS.md`. It loads every session, so it stays ≤ 15 lines
   with no filesystem paths.

## Hard constraints — do not violate

- **Hooks exit 0 and print nothing, on every path and every event.** A
  non-zero `PreCompact` exit can block compaction and strand a session;
  stdout may be parsed as host directives. `hook.sh` runs its whole body in
  a subshell with output discarded and `|| true` — preserve that.
- **Journals are append-only.** All writes go through
  `scripts/lib/journal.py:append_records`, which validates first, refuses
  duplicates, and only appends. Never truncate or rewrite a journal; to
  revise a decision, append a new entry. This repository's own journals in
  `docs/` follow the same rule.
- **Model strings live only in `skills/calamus/assets/calamus.env`**
  (`CALAMUS_CLAUDE_MODEL=claude-haiku-4-5`, `CALAMUS_CODEX_MODEL=gpt-5.4-mini`).
  `tests/test_layout.sh` enforces this. Do not change a pin without explicit
  instruction; a pin change makes Level 1 and Level 2 scores incomparable and
  requires re-baselining. Backends never fall back to another model.
- **Config is data.** Config files are parsed, never sourced.
  `CALAMUS_LLM_CMD` and `CALAMUS_*_BIN` are never read from a project-level
  file.
- **Journals never contain absolute local paths.** Pending-capture transcript
  paths go in `.calamus/state/`, which is never committed.
- **Scripts run on macOS `/bin/bash` 3.2 and Python 3 stdlib only.**

## Common commands

```bash
bash tests/run.sh                                       # full offline suite; run before every commit
python3 skills/calamus/scripts/lib/gendocs.py --check   # generated reference blocks are current
claude plugin validate packaging/claude-code                # check the Claude Code plugin (offline)
skills/calamus/scripts/calamus-install --host claude-code   # symlink skill, print hooks + adapter
skills/calamus/scripts/calamus-init --format md         # create both journals in a target project
skills/calamus/scripts/calamus-query --brief            # recall entries without reading whole files
skills/calamus/evals/eval-score.sh [N|--all]            # Level 2 scorer (makes a model call)
```

Tests use a fake `generic` backend and never call a model. Live checks
(Claude Code smoke test, overhead calibration, Level 2 before/after) make
real model calls and are run only on request.
