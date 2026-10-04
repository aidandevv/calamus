# Host Facts

Every host behavior that Calamus templates, installer output, or packages
depend on. A fact is `verified` only when an official source states it; a
template may use only verified facts. Re-check a row before changing the
template that depends on it, and update its access date.

Live checks: only the Claude Code CLI was available on 2026-10-03. Codex
and Cursor rows are documentation-verified.

| Fact | Host | Source | Accessed | Status |
|---|---|---|---|---|
| User skills load from `~/.claude/skills/<name>/` | Claude Code | https://code.claude.com/docs/en/skills | 2026-10-03 | verified |
| User skills load from `~/.agents/skills/` (repo: `.agents/skills/`; admin: `/etc/codex/skills`) | Codex | https://learn.chatgpt.com/docs/build-skills | 2026-10-03 | verified |
| User skills load from `~/.agents/skills/` and `~/.cursor/skills/`; `~/.claude/skills/` and `~/.codex/skills/` load as legacy paths | Cursor | https://cursor.com/docs/context/skills | 2026-10-03 | verified |
| Command hooks default to a 600 s timeout | Claude Code | https://code.claude.com/docs/en/hooks | 2026-10-03 | verified |
| `SessionEnd` hooks share a 1.5 s budget by default; a longer per-hook `timeout` in settings raises it, up to 60 s | Claude Code | https://code.claude.com/docs/en/hooks | 2026-10-03 | verified |
| A plugin-registered `SessionEnd` hook raises the 1.5 s budget the same way a settings hook does | Claude Code | (docs name settings only) | 2026-10-03 | unverified |
| Hooks default to 600 s; `SessionEnd` and `Interrupt` default to 1 s with a 3 s maximum | Codex | https://learn.chatgpt.com/docs/hooks | 2026-10-03 | verified |
| Non-managed hooks, including plugin hooks, run only after review and trust in `/hooks`; trust is tied to the hook's hash | Codex | https://learn.chatgpt.com/docs/hooks | 2026-10-03 | verified |
| Hooks load from `~/.codex/hooks.json`, `~/.codex/config.toml`, and the same files under a repo `.codex/` | Codex | https://learn.chatgpt.com/docs/hooks | 2026-10-03 | verified |
| `hooks.json` requires `"version": 1`; per-hook `timeout` exists with an undocumented platform default | Cursor | https://cursor.com/docs/agent/hooks | 2026-10-03 | verified |
| `sessionEnd` default or maximum timeout (template sets 5 s as a Calamus choice) | Cursor | (not documented) | 2026-10-03 | unverified |
| Project hooks run in any trusted workspace | Cursor | https://cursor.com/docs/agent/hooks | 2026-10-03 | verified |
| Imports Claude Code hooks from `.claude/settings.json`, `.claude/settings.local.json`, and `~/.claude/settings.json`, on by default | Cursor | https://cursor.com/docs/reference/third-party-hooks | 2026-10-03 | verified |
| Plugin layout: `.claude-plugin/plugin.json` (only `name` required), `skills/<name>/SKILL.md`, `hooks/hooks.json` with a top-level `hooks` key | Claude Code | https://code.claude.com/docs/en/plugins-reference | 2026-10-03 | verified |
| `${CLAUDE_PLUGIN_ROOT}` resolves in hook commands; quote it in shell-form commands | Claude Code | https://code.claude.com/docs/en/plugins-reference | 2026-10-03 | verified |
| Local marketplace: `.claude-plugin/marketplace.json` with `name`, `owner`, and `plugins` entries whose `source` starts with `./`; a source that is or traverses a symlink is not read | Claude Code | https://code.claude.com/docs/en/plugins/marketplace-reference | 2026-10-03 | verified |
| Plugin layout: `.codex-plugin/plugin.json`, root `skills/`, `hooks/hooks.json`; hooks get `PLUGIN_ROOT` and `CLAUDE_PLUGIN_ROOT` | Codex | https://learn.chatgpt.com/docs/hooks | 2026-10-03 | verified |
| Local marketplace at `.agents/plugins/marketplace.json` with `"source": {"source": "local", "path": ...}` | Codex | https://developers.openai.com/codex/plugins/build | 2026-10-03 | verified |
| Plugin layout: `.cursor-plugin/plugin.json`, `skills/`, `hooks/hooks.json`; hook commands may use `${CURSOR_PLUGIN_ROOT}` or `${CLAUDE_PLUGIN_ROOT}`; local plugins load from `~/.cursor/plugins/local` | Cursor | https://cursor.com/docs/reference/plugins | 2026-10-03 | verified |
| Whether a Cursor plugin `hooks/hooks.json` needs `"version": 1` and accepts `timeout` | Cursor | (plugin reference shows neither) | 2026-10-03 | unverified |
| Hook commands run through a shell, so `"${PLUGIN_ROOT}"` in a plugin hook command expands (docs show `~` in a command, which implies a shell) | Codex | (not stated) | 2026-10-03 | unverified |
| A plugin's symlinked `skills/calamus` directory is followed when the plugin is installed or loaded | Codex | (not documented) | 2026-10-03 | unverified |
| A plugin's symlinked `skills/calamus` directory is followed when the plugin is loaded from `~/.cursor/plugins/local` | Cursor | (not documented) | 2026-10-03 | unverified |
| Headless CLI `agent` takes `--model <model>`, `-p/--print` (all tools, including write and shell), `--output-format text\|json\|stream-json`, `--trust`, and `--sandbox enabled\|disabled` | Cursor | https://cursor.com/docs/cli/reference/parameters | 2026-10-04 | verified |
| Without `--force`, headless edits are proposed, not applied | Cursor | https://cursor.com/docs/cli/headless | 2026-10-04 | verified |
| stream-json events: `.type` (`system` init with `.model`, `assistant`, `tool_call`, `result`); file reads at `.tool_call.readToolCall.args.path` | Cursor | https://cursor.com/docs/cli/headless | 2026-10-04 | verified |
| Skill activation in a headless run appears as a tool call that reads `calamus/SKILL.md` (no real transcript captured yet) | Cursor | (not documented) | 2026-10-04 | unverified |
