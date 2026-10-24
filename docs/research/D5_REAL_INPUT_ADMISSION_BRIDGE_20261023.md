# D5 Real-Input Admission Bridge (Implemented, Offline)

> **V25 amendment (2026-10-25) — independent anchored admission (closes V25-S01).**
> The V24 decision below trusted `trust_root.production_trusted`, a property of a
> caller-supplied object; a subclass, fake, or no-op verifier could therefore produce
> real admission. That property is removed. The caller trust root now only verifies the
> acquisition envelope and never decides admission.
>
> - **Admission authority.** `real_data_admitted=True` requires a
>   `D5IndependentAdmissionRecord` (domain `ACASH-D5-INDEPENDENT-ADMISSION/v1`) that binds
>   the bundle `evidence_scope_sha256`, names the envelope's acquisition key, is signed by
>   a *different* admitter key, and verifies (shared Ed25519 primitive
>   `verify_ed25519_signature`) against the module-pinned `D5_ADMISSION_TRUST_ANCHORS`.
>   The anchors are **empty**: no production root is fabricated, so real admission is
>   unreachable until a production admitter public key is provisioned out of band and
>   added by a reviewed change. Private keys never enter the repository. Revocation is
>   removal from the anchors.
> - **Retrospective vs PIT (P1).** `D5AdmissionKind.RETROSPECTIVE_RESEARCH` yields
>   `D5_RETROSPECTIVE_RESEARCH_ADMITTED` at `RETROSPECTIVE_QUALITY_QUALIFIED` with
>   `NOT_POINT_IN_TIME` retained; `PIT_RESEARCH` yields `D5_REAL_INPUT_ADMITTED` at
>   `PIT_EVIDENCE_QUALIFIED`. The kind must match the claimed level, and the scope digest
>   covers claimed level and PIT fields, so metadata edits cannot upgrade a retrospective
>   record to PIT (`D5_ADMISSION_KIND_MISMATCH` / `D5_ADMISSION_RECORD_SCOPE_MISMATCH`).
> - **Temporal policy.** The acquisition envelope must be valid at review time
>   (`now_utc`). The admission record must satisfy
>   `envelope.valid_from_utc <= admitted_at_utc <= now_utc`
>   (`D5_ADMISSION_RECORD_PREDATES_EVIDENCE` / `D5_ADMISSION_RECORD_FUTURE_DATED`).
>   An expired envelope blocks even with a valid record; re-review requires a new envelope.
> - **Manifest.** `production_trust_root` is replaced by `admission_kind`;
>   `TRUST_ROOT_NOT_PRODUCTION` is replaced by `NO_ANCHORED_ADMISSION_RECORD`.
> - **Residual limits.** In-process code can still monkeypatch module state; anchors
>   defend against caller-supplied objects, not against code modification (which is
>   covered by review). The admission record attests a human/authority decision; it does
>   not itself prove census completeness or PIT archive genuineness. Distinct key IDs are
>   enforced; distinct key *custody* is an operational control outside this code.
>
> Tests (`tests/unit/data/test_lane_b_d5_admission.py`): fake/subclass/no-op roots,
> empty-anchor default, attacker and self-signed admitter keys, re-signed envelopes over
> fabricated pages / modified PIT digest / census omission / budget change, replayed
> record, revoked anchor, acquisition-operator self-admission, kind upgrade, temporal
> bounds. Positive paths use a test-only monkeypatched anchor (verifies logic only).

> **V24 amendment (2026-10-25) — evidence trust boundary.** The V23 bridge below could
> return `D5_REAL_INPUT_ADMITTED` with `real_data_admitted=True` from caller-constructed
> fields alone (`ISSUED`, `OPERATOR_ISSUED`, `pit_vintage_known=True`, a non-empty
> `pit_evidence_ref`). That path is closed. Admission now evaluates three boundaries:
>
> 1. **Structural qualification** — unchanged checks (authority fields, raw pages,
>    request identity, pagination, budgets, calendar, claimed level).
> 2. **External evidence** — an `OPERATOR_ACQUISITION` bundle must carry a
>    `D5EvidenceEnvelope` (domain `ACASH-D5-REAL-INPUT-ADMISSION/v1`) whose Ed25519
>    signature verifies through the shared D3 primitive `InMemoryTrustRoot.verify_signature`
>    and whose signed `evidence_scope_sha256` equals the recomputed digest of authority,
>    origin, claimed level, PIT flags/ref/digest, every page identity, dividends,
>    expected ex-dates and expected dividends. Missing envelope or trust root:
>    `D5_EXTERNAL_EVIDENCE_PENDING`.
> 3. **Admission decision** — `real_data_admitted=True` only for a PIT claim whose
>    envelope verified under a trust root with `production_trusted=True`. The repository
>    contains no such root (`InMemoryTrustRoot.production_trusted` is always `False`), so
>    a verified test-key PIT claim yields `D5_EVIDENCE_VERIFIED_INDEPENDENT_ADMISSION_REQUIRED`
>    and is sealed as `REAL_CANDIDATE` / `RETROSPECTIVE_QUALITY_QUALIFIED` with limitations
>    `INDEPENDENT_ADMISSION_REQUIRED` and `TRUST_ROOT_NOT_PRODUCTION`.
>    `FULL_DATASET_ADMITTED` remains unreachable from this function.
>
> **Remaining limits.** The envelope authenticates the signer's attestation of the scope;
> it does not prove the dividend census is complete against independent issuer data or
> that the PIT archive referenced by `pit_evidence_sha256` is a genuine vintage. Those
> require external evidence and a production trust root with ratified key custody.
> The envelope window is checked at `now_utc`; separating acquisition-time validity from
> later review is an open design item. Tests: `tests/unit/data/test_lane_b_d5_admission.py`
> (fail-first cases 1–10).

**Date:** 2026-10-23
**Scope:** Offline contract and adversarial tests only. No provider request, no credential use, no broker call.
**Status:** `IMPLEMENTED_OFFLINE`
**Real-data status:** `D5_REAL_DATA_NOT_ADMITTED`
**Lane B status:** `UNISSUED`

## 1. What Changed

Before this bridge, `evaluate_d5_offline_rehearsal()` could seal only synthetic input and
explicitly refused `DatasetOrigin.REAL_CANDIDATE`. That proved the pipeline but left no
truthful path from a real acquisition to a D5 seal.

The bridge is `evaluate_d5_real_admission()` in
`src/acash/data/qualification/lane_b_d5_rehearsal.py`. It re-derives the dataset from
retained raw pages and seals only the evidence level whose prerequisites are actually
present. It does not accept a caller-supplied `approved` flag.

## 2. Admission Contract

1. **Exact authority.** The bundle carries a `D5AdmissionAuthority` with status,
   provenance, symbol universe, feed, timeframe, inclusive date scope, adjustments,
   HTTP/byte budgets, validity window, authority reference and approval reference.
   `ISSUED` and an open time window are required.
2. **Page identity.** Every `D5RawPage` stores `request_sha256`, `content_sha256`,
   raw bytes, adjustment, contiguous page index and page tokens. The request digest
   binds the authority reference, approval reference, provider identity, scope,
   adjustment, page token and canonical request fields.
3. **Pagination integrity.** Pages must start at index 0, be contiguous, start with a
   null token, chain by `next_page_token`, terminate with null, and never replay a
   token.
4. **Raw derivation.** Bars are parsed from retained raw bytes with
   `parse_bars_page()`, attributed to the New York trading date with `bar_date()`, and
   converted to `DailyBar` under the existing model validators. The bridge does not
   accept caller-authored bars as proof.
5. **Coverage and calendar.** The exact exchange calendar is generated by
   `expected_session_dates()`/`NyseCa1Calendar`; D5's existing `qualify_bar_series()`
   and `require_no_unbound_splits()` enforce missing, duplicate, off-calendar and
   split/raw alignment.
6. **Dividend binding.** Events remain source-confirmed, row-referenced and
   symbol-bound. An optional expected event tuple must match exactly. GLD cash
   distributions remain forbidden.
7. **Evidence levels.** `SYNTHETIC_PIPELINE_PROOF` cannot become real by claim.
   Retrospective input may become `RETROSPECTIVE_QUALITY_QUALIFIED` with
   `real_data_admitted: false`. `PIT_EVIDENCE_QUALIFIED` additionally requires all
   PIT flags and a non-empty PIT evidence reference. `FULL_DATASET_ADMITTED` requires
   a separate admission record and is always refused here.
8. **One seal path.** The bridge calls the same private D5 sealing composer. Direct
   `DatasetOrigin.REAL_ADMITTED` sealing through
   `evaluate_d5_offline_rehearsal()` is blocked.

## 3. Evidence Levels

| Level | Produced by bridge | Real data admitted | Meaning |
| :--- | :--- | :--- | :--- |
| `SYNTHETIC_PIPELINE_PROOF` | Yes, synthetic input only | No | Pipeline/seal behavior |
| `SOURCE_VERIFIED_CANDIDATE` | No | No | D4 candidate status, not D5 |
| `RETROSPECTIVE_QUALITY_QUALIFIED` | Yes, operator bundle | No | Quality/coverage in hindsight |
| `PIT_EVIDENCE_QUALIFIED` | Yes, with PIT evidence | Yes, for this bundle | PIT-bound evidence level |
| `FULL_DATASET_ADMITTED` | No | No | Separate admission record required |

`RETROSPECTIVE_QUALITY_QUALIFIED` is not D4 admission, not PIT qualification and not a
trading authorization. The sealed manifest records the limitations.
`PIT_EVIDENCE_QUALIFIED` is still not Lane B issuance, not a D6 result and not
permission for live orders.

## 4. Adversarial Coverage

Tests: `tests/unit/data/test_lane_b_d5_admission.py`.

Covered cases include: retrospective sealing, PIT admission with evidence, PIT claim
without evidence, synthetic claims of real evidence, `FULL_DATASET_ADMITTED` refusal,
`SOURCE_VERIFIED_CANDIDATE` refusal, unissued/revoked/expired authority, request digest
tamper, content digest tamper, cross-authority page reuse, pagination chain breakage,
missing sessions, mixed/out-of-scope symbols, byte/page budgets, dividend input mismatch,
missing adjustment pages, and direct offline sealing of `REAL_ADMITTED`.

## 5. Known Limits

- Structural authority validation is not proof that a human signed the referenced
  approval. The signature/trust root is out-of-band evidence and remains unresolved.
- The bridge does not acquire data, resolve provider entitlements or prove that raw
  retention is permitted by contract.
- No crash-durability or immutable-persistence claim is made for stored pages.
- The bridge does not replace D4 panel adjudication, establish PIT vintages by itself,
  or authorize Lane B, D6 trading or real orders.
- Test pages are synthetic fixtures; they are not market evidence.

## 6. Files

- `src/acash/data/qualification/lane_b_d5_rehearsal.py`
- `src/acash/data/qualification/lane_a_rehearsal.py` (exported parser/date/calendar helpers)
- `tests/unit/data/test_lane_b_d5_admission.py`
- `docs/research/D5_OFFLINE_PIPELINE_REHEARSAL_20261022.md`
