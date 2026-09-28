# Golden Dataset Index
> Status: Stub — 1 of 15 target examples populated.
> See level-4-plan.md for the full collection protocol.

## Dataset Manifest

| ID | Transcript | Checkpoint Type | Should Journal | Label Status |
|---|---|---|---|---|
| t01 | t01-api-rate-limit.md | [CP-CONSTRAINT] | Yes | ✅ Complete |
| t02–t15 | TBD | Various | TBD | 🔲 Not yet collected |

**Target distribution:** See level-4-plan.md § Golden Dataset Design.

---

## t01 — Example: API Rate Limit Discovery

### Simulated Transcript Excerpt

```
User: run the load test against the presence endpoint

Claude: Running load test... [tool: bash] ab -n 500 -c 15 https://api.example.com/presence

[tool output]:
Requests per second: 87.3
Failed requests: 412
Error: 429 Too Many Requests (rate limit: 100 req/min per connection)

Claude: The load test hit a rate limit wall. The upstream presence API
enforces 100 requests/minute per connection. At 15 concurrent users we
saturate this in under 45 seconds. We need to either (a) implement
request queuing with exponential backoff, (b) fall back to polling at
a safe interval, or (c) switch to a WebSocket-based approach.

User: let's go with the polling fallback for now, we can revisit the
WS approach later. What file do we need to change?

Claude: We need to modify src/presence/manager.ts. I'll replace the
direct API call loop with a polling interval at 5s, which keeps us
safely under the rate limit even with 20 concurrent users.

[tool: Edit] src/presence/manager.ts
- Replaced: setInterval(fetchPresence, 500)
+ Added: PollingPresenceManager with 5000ms interval and jitter

User: looks good, ship it
```

### Label: t01-expected

**Should journal:** Yes

**Expected tag:** `[CP-CONSTRAINT]`

**Required assertions (entry must address all):**
- [ ] Identifies the rate limit as 100 req/min (or equivalent)
- [ ] States that the polling fallback was chosen over WebSocket approach
- [ ] Names `src/presence/manager.ts` as the affected file
- [ ] Notes that 5s polling interval was selected to stay under the limit
- [ ] Mentions that WebSocket approach was deferred (follow-up signal)

**Acceptable evidence statements:**
- "Load test at N concurrent users hit the limit in <60s" or similar
- "429 responses observed" or similar
- Does not need to name the exact ab command

**Forbidden content:**
- Do not invent a specific error code other than 429
- Do not claim the WebSocket approach was implemented
- Do not claim the polling interval is anything other than ~5s
- Do not mention files not in the transcript

**Cross-log check:**
- This transcript also contains a product-facing concern (stale presence
  indicators for concurrent users). A correct implementation should detect
  the `[CROSS-LOG]` trigger and note that a product insight entry is also
  warranted. This is a secondary assertion — failure here does not fail
  the primary eval, but is tracked separately.
