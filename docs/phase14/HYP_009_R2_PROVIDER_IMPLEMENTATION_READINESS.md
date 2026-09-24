# Phase 14 HYP_009: R2 Provider Implementation Readiness

```text
[READINESS RECORD: HYP_009 R2 PROVIDER IMPLEMENTATION]
[ARTIFACT_ID: HYP_009_R2_PROVIDER_IMPLEMENTATION_READINESS]
[STARTING_GIT_SHA: 3ba061379b93e4bc7c29c411b0ecd47800867914]
[PARENT_BASELINE_SHA: c700f50ff013da7d863f096f0a948fac8aa062cf]
[HYPOTHESIS_ID: HYP_009]
[CORE_ID: CORE-001]
[SCIENTIFIC_STATUS: UNMODIFIED / INTACT]
[STATE: READY_FOR_LIVE_PROVIDER_QUALIFICATION_NOT_EXECUTED]
[NETWORK_REQUESTS_ISSUED: 0]
[LIVE_PROVIDER_QUALIFICATION_PERFORMED: false]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/HYP_009_R2_PROVIDER_IMPLEMENTATION_READINESS.md`
- **Associated Manifest:** `docs/phase14/manifests/HYP_009_R2_PROVIDER_IMPLEMENTATION_READINESS.json`
- **Governing Standard:** ACASH `AGENTS.md` (Zero Unverified Claims, Strict
  Fail-Closed, Single Canonical Authority).
- **Human Authorization:** `AUTHORIZE_CORE_001_HYP_009_R2_PROVIDER_IMPLEMENTATION_CORRECTION`
  (implementation-readiness correction only; live qualification NOT authorized).

---

## 1. Starting State Classification

Starting commit `3ba0613` is a published additive child of `c700f50`. It is
**not** classified as an invalid HEAD requiring rollback. Correct
classification: **IMPLEMENTATION_READINESS_CORRECTION_REQUIRED**. The starting
commit is preserved as published history; this workflow adds one corrective
commit on top.

---

## 2. Defects Found at 3ba0613 (Verified Against Frozen Contract)

| ID | Defect | Evidence |
| :--- | :--- | :--- |
| A | `HYP009AlpacaClient` accepted RAW only, rejected SPLIT | `hyp_009_daily_client.py` enforced `adjustment == PriceAdjustment.RAW`; frozen contract requires SPLIT (signal prices) + RAW (execution/valuation) |
| B | Incorrectly inherited `FifteenMinuteAccessGuard` semantics | Client held a `FifteenMinuteAccessGuard` and called `validate_requested_end` (15-minute recency) on a daily historical path |
| C | Hard authorized bounds `2016-01-01..2020-12-31` missing | No date-boundary authority existed; out-of-window requests reached the network layer |
| D | `scripts/tiny_sip_probe.py` used the old 1Min path | Script called `AlpacaHistoricalSipClient` with `timeframe="1Min"` instead of the HYP_009 daily contract |
| E | Readiness docs/manifest missing | No `HYP_009_R2_PROVIDER_IMPLEMENTATION_READINESS` artifacts existed |
| F | Test coverage insufficient + collection broken | Only 2 tests existed, and the test file failed at import (`ImportError`: `SipContractViolationError` imported from `models.py`, where it does not exist at runtime) |
| G | Shared `models.py` modified without justification | `3ba0613` added a `TYPE_CHECKING`-only import block that is a runtime no-op and served only the broken test import |

---

## 3. Corrective Implementation (This Workflow)

### 3.1 Final client module/class

- **Module:** `src/acash/data/qualification/hyp_009_daily_client.py`
- **Class:** `HYP009AlpacaClient`
- **Pre-network guard:** `Hyp009PreNetworkGuard` (dedicated date-boundary
  authority; no 15-minute semantics, no 390-minute requirement, no 15:59 rule,
  no early-close exclusion)
- **Result type:** `Hyp009RetrievalResult` (frozen dataclass, `List[DailyBar]`;
  the intraday `SipRetrievalResult` is no longer misused for daily bars)
- **Alignment:** `assert_split_raw_alignment` (module-level; §12)

### 3.2 Frozen request contract (all enforced BEFORE HTTP execution)

| Field | Contract |
| :--- | :--- |
| symbol | `SPY` only |
| timeframe | `1Day` only |
| feed | `SIP` only (`MarketDataFeed.SIP`) |
| adjustments | `SPLIT`, `RAW` only (strict enum membership; raw strings rejected) |
| window | `2016-01-01 <= start_date <= end_date <= 2020-12-31` (UTC-normalized dates) |
| datetimes | timezone-aware required (naive rejected fail-closed) |

Forbidden requests perform **zero** HTTP calls (verified by counting-transport
test: HTTP call count == 0).

### 3.3 Response validation (fail closed, no silent trimming)

Row before start / row after end / duplicate session / weekend row /
full-holiday row / null-missing fields / malformed timestamp / malformed
numerics / non-finite values / non-positive OHLC / invalid OHLC geometry /
negative volume are all rejected with `SipContractViolationError` (a
`DataContractError`; pydantic/domain model errors are normalized into it with
chaining). Legitimate early-close sessions are accepted per CA-1 authority.

### 3.4 DailyBar model (§9)

`src/acash/data/qualification/daily_models.py` `DailyBar` preserved as valid:
frozen, timezone-aware UTC, strictly positive finite OHLC, non-negative finite
volume, OHLC geometry. Additive correction: `Decimal128(38, 18)` bounds parity
with `HistoricalSipBar` (`validate_decimal128_bounds` on all numeric fields).

### 3.5 Calendar contract (§10)

Canonical authority: `NyseCa1Calendar` (`src/acash/data/calendar/nyse_ca1.py`).
Regular session = valid; legitimate early-close session = valid; weekend =
invalid; full holiday = invalid.

**Actual early-close test date (not invented): `2016-11-25`** — pinned CA-1
`13:00 ET` early close (day after Thanksgiving 2016). Companion fixtures from
the same authority: full holiday `2016-11-24` (Thanksgiving), weekend
`2016-11-05` (Saturday).

`EARLY_CLOSE_POLICY_UNIT_TESTED = true`;
`EARLY_CLOSE_POLICY_LIVE_PROBE_VERIFIED = false`.

### 3.6 Runner (§11)

- **Removed:** `scripts/tiny_sip_probe.py` (invalid 1Min path).
- **Added:** `scripts/execute_hyp_009_r2_provider_qualification.py` — uses
  `HYP009AlpacaClient`; frozen probe `2016-11-01..2016-11-04` SPY 1Day SIP;
  Request A SPLIT, Request B RAW; credential presence -> split request ->
  raw request -> scope validation -> OHLCV validation -> date-set alignment ->
  concise verdict. Default is dry-run/blocked (`--execute-network` required
  for any live call; credentials required fail-closed). **Not executed in this
  workflow.**

### 3.7 Shared models.py (§13)

The `3ba0613` `TYPE_CHECKING`-only import block was **reverted** through the
corrective commit: it was unnecessary in the final architecture (no runtime
use; `client.py` imports from `models.py`, never the reverse, so no import
cycle exists) and it served only the broken test import, which now points at
`acash.data.qualification.client` where the names actually live. HYP_003
scientific semantics untouched; all legacy qualification tests remain green.

---

## 4. Test Coverage (§14)

Expanded `tests/unit/data/qualification/test_hyp_009_daily_alpaca_client.py`
(renamed from `test_hyp_009_daily_client.py`; content preserved and extended):

1. SPY accepted · 2. non-SPY rejected pre-network · 3. 1Day accepted ·
4. non-1Day rejected pre-network · 5. SIP accepted · 6. non-SIP rejected
pre-network · 7. SPLIT accepted · 8. RAW accepted · 9. unsupported adjustment
rejected pre-network · 10. 2016-01-01 lower boundary accepted ·
11. 2020-12-31 upper boundary accepted · 12. pre-2016 rejected pre-network ·
13. 2021-01-01 rejected pre-network · 14. 2024 rejected pre-network ·
15. 2025 rejected pre-network · 16. 2026-08-15 rejected pre-network ·
17. start > end rejected pre-network · 18. forbidden request proves HTTP call
count == 0 · 19. spill-before-start rejected · 20. spill-after-end rejected ·
21. duplicate session rejected · 22. zero price rejected ·
23. negative price rejected · 24. invalid high/low geometry rejected ·
25. negative volume rejected · 26. null/malformed input rejected ·
27. weekend row rejected · 28. holiday row rejected ·
29. legitimate early-close session accepted (2016-11-25, CA-1 pinned) ·
30. split/raw date mismatch rejected · 31. aligned split/raw result accepted ·
32. existing `AlpacaHistoricalSipClient` retains 1Min/RAW behavior.

Plus: naive-datetime fail-closed test, guard boundary unit test, and a
hermetic runner dry-run test (default `--execute-network=False`, exit blocked,
zero network). No real network in tests (mocked transport only).

---

## 5. State & Boundary Invariants

```text
M2_ACCESS_COUNT = 0
M3_ACCESS_COUNT = 0
QUARANTINE_ACCESS_COUNT = 0
PROSPECTIVE_ACCESS_COUNT = 0
HYP_007_EMPIRICAL_READ_COUNT = 0
HYP_003_SCIENTIFIC_FILES_MODIFIED = NO
HYP_003_RUNNER_EXECUTED = NO
NETWORK_REQUESTS_ISSUED = 0
LIVE_PROVIDER_QUALIFICATION_PERFORMED = false
PAPER_AUTHORIZED = false
LIVE_AUTHORIZED = false
CAPITAL_AUTHORITY_USD = 0.00
NO_REAL_ORDERS = true
```

Live provider qualification requires separate authorization:
`AUTHORIZE_CORE_001_HYP_009_R2_LIVE_PROVIDER_QUALIFICATION`.

---

## 6. Manifest Digests (Verification)

| Artifact | Digest |
| :--- | :--- |
| Manifest canonical payload (`canonical_payload_sha256`, repo convention) | `7c0e654814119e6047202b3438da8ce6227359710eee731d31f48d574693ccd6` |
| Manifest file `docs/phase14/manifests/HYP_009_R2_PROVIDER_IMPLEMENTATION_READINESS.json` | `fcd07fa869cba6a5ad6294059c7f59e657955be52bbd940f045a8b269d1cb2c2` |

Recompute with `CanonicalConfigSerializer.compute_sha256` over the manifest
payload (excluding the hash field) and `sha256sum` over the file bytes.

---

## 7. Full-Suite Baseline Note (Honesty Record)

At both the starting commit `3ba0613` (verified with all corrective changes
stashed) and with the corrective change applied, the repository-wide suite
shows the **identical** pre-existing baseline: 56 failures confined to
`tests/unit/research/` (pinned research-artifact hash preconditions) plus
2 collection errors in `tests/unit/execution/mt5/` (undeclared optional
`MetaTrader5` package absent from the lockfile-faithful environment). The
corrective change introduces **zero** new failures: all
`tests/unit/data/qualification/` tests pass (35 new HYP_009 + 26 legacy),
`mypy src/ tests/` is clean (504 files), and `git diff --check` is clean.
These pre-existing items are out of scope for this correction (HYP_003
scientific artifacts must not be altered here) and are recorded, not hidden.
