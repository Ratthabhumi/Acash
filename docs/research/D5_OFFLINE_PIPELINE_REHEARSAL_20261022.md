# D5 Offline Dataset-Sealing Rehearsal (Synthetic, Unissued)

**Date:** 2026-10-22
**Scope:** Offline only. No market-data request, no broker call, no protected dataset read.
**Verdict:** `D5_OFFLINE_PIPELINE_READY` (synthetic fixture)
**Real-data verdict:** `D5_REAL_DATA_NOT_ADMITTED`

## 1. What This Proves

The canonical price, dividend, split, provenance and manifest contracts compose into a
deterministic, fail-closed dataset seal:

1. Request identity is bound before sealing (symbols, feed, timeframe, adjustment, window).
2. Split/raw price series must match the expected session calendar exactly.
3. Cash distributions are validated per symbol and must be source-confirmed with a row
   reference and known PIT vintage.
4. The dataset payload is serialized with `CanonicalConfigSerializer` and sealed with
   `compute_page_sha256` + `compute_framed_composite_sha256`.
5. Any byte-level or framing tamper fails verification.
6. Synthetic payloads are labelled `SYNTHETIC_FIXTURE_NOT_MARKET_HISTORY` and carry
   `real_data_admitted: false`.
7. Every dividend event binds its `symbol`; cross-symbol reassignment changes the seal.
8. Full OHLCV (open/high/low/close/volume) is included in the sealed bytes, together
   with `price_semantics`, `time_basis`, `share_basis` and `sessions_authority`.
9. `DatasetOrigin.REAL_CANDIDATE` can never return READY or release sealed bytes: real
   sealing requires a separate authorized admission path (not implemented here).

This does **not** qualify real data and does **not** issue Lane B authority.

## 2. Reused Canonical Components (no second framework)

| Concern | Authority |
| :--- | :--- |
| Session/bar qualification | `src/acash/research/hyp_009/qualification.py::qualify_bar_series` |
| Dividend binding/contradiction | `qualify_dividends` |
| Split/raw reconciliation | `require_no_unbound_splits` |
| Canonical serialization | `src/acash/core/serialization.py::CanonicalConfigSerializer` |
| Page + composite hashing | `src/acash/data/qualification/manifest.py` |
| Candidate corporate actions | `src/acash/data/qualification/lane_b_candidate_evaluator.py` |

New code is limited to the rehearsal composer:
`src/acash/data/qualification/lane_b_d5_rehearsal.py`.

## 3. Adversarial Coverage

Tests: `tests/unit/data/test_lane_b_d5_rehearsal.py` (25 cases).

| Case | Expected | Result |
| :--- | :--- | :--- |
| Synthetic end-to-end seal + verify | READY | PASS |
| Permuted dividend/bar input order | identical SHA | PASS |
| Byte tamper | `D5_TAMPER_DETECTED_*` | PASS |
| Missing / duplicate / extra session | BLOCKED | PASS |
| `SOURCE_PARTIAL` contamination | PARTIAL, no seal | PASS |
| Missing `source_row_ref` | PARTIAL, no seal | PASS |
| Unknown PIT vintage | PARTIAL, no seal | PASS |
| GLD cash dividend attempt | BLOCKED | PASS |
| Contradictory same-ex-date amount | BLOCKED | PASS |
| Identical duplicate event | BLOCKED | PASS |
| Date-order violation (ex > record) | BLOCKED | PASS |
| Missing expected event coverage | PARTIAL | PASS |
| Unapproved (SPY) / excluded (GLDM) universe | BLOCKED | PASS |
| Wrong feed identity | BLOCKED | PASS |
| Missing approval lineage | BLOCKED | PASS |
| Payable date outside window | allowed + recorded | PASS |
| Non-positive amount | BLOCKED | PASS |
| Ex-date outside scope | BLOCKED | PASS |
| Missing series for a symbol | BLOCKED | PASS |
| Synthetic label present in bytes | PASS | PASS |
| Cross-symbol dividend reassignment | digest changes | PASS |
| Changed open/high/low (same close/volume) | digest changes | PASS |
| Dividend-paying symbol without declared coverage | BLOCKED | PASS |
| `REAL_CANDIDATE` with declared confirmed rows | PARTIAL, no bytes | PASS |
| Semantic fields present in payload | symbol/OHLC/basis bound | PASS |

## 3.1 Known limits

- `sessions_authority` is `CALLER_SUPPLIED_SYNTHETIC`; it is not an independently
  verified exchange calendar.
- `source_row_ref` is metadata, not artefact authenticity, and not a cryptographic seal.
- Real-data sealing requires a separate, versioned authorized admission entrypoint; the
  synthetic composer deliberately cannot produce one.

## 4. D4 Offline Qualification Rehearsal

No new D4 code was required: the existing `lane_b_candidate_evaluator.py` contracts
already fail closed on the adversarial cases above, and no failing test exposed a gap.
The evaluator now completes at `SOURCE_VERIFIED_CANDIDATE` after the V20 BND capture
(all 30 cash rows are issuer-source-bound); it is still not wired into D5 admission.

## 5. Gate Matrix

| Gate | Required contract | Evidence | Outcome | Blocker |
| :--- | :--- | :--- | :--- | :--- |
| D3 | Provider/feed access authorized | `docs/governance/D3_DECISION_PACKET_BYTE_POLICY_AND_RIGHTS.md` | **UNKNOWN** | No account entitlement; byte contract PROPOSED |
| D4 | Issuer actions independently source-qualified for scope | `lane_b_candidate_events_2025_2026.json`, report §2.1/§2.3 | **SOURCE_VERIFIED_CANDIDATE** | PIT vintage/revision policy unknown; no D4 admission |
| D5 | Reproducible dataset from qualified inputs | this rehearsal (synthetic) | **READY (synthetic)** | No authorized real inputs |
| D5 real | Empirical admission | — | **NOT ADMITTED** | D3/D4 gates open |

## 6. Next Owner Decision

Ratify or reject `IDENTITY_ONLY_RAW_RESPONSE_BODY_V1` (cap 524288 observed bytes,
identity encoding, no retries, no fallback), which is the only D3 gate that can unblock
real acquisition preparation.

## 7. Next Evidence-Producing Task

The 8 remaining BND rows were captured on 2026-10-22 from the Vanguard BND investor
product page embedded distribution table (226,062 bytes, SHA-256
`d09560f58834be2b1297f782969410aba07adab08f1a537a366f3dcd916d3abd`), bound by
`recordDate`. They are now `SOURCE_CONFIRMED_CANDIDATE`. The advisors page (HTTP 200,
161,898 bytes) still exposes no dataset or export endpoint.

The next evidence task is the D3 rights/byte-policy decision; BND vintage and revision
policy remain unverified.
