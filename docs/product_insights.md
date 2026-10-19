# Product Insight Journal
> Chronological log of user pain points, UX friction, product hypotheses,
> positioning insights, roadmap trade-offs, experiments, and product decisions.

---

### [PI-POSITIONING] | 2026-06-20: Journal Roles Need to Be Visible Before Installation

**Observation:**
- The root README named the journaling skill but did not quickly explain what the engineering and product skill files each do.

**Why It Matters:**
- Readers evaluating the repo as a portfolio artifact need to understand the product surface quickly: one skill captures technical decisions, the other captures user/product learning. Without that distinction, the dual-journal idea is less legible.

**Evidence:**
- **Source:** User feedback during README polish.
- **Strength:** Medium

**Hypothesis / Next Step:**
- If the root README shows a compact skill-role table and the journaling README shows examples, readers will understand the value of the dual-journal system before reading the procedural SKILL.md files.

> **[CROSS-LOG]** Engineering documentation change logged in `./docs/dev_journal.md`
> — see [CP-MILESTONE] | 2026-06-20: Journaling Skill Roles Made Visible in READMEs.

---

### [PI-POSITIONING] | 2026-06-20: Journaling Should Read Like a Live Memory Layer

**Observation:**
- The public README felt clearer when `journaling/` was presented as a live project-memory block instead of a catalog row with a feature table.

**Why It Matters:**
- The audience needs to understand the motivation before the mechanism: agents can write continuously to low-friction project memory, preserving engineering decisions and product insights for later write-ups, mock-ups, product pitches, retrospectives, and portfolio stories.

**Evidence:**
- **Source:** User feedback during README presentation polish.
- **Strength:** Medium

**Hypothesis / Next Step:**
- If the README leads with the live-memory motivation and then shows the engineering/product subskills as nested blocks, readers will understand the system's purpose before they evaluate install details or hook mechanics.

> **[CROSS-LOG]** Engineering documentation change logged in `./docs/dev_journal.md`
> — see [CP-MILESTONE] | 2026-06-20: README Skill Presentation Shifted to Abstract Blocks.

---

### [PI-POSITIONING] | 2026-06-20: Garden README Needs Modular Skill Blocks

**Observation:**
- The root README should make clear that `agent-skills-garden` is a collection of independent skill modules, not a repo only about journaling.

**Why It Matters:**
- As more unrelated skills are added, readers need to understand that each top-level folder is self-contained. `journaling/` can have its own internal engineering and product skills without setting the structure for every future module.

**Evidence:**
- **Source:** User feedback during README structure polish.
- **Strength:** Medium

**Hypothesis / Next Step:**
- If the README starts with a garden-level module table and then presents `journaling/` as one self-contained module block, future skills can be added cleanly without confusing the repo's architecture or portfolio story.

> **[CROSS-LOG]** Engineering documentation change logged in `./docs/dev_journal.md`
> — see [CP-MILESTONE] | 2026-06-20: Root README Reframed as Modular Skill Garden.

---

### [PI-POSITIONING] | 2026-09-26: Rebrand From Skill Garden to One Named Skill

**Observation:**
- The owner asked to rebrand the repository into one centralized skill named Calamus, the reed pen that preceded the quill, replacing the multi-module garden framing.

**Why It Matters:**
- A single named skill is easier to explain, install, and cite than a collection with one populated module. The never-started second module was implying scope the project does not have.

**Evidence:**
- **Source:** Owner request in session.
- **Strength:** Medium

**Hypothesis / Next Step:**
- If the README leads with one name, one install path per host, and the host matrix, readers evaluating the skill will grasp its value faster than through a module table. Validate by rewriting the README during implementation and reading its first screen.

> **[CROSS-LOG]** Engineering design logged in `./docs/dev_journal.md`
> — see [CP-ARCHITECTURE] | 2026-09-26: Calamus Design — Common Core With Host Shims.

---

### [PI-POSITIONING] | 2026-09-27: State Where Calamus Applies and Where It Does Not

**Observation:**
- The owner asked how agnostic Calamus is and whether it holds up across custom agents and major cloud agent platforms. The honest answer differs by layer: the skill text ports widely, the hook engine needs a shell, a local repo, and a transcript file, and hosted agent platforms use in-process callbacks and their own memory services instead.

**Why It Matters:**
- The word "agnostic" invites a broader reading than the design supports. Readers evaluating the skill may assume it works for deployed agents, when it targets coding agents working in a repository.

**Evidence:**
- **Source:** Owner question in session; search summaries of platform hook and memory support.
- **Strength:** Medium

**Hypothesis / Next Step:**
- If the README states plainly what each layer runs on and where Calamus does not apply, readers will form accurate expectations sooner. Add that table when the README is rewritten, and verify the platform claims against full docs first.

> **[CROSS-LOG]** Engineering design change logged in `./docs/dev_journal.md`
> — see [CP-ARCHITECTURE] | 2026-09-27: Token-Bounded Capture and Generic Host Added to Calamus Spec.

---

### [PI-FEATURE-IDEA] | 2026-09-27: One Journal, Two Readers

**Observation:**
- The owner asked for a flag that writes the journals for humans (Markdown) or for models (XML or JSON), and for a template that guarantees consistent quality. The same memory serves a person writing case studies and a future agent resuming work, and those readers want different things.

**Why It Matters:**
- Measuring one entry showed structured formats are not smaller than Markdown, so "model-optimized" cannot mean cheaper per entry. The value for a model reader is selective recall and validated structure, which is what a format flag has to deliver to be worth shipping.

**Evidence:**
- **Source:** Owner request in session; serialization size comparison on one real entry.
- **Strength:** Medium

**Hypothesis / Next Step:**
- If model mode ships with query, an agent resuming on a long-lived project should load a couple of thousand tokens instead of the whole journal. Validate by comparing tokens loaded to resume on a journal with many entries, and state plainly in the README that the saving comes from retrieval.

> **[CROSS-LOG]** Engineering design logged in `./docs/dev_journal.md`
> — see [CP-ARCHITECTURE] | 2026-09-27: Canonical Entry Schema With Md/XML/JSONL Renderers and Query Recall.

---

### [PI-ONBOARDING] | 2026-09-28: Cursor Users Need a Backend Choice at Install

<!-- calamus id:20260928-1429-c0d5 schema:1 variant:lightweight -->

**Observation:**
- With the Cursor backend disabled, a Cursor user who installs hooks with default settings gets pending markers instead of journal entries until they set CALAMUS_BACKEND to claude or generic.

**Why It Matters:**
- The first-run experience on Cursor would look broken even though the skill works, which undercuts the one-install, three-hosts positioning.

**Evidence:**
- **Source:** Implementation discovery from Cursor CLI headless documentation
- **Strength:** Medium

**Hypothesis / Next Step:**
- Have calamus-install --host cursor state the backend choice explicitly, and revisit once Cursor documents a model flag and a tool-free mode.

> **[CROSS-LOG]** Engineering root cause logged in `./docs/dev_journal.md`
> — see [CP-MILESTONE] | 2026-09-28: Calamus Skill and Hook Engine Implemented With Offline Tests.

---

### [PI-POSITIONING] | 2026-10-18: Lead the README with the lost-decision problem

**Observation:**
- The README described journals and hooks before giving readers a concrete reason to need them. The portfolio's editorial standard favors a specific problem, connected choices, and claims bounded by evidence. The revised opening starts with the decision context an agent can lose between sessions, then explains how the journals, query, and hooks address it.

**Why It Matters:**
- A reader evaluating Calamus can understand its purpose before meeting its file layout and host details. Clearer boundaries also help keep the beta synthesis skill from sounding like part of the core capture path.

**Evidence:**
- **Source:** Owner request to apply the portfolio's product voice; review of the README and portfolio editorial standard.
- **Strength:** Medium for intended voice and message structure; reader comprehension has not been tested.

**Hypothesis / Next Step:**
- Check whether a new reader can explain the problem, the two journals, and the optional role of hooks from the first screen of the README.

---
