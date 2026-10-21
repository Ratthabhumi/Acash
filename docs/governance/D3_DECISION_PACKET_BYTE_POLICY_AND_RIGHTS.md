# D3 Admission Decision Packet: Byte Policy, Provider Entitlement & Trust Root

**Classification:** GOVERNANCE_PROPOSAL (Pre-Ratification / Awaiting Human Decision)  
**Parent Canonical Main:** `9bc861dbbe2b3109e910cf5cce060dcac034718c`  
**Date Context:** 2026-10-22  
**Governing Documents:** [`AGENTS.md`](../../AGENTS.md), [`ROADMAP.md`](../ROADMAP.md), [`docs/research/LANE_A_UNISSUED_AUTHORITY_PACKET_20261013.md`](../research/LANE_A_UNISSUED_AUTHORITY_PACKET_20261013.md)  
**Hard Boundaries:** `REAL_CAPITAL_AUTHORITY = USD 0.00` · `NO_REAL_ORDERS = true` · `LANE_A = UNISSUED` · `LANE_B = UNISSUED`

---

## 1. Purpose & Decision Scope

This packet consolidates the three external gating prerequisites required before any real-data acquisition authority (D3) can be issued by the repository owner:
1. **Contract Ratification:** Versioned byte policy `IDENTITY_ONLY_RAW_RESPONSE_BODY_V1`.
2. **Account Entitlement Verification:** Alpaca rights, feed authorization, and raw caching permission.
3. **Host Durability & Trust Root:** Key custody, runtime attestation, and fail-closed persistence guarantees.

> [!WARNING]
> **Non-Ratification Notice:** Committing this document to the repository does **NOT** constitute ratification.
> It remains in status **`PROPOSED`** until the human operator signs the explicit authorization section below.
> Merging offline MockTransport proofs (PR #41) does **NOT** authorize production dispatch.

---

## 2. Decision 1 — Byte Contract: `IDENTITY_ONLY_RAW_RESPONSE_BODY_V1`

### 2.1 Specification Rules
| Component | Specification Rule | Fail-Closed Enforcement |
| :--- | :--- | :--- |
| **Request Header** | `Accept-Encoding: identity` | Enforced in request planner; no compression requested |
| **Encoding Guard** | Reject compressed or non-identity encodings | Raises `DataContractError` if `Content-Encoding` != `identity` |
| **Byte Accounting** | Count raw HTTP response-body bytes | Incremental chunk-by-chunk iteration before any decoding |
| **Cumulative Budget** | Max 524,288 raw bytes (512 KiB) per session | Immediate cap halt on overflow across all pagination calls |
| **Digest Lineage** | Retain bytes matching manifest SHA-256 | Recomputed incremental SHA-256 must match receipt record |
| **Zero Retry Policy** | 0 retries, 0 fallbacks, 0 attempt refunds | Failed or interrupted connections poison cap permanently |
| **Malformed Header** | Malformed / non-numeric `Content-Length` | Treated as absent; relies strictly on chunk byte counter |
| **Negative Header** | `Content-Length < 0` | Raises `DataContractError` immediately |
| **Header Disagreement** | Actual bytes streamed != declared length | Raises `DataContractError` upon stream completion |

### 2.2 Material Caveats & Runtime Disclosures
* **Post-Read Chunk Detection:** The streaming cap inspects chunks as they are yielded by the transport iterator. If an upstream network chunk of 100,000 bytes arrives when only 64 bytes remain in the budget, the counter observes the 100,000 bytes and immediately halts execution.
* **Memory Bound Disclosure:** This mechanism provides **post-read detection**, NOT a hardware or socket-level memory cap.
* **MockTransport vs. Real Transport:** Offline tests verify Python iterator accounting; they do **NOT** prove provider behavior under real socket stalls, TCP packet fragmentation, or TLS record boundaries.

---

## 3. Decision 2 — Alpaca Account Rights & Data Entitlement

### 3.1 Public Facts vs. Account Unknowns
* **Public Documentation:** Alpaca Basic lists free daily bars from 2016 with a 15-minute delay guard.
* **ACASH Account Reality:** The specific registered account tier, actual token permissions, historical window accessibility, and raw data retention rights remain **`ACCOUNT_ENTITLEMENT_UNKNOWN`**.

### 3.2 Operator Inquiry (Ready for Dispatch)
Please dispatch the following inquiry to the Alpaca account manager / institutional support:

```text
To: Alpaca Support / Account Representative
Subject: ACASH Research Project — Account Entitlement & Historical Data Caching Rights

Dear Alpaca Team,

Regarding our registered Alpaca account (Account ID: [INSERT ACCOUNT ID]):
1. Account Plan: Is our account enrolled in the Basic (free) tier or an active Market Data subscription?
2. Historical Feed Entitlement: Does our API token possess CTA/CQ and UTP Consolidated Tape (SIP) authorization for historical equity bars (2025–2026), or is it strictly limited to the IEX feed?
3. Local Research Storage: Does Alpaca's API Terms of Service permit permanent local offline storage (SHA-256 sealed SQLite/Parquet evidence archives) of raw HTTP historical bar payloads strictly for internal quantitative model validation (zero redistribution)?
4. Corporate Action Vintage: Does Alpaca provide immutable point-in-time dividend and split adjustment factors, or does 'adjustment=all' dynamically restate historical series?

Thank you,
ACASH Release & Operations Operator
```

---

## 4. Decision 3 — Trust Root & Host Durability Prerequisites

Prior to issuing production acquisition authority, the following technical controls must be verified:
1. **Production Signing Key Custody:** Ed25519 offline authority keys must not reside in plain text on development environments or repository checkouts. A distinct key custodian protocol is required.
2. **Key Rotation & Revocation:** An explicit key-revocation registry must exist before live keys are authorized.
3. **Parent-Directory Fsync & Host Durability:** Synthetic unit tests verify file writes, but do not prove host crash durability. Operating system-level `fsync()` on parent directories and journal write-ahead logs must be evidenced on the execution host.
4. **Homelab Isolation:** Deployment to Homelab or remote servers remains strictly prohibited under this sprint.

---

## 5. Human Decision Form (To Be Ratified by Owner)

```markdown
### OPERATOR RATIFICATION DECISION (Mark one)

[ ] RATIFIED: I explicitly approve IDENTITY_ONLY_RAW_RESPONSE_BODY_V1 as the canonical
    byte contract for the D3 canary feasibility window (VOO/BND/GLD/BIL).
    (Note: Acquisition authority remains unissued until Alpaca rights are confirmed).

[ ] REJECTED: Reject proposal and return with revision guidance.

[ ] DEFERRED: Await Alpaca written confirmation before ratifying byte contract.

Operator Signature: _______________________
Date (UTC):         _______________________
```
