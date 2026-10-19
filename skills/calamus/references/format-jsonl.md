# JSONL Journal Format

Read only for projects whose journals are `docs/dev_journal.jsonl` and
`docs/product_insights.jsonl`.

- One JSON object per line. The first line is a `header` record.
- Never pretty-print a record across lines, and never wrap the file in an
  array: each append adds whole lines at the end.
- Prefer `scripts/calamus-append`, which validates and serializes for you.
  Write by hand only when scripts cannot run.

Templates (placeholders in brackets; `a|b` means choose one):

<!-- BEGIN GENERATED: jsonl-templates -->
```json
{"record": "header", "journal": "engineering", "schema": "1"}
{"record":"entry","journal":"engineering","variant":"lightweight","schema":"1","id":"YYYYMMDD-HHMM-abcd","tag":"TAG","date":"YYYY-MM-DD","title":"[Title]","summary":"[1-2 sentences: decision made and why]","files":["[Files, modules, or components affected]"],"tradeoff":"[What was accepted or rejected and why]","evidence":{"status":"verified|unverified","text":"[How we know this worked; status unverified if not yet verified]"},"followups":["[Open questions]"],"crosslog":{"journal":"product","tag":"TAG","date":"YYYY-MM-DD","title":"[title]","note":"Product impact"}}
{"record":"entry","journal":"engineering","variant":"full","schema":"1","id":"YYYYMMDD-HHMM-abcd","tag":"TAG","date":"YYYY-MM-DD","title":"[Title]","context":["[Concrete technical goal, problem, or question]"],"design":{"choice":"[The design, library, pattern, or workflow selected]","alternatives":"[Serious alternatives, or state none were evaluated]","why":"[Technical justification and constraints weighed]"},"pivot":["[What changed during implementation; if the plan held, why]"],"impl":{"files":["[Files, modules, functions, components]"],"pattern":"[The implementation pattern or mechanism]"},"verification":["[Tests, builds, logs, manual checks]"],"references":["[Only references actually consulted: [Name](URL) - takeaway]"],"code":"[Pseudocode, diff concept, schema, or snippet]","crosslog_notes":["[Related product entry, if any]"],"followups":["[Unresolved risks, deferred work, edge cases]"],"crosslog":{"journal":"product","tag":"TAG","date":"YYYY-MM-DD","title":"[title]","note":"Product impact"}}
{"record":"entry","journal":"engineering","variant":"snapshot","schema":"1","id":"YYYYMMDD-HHMM-abcd","tag":"CP-COMPACT-SNAPSHOT","date":"YYYY-MM-DD","title":"[Title]","summary":"[What is in progress, 1-2 sentences]","files":["[Files actively being worked on]"],"decisions":["[Key choices, at most 3]"],"next_step":"[Exactly what to do right after compaction]","open_questions":["[Unresolved risks or blockers]"],"crosslog":{"journal":"product","tag":"TAG","date":"YYYY-MM-DD","title":"[title]","note":"Product impact"}}
{"record": "header", "journal": "product", "schema": "1"}
{"record":"entry","journal":"product","variant":"lightweight","schema":"1","id":"YYYYMMDD-HHMM-abcd","tag":"TAG","date":"YYYY-MM-DD","title":"[Title]","observation":["[What was noticed]"],"why":["[Impact on UX, strategy, or roadmap]"],"evidence":{"source":"[Where this came from]","strength":"Strong|Medium|Weak"},"next_step":["[What to test, build, measure, revisit, or ignore]"],"crosslog":{"journal":"engineering","tag":"TAG","date":"YYYY-MM-DD","title":"[title]","note":"Engineering root cause"}}
{"record":"entry","journal":"product","variant":"full","schema":"1","id":"YYYYMMDD-HHMM-abcd","tag":"TAG","date":"YYYY-MM-DD","title":"[Title]","observation":["[What was noticed, concretely]"],"context":{"segment":"[Who this affects]","stage":"Discovery|Onboarding|Activation|Core workflow|Retention|Support|Upgrade|Sharing","goal":"[What the user was trying to accomplish]"},"jtbd":{"functional":"[The practical progress the user wants]","emotional":"[Omit if purely about UI execution]"},"evidence":{"source":"[Quote, analytics, walkthrough, support issue, competitor, founder observation, or implementation discovery]","strength":"Strong|Medium|Weak","notes":"[Concrete evidence. Do not invent]","counter":"[Known counter-signal]"},"impact":["[Effect on activation, retention, trust, and so on]"],"risk":{"primary":"Value|Usability|Feasibility|Viability|Trust|Accessibility","why":"[What this de-risks or exposes]"},"hypothesis":["[If we change X, then Y should improve because Z]"],"next_step":["[What to design, test, build, measure, ignore, or revisit]"],"priority":{"reach":"Low|Medium|High|Unknown","impact":"Low|Medium|High|Unknown","confidence":"Low|Medium|High","effort":"Low|Medium|High|Unknown"},"content_angle":["[Case study, write-up, or interview angle]"],"crosslog_notes":["[Related engineering entry, if any]"],"open_questions":["[Unresolved risks, assumptions, follow-ups]"],"crosslog":{"journal":"engineering","tag":"TAG","date":"YYYY-MM-DD","title":"[title]","note":"Engineering root cause"}}
{"record":"marker","kind":"session","when":"YYYY-MM-DD HH:MM","session":"SESSION","event":"EVENT"}
{"record":"marker","kind":"compact","when":"YYYY-MM-DD HH:MM","session":"SESSION"}
{"record":"marker","kind":"resume","when":"YYYY-MM-DD HH:MM","session":"SESSION","snapshot":"ID"}
{"record":"marker","kind":"pending","date":"YYYY-MM-DD","session":"SESSION","host":"HOST","event":"EVENT"}
{"record":"marker","kind":"resolved","date":"YYYY-MM-DD","session":"SESSION","entry":"ID"}
```
<!-- END GENERATED: jsonl-templates -->
