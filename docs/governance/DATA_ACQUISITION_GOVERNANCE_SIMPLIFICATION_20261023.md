# Data-Acquisition Governance Simplification Proposal

**Date:** 2026-10-23
**Status:** `PROPOSAL_NOT_RATIFIED`
**Scope:** Reduce repeated decision friction without converting unresolved evidence into
permission. This document does not issue, widen or transfer authority.

## 1. Problem

The current path repeats the same questions across the D3 packet, Lane A packet, rights
matrix, trust-root discussion and acquisition authority:

- Is the byte contract ratified?
- Is the account entitled?
- Is raw retention permitted?
- Is the trust root proven?
- Is the exact scope authorized?
- Is the budget bounded?

Re-asking is safe, but duplicate unstructured requests delay work and obscure which
single artifact actually controls. The fix is one decision surface per boundary, not
fewer controls.

## 2. Proposed Decision Tiers

| Tier | Work | Human artifact | Repeat per PR? |
| :--- | :--- | :--- | :--- |
| 0 | Offline code, tests, docs, refactors, CI | Existing owner authorization for ordinary software work | No separate data signature |
| 1 | One exact-scope real acquisition | Signed scoped authority + rights addendum + byte contract | No, one artifact per scope |
| 2 | Dataset admission / paper / live | Separate admission and operating authorization | Yes, per boundary |

Tier 0 cannot dispatch real HTTP, use credentials, retain provider data or trade. Tier 1
cannot seal a dataset, issue Lane B or trade. Tier 2 cannot start without its own explicit
artifact.

## 3. Single Authority Object

A Tier 1 authority should be one immutable record containing:

- authority reference and approval reference;
- provider, feed, timeframe, symbols, inclusive start/end;
- adjustments (`raw`, `split`);
- maximum HTTP requests and observed bytes;
- issue/expiry timestamps;
- permitted use: acquisition and offline sealing only;
- explicit exclusions: no retry, no fallback, no redistribution, no paper/live orders,
  no capital.

The executable contract is
`D5AdmissionAuthority` in
`src/acash/data/qualification/lane_b_d5_rehearsal.py`. Structural validation is not a
signature. The human signature remains external evidence.

## 4. One Ratification, One Reference

- Ratify the byte contract once, with a versioned digest and effective date.
- Reuse that ratification in later packets by reference; do not re-ratify the same text.
- A material semantic change creates a new version and a new decision.
- V2 remains `PENDING_FORMAL_RATIFICATION` until the owner signs the V2 section of the
  D3 packet.

## 5. Evidence Levels Instead of Boolean “Approved”

Use the levels already implemented for D5:

`SYNTHETIC_PIPELINE_PROOF` → `SOURCE_VERIFIED_CANDIDATE` →
`RETROSPECTIVE_QUALITY_QUALIFIED` → `PIT_EVIDENCE_QUALIFIED` →
`FULL_DATASET_ADMITTED`.

A lower level must never be described as a higher one. In particular:

- D4 candidate status is not D5 admission.
- Retrospective quality is not PIT.
- A D5 seal is not Lane B issuance.
- A D6 baseline is not live-capital authorization.

## 6. Anti-Bypass Rules

1. No caller-supplied `approved=true` flag may seal data.
2. No missing authority, expired window, scope mismatch, page tamper or unbound split may
   be “warned” into a pass.
3. No self-approval by the implementing agent.
4. No merge without exact-head required CI and the repository ruleset.
5. No evidence-level upgrade by documentation alone.

## 7. What This Proposal Does Not Do

It does not reduce the trust-root requirement, grant raw-retention rights, authorize
acquisition, admit D4/D5 data, issue Lane A/B, start D6, unlock paper/live trading or
change `REAL_CAPITAL_AUTHORITY = USD 0.00` / `NO_REAL_ORDERS=true`.

Adoption requires a separate owner decision. Until then this is a proposal only.
