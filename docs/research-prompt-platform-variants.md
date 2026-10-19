# Research prompt: one portable skill vs. per-platform skills

Paste everything below the line into a research model.

---

## Role and task

You are a research analyst on agent-tooling architecture. Evaluate one design decision and give a recommendation with evidence. Verify every claim about host platforms (Claude Code, Codex CLI, Cursor) against current official documentation, changelogs, and source repositories. Do not rely on memory. Cite sources with URLs and access dates, and mark each claim `verified` or `inferred`.

**The question:** Calamus ships as one Agent Skill installed on three hosts from a single source tree. Should it instead ship as a separate, tailored skill for each platform (for example `calamus-claude-code`, `calamus-codex`, `calamus-cursor`)? Or is the single portable skill, with thin per-host adapters, the better design? If neither extreme is right, recommend a hybrid and say exactly where the boundary falls.

## What Calamus is

Calamus is an Agent Skill that maintains two append-only journals as live project memory for coding-agent sessions:

- an engineering decision journal (`docs/dev_journal.md`)
- a product insight journal (`docs/product_insights.md`)

Each journal can be `md`, `xml`, or `jsonl`. The motivation is that model-driven journaling is probabilistic and degrades near context limits. So the skill is paired with lifecycle hooks that capture entries deterministically. The repo is a development root. `skills/calamus/` is the only thing that gets installed.

## Current architecture (three layers, one source tree)

**1. Skill (the portable part, loaded by the agent)**

- `SKILL.md` is a router of at most 150 lines. It is currently 110 lines, with frontmatter `name`, `description`, `compatibility: Any Agent Skills-compatible agent`, and `metadata.version`.
- `references/` holds one file per journal plus format specs, each at most 300 lines. Only the reference for the journal being written is loaded (progressive disclosure).
- The SKILL.md body is host-agnostic. It tells the agent to run `scripts/calamus-init`, `calamus-append`, and `calamus-query` (validated, append-only writer and recall CLI). If scripts can't run, it falls back to writing the entry directly from a template.

**2. Engine (hooks, never in the working agent's context)**

- One entry point: `scripts/hook.sh --host <claude-code|codex|cursor|generic> --event <pre-compact|post-compact|turn-stop|session-end>`.
- `scripts/lib/payload.sh` normalizes each host's hook stdin payload into common fields (session, transcript path, cwd).
- `scripts/lib/` also holds config, transcript extractor, gates, schema validator, renderers, parser, and the single journal writer.
- `scripts/backends/{claude,codex,cursor,generic}.sh` are the model-call backends. A hook shells out to a small pinned model to draft a snapshot or sweep entry from the transcript. Model pins live in one file, `assets/calamus.env` (`claude-haiku-4-5` and `gpt-5.4-mini`), and backends never fall back across providers.
- `assets/profiles/*.env` holds per-provider tuning. It is currently almost empty because tuning values need a measurement before they are added.
- Hard constraints:
  - Hooks always exit 0 and print nothing, because a non-zero PreCompact exit can block compaction.
  - Journals are append-only through one writer.
  - Config is parsed as data, never sourced.
  - Journals never contain absolute local paths.
  - Scripts run on macOS bash 3.2 and Python 3 stdlib only.

**3. Adapter (per-host glue, small)**

- `assets/adapter.md` is about 14 lines of text pasted into the user's `CLAUDE.md` or `AGENTS.md`. It loads every session, so it is kept tiny and path-free.
- `assets/hosts/<host>/hooks.json` is a registration template per host, and `scripts/calamus-install --host <h>` symlinks or copies the skill. It never edits settings files. It prints the hooks JSON and adapter text for the user to merge.

## Where the hosts actually differ today

| | Claude Code | Codex CLI | Cursor |
|---|---|---|---|
| Skill install path | `~/.claude/skills/calamus` | `~/.agents/skills/calamus` | `~/.agents/skills/calamus` |
| Hook config | `settings.json` (`PreCompact`, `PostCompact`, `SessionEnd`) | `hooks.json` (`PreCompact`, `PostCompact`, `Stop`, `SessionEnd`) | `hooks.json` (`preCompact`, `stop`, `sessionEnd`) |
| Per-turn hook | none registered (sweep skipped) | `Stop` → `turn-stop` (90s) | `stop` → `turn-stop` (90s) |
| Post-compact hook | yes | yes | none |
| SessionEnd timeout budget | 60s | 3s | 5s |
| Adapter target | `CLAUDE.md` | `AGENTS.md` | `AGENTS.md` or a Cursor rule |
| Capture backend | `claude -p` (Haiku 4.5) | `codex exec` (gpt-5.4-mini) | `cursor` CLI backend |

Other known differences: Codex only runs project-local hooks from a trusted `.codex/` layer. Cursor also imports hooks from `.claude/settings.json`, so a user can double-register. Because Codex and Cursor give `SessionEnd` very little time, they rely on a per-turn sweep, while Claude Code gets enough `SessionEnd` time to capture at the end of the session.

Today every difference above lives in the hook and installer layer. The skill body (SKILL.md and references) is identical across hosts.

## Current state and evidence

- Implementation is complete through the installer, router, and Level 2 scorer. The offline suite passes. It uses a fake `generic` backend and never calls a model.
- **Not yet done:** a live Claude Code smoke test, overhead calibration (measured: `claude -p` costs about 3.7k input tokens fixed overhead per call), and Level 2 before/after scores. No live Codex or Cursor hook run has been measured. Level 3 (drift) and Level 4 (behavioral golden-set evals) do not exist.
- Evals: Level 1 is a structural validator plus a sampled model-judged 4-of-8 gate, which fails closed. Level 2 is a 5-dimension rubric, comparable only within one backend/model pair. The judge shares a model family with the capture backend, and the rubric is uncalibrated against humans.
- There is no empirical data yet on whether the single `description` and `SKILL.md` triggers equally well on all three hosts.

## What I want you to determine

Weigh these axes and cite evidence for each:

1. **Spec and portability.** What does the open Agent Skills spec guarantee across hosts (frontmatter fields, `compatibility`, progressive disclosure, `scripts/` execution, `allowed-tools`, `$ARGUMENTS`, invocation controls)? Where do Claude Code, Codex, and Cursor extend or diverge from it (skill discovery paths, frontmatter extensions, tool names, sandboxing, trust prompts, `AGENTS.md` vs `CLAUDE.md` handling)? Does any host silently ignore, reject, or misparse fields we depend on?
2. **Trigger quality.** Does a host-specific `description` or tool vocabulary measurably improve skill activation? Look for published evals, docs on description-matching, or known activation failures. Does one shared description risk under-triggering on any host?
3. **Hooks.** Hooks are the highest-value and most divergent piece. Check current hook event names, payload schemas, timeout semantics, whether non-zero exit blocks anything, whether stdout is parsed, and whether skills or plugins can bundle hooks natively. For each host, can a skill register its own hooks, or must users hand-merge JSON as they do now? Are there plugin or extension packaging formats (Claude Code plugins/marketplaces, Codex equivalents, Cursor rules/extensions) that would make per-host packaging the standard distribution path regardless of skill content?
4. **Maintenance cost.** Three skill directories imply triple the review surface, version skew, and drift in the references and schema. What do comparable multi-host projects do (for example, repos that ship one `SKILL.md` for many agents, versus ones that fork per agent)? Look for real cases of divergence causing bugs.
5. **Context cost and correctness.** Does host-specific text in SKILL.md (tool names, paths, slash commands) save tokens or prevent errors compared with the current host-neutral router? Does the 14-line adapter already cover that?
6. **Distribution and discovery.** Compare skill registries, marketplaces, and `npx skills`-style installers. Do they favor one skill with multi-host support, or per-host packages?
7. **User experience.** The current install prints hooks JSON for the user to merge by hand. Would per-host packages (for example a Claude Code plugin that bundles hooks) remove that step? Would that justify packaging per host even if the skill content stays shared?

## Options to evaluate

- **A. Status quo.** One portable skill, host logic in the engine and adapters.
- **B. Fully separate skills.** One distinct, tailored skill per platform, each with its own SKILL.md, references, and hooks.
- **C. Shared core with per-host packaging.** One canonical skill source. A build step generates per-host artifacts (host-tuned description and frontmatter, bundled hook registration, plugin or extension manifests) from it. Users install the generated per-host package.
- **D. Any other option your research surfaces.**

## Deliverable

1. A direct recommendation (A, B, C, or other) in the first paragraph, with a confidence level.
2. A comparison table of the options against the seven axes, with a one-line justification per cell.
3. The specific things that should differ per host and the things that should never differ, each justified.
4. A list of claims about Claude Code, Codex, and Cursor behavior that you verified, with sources. Flag anything you could not verify.
5. The cheapest experiment that would change your recommendation (for example, an activation test across hosts), and which result would flip it.
6. Risks of your recommended path and a migration sketch from the current layout.

Do not recommend splitting only because it feels more tailored. Do not recommend staying only because it exists. The decision should follow the evidence on activation, hooks, maintenance, and distribution.
