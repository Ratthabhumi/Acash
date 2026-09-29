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

## 6. Observation Ordinal Semantics

A governance ambiguity exists regarding ordinal numbering:
1. **Interpretation A (Attempt Ordinal):** Ordinal 1 was dispatched and consumed by the failed attempt; the next dispatch requires ordinal 2 (`AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0002`).
2. **Interpretation B (Committed Observation Ordinal):** Ordinal corresponds to `len(observed_sessions) + 1`; since 0 observations were committed, the first successful observation remains ordinal 1.

```text
OBSERVATION_ORDINAL_RECOVERY = HUMAN_ADJUDICATION_REQUIRED
```

---

## 7. Candidate Operational Schedule (Document Only)

No changes have been or will be made to systemd on the execution host as part of this branch. For future human planning:
- Regular session close: `20:00:00 UTC` (`03:00:00 ICT`).
- Provider eligibility boundary (15-min delay): `20:15:00 UTC` (`03:15:00 ICT`).
- Recommended safe dispatch schedule (`CANDIDATE_OPERATIONAL_SCHEDULE`):
  `20:20:00 UTC` (`03:20:00 ICT`), providing a 5-minute operational safety buffer beyond provider availability.
