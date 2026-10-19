# Product Insight Journal

Maintain `./docs/product_insights.md` (or `.xml` / `.jsonl`) — a
chronological log of user pain, UX friction, product hypotheses, positioning
insights, roadmap trade-offs, experiments, and product decisions. Write
entries that will support future portfolio write-ups, PM interview stories,
and product retrospectives. Do not fabricate details.

---

## Journal Header

A new Markdown journal starts with:

```markdown
# Product Insight Journal
> Chronological log of user pain points, UX friction, product hypotheses,
> positioning insights, roadmap trade-offs, experiments, and product decisions.

---
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
worth preserving independently, write separate entries in both journals,
linked by `[CROSS-LOG]` (a `crosslog` object with `calamus-append`).

Write cross-log entries when:
- A technical constraint directly degrades the user experience
- An implementation decision forecloses a product option
- A performance finding affects user trust or activation
- An API limitation requires a product-level workaround visible to users

---

## Lightweight Entry Schema

Use for small but real observations, or in compressed contexts.

<!-- BEGIN GENERATED: pi-lightweight -->
```markdown
### [TAG] | YYYY-MM-DD: [Title]

**Observation:**
- [What was noticed]

**Why It Matters:**
- [Impact on UX, strategy, or roadmap]

**Evidence:**
- **Source:** [Where this came from]
- **Strength:** Strong / Medium / Weak

**Hypothesis / Next Step:**
- [What to test, build, measure, revisit, or ignore]

> **[CROSS-LOG]** Engineering root cause logged in `./docs/dev_journal.md`
> — see [TAG] | YYYY-MM-DD: [title].

---
```
<!-- END GENERATED: pi-lightweight -->

---

## Full Entry Schema

Use for insights that affect roadmap, positioning, UX, growth, trust,
onboarding, retention, or major feature decisions. Omit the
Emotional/Social Job if the observation is purely about UI execution.

<!-- BEGIN GENERATED: pi-full -->
```markdown
### [TAG] | YYYY-MM-DD: [Title]

**Observation:**
- [What was noticed, concretely]

**User / Journey Context:**
- **User Segment:** [Who this affects] or `Unknown`
- **Journey Stage:** Discovery / Onboarding / Activation / Core workflow / Retention / Support / Upgrade / Sharing
- **User Goal:** [What the user was trying to accomplish]

**Jobs-to-Be-Done Lens:**
- **Functional Job:** [The practical progress the user wants]
- **Emotional/Social Job:** [Omit if purely about UI execution] (optional)

**Evidence:**
- **Source:** [Quote, analytics, walkthrough, support issue, competitor, founder observation, or implementation discovery]
- **Strength:** Strong / Medium / Weak
- **Notes:** [Concrete evidence. Do not invent]
- **Counter-Evidence:** [Known counter-signal] or `None identified.`

**Product Impact:**
- [Effect on activation, retention, trust, and so on]

**Product Risk Lens:**
- **Primary Risk:** Value / Usability / Feasibility / Viability / Trust / Accessibility
- **Why:** [What this de-risks or exposes]

**Hypothesis:**
- [If we change X, then Y should improve because Z]

**Decision / Next Step:**
- [What to design, test, build, measure, ignore, or revisit]

**Priority Signal:**
- **Reach:** Low / Medium / High / Unknown
- **Impact:** Low / Medium / High / Unknown
- **Confidence:** Low / Medium / High
- **Effort:** Low / Medium / High / Unknown

**Potential Content Angle:** (optional)
- [Case study, write-up, or interview angle]

**Cross-Log:**
- [Related engineering entry, if any] or `None.`

**Open Questions:**
- [Unresolved risks, assumptions, follow-ups] or `None identified.`

> **[CROSS-LOG]** Engineering root cause logged in `./docs/dev_journal.md`
> — see [TAG] | YYYY-MM-DD: [title].

---
```
<!-- END GENERATED: pi-full -->

---

## JSON Fields for `calamus-append`

`scripts/calamus-append --journal product` takes one object (or
`{"entries": [...]}`) with these fields. `journal` and `id` are filled in.

<!-- BEGIN GENERATED: pi-fields -->
```text
Lightweight:
- "variant": "lightweight"
- "tag": string, one of "PI-USER-PAIN" | "PI-UX-FRICTION" | "PI-AHA-MOMENT" | "PI-FEATURE-IDEA" | "PI-POSITIONING" | "PI-ONBOARDING" | "PI-RETENTION" | "PI-METRIC" | "PI-EXPERIMENT" | "PI-COMPETITIVE" | "PI-ROADMAP" | "PI-PRICING" | "PI-TRUST" | "PI-ACCESSIBILITY" | "PI-GROWTH" | "PI-SUPPORT"
- "date": string, YYYY-MM-DD
- "title": string, short and specific
- "observation": array of strings (required) — What was noticed.
- "why": array of strings (required) — Impact on UX, strategy, or roadmap.
- "evidence": object — Evidence, with:
  - "source": string (required) — Where this came from.
  - "strength": string, one of "Strong" | "Medium" | "Weak" (required)
- "next_step": array of strings (required) — What to test, build, measure, revisit, or ignore.

Full:
- "variant": "full"
- "tag": string, one of "PI-USER-PAIN" | "PI-UX-FRICTION" | "PI-AHA-MOMENT" | "PI-FEATURE-IDEA" | "PI-POSITIONING" | "PI-ONBOARDING" | "PI-RETENTION" | "PI-METRIC" | "PI-EXPERIMENT" | "PI-COMPETITIVE" | "PI-ROADMAP" | "PI-PRICING" | "PI-TRUST" | "PI-ACCESSIBILITY" | "PI-GROWTH" | "PI-SUPPORT"
- "date": string, YYYY-MM-DD
- "title": string, short and specific
- "observation": array of strings (required) — What was noticed, concretely.
- "context": object — User / Journey Context, with:
  - "segment": string (may be empty) — Who this affects.
  - "stage": string, one of "Discovery" | "Onboarding" | "Activation" | "Core workflow" | "Retention" | "Support" | "Upgrade" | "Sharing" (required)
  - "goal": string (required) — What the user was trying to accomplish.
- "jtbd": object — Jobs-to-Be-Done Lens, with:
  - "functional": string (required) — The practical progress the user wants.
  - "emotional": string (optional) — Omit if purely about UI execution.
- "evidence": object — Evidence, with:
  - "source": string (required) — Quote, analytics, walkthrough, support issue, competitor, founder observation, or implementation discovery.
  - "strength": string, one of "Strong" | "Medium" | "Weak" (required)
  - "notes": string (required) — Concrete evidence. Do not invent.
  - "counter": string (may be empty) — Known counter-signal.
- "impact": array of strings (required) — Effect on activation, retention, trust, and so on.
- "risk": object — Product Risk Lens, with:
  - "primary": string, one of "Value" | "Usability" | "Feasibility" | "Viability" | "Trust" | "Accessibility" (required)
  - "why": string (required) — What this de-risks or exposes.
- "hypothesis": array of strings (required) — If we change X, then Y should improve because Z.
- "next_step": array of strings (required) — What to design, test, build, measure, ignore, or revisit.
- "priority": object — Priority Signal, with:
  - "reach": string, one of "Low" | "Medium" | "High" | "Unknown" (required)
  - "impact": string, one of "Low" | "Medium" | "High" | "Unknown" (required)
  - "confidence": string, one of "Low" | "Medium" | "High" (required)
  - "effort": string, one of "Low" | "Medium" | "High" | "Unknown" (required)
- "content_angle": array of strings (optional) — Case study, write-up, or interview angle.
- "crosslog_notes": array of strings (may be empty) — Related engineering entry, if any.
- "open_questions": array of strings (may be empty) — Unresolved risks, assumptions, follow-ups.
```
<!-- END GENERATED: pi-fields -->
