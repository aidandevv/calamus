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
