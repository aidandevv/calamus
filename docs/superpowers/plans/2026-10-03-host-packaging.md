# Calamus Host Packaging Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Keep one canonical skill and engine, and ship host-native packages so hooks register with the skill instead of by hand-merged JSON. Prove it on Claude Code first. Add Codex and Cursor only after their formats are verified.

**Decision record:** Option C (shared core, per-host packaging) from the research pass in `docs/research-prompt-platform-variants.md`. Option B (separate skills per host) is rejected: host differences are in hooks, trust, timeouts, and install, not in the journaling workflow. A generator is deferred until hand-written wrappers drift.

## Global Constraints

Unchanged from `2026-09-27-calamus.md`: hooks exit 0 and print nothing; journals append-only; model pins only in `assets/calamus.env`; config is data; no absolute paths in journals; bash 3.2 and Python 3 stdlib only. Additionally:

- `SKILL.md` body and `references/` stay identical across hosts. Only discovery metadata, hook registration, and install text may differ.
- No `context: fork` in any generated frontmatter: journaling must run in the working session's context.
- Every host fact used in a template must be marked verified (with source and date) or left out.
- Local commits only; no push.

## Open facts to settle first (Task 1 blocks the rest)

| Fact | Status | Why it matters |
|---|---|---|
| Codex and Cursor standalone skill path (`~/.agents/skills/`) | Unverified | `calamus-install` hardcodes it for both |
| Cursor `sessionEnd` timeout | Unverified (5s in current template) | Template value |
| Claude `SessionEnd` default 1.5s, raised by explicit hook timeout up to 60s | Verified | Our 60s is configured, not a platform default |
| Codex `SessionEnd` default 1s, max 3s | Verified | Matches template |
| Codex requires trust review of bundled hooks | Verified | Cannot be packaged away; docs must say so |
| Cursor imports Claude Code hooks | Verified | Double-registration risk |

## Tasks

### Task 1: Verify host facts and record them

- [ ] Check the unverified rows above against current official docs and with a live smoke test where a CLI is installed.
- [ ] Add `docs/host-facts.md`: one row per fact, with source URL, access date, and verified/unverified status.
- [ ] Correct `calamus-install` output and the README timeout wording: default vs configured vs maximum.
- [ ] Verify: `bash tests/run.sh` passes; `tests/test_install.sh` updated for any path change.

### Task 2: Activation experiment (decision gate)

- [ ] Write `skills/calamus/evals/activation/prompts.jsonl`: about 10 direct, 10 indirect, 10 near-miss prompts, each labeled `expect: activate|skip`.
- [ ] Write a runner that, per host CLI available, records whether the skill activated and which reference loaded. Calls a model, so run only on request.
- [ ] Compare the shared description against one tuned variant.
- [ ] Decision rule: keep per-host descriptions only if recall improves by at least 10 points or precision by at least 5 with an identical body. Otherwise keep one shared description.
- [ ] Record the result in the journal whether or not it changes the plan.

### Task 3: Claude Code plugin wrapper

- [ ] Add `packaging/claude-code/.claude-plugin/plugin.json` and `hooks/hooks.json` using `${CLAUDE_PLUGIN_ROOT}/skills/calamus/scripts/hook.sh`, with the same three events and timeouts as `assets/hosts/claude-code/hooks.json`.
- [ ] Plugin `skills/calamus` is a symlink or copy of the canonical `skills/calamus/`, never an edited fork.
- [ ] Test: a layout test asserts the plugin hook commands and timeouts equal the host template, and that no file under the plugin differs from canonical besides the manifests.
- [ ] Live check (on request): `claude plugin install` from a local marketplace, then one compaction and one session end each produce an entry or pending marker.
- [ ] `calamus-install --host claude-code` prints the plugin install command and warns not to also merge settings hooks.

### Task 4: Duplicate-registration guard

- [ ] `calamus-install` detects Calamus hooks already present in `.claude/settings.json` or `.cursor/hooks.json` and warns before printing more.
- [ ] Test the Cursor-imports-Claude case with a fixture: two registrations, one journal entry (relies on existing `calamus_dedupe`).

### Task 5: Codex and Cursor packages (after Task 1)

- [ ] Only for formats verified in Task 1. Reuse `assets/hosts/<host>/hooks.json` as the source; add a manifest wrapper per host.
- [ ] Codex: document the hook trust review step in the install output; do not claim zero-touch.
- [ ] Cursor: `version: 1` hooks file; call out workspace trust and the Claude import overlap.
- [ ] Layout test equivalent to Task 3 for each host.

### Task 6: Generator (deferred, conditional)

- [ ] Start only if two or more host packages have drifted from `assets/hosts/` in review. Then add a stdlib `scripts/lib/` or `tools/` build that emits manifests from `assets/hosts/`, with a CI check that regenerating leaves no diff.

### Task 7: Docs

- [ ] README install section: plugin install first, raw symlink as the advanced fallback.
- [ ] `docs/design-rationale.md`: add why per-host semantic skills were rejected and why a generator is deferred.
- [ ] `CLAUDE.md` and the adapter stay unchanged unless install guidance changes.

## Review focus

1. **Fork drift:** any host package whose `SKILL.md` or `references/` differs from canonical. Task 3 and 5 layout tests enforce byte equality.
2. **Hook equivalence:** plugin hooks must match the host template in events, timeouts, and the exit-0-silent behavior.
3. **Unverified claims in templates:** none allowed past Task 1.
4. **Double registration:** plugin plus manual settings merge on the same host.
