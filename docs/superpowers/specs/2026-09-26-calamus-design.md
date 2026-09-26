# Calamus — Design Spec

> Status: draft for review. Date: 2026-09-26. Branch: `refactor/calamus`.
> Scope: rebrand this repository from a multi-skill garden into one
> centralized skill named **Calamus**, and rework the hook layer so it is
> host-neutral and model-agnostic across Claude Code, Codex CLI, and Cursor.

## 1. Goals and non-goals

**Goals**

1. One skill, `calamus`, that maintains two append-only journals:
   `docs/dev_journal.md` (engineering decisions) and
   `docs/product_insights.md` (product insights).
2. The skill validates against the Agent Skills specification and installs
   on Claude Code, Codex CLI, and Cursor from a single source.
3. Hook registrations match each host's current documentation.
4. The model is configuration, not code. No script or skill text names a
   model outside one config file.
5. Existing behavior is preserved where it was correct: append-only
   journals, hooks that never block the host, pinned judge models.

**Non-goals**

- Native hook shims for hosts other than the three above. The `generic`
  backend covers other *models*; other *hosts* are out of scope.
- Implementing Level 3 (drift) or Level 4 (behavioral) evals.
- Packaging as a Claude Code or Codex plugin. The layout is compatible with
  a later plugin wrapper; no manifest is added now.
- Per-host transcript readers. The engine feeds a raw transcript tail to the
  backend, as today. Revisit if capture quality proves poor.
- Injecting pending captures at session start (see 4.6).
- Renaming the GitHub repository or the local directory. That is an
  outward-facing action left to the owner.
- Editing any user-global configuration (`~/.claude`, `~/.codex`,
  `~/.cursor`, `~/.agents`) as part of the change.

## 2. Research findings that drive the design

Sources are current documentation fetched 2026-09-26. Items marked
*local* were verified against the installed Claude Code (2.1.283). Codex
CLI and the Cursor agent CLI are not installed in the authoring
environment, so their behavior is documentation-only until tested.

| # | Finding | Source | Consequence |
|---|---|---|---|
| F1 | Agent Skills spec: `name` must match the parent directory, 1–64 chars, lowercase/digits/hyphens; `description` ≤ 1024 chars; keep `SKILL.md` under 500 lines and under ~5000 tokens; references one level deep. | agentskills.io/specification | Skill id is `calamus`. Two schemas merged into one file would be ~560 lines, so `SKILL.md` becomes a router and schemas move to `references/`. |
| F2 | Codex and Cursor discover skills in `.agents/skills` and `~/.agents/skills`. Cursor also reads `.cursor/skills`, `.claude/skills`, `.codex/skills`. Claude Code's docs list `.claude/skills` only. | Codex skills docs; Cursor skills docs; Claude skills docs | Canonical install at `~/.agents/skills/calamus`, symlinked into `~/.claude/skills/`. |
| F3 | Codex has no `TaskCompleted` event. Events: SessionStart, SessionEnd, PreToolUse, PostToolUse, PermissionRequest, PreCompact, PostCompact, UserPromptSubmit, SubagentStart, SubagentStop, Stop, Interrupt. | Codex hooks docs | The Codex "task boundary" mode is dead code and is removed. |
| F4 | Codex `hooks.json` is an object keyed by event name, each holding `{matcher?, hooks:[{type, command, timeout}]}`. Project-local `.codex/hooks.json` loads only when the project `.codex/` layer is trusted; non-managed hooks need review via `/hooks`. | Codex hooks docs | The current adapter's array-with-`"event"` shape is replaced. |
| F5 | Claude `SessionEnd` shares a 1.5 s budget unless a hook sets `timeout` (raised to match, up to 60 s). Codex `SessionEnd` defaults to 1 s and allows at most 3 s. | Claude hooks docs; Codex hooks docs | Claude registers `timeout: 60`. Codex/Cursor session-end is stub-only by default. |
| F6 | `claude --safe-mode` disables hooks, skills, plugins, MCP and CLAUDE.md for the run (*local*). `--bare` also skips hooks. Codex documents no guard against `codex exec` re-triggering hooks. | `claude --help` (*local*); Codex hooks docs | Recursion is guarded by an inherited env var, independent of host flags. |
| F7 | Cursor hooks are GA: `sessionStart`, `sessionEnd`, `preCompact`, `stop`, and others; config is `hooks.json` with `"version": 1`; exit 2 blocks, other non-zero fails open. Cursor imports Claude Code hooks from `.claude/settings.json` (SessionEnd, PreCompact, Stop mapped; no PostCompact equivalent). Payload uses `conversation_id` and `workspace_roots`. | Cursor hooks docs; Cursor third-party hooks docs | New Cursor host shim; payload normalizer; dedupe to cover double registration. |
| F8 | Model names are hardcoded in four scripts (`claude-haiku-4-5`, `gpt-5.4-mini`), and three scripts duplicate payload parsing, journal creation, and the Level 1 gate. | Repository | One engine plus a backend axis; pins move to one config file. |

## 3. Layout

The repository root keeps development files. The distributable skill lives
at `skills/calamus/`, which is also the layout Claude Code plugins use.

```
README.md                      overview, install per host, host matrix, research
CLAUDE.md  AGENTS.md           development guidance for this repo (Calamus)
docs/
  design-rationale.md          design decisions and eval stack (from journaling/README.md)
  superpowers/specs/           this spec
  dev_journal.md               this repo's own journals (append-only)
  product_insights.md
tests/
  run.sh                       offline hook-engine tests
  fixtures/                    synthetic payloads and transcripts per host
skills/calamus/
  SKILL.md                     router, name: calamus
  references/
    engineering-journal.md     triggers, tags, Lightweight + Full schema
    product-insights.md        triggers, tags, evidence rules, schemas
  scripts/
    hook.sh                    single hook entry
    lib/                       payload.sh  gate.sh  journal.sh  config.sh  timeout.py
    backends/                  claude.sh  codex.sh  cursor.sh  generic.sh
    prompts/                   snapshot.txt  sweep.txt  eval-gate.txt
    calamus-init               creates both journal files
    calamus-install            symlinks the skill, prints host config
  assets/
    calamus.env                defaults: pins, thresholds
    adapter.md                 host-neutral snippet for CLAUDE.md / AGENTS.md
    hosts/{claude-code,codex,cursor}/hooks.json     registration templates
    examples/                  example entries (from journaling/docs/)
  evals/                       rubric.md  eval-score.sh  level-4-plan.md  golden/
```

### 3.1 `SKILL.md` (router)

Target: ≤ 150 lines. Frontmatter:

```yaml
---
name: calamus
description: >-
  Live project memory for agent sessions. Maintains an engineering decision
  journal (docs/dev_journal.md) and a product insight journal
  (docs/product_insights.md). Use when making architecture or implementation
  decisions, pivoting, fixing a non-obvious bug, hitting a constraint, or
  finishing a verified milestone, and when observing user pain, UX friction,
  positioning, roadmap trade-offs, or growth signals worth recalling later.
  Also use to resolve CALAMUS-PENDING markers. Append-only.
compatibility: Any Agent Skills-compatible agent. Optional lifecycle hooks need bash and python3.
metadata:
  version: "3.0.0"
---
```

Body sections, all procedure-only (no rationale, no citations):

1. Which journal: signal → journal → reference file. Read
   `references/engineering-journal.md` before writing an engineering entry,
   `references/product-insights.md` before a product entry, both plus the
   cross-log rule when an observation spans both.
2. Initialization: run `scripts/calamus-init`; if scripts cannot run, create
   the file with the header given in the relevant reference.
3. Noise gate: the entry must answer at least four of the questions listed in
   the relevant reference; otherwise use the Lightweight schema or ask.
4. Append safety and file-writing behavior (shared): always append, never
   overwrite, check recent entries before appending, append a new entry to
   revise a decision; if files cannot be written, output the entry in a
   copyable code fence and say the file was not modified.
5. Compaction awareness: do not log manually before `/compact` when hooks are
   installed; otherwise write a `[CP-COMPACT-SNAPSHOT]` entry first.
6. Cross-log rule and `[CROSS-LOG]` marker format.
7. Pending markers: a `<!-- CALAMUS-PENDING ... id:<id> -->` marker means a
   hook could not reach a model. When at a natural boundary, offer to draft
   the entry from the session context and append it after the marker with a
   `<!-- CALAMUS-RESOLVED id:<id> -->` line. Never delete the marker.

### 3.2 References

`references/engineering-journal.md` and `references/product-insights.md` are
the current `SKILL.md` bodies with these removals: frontmatter, "Global
Adapter", "Relationship to …", and the Append Safety / File-Writing sections
now hoisted into the router. Schemas, tags, triggers, evidence rules, and the
initialization header are kept verbatim. Each stays ≤ 300 lines.

### 3.3 Adapter (`assets/adapter.md`)

One host-neutral snippet, ≤ 15 lines, no filesystem paths:

- Use the `calamus` skill for `./docs/dev_journal.md` and
  `./docs/product_insights.md`.
- At the end of meaningful engineering, product, UX, growth, onboarding,
  retention, or roadmap work, evaluate whether an entry should be logged.
  Prefer the Lightweight schema in long or compressed sessions. Never
  overwrite. Never fabricate.
- When one observation has both dimensions, write separate entries linked by
  `[CROSS-LOG]`.
- If Calamus hooks are installed, do not log manually before `/compact`.

## 4. Hook engine

Entry: `scripts/hook.sh --host <claude-code|codex|cursor> --event <event>`.
Registration templates pass both flags; nothing is auto-detected.

### 4.1 Semantic events

| Event | Purpose | Writes |
|---|---|---|
| `pre-compact` | Snapshot progress before context is lost | `[CP-COMPACT-SNAPSHOT]` entry |
| `post-compact` | Boundary marker for the next context window | Marker only, no model call |
| `turn-stop` | Growth-gated sweep at a turn boundary | Checkpoint entries |
| `session-end` | Final sweep, or a stub when the host's budget is too small | Checkpoint entries or a pending stub |

### 4.2 Pipeline

1. **Recursion guard.** If `CALAMUS_ACTIVE=1`, exit 0. Backends export
   `CALAMUS_ACTIVE=1` to the child process, so any host that re-fires hooks
   from a headless run is stopped regardless of host flags.
2. **Normalize payload** (one `python3` call; missing or invalid JSON yields
   empty fields, never an error):

   | Field | claude-code | codex | cursor |
   |---|---|---|---|
   | session id | `session_id` | `session_id` | `conversation_id`, else `session_id` |
   | cwd | `cwd` | `cwd` | first of `workspace_roots`, else `CURSOR_PROJECT_DIR` |
   | transcript | `transcript_path` | `transcript_path` (may be null) | `transcript_path`, else `CURSOR_TRANSCRIPT_PATH` |

3. **Resolve root and state.** Root is the git top level of `cwd`, else
   `cwd`. State lives in `<root>/.calamus/` (`logs/hook.log`, `state/`),
   replacing `.claude/logs`, `.codex/logs`, and `/tmp` files. `.calamus/` is
   never committed; `calamus-init` prints a reminder to ignore it.
4. **Gate.** Skip with a log line when: no transcript file; transcript below
   `CALAMUS_MIN_BYTES_*`; for `turn-stop` and `session-end`, growth since the
   last sweep (per-session size cache) below `CALAMUS_MIN_GROWTH`; or the
   same `(host, session, event)` already ran within `CALAMUS_DEDUPE_SECS`.
   `pre-compact` has no growth gate.
5. **Prompt.** `prompts/<snapshot|sweep>.txt` plus the last
   `CALAMUS_TAIL_*` bytes of the transcript. Prompts are shipped files and
   cannot be overridden by project configuration.
6. **Backend call** under a portable timeout (`lib/timeout.py`; macOS has no
   `timeout`), limit `CALAMUS_BACKEND_TIMEOUT`.
7. **Append.** `NO_CHECKPOINT` writes nothing. Otherwise append the existing
   marker comment (`SESSION`, `COMPACT`, or `POST-COMPACT RESUME`) and the
   entry to `docs/dev_journal.md`, creating it with the standard header if
   absent.
8. **Failure path.** Backend missing, non-zero, empty, or timed out: append
   `<!-- CALAMUS-PENDING: <date> | id:<session> | host:<h> | event:<e> -->`
   and record the transcript path in `<root>/.calamus/state/pending/<id>`.
   The journal never contains a local path.
9. **Level 1 gate** on what was written (skipped for pending stubs and
   markers): same backend, prompt `prompts/eval-gate.txt`. A failing verdict
   appends the existing `EVAL-FAIL` note, now naming backend and model.
   Disabled by `CALAMUS_LEVEL1_GATE=off`.
10. **Exit 0 and print nothing** on every path. The whole pipeline runs in a
    subshell with `|| true`. This preserves the repository's hard constraint
    that `PreCompact` can never block compaction, and extends it to every
    event so stdout is never parsed as host directives.

### 4.3 Backends

Contract: `backends/<name>.sh` reads the full prompt on stdin, writes plain
text to stdout, exits non-zero on failure or unavailability. Each backend
must run read-only, with no tools, with user hooks disabled, and with
`CALAMUS_ACTIVE=1` exported.

| Backend | Invocation | Status |
|---|---|---|
| `claude` | `claude --print --safe-mode --tools "" --model "$CALAMUS_CLAUDE_MODEL"` | Flags verified locally |
| `codex` | `codex exec --sandbox read-only --skip-git-repo-check -c model_reasoning_effort=low --model "$CALAMUS_CODEX_MODEL" -o <tmpfile>`; binary from `PATH`, then `CALAMUS_CODEX_BIN`, then the desktop app's bundled CLI | Carried over from the current script; Codex not installed locally |
| `cursor` | Cursor CLI headless mode. Flags are confirmed from Cursor's CLI documentation during implementation; if they cannot be confirmed, the backend ships as a stub that exits non-zero with an "unverified" log line | Unverified |
| `generic` | `sh -c "$CALAMUS_LLM_CMD"` with the prompt on stdin | Covers any other CLI or local model |

`CALAMUS_BACKEND=auto` resolves to the backend matching `--host`. An
explicit value (`claude`, `codex`, `cursor`, `generic`) overrides it, so a
Codex user can choose `claude`. Switching backend sends transcript excerpts
to that provider; the README states this.

**No silent model substitution.** A backend never falls back to a different
backend or model. Unavailable means the failure path (4.2 step 8) for
capture, and a clear error for the Level 2 scorer.

### 4.4 Configuration

Precedence: environment variables, then `<root>/.calamus/calamus.env`, then
`${XDG_CONFIG_HOME:-$HOME/.config}/calamus/calamus.env`, then the shipped
`assets/calamus.env`. Files are parsed as data, never sourced or evaluated:
only `CALAMUS_[A-Z0-9_]+=value` lines are read.

**Security rule:** `CALAMUS_LLM_CMD` and `CALAMUS_*_BIN` are honored only from
the environment or the user-level file, never from the project-level file,
so a cloned repository cannot cause command execution at hook time.

| Key | Default | Notes |
|---|---|---|
| `CALAMUS_BACKEND` | `auto` | |
| `CALAMUS_LLM_CMD` | empty | generic backend; env or user-level only |
| `CALAMUS_CLAUDE_MODEL` | `claude-haiku-4-5` | pinned; unchanged from current scripts |
| `CALAMUS_CODEX_MODEL` | `gpt-5.4-mini` | pinned; unchanged from current scripts |
| `CALAMUS_CURSOR_MODEL` | empty | no baseline yet |
| `CALAMUS_CODEX_BIN` | empty | explicit Codex binary; env or user-level only |
| `CALAMUS_EVAL_BACKEND` | `claude` | Level 2 scorer; independent of host |
| `CALAMUS_LEVEL1_GATE` | `on` | |
| `CALAMUS_BACKEND_TIMEOUT` | `25` | seconds per backend call; two calls fit a 60 s host budget |
| `CALAMUS_TAIL_SWEEP` / `CALAMUS_TAIL_SNAPSHOT` | `28000` / `20000` | bytes, as today |
| `CALAMUS_MIN_BYTES_SWEEP` / `CALAMUS_MIN_BYTES_SNAPSHOT` | `800` / `500` | as today |
| `CALAMUS_MIN_GROWTH` | `2000` | as today's Codex Stop gate |
| `CALAMUS_DEDUPE_SECS` | `30` | |
| `CALAMUS_SESSION_END_MODE` | `auto` | `auto` = `sweep` on claude-code, `stub` on codex/cursor |

Pin policy (carried over): default values equal the current pins, so moving
them into config is a relocation, not a model change. Changing a pin or the
backend makes scores incomparable; the Level 2 report header records the
resolved backend and model, and any pin change requires re-baselining.

### 4.5 Host matrix and registration

| Semantic event | Claude Code | Codex CLI | Cursor |
|---|---|---|---|
| `pre-compact` | `PreCompact`, timeout 45 | `PreCompact`, timeout 45 | `preCompact`, timeout 45 |
| `post-compact` | `PostCompact`, timeout 10 | `PostCompact`, timeout 10 | none |
| `turn-stop` | not used | `Stop`, timeout 90 | `stop`, timeout 90 |
| `session-end` | `SessionEnd`, timeout 60, sweep | `SessionEnd`, timeout 3, stub | `sessionEnd`, timeout 5, stub |

Templates in `assets/hosts/<host>/hooks.json` use the placeholder
`__CALAMUS_DIR__` for the skill directory, and each command is a single
string of the form `__CALAMUS_DIR__/scripts/hook.sh --host <h> --event <e>`
so the same form works on every host.

Claude Code (`settings.json`):

```json
{"hooks": {
  "PreCompact":  [{"hooks": [{"type": "command", "timeout": 45,
    "command": "__CALAMUS_DIR__/scripts/hook.sh --host claude-code --event pre-compact"}]}],
  "PostCompact": [{"hooks": [{"type": "command", "timeout": 10,
    "command": "__CALAMUS_DIR__/scripts/hook.sh --host claude-code --event post-compact"}]}],
  "SessionEnd":  [{"hooks": [{"type": "command", "timeout": 60,
    "command": "__CALAMUS_DIR__/scripts/hook.sh --host claude-code --event session-end"}]}]
}}
```

Codex uses the same object-keyed shape with `PreCompact`, `PostCompact`,
`Stop` (`turn-stop`), and `SessionEnd`. Cursor uses
`{"version": 1, "hooks": {"preCompact": [...], "stop": [...], "sessionEnd": [...]}}`
with flat `{"command", "timeout"}` entries.

Notes:

- Codex `SessionEnd` and Cursor `sessionEnd` run in stub mode: they append a
  pending stub only if uncaptured growth exists. `CALAMUS_SESSION_END_MODE=sweep`
  promotes them once a host's real budget is measured.
- Cursor imports `.claude/settings.json` hooks by default. Use either
  `.cursor/hooks.json` or the import, not both; the dedupe window is a
  backstop only.
- Codex project-local hooks require a trusted `.codex/` layer and `/hooks`
  review. The installer documents this rather than working around it.

### 4.6 Installer

`scripts/calamus-install --host <claude-code|codex|cursor> [--copy]`:

1. Symlinks `skills/calamus` to `~/.agents/skills/calamus` (Codex, Cursor)
   or `~/.claude/skills/calamus` (Claude Code). `--copy` copies instead, as a
   fallback if a host does not follow symlinks. It refuses to overwrite an
   existing destination.
2. Prints the host's `hooks.json` content with `__CALAMUS_DIR__` resolved to
   the absolute installed path, and names the file to merge it into.
3. Prints `assets/adapter.md` and the file to paste it into.

It does not edit any host settings file. Symlink-following behavior of each
host is confirmed during verification (section 7).

## 5. Rebrand and documentation changes

- `README.md`: rewritten around Calamus. Tagline: the reed pen that preceded
  the quill, a scribe for agent sessions. Removes the garden table and the
  unstarted `travel-agent`. Adds install per host, the host matrix, the
  backend axis, and the transcript-to-provider note. Keeps the research
  bibliography with corrections: the claims that Codex supports
  `TaskCompleted` and shares Claude's hook schema are removed or restated,
  and Cursor and Agent Skills specification sources are added.
- `docs/design-rationale.md`: `journaling/README.md` design decisions,
  merged and updated. "Why `TaskCompleted` for Codex dispatch chains" is
  replaced by "Why growth-gated `Stop` for Codex and Cursor".
- `CLAUDE.md`, `AGENTS.md`: rewritten for a single skill. Three layers
  become: skill (router plus references), engine (hook, backends, host
  templates), adapter. Hard constraints keep their intent with updated
  locations: exit 0 now covers every event in `hook.sh`; the pinned model
  strings live in `assets/calamus.env` with unchanged values; journals stay
  append-only.
- `.gitignore`: add `.calamus/`; remove the `/tmp/codex-journal-*.cache`
  entry, which never matched a repository path.
- This repository's own `docs/dev_journal.md` and `docs/product_insights.md`
  are append-only; new entries reference the rebrand, old entries are not
  rewritten.

## 6. File migration (history-preserving `git mv`)

| From | To |
|---|---|
| `journaling/skills/engineering-journal/SKILL.md` | `skills/calamus/references/engineering-journal.md` (trimmed per 3.2) |
| `journaling/skills/product-insight-journal/SKILL.md` | `skills/calamus/references/product-insights.md` (trimmed per 3.2) |
| `journaling/hooks/*.sh` | replaced by `scripts/hook.sh`, `lib/`, `prompts/`; removed only after tests pass |
| `journaling/adapters/*.md` | `assets/adapter.md`, `assets/hosts/*/hooks.json` |
| `journaling/scripts/journal-init` | `skills/calamus/scripts/calamus-init` |
| `journaling/evals/*` | `skills/calamus/evals/*` |
| `journaling/docs/*` | `skills/calamus/assets/examples/` |
| `journaling/README.md` | `docs/design-rationale.md` |

Existing installs under `~/.claude` or `~/.codex` are copies, so they keep
working until the owner replaces them. Migration steps for the owner's
global setup are documented in the README; nothing outside this repository
is changed.

`evals/eval-score.sh` fixes: locate `rubric.md` relative to the script first
(today it looks in the target project first), call the judge through
`backends/` using `CALAMUS_EVAL_BACKEND`, and write the resolved backend and
model into the report header.

## 7. Verification

The repository has no toolchain today; this change adds a small one.

1. `tests/run.sh` (bash, offline). Each case runs in a temporary git repo
   with the `generic` backend pointed at a canned-output command. Cases:
   every host × event with valid payloads appends the expected marker and
   entry; `NO_CHECKPOINT` appends nothing; missing, tiny, and null
   transcripts skip; empty stdin and malformed JSON exit 0; a failing or
   hanging backend produces a pending stub with no absolute path and exit 0;
   `CALAMUS_ACTIVE=1` is a no-op; two identical events inside the dedupe
   window append once; the growth gate skips small `turn-stop` growth;
   project-level config cannot set `CALAMUS_LLM_CMD`; Level 1 failure appends
   `EVAL-FAIL`; nothing is ever written to stdout.
2. Skill validation: `skills-ref validate skills/calamus` if it can be
   obtained; otherwise a check in `tests/run.sh` for name equals directory,
   description length, `SKILL.md` and reference line counts, and reference
   depth.
3. `shellcheck` on all scripts if available.
4. Live smoke test on Claude Code only, in a scratch project with a
   project-level registration: a short `claude -p` session confirms
   `SessionEnd` completes its sweep within the 60 s timeout (confirms F5);
   a manual `/compact` confirms `PreCompact` and `PostCompact`; both
   symlinked and `--copy` installs are checked for skill discovery.
5. Codex and Cursor: synthetic payload fixtures built from documented fields
   only. Their live behavior is labeled documentation-verified, not tested.

## 8. Risks and unverified items

- Codex flags (`exec -o`, `--sandbox`, `-c model_reasoning_effort`) and live
  `Stop`/`SessionEnd`/trust behavior are unverified locally. The old note
  that project-local Codex hooks do not fire (issue 17532, v0.120) is
  neither confirmed nor refuted against current Codex.
- Cursor's headless CLI flags, `sessionEnd` timeout, and whether `stop` and
  `sessionEnd` payloads include `transcript_path` (documented as "if
  enabled") are unverified. With no transcript, hooks log and skip.
- Docs were read through a summarizing fetch tool that misreported at least
  one flag (`--safe-mode`); the two highest-impact claims (F3, F5) were
  cross-checked with a second fetch, the rest were not.
- A raw transcript tail includes tool output and JSONL structure; capture
  quality may vary by host format. Deferred per non-goals.
- `turn-stop` runs a model call at qualifying turn ends on Codex and Cursor,
  adding latency; `CALAMUS_MIN_GROWTH` tunes it.

## 9. Git workflow

Work happens on `refactor/calamus`, branched from `main` (the only branch).
Local commits at checkpoints: spec; structure move; engine plus tests;
host templates and installer; docs and rebrand. No push, no PR, no tag. The
suggested tag for release is `v3.0.0` from `main` after review, at the
owner's discretion.
