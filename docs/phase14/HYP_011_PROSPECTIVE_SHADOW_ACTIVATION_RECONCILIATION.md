# HYP_011 Prospective Shadow Activation Reconciliation

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_PROSPECTIVE_SHADOW_ACTIVATION]
[SCIENTIFIC_PROSPECTIVE_BOUNDARY: 2026-09-25 (UNCHANGED)]
[NO_HISTORICAL_BACKFILL]
```

- **Manifest:** `docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_ACTIVATION_RECONCILIATION.json`
- **Corrected R3 authority:** `HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW`
  (G1–G6 PASS, network 0, dataset `4cf20b51…`)

## 1. Scientific Boundary Preserved

R1 prospective boundary 2026-09-25 (first open strictly after R1 commit
2026-09-24T22:34:44Z) is NOT rewritten and NOT pretended later.

## 2. No-Backfill Reconciliation

Sessions in [2026-09-25, activation-exclusive) that completed without
authorized observation are `MISSED_UNOBSERVED_DUE_TO_AUTHORIZATION_LOCK`:
zero price access, no retrospective fetch, no reconstruction, excluded from
P&L, metrics, and the 504-session clock. This is an operational gap, not
hypothesis failure. It is NOT quarantine (2026-08-15..2026-09-25-exclusive
remains untouched under its own classification).

## 3. Operational Activation (Two-Stage Binding)

- Operational start: first canonical NYSE regular-session open STRICTLY AFTER
  the Stage-A activation commit timestamp (derived from NyseCa1Calendar, never
  hard-coded, never from prices).
- Activation commit SHA/timestamp: `PENDING_BINDING` in Stage A; bound in the
  additive Stage-B artifact from the real commit.
- At activation: fresh 100000.00 shadow simulation (80/20 whole-share solver,
  no historical holdings carryover, no 2025/recent-stress/missed data).
- Minimums: ≥504 observed sessions AND ≥2 observed annual rebalances
  (later of the two); missed sessions count 0 and cannot shorten the minimum.
- No interim verdict/tuning before both minimums (`NON_DECISIVE_PROSPECTIVE_SHADOW_MONITORING`).
- Recent stress stays unused and non-decisive. No backfill ever.

## 4. Implementation

- Module: `src/acash/research/hyp_011/shadow.py` (activation derivation,
  missed-session derivation, append-only state with duplicate/out-of-order/
  early/future/recent-stress/quarantine guards).
- Session runner contract (§14): process exactly the next unprocessed eligible
  COMPLETED session; reject duplicates/out-of-order/early/future/stress/
  quarantine. No autonomous trading; data/research only.
- Tests: `tests/unit/research/test_phase14_hyp_011_prospective_shadow.py`.
- Paper NOT_AUTHORIZED, live LOCKED, capital $0.00, NO_REAL_ORDERS=true.
