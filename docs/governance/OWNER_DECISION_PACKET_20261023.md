# Owner Decision Packet — 2026-10-23

**Status:** `AWAITING_OWNER_DECISIONS`
**Software baseline:** `2cd9a02104d30b3a6dddf90ce39f1d70b0731ba6` (PR #48 merged; main CI `39889802190` 5/5 success)
**Real-data admission:** `NOT_ADMITTED`
**Lane A/B:** `UNISSUED`
**Capital authority:** USD 0.00; `NO_REAL_ORDERS=true`

This packet consolidates the decisions that actually require the owner. It does not
ratify anything by itself, and it does not authorize acquisition, retention, dataset
admission or trading.

## 1. Current Truth

- PR #48 is merged into `main`; exact-head CI passed 5/5 and post-merge main CI
  `39889802190` passed 5/5.
- The D3 V2 byte contract is implemented and offline-tested, but formally
  `PENDING_FORMAL_RATIFICATION`.
- The D5 real-input admission bridge is implemented offline. It can seal retrospective
  input at `RETROSPECTIVE_QUALITY_QUALIFIED` and PIT input at `PIT_EVIDENCE_QUALIFIED`;
  no real bundle has been admitted.
- Alpaca historical retrieval is evidenced for a prior account/window. Current account
  tier, 2026 access, raw-retention permission and redistribution permission remain
  unresolved.
- BND/BIL/VOO/GLD have 30 `SOURCE_VERIFIED_CANDIDATE` events and 0 partial events. This is
  D4 candidate evidence, not D5 admission.
- Trust root, key custody, trusted clock and crash durability remain unresolved or
  `CANNOT_VERIFY`.
- No provider request, credential use, subscription purchase, real dataset read, paper
  order, live order or capital deployment occurred in V23.

## 2. Decisions Requested

### Decision 1 — V2 Byte Contract

Sign, defer or reject
`docs/governance/D3_V2_RATIFICATION_ARTIFACT_DRAFT_20261023.md`.

If ratified, the contract is
`IDENTITY_ONLY_RAW_RESPONSE_BODY_V2`, with exact implementation/test digests, 524,288
observed bytes per invocation, zero retry/fallback and cap poisoning on rejection.

This decision does **not** authorize HTTP, credentials or acquisition.

### Decision 2 — Alpaca Rights

Provide or authorize a written answer covering the eight dimensions in
`docs/governance/ALPACA_RIGHTS_MATRIX_20261023.md`, especially:

1. current plan/tier and 2016-2025 access;
2. SIP/IEX entitlement;
3. raw retention;
4. derived internal use;
5. redistribution;
6. adjustment/corporate-action/PIT policy.

If no written answer is available, record `UNKNOWN` and keep acquisition
`UNISSUED`. Do not treat public documentation as account-specific permission.

### Decision 3 — Trust Root and Durability

Choose one:

- provide authenticated trust-root, key-custody and crash-durability evidence;
- explicitly accept the unresolved state for a bounded offline-only phase; or
- keep the boundary closed.

The current state does not support an immutable-persistence or authenticated-owner claim.

### Decision 4 — Full-History Scope

Approve, defer or reject
`docs/research/FULL_HISTORY_ACQUISITION_PROPOSAL_20261023.md`.

The proposed scope is VOO/BND/GLD/BIL, `1Day`, `raw` + `split`, 2016-01-01 through
2025-12-31, one feed, at most 32 requests and 8,388,608 observed bytes, USD 0, zero
retry/fallback. It is separate from the five-session canary and is **not issued** by
this packet.

### Decision 5 — Governance Simplification

Approve, defer or reject
`docs/governance/DATA_ACQUISITION_GOVERNANCE_SIMPLIFICATION_20261023.md`.

The proposal reduces duplicate decision surfaces while preserving exact-scope authority,
anti-bypass rules and separate paper/live gates. It does not reduce the trust-root or
rights requirements by itself.

### Decision 6 — D6 Run

Do **not** approve a D6 empirical run yet. The preregistered contract is
`docs/research/D6_PREREGISTERED_CONTRACT_20261023.md`; execution requires D5 admission
and a separate empirical-run authorization.

## 3. Evidence Index

| Item | Location | State |
| :--- | :--- | :--- |
| V2 code/tests | `src/acash/data/qualification/lane_a_d3_streaming.py`, `tests/unit/data/test_lane_a_d3_streaming_v2.py` | 20 V2 + 19 V1 tests pass offline |
| D5 admission bridge | `src/acash/data/qualification/lane_b_d5_rehearsal.py`, `tests/unit/data/test_lane_b_d5_admission.py` | Implemented offline; no real admission |
| D5 bridge design | `docs/research/D5_REAL_INPUT_ADMISSION_BRIDGE_20261023.md` | `IMPLEMENTED_OFFLINE` |
| V2 ratification draft | `docs/governance/D3_V2_RATIFICATION_ARTIFACT_DRAFT_20261023.md` | `DRAFT_UNSIGNED` |
| Rights matrix | `docs/governance/ALPACA_RIGHTS_MATRIX_20261023.md` | 1 proven / 5 limited / 2 unknown |
| Governance proposal | `docs/governance/DATA_ACQUISITION_GOVERNANCE_SIMPLIFICATION_20261023.md` | `PROPOSAL_NOT_RATIFIED` |
| Full-history proposal | `docs/research/FULL_HISTORY_ACQUISITION_PROPOSAL_20261023.md` | `PROPOSED_NOT_ISSUED` |
| D6 contract | `docs/research/D6_PREREGISTERED_CONTRACT_20261023.md` | `DRAFT_PREREGISTRATION_NOT_RATIFIED` |
| D4 candidate panel | `docs/research/lane_b_candidate_events_2025_2026.json` | 30 candidate / 0 partial |
| Alpaca historical evidence | `docs/phase14/HYP_009_R2_M1_DATA_QUALIFICATION.md` | Prior window; not current entitlement |

## 4. Boundaries Preserved

- No real HTTP dispatch.
- No credential use or paid subscription.
- No raw or protected dataset read.
- No Lane A or Lane B issuance.
- No D3/D4/D5 real-data admission.
- No D6 empirical run.
- No paper/live orders.
- `REAL_CAPITAL_AUTHORITY = USD 0.00`.
- `NO_REAL_ORDERS = true`.

## 5. Owner Signature

```markdown
Decision 1 (V2):        [ ] RATIFIED   [ ] DEFERRED   [ ] REJECTED
Decision 2 (Rights):    [ ] PROVIDED   [ ] DEFERRED   [ ] KEEP UNKNOWN
Decision 3 (Trust):     [ ] EVIDENCE   [ ] ACCEPT UNRESOLVED OFFLINE   [ ] KEEP CLOSED
Decision 4 (History):   [ ] APPROVED   [ ] DEFERRED   [ ] REJECTED
Decision 5 (Governance):[ ] APPROVED   [ ] DEFERRED   [ ] REJECTED
Decision 6 (D6 run):    [ ] NOT NOW

Effective date (UTC): ____________________
Operator signature: ______________________
Operator name: ___________________________
Notes: __________________________________
```
