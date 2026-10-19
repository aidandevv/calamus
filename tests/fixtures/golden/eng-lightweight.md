### [CP-DEBUG] | 2026-09-27: Offset Not Advanced on Timeout

<!-- calamus id:20260927-1630-a1b2 schema:1 variant:lightweight -->

**Summary:** The sweep offset stayed put after a backend timeout, so the next event retried the same text.

**Files/Modules Affected:** `scripts/hook.sh`, `scripts/lib/gate.sh`

**Key Trade-off:** Retrying costs one more call but never loses text.

**Evidence:** Covered by the hanging-backend test.

**Follow-ups:** Measure retry frequency; Tune the timeout

> **[CROSS-LOG]** Product impact logged in `./docs/product_insights.md`
> — see [PI-TRUST] | 2026-09-27: Lost Captures Erode Trust.

---
