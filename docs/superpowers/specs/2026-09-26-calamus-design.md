# Calamus — Design Spec

> Status: draft for review. Date: 2026-09-26; amended 2026-09-27 (incremental
> capture window, transcript extractor, generic host, backend profiles and
> gating, entry schema and journal formats). Branch: `refactor/calamus`.
> Scope: rebrand this repository from a multi-skill garden into one
> centralized skill named **Calamus**, and rework the hook layer so it is
> host-neutral and model-agnostic across Claude Code, Codex CLI, and Cursor.

## 1. Goals and non-goals

**Goals**

1. One skill, `calamus`, that maintains two append-only journals:
   `docs/dev_journal.md` (engineering decisions) and
   `docs/product_insights.md` (product insights). The file extension follows
   the chosen format (goal 8).
2. The skill validates against the Agent Skills specification and installs
   on Claude Code, Codex CLI, and Cursor from a single source.
3. Hook registrations match each host's current documentation.
4. The model is configuration, not code. No script or skill text names a
   model outside one config file.
5. Existing behavior is preserved where it was correct: append-only
   journals, hooks that never block the host, pinned judge models.
6. Capture is token-bounded: each hook call sends only new, distilled
   session text to the backend, never a repeated or tool-output-heavy tail.
7. Any runtime that can shell out and supply a transcript file can call the
   engine through a `generic` host, without a native shim.
8. Journals are written in one of three formats from a single schema: `md`
   (human-readable, the default), `xml`, or `jsonl` (model-optimized). Every
   write is validated, and recall is by query, not by reading whole files.

**Non-goals**

- Native hook registration for hosts other than the three above. The
  `generic` backend covers other *models*; the `generic` host covers any
  caller that can shell out (section 4.5).
- Implementing Level 3 (drift) or Level 4 (behavioral) evals.
- Packaging as a Claude Code or Codex plugin. The layout is compatible with
  a later plugin wrapper; no manifest is added now.
- Provider-specific structured-output modes (JSON-schema flags on individual
  CLIs). Validation with a fail-safe replaces them (4.2 step 7).
- Injecting pending captures at session start. Pending markers are resolved
  through the skill instead (section 3.1, item 7).
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

### 2.1 Token accounting

Estimates are characters divided by 4, not tokenizer counts.

| Cost | Current | Calamus |
|---|---|---|
| Always loaded: skill descriptions | ~190 tokens (two skills) | ~150 tokens |
| Always loaded: adapter | ~430 tokens | at most 15 lines, ~200 tokens |
| On activation, one journal | ~2.3–2.6K tokens | ~3.3–3.5K (router plus one reference; not yet drafted) |
| On activation, both journals | ~4.8K tokens | about the same |
| Hook engine, in the working agent's context | 0 tokens | 0 tokens |
| Hook engine, separate backend call | up to ~7K input per sweep, and the same tail is resent on every qualifying `turn-stop` | bounded by the caps in 4.4; only text added since the last sweep, tool output removed (4.2, 4.7) |

Consolidation is token-neutral, and slightly worse for a single-journal
task. Its value is one name, one install, and one config. The token savings
come from the hook changes in 4.2 and 4.7.

Fixed per-call overhead: a six-word prompt through `claude -p --safe-mode
--tools ""` on the pinned model consumed 3,698 input tokens with no cache
hits (measured once, Claude Code 2.1.283, 2026-09-27; Codex and Cursor are
unmeasured). A capture makes up to two calls, so about half of a ~15K-token
capture was overhead before extraction. Once extraction shrinks the payload,
call count dominates, so thresholds are tuned to amortize the overhead (4.4)
and the model-judged gate is sampled (4.2 step 10).

### 2.2 Journal format cost

One real entry (an engineering Lightweight entry from this repository's
journal) serialized four ways. Sizes are characters; tokens are characters
divided by 4.

| Format | Chars | vs Markdown |
|---|---|---|
| Markdown (current) | 1,821 | 100% |
| XML, readable tags | 1,899 | 104% |
| JSON line, full keys | 1,823 | 100% |
| JSON line, 1-letter keys | 1,772 | 97% |

A model-optimized format does not make entries smaller; it changes cost
through retrieval. Reading the whole journal to resume costs about 2.2K
tokens at 7 entries and grows linearly: at the current average of ~1.2K
characters per entry, about 150K tokens at 500 entries. A query returning
the last 3 entries stays near 1.4K tokens. The formats exist to make that
query and write-time validation possible (4.8, 4.9).

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
    format-xml.md              generated from the schema; read only for xml journals
    format-jsonl.md            generated from the schema; read only for jsonl journals
  scripts/
    hook.sh                    single hook entry
    lib/                       payload.sh  gate.sh  config.sh  timeout.py  extract.py
                               schema.py  render.py  records.py
    backends/                  claude.sh  codex.sh  cursor.sh  generic.sh
    prompts/                   snapshot.txt  sweep.txt  eval-gate.txt
    calamus-init               creates both journal files (--format md|xml|jsonl)
    calamus-install            symlinks the skill, prints host config
    calamus-append             validate, render, and append entries (agent write path)
    calamus-query              recall entries without reading whole files
    calamus-convert            write a journal in another format, never overwriting
  assets/
    calamus.env                defaults: pins, thresholds
    profiles/                  claude.env  codex.env  cursor.env  generic.env (measured tuning)
    schema/entry.schema.json   single source: record types, fields, enums, renderings
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
  Also use to recall earlier decisions and to resolve CALAMUS-PENDING
  markers. Append-only.
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
7. Pending markers: a pending marker (`<!-- CALAMUS-PENDING ... id:<id> -->`,
   or the equivalent `marker` record in `xml` and `jsonl` journals) means a
   hook could not reach a model. When at a natural boundary, offer to draft
   the entry from the session context and append it after the marker with a
   matching resolved marker. Never delete the marker.
8. Format and writing: the journal's file extension sets the format (`.md`,
   `.xml`, `.jsonl`). If scripts can run, write entries with
   `scripts/calamus-append`, which validates against the schema, renders in
   the project's format, and reports errors to fix. If not, write directly
   using the template in the matching reference (`format-xml.md`,
   `format-jsonl.md`; the Markdown templates are in the journal references).
9. Recall: to resume or check a prior decision, run `scripts/calamus-query`
   (`--brief` for an index, then `--id` for one entry) instead of reading a
   journal file whole. Read the file directly only if scripts cannot run.

### 3.2 References

`references/engineering-journal.md` and `references/product-insights.md` are
the current `SKILL.md` bodies with these removals: frontmatter, "Global
Adapter", "Relationship to …", and the Append Safety / File-Writing sections
now hoisted into the router. Tags, triggers, evidence rules, and guidance
are kept verbatim. The Lightweight and Full Markdown schema blocks are
generated from `assets/schema/entry.schema.json` between BEGIN/END GENERATED
comments and checked by a test, so they cannot drift from the validator.
`format-xml.md` and `format-jsonl.md` (about 40 lines each) are generated
the same way and loaded only for journals in that format. Each reference
stays ≤ 300 lines.

### 3.3 Adapter (`assets/adapter.md`)

One host-neutral snippet, ≤ 15 lines, no filesystem paths:

- Use the `calamus` skill for `./docs/dev_journal.md` and
  `./docs/product_insights.md` (or their `.xml` / `.jsonl` equivalents).
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

   | Field | claude-code | codex | cursor | generic |
   |---|---|---|---|---|
   | session id | `session_id` | `session_id` | `conversation_id`, else `session_id` | `session_id`, else `CALAMUS_SESSION_ID` |
   | cwd | `cwd` | `cwd` | first of `workspace_roots`, else `CURSOR_PROJECT_DIR` | `cwd`, else `CALAMUS_CWD` |
   | transcript | `transcript_path` | `transcript_path` (may be null) | `transcript_path`, else `CURSOR_TRANSCRIPT_PATH` | `transcript_path`, else `CALAMUS_TRANSCRIPT` |

3. **Resolve root and state.** Root is the git top level of `cwd`, else
   `cwd`. State lives in `<root>/.calamus/` (`logs/hook.log`, `state/`),
   replacing `.claude/logs`, `.codex/logs`, and `/tmp` files. `.calamus/` is
   never committed; `calamus-init` prints a reminder to ignore it.
4. **Gate.** Skip with a log line when: no transcript file; transcript below
   `CALAMUS_MIN_BYTES_*`; or the same `(host, session, event)` already ran
   within `CALAMUS_DEDUPE_SECS`.
5. **Read the window.** Take the transcript's current end offset (`eof`).
   For `turn-stop` and `session-end`, start at the per-session sweep offset
   in `.calamus/state/`; for `pre-compact`, start at zero. In both cases
   read at most the last `CALAMUS_RAW_WINDOW` raw bytes, pass them through
   the host extractor (4.7), and keep the last `CALAMUS_TAIL_*` characters
   of the extracted text. `turn-stop` and `session-end` skip with a log line
   when the extracted text is shorter than `CALAMUS_MIN_TEXT`, leaving the
   offset unchanged so text accumulates until it is worth a call.
   `pre-compact` has no text minimum beyond non-empty.
6. **Prompt.** `prompts/<snapshot|sweep>.txt` plus the extracted text. The
   prompt asks for one JSON object, `{"entries": [...]}`, whose fields come
   from the schema (4.8); a schema-derived shape block is substituted into
   the prompt at build time, so the prompt cannot drift from the validator.
   The same prompt serves every journal format. Prompts are shipped files
   and cannot be overridden by project configuration.
7. **Backend call and validation.** Call the backend under a portable
   timeout (`lib/timeout.py`; macOS has no `timeout`), limit
   `CALAMUS_BACKEND_TIMEOUT`. Then strip code fences, parse the JSON, treat
   `{"entries": []}` or the literal `NO_CHECKPOINT` as no checkpoint, and
   validate every entry against the schema. Unparseable or invalid output is
   a backend failure (step 9); the rejected payload is saved to
   `<root>/.calamus/state/rejected/<id>.json`. There is no repair retry,
   because a retry would pay the fixed per-call overhead again.
8. **Append.** No checkpoint writes nothing. Otherwise render the marker
   (`session`, `compact`, or `resume`) and the entries in the project's
   journal format (4.8) and append them to the engineering journal, creating
   it with the format's header if absent. After a verdict (entries or no
   checkpoint) on `turn-stop` or `session-end`, advance the sweep offset to
   `eof`; `pre-compact` never moves it.
9. **Failure path.** Backend missing, non-zero, empty, or timed out.
   `turn-stop`: log only and leave the offset unchanged, so the next event
   retries the same text. `pre-compact` and `session-end`: append a
   `pending` marker (`<!-- CALAMUS-PENDING: <date> | id:<session> | host:<h> |
   event:<e> -->` in `md`, the equivalent `marker` record in `xml` and
   `jsonl`) and record the transcript path in
   `<root>/.calamus/state/pending/<id>`. The journal never contains a local
   path. Invalid model output takes the same path.
10. **Level 1 gate** on what was written (skipped for pending stubs and
    markers). Structural validity is enforced earlier, at step 7, on every
    capture at no model cost. The model-judged check uses
    `prompts/eval-gate.txt` through the same backend: on every capture when
    `CALAMUS_LEVEL1_GATE=full`, on 1 in `CALAMUS_LEVEL1_SAMPLE` captures when
    `sampled` (a per-project counter in `.calamus/state/`), and never when
    `structural` or `off`. A failing verdict appends an `eval-fail` marker
    (the existing `EVAL-FAIL` note in `md`) naming the backend and model. The
    judge reads entries rendered as Markdown whatever the journal's format,
    so verdicts stay comparable across formats.
11. **Exit 0 and print nothing** on every path. The whole pipeline runs in a
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
| `claude` | `claude --print --safe-mode --tools "" --model "$CALAMUS_CLAUDE_MODEL"` | Flags verified locally. `--bare` is not used: it failed with "Not logged in" under login-based auth (measured 2026-09-27) |
| `codex` | `codex exec --sandbox read-only --skip-git-repo-check -c model_reasoning_effort=low --model "$CALAMUS_CODEX_MODEL" -o <tmpfile>`; binary from `PATH`, then `CALAMUS_CODEX_BIN`, then the desktop app's bundled CLI | Carried over from the current script; Codex not installed locally |
| `cursor` | Cursor CLI headless mode. Flags are confirmed from Cursor's CLI documentation during implementation; if they cannot be confirmed, the backend ships as a stub that exits non-zero with an "unverified" log line | Unverified |
| `generic` | `sh -c "$CALAMUS_LLM_CMD"` with the prompt on stdin | Covers any other CLI or local model |

`CALAMUS_BACKEND=auto` resolves to the backend matching `--host`. An
explicit value (`claude`, `codex`, `cursor`, `generic`) overrides it, so a
Codex user can choose `claude`. Switching backend sends transcript excerpts
to that provider; the README states this.

**No silent model substitution.** A backend never falls back to a different
backend or model. Unavailable means the failure path (4.2 step 9) for
capture, and a clear error for the Level 2 scorer.

**Lean path.** `generic` can point at a direct API call, which avoids the
CLI's fixed per-call overhead (2.1). It needs an API key, so it is opt-in
and documented in the README.

### 4.4 Configuration

Precedence: environment variables, then `<root>/.calamus/calamus.env`, then
`${XDG_CONFIG_HOME:-$HOME/.config}/calamus/calamus.env`, then the backend
profile `assets/profiles/<backend>.env`, then the shipped
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
| `CALAMUS_LEVEL1_GATE` | `sampled` | `structural` (free check only), `sampled` (free check every capture, model judge on 1 in `CALAMUS_LEVEL1_SAMPLE`), `full` (model judge every capture), `off` |
| `CALAMUS_LEVEL1_SAMPLE` | `4` | |
| `CALAMUS_BACKEND_TIMEOUT` | `25` | seconds per backend call; two calls fit a 60 s host budget |
| `CALAMUS_TAIL_SWEEP` / `CALAMUS_TAIL_SNAPSHOT` | `28000` / `20000` | characters of extracted text sent to the backend; same numbers as today's byte caps |
| `CALAMUS_RAW_WINDOW` | `262144` | max raw transcript bytes read per call |
| `CALAMUS_EXTRACT` | `on` | `off` sends the raw tail, as today |
| `CALAMUS_MIN_BYTES_SWEEP` / `CALAMUS_MIN_BYTES_SNAPSHOT` | `800` / `500` | minimum total transcript size, as today |
| `CALAMUS_MIN_TEXT` | `8000` | minimum new extracted characters for `turn-stop` and `session-end`; replaces the raw-byte growth gate. About 2K tokens, so content is at least a third of a call given the measured ~3.7K fixed overhead (2.1). Provisional until a backend is measured. |
| `CALAMUS_DEDUPE_SECS` | `30` | |
| `CALAMUS_SESSION_END_MODE` | `auto` | `auto` = `sweep` on claude-code, `stub` on codex/cursor |
| `CALAMUS_FORMAT` | `md` | `md`, `xml`, or `jsonl`; `human` is an alias for `md` and `model` for `xml`. Read by `calamus-init` and when a journal does not exist yet; an existing journal's file extension wins (4.8). |

Pin policy (carried over): default values equal the current pins, so moving
them into config is a relocation, not a model change. Changing a pin or the
backend makes scores incomparable; the Level 2 report header records the
resolved backend and model, and any pin change requires re-baselining.
Moving capture input from a raw tail to extracted text (4.7) also changes
what the model sees, so it is validated as described in section 7.

**Backend profiles.** `assets/profiles/<backend>.env` holds provider-specific
tuning as data: `CALAMUS_MIN_TEXT`, the tail caps, and the backend timeout.
A profile value must carry a `# measured:` comment giving the number, CLI
version, and date; a key without a measurement is omitted so the shipped
default applies. Profiles never set model pins, which stay in
`assets/calamus.env` so every pin is one grep away. Profiles ship for
`claude` (measured), `codex`, `cursor`, and `generic` (empty until measured).
Provider-specific prompt overlays (`prompts/<backend>/<name>.txt`, resolved
before `prompts/<name>.txt`) are added only when a Level 2 comparison shows a
measured gap on that provider; none ship initially. Everything else,
including the skill text, ships once for all providers.

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
  pending stub only if at least `CALAMUS_MIN_TEXT` characters of extracted
  text remain past the sweep offset. `CALAMUS_SESSION_END_MODE=sweep`
  promotes them once a host's real budget is measured.
- Cursor imports `.claude/settings.json` hooks by default. Use either
  `.cursor/hooks.json` or the import, not both; the dedupe window is a
  backstop only.
- Codex project-local hooks require a trusted `.codex/` layer and `/hooks`
  review. The installer documents this rather than working around it.
- `--host generic` has no registration template. A custom agent, CI job, or
  SDK callback invokes the four events directly, with the payload as JSON on
  stdin (`session_id`, `cwd`, `transcript_path`) or as `CALAMUS_SESSION_ID`,
  `CALAMUS_CWD`, and `CALAMUS_TRANSCRIPT`. `CALAMUS_BACKEND=auto` has no host
  CLI to resolve to, so it uses `generic` when `CALAMUS_LLM_CMD` is set and
  otherwise takes the failure path. `session-end` defaults to `sweep`, since
  the caller controls its own time budget.

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

### 4.7 Transcript extraction

`scripts/lib/extract.py <host> <path> <start> <raw-window> <cap>` reads the
transcript from `max(start, eof - raw-window)`, drops a leading partial
line, and prints JSON `{"eof": <offset>, "text": "<extracted>"}`. The engine
uses `eof` as the next sweep offset (4.2 step 8).

Output is plain text, one item per line:

```
USER: <text>
ASSISTANT: <text>
[tool] <name>: <argument summary, at most 120 characters>
[result] <first 200 characters>
```

Kept: user and assistant text; tool calls as one-line summaries (they carry
the files-affected signal); the start of each tool result (it carries test
and build evidence). Dropped: reasoning and thinking blocks, signatures and
encrypted content, system and metadata records, binary and image data, and
the remainder of long tool results.

| Host | Extractor | Status |
|---|---|---|
| claude-code | Parses Claude Code's JSONL records (`user` and `assistant` records whose message content blocks are `text`, `tool_use`, `tool_result`, or `thinking`) | Block and field names are confirmed against a real local transcript during implementation; only aggregate statistics are recorded |
| codex, cursor, generic | Generic JSONL harvester: for each line keep string values under `text`, `content`, `message`, `output`; skip subtrees under `thinking`, `reasoning`, `encrypted_content`, `signature`; use a `role` of `user` or `assistant` as the line prefix; pass non-JSON lines through unchanged | Unverified: no Codex or Cursor transcript samples exist in the authoring environment. Replaced by host-specific extractors once samples are available |

Fail-safe: if the extractor errors, times out, or returns empty text for a
non-empty window, the engine logs `extract-fallback` and sends the raw tail
(the last `CALAMUS_TAIL_*` bytes), so extraction can never stop a capture.
`CALAMUS_EXTRACT=off` forces the raw tail. Extraction removes most tool
output from what is sent to a backend, which reduces, but does not
eliminate, incidental content leaving the session.

### 4.8 Entry schema and journal formats

**One schema.** `assets/schema/entry.schema.json` is the single source for
every record the journals hold. Per record type it defines the fields,
whether each is required, its shape (`text`, `list`, `enum`, `code`, or a
small group), allowed enum values (tags, evidence strength, risk classes),
the Markdown label it renders under, and the XML element and JSONL key.
Renderers, the validator, the query parser, the prompt shape block, and the
generated reference docs are all derived from it. Markdown labels are chosen
so `md` output matches today's Lightweight and Full schemas. Schema version
is 1; each entry carries `schema="1"`.

| Record | Variants | Notes |
|---|---|---|
| `entry`, engineering | `lightweight`, `full`, `snapshot` | Tags are the `CP-*` list. `snapshot` is `CP-COMPACT-SNAPSHOT`: summary, files in progress, decisions, next step, open questions |
| `entry`, product | `lightweight`, `full` | Tags are the `PI-*` list; evidence strength `strong`, `medium`, `weak`; risk class from the six-item lens |
| `marker` | `session`, `compact`, `resume`, `pending`, `resolved`, `eval-fail` | Everything the hooks and skill write outside entries, so every write is a valid record |

Every entry has `id` (`YYYYMMDD-HHMM-<4 hex>`, derived from its content so a
repeated write is detected), `tag`, `date`, and `title`. A cross-log link is
a `crosslog` record with `journal`, `tag`, `date`, and `title`, which
renders as today's `[CROSS-LOG]` blockquote in `md`.

| Format | Files | Audience | Append form |
|---|---|---|---|
| `md` | `docs/dev_journal.md`, `docs/product_insights.md` | Human-readable; matches today's entries | Markdown with HTML-comment markers |
| `xml` | `docs/dev_journal.xml`, `docs/product_insights.xml` | Model-optimized | A stream of `<entry>` and `<marker>` elements with no root element and a leading comment; readers wrap it in a root before parsing. Text is escaped and code snippets use CDATA |
| `jsonl` | `docs/dev_journal.jsonl`, `docs/product_insights.jsonl` | Model-optimized | One JSON object per line, a header record first. A JSON array is not used because it cannot be appended |

XML template for an engineering Lightweight entry (generated from the
schema and checked by a test):

```xml
<entry type="engineering" variant="lightweight" schema="1" id="20260927-1630-a1b2" tag="CP-DEBUG" date="2026-09-27">
  <title>Short title</title>
  <summary>Decision made and why, 1–2 sentences.</summary>
  <files><file>path/or/module</file></files>
  <tradeoff>What was accepted or rejected, and why.</tradeoff>
  <evidence status="verified">How we know it worked.</evidence>
  <followups><item>Open question</item></followups>
  <crosslog journal="product" tag="PI-UX-FRICTION" date="2026-09-27">Linked entry title</crosslog>
</entry>
```

Rendering rules shared by all formats: an empty required list renders as
`None identified.` in `md` and as an empty element or array elsewhere;
`evidence` with status `unverified` and empty text renders as
`Not yet verified.` in `md`.

**The flag.** `CALAMUS_FORMAT=md|xml|jsonl` (`human` is `md`, `model` is
`xml`) is read by `calamus-init --format` and when a journal does not yet
exist. After that the journal's file extension is the source of truth, so the
agent needs no environment access, the hooks and the skill always agree, and
formats never mix in one project. If more than one format's journal exists,
`CALAMUS_FORMAT` breaks the tie, else `md` with a logged warning.

**Who writes markup.** Backends never write XML or Markdown. They return
JSON fields (4.2 step 6); code validates, renders, and appends. That removes
escaping errors, keeps one prompt and one eval baseline for all formats, and
guarantees XML and JSONL journals never receive a malformed record.

### 4.9 Writing, recall, and conversion

- `scripts/calamus-append --journal <engineering|product>` reads a JSON
  object or `{"entries": [...]}` on stdin, validates against the schema,
  refuses an `id` already present, renders in the project's format, appends,
  and prints `ok <id>`. On failure it prints the field errors and exits
  non-zero so the agent can correct and retry. It is the agent's write path
  when scripts can run, and it enforces append-only.
- `scripts/calamus-query [--journal engineering|product|both] [--last N]
  [--tag T] [--since DATE] [--file PATH] [--id ID] [--type entry|marker]
  [--brief] [--out md|xml|jsonl]` reads any format through `lib/records.py`.
  `--brief` prints one line per entry (id, tag, date, title) so an agent can
  list first and fetch by `--id` second. Output defaults to the journal's own
  format. Markdown journals are parsed by heading and label; content that
  matches no schema label is kept in a `body` field, so old hand-written
  entries stay queryable.
- `scripts/calamus-convert --to <md|xml|jsonl> [--journal ...]` reads a
  journal in any format and writes it in another, next to the original. It
  refuses to overwrite and never deletes. Conversion from `md` is lossy for
  free-form entries, whose text moves into `body`.
- `calamus-init --format <fmt>` creates both journals in that format.
- `eval-score.sh` loads entries through `records.py` and always judges their
  Markdown rendering, so Level 2 scores are comparable across formats.
- The `resume` marker carries the id of the latest snapshot (kept in
  `.calamus/state/`), so recall after compaction is
  `calamus-query --tag CP-COMPACT-SNAPSHOT --last 1`.

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
- The README documents the format flag, the measured format cost (2.2), and
  that model formats save tokens through query, not smaller entries.

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
model into the report header. It loads entries through `lib/records.py`, so
it scores journals in any format.

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
6. Extraction and window tests in `tests/run.sh`, on synthetic transcripts
   per host: user and assistant text kept; thinking and long tool results
   dropped; tool calls summarized; a partial leading line dropped; a second
   sweep sends only text added since the first (the fake backend records its
   stdin and the test asserts no overlap); the offset does not advance on
   backend failure and does advance on `NO_CHECKPOINT`; extractor failure
   and empty output fall back to the raw tail.
7. Token measurement on a real local Claude Code transcript, read-only,
   recording only aggregates (raw bytes, extracted characters, and a
   characters/4 token estimate) in the engineering journal. Extraction ships
   with `CALAMUS_EXTRACT=on` only if a before/after Level 2 comparison on the
   same session shows no regression; otherwise it ships `off` until fixed.
8. `--host generic` tests: payload as stdin JSON and as environment
   variables, all four events, and `auto` resolution with and without
   `CALAMUS_LLM_CMD`.
9. Gate and profile tests: the structural check runs on every capture and
   rejects an entry missing a required field; `sampled` invokes the model
   judge on exactly 1 in N captures using the state counter; profile
   precedence is env, project, user, profile, defaults; every profile value
   carries a `# measured:` comment; no profile sets a model pin.
10. Overhead calibration: record each available backend's fixed per-call
    overhead (trivial-prompt usage report) in its profile comment;
    unavailable backends stay unmeasured.
11. Schema and format tests: render then parse returns the same record in all
    three formats; the `md` rendering of a Lightweight record equals a golden
    file matching today's Markdown schema byte for byte; text containing
    `<`, `&`, `]]>`, quotes, unicode, and multi-line code survives a round
    trip in every format; XML journals parse after wrapping in a root; every
    JSONL line parses; the validator rejects a missing required field, a bad
    tag, and a bad enum value; generated reference blocks and templates equal
    the checked-in ones.
12. Writer and reader tests: invalid or unparseable backend output takes the
    failure path, saves the rejected payload, and appends nothing to an `xml`
    or `jsonl` journal; `calamus-append` reports readable errors, refuses a
    duplicate `id`, and never overwrites; `calamus-query` filters, `--brief`,
    and `--id` behave identically on all three formats and on this
    repository's own Markdown journals (every existing entry yields a tag,
    date, and title); `calamus-convert` round-trips `md`, `xml`, `jsonl`, and
    back on fixtures, refuses to overwrite, and leaves the original
    untouched; format detection with more than one journal present.
13. Prompt change check: the extraction plus JSON-field pipeline ships only if
    a before/after Level 2 comparison against the current Markdown-writing
    prompt, on the same sessions, shows no regression (extends item 7).

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
- Extraction can drop evidence (long tool results are truncated), and its
  Codex, Cursor, and generic paths are untested on real transcripts. The
  raw-tail fallback and the before/after Level 2 check in section 7 bound
  the risk.
- `turn-stop` runs a model call at qualifying turn ends on Codex and Cursor,
  adding latency; `CALAMUS_MIN_TEXT` tunes it.
- The fixed-overhead figure is one measurement on one CLI version and moves
  with CLI releases; profile comments record version and date so stale
  values are visible. Codex and Cursor overheads are unknown, and their
  profiles inherit provisional defaults.
- Constraining the backend to JSON fields could change entry quality
  compared with free Markdown; the Level 2 comparison (section 7, item 13)
  decides. Models occasionally emit malformed JSON; with no repair retry, a
  failure costs one pending marker, never a bad journal.
- Parsing hand-written Markdown journals is heuristic, and `calamus-convert`
  from `md` is lossy for free-form entries. An XML journal is a fragment
  stream, not a standalone well-formed document.
- The schema adds a source of truth to maintain. Generated docs and a drift
  test bound the cost. Schema changes bump `schema` and need a conversion
  path, which is not designed now.
- Append and query need `python3` and the ability to run scripts; without
  them the skill falls back to direct writes from the templates and
  whole-file reads.

## 9. Git workflow

Work happens on `refactor/calamus`, branched from `main` (the only branch).
Local commits at checkpoints: spec; structure move; engine plus tests;
host templates and installer; docs and rebrand. No push, no PR, no tag. The
suggested tag for release is `v3.0.0` from `main` after review, at the
owner's discretion.
