# Calamus

When you're building a product and iterating constantly, it becomes incredibly easy to forget certain pivots and decisions you made. I found that when I'm doing writeups or documentation at the end of a development cycle or project, I wished I had tracked my tradeoffs and decisions. Doing so during development can break your flow, and that's where Calamus comes in. It keeps those decisions and reasoning passively in the project, where both the agents and the people working on it can find it.

The core skill maintains two append-only journals. The **engineering journal**
(`docs/dev_journal.md`) records decisions, pivots, constraints, debugging
lessons, and verified milestones. The **product insight journal**
(`docs/product_insights.md`) records user problems, UX friction, positioning,
and roadmap choices. Agents can query relevant entries instead of loading the
whole history. Optional hooks capture checkpoints at compaction, turn, and
session boundaries, when useful context is most likely to be lost.

The beta synthesis skill turns those records into a project overview, decision
log, phase history, or insight writeup. It can add Mermaid diagrams and code
excerpts from the commit associated with a journal entry, while leaving the
journals untouched.

| Skill | Tier | Role |
|---|---|---|
| `calamus` | core | Records and recalls decisions and insights; registers optional capture hooks |
| `calamus-synthesis` | beta | Builds cited writeups from the journals |

The core has no dependency on the beta skill. Synthesis uses the core's
parser, ships beside it in every package, and may change its commands and
output formats between releases.

Both install on **Claude Code**, **Codex CLI**, and **Cursor** from one
source, and any runtime that can run a shell command can drive them.

---

## What's Here

```
skills/calamus/                core: the journaling skill
  SKILL.md                     router: which journal, how to write, how to recall
  references/                  per-journal procedures and schemas (loaded on demand)
  scripts/                     calamus-init | -append | -query | -convert | -install, hook.sh
  scripts/lib/                 schema, renderers, parser, extractor, config, gates
  scripts/backends/            claude | codex | cursor | generic
  scripts/prompts/             snapshot, sweep, and eval-gate prompts for the hooks
  assets/                      calamus.env (all model pins), profiles/, schema/, hosts/, adapter.md
  evals/                       rubric, Level 2 scorer, Level 4 plan, activation experiment
skills/calamus-synthesis/      beta: read-only writeups from the journals
  SKILL.md                     router: pick a mode, run the steps, follow the rules
  references/                  analyst procedure, output contracts, white paper, style, voice
  agents/journal-analyst.md    brief for an optional analysis subagent
  scripts/calamus-synth        extract | diagrams | excerpt | embed | snapshot | check | render
  scripts/lib/                 signals, candidates, excerpts, Mermaid, lint, fidelity
  assets/                      synth.conf, style.conf, JSON schemas, voice template
packaging/                     per-host plugin wrappers: manifests + hooks, both skills linked from skills/
.claude-plugin/                marketplace for the Claude Code plugin
docs/                          design rationale, specs, host facts, and this repo's own journals
tests/run.sh                   offline test suite for both skills
```

---

## Install

For Claude Code, install the plugin from a clone of this repository. The
plugin includes both skills and registers the core's hooks:

```bash
claude plugin marketplace add /path/to/this/repo
claude plugin install calamus@calamus
```

Codex and Cursor packages are in `packaging/codex` and `packaging/cursor`.
Their layouts follow each host's plugin docs; neither has been tested live
(see [docs/host-facts.md](docs/host-facts.md)):

- **Codex:** add `packaging/codex` to a Codex plugin marketplace. Its hooks
  still run only after you review and trust them in `/hooks`.
- **Cursor:** `ln -s "$PWD/packaging/cursor" ~/.cursor/plugins/local/calamus`,
  then restart Cursor. Plugin hooks run only in a trusted workspace.

To install the skills without a plugin and manage hook registration yourself:

```bash
skills/calamus/scripts/calamus-install --host claude-code   # or codex, cursor
```

The installer links both skills into the host's skills directory
(`~/.claude/skills/` for Claude Code, `~/.agents/skills/` for Codex and
Cursor; `--copy` copies instead), with `calamus-synthesis` beside `calamus`
so it can find the core's parser. It prints the hook configuration to merge
and the adapter text to paste into `CLAUDE.md` or `AGENTS.md`. It does not
edit settings or overwrite an existing install. If plugin hooks are already
registered, the installer warns before you add another registration.

In each project, with `CALAMUS` set to the skill directory (the clone's
`skills/calamus`, or the raw install's `~/.claude/skills/calamus`):

```bash
"$CALAMUS/scripts/calamus-init"                          # docs/dev_journal.md + docs/product_insights.md
echo ".calamus/" >> .gitignore                           # hook state and logs
```

Hooks are optional. Without them, the agent writes entries when the adapter
calls for a checkpoint.

### Host matrix

| Event | Claude Code | Codex CLI | Cursor |
|---|---|---|---|
| `pre-compact` — snapshot before context is lost | `PreCompact`, 45 s | `PreCompact`, 45 s | `preCompact`, 45 s |
| `post-compact` — resume marker | `PostCompact`, 10 s | `PostCompact`, 10 s | — |
| `turn-stop` — sweep once enough new text accrues | — | `Stop`, 90 s | `stop`, 90 s |
| `session-end` | `SessionEnd`, 60 s, sweep | `SessionEnd`, 3 s, pending marker | `sessionEnd`, 5 s, pending marker |

- Timeouts above are Calamus settings, not platform defaults. Claude Code
  gives `SessionEnd` 1.5 s by default and raises it to a configured timeout,
  up to 60 s. Codex gives `SessionEnd` 1 s by default and 3 s at most.
  Cursor documents no default or maximum. Sources and access dates are in
  [docs/host-facts.md](docs/host-facts.md).
- Codex runs no hook until you review and trust it with `/hooks`, and asks
  again when a hook changes. Project-local hooks also need a trusted
  `.codex/` layer.
- Cursor imports hooks from `.claude/settings.json`,
  `.claude/settings.local.json`, and `~/.claude/settings.json`. Register one
  or the other, not both (a dedupe window is only a backstop).
- Codex and Cursor behavior is documentation-verified; only Claude Code is
  tested live.
- **Other runtimes:** call `scripts/hook.sh --host generic --event <event>`
  with `{"session_id", "cwd", "transcript_path"}` as JSON on stdin, or set
  `CALAMUS_SESSION_ID`, `CALAMUS_CWD`, and `CALAMUS_TRANSCRIPT`.

### Migrating from `journaling/`

Earlier versions installed copies under `~/.claude/skills/journaling/`,
`~/.claude/hooks/journaling/`, and `~/.codex/hooks/journaling/`. Those keep
working until you replace them: remove the old hook registrations and the
adapter block that points at `journaling/`, then run `calamus-install` and
paste the new adapter. Existing journals need no change — Calamus reads
them as they are and appends in the same Markdown format.

---

## Backends and Models

Hooks call a model through a backend. `CALAMUS_BACKEND=auto` (default) uses
the host's own CLI; set `claude`, `codex`, or `generic` to choose.

| Backend | Command | Model pin (`assets/calamus.env`) |
|---|---|---|
| `claude` | `claude --print --safe-mode --tools "" --model …` | `CALAMUS_CLAUDE_MODEL` |
| `codex` | `codex exec --sandbox read-only …` | `CALAMUS_CODEX_MODEL` |
| `cursor` | disabled: the CLI has no documented model flag or tool switch | `CALAMUS_CURSOR_MODEL` |
| `generic` | `sh -c "$CALAMUS_LLM_CMD"`, prompt on stdin | your command |

- **No silent substitution.** An unavailable backend never falls back to
  another model; the capture becomes a `CALAMUS-PENDING` marker that the
  skill offers to resolve later.
- **Transcript excerpts go to the backend's provider.** Choosing a backend
  from a different provider than your host sends session text there.
  Extraction removes most tool output first, but not everything.
- **Lean path:** `generic` can call an API directly and skip a CLI's fixed
  per-call overhead (measured at ~3.7K input tokens for `claude -p`). It
  needs an API key, so it is opt-in.
- `CALAMUS_LLM_CMD` and `CALAMUS_*_BIN` are honored only from the
  environment or `~/.config/calamus/calamus.env`, never from a project's
  `.calamus/calamus.env`, so a cloned repository cannot run commands.

Configuration precedence: environment, `<project>/.calamus/calamus.env`,
`~/.config/calamus/calamus.env`, `assets/profiles/<backend>.env` (measured
tuning only), `assets/calamus.env`. Files are parsed as data, never sourced.

---

## Journal Formats and Recall

`calamus-init --format md|xml|jsonl` picks the format (`human` = `md`,
`model` = `xml`); after that the file extension is the source of truth.

| Format | For | Notes |
|---|---|---|
| `md` (default) | People | Matches the original Lightweight and Full schemas |
| `xml` | Models | Stream of `<entry>`/`<marker>` elements, no root element |
| `jsonl` | Models | One record per line, header first |

Changing formats does not meaningfully shrink an entry: in one measured
example, XML was 104% of the Markdown size and JSONL was 97–100%. Querying
is what saves context. Reading a whole journal costs about 2.2K tokens at
7 entries and about 150K at 500; `calamus-query --last 3` stays near 1.4K.

```bash
calamus-append --journal engineering < entry.json   # validate, render, append; prints "ok <id>"
calamus-query --brief --last 10                     # index: id, journal, tag, date, title
calamus-query --id 20260927-1630-a1b2               # one entry in full
calamus-query --tag CP-COMPACT-SNAPSHOT --last 1    # where to resume after compaction
calamus-convert --to xml                            # writes docs/*.xml beside the originals
```

---

## Writeups (beta)

`calamus-synthesis` is the beta skill. Its commands and output formats may
change between releases. Ask it to explain a project or a decision ("write
up this project" or "why did we move to SQLite?") and it uses the journals
to build an overview, phase history, decision log, insight writeup,
white-paper scaffold, or focused brief:

```bash
calamus-synth extract --out docs/writeups/2026-10-15-full   # facts.json: records, signals, candidates
calamus-synth diagrams docs/writeups/2026-10-15-full         # timeline, phases, pivots, mind map (.mmd)
calamus-synth excerpt --id <entry> --path src/x.py --symbol f # verbatim code from the commit of that entry
calamus-synth check docs/writeups/2026-10-15-full            # citations, excerpts, diagrams, style lint
```

The engine proposes phase boundaries from time gaps, changes in journal tags,
file turnover, and recorded pivots; the model names the phases. Each claim
cites a journal entry. Code excerpts come from the commit in effect when the
entry was logged. `check` extracts them again and rejects edited excerpts,
paths outside the repository, key and environment files, and lines that look
like secrets. Diagrams are Mermaid source embedded in Markdown. HTML is
written only when requested (`render --html`).

Writeups get an advisory style check and at most two revision passes. An
optional voice profile, kept out of version control in
`.calamus/voice.md` or `~/.config/calamus/voice.md`, restyles the prose;
a fidelity check fails if the restyle changes a cited id, date, number, or
path.

---

## Development

```bash
bash tests/run.sh                                   # offline: Python unit tests + shell tests, both skills
python3 skills/calamus/scripts/lib/gendocs.py --write   # regenerate schema blocks in references/
claude plugin validate packaging/claude-code        # check the Claude Code plugin (offline)
```

Tests never call a model. Design specs:
`docs/superpowers/specs/2026-09-26-calamus-design.md` (core) and
`docs/superpowers/specs/2026-10-15-calamus-synthesis-design.md` (beta).
The reasoning behind each choice is in `docs/design-rationale.md`, and
every host behavior the packages rely on is tracked, with sources, in
`docs/host-facts.md`.

---
## Research Foundation

This repo is built around one core premise: reliable agent skills are context
engineering artifacts, not just prompt snippets. The research points toward
four design constraints that shape the implementation here:

- **Progressive disclosure:** keep discovery metadata tiny, load full
  procedures only on activation, and keep rationale out of `SKILL.md`.
- **Externalized memory:** use journals and examples to preserve useful
  session knowledge outside the model context window.
- **Deterministic lifecycle hooks:** use shell hooks for capture points that
  should not depend on model attention, especially session end and compaction.
- **Eval-backed iteration:** treat journal quality and checkpoint detection as
  measurable behavior with explicit quality gates.

<details>
<summary>Sources and design rationale</summary>

This repo engages with the following body of work. These sources informed
the design of every skill here — particularly the context engineering
constraints, the Agent Skills architecture, the hook-layer integration
patterns, and the eval methodology.

### Context Engineering

**[Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172)**
Liu et al., 2023
The foundational paper documenting U-shaped positional attention bias in
LLMs. Information at the start and end of context is attended to far more
reliably than information in the middle. Core implication for skill design:
important triggers and output format instructions must appear near the top
of any protocol file. Informs why SKILL.md files are short and front-loaded.

**[A Survey of Context Engineering for Large Language Models](https://arxiv.org/abs/2507.13334)**
Mei et al., 2025
Coined "context engineering" as the systematic discipline of curating what
enters the context window. Distinguishes four operations: writing, selecting,
compressing, and isolating information. The framework this repo uses to
think about skill file design.

**[Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering)**
Anthropic, September 2025
Anthropic's formalization of context engineering as the primary design
discipline for reliable agents. Documented how agents processing large
codebases routinely exceed available context through sequential tool calls.

**[Context Rot and Long-Context Degradation](https://stackone.com/blog/agent-suicide-by-context)**
Chroma / StackOne, 2025
A Chroma study tested 18 frontier models and found every one degrades as
context fills, through lost-in-the-middle effects, attention dilution, and
distractor interference. Model correctness starts dropping after 32K tokens.
Motivates keeping each `SKILL.md` a short router (111 lines for the core,
81 for the beta skill).

**[Knowledge Activation: AI Skills as the Institutional Knowledge Primitive](https://arxiv.org/abs/2603.14805)**
2026
Documents the three constraints defining the context window economy: token
budget (hard limit), attention decay (effective capacity is smaller than
nominal), and latency cost (inference cost scales with context). Informs the
strict separation between skill instructions (SKILL.md, always lean) and
design rationale (README, never loaded by agents).

**[Externalization in LLM Agents: Memory, Skills, Protocols and Harness Engineering](https://arxiv.org/abs/2604.08224)**
2026
"Agentic memory stores what the agent learned; skills store how the agent
should act. Both keep information outside the context window until needed."
The conceptual foundation for the skill/journal split in this repo.

**[Less Context, Better Agents: Efficient Context Engineering](https://arxiv.org/abs/2606.10209)**
2026
Shows that for tool-heavy single-session workflows, a lightweight recency
window plus a compact running summary is sufficient — no external store or
retriever required. Informs the journal-as-external-memory design.

### Agent Skills Open Standard

**[Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering)**
Anthropic Engineering, December 2025
The announcement and design rationale for Agent Skills. Introduced progressive
disclosure: name + description (~30–50 tokens) at discovery, full SKILL.md
on activation, referenced files and scripts only during execution.

**[Agent Skills Open Standard](https://agentskills.io)** and
**[Specification](https://agentskills.io/specification)**
Released December 18, 2025
Three-stage loading: Discovery → Activation → Execution. `name` must match
the directory (1–64 lowercase characters), `description` ≤ 1024 characters,
`SKILL.md` under 500 lines, references one level deep. Both skills are
checked against these rules, in `tests/test_skill.sh` and
`tests/test_synth_skill.sh`.

**[Progressive Disclosure as a System Design Pattern](https://swirlai.substack.com/)**
SwirlAI Newsletter, March 2026
"The SKILL.md file organizes information into three layers. The platform
implements the loading logic, deciding when to promote from one layer to the
next." Explains why the open standard achieved immediate cross-platform
adoption.

**[Configuration Smells in AGENTS.md Files](https://arxiv.org/abs/2606.15828)**
2026
Documents anti-patterns in agent configuration: context bloat, skill leakage,
conflicting instructions. Referenced in the skill authoring guidelines.

**[How to Build Your AGENTS.md](https://www.augmentcode.com/guides/how-to-build-agents-md)**
Augment Code, June 2026
An ETH Zurich study found LLM-generated context files reduced task success
rates ~3% and increased inference cost >20%. Human-curated files provided
a marginal 4% gain but still incurred token overhead. Justifies keeping
CLAUDE.md / AGENTS.md adapters under 15 lines.

### Hook-Layer Integration

**[Claude Code Hooks — Complete Guide](https://hidekazu-konishi.com/)**
Konishi, June 2026
Comprehensive reference for all Claude Code hook events, exit-code protocol,
tool matchers, and settings.json hierarchy.

**[All 30 Claude Code Hook Events](https://morphllm.com/claude-code-hooks)**
MorphLLM, June 2026
Documents the full event list including `SessionEnd` (receives `transcript_path`),
`PreCompact`, `PostCompact`, `TaskCreated`, and `TaskCompleted`.

**[SessionEnd vs Stop](https://github.com/luongnv89/claude-howto)**
luongnv89/claude-howto, 2026
"Stop fires after every Claude response. SessionEnd fires once when the
session terminates — exactly what you want for an end-of-session diary entry."
Informs the choice of `SessionEnd` (not `Stop`) for Claude Code journaling.

**[PreCompact and PostCompact Hooks](https://developersdigest.tech/)**
Developers Digest, April 2026
"PreCompact fires just before Claude summarizes older turns. It can block the
compaction, customize the summary strategy, or persist important context before
it gets condensed." Core hook used for compaction-boundary journal capture.

**[Claude Code Compaction and Long-Session Operations Guide](https://hidekazu-konishi.com/)**
Konishi, June 2026
"The PreCompact hook fires immediately before a compaction, with a matcher
that distinguishes manual (/compact) from automatic triggers." Documents
the integration pattern behind the `pre-compact` event.

**[Claude Code Compaction Kept Destroying My Work](https://dev.to/adolan)**
Adolan, DEV Community, April 2026
Documents PreCompact + PostCompact as the production pattern for persistent
memory across compaction events, including the subshell pattern for making
PreCompact hooks crash-safe.

**[precompact-hook by mvara-ai](https://github.com/mvara-ai/precompact-hook)**
GitHub
"The hook fires at the death boundary — the moment between full context and
compaction. A subagent called from the hook has an empty context window,
meaning it can dedicate full attention to interpreting the session." Informed
the snapshot prompt design (`scripts/prompts/snapshot.txt`).

**[Codex CLI Hooks Reference](https://developers.openai.com/codex/hooks)**
OpenAI Developers, read 2026-09-26
`hooks.json` is an object keyed by event name. Events: `SessionStart`,
`SessionEnd`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `PreCompact`,
`PostCompact`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`,
and `Interrupt` — there is no `TaskCompleted`. `SessionEnd` defaults to 1 s
and allows at most 3 s. Project-local hooks load only when the project `.codex/` layer is
trusted. *Correction:* an earlier version of this README said Codex shares
Claude Code's hook schema and supports `TaskCompleted`; it does neither.

**[Codex CLI v0.124.0 — Hooks Engine Stable](https://blakecrosley.com/guides/codex)**
Blake Crosley, June 2026
As of v0.124.0 (April 23, 2026) the Codex CLI hooks engine is marked stable.
New hook events continue to ship in releases.

**[Codex CLI Issue #17532](https://github.com/openai/codex/issues/17532)**
GitHub openai/codex, April 2026
Reported that project-local hook config did not fire in interactive sessions
as of v0.120. Neither confirmed nor refuted against current Codex; Calamus
documents the trusted-layer requirement instead.

**[Claude Code vs Codex CLI 2026 Decision Reference](https://blakecrosley.com/blog/claude-code-vs-codex)**
Blake Crosley
Documents `TaskCreated` and `TaskCompleted` as Claude Code lifecycle events.
*Correction:* its claim that Codex shares them is not supported by Codex's
hooks documentation, and the per-task Codex mode built on it was removed.

**[Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)**
Anthropic, read 2026-09-26
`SessionEnd` hooks share a 1.5 s budget by default; a longer per-hook
`timeout` in settings raises it, up to 60 s. Calamus configures
`timeout: 60` for its sweep.

**[Cursor Hooks](https://cursor.com/docs/agent/hooks)** and
**[Cursor Third-Party Hooks](https://cursor.com/docs/agent/third-party-hooks)**
Cursor, read 2026-09-26
`hooks.json` with `"version": 1`; events include `sessionStart`,
`sessionEnd`, `preCompact`, and `stop`; payloads use `conversation_id` and
`workspace_roots`. Cursor imports Claude Code hooks from
`.claude/settings.json`, which is why Calamus deduplicates by session and
event rather than by host.

**[Cursor CLI Headless Mode](https://cursor.com/docs/cli/headless)**
Cursor, read 2026-09-28
Documents `agent -p --output-format text`, but no model flag and no way to
disable tools, so the Cursor backend ships disabled. *Correction
(2026-10-04):* the [CLI parameters reference](https://cursor.com/docs/cli/reference/parameters)
now documents `--model`; there is still no flag that disables tools, so the
backend stays disabled. The activation runner uses `--model` when
`CALAMUS_CURSOR_MODEL` is set and otherwise labels its results unpinned.

### Eval Methodology

**[LLM Agent Evaluation Metrics in 2026](https://www.confident-ai.com/)**
Confident AI, June 2026
Distinguishes agent tracing (what happened) from agent evaluation (whether
the right decisions were made). Covers tool calling, planning effectiveness,
task completion, and trajectory-level evaluation. Basis for the Level 4
behavioral eval design.

**[Rubric-Based Evals & LLM-as-a-Judge](https://medium.com/)**
Medium / Masood, April 2026
"Analytic rubrics score criterion-by-criterion. This is the cornerstone of
modern Eval Ops; it allows for regression root-cause analysis that a single
holistic score cannot provide." Basis for the five-dimension rubric in
`evals/rubric.md`.

**[LLM as a Judge — Primer and Pre-Built Evaluators](https://arize.com/llm-as-a-judge)**
Arize AI, 2026
"A judge model applies a written rubric to outputs and returns structured
scores. You define what 'good' looks like once; the judge applies it
consistently across thousands of traces." The pattern used in `eval-score.sh`.

**[LLM-as-judge for Multi-Step Agent Evaluation](https://medium.com/)**
Vinod Rane, Medium, May 2026
"Locking judge model versions is now a standard engineering requirement, not
optional. A model provider quietly updating the underlying LLM can change
scoring without any alert." Informs the judge model pinning requirement in
the Level 4 plan.

**[MCP-Bench: Benchmarking Tool-Using LLM Agents](https://arxiv.org/abs/2508.20453)**
arXiv
Uses an LLM-as-judge framework scoring across task completion quality, tool
selection rationale, and planning effectiveness. The judge is provided task
description, final solution, and summarized execution trace. Informs the
Level 4 behavioral eval methodology.

**[A Comprehensive Survey of Self-Evolving AI Agents](https://arxiv.org/abs/2508.07407)**
arXiv
Documents LLM-as-a-Judge in pointwise mode (scoring each output independently
against a rubric) as the standard for scalable evaluation. Notes that LLM
judges can correlate with human judgments, reaching inter-annotator agreement
levels in some domains.

### Product Discovery and Product Strategy

*(Informing the product insight journal)*

**[Continuous Discovery Habits](https://www.producttalk.org/category/continuous-discovery-habits/)**
Teresa Torres / Product Talk
Product insight should be tied to recurring user touchpoints and desired
product outcomes, not one-off feature ideas.

**[Opportunity Solution Trees](https://www.producttalk.org/opportunity-solution-trees/)**
Teresa Torres / Product Talk
Product notes should connect outcomes, opportunities, solutions, and
experiments. Informs the hypothesis and decision fields in the full schema.

**[Jobs to Be Done](https://www.christenseninstitute.org/jobs-to-be-done/)**
Christensen Institute
Product observations should capture the functional, social, and emotional
context behind user behavior. Informs the JTBD lens in the full entry schema.

**[Four Big Risks](https://www.svpg.com/four-big-risks/)**
Silicon Valley Product Group
Product observations should help de-risk value, usability, feasibility, and
business viability. Informs the Product Risk Lens field.

**[Feature Documentation Research](https://arxiv.org/abs/2208.01317)**
arXiv
Product-feature knowledge in GitHub projects is often fragmented and weakly
linked to implementation context. Motivates the dual-journal system with
explicit cross-referencing rather than a single mixed-concern log.

</details>

---

## Design choices

**Keep instructions close to the work.** `SKILL.md` and its references tell
the agent what to do. Rationale and research stay in documentation that the
agent does not need to load for each task.

**Capture at the moment context changes.** An agent may miss a journal entry,
especially near the context limit. Hooks run at lifecycle boundaries and
leave the host alone if capture fails: every path exits 0 and prints nothing.

**Measure entries without rewriting them.** The Level 1 gate flags weak
captures and the Level 2 scorer shows which parts need work. People decide
what to change; neither gate rewrites prompts or journal history.

**Load only what a task needs.** Discovery uses a short description,
activation loads a router, and writing loads the relevant journal reference.
Scripts run when the task calls for them.

**Let the core change slowly.** Journaling runs across sessions and has no
dependency on synthesis. Writeups live in a separate beta skill that can
evolve without expanding the core procedure.
