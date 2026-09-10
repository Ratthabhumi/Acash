# ACASH V5 — F-1 D1 BLOCKER RESOLUTION RESEARCH

**Document ID:** `docs/phase14/f1_d1_blocker_resolution.md`
**Object:** F-1 `CAND-FLOW-CALENDAR-REBALANCE-001` — targeted re-audit of the six D1 data blockers under a strict `$0` budget
**Status:** `[FEASIBILITY-ONLY]` · `[NON-NORMATIVE]` · `[NOT HYP_003]` · `[NOT R1]` · `[NOT D2]`
**Date:** 2026-09-10 (retrieval date for every web/archive file evidence below)
**Predecessor:** `docs/phase14/f1_d1_free_data_feasibility.md` (D1 = `NOT READY`; human decision OPTION A — RETAIN COMPOSITE 1500)
**Git policy:** created file stays UNTRACKED; NO `git add/commit/push/fetch/pull/merge/rebase/reset/revert/stash`. [VERIFIED at the end]

**Classification labels:** `[FREE-FIRST]` `[FEASIBILITY-ONLY]` `[NON-NORMATIVE]` `[NOT HYP_003]` `[NOT R1]` `[NOT D2]`
`[PIT PROVEN]` `[PIT UNPROVEN]` `[ACCEPT]` `[CONDITIONAL]` `[UNVERIFIED]` `[NOT SUFFICIENT AT $0]` `[REJECT]`
**Statement classes:** `V` = verified directly in this audit · `R` = reported/source claim · `I` = inference · `P` = proposal · `NP` = not proven.

---

## 1. EXECUTIVE CONCLUSION

This audit re-ran every one of the six D1 blockers against the free/public layer with new primary
evidence (Wayback Machine CDX index audit, S&P DJI press archives, SEC EDGAR fund-holdings filings,
free CA endpoints, S&P U.S. Indices Methodology). The result is a **partial, evidence-backed upgrade**
of the *blocker set*, NOT an upgrade of the D1 verdict:

- **B1 (S&P 600 historical membership):** upgraded from "NO free source pre-2021" to
  `CONDITIONAL` for a **2013+ window** — quarterly reconstitution announcements for the 500/400/600
  family are archived in the Wayback Machine from 2013-12-11 onward (`[V]`), and full-roster member
  snapshots are reconstructable from SEC fund-holdings filings (N-PORT/N-CSR, `[V]` for the filing
  series) and from archived S&P DJI index pages (2012+, `[V]` presence). Completeness of any
  reconstructed roster remains `[UNVERIFIED]` until validated against the entire announcement corpus.
- **B3 (announcement PIT):** upgraded from "not in any free dataset" to `CONDITIONAL` for
  ~2012/2013+ — dated reconstitution press releases and announcement PDFs are free-accessible
  (`[V]` for recent years, PRNewswire/press.spglobal.com; `[V]` Wayback presence 2013–2022).
  `T_announcement < T_effective` is structurally satisfied for archived quarterly releases.
- **B2 (delisted prices), B4 (structured splits/dividends), B5 (free-float PIT), B6 (license of the
  new free-era sources):** **NOT resolved** under `$0`. Only partial/conditional/unverified
  candidates exist (Kaggle delisted archive — license `[UNVERIFIED]`; securitiesdb free
  CA endpoint — `[CONDITIONAL]/[UNVERIFIED]`; EDGAR Form 25 delistings — `[ACCEPT]`).

**FINAL RECOMMENDATION (unchanged):** F-1 D1 remains **`NOT READY`** for the frozen full-depth
Composite 1500 research design at `$0`. The audit does narrow the feasible region: a
**`2013+ quarterly-reconstitution window on the full Composite 1500`** is now `CONDITIONAL`-feasible
at `$0`, subject to the remaining conditions in §13. Whether to accept any constrained window is a
**HUMAN GOVERNANCE OPTION ONLY** (§14). No universe is downgraded, no decision is taken here, nothing
is implemented. [NON-NORMATIVE] [NOT HYP_003] [NOT R1] [NOT D2]

---

## 2. FROZEN F-1 SCOPE (AUDIT INPUTS, NOT MODIFIED)

- **Candidate:** `CAND-FLOW-CALENDAR-REBALANCE-001`. [FROZEN]
- **Universe:** S&P Composite 1500 = S&P 500 + S&P MidCap 400 + S&P SmallCap 600. [FROZEN]
- **Universe filters (PIT):** ADV ≥ US$5M/day; Free Float ≥ 20%. [FROZEN at rule/numeric level
  for the candidate — see methodology-vs-proxy note in §8]
- **Events:** INDEX RECONSTITUTION ONLY; Addition = +1, Deletion = −1; composite
  `FLOW = ΣAdd − ΣDel`; anchor = effective date T0. [FROZEN]
- **Returns:** `R(h) = Close(T0+h)/Close(T0) − 1`, h ∈ {1,5,10}, primary 5. [FROZEN]
- **Minimum sample:** `T_eff ≥ 25` per composite leg; `N_valid ≥ 250` active. [FROZEN]
- **PIT hard rule:** observation with unproven PIT = INVALID for a future empirical F-1 dataset.
  [FROZEN]
- **Budget:** DATA COST = `$0.00`. No paid subscription, no payment data, no vendor free-trials that
  require payment, no paid previews counted as usable history. [FROZEN]
- Human decision on D1 = **OPTION A — RETAIN COMPOSITE 1500** (`NOT READY` / `CONDITIONAL`). [FROZEN]

This document does NOT change F-1, create F-1-Free, create HYP_003, advance D2, invoke any gate,
or start R1. [FROZEN — all]

---

## 3. CURRENT D1 BLOCKERS (RECAP FROM PREDECESSOR AUDIT)

| # | Blocker (D1 wording) | Predecessor D1 status |
|---|----------------------|------------------------|
| B1 | S&P 600 historical constituents (pre-2021 absent) | `[REJECT]`-grade for required depth; `[UNVERIFIED]` constrained window |
| B2 | Historical delisted OHLCV prices | `[NOT SUFFICIENT AT $0]` (only metadata: EDGAR Form 25 / AV LISTING_STATUS) |
| B3 | Announcement-time PIT (T_announcement < T_effective) | `[PIT UNPROVEN]` except verified recent PDFs |
| B4 | Structured corporate actions (splits/dividends/ex-dates) | `[CONDITIONAL]` (Form 25 solid; free structured splits/dividends NOT found) |
| B5 | Free-float PIT + ADV PIT for universe filter | `[UNVERIFIED]` (free-float history not free) |
| B6 | Provenance / license / reproducibility | `[CONDITIONAL]` (pinning possible; publication review needed) |

---

## 4. B1 — S&P 600 HISTORICAL CONSTITUENTS

### 4.1 New primary evidence — Wayback Machine CDX audit of the S&P DJI announcement corpus

`http://web.archive.org/cdx/search/cdx?url=spglobal.com/spdji/en/documents/indexnews/announcements*`
(collapse=urlkey, statuscode 200, 2026-09-10). Of 1,500 sampled unique archived URLs: [V]

- Content-date subfolders span **2013-04-16 → 2022-08-04** (688 distinct content dates in sample).
  Missing/beyond-sample coverage is `[UNVERIFIED]` — the CDX query this audit ran is a floor, not a
  ceiling. [V with bound]
- **Quarterly reconstitution documents are present and named** (`shuf` ×11 URL strings, `migra` ×6;
  also `migrshuf`, `shuffle`): e.g. `20131211/67155_fbshuf252426100.pdf`,
  `20190906-989159/989159_finalmigrasept10ad69ad43mig642discr47discr6outsid6to4outsid3to6.pdf`,
  `20200612-1163959/1163959_june2020migrshuf.pdf`,
  `20210312-1336360/1336360_march2021-5146-shuf-pr.pdf`,
  `202106?`/`20210903-1443045/1443045_sept2021-546-shuf-rebal.pdf`,
  `20211203-1445690/1445690_5shuffle64pr.pdf`, `20220603-1453030/1453030_shufcernjune2022-546.pdf`.
  [V — URL/presence level; per-document content NOT individually verified in this audit]
- Content of the equivalent quarterly press PDFs was verified in the predecessor audit for
  2023-06-02 (`1464356_shufjun23.pdf`) and 2026-06-05 (`1483743_shuffle546-june2026.pdf`):
  announcement date + effective date + additions/deletions + ticker + GICS for the 500/400/600
  family. [V — predecessor]
- **Conclusion for deltas:** additions **and** deletions of the S&P 500/400/600 at each quarterly
  reconstitution are reconstructable (in principle) from free archived announcements for
  **2013-12 → present**, subject to corpus completeness (see §4.4). [CONDITIONAL]

### 4.2 Full-roster snapshot paths

- **Archived S&P DJI index pages for S&P 600 exist since 2012:** `us.spindices.com/indices/equity/sp-600`
  snapshot 2012-09-17, continuing through the `spglobal.com/spdji/en/indices/equity/sp-600`
  series (2020+ snapshots verified). [V — CDX presence; page content/roster-column availability
  `[UNVERIFIED]` per snapshot]
- **Live current roster is public:** the S&P 600 index page exposes a "Full Constituents List"
  today. [V]
- **NEW — SEC EDGAR fund-holdings filings as PIT roster snapshots:** the registrant **iShares
  Trust (CIK 0001100663)**, house of the S&P SmallCap 600 index ETF (IJR), files **Form N-PORT**
  ("Monthly Portfolio Investments Report", complete portfolio schedules, filing-date PIT
  `[ACCEPT]` semantics by EDGAR timestamp). Multiple NPORT-P filings verified (filed 2026-08-27;
  file number 811-09729). [V] Pre-2019 the equivalent complete schedules were filed via N-CSR/N-Q
  (series existence `[V]` for the regulatory regime; per-fund depth `[UNVERIFIED]` in this audit).
  Cross-fund candidates: iShares IJR, SSGA SLY (SPDR Series Trust), Vanguard VIOO. [R/I — fund
  mapping]
- **Caveats (not resolved):** fund holdings ≠ index membership (up to small tracking deviations,
  occasional defensive exclusions/cash, different share-class/liquidly policy); N-PORT is filed with
  up to ~60 days after quarter end (holdings as of quarter-end date, not publication); roster must
  be union-validated against the quarterly announcement deltas; SPDR/Vanguard registrants were not
  independently re-verified here. [UNVERIFIED — validation burden real]

### 4.3 Earlier free sources (unchanged status)

- pitindex (`github.com/arielNacamulli/pitindex`, MIT): `sp600` floor 2021-03-26; pre-2021
  Wikipedia roster corrupt (~1,000-name list) and "no free source for its membership exists"
  (self-disclosed). [R — verified DOCUMENTED]
- Wikipedia S&P 600 changes tables ~2014+, deletions reported incomplete. [R]
- `fja05680/sp500` covers S&P 500 only. [V]

### 4.4 B1 decision

- **S&P 600 membership (full roster + deltas): `CONDITIONAL` for 2013+** — announcement corpus
  (Wayback) + fund-holdings rosters (EDGAR) + page snapshots (Wayback), all `$0`.
- **Pre-2013 S&P 600 membership: `UNVERIFIED` at `$0`** — no verified free source; nothing below
  is inferred to exist.
- Completeness of any reconstruction is a **material, testable condition** (reconcile every
  archived quarterly + every single-company "migr" document against the roster series; flag any
  gap). Until that reconciliation is executed, completeness = `[UNVERIFIED]`, therefore per the
  PIT hard rule such observations are not yet research-eligible. [FROZEN — PIT hard rule]

---

## 5. B2 — HISTORICAL DELISTED PRICES

Candidates audited at `$0` (2026-09-10):

| Source | Evidence | Classification |
|--------|----------|----------------|
| **Kaggle "Arandkei: Historical Delisted Assets Archive"** (`kaggle.com/datasets/rodas86/arandkei-historical-delisted-assets-archive`) | Free Kaggle download; daily OHLCV for delisted assets; created 2026-02-19, updated 2026-03-08 [V — public page/mirror]. License **NOT stated on any verified surface** [UNVERIFIED]; coverage/completeness of delisted universe [UNVERIFIED]; created 2026 so deep pre-2000 coverage [UNVERIFIED]. Version pinning possible on Kaggle [CONDITIONAL]. | `CONDITIONAL` / `UNVERIFIED` — **not an ACCEPT** |
| **`github.com/tenicho/data-cleaning`** (survivorship-clean US equity panel) | Self-disclosed: delistings concentrated 2021–2026; deaths before ~2016 largely absent → panel is materially incomplete exactly where F-1 needs deletion-leg history. [R] | `NOT SUFFICIENT AT $0` (for the F-1 requirement) |
| **historicaldata.net** | Claims "including active and delisted securities"; free = sample only; full = paid subscription. [R] | `NOT SUFFICIENT AT $0` |
| **Financial Modeling Prep free API** | Blog claims free delisted-company handling; free tier depth/endpoint availability at `$0` not verified. [R] | `UNVERIFIED` |
| **Wayback-based stock scrapers** (`github.com/Acelogic/WayBackMachineStockScraper`) | Archival scraping of old Yahoo quote history for delisted names; unofficial, non-contractual, fragile, no license. | `CONDITIONAL` / `UNVERIFIED` |
| **Alpha Vantage `LISTING_STATUS&state=delisted`** | Free CSV: delisted **roster metadata** (ipoDate/delistingDate), **no OHLCV**. [V — predecessor] | `[ACCEPT]` metadata only; prices `[NOT SUFFICIENT AT $0]` |
| **SEC EDGAR Form 25/25-NSE** | Delisting **events** with filing timestamps, May 2006+. No prices. [V — predecessor] | `[ACCEPT]` events only |
| EODHD / Sharadar / Norgate / CRSP / QuantConnect+AlgoSeek (incl. "the entire US stock market including delisted" products) | All require payment for the delisted-history product. [V — vendor pages] | `[REJECT]` at `$0` |

- **Active vs delisted vs dead vs renamed:** free OHLCV is essentially limited to active names;
  delisted/renamed series are not certifiably available. Symbol continuity must come from
  OpenFIGI/EDGAR identity mapping — identities yes, prices no. [V]
- **Survivorship-bias risk:** remains in every `$0` price source; current-ticker availability is
  NOT evidence of historical delisted coverage. [V]

**B2 decision: `NOT SUFFICIENT AT $0` for a certified delisted-price history.** The only free
candidates that move the needle even conditionally are the Kaggle archive (license unverified) and
Wayback scraping (fragile). F-1's canonical "unavailable forward price ⇒ exclude" rule genuinely
mitigates part of the deletion-leg T0+h gap, but it does NOT certify the deletion-leg coverage the
frozen design otherwise assumes. [CONDITIONAL mitigation]

---

## 6. B3 — POINT-IN-TIME ANNOUNCEMENT DATA

### 6.1 Quarterly reconstitution — now free and dated

- **PRNewswire + S&P Global press archive.** Quarterly releases of the form *"…Set to Join
  S&P 500; Others to Join S&P 100, S&P MidCap 400 and S&P SmallCap 600, effective prior to the open
  of trading …, to coincide with the quarterly rebalance"* are confirmed, free, and dated:
  - 2023-09-01 (`press.spglobal.com/2023-09-01-Blackstone-and-Airbnb-Set-to-Join-S-P-500-…`) [V]
  - 2026-09-04 (`prnewswire.com/news-releases/bloom-energy-illumina-and-everpure-set-to-join-sp-500-…-302870517.html`) [V]
  - Multiple smaller additions: "Tenable Holdings Set to Join S&P SmallCap 600" 2026-08-26;
    "Ferguson Enterprises Set to Join S&P 500 and ADI Global Distribution to Join S&P SmallCap 600"
    2026-07-31; "Molina Healthcare Set to Join S&P MidCap 400 and Construction Partners to Join S&P
    SmallCap 600" 2026-07-16 [V — press.spglobal.com archive]
  - `press.spglobal.com` news archive exposes a year filter **2012–2026** for S&P DJI releases. [V —
    page presence; per-year completeness of S&P DJI membership releases `[UNVERIFIED]`]
- **Announcement PDFs (as-announced, authoritative semantics):** live for recent years (2023/2026
  verified in predecessor) and Wayback-archived for **2013-12 → 2022-06** (`shuf`/`migr`/`migrshuf`
  corpus, §4.1). Each such document contains announcement date + effective date + the change list. [V
  for presence; content verified on 2023 & 2026 samples]
- **PIT property:** for the archived/citable releases, `T_announcement < T_effective` is satisfied
  and both are recorded on the primary document → **`[PIT PROVEN]` for each such event**, at the
  cost of per-event archival verification. [V-derived for samples / `[UNVERIFIED]` per-archive-wide]

### 6.2 What is NOT resolved

- Deep-history (pre-2012/2013) announcement timestamps: `[PIT UNPROVEN]`.
- A complete, machine-readable event calendar does not exist free; reconstructing one requires
  parsing hundreds of PDFs/press pages and reconciling duplicates (press page + PDF + PRNewswire
  mirror). Completeness of that corpus `[UNVERIFIED]` until executed.
- Effective-date-only sources (Wikipedia tables, pitindex revision-diffs) remain `[PIT UNPROVEN]`
  for announcement timing — unchanged. [V — predecessor]

### 6.3 B3 decision

- **Announcement PIT: `CONDITIONAL` for the ~2012/2013+ window**; `[PIT PROVEN]` per-event once the
  responsible announcement artifact is archived and timestamped; `[PIT UNPROVEN]` for the full F-1
  historical depth (pre-2013). Upgrade vs. predecessor audit: **genuine, evidence-backed.**

---

## 7. B4 — CORPORATE ACTIONS

- **Delistings — SEC EDGAR Form 25 / 25-NSE (May 2006+):** authoritative, free, filing-stamped.
  Unchanged `[ACCEPT]`. [V — predecessor]
- **NEW — securitiesdb.com free Dividend/Split API**
  (`securitiesdb.com/developers/dividend-api`): `GET …/api/v1/stocks/{ticker}/dividends` → dividends
  array (`ex_date`, `amount`, `type`) and `splits[]` (`date`, `ratio`); no API key; "Data last
  updated 6/11/2026"; terms state data aggregated from public filings + third-party feeds, provided
  "as-is", may be delayed/inaccurate, and the endpoint may be "rate-limited, changed, or
  discontinued at any time". [V — endpoint + terms verified]. Historical depth/completeness, symbol
  coverage (incl. delisted), and adjustment semantics `[UNVERIFIED]`. | `CONDITIONAL` / `UNVERIFIED`
  for a cold-storage CA store
- **EODHD splits/dividends API free plan:** free tier limited to **~1 year** of dividend history —
  `[NOT SUFFICIENT AT $0]` for deep history. [R — vendor docs verified]
- **Tiingo splits & dividends:** free tier existence/limits in 2026 `[UNVERIFIED]`; would require a
  billing-able account. `[UNVERIFIED]/[CONDITIONAL]`
- **stockanalysis.com / per-fund dividend pages:** free to view; scraping terms unverified,
  mutable. `[UNVERIFIED]`
- Zacks, FirstRate, FactSet pages, CRSP/Compustat: paid `[REJECT]`.
- **Adjustment algorithm provenance:** still opaque across free vendors. `[UNVERIFIED]` (unchanged)

**B4 decision: `CONDITIONAL`** — delisting/identity events solid (EDGAR); structured free
split/dividend history now has free candidates (securitiesdb) but none certified for coverage,
depth, license, or adjustment provenance. The PIT CA-ordering requirement of the frozen
methodology is **NOT** satisfied to the archiveable-evidence standard. [NOT RESOLVED]

---

## 8. B5 — FREE FLOAT + ADV (UNIVERSE FILTER)

### 8.1 Methodology fact vs. frozen proxy (recorded, not changed) [V]

The frozen F-1 filter (PIT `ADV ≥ $5M/day` and `Free Float ≥ 20%`) is the candidate's **research
proxy**, not the S&P DJI rule. Per the free, public **"S&P U.S. Indices Methodology"** (July 2026,
`spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf`):

- **IWF (float):** S&P Composite 1500 current constituents must maintain **IWF ≥ 0.1** (weighted
  average across class lines); additions must clear **float-adjusted market cap (FMC)** thresholds —
  i.e. "free float ≥ 20%" residential proxy is not the actual IWF gate. [V]
- **Liquidity:** **FALR ≥ 0.1**, where FALR = annual dollar value traded / FMC, computed with
  **composite pricing** and consolidated volume over the 365 calendar days before the evaluation
  date (evaluation date = open two business days prior to announcement date). Not "60-day ADV". [V]
- Historical snapshots of the methodology agreed (2013 spice-hosted version: FALR ≥ 1.00 plus a
  250k-share/6-month test) — i.e. the rule itself changed over time, so *any* proxy must be pinned
  to a vintage. [R — archived methodology PDF, `spice-indices.com/…/methodology-sp-us-indices_20120228.pdf`]

### 8.2 Reproducibility of the frozen filters at $0

- **ADV (60-day, my proxy):** computable from free daily volume for **active** names; volume =
  vendor-consolidated, mutable, delisted names absent → `[CONDITIONAL]` (active) / `[NOT SUFFICIENT]`
  (deletion leg, see B2).
- **Free float history (IWF):** requires historical share-class IWF / float-adjusted shares → **no
  free historical float dataset exists**. SEC filings provide total shares outstanding (PIT), but
  float ≠ outstanding (closely-held/control-block exclusions require ownership data not freely
  available historically). `FREE_FLOAT_PIT = UNVERIFIED` (unchanged). Do NOT substitute current
  float for historical float. [V — absence]

**B5 decision: `FREE_FLOAT_PIT = UNVERIFIED`; ADV-proxy = `CONDITIONAL` (active names only).**
The frozen filters cannot be PIT-certified at `$0`; additionally, their numerical binding is a
proxy that does not match the S&P DJI rule — flag for human ratification (this document does NOT
change the frozen filters). [HUMAN DECISION REQUIRED]

---

## 9. B6 — PROVENANCE / LICENSE / REPRODUCIBILITY

Per-source provenance/license on the newly-admitted free candidates (2026-09-10):

- **S&P DJI announcement PDFs (live + Wayback):** stable URLs + Wayback capture timestamps
  (CDX) give reproducible artifacts; content © S&P DJI; research use normal, redistribution of
  derived S&P-related datasets requires human/legal review. `[CONDITIONAL]`
- **press.spglobal.com / PRNewswire press releases:** stable URL slugs, dated; PRNewswire ToS +
  S&P attribution required; bulk harvesting terms `[UNVERIFIED]`; redistribution review needed.
  `[CONDITIONAL]`
- **SEC EDGAR (Form 25, N-PORT/N-CSR, company_tickers):** public, immutable accession numbers,
  fair-access rate limits, no redistribution restriction for this use. `[ACCEPT]`
- **securitiesdb.com:** terms = "as-is, no warranty, may change/discontinue, third-party inputs,
  user must comply with upstream terms" → reproducibility NOT guaranteed; license of underlying
  data `[UNVERIFIED]`. `[UNVERIFIED]`
- **Kaggle Arandkei delisted archive:** free download, version-pinnable on Kaggle, but dataset
  license not stated on verified surfaces. `[UNVERIFIED]`
- **pitindex / fja05680 / Wikipedia changes tables / NYU Wurgler:** MIT / MIT / CC BY-SA 4.0 /
  academic — pinnable via commit SHA / `oldid`. `[ACCEPT]/[CONDITIONAL]` (unchanged)
- **OpenFIGI, SEC CIK identity:** MIT/Apache + public. `[ACCEPT]`
- **Reproducibility rule (unchanged):** any mutable free source requires archive-at-retrieval
  (store raw bytes + fetch timestamp) for provenance to be reconstructable. [V]

**B6 decision: `CONDITIONAL`**, with two NEW `[UNVERIFIED]` licenses (securitiesdb, Kaggle archive)
that a data build must clear before use. Nothing invented; no license is assumed where undocumented.

---

## 10. SOURCE-BY-SOURCE EVIDENCE TABLE

| Source | URL (retrieved 2026-09-10) | Layer | $0 access | Coverage (verified) | PIT | Provenance | License | Classification |
|--------|---------------------------|-------|-----------|---------------------|-----|------------|---------|----------------|
| S&P DJI quarterly announcements (live) | `spglobal.com/spdji/en/documents/indexnews/announcements/1464356_shufjun23.pdf`, `…/1483743_shuffle546-june2026.pdf` | Events/PIT | Yes | 2023, 2026 samples content-verified | Announcement+effective `[PIT PROVEN]` (samples) | Stable URL; archive-on-retrieval | S&P DJI; publication review | `[CONDITIONAL]` |
| S&P DJI announcements (Wayback) | CDX: `spglobal.com/spdji/en/documents/indexnews/announcements*` (2013-04-16 → 2022-08-04 observed) | Events/PIT | Yes | URL-level: 688 content dates; quarterly `shuf`/`migr` set listed | Per-event after artifact check | CDX capture timestamp + URL | S&P DJI content | `[CONDITIONAL]` |
| press.spglobal.com + PRNewswire quarterly releases | `press.spglobal.com/2023-09-01-…`, `prnewswire.com/news-releases/bloom-energy-…302870517.html` | Events/PIT | Yes | 2023/2026 samples; year filter 2012+ (page) | Announcement+effective `[PIT PROVEN]` (samples) | Static slugs | PRNewswire/S&P terms; redistribution review | `[CONDITIONAL]` |
| S&P 600 index page (+ Wayback) | `spglobal.com/spdji/en/indices/equity/sp-600`; Wayback `us.spindices.com/indices/equity/sp-600` 2012-09-17+ | Membership roster | Yes | Page snapshots 2012+ (presence); "Full Constituents List" current | Snapshot-date PIT only | Wayback capture | S&P DJI terms | `[CONDITIONAL]` |
| SEC EDGAR N-PORT (iShares Trust 0001100663) | `sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001100663&type=NPORT-P` | Membership roster | Yes | Multiple NPORT-P filings verified (2026-08-27 batch) | Filing-ts PIT `[ACCEPT]` | Accession numbers + filing-date | Public/fair-access | `[ACCEPT]` (filing series) / roster-index parity `[UNVERIFIED]` |
| pitindex | `github.com/arielNacamulli/pitindex` (MIT) | Membership | Yes | sp600 2021-03+, sp400 2011+; pre-2021 600 roster corrupt (self-disclosed) | Upper-bound event dates; no announcements | SHA pin | MIT (+Wikipedia CC BY-SA) | `[CONDITIONAL]` |
| fja05680/sp500 | `github.com/fja05680/sp500` (MIT) | Membership | Yes | S&P 500 1996+ | Effective-date diffs | SHA pin | MIT | `[CONDITIONAL]` |
| Wikipedia changes tables | `en.wikipedia.org/wiki/List_of_S%26P_600_companies` etc. | Membership | Yes | ~2014+; deletions incomplete | Effective date only | `oldid` | CC BY-SA | `[CONDITIONAL]` |
| NYU Wurgler file | `pages.stern.nyu.edu/~jwurgler/data/sp500 changes.xls` | Events | Yes | 1976–2000 (500) | Two dates | Static | Academic | `[ACCEPT]` |
| Kaggle Arandkei delisted archive | `kaggle.com/datasets/rodas86/arandkei-historical-delisted-assets-archive` | Delisted prices | Yes | Created 2026; delisted OHLCV; coverage/age unverified | n/a | Kaggle version | **UNVERIFIED** | `[UNVERIFIED]` |
| tenicho/data-cleaning | `github.com/tenicho/data-cleaning` | Delisted prices | Yes | Deaths concentrated 2021–2026; pre-2016 absent (self-disclosed) | n/a | repo | UNVERIFIED | `[NOT SUFFICIENT AT $0]` |
| SEC EDGAR Form 25/25-NSE | `sec.gov` | CA/delisting | Yes | Delistings May 2006+ | Filing ts | Accession | Public | `[ACCEPT]` |
| securitiesdb splits/dividends | `securitiesdb.com/developers/dividend-api` | CA | Yes | Dividend history + splits/ex-date; depth/coverage unverified | Not established | n/a (api) | Terms: as-is; may change | `[CONDITIONAL]/[UNVERIFIED]` |
| EODHD splits/dividends | `eodhd.com/financial-apis/api-splits-dividends` | CA | Free tier ~1yr div | 30+ yrs = paid | — | — | — | `[NOT SUFFICIENT AT $0]` |
| Stooq / Alpha Vantage / yfinance | stored in predecessor audit | Prices | Free tiers | Active names; full AV history premium | Mutable, no vintage | archive-at-retrieval | personal/ToS risk | `[CONDITIONAL]`/`[REJECT]` (deep) |
| S&P U.S. Indices Methodology | `spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf` (Jul 2026); 2012/2013 snapshot `spice-indices.com/…/methodology-sp-us-indices_20120228.pdf` | Float/liquidity rule | Yes | IWF≥0.1 (1500); FALR≥0.1; composite pricing | Defines evaluation-date window | Static/archived | S&P DJI | `[ACCEPT]` (rule reference) |
| OpenFIGI / SEC CIK | `api.openfigi.com` / `sec.gov/files/company_tickers.json` | Identity | Yes | current mapping / stable ids | current only | versioned | MIT/Apache / public | `[ACCEPT]/[CONDITIONAL]` |
| EODHD / Siblis / SHARADAR / CRSP / Norgate / QC+AlgoSeek | vendor pages | All missing layers | No | — | — | — | paid | `[REJECT]` |

---

## 11. $0 FEASIBILITY MATRIX (updated)

| Layer | Free path | Status NOW | Status in predecessor |
|-------|-----------|------------|-----------------------|
| Price/OHLCV (active) | Stooq/AV/yfinance archive-at-retrieval | `[CONDITIONAL]` | `[CONDITIONAL]` |
| Delisted OHLCV | Kaggle archive (license unverified) / Wayback scraper | `[UNVERIFIED]` / `[NOT SUFFICIENT AT $0]` certifiable | `[NOT SUFFICIENT AT $0]` |
| S&P 500 membership/events | fja05680 + pitindex + announcements + Wurgler | `[CONDITIONAL]` | `[CONDITIONAL]` |
| S&P 400 membership/events | pitindex 2011+ + announcements 2013+ (Wayback) + fund-holdings | `[CONDITIONAL]` 2013+ | `[UNVERIFIED]` |
| **S&P 600 membership/events** | **Announcements 2013+ (Wayback) + EDGAR N-PORT fund rosters + page snapshots 2012+** | **`[CONDITIONAL]` 2013+, pre-2013 `[UNVERIFIED]`** | `[REJECT]`-grade / `[UNVERIFIED]` |
| Composite 1500 events | union of the above, anniversary-validated | `[CONDITIONAL]` 2013+; **full depth `[NOT READY]`** | `[NOT READY]` |
| Event announcement PIT | quarterly PDFs/presses (live + Wayback) | `[CONDITIONAL]` 2012/2013+; per-event `[PIT PROVEN]` after archival | `[UNVERIFIED]`/deep `[PIT UNPROVEN]` |
| CA delistings | EDGAR Form 25 | `[ACCEPT]` | `[ACCEPT]` |
| CA splits/dividends | securitiesdb (unverified) / EODHD-free (1yr) | `[UNVERIFIED]`/`[NOT SUFFICIENT AT $0]` | `[REJECT]`/`[UNVERIFIED]` |
| Free-float PIT (IWF) | none | `[UNVERIFIED]` | `[UNVERIFIED]` |
| ADV PIT (proxy) | free OHLCV (active) | `[CONDITIONAL]` active only | `[CONDITIONAL]` |
| Identity/symbology | SEC CIK + OpenFIGI | `[ACCEPT]` | `[ACCEPT]` |
| Provenance/reproducibility | pinned commits/oldids/accessions + archive-at-retrieval | `[CONDITIONAL]` | `[CONDITIONAL]` |
| Licensing | research-OK core; publication review; 2 new `[UNVERIFIED]` (Kaggle, securitiesdb) | `[CONDITIONAL]` | `[CONDITIONAL]` |
| Cost/access | `$0` maintained; no purchases | `[ACCEPT]` | `[ACCEPT]` |

---

## 12. REMAINING BLOCKERS (after this audit)

1. **Pre-2013 S&P 600 membership/announcement depth** — no verified free source. [BLOCKING for full depth]
2. **Delisted-price history certification** — only unverified/fragile free candidates (Kaggle license
   undefined; Wayback scraper). [BLOCKING for deletion-leg T0+h coverage]
3. **Free-float PIT (IWF history)** — no free historical float; SEC shares-outstanding ≠ float.
   [BLOCKING for the frozen universe filter]
4. **Structured split/dividend/ex-date CA record with provenance** — free candidates are
   uncertified (depth/coverage/license/adjustment). [BLOCKING for frozen CA-ordering/PIT]
5. **Announcement-corpus completeness (2013–2022)** — must be proven by executing the full
   retrieval/reconciliation, not assumed from URL patterns. [CONDITION until executed]
6. **Fund-holdings ↔ index-membership parity** — must be validated (tracking deviations,
   exclusions, share classes) before rosters are admitted. [CONDITION until validated]
7. **Frozen filter binding vs. S&P methodology (ADV/float proxy vs. FALR/IWF 0.1)** — needs human
   ratification of what the filters mean going forward. [HUMAN]
8. **Vendor-EOD close semantics for `Close(T0)`** — uncertified vs official consolidated close
   (unchanged from predecessor). [CONDITIONAL]
9. **License review** for Kaggle/securitiesdb-derived data **and** any public release of an
   S&P-related derived dataset. [HUMAN/LEGAL]

---

## 13. CAN D1 BE UPGRADED FROM NOT READY?

**Not for the frozen, full-depth design.** The blocking conditions in §12 (pre-2013 depth,
free-float PIT, certified delisted prices, certified CA, corpus completeness) cannot be cleared at
`$0` with the evidence available today, so `F-1 D1 = NOT READY` is **re-affirmed, unchanged**.

**What MAY now be human-ratified instead (HUMAN GOVERNANCE OPTION ONLY — not taken here):** a
**constrained F-1 window = "quarterly reconstitution events on the full Composite 1500 for
~2013-12 → present"**, at `$0`, with: (a) events anchored to individually-archived S&P DJI
announcements (`[PIT PROVEN]` per event), (b) the S&P 600 roster leg reconstructed from fund
holdings + announcement deltas and validated against page snapshots, (c) deletion-leg prices handled
by the frozen exclude-rule (with an explicit coverage report), (d) free-float PIT for those names
recorded as `[UNVERIFIED]` and therefore input-negative per the hard PIT rule. Even this constrained
window remains OUTSIDE HYP_003/R1/gate authority until the human ratifies it and the data
engineering is authorized separately.

---

## 14. EXPLICIT HUMAN DECISIONS STILL REQUIRED

1. Confirm D1 = `NOT READY` (recommended) for the full-depth frozen F-1 at `$0`.
2. Decide whether to authorize the **constrained 2013+ quarterly-reconstitution window** described
   in §13 as a data-engineering feasibility build (NOT as R1).
3. Ratify the **semantics of the frozen filters** — ADV/float proxies vs. the actual S&P DJI
   FALR/IWF methodology requirement (recorded in §8.1; this audit does not change F-1).
4. Accept or reject **vendor-EOD close** as the documented `Close(T0)` substitute.
5. Accept or reject **fund-holdings (N-PORT/N-CSR) rosters as a validated membership proxy** after
   parity validation.
6. Commission **legal/licensing review** for: (a) S&P DJI / PRNewswire derivatives, (b) Kaggle
   Arandkei archive, (c) securitiesdb CA data, (d) Wikipedia CC BY-SA share-alike implications.
7. Decide whether archive-at-retrieval + provenance manifest engineering is authorized at `$0`.
8. Re-assess F-1 readiness via the canonical ReInceptionGate path AFTER the data decisions above.
   All are `[HUMAN DECISION REQUIRED]`; none are taken by this document. [NON-NORMATIVE]

---

## 15. NO-GO CONDITIONS (verified: none violated)

This audit did **NOT**: change F-1 universe/numerics · create F-1-Free · create HYP_003 · invoke
ReInceptionGate · start R1 · run backtest/optimization · compute any empirical return/alpha/IC/HAC ·
specify D2 · touch `src/`, gates, ROADMAP, registry, broker, or capital · modify any governance
record · purchase/order/bill any data · create any account requiring payment · commit/push/reset/
rebase/stash/checkout · create any file other than this document · assume any license where
undocumented. No magic floors / silent fallbacks / fabricated coverage: every unverifiable claim is
`[UNVERIFIED]`, every presence-only claim is labeled as such. [VERIFIED]

---

## 16. RESEARCH BOUNDARY STATEMENT

- This document is `[FEASIBILITY-ONLY]` `[NON-NORMATIVE]`. It reports what the free layer can and
  cannot certify for the **frozen** F-1 data construction, on retrieval date 2026-09-10.
- Evidence is tagged `V` (verified from primary artifacts this audit loaded), `R` (self/source
  disclosed), `I` (inference), `NP` (not proven); Voy narrowly, nothing is inferred into a verified
  fact. Searches were resolved to real archives (Wayback CDX, SEC EDGAR, vendor pages) rather than
  snippets.
- Archive-depth findings are **floors, not ceilings** — further CDX pagination and per-PDF content
  checks can extend (or correct) the 2013-12 ↔ 2022-06 quarterly corpus evidence, and are the natural
  next documentation-only probe if the human ratifies §14.2.
- The next valid step remains a HUMAN D1 decision. D2, HYP_003, R1, gates and trading remain locked.

**Canonical research state after this work (unchanged):**
`F-1 = S&P Composite 1500 · D1 = NOT READY / CONDITIONAL · D2 = LOCKED · HYP_003 = NOT AUTHORIZED
· R1 = NOT AUTHORIZED · GATE = NOT AUTHORIZED · TRADING = LOCKED · CAPITAL = $0.00`

### Verification Ledger (this audit)
- Implementation Status: NONE (documentation-only; `src/` untouched; single new untracked file).
- Contract Enforcement: STRICT FAIL-CLOSED — no promoted source claim; `[UNVERIFIED]`/`[CONDITIONAL]`
  used wherever evidence fell short; no license invented.
- Mathematical Authority: N/A for data feasibility; canonical gate floors untouched.
- Local Test Suite: NOT RUN (no code changed — documentation-only convention).
- Remote CI Status: NOT AVAILABLE.
- Methodological Caveats: all archive/timeline findings are floors based on 2026-09-10 retrieval;
  per-PDF content verification for 2013–2022 announcements remains outstanding; fund↔index parity,
  Kaggle/securitiesdb licensing, and free-float PIT remain `[UNVERIFIED]`; D1 stays `NOT READY`.

STOP — D1 BLOCKER RESOLUTION RESEARCH COMPLETE. F-1 UNCHANGED · D2 LOCKED · HYP_003 NOT AUTHORIZED ·
R1 NOT AUTHORIZED · GATE NOT AUTHORIZED · TRADING LOCKED.