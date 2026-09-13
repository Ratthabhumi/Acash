---
name: acash-feed-resilience
description: Diagnose ACASH feed disconnects, ReadTimeout, missing bars and recovery observability; preserve operator-only resume and fail-closed behavior.
---

# ACASH feed resilience and observability

Read root `AGENTS.md`, O1 in `E3.6-HUMAN-DECISIONS.md`, and the feed source/test
links in `docs/engineering/agent-workflow.md`. Verify explicit supersession before
using a different recovery policy. Inspect both `feed.py` (provider) and
`session.py` (supervisor); do not infer supervisor behavior from adapter code.

The O1 Option A contract is explicit operator resume only:
feed failure -> FEED_DISCONNECTED -> HALTED / fail closed -> explicit operator
resume -> RECOVERY_ATTEMPTED -> FEED_CONNECTED or FEED_CONNECT_FAILED.
Audit requests do not authorize calling `reconnect()` or `--resume`.

- Preserve logs and journal chronology with secrets redacted before output. Reuse
  the existing `sanitize_diagnostic_text` implementation and inspect its coverage;
  its existence alone is not proof that every secret format is handled.
- Record error class/category, operation, endpoint without credentials, provider,
  symbol/timeframe, HTTP status when present, configured timeout, last successful
  poll, last successful bar and recovery attempts. Distinguish request success
  from new-bar admission and event time from observation time.
- Derive a data gap only from available, correctly ordered timestamps and the
  documented definition. Missing timestamps are unknown, not zero. Inspect
  diagnostics metadata and journal events rather than inventing provider status.
- Reproduce with mocked transport when appropriate. `ReadTimeout` proves a read
  timeout; provider outage, network instability or memory exhaustion remain
  unproven until independent evidence supports them.
- Verify no market-data decisions occur while unhealthy; a failed recovery must
  remain halted and must not emit fake connected success. No automatic retry or
  reconnect loop, automatic bar admission or altered freshness gate without the
  relevant human decision. Reconnection does not grant trading authority.

Run the existing feed observability and mocked integration tests for an
authorized implementation change. Report PROVEN, LIKELY and POSSIBLE causes,
containment, minimal proposed fix, regression evidence and governance impact;
finish with the root ledger.
