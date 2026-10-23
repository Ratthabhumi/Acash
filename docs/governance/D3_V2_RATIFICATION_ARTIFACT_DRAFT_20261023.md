# D3 V2 Ratification Artifact (Draft, Unsigned)

**Status:** `DRAFT_UNSIGNED`
**Contract:** `IDENTITY_ONLY_RAW_RESPONSE_BODY_V2`
**Parent main:** `ef89fd49b1f092bacd0847d6d56dfc4d8c132bfd`
**Date:** 2026-10-23

This artifact is a signing surface, not a ratification. It does not authorize HTTP
dispatch, credentials, market-data acquisition, Lane A/B, dataset admission or trading.

## 1. Exact Specification

V2 preserves V1 except for the following, all evaluated before body iteration:

1. A present `Content-Length` must be exactly one field of `1*DIGIT`.
2. Multiple fields, whitespace, signs, commas, decimal points, empty fields or other
   non-digits are rejected.
3. Negative or ambiguous lengths are rejected.
4. A missing `Content-Length` remains allowed; observed chunk bytes are authoritative.
5. A non-identity `Content-Encoding` is rejected and poisons the byte cap.
6. An already-consumed response is rejected and poisons the byte cap.
7. A poisoned cap is rejected before any subsequent read; an empty body cannot be used
   to retry or bypass the failed response.
8. Budget: 524,288 observed raw body bytes per approved invocation; no reset on failure;
   zero retry; zero fallback; no alternate-feed substitution.
9. Identity-only encoding, raw-byte counting, post-read oversized-chunk disclosure and
   the no-hard-memory-bound limitation remain in force.
10. V1 remains available and unchanged for reproducibility of previously reviewed
    evidence.

## 2. Bound Implementation

| Artifact | SHA-256 |
| :--- | :--- |
| `src/acash/data/qualification/lane_a_d3_streaming.py` | `d556a438d72df701e9f2b4c9f4b7406bedf39e8f3cb5f76d8026967244834ecb` |
| `tests/unit/data/test_lane_a_d3_streaming_v2.py` | `d1506e113cded65f1669e70dbb9204136c3bf7a962c99a1d80db4bb1c2d5a588` |
| `tests/unit/data/test_lane_a_d3_streaming.py` | `86b921586931cf2b24e6bcdb0c6d5a9a427c1ace6f61ca509be7954a82024c7d` |

These digests bind the reviewed working-tree implementation. A later commit must
recompute and record the committed blob hashes before signing.

## 3. Evidence

- V2: 20 `httpx.MockTransport` tests, including malformed/ambiguous/negative length,
  cap poisoning, consumed-response rejection, zero-byte rejection and budget behavior.
- V1: 19 regression tests.
- Targeted run: 39 passed.
- Main CI at parent main: 5/5 success (run `39883674685`).

This evidence proves offline contract behavior only. It does not prove live-provider
behavior, entitlement, durable storage or crash safety.

## 4. Scope and Exclusions

Ratification, if signed, applies only to the versioned byte contract for D3 acquisition.
It does **not**:

- issue Lane A or Lane B;
- authorize credentials, HTTP dispatch or a provider feed;
- admit any dataset to D4 or D5;
- prove Alpaca account rights, raw-retention permission or redistribution rights;
- prove a trust root, key custody, trusted clock or crash durability;
- authorize paper trading, live trading, capital or real orders.

`REAL_CAPITAL_AUTHORITY` remains USD 0.00 and `NO_REAL_ORDERS=true`.

## 5. Prerequisites Still Open

- Owner signature for V2.
- Written Alpaca account/rights confirmation (see
  `docs/governance/ALPACA_RIGHTS_MATRIX_20261023.md`).
- Trust-root/key-custody and crash-durability evidence, or an explicit owner decision
  recording their unresolved state.
- A separate exact-scope acquisition authority.

## 6. Signature Block

```markdown
[ ] RATIFIED: I approve IDENTITY_ONLY_RAW_RESPONSE_BODY_V2 exactly as specified above,
    with the bound implementation and limitations. This approval does NOT authorize
    HTTP dispatch, credentials, Lane A/B, dataset admission or trading.

[ ] DEFERRED: Do not ratify yet; the stated prerequisites remain open.

[ ] REJECTED: Do not adopt V2.

Effective date (UTC): ____________________
Operator signature: ______________________
Operator name: ___________________________
Referenced commit: _______________________
Notes: __________________________________
```

An unsigned copy of this file is evidence of a proposed decision, not consent.
