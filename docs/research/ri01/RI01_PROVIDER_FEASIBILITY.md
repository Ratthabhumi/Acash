# RI-01 Provider Feasibility (ZERO-OUTCOME, DOCUMENTATION EVIDENCE ONLY)

**Network posture**: ZERO network requests performed in this pack. No explicit
research-network authority was granted, so per the fail-closed rule this pack
STOPS at documentation/API-contract evidence already present in the
repository. Every provider fact below is therefore either `PROVEN_IN_REPO`
(cryptographic manifest or sealed qualification on record) or `UNKNOWN`
(requires an entitled check under separate authorization).

## 1. Candidate providers

**Official-authority reconciliation date**: 2026-10-04 (sources in §4; zero
market-data requests performed — documentation pages only).

### P1 — Alpaca Markets Historical Stock Data (SIP)
Role: primary candidate (all ACASH qualifications to date use it).

| Dimension | Status | Evidence |
| :--- | :--- | :--- |
| Official source | `DOCUMENTED_OFFICIAL` (endpoint shapes) | OpenAPI reference `GET /v2/stocks/bars` + `MEC-0015-provider-qualification-contract.md` §2 |
| 1Min timeframe support | `DOCUMENTED_OFFICIAL` | `[1-59]Min` per reference; example `1Min` |
| `feed=sip` support | `DOCUMENTED_OFFICIAL` | Historical feed enum incl. SIP |
| `adjustment=raw` support | `DOCUMENTED_OFFICIAL` | `raw` = no adjustments (default) |
| Symbol `asof` mapping | `DOCUMENTED_OFFICIAL` **with rename-day lag** | FB→META example; mapping available only the day AFTER rename (upstream limitation) |
| Historical depth (documented) | `DOCUMENTED_OFFICIAL` (both plans) | Equities historical data since 2016, Basic and Plus |
| 15-minute historical SIP rule | `DOCUMENTED_OFFICIAL` | FAQ: historical `end` ≥ 15 min old queries SIP without subscription; recent SIP needs Plus |
| Plan baselines (documented) | `DOCUMENTED_OFFICIAL` (not our tier) | Basic free / 200 calls-min; Plus $99-mo / 10,000 calls-min. Our actual tier NOT inferred |
| Rate-limit headers | `DOCUMENTED_OFFICIAL` | `ratelimit_limit/remaining/reset` in OpenAPI |
| Pagination contract | `DOCUMENTED_OFFICIAL` | `next_page_token` to exhaustion |
| Historical trades (SIP + asof) | `DOCUMENTED_OFFICIAL` (capability) | Trades reference supports SIP feed + asof; unprobed for RI-01 |
| Trade conditions O/Q/X/6 | `DOCUMENTED_OFFICIAL` (semantics) | O = Opening (updates bars), Q = Official Open (updates nothing), X = Cross (updates), 6 = Closing (updates); M = Official Close (updates nothing) |
| Bar aggregation (left-edge) | `DOCUMENTED_OFFICIAL` | Trade timestamp truncated to minute; bar = `[minute, minute+1)`; no-trade interval emits NO bar |
| Corporate-action REST | `DOCUMENTED_OFFICIAL` (with warning) | `GET /v1/corporate-actions`; **no creation-time guarantee**, may be delayed |
| Corporate-action SSE | `DOCUMENTED_OFFICIAL` (capability) | insert/update/delete mutations + ULID event_id + since/since_id/Last-Event-Id replay |
| Daily coverage (1Day SIP, raw/split) | `PROVEN_IN_REPO` (narrow scope) | HYP_011 qualification: 2016-01-04..07, ACWI/AGG/SPY |
| Minute coverage (1Min SIP raw, SPY) | `PROVEN_IN_REPO` (narrow scope) | MEC-0015 manifest: 6 sessions, 2,340/2,340 bars, 390/390 each |
| Minute coverage (ACWI/AGG, any window) | `UNKNOWN` | Never qualified |
| Minute coverage (SPY, RI-01 scope) | `UNKNOWN` | Only 6 probe sessions on record |
| Current credential entitlement | `UNKNOWN` | Mechanism exists (`EnvAlpacaCredentialProvider`); tier/coverage/depth unverified without a call |
| Reproducibility (byte-stable re-fetch) | `UNKNOWN` | Never re-fetch-tested |
| Bar revision behavior | `UNKNOWN` | Never tested |
| Dividend PIT vintage | `BLOCKED_HISTORICAL` | Vendor gives no creation-time guarantee; historical first-publication vintage unrecoverable |
| Symbol lifecycle (contract test) | `UNKNOWN` | asof documented; rename-day PIT + full lifecycle never contract-tested |
| Licensing / redistribution | `UNKNOWN` | Never reviewed |

### P2 — Exchange/consolidated-tape archives (e.g. TAQ-style)
Role: literature-grade alternative (Gao et al. used TAQ).

| Dimension | Status | Evidence |
| :--- | :--- | :--- |
| All dimensions | `UNKNOWN` | No ACASH qualification, no entitlement, no cost review on record |

### P3 — Zero/low-cost free sources
Role: rejected for feasibility scope (not evaluated).

| Dimension | Status | Evidence |
| :--- | :--- | :--- |
| Suitability | `REJECTED_OUT_OF_SCOPE` | Free-data feasibility belongs to a different lane (HYP_006/MEC-0016); SIP-qualified lineage is the RI-01 baseline |

## 2. Proven in-repo constraints (bind the next step regardless of provider)

1. **The currently-qualified HYP_011 client is 1Day-only.** `HYP011AlpacaClient`
   hard-rejects any other timeframe (`src/acash/data/qualification/hyp_011_qual_client.py`).
   RI-01 minute access therefore requires a NEW minute-capable qualification;
   it cannot ride the HYP_011 client.
2. **Prior close ≠ 15:59 bar close.** The 16:00 auction cross can diverge 1–5 bps
   (MEC-0014 §10.2). A dedicated close-authority contract test is mandatory
   before any $r_1$-style predictor is defined.
3. **Dividend PIT vintage is NOT guaranteed** by the vendor (MEC-0015 §7.3).
   Acceptable only for publication-exposed historical replication, never
   assumed for prospective use.
4. **OOS boundary discipline holds.** Nothing on/after the sealed holdout may
   be touched without explicit human authorization (MEC-0014 §13).

## 3. Official authority sources (retrieved 2026-10-04, documentation only)

- Bars reference: `https://docs.alpaca.markets/us/reference/stockbars`
  (`[1-59]Min`, `feed`, `adjustment=raw/split/dividend/spin-off/all`, `asof`
  with FB→META rename example, `next_page_token`).
- OpenAPI spec: `https://docs.alpaca.markets/us/openapi/market-data-api.json`
  (feeds incl. `sip`/`delayed_sip`, rate-limit headers, CA SSE `since`/
  `since_id`/`Last-Event-Id`, ULID event ids).
- Plans: `https://docs.alpaca.markets/docs/about-market-data-api`
  (Basic free/200-min/since-2016/latest-15-min; Plus $99-mo/10,000-min/no
  restriction) and `https://alpaca.markets/data` (7+ years historical).
- Market Data FAQ: `https://docs.alpaca.markets/us/docs/market-data-faq`
  (historical SIP `end` ≥ 15 min old without subscription; `asof` rename-day
  lag; left-edge `[minute, minute+1)` aggregation; O/Q/X/6/M condition table;
  no-trade interval emits no bar).
- Corporate actions reference:
  `https://docs.alpaca.markets/us/reference/corporateactions-1`
  (no creation-time guarantee; `data_quality=complete/all`).
- CA events SSE reference:
  `https://docs.alpaca.markets/eu/reference/subscribetocorporateactionseventssse`
  (insert/update/delete mutations + replay).
- Community/blog sources were NOT used where official docs answer the point.

## 4. Evidence required to flip each UNKNOWN (future authorized probe plan, NOT executed)

- Entitlement probe: credential-tier capability listing (zero market dates).
- Depth probe: earliest retrievable 1Min SIP session per candidate symbol.
- Coverage probe: session×symbol availability census over the feasibility window.
- Stability probe: byte-identical re-fetch of a fixed session (reproducibility).
- Revision probe: first-publication vs delayed re-fetch diff.
- Cost probe: measured quota/latency per 1,000 sessions.
- License review: redistribution terms for derived research artifacts.

Each probe needs its own explicit network authorization with a date-bounded,
symbol-bounded scope. This pack performs NONE of them.
