# XML Journal Format

Read only for projects whose journals are `docs/dev_journal.xml` and
`docs/product_insights.xml`.

- A journal is a stream of `<entry>` and `<marker>` elements after one
  leading comment. There is no root element; wrap the file in one before
  parsing it.
- Escape `<`, `&`, and quotes in text. Put code in `<![CDATA[...]]>`.
- Prefer `scripts/calamus-append`, which validates and escapes for you. Write
  by hand only when scripts cannot run, and append at the end of the file.
- Do not add `<!DOCTYPE>` or entity declarations; readers reject them.

Templates (placeholders in brackets; `a|b` means choose one):

<!-- BEGIN GENERATED: xml-templates -->
```xml
<!-- calamus journal:engineering schema:1 -->
<entry type="engineering" variant="lightweight" schema="1" id="YYYYMMDD-HHMM-abcd" tag="TAG" date="YYYY-MM-DD">
  <title>[Title]</title>
  <summary>[1-2 sentences: decision made and why]</summary>
  <files><file>[Files, modules, or components affected]</file></files>
  <tradeoff>[What was accepted or rejected and why]</tradeoff>
  <evidence status="verified|unverified">[How we know this worked; status unverified if not yet verified]</evidence>
  <followups><item>[Open questions]</item></followups>
  <crosslog journal="product" tag="TAG" date="YYYY-MM-DD" note="Product impact">[title]</crosslog>
</entry>
<entry type="engineering" variant="full" schema="1" id="YYYYMMDD-HHMM-abcd" tag="TAG" date="YYYY-MM-DD">
  <title>[Title]</title>
  <context><item>[Concrete technical goal, problem, or question]</item></context>
  <design>
    <choice>[The design, library, pattern, or workflow selected]</choice>
    <alternatives>[Serious alternatives, or state none were evaluated]</alternatives>
    <why>[Technical justification and constraints weighed]</why>
  </design>
  <pivot><item>[What changed during implementation; if the plan held, why]</item></pivot>
  <impl>
    <files><file>[Files, modules, functions, components]</file></files>
    <pattern>[The implementation pattern or mechanism]</pattern>
  </impl>
  <verification><item>[Tests, builds, logs, manual checks]</item></verification>
  <references><item>[Only references actually consulted: [Name](URL) - takeaway]</item></references>
  <code><![CDATA[[Pseudocode, diff concept, schema, or snippet]]]></code>
  <crosslog_notes><item>[Related product entry, if any]</item></crosslog_notes>
  <followups><item>[Unresolved risks, deferred work, edge cases]</item></followups>
  <crosslog journal="product" tag="TAG" date="YYYY-MM-DD" note="Product impact">[title]</crosslog>
</entry>
<entry type="engineering" variant="snapshot" schema="1" id="YYYYMMDD-HHMM-abcd" tag="CP-COMPACT-SNAPSHOT" date="YYYY-MM-DD">
  <title>[Title]</title>
  <summary>[What is in progress, 1-2 sentences]</summary>
  <files><file>[Files actively being worked on]</file></files>
  <decisions><item>[Key choices, at most 3]</item></decisions>
  <next_step>[Exactly what to do right after compaction]</next_step>
  <open_questions><item>[Unresolved risks or blockers]</item></open_questions>
  <crosslog journal="product" tag="TAG" date="YYYY-MM-DD" note="Product impact">[title]</crosslog>
</entry>
<!-- calamus journal:product schema:1 -->
<entry type="product" variant="lightweight" schema="1" id="YYYYMMDD-HHMM-abcd" tag="TAG" date="YYYY-MM-DD">
  <title>[Title]</title>
  <observation><item>[What was noticed]</item></observation>
  <why><item>[Impact on UX, strategy, or roadmap]</item></why>
  <evidence>
    <source>[Where this came from]</source>
    <strength>Strong|Medium|Weak</strength>
  </evidence>
  <next_step><item>[What to test, build, measure, revisit, or ignore]</item></next_step>
  <crosslog journal="engineering" tag="TAG" date="YYYY-MM-DD" note="Engineering root cause">[title]</crosslog>
</entry>
<entry type="product" variant="full" schema="1" id="YYYYMMDD-HHMM-abcd" tag="TAG" date="YYYY-MM-DD">
  <title>[Title]</title>
  <observation><item>[What was noticed, concretely]</item></observation>
  <context>
    <segment>[Who this affects]</segment>
    <stage>Discovery|Onboarding|Activation|Core workflow|Retention|Support|Upgrade|Sharing</stage>
    <goal>[What the user was trying to accomplish]</goal>
  </context>
  <jtbd>
    <functional>[The practical progress the user wants]</functional>
    <emotional>[Omit if purely about UI execution]</emotional>
  </jtbd>
  <evidence>
    <source>[Quote, analytics, walkthrough, support issue, competitor, founder observation, or implementation discovery]</source>
    <strength>Strong|Medium|Weak</strength>
    <notes>[Concrete evidence. Do not invent]</notes>
    <counter>[Known counter-signal]</counter>
  </evidence>
  <impact><item>[Effect on activation, retention, trust, and so on]</item></impact>
  <risk>
    <primary>Value|Usability|Feasibility|Viability|Trust|Accessibility</primary>
    <why>[What this de-risks or exposes]</why>
  </risk>
  <hypothesis><item>[If we change X, then Y should improve because Z]</item></hypothesis>
  <next_step><item>[What to design, test, build, measure, ignore, or revisit]</item></next_step>
  <priority>
    <reach>Low|Medium|High|Unknown</reach>
    <impact>Low|Medium|High|Unknown</impact>
    <confidence>Low|Medium|High</confidence>
    <effort>Low|Medium|High|Unknown</effort>
  </priority>
  <content_angle><item>[Case study, write-up, or interview angle]</item></content_angle>
  <crosslog_notes><item>[Related engineering entry, if any]</item></crosslog_notes>
  <open_questions><item>[Unresolved risks, assumptions, follow-ups]</item></open_questions>
  <crosslog journal="engineering" tag="TAG" date="YYYY-MM-DD" note="Engineering root cause">[title]</crosslog>
</entry>
<marker kind="session" when="YYYY-MM-DD HH:MM" session="SESSION" event="EVENT"/>
<marker kind="compact" when="YYYY-MM-DD HH:MM" session="SESSION"/>
<marker kind="resume" when="YYYY-MM-DD HH:MM" session="SESSION" snapshot="ID"/>
<marker kind="pending" date="YYYY-MM-DD" session="SESSION" host="HOST" event="EVENT"/>
<marker kind="resolved" date="YYYY-MM-DD" session="SESSION" entry="ID"/>
```
<!-- END GENERATED: xml-templates -->
