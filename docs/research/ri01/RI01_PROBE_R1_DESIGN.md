# RI-01 Provider Probe R1 — Design (HARNESS BUILT, PRE-LIVE CORRECTIONS V1.1)

**Status**: `PRE_LIVE_CORRECTION_REQUIRED`. The harness in
`src/acash/research/ri01/probe.py` (28 hermetic mock-transport tests) has
NEVER touched a live endpoint (`NETWORK_REQUESTS_PERFORMED = 0`) and MUST NOT run before ALL of:

1. Verification and merge of PR #10 (`fix/evidence-plane-v11-prelive-correctness-20261007`),
2. HYP_011 Observation #1 forensic check completed on Homelab,
3. A separate, single, explicit operator network authority candidate ratified,
4. Execution from an ISOLATED worktree — never `/home/mew/Acash` while
   HYP_011 V2 is armed.

---

## 1. Frozen Scope

- **Symbol**: SPY only (hardcoded; anything else is rejected pre-network).
- **Sessions** (allowlisted, already-consumed or pre-holdout ONLY):
  - `2018-06-01` — early-depth regular session (390 min)
  - `2021-06-01` — normal later in-sample regular session (390 min)
  - `2021-11-26` — historical half-day (210 min)
- **Hard Holdout Guard**: Any session ≥ `2023-01-01` is strictly rejected BEFORE any
  network, even with an otherwise valid authority.
- **Capabilities**:
  - `bars`: 1Min SIP raw, paginated to exhaustion, exact RTH grid `[session_open, session_close)`.
  - `trades`: narrow ±5-min windows around open/close, exchange + conditions preserved.

---

## 2. Separation of Generic Retrieval vs Consumer Qualification

In Evidence Plane V1.1, generic retrieval and consumer qualification are decoupled:

1. **Retrieval Evidence Plane (`manifest.json`)**:
   - Status represents retrieval outcome only: `RETRIEVED`, `PARTIAL`, `ENTITLEMENT_DENIED`, `HTTP_FAILED`, `MALFORMED_RESPONSE`.
   - `RETRIEVED` indicates only that all network pages were acquired from the provider; it **NEVER** means qualified or covered.
   - Terminal retrieval evidence is immutably recorded even on network/provider failures.
2. **RI-01 Consumer Qualification (`qualification.json`)**:
   - Status represents market-data qualification: `QUALIFIED`, `DATA_UNAVAILABLE`, `CONTRACT_FAILED`.
   - Evaluated **AFTER** raw retrieval evidence is sealed.
   - Only exact `[session_open, session_close)` calendar-derived RTH grid receives `status = "QUALIFIED"`.
   - Any incomplete session (e.g. 389 bars instead of 390) writes `status = "CONTRACT_FAILED"`, preserving raw evidence while failing closed without ever marking the session as `QUALIFIED` or `COVERED`.

---

## 3. Ordered Page-Chain Provenance & Authority Binding

- **Page-Chain Provenance**:
  - `ordered_page_chain_digest()` binds the canonical tuple:
    `(page_index, request_token, next_page_token, raw_bytes_sha256, item_count)`.
  - Serialized via `acash.core.serialization.CanonicalConfigSerializer`.
  - Sensitive to page order, raw byte hashes, request tokens, next tokens, and item counts.
- **Authority Binding**:
  - `RI01ProbeAuthority` is classified honestly as a **hash-bound operator authorization artifact** (NOT a cryptographically signed PKI credential).
  - Deterministic `authority_sha256` is computed over canonical authority JSON and immutably bound into `RetrievalRunManifest` and `RI01QualificationRecord`.
  - Strict type validation: rejects string booleans (`"false"`, `"true"`), integer booleans (`0`, `1`), string ints, unknown fields, and naive timestamps fail-closed.
- **Rate-Limit Capture**:
  - Only response header names beginning case-insensitively with `x-ratelimit-` are recorded.

---

## 4. Staged Canary Empirical Sequence (Proposed Post-PR #10)

Upon separate explicit human authorization, empirical probe execution must follow a strict staged canary sequence:

1. **CANARY 1**: SPY `2021-06-01` 1Min bars (raw SIP), max request budget tightly bounded.
   - Verify retrieval status `RETRIEVED` and qualification status `QUALIFIED` (390 bars).
   - If Canary 1 passes:
2. **CANARY 2**: SPY `2018-06-01` bars (historical depth check, 390 bars).
3. **CANARY 3**: SPY `2021-11-26` half-day bars (210 bars).
4. **CANARY 4**: Narrow historical trades windows around open/close (`±5m`).
   - Page size limit up to 10,000 where appropriate to minimize request count while preserving pagination.

**Zero Outcome Invariant**: No returns, no PnL, no Sharpe, no hit-rate, no predictive indicators. Missing data is `DATA_UNAVAILABLE`, never imputed. Sealed holdout (`>= 2023-01-01`) is never touched.
