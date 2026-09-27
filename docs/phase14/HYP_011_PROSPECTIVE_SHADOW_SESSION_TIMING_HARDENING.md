# HYP_011 Prospective Shadow — Session-Timing Hardening

Authorization: `AUTHORIZE_HYP_011_PRE_OBSERVATION_SESSION_TIMING_HARDENING`
Base: `a1fb06323a9722c82a491fa938cc70060f0624d9`
Zero network. Zero prospective data. No observation. Observed count remains 0.

## Finding (operator-facing time bomb, execute path unaffected)

`EXPECTED_SESSION_OPEN_US = time(13, 30)` was presented as the observation
trigger. Wrong in two dimensions:

1. A daily-bar observation requires the session to be COMPLETE — the trigger
   is the close, never the open.
2. 13:30 UTC is not the NYSE open year-round: DST changes the UTC offset
   (winter regular open is 14:30 UTC; verified via `NyseCa1Calendar`).

The production execute path was never contaminated: it gates on
`calendar.get_session(target).close_utc` with strict `now > close_utc`
(`ShadowState.record_session`, `now <= close_utc` raises). Only the
operator-facing trigger message could have caused a mistimed run.

## Fix

- `EXPECTED_SESSION_OPEN_US` removed from
  `src/acash/research/hyp_011/shadow.py` (no remaining references anywhere).
- New canonical helper `observation_eligible_after(session, calendar)`:
  returns the calendar-derived `close_utc`; production eligibility remains
  strictly `now_utc > close_utc` — at exactly `close_utc`, NOT YET
  PROCESSABLE.
- The zero-network dry-run now derives the exact expected session from
  `NyseCa1Calendar` and prints calendar-derived values (never hard-coded):

  ```text
  EXPECTED_SESSION = 2026-09-28
  SESSION_OPEN_UTC = 2026-09-28T13:30:00+00:00
  SESSION_CLOSE_UTC = 2026-09-28T20:00:00+00:00
  OBSERVATION_ELIGIBLE = false
  NETWORK_REQUESTS = 0
  ```

  After close it may print `OBSERVATION_ELIGIBLE = true`, but network stays 0
  (dry-run never executes network) and nothing is written.

## Canonical semantics (must not be conflated)

- `open_utc` = portfolio execution timestamp semantics (calendar-derived).
- `close_utc` = observation availability / network-processing eligibility.
- Bound activation session 2026-09-28: open `2026-09-28T13:30:00Z`,
  close `2026-09-28T20:00:00Z`.
- Observation #0001: ONLY after canonical NYSE close =
  strictly after `2026-09-28T20:00:00Z`
  (≈ after 03:00 ICT on 2026-09-29). Never 13:30 UTC.

## Verification

- Targeted: 37 passed (`prospective_shadow`, `shadow_ops`, `shadow_ca`).
- New tests: hard-coded trigger absent; Sep-28 open+close calendar-derived;
  winter open 14:30Z (DST-safe); early-close actual close (pre-existing);
  1s-before and exactly-at-close rejected; 1µs-after eligible; dry-run
  before/after close prints correct eligibility with zero network and zero
  writes; activation still 2026-09-28.
- `uv run mypy src/ tests/`: clean.
- `git diff --check`: clean.
- Full `uv run pytest`: 3232+ passed (see commit report).
- Scientific/activation contracts unchanged; no market or sponsor requests.
