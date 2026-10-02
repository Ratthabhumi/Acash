# HYP_011 Prospective Segment Policy — V1 Closure / V2 Proposal

**Status**: `V1 = CLOSED_INCOMPLETE_GOVERNANCE_HARDENING` (ratified by this
amendment's acceptance) · `V2 = PROPOSED_PENDING_HUMAN_RATIFICATION`.
**This document activates nothing.** V2 activation requires a separate
explicit human authorization after all V2 gates pass.

---

## 1. Why V1 Must Close (No Rescue Patch)

Observation #1 (2026-09-30) is `COMMITTED_AND_RECONCILED`. Session
2026-10-01 is `MISSED_UNOBSERVED` under the F14 contract (next session
opened before observation).

V1 held **211 AGG shares** at the 2026-09-30 close (operator-supplied
production figure), and AGG has an official 2026-10-01 ex-date distribution
of **$0.334142/share** (BlackRock/iShares official table; see
`docs/audit/CA_2026_10_01_OFFICIAL_SCOPE_NOTE.md`). The missed session
therefore carries a real economic entitlement:

```text
211 shares × $0.334142/share = $70.503962
```

(Arithmetic: 0.334142 × 200 = 66.828400; 0.334142 × 11 = 3.675562;
total 70.503962. Entitlement direction per FINRA ex-date semantics: holders
of record before the ex-date retain the distribution right.)

The current HYP_011 implementation accrues dividends ONLY for corporate
actions fed into `process_strategy_session()` for the session being
processed. Continuing V1 directly to a later observed session would
therefore require reconstructing missed entitlement, peak/drawdown, and
return-path semantics across the gap — an ambiguous economic bridge that
would contaminate the prospective sample. No such bridge is built by this
amendment, deliberately.

## 2. V1 Closure Terms

```text
HYP_011_PROSPECTIVE_V1 = CLOSED_INCOMPLETE_GOVERNANCE_HARDENING
COMMITTED_OBSERVATIONS = 1 (session 2026-09-30)
RESULT = platform-validation evidence preserved;
         NOT mixed into any future contiguous prospective sample
```

Preserved unchanged: Observation #1 artifact bytes, state bytes, all hashes,
all forensic evidence, S1 = 1/20 as platform-validation progress (not as
V2 sample progress).

Forbidden: backfilling 2026-10-01, continuing V1 state across the missed
session, reusing V1 chain/ledger/authority artifacts for V2.

## 3. V2 Proposal (Not Activated)

```text
HYP_011_PROSPECTIVE_V2 = PROPOSED_PENDING_HUMAN_RATIFICATION
- fresh activation session (to be fixed by dispatch authorization)
- fresh simulated $100,000 AUM
- fresh state/hash chain (no V1 carry-over of any kind)
- hardened Evidence Kernel from the first observation
  (intent registry, dispatch authority, attempt ledger, evidence digest
  + semantic identity, CA evidence bundle, zero-network local preflight)
- RegisteredIntent ratified BEFORE the first session opens
- no-backfill; any missed session terminates the segment (same rule)
```

V1 Obs #1 remains platform-validation evidence. It does NOT count toward
any V2 statistical sample. A clean target under discussion is Monday
2026-10-05 or the next session after all gates pass — never retroactively;
if gates are not ready before a session opens, that session is simply not
part of V2 either.

## 4. Boundaries

V2 activation, timer creation, homelab deployment, merges, Paper/Live,
broker connectivity, and real capital are all NOT authorized by this
document. Each requires its own explicit human authorization.
