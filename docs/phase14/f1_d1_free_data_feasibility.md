# ACASH V5 — F-1 D1 FREE-FIRST DATA FEASIBILITY AUDIT

**Document ID:** `docs/phase14/f1_d1_free_data_feasibility.md`
**Object:** F-1 `CAND-FLOW-CALENDAR-REBALANCE-001` data feasibility using `$0` free/public data
**Status:** `[FEASIBILITY-ONLY]` · `[NON-NORMATIVE]` · `[NOT HYP_003]` · `[NOT R1]`
**Date:** 2026-09-10 (retrieval date for all web evidence in this document)
**Classification labels:** `[FREE-FIRST]` `[FEASIBILITY-ONLY]` `[NON-NORMATIVE]` `[NOT HYP_003]`
`[NOT R1]` `[PIT PROVEN]` `[PIT UNPROVEN]` `[ACCEPT]` `[CONDITIONAL]` `[UNVERIFIED]` `[REJECT]`

---

## 1. HEADER / GOVERNANCE STATUS

Continue from the existing canonical governance state. Nothing below is reset, reinterpreted, or
redesigned. [FROZEN]

- HYP_001 = terminally falsified / closed. [FROZEN]
- HYP_002 = terminally falsified / closed. [FROZEN]
- HYP_003 does **NOT** exist. [FROZEN]
- `ResearchReInceptionGate` has **NOT** been invoked for F-1. [FROZEN]
- R1 has **NOT** started. [FROZEN]
- Trading is **LOCKED**; capital remains `$0.00`; no broker / live-trading authorization exists.
  [FROZEN]
- F-1 remains a RESEARCH CANDIDATE: `CAND-FLOW-CALENDAR-REBALANCE-001`. [FROZEN]
- F-1 candidate review recommendation = **ACCEPT WITH FREEZES**; F-1 is **NOT READY** for
  ReInceptionGate. [FROZEN — `docs/phase14/candidate_f1_flow_calendar_rebalance_review.md`]
- This audit is **documentation-only** and creates/alters NO governance state. [NON-NORMATIVE]
- Files changed by this audit: this document only. No `src/`, schema, gate, ROADMAP, registry, R1,
  or trading state was touched. `git status --short` recorded before/after (see §29). [VERIFIED]

## 2. OBJECTIVE

Determine **whether F-1 can be researched initially using ONLY free / publicly accessible data**,
under a `$0 DATA COST` budget. This is a **feasibility audit of data construction**, NOT an
empirical validation. The only question answered here is the data question:

> **Can the required F-1 dataset be constructed with sufficient coverage, PIT validity,
> provenance, and reproducibility using free/public data?**

[FEASIBILITY-ONLY]

## 3. EXPLICIT $0 BUDGET RULE

- DATA COST = `$0.00`. [FROZEN]
- Explicitly NOT purchasing: Databento, S&P DJI, NYSE TAQ, Bloomberg, FactSet, CRSP, Compustat,
  Refinitiv/LSEG, Polygon paid plans, EODHD, Siblis, Sharadar/Nasdaq Data Link, or any other paid
  dataset. [FROZEN]
- No paid account may be created; no charge may be incurred. [FROZEN]
- Free tiers are allowed ONLY if genuinely non-billable for this research **and** the audit
  establishes that fact from documented evidence. Where a source requires payment for the required
  historical dataset it is marked `[REJECT]`; where it could not be verified it is marked
  `[UNVERIFIED]`. [FROZEN]
- "Free API documentation" or "free page" alone is NEVER treated as proof of free usable history.
  [FROZEN]

## 4. EXPLICIT PROHIBITED ACTIONS

This audit does **NOT**: create HYP_003 · invoke ReInceptionGate · invoke R1 · run F-1 hypothesis
tests · run backtests · calculate strategy performance / alpha / Sharpe · optimize parameters ·
select a profitable configuration · inspect outcomes to choose a spec · modify canonical gate
thresholds · authorize paper/live trading · create orders · modify capital/broker state · modify
unrelated ACASH source code. [FROZEN — all]

The audit does NOT turn feasibility into empirical validation. It only records what data can be
obtained and with what properties. [FEASIBILITY-ONLY]

## 5. F-1 SPECIFICATION BEING AUDITED

Frozen/proposed inputs (audited as-is; not revised here):
- **Universe:** S&P Composite 1500 family = S&P 500 + S&P MidCap 400 + S&P SmallCap 600.
  [FROZEN]
- **Universe filters:** ADV ≥ US$5M/day; Free Float ≥ 20%, both PIT. [FROZEN rule level / numeric
  bindings pending]
- **Event family:** INDEX RECONSTITUTION ONLY. NOT combined with month-end/generic calendar
  effects / ES / NQ / SPY / QQQ / other families. [FROZEN]
- **Signal:** Addition = +1, Deletion = −1, Otherwise = 0; composite `FLOW = sum(Additions) −
  sum(Deletions)`. [FROZEN]
- **Event anchor:** Effective Date = T0. [FROZEN]
- **Return:** `R(h) = Close(T0+h) / Close(T0) − 1`, h ∈ {1, 5, 10}; primary 5. [FROZEN]
- **Direction:** SHORT reversal (positive flow → SHORT; negative flow → LONG). [FROZEN]
- **Minimum sample:** `T_eff ≥ 25` per composite leg; `N_valid ≥ 250` active (canonical).
  [FROZEN]
- **PIT hard rule (from governance):** if PIT cannot be proven for an observation, that observation
  is INVALID for a future empirical F-1 dataset. This audit only determines feasibility — it does
  NOT run that filtering. [FROZEN]

## 6. AUDIT METHODOLOGY

1. Enumerate data layers required by the F-1 spec: prices, index membership / reconstitution,
   PIT/announcement timing, corporate actions, delisted/symbology, close semantics.
2. For each layer, discover and compare free/public candidate sources.
3. Record evidence per source: URL, retrieval date (2026-09-10), coverage, free/paid, license,
   PIT semantics, limitations, reproducibility.
4. Classify each layer as `[ACCEPT]` / `[CONDITIONAL]` / `[UNVERIFIED]` / `[REJECT]` from evidence.
5. Classify the Composite 1500 verdict by the **weakest** required component, never the strongest.
6. Optionally run a SMALL data-structure feasibility probe (§11 restriction: no returns/alpha/IC/
   HAC/profitability) and label it `FEASIBILITY SAMPLE ONLY — NOT EMPIRICAL EVIDENCE`.
7. No empirical F-1 test or performance number is computed anywhere in this document.
   [FEASIBILITY-ONLY]

## 7. SOURCE DISCOVERY METHODOLOGY

- Sources were discovered via public web search and directly loaded/verified pages (2026-09-10).
- Each source record below gives: name · exact URL · what was actually verified · free/paid ·
  coverage · PIT semantics · limitations. Where a claim could not be verified from evidence, it is
  marked `[UNVERIFIED]` — nothing is inferred from a free-looking page.
- No vendor access, API key, dataset, coverage, PIT guarantee, or license was fabricated.
  Anything not verifiable is `[UNVERIFIED]`. [FROZEN]

## 8. PRICE / OHLCV SOURCE COMPARISON

### 8.1 Stooq — `https://stooq.com/db/h/` , `https://stooq.com/terms.html`
- **Free?** Yes, download of daily/hourly/5-min ASCII/CSV by region; "intended solely for personal
  use. Any commercial use is prohibited." (terms page, verified 2026-09-10). `[FREE-FIRST]`
- **Coverage:** U.S. daily historical zip ~500 MB; daily history for many US names 30+ years;
  index symbols available (e.g. `^spx`). Sources state coverage of 21k+ global securities/ETFs.
- **Delisted:** NOT covered — an existing GitHub scraper for delisted tickers explicitly lists
  Stooq among providers that "remove delisted stocks from their databases". [VERIFIED via
  github.com/Acelogic/WayBackMachineStockScraper]
- **Close / adjustment:** vendor-derived; an independent tutorial documents that Stooq's close is
  adjusted and that "determining whether adjustments have been made … and how they were carried out"
  is a known free-data issue. Adjustment method not fully documented by Stooq. [UNVERIFIED method]
- **PIT:** none. Mutable database; no snapshot/vintage identifiers exposed. [PIT UNPROVEN]
- **License:** personal-use only; no redistribution without consent; S&P Dow Jones indices data is
  restricted to "personal, non-commercial purposes" and may not be used to create financial
  products. [VERIFIED terms]
- **Reproducibility:** downloads are periodic snapshots without version IDs → `[REPRODUCIBILITY
  RISK]` if not archived at retrieval.
- **Decision:** `[CONDITIONAL]` — usable for active-name daily OHLCV under the personal-use
  license; NOT usable for delisted names; cannot prove official close; mutable.

### 8.2 Alpha Vantage — `https://www.alphavantage.co/documentation`, `https://www.alphavantage.co/premium`
- **Free tier:** free API key + "free forever" (self-described); **25 requests/day, 5/min**
  (verified via AV premium page and independent Macroption article). Registered account, non-billable.
- **Historical OHLCV:** `TIME_SERIES_DAILY` returns raw OHLCV; docs state `outputsize=compact`
  (≈100 points) is available to free AND premium, but **`outputsize=full` is available to premium
  keys**. `TIME_SERIES_INTRADAY` is explicitly a PREMIUM endpoint. `Daily Adjusted` is listed as
  "Trending" and its full adjusted history is likewise premium-gated for deep windows.
  ⇒ **Free tier cannot bulk-reconstruct deep historical daily series for ~1,500 names.** It is NOT
  the automatic winner; it is depth-limited. [VERIFIED]
- **Delisted:** `LISTING_STATUS&state=delisted` returns a free CSV of delisted tickers with
  ipoDate/delistingDate — useful **roster metadata**, but historical OHLCV for delisted names is not
  served by the timeseries APIs. [VERIFIED + PIT UNPROVEN for prices]
- **License:** registered use; commercial re-distribution restricted; rate limits. Personal
  research use OK subject to limits.
- **Decision:** prices `[CONDITIONAL]` for shallow windows / active names only; **effectively
  `[REJECT]` for the deep, full-history OHLCV requirement** on the free tier. Delisted LISTING_STATUS
  = `[ACCEPT]` for delisted roster metadata (free CSV).

### 8.3 Yahoo Finance / `yfinance` (unofficial)
- Free endpoint used by community tools; no official license for bulk download; ToS permits only
  personal, non-commercial limited use; unofficial.
- Coverage: active US names, ~1980s-present daily; **"Yahoo Finance only keeps current stock
  history"** (verified: repository maintainers of the S&P 500 history dataset state that delisted
  symbols must be purchased e.g. via Norgate).
- Delisted: effectively NOT served. Adjustment: split+dividend adjusted + raw close available;
  method opaque. PIT: none. Reproducibility: mutable.
- **Decision:** `[CONDITIONAL]` active names; `[REJECT]` for delisted/back-history reconstruction.

### 8.4 GitHub / open hist-data projects
- Community daily datasets (e.g. `historicaldata.net`, various GitHub repos): free samples only or
  unverified licensing → `[UNVERIFIED]`.

### 8.5 Nasdaq / exchange public datasets
- Public "Nasdaq" listings pages exist but do not provide survivorship-free historical daily OHLCV
  without registration/license; not verified as a free bulk historical feed → `[UNVERIFIED]`.

**Price layer overall: `[CONDITIONAL]`** — active-name daily OHLCV is obtainable free; delisted
historical prices are NOT freely obtainable; official consolidated close semantics not certifiable.

## 9. INDEX / EVENT SOURCE COMPARISON

### 9.1 S&P DJI official announcement PDFs — `https://www.spglobal.com/spdji/en/documents/indexnews/announcements/…`
- **Verified (2026-09-10):** press announcements for the S&P 500 / MidCap 400 / SmallCap 600
  quarterly changes, e.g. 2023-06-02 (`…/1464356_shufjun23.pdf`) and 2026-06-05
  (`…/1483743_shuffle546-june2026.pdf`). Each lists announcement date, effective date, index, action,
  company, ticker, GICS sector.
- **Free?** Yes — publicly hosted, no login observed. `[FREE-FIRST]`
- **PIT semantics:** announcement date + effective date + names → this is the authoritative
  **as-announced** source semantics for covered events. For coverage years it satisfies "what
  existed / when published / before T0". [PIT-satisfying for covered years]
- **Archive depth:** full historical archive coverage NOT verified (2023 and 2026 demonstrated;
  older years may exist but nothing is assumed) → `[UNVERIFIED]` for the deep history.
- **License:** S&P DJI intellectual property. Internal research use of announcements is normal;
  redistribution/product-creation restricted. Flag for human/legal review if a derived membership
  dataset is to be distributed. `[SEE §20]`
- **Decision:** `[CONDITIONAL]` — primary event authority for recent years; deep-history archive
  unverified.

### 9.2 Wikipedia — `https://en.wikipedia.org/wiki/List_of_S%26P_500_companies` (and S&P 400 / S&P 600 pages)
- "Selected changes…" tables with **Date (effective), Added/Removed ticker+security, reason**,
  from ~2014 to present across the 500/400/600 pages; dedicated "Historical components of the S&P
  400/600" pages exist. CC BY-SA 4.0.
- PIT: effective dates only; **announcement dates are NOT structured**; the S&P 400/600 tables are
  documented by a canonical review as "measurably incomplete … mostly missing removals".
  ⇒ `[PIT UNPROVEN]` for announcement timing from Wikipedia alone. [VERIFIED via pitindex DESIGN
  notes + page content]
- **Decision:** `[CONDITIONAL]` — reconstructed membership/effective-date events for recent years;
  deletion completeness and announcement timing not guaranteed.

### 9.3 `fja05680/sp500` — `https://github.com/fja05680/sp500` (MIT)
- Daily S&P 500 membership snapshots 1996 → present; seeded from Andreas Clenow's "Trading Evolved"
  open data + Wikipedia updates; 933★/203 forks; MIT.
- PIT: effective-date-diff daily snapshots (reconstructed), tickers as-listed; delisted tickers
  post-event notation noted (e.g. LEHMQ); 487 names in early rows. S&P 500 ONLY.
- **Decision:** S&P 500 membership anchor `[CONDITIONAL]`/usable; NOT official; delisted price gap
  acknowledged by maintainers.

### 9.4 pitindex — `https://github.com/arielNacamulli/pitindex` (MIT) — REQUIRED SPECIAL AUDIT
- What it supports: S&P 1500 family — `sp500` (from 2005-01-03), `sp400` (from **2011-11-20**),
  `sp600` (from **2021-03-26**), `sp1500` composite (max of the three).
- Methodology: built from free public sources in order of trust — (1) seed snapshot dataset
  `fja05680/sp500` for S&P 500; (2) Wikipedia "changes" tables; (3) Wikipedia page **revision
  history** diffs for S&P 400/600. Per-index reconciliation gate (≤5% roster diff) fails loud.
- **Limitations (self-disclosed):**
  - S&P 600 coverage only from 2021-03-26 because the pre-2021 Wikipedia S&P 600 page carried a
    wrong ~1000-name roster and "no free source for its membership exists."
  - S&P 400/600 fill-event dates are **upper bounds** (revision timestamps, lag ≤ ~1 month vs true
    effective date); precisely-dated changes-table events preferred where present.
  - S&P 400/600 changes tables "measurably incomplete (mostly missing removals)".
  - Delisted-constituent tickers may be upstream-encoded (LEHMQ/WAMUQ patched via renames CSV;
    best-effort).
  - No index weights; no corporate-action provenance; no CIK for S&P 400 (the 400 Wikipedia page
    has no CIK column; 500 and 600 pages do).
- PIT: event dates are upper-bounded for 400/600 → `[PIT UNPROVEN]` for exactness; no announcement
  timestamps.
- License: MIT; underlying data Wikipedia CC BY-SA + fja05680 MIT.
- **NOT authoritative S&P DJI data.** 
- **Decision:** `[CONDITIONAL]` for S&P 500 events (2005+); `[UNVERIFIED]`/INCOMPLETE for S&P 400
  (2011+ only, removal gaps); `[REJECT]`-grade for S&P 600 required depth (2021+ only).

### 9.5 NYU Stern Wurgler file — `https://pages.stern.nyu.edu/~jwurgler/data/sp500%20changes.xls`
- S&P 500 additions 1/1976–12/2000, deletions 1/1979–12/2000, with two event dates (CE1/CE2),
  reason codes, and (~PERMNO) identifiers; free academic supplement (Wurgler 2001).
- S&P 500 ONLY; does not cover 2001+. `[ACCEPT]` as pre-2000 S&P 500 anchor; `[CONDITIONAL]`.

### 9.6 shawnlinxl/snp-history — `https://github.com/shawnlinxl/snp-history`
- S&P 500 addition/removal history 2000–2016 with **announcement AND implementation dates**;
  self-disclosed caveats (tickers PIT; add timing before/after close unverified pre-2017; pre-2000
  missing). S&P 500 only. `[CONDITIONAL]`/`[UNVERIFIED]` as unlicensed single-maintainer dataset.

### 9.7 Other index providers (S&P 400/600 deep history)
- EODHD Historical Constituents and Siblis Research offer 400/600 history → **paid** `[REJECT]`.
- WRDS/CRSP historical membership → **paid subscription** `[REJECT]`.
- `tickerleague.com` S&P 500 changes (1523 records) → unverified third-party `[UNVERIFIED]`.
- No free deep (pre-2011/2021) S&P 400/600 membership source was found. `[VERIFIED absence]`

## 10. S&P 500 FEASIBILITY

- Membership/effective-dates: multiple independent free sources (fja05680 1996+, hanshof,
  pitindex 2005+, Wurgler 1976–2000, Wikipedia). `[VERIFIED]`
- Additions/deletions event identity: reconstructable with effective dates. `[CONDITIONAL]`
- **Announcement timestamps (PIT):** only partial free coverage — shawnlinxl 2000–2016 (caveated);
  official S&P DJI announcement PDFs for demonstrated recent years (2023+, older `[UNVERIFIED]`).
  ⇒ **PIT for the full S&P 500 historical window: `[PIT UNPROVEN]`**; provable only for the years
  whose official announcements are online.
- **Delisted price leg:** not freely available (Yahoo/Stooq/AV gaps) → survivorship issue for
  deletion-event price history; F-1's canonical rule (unavailable forward price ⇒ exclude) partially
  mitigates but materially constrains the deletion leg. `[VERIFIED]`
- **S&P 500 status: `[CONDITIONAL]`** — events feasible for effective-date design in recent
  windows; full-history announcement-PIT and delisted prices are NOT provable free.

## 11. S&P 400 FEASIBILITY

- Free membership: pitindex covers 2011-11-20+; Wikipedia changes table ~2014+; official S&P
  announcement PDFs for recent years. No pre-2011 free source found. `[VERIFIED]`
- Removals: Wikipedia S&P 400 changes table "mostly missing removals" (pitindex DESIGN notes) →
  deletion-leg completeness NOT established. `[VERIFIED]`
- Event dates for revision-derived events are upper bounds (≤1 month lag). `[PIT UNPROVEN]`
- Deep events ~2011–2014 (index year) can only satisfy T_eff=25/leg if event-dates reach ~25+;
  reconstitution events ~4/yr from 2011 → borderline, and removals incomplete ⇒ NOT demonstrable
  from free data. `[UNVERIFIED]`
- **S&P 400 status: `[UNVERIFIED]`** — partial free post-2011 reconstruction only; deletion
  completeness and PIT exactness NOT proven.

## 12. S&P 600 FEASIBILITY

- Free membership: pitindex floor **2021-03-26** only; documented reason = pre-2021 Wikipedia S&P
  600 roster was wrong (~1000 names) and "no free source for its membership exists." `[VERIFIED]`
- Wikipedia S&P 600 changes/deletions completeness: NOT established (same documented gap).
  `[VERIFIED]`
- Post-2021 window = ~21–22 quarterly reconstitutions to 2026-09, i.e. ~20+ event dates at best →
  cannot certify `T_eff ≥ 25/leg` with the required margin; deletion leg weaker still.
  `[UNVERIFIED]`
- **S&P 600 status: `[REJECT]` for the required historical depth** (`[UNVERIFIED]` for the
  constrained 2021+ window). This is the WEAKEST component.

## 13. COMPOSITE 1500 FEASIBILITY

- Composite = union of S&P 500 + 400 + 600 membership with per-sub-index attribution.
- pitindex provides a `sp1500` composite but ONLY from 2021-03-26 (= max(S&P600 floor)); before
  that date the S&P 600 leg does not exist in any free source. `[VERIFIED]`
- Rule followed: **the Composite 1500 conclusion is based on the WEAKEST required component
  (S&P 600).** Do not silently substitute S&P 500.
- **Composite 1500 = `[NOT READY]`** under a `$0` free-first stack for the audited F-1 design.
  It may be **partially constructible (`[CONDITIONAL]`)** for the 2021-03 → present window, subject
  to (a) S&P 600 deletion completeness, (b) announcement-PIT from official PDFs for those years, and
  (c) price availability for survivors. Any such partial window is NOT the frozen F-1 universe depth;
  relaxing the universe is a HUMAN GOVERNANCE DECISION, not an implementation decision (§28).

## 14. PIT AUDIT

The required PIT chain is: what existed → when published → in which timezone → available before T0 →
reproducible later. [FROZEN]

| Input | Free source | PIT on effective date | PIT on announcement time |
|-------|-------------|------------------------|---------------------------|
| Event identity (add/delete) | Wikipedia; pitindex; fja05680 | Partial (effective dates) | NOT present |
| Event announcement timestamp | S&P DJI announcement PDFs (recent years only) | Yes for covered years | Yes (press release date) |
| Prices @ T0 / T0+h | Stooq/AV/Yahoo (active names) | Date-keyed but MUTABLE, no vintage | Opaque release semantics |
| ADV (60d) | Same price sources | Computable but mutation risk | Not PIT-proven |
| Free float | No free PIT free-float source verified | `[UNVERIFIED]` | — |
| Corporate actions | SEC EDGAR (filing-stamped) | Yes (filing ts) | Yes for covered filings |
| HTB / borrow | None free | `[UNVERIFIED]` | — |

- **Conclusion: `[PIT UNPROVEN]`** for the F-1 historical requirement. Effective-dates are
  reconstructable; **announcement/release timestamps are not part of any free structured dataset**;
  only recent years can be anchored to the official S&P DJI press releases. Per the governance hard
  rule (§5), any observation whose PIT cannot be proven must be treated INVALID in a future
  empirical F-1 dataset — restricting free-first research to the announcement-verified window.

## 15. CORPORATE-ACTION AUDIT

- **SEC EDGAR Form 25 / 25-NSE — `https://www.sec.gov` (free):** authoritative delisting
  notifications ("removal from listing and registration", effective ~10 days after filing), filed
  electronically since **May 2006** with filing timestamps (`Accepted` = publication time, ET),
  issuer CIK, CUSIP, exchange. `[FREE-FIRST]` `[ACCEPT for delisting events — PIT by filing]`
  Coverage: delistings only; NO splits/dividends/ex-dates.
- **Splits / dividends / ex-dates:** no free structured consolidated source was verified. Alpha
  Vantage split/dividend history now premium-gated; Stooq embeds adjustment in the close without an
  event record; `businessquant` free corporate-actions endpoint (splits/dividends/IPOs parsed from
  SEC, free tier 30 calls/day) and Alpaca `v1/corporate-actions` (CC-BY-SA-4.0 docs; requires an
  Alpaca account; history retention/certainty of creation times caveated) exist but are
  `[CONDITIONAL]/[UNVERIFIED]` for a cold-storage, archivally reproducible store. `[VERIFIED — no
  free authoritative CA record]`
- **QuantConnect US Equity Security Master** (27,500 equities since Jan 1998; splits, dividends,
  delistings, mergers, ticker changes; map+factor files): usable **within the QC cloud platform**
  for free, but on-premise bulk download costs $600/yr and requires a paid organization tier.
  ⇒ For a `$0` EXTERNAL, archiveable dataset: `[REJECT]`; as platform research: `[CONDITIONAL]`
  `[UNVERIFIED]` for archival/reproducibility.
- **Adjustment methodology:** no free source documents its CA adjustment algorithm end-to-end
  (Stooq/AV opaque) → adjusted-price provenance `[UNVERIFIED]`.
- **Corporate-action layer: `[CONDITIONAL]`** (EDGAR delistings = solid; splits/dividends structured
  free = NOT found).

## 16. DELISTED / SYMBOLOGY AUDIT

- **Delisting EVENTS:** SEC EDGAR Form 25/25-NSE (May 2006+) — authoritative, free, PIT.
  `[ACCEPT]`
- **Delisting PRICES:** effectively NOT free — Yahoo/Stooq/AV serve active names only; community
  Wayback-Machine scrapers exist (github.com/Acelogic/WayBackMachineStockScraper) but are fragile,
  unofficial, and non-contractual → `[CONDITIONAL]`/`[UNVERIFIED]`, reproducibility risk.
- **Ticker changes / identity:** ticker ≠ identity (governance rule). OpenFIGI
  (`https://api.openfigi.com/v3/mapping`, free, MIT/Open Symbology, bulk, rate-limited 25 req/min
  without key) maps ticker/CUSIP/ISIN↔FIGI/other; NOT historical-point-in-time by itself; causal for
  current symbology. `[CONDITIONAL]`
- **CIK (stable issuer id):** SEC `company_tickers.json` / EDGAR submissions — free, stable.
  `[ACCEPT]`
- **Survivorship bias:** present in ALL free price sources (active-name only); current-ticker lists
  cannot reconstruct historical membership (already handled via §9/§10). `[VERIFIED]`
- **Delisted/symbology layer: `[CONDITIONAL]`** — event + identity OK; delisted price history NOT
  freely available.

## 17. CLOSE / T0 SEMANTICS

- F-1 requires `Close(T0)` = official closing price on the effective date (raw ratio, no
  imputation). [FROZEN]
- Free price vendors supply **vendor/EOD close** (Stooq, AV, Yahoo), typically **consolidated
  US/Eastern last/close prints** but NOT certified official closing-auction / SIP-consolidated close;
  adjustment applied to "adjusted close" only; raw close available from Stooq/AV.
- None of the free sources certifies "official exchange close." Any free source used would make
  `Close(T0)` a **documented vendor-EOD substitute** with an acknowledged semantic deviation.
  `[CONDITIONAL]` — acceptable only with an explicit provenance note; `[PIT UNPROVEN]` for
  authoritative close semantics.
- Raw (unadjusted) close per name must be used for the ratio (not the adjusted close) to match the
  frozen definition; split-adjusted columns must NOT be silently substituted. `[FROZEN → audit
  note]`

## 18. PROVENANCE AUDIT

- Best provenance in the free stack: **pinned GitHub commits** (e.g. fja05680/sp500, pitindex, at a
  fixed SHA) + **SEC EDGAR filing records** (immutable accession numbers) + **S&P DJI announcement
  PDFs** (stable URLs) + Wikipedia `oldid` revisions. "Same source / same snapshot" is satisfiable
  for these. `[CONDITIONAL]`
- Stooq / AV / Yahoo are **mutable**; provenance requires an at-retrieval archive (store raw bytes +
  fetch timestamp). Without archiving, provenance is not reconstructable. `[REPRODUCIBILITY RISK]`
- Community-curated datasets are SECONDARY sources (Wikipedia-based reconstruction) whose lineage to
  the official S&P records is indirect → provenance `[UNVERIFIED]` for officiality, `[VERIFIED]`
  for reproducibility.
- **Provenance layer: `[CONDITIONAL]`.**

## 19. REPRODUCIBILITY AUDIT

- Same source+version+transformation+identity: achievable for pinned GitHub/Wikipedia/EDGAR/S&P-PDF
  artifacts by archiving at retrieval. `[CONDITIONAL]`
- Mutable sites (Stooq, AV, Yahoo): no version/snapshot mechanism → document
  `[REPRODUCIBILITY RISK]` unless archived instantly.
- pitindex weekly rebuild + reconciliation gate gives a refreshable but **NOT frozen** dataset;
  must pin a specific release/SHA for research. `[CONDITIONAL]`
- **Reproducibility layer: `[CONDITIONAL]`** — with strict archival discipline for mutable sources.

## 20. LICENSING / TERMS AUDIT

Recorded terms (no legal advice; flag items for human/legal review):
- **Stooq:** personal use only; commercial prohibited; redistribution without consent prohibited;
  S&P/DJ data restricted to personal non-commercial; LME restricted. [VERIFIED terms]
- **Alpha Vantage:** free key w/ 25/day; premium tiers for depth; redistribution per their terms
  (restricted); personal research use stated as free. [VERIFIED pricing/docs]
- **Yahoo / yfinance:** unofficial; Yahoo ToS prohibits bulk download/redistribution previously —
  flag `[UNVERIFIED]/[USE AT RISK]`.
- **Wikipedia:** CC BY-SA 4.0 — derived dataset embedding content requires attribution/share-alike.
  `[CONDITIONAL]`
- **S&P DJI announcements & index data:** S&P licensing governs use; internal research OK; creating
  investment products from index data prohibited without license (Stooq terms echo this). Publishing
  large derived S&P membership datasets → human/legal review REQUIRED.
- **OpenFIGI:** free, MIT/Open Symbology, Apache-2.0 API spec; unrestricted research use. `[ACCEPT]`
- **SEC EDGAR:** public; fair-access rate limits apply; no data redistribution restriction for this
  use. `[ACCEPT]`
- **QuantConnect:** platform-bound free use; on-prem download paid; redistribution restricted.
  `[CONDITIONAL]/[UNVERIFIED]`
- **Licensing layer: `[CONDITIONAL]`** — research use OK for the core free stack; publication of
  derived S&P-related datasets requires human/legal review. `[HUMAN DECISION REQUIRED]`

## 21. COST / ACCESS AUDIT

- `$0` total achieved for: Wikipedia, GitHub (fja05680/pitindex/etc.), SEC EDGAR, OpenFIGI, Stooq
  downloads, AV free key (shallow), S&P DJI announcement PDFs, NYU Wurgler file. `[VERIFIED]`
- $0 does NOT buy: deep AV history (premium), QuantConnect on-prem data ($600/yr), delisted price
  history, S&P 400/600 deep membership, structured CA records, HTB. `[VERIFIED]`
- No account requiring payment was created; no charge incurred; nothing purchased. `[FROZEN]`
- **Cost/access: meets the `$0` budget**; the constraint binds on depth (see decisions).

## 22. SOURCE COMPARISON MATRIX

| Layer | Source | Free? | Coverage | PIT | Provenance | Reproducibility | License | Status |
|-------|--------|-------|----------|-----|------------|-----------------|---------|--------|
| Price/OHLCV | Stooq | Yes (personal use) | US active, 30+yr daily | Mutable, no vintage | Vendor | Archiving required | Personal-only, no redistribution | `[CONDITIONAL]` |
| Price/OHLCV | Alpha Vantage | Free tier only (25/day) | active names, **full history = premium** | Mutable | Licensed vendor (NASD/S&P DJI/…) | Archiving required | Registered use | `[CONDITIONAL]` (shallow) / `[REJECT]` (deep) |
| Price/OHLCV | Yahoo (unofficial) | Free unofficial | active names, delisted absent | Mutable | Vendor | Archiving required | ToS risk | `[CONDITIONAL]` |
| Index events | S&P DJI announcement PDFs | Yes | recent years (2023/2026 verified) | Announcement+effective for covered | Primary official | Stable URLs | S&P license; publication review | `[CONDITIONAL]` |
| Index events | Wikipedia changes tables | Yes (CC BY-SA) | ~2014+; deletions incomplete (400/600) | Effective date only | Secondary | oldid pinning | CC BY-SA 4.0 | `[CONDITIONAL]` |
| Index events | fja05680/sp500 | Yes (MIT) | S&P 500 1996+ daily | Effective-date diffs | Community (Clenow+Wiki) | Commit pinning | MIT | `[CONDITIONAL]` |
| Index events | pitindex | Yes (MIT) | S&P500 2005+; S&P400 2011-11+; S&P600 2021-03+ | Upper-bound event dates; no announcements | Community/Wikipedia | Release pinning | MIT + CC BY-SA | `[CONDITIONAL]` (500) `[UNVERIFIED]` (400) `[REJECT]`-grade (600) |
| Index events | NYU Wurgler | Yes | S&P500 add 1976–2000, del 1979–2000 | Two event dates | Academic | Static xls | Academic | `[ACCEPT]`/`[CONDITIONAL]` |
| Index events | EODHD / Siblis | No | 400/600 history | — | — | — | Paid | `[REJECT]` |
| Index events | WRDS | No (sub) | 400/600 history | — | — | — | Paid | `[REJECT]` |
| CA/delist | SEC EDGAR Form 25/25-NSE | Yes | delistings May 2006+ | Filing timestamp | Primary | Accession numbers | Public/fair-access | `[ACCEPT]` |
| CA(splits/div) | Structured free record | — | NOT FOUND | — | — | — | — | `[UNVERIFIED]`/`[REJECT]` |
| CA/security-master | QuantConnect | Platform-free; on-prem paid | 1998+, 27.5k eq | Events; Timestamps | Vendor | Platform-bound | QC license | `[CONDITIONAL]`/`[UNVERIFIED]` |
| Symbology | OpenFIGI | Yes | current mapping | Not historical | Open Symbology | API | MIT/Apache | `[CONDITIONAL]` |
| Symbology | SEC CIK files | Yes | stable issuer ids | Yes | Primary | Versioned | Public | `[ACCEPT]` |

## 23. S&P 500 / 400 / 600 FEASIBILITY MATRIX (mandatory)

| Index | Historical Membership | Additions | Deletions | Effective Date | Announcement Time | PIT | Free Source | Status |
|-------|------------------------|-----------|-----------|----------------|--------------------|-----|-------------|--------|
| S&P 500 | 1996+ (fja/pitindex), 1976–2000 (Wurgler) | Yes (reconstructed) | Yes (reconstructed) | Yes | Partial (2000–2016 shawnlinxl; recent S&P PDFs; deep `[UNVERIFIED]`) | `[PIT UNPROVEN]` (deep) | GitHub/Wikipedia/S&P PDFs/Wurgler | `[CONDITIONAL]` |
| S&P 400 | 2011-11+ only (pitindex); pre-2011 NONE free | Partial | Partial (removals gap) | Upper-bound dates | None in free data | `[PIT UNPROVEN]` | pitindex/Wikipedia/S&P PDFs (recent) | `[UNVERIFIED]` |
| S&P 600 | 2021-03+ only (pitindex); pre-2021 rosters corrupt/no source | Partial | Partial (removals gap) | Upper-bound dates | None in free data | `[PIT UNPROVEN]` | pitindex/S&P PDFs (recent) | `[UNVERIFIED]` (constrained window); `[REJECT]` (required depth) |
| S&P 1500 composite | = max(S&P 500, 400, 600 floors) = **2021-03-26** | — | — | — | — | `[PIT UNPROVEN]` | pitindex `sp1500` | **`[NOT READY]`** (weakest component: S&P 600) |

## 24. FREE-STACK ARCHITECTURE PROPOSAL `[FREE-FIRST]`

Only what the audit could verify — a **constrained-window** architecture (NOT the frozen full-depth
universe; see §28):

1. **Events (as-announced):** S&P DJI announcement PDFs for every covered quarterly change
   (archive the URL + PDF at retrieval; parse effective date, additions, deletions, GICS). Validate
   against Wikipedia change tables and pitindex event diffs.
2. **Membership floor:** pitindex (`sp500`/`sp400`/`sp600`) pinned at a release SHA; cross-check
   roster against Wikipedia `oldid` snapshots; record the ≥5% reconcile-gate output as provenance.
3. **Prices (active names):** Stooq daily OHLCV raw close + volume (personal-use license, archive
   on retrieval); supplement ADV via same source; do NOT rely on AV full history (premium-gated) or
   Yahoo (ToS risk). Document vendor-EOD close semantics (§17).
4. **Delisting events:** SEC EDGAR Form 25/25-NSE (May 2006+) via accession numbers.
5. **Identity:** CIK from SEC `company_tickers.json`; FIGI/CUSIP mapping via OpenFIGI; ticker ≠
   identity everywhere.
6. **Store:** archive raw artifacts + fetch timestamps; pin commits; write a provenance manifest
   (source URL, retrieved-at, version/sha, transformation) per artifact — matching the ACASH
   canonical provenance/`DataContractError` discipline from `AGENTS.md`.
7. **Explicit boundary:** this architecture is `[FEASIBILITY-ONLY]` `[NON-NORMATIVE]`. It is NOT
   approved for R1, does NOT change gate thresholds or the frozen spec, and would still require
   human authorization to be executed.

### FUTURE PAID DATA PATH — `NOT AUTHORIZED` (clearly separated)
- Missing capabilities under $0: S&P 400/600 deep (pre-2011/pre-2021) membership; announcement-PIT
  for deep history; delisted-name price history; structured split/dividend CA records; HTB/short
  availability; certified official close; free-float PIT.
- Providers that could address them (identified only, NO purchase, NO access implied, NO influence
  on this audit's findings): S&P DJI licensing (official membership/close files), CRSP, Compustat,
  Databento/Norgate/EODHD for survivorship-free prices, Sharadar/Nasdaq Data Link for PIT
  fundamentals/floats, AlgoSeek via QuantConnect for full SIP history.
- This section is informational only and does NOT authorize spending. `[NOT AUTHORIZED]`

## 25. ACCEPT / CONDITIONAL / UNVERIFIED / REJECT DECISIONS (per layer)

- **PRICE / OHLCV** = `[CONDITIONAL]` (active names, free; delisted prices not free; vendor-close)
- **INDEX EVENTS** = `[UNVERIFIED]` (effective-dates yes recent; deletions + announcement-PIT no)
- **S&P 500** = `[CONDITIONAL]`
- **S&P 400** = `[UNVERIFIED]` (2011+ partial only)
- **S&P 600** = `[UNVERIFIED]` for 2021+ constrained window; `[REJECT]` for required depth
- **S&P 1500 COMPOSITE** = **`[NOT READY]`** (weakest required component)
- **CORPORATE ACTIONS** = `[CONDITIONAL]` (EDGAR delistings `[ACCEPT]`; splits/dividends free
  structured `[REJECT]/[UNVERIFIED]`)
- **PIT** = `[UNVERIFIED]` (announcement timestamps not freely available for the F-1 history;
  `[PIT PROVEN]` only for announcement-PDF-covered recent years)
- **PROVENANCE** = `[CONDITIONAL]` (pinned commits + EDGAR accession + archived PDFs)
- **REPRODUCIBILITY** = `[CONDITIONAL]` (mutable sources ⇒ archive-at-retrieval discipline)
- **LICENSING** = `[CONDITIONAL]` (research OK; publication/redistribution review required)
- **COST / ACCESS** = `[ACCEPT]` within `$0` (no paid service purchased; none authorized)

## 26. KNOWN LIMITATIONS

1. S&P 600 free membership does not exist before 2021-03-26 (documented, pitindex). [VERIFIED]
2. S&P 400 free membership does not exist before 2011-11-20. [VERIFIED]
3. No free dataset stores announcement/release timestamps for reconstitution events historically;
   only recent-year official S&P DJI press releases do. [VERIFIED]
4. Delisted-name daily PRICES are not freely available from any API audited. [VERIFIED]
5. Free sources are mutable and lack official vintages; all free prices/events require archival at
   retrieval. [VERIFIED]
6. S&P 400/600 Wikipedia change tables are incomplete, especially for removals. [VERIFIED via
   pitindex DESIGN notes]
7. No structured free split/dividend/ex-date history was verified; adjustment algorithms are
   opaque in free vendors. [VERIFIED absence]
8. Free-float PIT and HTB/short availability are not freely available; ADV uses vendor volume
   (mutable). [VERIFIED absence]
9. Nothing here verifies OFFICIAL consolidated close semantics. [VERIFIED]
10. Community-curated free sources are secondary reconstructions, not S&P DJI authoritative
    records. [VERIFIED]

## 27. BLOCKING ISSUES

1. **S&P 600 (and 400) deep membership absent** → Composite 1500 impossible at the frozen universe
   depth for free. [BLOCKING]
2. **Announcement-time PIT not provable** for the F-1 historical window (hard-rule ⇒ such
   observations are INVALID for a future empirical dataset). [BLOCKING]
3. **Delisted-price history not free** → deletion-leg price coverage gap. [BLOCKING]
4. **No free structured split/dividend CA record** for the PIT CA ordering requirement.
   [BLOCKING]
5. **Free-float PIT / HTB** inputs unavailable free. [BLOCKING]
6. **Licensing of S&P-derived redistribution** requires human/legal review before any public
   derived release. [HUMAN]

## 28. HUMAN DECISIONS REQUIRED

1. F-1 D1 overall verdict: `NOT READY` (recommended) vs. a constrained research window.
2. Whether to constrain the audited Free-First window to years with verifiable announcement-PIT
   (e.g. recent years with S&P DJI PDFs) — a SPECIFICATION/universe change that only the human can
   ratify (governance rule: never downgrade the standard to fit free data; never switch Composite
   1500→S&P 500).
3. Acceptance of vendor-EOD close semantics as the documented `Close(T0)` substitute.
4. Licensing/legal review (S&P DJI, Stooq, Wikipedia CC BY-SA) before any data construction or
   publication.
5. Whether to authorize archive-at-retrieval engineering (provenance manifest) at $0.
6. ReInceptionGate: human re-assessment of F-1 readiness AFTER data decisions are made.
   All of the above are `[HUMAN DECISION REQUIRED]` — none are taken by this audit. [NON-NORMATIVE]

## 29. FINAL D1 STATUS

**F-1 D1 (FREE-FIRST DATA FEASIBILITY AUDIT) = `NOT READY`** for the frozen F-1 research design at
`$0`.

- Verifiable free-first research is limited to a **recent, announcement-PIT-verifiable window** on a
  **partial universe** (S&P 500 full; S&P 400 ≈2011+; S&P 600 only 2021+). That does not meet the
  frozen Composite 1500 requirement, and narrowing the design (event/universe/PIT/cost/grid) is
  reserved to the human — never an implementation choice.
- Repo state before/after: `git status --short` shows only untracked documentation
  (`f1_d1_free_data_feasibility.md`, plus the previously created candidate review doc). No tracked
  files modified; no commit; no push; no `src/`/schema/gate/ROADMAP/registry change. [VERIFIED]
- Verification checklist (§21 of the task):
  - HYP_003 created: **NO** · ReInceptionGate invoked: **NO** · R1 started: **NO**
  - No empirical F-1 performance result produced: **NO results** (zero return/alpha/IC/HAC/profit
    numbers in this document) · No paid service purchased: **NONE** · No trading state changed:
    **NONE** · Unsupported PIT claim used: **NO** (all `[PIT PROVEN]` claims restricted to the
    announcement-PDF-covered years; global claim is `[PIT UNPROVEN]`) · Intended documentation only:
    **VERIFIED**.

## 30. GOVERNANCE STOP BOUNDARY

- This audit created **NO** HYP_003, **NO** R1, **NO** gate invocation, **NO** trading
  authorization, **NO** empirical result. F-1 remains a RESEARCH CANDIDATE
  (`CAND-FLOW-CALENDAR-REBALANCE-001`); Trading remains **LOCKED**; Capital remains `$0.00`.
- The next valid step is a HUMAN D1 decision on whether/where free-first research is acceptable,
  followed by (if ratified) a data-engineering feasibility build with provenance manifests — both
  still outside HYP_003/R1 gate authority.
- All `[FROZEN]`/`[PROPOSED]` F-1 specifications referenced here are audit inputs, NOT modified by
  this document. [NON-NORMATIVE]

---

### Verification Ledger (this audit)
- Implementation Status: NONE (documentation-only; `src/` untouched; zero code change).
- Contract Enforcement: STRICT FAIL-CLOSED — every unverifiable claim is `[UNVERIFIED]`; no
  fabricated vendor/API/coverage/PIT/license; no promoted external claim.
- Mathematical Authority: N/A for data feasibility; canonical gate floors untouched.
- Local Test Suite: NOT RUN (no code changed — documentation-only convention).
- Remote CI Status: NOT AVAILABLE.
- Methodological Caveats: retrieval date 2026-09-10; free-source coverage/licensing may change;
  the ~2021+ / 2011+ coverage floors and the S&P-announcement archive depth are the binding limits;
  F-1 D1 = NOT READY at $0 for the frozen Composite 1500 design.