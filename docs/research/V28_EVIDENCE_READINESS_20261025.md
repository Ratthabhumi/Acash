# V28 Evidence Readiness — Source/Rights Gap Matrix and Owner Packet

Boundaries unchanged: `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`,
`LANE_A = UNISSUED`, `LANE_B = UNISSUED`, `D5_REAL_DATA_NOT_ADMITTED`,
`V2_FORMAL_RATIFICATION = PENDING`, `D5_ADMISSION_TRUST_ANCHORS = EMPTY`.

## 1. V28 engineering changes

| Item | Change | Evidence |
|---|---|---|
| F01 | additive correction record; frozen R4 untouched; verdict unchanged | `docs/phase14/HYP_007_M2_TAF_RATE_CORRECTION_001.md`, `tests/unit/research/test_hyp_007_taf_correction_001.py` |
| F02 | ADR: separate engines, shared primitives | `docs/research/ADR_V28_F02_HOLDINGS_ACCOUNTING_ENGINES.md` |
| F03 | D6 keeps every distribution event per ex-date; duplicates/revisions fail closed; per-event settlement | `tests/unit/research/test_d6_v28_causal_and_identity.py` |
| F04 | ledger schema V2: extraction ≠ census; `CensusEvidence` required; split census separate | `tests/unit/data/test_corporate_action_ledger.py` |
| P4 | D6 primary timing = prior-close decision, next-open execution | same D6 test file; amendment A2 |
| P8 | FX reporting overlay (synthetic tests only) | same D6 test file |

## 2. Issuer source and rights gap matrix (2016-01-01..2025-12-31)

No extraction was performed in V28: for every source below the redistribution/derived-use
terms have not been verified, so extraction stops at the rights boundary. Retrieved-now
data would also not establish published-then vintage (PIT `UNKNOWN`).

| Ticker | Source identified | Coverage claimed by source | Terms verified | Ledger status (cash / split) |
|---|---|---|---|---|
| VOO | Vanguard product page, distribution history export (up to 10 years) | not verified for 2016 | UNKNOWN | `SOURCE_IDENTIFIED` / missing |
| BND | Vanguard product page, distribution history export | not verified | UNKNOWN | `SOURCE_IDENTIFIED` / missing |
| BIL | State Street SPDR historical distributions XLSX | not opened | UNKNOWN | `SOURCE_IDENTIFIED` / missing |
| GLD | SPDR Gold Trust sponsor page / trust documents | n/a (no cash distributions) | UNKNOWN | `NO_CASH_DISTRIBUTION_ENTITLEMENT` / missing (split census not established) |

## 3. Alpaca (provider decision)

- Public capability (`PUBLIC_DOCUMENTATION_ONLY`): Basic plan free with historical equity
  data since 2016; historical SIP older than 15 minutes documented as available without a
  real-time SIP subscription. No paid subscription is assumed necessary.
- Account rights: `UNKNOWN` — tier, feed entitlement, verbatim raw retention, local
  storage duration, internal derived research, contract version, expiry, continued use
  after closure. Redistribution: publicly documented as prohibited.
- Acquisition stays `UNISSUED`. Single provider inquiry:

> For account [owner fills in], under the current agreement version: may a single-user
> internal research project download 2016–2025 daily US ETF bars (IEX and/or SIP older
> than 15 minutes), retain the verbatim JSON responses with checksums in private local
> storage, for how long, and use derived backtest results internally without
> redistribution, including after the account or subscription ends? Please name the
> controlling agreement and version.

## 4. D7 policy

DSR/PBO/CPCV/multiple-testing stay unwired from the five fixed D6 comparators (D6 is
descriptive). They apply to future strategy research only with sealed trial counts,
partitions and separate research authorization. HYP_003 stays `TERMINALLY_FALSIFIED`.

## 5. Owner decision packet

1. Ratify or reject D6 A1 (descriptive, no numeric risk threshold) and A2 (causal timing).
2. Send or answer the single Alpaca inquiry above; record the controlling agreement.
3. Authorize issuer extraction once each issuer's terms are confirmed to permit private
   research use (repository stores only parsers, schemas, hashes and derived diagnostics).
4. Acknowledge F01 record (verdict unchanged) and the F02 ADR.

## 6. External research brief (for ChatGPT research, not executed here)

For Vanguard (VOO, BND), State Street (BIL) and the SPDR Gold Trust (GLD): quote the
site terms of use relevant to downloading distribution history for private research;
state the earliest year actually present in each official export; list any splits or
capital-gain distributions 2016–2025 with the issuer document that records them; and
state whether the GLD trust has had any share split since inception, citing the trust
filing.

Next scientific milestone: a rights-verified, D5-admitted 2016–2025 price and
distribution dataset with ledger V2 census evidence, then the D6 descriptive run under
ratified A1/A2.
