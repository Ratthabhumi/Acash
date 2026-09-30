# ACASH Canonical Authority Map

**Date Context**: 2026-09-30  
**Scope**: Single Canonical Authority Identification across ACASH Quantitative Engine

---

## 1. Governance & Lineage Principles (AGENTS.md §§ 1, 4, 13)

Every derived mathematical, cryptographic, or operational parameter must possess exactly **one single canonical point of authority** bound by cryptographic lineage. Dual implementations, heuristic aliases, or loose bindings are strictly forbidden.

---

## 2. Core Authority Table

| Domain / Parameter | Single Canonical Authority | Specification / Source File | Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **Trading Calendar & RTH Schedule** | `NyseCa1Calendar` (CA-1 Sovereign Authority) | `src/acash/data/calendar/nyse_ca1.py` | Strict fail-closed on non-trading days; exact RTH Open (09:30 ET / 13:30 UTC), Close (16:00 ET / 20:00 UTC), and early closes (13:00 ET / 17:00 UTC). |
| **Market Data Provider Access** | Alpaca Delayed Historical SIP Contract | `src/acash/data/qualification/hyp_011_qual_client.py` | Mandates `now_utc > session_close + 15m`. Queries with `end` fresher than 15 minutes trigger 403 `SipContractViolationError`. |
| **Operational Dispatch Schedule** | Candidate Schedule Calculation | `src/acash/research/hyp_011/shadow.py` | `candidate_schedule_time()`: `session_close + 15m (provider delay) + 5m (operational margin)` = 20:20:00 UTC. |
| **Scientific Boundary** | Pre-registered Prospective Epoch | `docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_A.json` | Fixed at `2026-09-25`. Cannot be moved or backfilled. |
| **Failed Session Forensic Record** | Option B Ratified Stage C-A Dossier | `docs/phase14/HYP_011_OBSERVATION_0001_BLOCKED_FORENSIC_20260929.md` | Session `2026-09-28` Attempt 1 classified `MISSED_UNOBSERVED_DUE_TO_PROVIDER_ACCESS_BLOCK`. Re-execution forbidden. |
| **Recovery Integration Anchor** | Dedicated Integration Merge Commit | Git Commit `08530b1ab4ec64788d0eadfaf821aa01e07d0a5f` | Dedicated non-fast-forward merge commit timestamp `2026-09-29T17:12:46+00:00` acts as immutable physical timestamp anchor. |
| **Recovery Binding Manifest** | Stage C-B Sealed Authority | `docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json` | SHA-256 Digest: `eea52f69ccc97ece80c03e87780e110031d54db6ec4087b2a79480b7b45ed46f`. Create-once immutable. |
| **Operational Activation Session** | First NYSE Open Strictly After Integration Anchor | `derive_activation_session()` in `shadow.py` | Session `2026-09-30`. Missed intermediate sessions `['2026-09-25', '2026-09-28', '2026-09-29']` sealed as unobserved. |
| **Observation Artifact Format** | Prospective Observation JSON V1 | `src/acash/research/hyp_011/shadow_ops.py` | Contains 6-field authority lineage, 6 qualified price series (raw/split for ACWI/AGG/SPY), split continuity ratio check, pre/post economic state. |
| **Observation Hash Chain** | SHA-256 Backwards Lineage | `append_observation()` in `shadow_ops.py` | Observation file SHA computed over exact LF UTF-8 bytes. State stores `last_observation_sha256` matching `previous_observation_sha256`. |
| **Capital Authority** | Human Sovereign Authorization | Governance Decision Records (`docs/phase14/`) | Locked at `$0.00`. `paper_trading = false`, `live_trading = false`, `no_real_orders = true`. |
| **Execution Dispatch Attempt** | Sealed Dispatch Counter | Observation Authority Block | Attempt #1 recorded failed. Current authorized attempt is Attempt #2. |

---

## 3. Authority Verification Ledger

```text
CALENDAR_AUTHORITY = NyseCa1Calendar
PROVIDER_DELAY_AUTHORITY = Alpaca SIP 15m Rule
INTEGRATION_ANCHOR_AUTHORITY = 08530b1ab4ec64788d0eadfaf821aa01e07d0a5f
STAGE_C_B_DIGEST_AUTHORITY = eea52f69ccc97ece80c03e87780e110031d54db6ec4087b2a79480b7b45ed46f
ACTIVATION_SESSION_AUTHORITY = 2026-09-30
CAPITAL_AUTHORITY = $0.00 (STRICT FAIL-CLOSED)
```
