---
name: product-insight-journal
description: >-
  Maintain a running product insight journal. Use when observing user pain,
  UX friction, activation or retention patterns, positioning insights, roadmap
  trade-offs, feature hypotheses, competitive signals, or any product decision
  worth capturing for a future case study, PM interview, or founder update.
  Appends entries to ./docs/product_insights.md. Evaluates at end of every
  meaningful product or UX interaction.
---

# Product Insight Journal — Skill Instructions

A model-agnostic agent instruction for maintaining a chronological product
insight journal across agentic coding, design, and product-development
workflows. Works with Claude Code, Codex CLI, Cursor, Gemini CLI, and any
Agent Skills-compatible runtime.

Design rationale, research citations, and version history live in
`../../README.md` (skill-level) and the repo-level `README.md`. This file
contains only what the agent needs to do the job.

---

## Core Objective

Maintain `./docs/product_insights.md` — a chronological log of user pain,
UX friction, product hypotheses, positioning insights, roadmap trade-offs,
experiments, and product decisions. Write entries that will support future
portfolio write-ups, PM interview stories, and product retrospectives.

If the environment supports file writes, append directly. If not, output the
exact Markdown inside a copyable code fence and tell the user to append it.

Do not overwrite existing content. Do not fabricate details.

---

## Initialization

If `./docs/product_insights.md` does not exist:

```bash
mkdir -p docs
cat > docs/product_insights.md << 'EOF'
# Product Insight Journal
> Chronological log of user pain points, UX friction, product hypotheses,
> positioning insights, roadmap trade-offs, experiments, and product decisions.

---
EOF
```

---

## When to Write — Insight Triggers

Write an entry when the session includes any of:

- A user pain point or repeated friction pattern.
- A confusing, slow, broken, or high-cognitive-load UX moment.
- A new feature idea grounded in user behavior, strategy, or an observed gap.
- A product positioning, narrative, messaging, or differentiation insight.
- A user onboarding, activation, retention, conversion, trust, or growth
  observation.
- A metric, funnel, or engagement signal that changes product understanding.
- A competitor or market observation that affects roadmap thinking.
- A roadmap trade-off or prioritization decision.
- A product experiment, hypothesis, or validation plan.
- A feature request that reveals an underlying job-to-be-done.
- A moment where implementation reveals a product limitation or UX trade-off.
- A product decision worth explaining in a portfolio write-up or PM interview.

Do not log pure aesthetic preferences, ungrounded brainstorms, minor copy
edits without positioning impact, or routine engineering details.

**Quality bar:** Before writing, verify the observation answers at least four of:

1. What did we observe?
2. Who does it affect?
3. Where in the journey did it happen?
4. What user job does it reveal?
5. What evidence supports it?
6. How strong is the evidence?
7. What product risk does it affect?
8. What hypothesis follows?
9. What should we test, build, measure, or revisit?
10. How could this support a future product write-up?

If fewer than four can be answered, use the Lightweight schema or ask whether
to wait.

---

## Insight Types

| Tag | Use for |
|---|---|
| `[PI-USER-PAIN]` | User problem, frustration, unmet need, or repeated pain point |
| `[PI-UX-FRICTION]` | Confusing, slow, hidden, or high-effort user experience |
| `[PI-AHA-MOMENT]` | Where product value becomes clear, or should be made clearer |
| `[PI-FEATURE-IDEA]` | Feature idea grounded in evidence or observed user need |
| `[PI-POSITIONING]` | Messaging, narrative, audience, or differentiation insight |
| `[PI-ONBOARDING]` | First-time UX, setup, activation, empty states, time-to-value |
| `[PI-RETENTION]` | Why users would return, churn, build habits, or disengage |
| `[PI-METRIC]` | Insight based on activation, conversion, retention, or engagement |
| `[PI-EXPERIMENT]` | Testable hypothesis, experiment design, or validation plan |
| `[PI-COMPETITIVE]` | Competitor or adjacent product observation that changes strategy |
| `[PI-ROADMAP]` | Prioritization, sequencing, scope, or strategic roadmap decision |
| `[PI-PRICING]` | Willingness to pay, packaging, monetization, or perceived value |
| `[PI-TRUST]` | Credibility, privacy, security, reliability, or user confidence |
| `[PI-ACCESSIBILITY]` | Usability across abilities, devices, language, or cognitive load |
| `[PI-GROWTH]` | Acquisition, referral, sharing, virality, SEO, or lifecycle insight |
| `[PI-SUPPORT]` | Insight from support questions, repeated confusion, or help flows |

---

## Evidence Strength

Classify every observation:

- **Strong** — Multiple user signals, clear analytics, repeated observations,
  direct user feedback, or validated experiment results.
- **Medium** — One user quote, one manual walkthrough, one support issue, one
  competitor contrast, or a clear founder observation.
- **Weak** — Plausible but mostly intuition, limited context, or early
  speculation. Label honestly. Do not promote to roadmap without validation.

---

## Product Risk Lens

When relevant, classify the main product risk being reduced or exposed:

- **Value risk** — Will users want this? Does it solve a real problem?
- **Usability risk** — Can users understand and successfully use it?
- **Feasibility risk** — Can we build and maintain it with available resources?
- **Viability risk** — Does it make sense for the business, pricing, distribution?
- **Trust risk** — Will users believe, trust, and feel safe using it?
- **Accessibility risk** — Can different users access and benefit from it?

---

## Cross-Log Coordination

When an observation has both an engineering dimension and a product dimension
worth preserving independently, write separate entries in both files.

Add a `[CROSS-LOG]` marker:

```markdown
> **[CROSS-LOG]** Engineering root cause logged in `./docs/dev_journal.md`
> — see [CP-CONSTRAINT] | YYYY-MM-DD: [title].
```

Write cross-log entries when:
- A technical constraint directly degrades the user experience
- An implementation decision forecloses a product option
- A performance finding affects user trust or activation
- An API limitation requires a product-level workaround visible to users

---

## Lightweight Entry Schema

Use for small but real observations, or in compressed contexts.

```markdown
### [TAG] | YYYY-MM-DD: [Observation Title]

**Observation:**
- [What was noticed?]

**Why It Matters:**
- [Impact on user experience, product strategy, or roadmap.]

**Evidence:**
- **Source:** [Where this came from.]
- **Strength:** [Strong / Medium / Weak]

**Hypothesis / Next Step:**
- [What to test, build, measure, revisit, or ignore.]

---
```

---

## Full Entry Schema

Use for insights that affect roadmap, positioning, UX, growth, trust,
onboarding, retention, or major feature decisions.

```markdown
### [TAG] | YYYY-MM-DD: [Observation Title]

**Observation:**
- [What was noticed? Be concrete.]

**User / Journey Context:**
- **User Segment:** [Who this affects, or `Unknown`.]
- **Journey Stage:** [Discovery / onboarding / activation / core workflow /
  retention / support / upgrade / sharing]
- **User Goal:** [What the user was trying to accomplish.]

**Jobs-to-Be-Done Lens:**
- **Functional Job:** [The practical progress the user wants.]
- **Emotional/Social Job:** [What the user wants to feel, avoid, or signal.]
  *(Omit if the observation is purely about UI execution.)*

**Evidence:**
- **Source:** [User quote / analytics / manual walkthrough / support issue /
  competitor example / founder observation / implementation discovery]
- **Strength:** [Strong / Medium / Weak]
- **Notes:** [Concrete evidence. Do not invent.]
- **Counter-Evidence:** [Known counter-signal, or `None identified.`]

**Product Impact:**
- [How this affects activation, retention, conversion, trust, clarity,
  accessibility, differentiation, growth, revenue, or usability.]

**Product Risk Lens:**
- **Primary Risk:** [Value / Usability / Feasibility / Viability / Trust /
  Accessibility]
- **Why:** [What this observation helps de-risk or exposes as risky.]

**Hypothesis:**
- [If we change X, then Y should improve because Z.]

**Decision / Next Step:**
- [What to design, test, build, measure, ignore, or revisit.]

**Priority Signal:**
- **Reach:** [Low / Medium / High / Unknown]
- **Impact:** [Low / Medium / High / Unknown]
- **Confidence:** [Low / Medium / High]
- **Effort:** [Low / Medium / High / Unknown]

**Potential Content Angle:**
- [How this might support a case study, portfolio write-up, founder
  reflection, PM interview story, or LinkedIn post.]

**Cross-Log:**
- [Related engineering entry in dev_journal.md, or `None.`]

**Open Questions:**
- [Unresolved risks, assumptions, or follow-ups. If none: `None identified.`]

---
```

---

## Append Safety

- Always append. Never overwrite. Never delete previous entries unless
  explicitly asked.
- Do not duplicate an entry for the same observation, evidence, and decision.
- If a prior insight changed, append a new entry explaining the revision.

---

## File-Writing Behavior

**File access available:** Ensure `./docs/` and `./docs/product_insights.md`
exist, append entry, preserve all existing content, confirm briefly.

**File access unavailable:** Output entry in a copyable code fence, tell the
user to append to `./docs/product_insights.md`, do not claim modification.

---

## Relationship to Engineering Journal

Product decisions → `product_insights.md`
Engineering decisions → `dev_journal.md`
Both → separate entries with `[CROSS-LOG]` markers.

Engineering journal skill: `../engineering-journal/SKILL.md`

---

## Global Adapter (paste into CLAUDE.md / AGENTS.md)

```
Follow product-insight-journal skill at:
  ~/.claude/skills/journaling/product-insight-journal/SKILL.md

Maintain: ./docs/product_insights.md

At the end of meaningful product, UX, growth, onboarding, retention,
roadmap, or user-facing work, evaluate whether an insight should be logged.
Prefer Lightweight schema for small observations. Never overwrite. Never
fabricate.
```
