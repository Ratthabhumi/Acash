# HYP_011 Prospective Shadow — Observation #0001 Blocked Forensic Record

```text
[RECORD_TYPE: FORENSIC_FAILURE_PRESERVATION_AND_RECOVERY_DESIGN]
[CANONICAL_MAIN_HEAD: d9608c0a2353bd5ed41943e5fb893ef9648089d2]
[TARGET_SESSION: 2026-09-28]
[SCIENTIFIC_PROSPECTIVE_BOUNDARY: 2026-09-25 (UNCHANGED)]
[PROSPECTIVE_STATE_MUTATION: FALSE]
[OBSERVED_SESSIONS: 0]
[S1_PROGRESS: 0/20]
[RETRY_2026_09_28: FORBIDDEN]
[BACKFILL_2026_09_28: FORBIDDEN]
[MANUAL_REEXECUTION: FORBIDDEN]
[AUTHORIZATION_ORDINAL_1: CONSUMED_EXIT_1_BLOCKED]
[REAL_CAPITAL_AUTHORITY: $0.00]
[PAPER_TRADING_AUTHORITY: FALSE]
[LIVE_TRADING_AUTHORITY: FALSE]
[NO_REAL_ORDERS: TRUE]
```

---

## 1. Forensic Evidence & Event Timeline

On 2026-09-29 (Asia/Bangkok, UTC+07:00), the automated systemd timer dispatched the prospective runner for target session `2026-09-28`:

- **Automatic Timer Dispatch:** `2026-09-29T03:10:00+07:00` (`2026-09-28T20:10:00Z`).
- **Service Process Start:** `2026-09-29T03:10:00+07:00`.
- **Pretest Execution:** Zero-network dry-run pretest passed (`NETWORK_REQUESTS = 0`).
- **Authorization Verification:** Token `AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001` with `--ordinal 1` was evaluated and marked `ACCEPTED`.
- **Service Process Exit:** `2026-09-29T03:10:11+07:00` (elapsed time: 11 seconds).
- **Service Exit Status:** `status=1/FAILURE` (`EXIT_FAILURE`).
- **Systemd Restart Metric:** `NRestarts=0` (fail-closed, no blind restart loop).
- **Error Encountered:** `DataContractError: Alpaca access forbidden (HTTP 403). SIP denied.`
- **Directory Existence Check:**
  - `data/hyp_011/prospective/` did not exist.
  - `data/hyp_011/prospective/observations/2026-09-28.json` was NOT created.
  - `data/hyp_011/prospective/state.json` was NOT created.
- **Git Working Tree:** Remained completely clean on canonical main (`d9608c0a2353bd5ed41943e5fb893ef9648089d2`).
- **Order Execution Exposure:** Exactly 0 real/broker orders placed; simulated accounting only.

### Classification

```text
HYP_011_OBSERVATION_0001 = BLOCKED_PROVIDER_ACCESS_BEFORE_OBSERVATION_COMMIT
OBSERVED_SESSIONS = 0
S1_PROGRESS = 0/20
```

This event is **NOT** a scientific hypothesis falsification or rejection. It is an **operational provider-access failure occurring prior to observation commit**. Because no prospective state mutation occurred, the prospective sample count remains strictly 0.

---

## 2. Root Cause Audit & Provider Primary-Source Contract

### A. Canonical Code Query Window Defect

Inspection of `fetch_single_session` in `src/acash/data/qualification/hyp_011_qual_client.py` revealed:

```python
start_utc = _datetime(session.year, session.month, session.day, tzinfo=timezone.utc)
end_utc = _datetime(
    session.year, session.month, session.day, 23, 59, 59, 999999,
    tzinfo=timezone.utc,
)
```

For target session `2026-09-28`, the runner executed at `20:10:00Z`. The query sent to Alpaca's `/v2/stocks/{symbol}/bars` endpoint requested an `end` parameter of `2026-09-28T23:59:59.999999Z`. This requested an interval extending nearly 4 hours into the future relative to the request time.

### B. Provider Primary-Source Rule (Alpaca Market Data API)

- **Primary Source:** Alpaca US Market Data Documentation (`https://docs.alpaca.markets/reference/stockbars`, retrieved 2026-09-29).
- **Endpoint:** `GET /v2/stocks/{symbol}/bars`.
- **Feed Semantics:**
  - `feed=sip`: Full consolidated tape across all US exchanges.
  - Real-time SIP queries require an active paid subscription (e.g., Algo Trader Plus).
  - Accounts without real-time SIP access are restricted from querying data within the most recent 15 minutes.
  - If a request specifies an `end` timestamp within the 15-minute window or in the future, the endpoint rejects the call with **HTTP 403 Forbidden** (`"subscription does not permit querying recent SIP data"`).
- **Execution Timing Mismatch:**
  - Canonical NYSE regular trading session for `2026-09-28` closed at `20:00:00Z` (16:00:00 America/New_York).
  - The dispatch occurred at `20:10:00Z`, exactly 10 minutes post-close.
  - Even if `end` had been set to `20:00:00Z`, the execution occurred 5 minutes earlier than the 15-minute delayed SIP availability boundary (`20:15:00Z`).

### C. Root Cause Classification & Remaining Uncertainty

- **PRIMARY_CONFIRMED_DEFECT:** `PROVIDER_ACCESS_WINDOW_CONTRACT_MISMATCH`
  1. The code requested an `end` timestamp in the future (`23:59:59.999999Z` instead of canonical market close).
  2. The dispatch at `20:10:00Z` was executed prior to the required 15-minute post-close delayed SIP threshold.
- **ADDITIONAL_ACCOUNT_ENTITLEMENT_ISSUE:** `NOT_EXCLUDED`
  Because no live network probes are permitted on this branch, we do not claim that the provider subscription is fully verified until an authorized credential probe is separately ratified.

---

## 3. Technical Correction

On this isolated branch (`fix/hyp011-prospective-sip-window-recovery-20260929`), the defect is corrected at two distinct architectural levels:

### 1. Request Boundary Bound to Canonical Market Session Close
In `HYP011AlpacaClient.fetch_single_session`:
- `end_utc` is bound directly to `calendar.get_session(session).close_utc` (e.g. `20:00:00Z` for regular sessions, `18:00:00Z` for early closes).
- Under no circumstances is `23:59:59Z` used.
- Query parameters remain locked to: `feed=sip`, `timeframe=1Day`, `adjustment in {split, raw}`, `symbols in {ACWI, AGG, SPY}`.
- Zero fallback to IEX; zero provider splicing; zero synthetic substitution.

### 2. Separation of Market Session Completion from Provider Data Accessibility
In `src/acash/research/hyp_011/shadow.py`:
- `market_session_completed_after(session, calendar)` defines the completion instant (`close_utc`).
- `provider_observation_eligible_after(session, calendar, provider_delay, safety_margin)` defines the delayed SIP data accessibility threshold:
  $$\text{provider\_eligible\_after\_utc} = \text{session\_close\_utc} + \text{provider\_delay (15m)} + \text{safety\_margin (0m)}$$
- `fetch_single_session` and the runner enforce this boundary fail-closed: if invoked when $\text{now\_utc} \le \text{provider\_eligible\_after\_utc}$, the process fails closed immediately with zero network calls issued.

---

## 4. Prohibition of Retry / Backfill for 2026-09-28

Because session `2026-09-28` is now complete and unobserved, any retrospective API query to fetch `2026-09-28` would violate the prospective protocol and constitute a prohibited backfill.

- `2026-09-28` must remain permanently: `UNOBSERVED`.
- `2026-09-28` counts exactly `0` toward the 504 prospective sessions and the 2 annual rebalances.
- Proposed recovery classification:
  `MISSED_UNOBSERVED_DUE_TO_PROVIDER_ACCESS_BLOCK`
- Zero retrospective prices will ever be inserted for this session.

---

## 5. Operational Recovery Governance (Decision Surface)

Under canonical code, if `observed_sessions` is empty, `_expected_next()` returns `ACTIVATION_SESSION = 2026-09-28`. To prevent an unauthorized attempt to re-process `2026-09-28`, a formal recovery policy must be adjudicated by human governance.

### Option A: Explicit Immutable Missed-Session State
- **Mechanism:** Add an immutable `missed_sessions` collection in persistent state (`state.json`), recording `2026-09-28` as `MISSED_UNOBSERVED_DUE_TO_PROVIDER_ACCESS_BLOCK`.
- **Session Derivation:** `_expected_next()` derives the next eligible session by advancing past both `observed_sessions` and `missed_sessions`.
- **Scientific Impact:** Prospective boundary `2026-09-25` is strictly preserved.
- **Operational Impact:** Activation session remains recorded as `2026-09-28`, with `2026-09-28` explicitly marked as an operational gap.
- **Sample Count:** 0 observed sessions; minimum requirement remains 504.

### Option B: Additive Operational Re-Activation Amendment
- **Mechanism:** Enact a formal Stage-C operational activation amendment updating `ACTIVATION_SESSION` to a future NYSE session (e.g. `2026-09-29` or later, derived from the ratification commit timestamp via `derive_activation_session`).
- **Session Derivation:** `_expected_next()` selects the new activation session. `2026-09-28` falls into `[SCIENTIFIC_BOUNDARY, NEW_ACTIVATION)` and is derived by `missed_unobserved_sessions()`.
- **Scientific Impact:** Prospective boundary `2026-09-25` is strictly preserved.
- **Operational Impact:** Clean re-activation without mutating state schema.
- **Sample Count:** 0 observed sessions; minimum requirement remains 504.

```text
RECOVERY_POLICY = HUMAN_ADJUDICATION_REQUIRED
```

---

## 6. Observation Ordinal Semantics & Human Adjudication

Human governance adjudication for recovery ratified:
```text
RECOVERY_POLICY = OPTION_B_ADDITIVE_OPERATIONAL_REACTIVATION
OBSERVATION_ORDINAL_SEMANTICS = COMMITTED_OBSERVATION_ORDINAL
```

Therefore:
- `OBSERVATION_ORDINAL = 1` (reflects committed count of 0 observations + 1; `S1_PROGRESS = 0/20`).
- Operational attempt history is tracked separately:
  - `FAILED_DISPATCH_ATTEMPT = 1` (Session 2026-09-28)
  - `NEXT_DISPATCH_ATTEMPT = 2`
- Post-recovery authorization tokens explicitly bind both dimensions:
  `AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002`
- Classification:
  `FAILED_DISPATCH_2026_09_28 = BLOCKED_PROVIDER_ACCESS_BEFORE_OBSERVATION_COMMIT`
  `OBSERVATION_COMMIT_COUNT = 0`

---

## 7. Candidate Operational Schedule & Derivation

No changes have been or will be made to systemd on the execution host as part of this branch.
Operational scheduling must **never** be treated as a universal fixed UTC timer (such as `20:20:00 UTC`), because US Daylight Saving Time changes the NYSE UTC close time (20:00 UTC under DST vs 21:00 UTC under standard time) and early close sessions conclude earlier.

Canonical schedule derivation formula:
```text
CANDIDATE_SCHEDULE_DERIVATION = CALENDAR_CLOSE_PLUS_PROVIDER_DELAY_PLUS_MARGIN
schedule_utc = calendar.get_session(session).close_utc + provider_delay + operational_margin
```

Where:
- `provider_delay`: 15 minutes (`ALPACA_SIP_DELAY`).
- `operational_margin`: 5 minutes recommended buffer.
- `20:20:00 UTC`: Illustrative instance only for regular September 2026 DST sessions (close 20:00 UTC + 15m delay + 5m buffer).

---

## 8. Historical Timing Authority Supersession

Existing historical governance and manifest documents state that observation eligibility begins strictly after market close. Those historical records remain immutable evidentiary artifacts.
This recovery pass formally records an additive supersession:
- **Historical Timing Rule:** `MARKET_CLOSE_ONLY`
- **Superseded Operational Rule:** `MARKET_CLOSE + PROVIDER_ACCESS_DELAY + FAIL_CLOSED_BOUNDARY`

Runtime execution uses the superseded rule strictly via Stage C recovery binding.

---

## 9. Forensic Audit Correction: No-Backfill Proof at Commit c6f65cf

The initial verification test `test_5_no_retry_backfill_of_missed_prospective_session()` at commit `c6f65cfd` proved only that an attempt to record `2026-09-25` (a date prior to original activation `2026-09-28`) was rejected. It did **not** prove that the failed activation session `2026-09-28` could not be retried, because `_expected_next()` still fell back to hard-coded `ACTIVATION_SESSION = date(2026, 9, 28)` when `observed_sessions` was empty.

Classification:
```text
NO_BACKFILL_TEST_AT_c6f65cf = INSUFFICIENT_FOR_FAILED_ACTIVATION_SESSION
```

**Corrective Hardening (Stage C-A):**
1. The hardcoded fallback in the runner was eliminated.
2. Operational activation is now strictly resolved via `resolve_operational_activation()`.
3. In the post-failure operational state (`now_utc >= 2026-09-28 close_utc` and 0 committed observations), the runner strictly requires a ratified Stage C-B recovery binding (`STAGE_C_RECOVERY_BINDING_PATH`).
4. If no Stage C-B binding exists, the runner fails closed immediately with `SHADOW_RECOVERY_BINDING_REQUIRED` with **zero network calls**, deterministically preventing retry of `2026-09-28`.
5. Once a Stage C-B binding is ratified, the new operational activation date is derived from the canonical main commit timestamp, and all prior sessions in `[2026-09-25, new_activation)` (including `2026-09-28`) are permanently unobserved (`MISSED_UNOBSERVED_DUE_TO_PROVIDER_ACCESS_BLOCK`).
