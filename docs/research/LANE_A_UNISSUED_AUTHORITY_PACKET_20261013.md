# ETF Lane A — Unissued Authority Packet (OFFLINE PROPOSAL — NOT ISSUED)

**Packet ID:** `LANE-A-ETF-DAILY-20261013-PROPOSAL`
**Status:** `PENDING_OPERATOR_AUTHORIZATION` — no HTTP executed, no authority issued.
**Purpose:** Bounded smoke qualification: is Alpaca 1Day historical bars usable
for further VOO/BND/GLD/BIL daily benchmark qualification (DS-01)? Five
sessions cannot prove historical coverage, PIT availability, or total-return
qualification.

## Candidate scope

- Provider: Alpaca Market Data (`GET /v2/stocks/bars?timeframe=1Day`)
- Symbols: VOO, BND, GLD, BIL (4 symbols; VOO inception 2010-09-07 — window is post-inception)
- Window: 2026-09-28 through 2026-10-02 (5 sessions; start/end inclusive per
  Alpaca docs; consumer treats end as inclusive date bound)
- Adjustments requested: `raw` and `all` (2 variants; `all` is a retroactive
  snapshot, NOT PIT-guaranteed — compare raw vs all for corporate-action drift)
- Feed: operator-bound at issuance to exactly one of `iex`|`sip` (`iex` vs `sip`
  semantics differ; entitlement uncertainty recorded, not assumed). No
  server-side default is trusted and no fallback feed is permitted; `otc`/`boats`
  are excluded from Lane A scope
- Max HTTP requests: 12 (canonical multi-symbol shape: 2 base requests
  [all 4 symbols × 2 adjustments] + 10 pagination spare; stop at budget even if
  pages remain → PARTIAL)
- Max response payload: 524288 bytes total (accounted across successes AND
  failures/pagination; abort on exceed)
- Paid budget: USD 0 (Basic free only; no $99 upgrade; 2016+ coverage only —
  does NOT prove 2010–2015)
- Real capital authority: USD 0

## Request semantics (exact)

- Base: `https://data.alpaca.markets/v2/stocks/bars?symbols=VOO,BND,GLD,BIL&timeframe=1Day&start=2026-09-28&end=2026-10-02&adjustment={raw,all}&feed={iex|sip, operator-chosen}&sort=asc&limit=1000&currency=USD`
  (verified 2026-10-13 against official `stockbars` reference: endpoint
  `/v2/stocks/bars`, `start`/`end` INCLUSIVE accepting YYYY-MM-DD, `page_token`
  pagination, `sort=asc|desc`, `feed=sip|iex|otc|boats` with a server-side
  default of sip (hence bound explicitly, never trusted), currency default USD
  (bound explicitly here); 4xx/429 taxonomy per reference. The exact first-page
  binding is canonicalized in `canonical_query_parameters()` in
  `src/acash/data/qualification/lane_a_authority.py`)
- Timezone: UTC bounds; NYSE session mapping validated per-bar (no weekend/holiday bars accepted)
- Pagination: follow `next_page_token` until absent/empty; each page = 1 request
  against budget; incomplete at budget → PARTIAL, no auto-retry/extension
- Accounting: every page fetch (base or continuation) is pre-reserved via the
  dispatch-reserve ledger (`begin_dispatch` consumes budget BEFORE send;
  failed/timed-out attempts still consume budget; duplicate settlement and
  byte-budget overruns terminate execution — `LaneARequestLedger`)
- Rate limits: honor 429 + Retry-After as STOP (no retry within this packet)

## Evidence & lineage

- Raw response bytes preserved verbatim per request (immutable external root,
  operator-designated; never inside repo without review)
- SHA-256 per raw payload + manifest binding (request URL sans secrets, params,
  page token, status, byte count, timestamp)
- Credentials: environment provider only; redacted from all logs/manifests
- Error taxonomy: RETRIEVED / PARTIAL / AUTH_FAILED / FORBIDDEN /
  ENTITLEMENT_DENIED / HTTP_FAILED / TRANSPORT_FAILED / MALFORMED /
  BUDGET_EXHAUSTED (map per RI-01 Canary 1 precedent)

## Fail-closed stops

- Any 401/403 without allowlisted SIP-restriction message → stop, no entitlement inference
- Payload budget exceeded → stop, preserve partial manifest
- Non-monotonic/duplicate/off-calendar bars → contract failure, unqualified
- Corporate-action fields present but share-basis undeclared → Lane B scope,
  not inferred here
- UTC validity: unissued (operator binds `approved_at_utc` AND fills
  `valid_from_utc >= approved_at_utc` per the 2026-10-11 invariant; naive
  timestamps and retroactive windows rejected)

## Out of scope

- No FRED/BOT under this packet; no paid plan; no sealed holdout; no strategy
  outcome testing; no paper/live orders; no IBKR connection.
- Lane B (genuine corporate-action event qualification vs issuer records) needs
  a separate authority.
