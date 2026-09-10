# ACASH V5 — FREE-DATA SOURCE REGISTRY

**Document ID:** `docs/phase14/free_data_source_registry.md`
**Object:** Structured register of free/public data sources for the Free-Data Capital Bootstrap Program — tier-classified, evidence-tracked, `$0`-only
**Status:** `[DOCUMENTATION-ONLY]` · `[NOT HYP_003]` · `[NOT R1]` · `[NOT D2]` · `[NOT F-1]`
**Date:** 2026-09-10 (retrieval date for all records; every claim is drawn from the audited evidence baseline of the F-1 D1 audits, not from new day-of research)

**Terms of use of this registry:**
- "Free" = accessible at $0 under applicable terms; **"free" ≠ "research-safe"** — each record states terms/license. Unknown → `[UNVERIFIED]` (never assumed).
- Tier rule: TIER 4 may be used for **exploratory feasibility only** and is NOT automatically evidence for a production-quality candidate.
- Every source used in data construction requires archive-at-retrieval (raw bytes + fetch timestamp) and a provenance manifest entry.
- This registry is a living governance doc; additions require evidence, not discovery-by-hunch. No vendor here is "selected" for purchase — paid items appear only in the FUTURE ACQUISITION QUEUE (§27 of the program charter) and are NOT purchasable without Human Governance budget authorization.

**Classification labels (inherited):** `[ACCEPT]` `[CONDITIONAL]` `[UNVERIFIED]` `[NOT SUFFICIENT AT $0]` `[REJECT]` · `[PIT PROVEN]` / `[PIT UNPROVEN]`

---

## 1. REGISTRY INDEX BY TIER

| Tier | Definition | Registered sources |
|------|-----------|--------------------|
| **TIER 1** | Primary authoritative source | SEC EDGAR (filings/submissions/company_tickers/Form 25) · Federal Reserve (FRED/VIXCLS) · BLS (CPI/NFP/Official release calendar) · U.S. Treasury · CBOE official index data · Federal Reserve FOMC calendar & statements · S&P DJI announcement PDFs/press releases (index events) |
| **TIER 2** | High-quality public secondary | Stooq (daily OHLCV) · Alpha Vantage free tier · OpenFIGI (symbology) · FRED mirrors (where applicable) · public exchange listing/schedule pages (as verified) |
| **TIER 3** | Community-maintained with provenance | fja05680/sp500 · pitindex · NYU Wurgler file · shawnlinxl/snp-history · Wikipedia (index membership) · yfinance (unofficial, ToS risk) · Acelogic Wayback scraper · businessquant CA endpoint · tenicho/data-cleaning |
| **TIER 4** | Unverified aggregation / convenience — exploratory only | securitiesdb CA API · Kaggle Arandkei delisted archive · Financial Modeling Prep free tier · tickerleague · historicaldata.net (free sample) · Tiingo (free tier status unverified) · stockanalysis.com |

---

## 2. SOURCE RECORDS

### 2.1 TIER 1 — Primary authoritative

**S-01 SEC EDGAR (filings, submissions index, company_tickers.json)**
- Owner: U.S. Securities and Exchange Commission. URL: `www.sec.gov/edgar/searchedgar/companysearch.html`; `www.sec.gov/files/company_tickers.json`; submissions API `data.sec.gov/submissions/CIKxxxxxxxxxx.json`.
- Access date: 2026-09-10 (verified in F-1 D1 audits). Data type: issuer identity (CIK/tickers), filing metadata, full-text; PIT: accession numbers + acceptance timestamps `[PIT PROVEN]` per filing.
- Depth: electronic filings since ~1993–2001 (varies by form; Form 25/25-NSE May 2006+). Survivorship: N/A (filings persist; issuers delisted still addressable by CIK). License: public; fair-access rate limits (10 req/s guidance for SEC, 5 req/s historically; bulk allowed but etiquette required); no redistribution restriction for research. Reproducibility: immutable accession numbers `[CONDITIONAL]` (excellent).
- Limitations: no prices; earnings press-release timing ≠ filing acceptance (offset must be handled); subject to SEC rate limits.
- Classification: `[ACCEPT]`.

**S-02 SEC EDGAR Form 25 / 25-NSE (delisting notifications)**
- Owner: SEC. URL: `www.sec.gov` (full-text search "FORM 25"); verified 2026-09-10. Data: issuer delisting (removal from listing & registration), exchange, filing timestamp, CIK; depth May 2006+.
- PIT `[PIT PROVEN]` by filing timestamp. Survivorship: covers DELISTED identities (no prices). License: public. Reproducibility: accession-numbered.
- Limitations: delisting events only; effective delisting ≈ filing + ~10 days (minor offset); no OHLCV.
- Classification: `[ACCEPT]` (delisting events) — used by F-1 B4 and this track's delisting-identity needs.

**S-03 SEC EDGAR N-PORT / N-CSR / N-Q (fund portfolio holdings)**
- Owner: SEC. URL: `www.sec.gov` (search type NPORT-P, e.g., CIK 0001100663 iShares Trust). Verified 2026-09-10 (multiple NPORT-P filings observed; N-PORT regime ~2019+, earlier N-CSR/N-Q).
- Data: complete fund portfolio holdings schedules, filing-date PIT `[PIT PROVEN]` (quarterly/semi-annual; holdings as of period/quarter end). License: public. Reproducibility: accession numbers.
- Limitations: fund holdings ≠ official index membership (tracking deviation, sampling, substitutions, cash); fill ~up to 60 days after period end → event-lag; only useful as a **conditional roster proxy** with parity validation.
- Classification: `[ACCEPT]` for the filing series; roster↔index parity `[UNVERIFIED]`.

**S-04 Federal Reserve / FRED (St. Louis Fed)**
- Owner: Federal Reserve Bank of St. Louis (FRED); underlying series from official sources (CBOE for VIXCLS, etc.). URL: `fred.stlouisfed.org`. Verified 2026-09-10 (referenced methodology/official series in F-1 D1 baseline).
- Data: macro indicators, rates, **VIXCLS (CBOE VIX daily close, 1990+)**; free CSV API. PIT: vintage-history available for many series (as-published) `[CONDITIONAL]`; standard series snapshot `[UNVERIFIED]` vintage-wise unless archived.
- Survivorship: N/A (index/aggregate). License: public/Federal data; FRED ToS free for research. Reproducibility: series IDs stable; archive-at-retrieval recommended.
- Limitations: daily frequency only for VIXCLS (VIX intraday is CBOE premium); some series revised (revisions -> versioning needed).
- Classification: `[ACCEPT]` (official series) with `[CONDITIONAL]` vintage discipline.

**S-05 BLS (Bureau of Labor Statistics) — CPI / Employment Situation (NFP)**
- Owner: U.S. BLS. URL: `www.bls.gov` (release calendar, `bls.gov/schedule/news_release/`). Verified 2026-09-10 (public schedule; release datetimes published in advance; 8:30am ET convention).
- Data: scheduled economic release calendar (dates + times), CPI/NFP values, revisions. PIT: release schedule is pre-announced and stable `[ACCEPT]` for event dates/times; series values subject to revision (as-published vintage needed).
- License: public domain/PD. Reproducibility: calendar archived at retrieval.
- Limitations: release times are ET-anchored; early-release count adjustments occur rarely — must be archived.
- Classification: `[ACCEPT]` for announcement-date PIT; series vintage `[CONDITIONAL]`.

**S-06 U.S. Department of the Treasury — rates / auction calendar**
- Owner: U.S. Treasury. URL: `home.treasury.gov`. Data: official rates, auction/reopening calendar. PIT: official schedule `[PIT PROVEN]` for auctions. Public/PD. Classification: `[ACCEPT]` (as needed).

**S-07 CBOE — official VIX / index data**
- Owner: Cboe Global Markets. URL: `www.cboe.com/tradable_products/vix/` and historical data files. Verified 2026-09-10 (referenced in feasibility baseline at reference-document level; daily history availability free, intraday premium).
- Data: VIX historical daily (official), VIX subs (VIX9D/VIX3M etc. — availability `[UNVERIFIED]` free; some free via Yahoo). PIT: index-level daily `[PIT PROVEN]`-adjacent (official publication); vintage `[CONDITIONAL]`.
- License: CBOE terms; research use normal; redistribution review required. Reproducibility: archive-at-retrieval.
- Classification: `[CONDITIONAL]` (official daily at $0; intraday/term-structure more constrained).

**S-08 Federal Reserve — FOMC meeting calendar & statements**
- Owner: Federal Reserve System. URL: `www.federalreserve.gov/monetarypolicy/fomccalendars.htm`. Verified 2026-09-10 (public schedule).
- Data: meeting dates, statement release 2:00pm ET, Press Conference schedule (2011+ meetings typically; 2019+ each meeting). PIT: schedule pre-announced `[ACCEPT]`; statement timestamps official.
- Classification: `[ACCEPT]`.

**S-09 S&P DJI — quarterly reconstitution announcements (press + announcement PDFs, incl. Wayback)**
- Owner: S&P Dow Jones Indices LLC. URLs: `www.spglobal.com/spdji/en/documents/indexnews/announcements/…` (e.g., `1464356_shufjun23.pdf`, `1483743_shuffle546-june2026.pdf`); `press.spglobal.com`; PRNewswire S&P DJI hub; Wayback CDX `spglobal.com/spdji/en/documents/indexnews/announcements*` (2013-04-16→2022-08-04 observed; quarterly artifacts 2013-12-11+).
- Data: S&P 500/400/600 membership changes — announcement + effective dates, ticker, GICS; full memo format. PIT: `[PIT PROVEN]` for content-verified samples (2023/2026); per-event proof for 2013–2022 outstanding `[UNVERIFIED]` (presence verified).
- Survivorship: announcements are as-announced (PIT, no survivor lists) — critical for index research. License: S&P DJI IP; internal research OK; redistribution/product-creation restricted → publication review required.
- Reproducibility: stable URLs + Wayback captures + archive-at-retrieval `[CONDITIONAL]` (excellent with discipline).
- Classification: `[CONDITIONAL]` — **primary event authority for the family-7 (index/rebalance) lane (F-1), NOT for bootstrap-track intake** (lane separation, charter §2).

### 2.2 TIER 2 — High-quality public secondary

**S-10 Stooq — daily OHLCV downloads**
- Owner: Stooq (commercial entity). URL: `stooq.com/db/h/` , `stooq.com/terms.html`. Verified 2026-09-10.
- Data: daily (and intraday) OHLCV CSV by region; US daily ~500MB zip; 30+ years for many active names; `^spx` index symbols. Delisted: **NOT covered** (removed from provider DB — verified via Acelogic scraper README).
- PIT: none (mutable DB, no vintage IDs) `[PIT UNPROVEN]` unless archived at retrieval. Close/adjustment: vendor-derived; raw close available but adjustment method not fully documented `[UNVERIFIED]`.
- License: **personal use only; commercial prohibited; redistribution without consent prohibited; S&P/DJ data restricted to personal non-commercial**. Survivorship: active names only → `SURVIVORSHIP_LIMITED` for equity construction.
- Reproducibility: `[REPRODUCIBILITY RISK]` unless archived instantly.
- Classification: `[CONDITIONAL]` (active-name OHLCV/ADV; personal-use terms; not lo N/A cavalier for production).

**S-11 Alpha Vantage — free tier**
- Owner: Alpha Vantage Inc. URL: `www.alphavantage.co/documentation` , `www.alphavantage.co/premium`. Verified 2026-09-10.
- Data: free key 25 req/day, 5/min; `TIME_SERIES_DAILY` compact (~100 pts) free, **`full` deep history = premium**; intraday premium; delisted `LISTING_STATUS&state=delisted` CSV free (metadata only).
- PIT: none (mutable) `[PIT UNPROVEN]`; License: registered use, restricted redistribution; Survivorship: active + delisted-ROSTER metadata only.
- Classification: prices `[CONDITIONAL]` (shallow)/`[REJECT]` (deep); delisted metadata `[ACCEPT]`.

**S-12 OpenFIGI — symbology mapping**
- Owner: OpenFIGI (Bloomberg/Open Symbology). URL: `www.openfigi.com` (API v3 `api.openfigi.com/v3/mapping`). Verified 2026-09-10.
- Data: ticker/CUSIP/ISIN ↔ FIGI/other; current mapping (NOT historical PIT); rate-limited 25 req/min without key. License: MIT/Open Symbology, Apache-2.0 API spec. Classification: `[ACCEPT]` identity / `[CONDITIONAL]` historical.

### 2.3 TIER 3 — Community-maintained with provenance

**S-13 fja05680/sp500** — GitHub, MIT. Daily S&P 500 membership snapshots 1996→present; seeded from Clenow ("Trading Evolved") + Wikipedia; commit-pinnable. S&P 500 ONLY; effective-date diffs; tickers as-listed; delisted names post-event notation done (e.g., LEHMQ). `[CONDITIONAL]` (S&P 500 events; not official; secondary reconstruction).

**S-14 pitindex** — GitHub, MIT + CC BY-SA underlying. S&P 500 (2005+), S&P 400 (2011-11+), S&P 600 (2021-03+), `sp1500` composite. Upper-bound event dates (≤ ~1 month lag); removals-gap documented; no announcement timestamps. `[CONDITIONAL]` for families; `[UNVERIFIED]` deep-history for 400/600.

**S-15 NYU Wurgler file** — academic static file: S&P 500 additions 1976–2000, deletions 1979–2000, two event dates, reason codes. `[ACCEPT]`/`[CONDITIONAL]` (S&P 500 anchor, ends 2000).

**S-16 shawnlinxl/snp-history** — GitHub single-maintainer: S&P 500 add/remove 2000–2016 with announcement + implementation dates; caveats (tickers PIT; pre-2017 add timing unverified). `[CONDITIONAL]`/`[UNVERIFIED]` (unlicensed).

**S-17 Wikipedia — S&P membership + changes tables** — CC BY-SA 4.0, `oldid`-pinnable. Changes tables ~2014+ with effective dates (announcement NOT structured); S&P 400/600 deletions incomplete (documented). `[CONDITIONAL]` membership; `[PIT UNPROVEN]` announcements.

**S-18 yfinance (unofficial Yahoo wrapper)** — free, unofficial; Yahoo ToS restricts bulk/redistribution (risk). Active names; delisted absent; no vintage; mutable. `[CONDITIONAL]` active / `[REJECT]` deep delisted.

**S-19 Acelogic Wayback Machine Stock Scraper** — GitHub: scrapes archived old-Yahoo daily data for delisted names; unofficial, fragile, non-contractual, unlicensed. `[CONDITIONAL]`/`[UNVERIFIED]` — viable for **exploratory** delisted-price feasibility only.

**S-20 businessquant corporate-actions API** — registered free tier (30 calls/day) parsing SEC; splits/dividends/IPOs; reproducibility/coverage `[UNVERIFIED]`; terms `[UNVERIFIED]`. `[CONDITIONAL]`/`[UNVERIFIED]`.

**S-21 tenicho/data-cleaning** — GitHub survivorship-clean US panel; delistings concentrated 2021–2026, pre-2016 deaths largely absent (self-disclosed) → materially incomplete for deep delisted work. `[NOT SUFFICIENT AT $0]` for the F-1-calibre deletion leg; `[CONDITIONAL]` exploratory.

### 2.4 TIER 4 — Unverified aggregation / convenience (exploratory only)

**S-22 securitiesdb Dividend/Split API** — `securitiesdb.com/developers/dividend-api`; free GET `…/api/v1/stocks/{ticker}/dividends` (ex_date/amount/type; splits date/ratio); no key; terms: as-is, may be rate-limited/changed/discontinued, third-party feeds; depth/coverage/adjustment `[UNVERIFIED]`. `[UNVERIFIED]` (license also unverified).

**S-23 Kaggle "Arandkei: Historical Delisted Assets Archive"** — `kaggle.com/datasets/rodas86/arandkei-historical-delisted-assets-archive`; created 2026-02-19/updated 2026-03-08; daily OHLCV for delisted assets; **license page unrenderable 2026-09-10 → LICENSE = `[UNVERIFIED]`**; coverage/age/provenance `[UNVERIFIED]`. `[UNVERIFIED]` — do NOT promote (prompt rule).

**S-24 Financial Modeling Prep (FMP) free tier** — delisted-company handling claimed in blog; free-tier depth `[UNVERIFIED]`; no verified free bulk delisted OHLCV. `[UNVERIFIED]`.

**S-25 tickerleague** — S&P 500 changes list (1523 records) unverified third-party. `[UNVERIFIED]`.

**S-26 historicaldata.net** — free = sample only; full = paid subscription; claims incl. active + delisted. `[NOT SUFFICIENT AT $0]`.

**S-27 Tiingo** — free tier exists in 2026? status `[UNVERIFIED]` (would require billing-able account; splits/dividends free-tier depth unverified). `[UNVERIFIED]`/`[CONDITIONAL]`.

**S-28 stockanalysis.com / per-fund pages** — free to view; scraping terms unverified; mutable. `[UNVERIFIED]`.

---

## 3. FUTURE DATA ACQUISITION QUEUE (PURCHASE NOT AUTHORIZED)

Capability names only; rank by blocker-resolution value; **no vendor selected**.

| Priority | Capability | Solves | Why valued | Est. pathways (illustrative only) |
|----------|-----------|--------|-----------|-----------------------------------|
| 1 | Delisted/security-master daily OHLCV history (survivorship-free, CA-treated) | **B2** (F-1); survivorship ceilings for momentum/reversal/PEAD | certified deletion-leg coverage | academic (WRDS/CRSP) / commercial (EODHD-style, Norgate-style, Sharadar-style) — illustrative |
| 2 | Historical PIT free-float / IWF-quality data | **B5** (F-1) | frozen universe filter PIT | fundamentals/historical-float vendors — illustrative |
| 3 | Historical analyst-consensus EPS expectations (long history) | PEAD SUE variant (`CAND-FREE-PEAD-001`) | standardized surprise (SUE) measurement | consensus-estimate vendors — illustrative |
| 4 | Structured historical split/dividend/ex-date master with adjustment provenance | **B4** (F-1) + general CA layer | PIT CA ordering | corporate-action masters — illustrative |

Any purchase requires explicit Human Governance budget authorization; nothing here authorizes it.
[NOT AUTHORIZED]

---

## 4. SURVIVORSHIP SUMMARY (ACROSS TIERS)

- **Active-name OHLCV:** TIER 2 (Stooq/AV/shallow), TIER 3 (yfinance) — no delisted price history.
- **Delisted identities/dates:** TIER 1 (SEC Form 25, N-PORT rosters) — no prices.
- **Delisted OHLCV:** TIER 3 (Wayback scraper, exploratory) / TIER 4 (Kaggle — license UNVERIFIED) — **no certified $0 path**. [VERIFIED ABSENCE — 2026-09-10]
- Consequence: equity candidates on this track must be marked **`SURVIVORSHIP_LIMITED`** unless a
  survivorship-free leg is added (bounded B2-adjacent queue). [FROZEN]

### Verification Ledger (this registry)
- Implementation Status: NONE (documentation-only; no code, no ingestion).
- Contract Enforcement: STRICT FAIL-CLOSED — no license inferred; no TIER 4 promoted; no vendor
  "selected"; no paid data authorized.
- Evidence Baseline: all records cited from the 2026-09-10 audited F-1 D1 evidence; no new day-of
  research was run (registry is a governance compilation, not a source hunt).
- Local Test Suite / Remote CI: NOT RUN / NOT AVAILABLE (documentation-only convention).
- Methodological Caveats: source terms/license can change post-retrieval; every mutable source needs
  archive-at-retrieval; Kaggle (S-23) license remains unrenderable and unverified.

STOP — SOURCE REGISTRY (FREE-DATA TRACK) ESTABLISHED. NO DATA INGESTED. NO PURCHASE AUTHORIZED.