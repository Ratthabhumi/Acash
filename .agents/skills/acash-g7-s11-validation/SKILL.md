---
name: acash-g7-s11-validation
description: Audit G7 or S11 soak evidence in ACASH against the ratified continuous-run criteria; distinguish continuous, interrupted and operator-recovered runs.
---

# ACASH G7 / S11 evidence audit

Read root `AGENTS.md`, `E3.6-HUMAN-RATIFICATION-G7-SOAK.md` and
`E3.6-HUMAN-DECISIONS.md`. The duration authority is
RATIF-E36-G7-SOAK-20260912: 6 continuous hours, an explicit amendment of historical
72 hours. Verify any later scoped supersession; never silently rewrite the old
design or weaken the amendment's remaining criteria.

An audit is read-only and grants no launch, container restart, resume or trading
permission. Locate the actual host/container records, session and window
manifests, journal and telemetry for the same run and provenance.

- Classify the run CONTINUOUS, INTERRUPTED or OPERATOR-RECOVERED. Use event-time
  coverage and halt/recovery chronology, not elapsed process age alone. Disjoint
  intervals cannot be added into an uninterrupted six-hour result.
- Check at least 6.00 consecutive hours of continuous M1 execution; the record
  expects 360 bars under active feed. Inspect duplicates, gaps and timestamps;
  a count alone is insufficient. Unknown coverage stays unresolved.
- Verify zero unexpected crashes/restarts and `RestartCount == 0`; memory bounded
  under 512 MiB with the record's expected <150 MiB distinguished from its hard
  limit; inspect growth through the interval, not a single RSS sample.
- Verify journal/window integrity and reconciliation using existing code, and
  continuous VictoriaMetrics scraping on internal port 9102 without stalls or
  target dropouts. A healthy final scrape does not establish continuity.
- Inspect the actual run's internal `homelab_acash_staging` network, zero
  published host ports, non-root UID `10001:10001`, no-new-privileges,
  `NO_REAL_ORDERS=true` and `ACASH_CANONICAL_CAPITAL=0`. Repository Dockerfile
  inspection cannot establish the deployed compose/runtime configuration.
- Preserve O1 operator-only recovery. An interrupted/recovered run may provide
  diagnostic evidence; it is not automatically equivalent to continuous G7
  acceptance. Passing infrastructure acceptance never authorizes Paper trading.

Return a criterion/evidence/verdict/missing-evidence matrix. Separate audit
completion, technical acceptance assessment and human acceptance/authorization.
If run artifacts are unavailable, report NOT VERIFIED and identify the needed
evidence without inventing a PASS or launching a new run. Finish with the root
ledger; unit tests are not empirical soak verification.
