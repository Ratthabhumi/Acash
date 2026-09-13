---
name: acash-paper-flight-recorder
description: Audit ACASH simulated session journals, manifests, replay and reconciliation; use for flight recorder integrity, deterministic evidence and session provenance reviews.
---

# ACASH paper flight recorder

Read root `AGENTS.md` and the flight-recorder row in
`docs/engineering/agent-workflow.md`. Inspect `src/acash/paper/manifest.py`,
`journal.py`, `replay.py`, `reconcile.py` and `window.py` for the actual schemas and
canonical verification methods before interpreting an artifact.

- Request/locate the specific session and window evidence; do not launch or resume
  a runtime to satisfy an audit. Use read-only inputs and separate temporary
  output for authorized replay; never repair or reseal original evidence silently.
- Trace market/feature/signal/risk/intent/simulated-fill/position/portfolio/health
  events by session ID and correlation IDs. Verify ordering, counts, journal
  chain, final state, reconciliation and the sealed manifest using the existing
  verifier. Surface missing, malformed, contradictory and tampered artifacts.
- Inspect session ID, strategy ID/version, Git commit, config and strategy config
  hashes, environment and dependency metadata, data source, market configuration,
  UTC start/end, event/order/trade/error counts, final state and manifest hash.
  If a requested fact is not in the schema, identify its actual authoritative
  artifact or report it unavailable; never synthesize metadata.
- Distinguish member sessions (UTC days), runtime segments and observation
  windows. Inspect interlock state, failed feeds and operator recovery chronology.
  A session end or restart is not automatically a completed continuous soak.
- Replay stays audit-only with simulated execution and no real broker orders.
  Check the engine's documented nondeterministic fields; do not demand bytewise
  identity of wall-clock metadata or ignore differences in actual decisions.
  Preserve PASS/PARTIAL/FAIL/INSUFFICIENT_DATA distinctions.

Use the recorder, window, and backup/restore tests linked in the source map for
implementation verification. Report artifact integrity, provenance and replay
results separately from research qualification or trading authorization. End
with unresolved evidence, permitted next step and the root ledger.
