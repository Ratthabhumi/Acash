# ACASH V31 — Owner Decision Record and Evidence Registry (2026-10-25)

Status: **ADDITIVE RECORD**. It does not modify any historical draft, contract,
amendment, phase record or frozen evidence.

| Field | Value |
|---|---|
| Recorded (UTC) | 2026-10-25T09:17:48Z |
| Parent main | `1d5da43adec4804becd180b42b1c962805a54212` (PR #60, CI run 40177143639) |
| Recorder | Coding agent (no sovereign authority; not a signatory) |
| Source of owner decision | V31 mandate text supplied by the repository owner in the operator session |
| Owner directive (verbatim) | "ยืนยันสิทธิ์จาก Alpaca และเจ้าของข้อมูล ETF, อนุมัติ A1/A2 อย่างเป็นทางการ และจัดตั้ง Independent Admitter ยืนยันแล้ว อนุมัติทั้งหมด แล้ว ลุยต่อได้เลย" |

Hashing convention: SHA-256 over the committed LF blob bytes
(`git show <commit>:<path>`). The bindings below are re-checked by
`tests/unit/validation/test_v31_owner_decision_bindings.py`.

## 1. A1/A2 owner decision

| Artifact | Path | SHA-256 |
|---|---|---|
| D6 preregistered contract | `docs/research/D6_PREREGISTERED_CONTRACT_20261023.md` | `534e33e57222de5dc478ae1326d21cab1341544eb3361cd87fd9421de38eec32` |
| Amendment A1 (descriptive comparison) | `docs/research/D6_AMENDMENT_A1_DESCRIPTIVE_COMPARISON_UNRATIFIED_20261025.md` | `ab58f1f7a7e05364ee8a70b99209a3d62a32a2a91a29cd4565bebd8ac8d66a65` |
| Amendment A2 (causal execution timing) | `docs/research/D6_AMENDMENT_A2_CAUSAL_EXECUTION_TIMING_UNRATIFIED_20261025.md` | `a285ae8b2b8b124231029899f30d5bbd2ce74bb447deebe815432b7178773869` |

Conflict and precedence check (reviewed against the contract text):

- A1 replaces the contract's undefined §7 risk-limit comparison with a
  descriptive-only comparison. No other contract clause is altered.
- A2 makes `PRIOR_CLOSE_DECISION_NEXT_OPEN` the primary timing. This is consistent with §3.
  `SAME_OPEN_SIZING_IDEALIZED` is a sensitivity mode only. Clarification: the initial
  construction executes on the second session of the window.
- A1's execution row defers to A2 (V28). There is no remaining conflict between A1 and A2.
- Precedence: contract < A1 < A2 for the clauses each amendment names. Nothing else changes.

| Field | State |
|---|---|
| OWNER_DECISION | **OWNER_AUTHORIZED**: A1 and A2 approved by the owner directive above |
| FORMAL_RATIFICATION | **OWNER_APPROVED_PENDING_FORMAL_ATTESTATION** |
| Reason | `docs/governance/MANDATE_RATIFICATION_EVIDENCE_BOUNDARY.md` requires an operator-signed record. An agent-authored commit is not an owner signature. |
| D6 empirical run | **NOT_RUN** (blocked by D5 dataset admission, §5) |

## 2. D3 V2 owner decision

Draft: `docs/governance/D3_V2_RATIFICATION_ARTIFACT_DRAFT_20261023.md` (left unchanged).

| Bound file | Draft digest | Recomputed at `1d5da43` | Match |
|---|---|---|---|
| `src/acash/data/qualification/lane_a_d3_streaming.py` | `8d34c92e…6ec4` | `8d34c92ec554f32938a8fd9e164112d626d97323013846f11b2ed7646e8a6ec4` | YES |
| `tests/unit/data/test_lane_a_d3_streaming_v2.py` | `35185fbd…e9dc` | `35185fbdea0bfd49ca2148a8a163f798c48edadddcb7df355877c4316087e9dc` | YES |
| `tests/unit/data/test_lane_a_d3_streaming.py` | `60214651…c133` | `6021465140db3c0f0c83bd4e09b0cea9e2f5943e12e730cc52c292d4d714c133` | YES |

| Field | State |
|---|---|
| V2_OWNER_DECISION | **OWNER_AUTHORIZED** |
| V2_RATIFICATION | **OWNER_APPROVED_PENDING_FORMAL_ATTESTATION** |
| HTTP authority from V2 | **NONE**. V2 ratification never authorizes provider requests. |

## 3. Rights evidence matrix

No provider agreement, entitlement, issuer permission letter, or digest of such
evidence exists in the repository or the inspected local workspace. Private
agreements and account identifiers must never be committed here. Only a digest and
a scope summary may be recorded.

| PROVIDER | AGREEMENT_REFERENCE / VERSION | RIGHTS_HOLDER | EFFECTIVE_FROM / UNTIL | PERMITTED_FEED / SYMBOLS / HISTORY | RAW_RETENTION_ALLOWED / DURATION | PRIVATE_NORMALIZATION | DERIVED_RESEARCH | AUTOMATED_ACCESS | REDISTRIBUTION | EVIDENCE_DIGEST | VERIFICATION_CLASS | GATE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Alpaca (historical bars) | UNKNOWN | Owner (attested) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | NO (public support page) | NONE | OWNER_ATTESTED | BLOCKED_BY_MISSING_EVIDENCE |
| Vanguard (VOO, BND distributions) | UNKNOWN | Owner (attested) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Restricted by site terms without written permission | NO | NONE | OWNER_ATTESTED | BLOCKED_BY_MISSING_EVIDENCE |
| State Street (BIL distributions) | UNKNOWN | Owner (attested) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | NO | NONE | OWNER_ATTESTED | BLOCKED_BY_MISSING_EVIDENCE |
| WGTS (GLD, not GLDM) | UNKNOWN | Owner (attested) | UNKNOWN | UNKNOWN | UNKNOWN | Written authorization required by site terms | UNKNOWN | UNKNOWN | NO | NONE | OWNER_ATTESTED | BLOCKED_BY_MISSING_EVIDENCE |

Public-terms context: `docs/research/V30_EXTERNAL_RESEARCH_RESULTS_20261025.md`.

To raise a row to `PROVIDER_DOCUMENT_VERIFIED`, the owner keeps the document
outside the repository and supplies its SHA-256, agreement version, effective
dates and the scope fields above. `RIGHTS_SCOPE_MATCHED` requires every scope
field to cover the bounded pilot in §6.

## 4. Independent admitter onboarding

Protocol (reused unchanged; no second signature scheme):
`D5IndependentAdmissionRecord`, `verify_ed25519_signature`, `evaluate_d5_real_admission`
and `D5_ADMISSION_TRUST_ANCHORS` in `src/acash/data/qualification/lane_b_d5_rehearsal.py`.

| Field | State |
|---|---|
| INDEPENDENT_ADMITTER | OWNER_ATTESTED (appointment stated; identity evidence not supplied) |
| PUBLIC_KEY_FINGERPRINT | NONE SUPPLIED |
| CUSTODY_VERIFICATION | UNKNOWN (no separation evidence) |
| D5_TRUST_ANCHOR_STATUS | **EMPTY** (`MappingProxyType({})`, unchanged) |
| D5 dataset admission | **D5_REAL_DATA_NOT_ADMITTED** |

The admitter, not the agent, must supply the following before any anchor is added:

1. An Ed25519 public key (raw 32 bytes, hex) and its SHA-256 fingerprint. The keypair
   must be generated on the admitter's own device. The private key never enters the
   repository, logs, chat or an agent session.
2. Appointment evidence naming the admitter and its scope (D5 dataset admission only).
3. Custody separation: the admitter is not the acquisition operator and does not hold
   the owner's provider credentials.
4. A validity window and a revocation procedure (anchor removal commit plus a reason).
5. An owner-authored commit or PR review that adds the anchor. Synthetic or
   monkeypatched anchors are rejected.

## 5. Transport, host and pilot readiness

| Gate | State | Evidence |
|---|---|---|
| TRANSPORT | EXISTS, not rebuilt | `lane_a_transport.RealTransportBoundary`, allowlist, durable journal |
| Canary authority reuse | REJECTED | `lane_a_authority.py` is a 5-session 2026 raw+all canary and is not reused for ten years |
| HOST_PREFLIGHT | `ready_for_real_acquisition=false` (not overridden) | `host_preflight.py` |
| DURABILITY | OS_CRASH / POWER_LOSS **UNPROVEN** | V27 status |
| Date-only `end` convention | UNKNOWN; needs provider clarification or a separately authorized boundary probe | V30 results |
| LIVE_PILOT_AUTHORITY | **NOT_ISSUED** | §3 and §4 blocked; no exact-scope authority artifact |
| LIVE_PILOT_EXECUTION | NOT_RUN; HTTP requests used = 0; bytes observed = 0 | — |

## 6. Bounded pilot scope (frozen proposal, not authority)

VOO, BND, GLD, BIL · `1Day` · 2016-01-01..2025-12-31 · `adjustment` raw and split
(separate request series) · `limit=1000` · at most 32 requests · at most 8,388,608
observed bytes · 0 retries · no fallback · USD 0 · one explicit `feed` frozen in the
authority and never switched between IEX and SIP · explicit `asof`. Planning
simulation: 22–24 requests and 2.46–4.12 MB, which fits the cap.

Stage order: dry run (this record: **BLOCKED** at §3, §4 and §5) → minimal live only
after every gate passes → offline evaluation → separate full-history authority.

## 7. Signable attestation block (owner only; left blank deliberately)

The owner completes this block in an owner-authored commit or an approving GitHub
PR review that quotes it. The agent must not fill it in.

```text
ACASH V31 FORMAL ATTESTATION
Record: docs/governance/V31_OWNER_DECISION_AND_EVIDENCE_REGISTRY_20261025.md
Parent main: 1d5da43adec4804becd180b42b1c962805a54212
A1 sha256: ab58f1f7a7e05364ee8a70b99209a3d62a32a2a91a29cd4565bebd8ac8d66a65   [ ] RATIFIED [ ] REJECTED
A2 sha256: a285ae8b2b8b124231029899f30d5bbd2ce74bb447deebe815432b7178773869   [ ] RATIFIED [ ] REJECTED
D3 V2 streaming sha256: 8d34c92ec554f32938a8fd9e164112d626d97323013846f11b2ed7646e8a6ec4   [ ] RATIFIED [ ] DEFERRED [ ] REJECTED
Effective date (UTC): ____________________
Owner name: ____________________
Owner signature / signed-commit SHA / PR review URL: ____________________
```

## 8. Unchanged boundaries

REAL_CAPITAL_AUTHORITY = USD 0.00 · NO_REAL_ORDERS = true ·
PAPER_TRADING_AUTHORITY = false · LIVE_TRADING_AUTHORITY = false ·
HYP_003 = TERMINALLY_FALSIFIED · LANE_A = UNISSUED · LANE_B = UNISSUED ·
D6 = NOT_RUN · no DSR/PBO claims.
