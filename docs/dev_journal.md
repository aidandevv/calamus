# Engineering Development Journal
> Chronological log of architecture decisions, implementation pivots,
> constraint discoveries, verification results, and engineering milestones.

---

### [CP-MILESTONE] | 2026-06-20: Transfer Artifact Removed From Repository History

**Summary:** Removed the Claude-to-Codex transfer handoff artifact from the repository and rewrote the single root commit so the public branch no longer carries it. Added Mermaid diagrams to the README surfaces without changing the existing explanatory copy.

**Files/Modules Affected:** `.gitignore`, `README.md`, `journaling/README.md`, `journaling/docs/example-entries.md`, Git refs/history.

**Key Trade-off:** Chose a history rewrite and force push because the artifact had been committed in the root commit; a normal deletion would have left it recoverable from branch history.

**Evidence:** `git log --all -- handoff.md` returned no commits, `git rev-list --objects --all | rg '(^| )handoff\.md$'` returned no reachable objects, and `git status --short --branch` showed `main...origin/main` clean.

**Follow-ups:** GitHub may retain server-side unreachable objects for a period after force-push; contact GitHub support if the artifact must be purged from provider backups or caches.

---

### [CP-MILESTONE] | 2026-06-20: README Research Section Reframed for GitHub

**Summary:** Reworked the root README presentation so the implemented skill is the only visible garden entry, the research foundation opens with an executive summary, and the detailed source list is collapsible with source titles carrying the links.

**Files/Modules Affected:** `README.md`, `docs/dev_journal.md`.

**Key Trade-off:** Kept the detailed research bibliography intact for credibility while moving it behind a GitHub-supported disclosure block so the README reads cleaner on first pass.

**Evidence:** Verified the markdown structure with `sed`, `git diff -- README.md`, and `rg` checks for `travel`, `Research Foundation`, `<details>`, and `</details>`.

**Follow-ups:** None identified.

---

### [CP-MILESTONE] | 2026-06-20: Journaling Skill Roles Made Visible in READMEs

**Summary:** Added a compact root README subtable for the engineering and product journal skills, then expanded `journaling/README.md` with a dedicated two-journal explanation, examples, and cross-log diagram.

**Files/Modules Affected:** `README.md`, `journaling/README.md`, `docs/dev_journal.md`, `docs/product_insights.md`.

**Key Trade-off:** Kept the root README concise for portfolio scanning while moving the fuller examples and operational nuance into the journaling README.

**Evidence:** Verified the markdown diff and Mermaid fences with `git diff -- README.md journaling/README.md` and `rg` checks for journal skill links, Mermaid blocks, and output-file references.

**Follow-ups:** None identified.

> **[CROSS-LOG]** Product-facing README clarity logged in `./docs/product_insights.md`
> — see [PI-POSITIONING] | 2026-06-20: Journal Roles Need to Be Visible Before Installation.

---

### [CP-MILESTONE] | 2026-06-20: README Skill Presentation Shifted to Abstract Blocks

**Summary:** Reworked the README skill presentation from catalog/table-first into block-style explanations, with `journaling/` framed as a live project-memory layer and the two subskills described as nested decision/insight logs.

**Files/Modules Affected:** `README.md`, `journaling/README.md`, `docs/dev_journal.md`, `docs/product_insights.md`.

**Key Trade-off:** Preserved scan-friendly metadata tables where useful, but moved the motivation and value proposition into prose blocks so the public README flows more like an authored portfolio artifact.

**Evidence:** Read back the top sections of both READMEs and reviewed `git diff -- README.md journaling/README.md`.

**Follow-ups:** None identified.

> **[CROSS-LOG]** Product-facing positioning change logged in `./docs/product_insights.md`
> — see [PI-POSITIONING] | 2026-06-20: Journaling Should Read Like a Live Memory Layer.

---

### [CP-MILESTONE] | 2026-06-20: Root README Reframed as Modular Skill Garden

**Summary:** Updated the root README so `agent-skills-garden` reads as a collection of independent top-level skill modules, with `journaling/` presented as one self-contained module and its engineering/product skills nested underneath.

**Files/Modules Affected:** `README.md`, `docs/dev_journal.md`, `docs/product_insights.md`.

**Key Trade-off:** Kept the strong journaling abstract while adding enough garden-level structure that future unrelated skills can be added without making journaling feel like the whole repository.

**Evidence:** Reviewed the first screen of `README.md`, checked the diff, and ran `git diff --check`.

**Follow-ups:** None identified.

> **[CROSS-LOG]** Product-facing modularity change logged in `./docs/product_insights.md`
> — see [PI-POSITIONING] | 2026-06-20: Garden README Needs Modular Skill Blocks.

---

<!-- SESSION: 2026-09-26 16:30 | calamus design -->

### [CP-ARCHITECTURE] | 2026-09-26: Calamus Design — Common Core With Host Shims

**Summary:** Designed the consolidation of the journaling module into one skill, `calamus`: a router `SKILL.md` plus per-journal references, one host-neutral hook engine with a separate model-backend axis, and thin per-host registration shims for Claude Code, Codex CLI, and Cursor. The spec is written; nothing is implemented yet.

**Files/Modules Affected:** `docs/superpowers/specs/2026-09-26-calamus-design.md` (new). Implementation will touch all of `journaling/`, `README.md`, `CLAUDE.md`, `AGENTS.md`.

**Key Trade-off:** Chose a common core plus host shims over one universal script (host differences would become branches in a single script) and over per-host copies (format, prompts, and model pins would triplicate and drift, as the current scripts already show). The firing host's CLI is only the default backend; the backend is its own axis with a generic stdin-to-stdout escape hatch. A pinned model never silently falls back to another.

**Evidence:** Read the current Claude Code, Codex, Cursor, and Agent Skills docs; `claude --help` confirmed `--safe-mode` and `--bare` locally. Doc-derived findings that the existing hooks are stale: Codex has no `TaskCompleted` event and uses a different `hooks.json` shape, and Claude `SessionEnd` has a 1.5 s default budget while `session-end.sh` makes two model calls with no `timeout` registered (not reproduced live). Codex and Cursor CLIs are not installed locally, so their behavior is documentation-only.

**Follow-ups:** Owner review of the spec, then an implementation plan. Live-test the Claude `SessionEnd` timeout behavior and confirm Cursor headless CLI flags during implementation.

> **[CROSS-LOG]** Positioning change logged in `./docs/product_insights.md`
> — see [PI-POSITIONING] | 2026-09-26: Rebrand From Skill Garden to One Named Skill.

---

<!-- SESSION: 2026-09-27 20:36 | calamus spec amendment -->

### [CP-ARCHITECTURE] | 2026-09-27: Token-Bounded Capture and Generic Host Added to Calamus Spec

**Summary:** Amended the Calamus spec so hook capture sends only text added since the last sweep (capped), passes it through a per-host transcript extractor that drops thinking blocks and long tool output, and can be called from any runtime through a `generic` host. Prompted by a portability and token-cost review of the original design.

**Files/Modules Affected:** `docs/superpowers/specs/2026-09-26-calamus-design.md` (sections 2.1, 4.2, 4.4, 4.5, 4.7, 7, 8).

**Key Trade-off:** Committed to the extractor before measuring how noisy real transcripts are, accepting that the Codex, Cursor, and generic paths are best-effort until samples exist. Bounded that risk with a raw-tail fallback and a before/after Level 2 check that decides whether extraction ships on by default. Consolidating into one skill was found to be token-neutral, so it is justified by install and naming, not cost.

**Evidence:** Sizes measured from the current files (`wc -c`: adapter 1709 B, the two SKILL.md files 9017 B and 10371 B), converted with a characters/4 estimate rather than a tokenizer. The earlier sweep design resent a 28000-byte tail on every qualifying turn-stop, read from the existing hook scripts. Platform hook and skill support for Gemini CLI, Copilot CLI, Bedrock AgentCore, and Google ADK comes from search summaries, not full docs. Nothing implemented yet.

**Follow-ups:** Measure raw versus extracted size on a real local transcript during implementation; confirm the extractor's field names against it; obtain Codex and Cursor transcript samples.

> **[CROSS-LOG]** Positioning implication logged in `./docs/product_insights.md`
> — see [PI-POSITIONING] | 2026-09-27: State Where Calamus Applies and Where It Does Not.

---

<!-- SESSION: 2026-09-27 21:11 | calamus overhead tuning -->

### [CP-CONSTRAINT] | 2026-09-27: Fixed Per-Call Overhead Dominates Hook Capture Cost

**Summary:** Measured the fixed token overhead of a headless `claude -p` call and found it is the main cost of a hook capture once transcript extraction shrinks the payload. Amended the Calamus spec to add backend profiles for measured tuning, raise the default minimum-text threshold, and make the model-judged Level 1 gate sampled instead of per-capture.

**Files/Modules Affected:** `docs/superpowers/specs/2026-09-26-calamus-design.md` (sections 2.1, 3, 4.2 step 10, 4.3, 4.4, 7, 8).

**Key Trade-off:** Sampling the model-judged gate at 1 in 4 saves roughly 28% of tokens per capture but reduces eval coverage; a free structural check still runs on every capture and `full` mode remains available. Provider-specific tuning lives in data profiles that must cite a measurement, rather than in forked prompts or separate packages.

**Evidence:** One call with a six-word prompt through `claude -p --safe-mode --tools ""` on the pinned model used 3,698 input tokens and 38 output tokens, with no cache hits, at about $0.004. The same call with `--bare` failed with "Not logged in", so `--safe-mode` is the only usable guard under login-based auth. `timeout` is not available on macOS, which supports the `lib/timeout.py` design. All from a single run on one CLI version; Codex and Cursor overheads are unmeasured.

**Follow-ups:** Calibrate each available backend during implementation and record it in its profile; owner review of the spec.

---

<!-- SESSION: 2026-09-27 21:17 | calamus format design -->

### [CP-ARCHITECTURE] | 2026-09-27: Canonical Entry Schema With Md/XML/JSONL Renderers and Query Recall

**Summary:** Added to the Calamus spec a single entry schema with three serializations (`md` for humans, `xml` and `jsonl` for models), a `CALAMUS_FORMAT` flag set at init with the journal's file extension as the source of truth, code-side validation and rendering so backends return JSON fields instead of markup, and three scripts for writing, recall, and conversion. No XML template existed before; the only templates were Markdown.

**Files/Modules Affected:** `docs/superpowers/specs/2026-09-26-calamus-design.md` (sections 2.2, 3, 4.2 steps 6-10, 4.4, 4.8, 4.9, 7, 8).

**Key Trade-off:** Chose to have backends return JSON fields and let code render every format over asking the model to write XML directly, so append-only XML and JSONL files can never receive malformed or badly escaped records and one prompt and one eval baseline serve all formats. Accepted the risk that field-constrained output changes entry quality, gated by a before/after Level 2 comparison. Included query recall in scope because model formats do not make entries smaller; the saving is in loading only relevant entries.

**Evidence:** One real entry serialized four ways: Markdown 1,821 chars, XML 1,899 (+4%), JSON line 1,823 (+0.1%), JSON line with one-letter keys 1,772 (-3%). Retrieval savings are extrapolated linearly from 7 entries at the current average entry length, not measured on a long-lived journal. Nothing implemented yet.

**Follow-ups:** Draft the schema file and confirm the Markdown rendering is byte-compatible with today's entries; run Level 2 before and after the JSON-field prompt; measure recall cost on a journal with more entries.

> **[CROSS-LOG]** User-facing implication logged in `./docs/product_insights.md`
> — see [PI-FEATURE-IDEA] | 2026-09-27: One Journal, Two Readers.

---
