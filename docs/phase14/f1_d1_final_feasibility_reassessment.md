# ACASH V5 — F-1 D1 FINAL FEASIBILITY REASSESSMENT

**Document ID:** `docs/phase14/f1_d1_final_feasibility_reassessment.md`
**Object:** F-1 `CAND-FLOW-CALENDAR-REBALANCE-001` — HUMAN DECISION RESOLUTION (D1-A / D1-B) + FINAL D1 FEASIBILITY RE-ASSESSMENT under the proposed decisions

**Status:** `[NON-NORMATIVE]` · `[DOCUMENTATION-ONLY]` · `[D1 FINAL FEASIBILITY REASSESSMENT]` · `[HUMAN GOVERNANCE REQUIRED]`
**Date:** 2026-09-10 (retrieval date for all web/archive evidence in this document)

**Baseline documents (evidence carried, NOT rewritten):**
- `docs/phase14/candidate_f1_flow_calendar_rebalance_review.md` (F-1 specification freeze, 2026-09-09)
- `docs/phase14/f1_d1_free_data_feasibility.md` (D1 free-first audit, 2026-09-10)
- `docs/phase14/f1_d1_blocker_resolution.md` (D1 blocker-resolution research, 2026-09-10)

> [!CAUTION]
> **This document does NOT authorize HYP_003, R1, ReInceptionGate execution, backtesting,
> optimization, parameter search, paper trading, live trading, broker connection, or capital
> deployment.** It only resolves, **as PROPOSED defaults**, the outstanding human governance decisions
> and re-assesses data feasibility under those proposed defaults. No decision here is
> HUMAN-ACCEPTED unless an actual human acceptance record exists elsewhere in the repository.

**Statement classes:** `[VERIFIED FACT]` = verified from a primary artifact this audit loaded ·
`[SOURCE CLAIM]` = reported/secundary, not independently evidenced · `[MODEL INFERENCE]` = inferred,
never promoted · `[UNVERIFIED]` = evidence insufficient. **Classification labels:** `[ACCEPT]`
`[CONDITIONAL]` `[UNVERIFIED]` `[NOT SUFFICIENT AT $0]` `[REJECT]` · `[PIT PROVEN]` `[PIT UNPROVEN]`
· `READY` / `CONDITIONAL` / `NOT READY` (semantics per prompt §15).

---

## 1. EXECUTIVE DECISION

**FINAL D1 VERDICT: `NOT READY / CONDITIONAL`** (i.e. NOT `READY`).

| Item | Proposed default (this document) | Status in register |
|------|----------------------------------|--------------------|
| **D1-A** Constrained research window ~2013-12 → present | ACCEPT **as a CONDITIONAL research window** for further DATA FEASIBILITY validation only. Logically compatible with the frozen candidate (temporal-coverage constraint only; no universe/event/signal/return/horizon/cost change). | `PROPOSED / PENDING HUMAN RATIFICATION` |
| **D1-B** Filter semantics | **RETAIN FROZEN PROXY** (`ADV ≥ $5M/day`, `Free Float ≥ 20%`). The official S&P FALR/IWF methodology difference is recorded as a **KNOWN METHODOLOGICAL CAVEAT**, NOT an automatic spec rewrite. | FROZEN (2026-09-07); re-ratification of the caveat acknowledgment `PROPOSED` |
| B2 delisted-price leg | `NOT SUFFICIENT AT $0` (certifiable); frozen §27G exclude-rule fallback analyzed (§7.3) — consistent with the frozen spec, coverage consequence must be human-ratified. | `PROPOSED / PENDING HUMAN RATIFICATION` |
| B5 free-float PIT | `UNVERIFIED` — no free historical PIT float. Blocks `READY`. | `PROPOSED / PENDING HUMAN RATIFICATION` |
| B6 provenance/license | `CONDITIONAL` — but **2 new `[UNVERIFIED]` licenses** (Kaggle archive, securitiesdb) and S&P-derivative publication review remain open. | `PROPOSED / PENDING HUMAN RATIFICATION` |

**Reasoning (compressed):** the ~2013-12 → present window does give genuine, evidence-backed
improvements — S&P 600/400 membership and quarterly addition/deletion events become *reconstructable
in principle* from archived S&P DJI announcements (Wayback, first verified artifact 2013-12-11) plus
annual fund-holdings rosters (EDGAR N-PORT/N-CSR), and announcement→effective chronology is
provable **per archived event**. But this does NOT make the dataset complete: announcement-corpus
completeness for 2013–2022 is `[UNVERIFIED]` until executed; fund-roster ↔ official-index parity is
`[UNVERIFIED]`; **free-float PIT is `[UNVERIFIED]` (B5)**; delisted-price coverage is
`[NOT SUFFICIENT AT $0]` verified (B2); and licenses for two proposed free sources are `[UNVERIFIED]`
(B6). Per the frozen **PIT hard rule** and the **weakest-component rule**, the frozen full-depth F-1
design is NOT data-feasible at `$0` today. The constrained window is worth one more DATA FEASIBILITY
validation pass only **if** the human ratifies D1-A and the §14 register items. [NON-NORMATIVE]

---

## 2. CURRENT CANONICAL GOVERNANCE STATE

Unchanged from freeze; nothing below is modified by this document. [FROZEN — all]

- **Candidate:** F-1 `CAND-FLOW-CALENDAR-REBALANCE-001` — RESEARCH CANDIDATE ONLY. [FROZEN] [VERIFIED FACT]
- **Mechanism:** passive index/ETF forced rebalancing flow ≈ daily price-insensitive demand/supply at
  the effective-date close. Mechanism defined; truth NOT PROVEN. [FROZEN definition] [MODEL INFERENCE — NP]
- **Direction:** SHORT composite reversal (positive flow → SHORT; negative flow → LONG). [FROZEN]
- **Horizons:** {1, 5, 10}; PRIMARY = 5. [FROZEN]
- **Universe:** S&P Composite 1500 family (S&P 500 / MidCap 400 / SmallCap 600). [FROZEN]
- **Filter proxies:** ADV ≥ US$5M/day (60-day pre-event); Free Float ≥ 20% (PIT by effective date). [FROZEN — human-frozen 2026-09-07]
- **Event family:** reconstitution only; month-end/periodic SEPARATE; special/mid-stream excluded. [FROZEN]
- **Anchor:** effective date T0; entry = official close T0; `R(h) = Close(T0+h)/Close(T0) − 1`. [FROZEN]
- **Sample:** `T_eff ≥ 25/leg`; canonical `N_valid ≥ 250` (not overridden). [FROZEN]
- **Prior human decision:** OPTION A — RETAIN COMPOSITE 1500 (no downgrade to S&P 500, no S&P 600
  removal, no F-1-Free replacement). [FROZEN] [VERIFIED FACT — candidate review §2]
- **Current D1 status:** `NOT READY / CONDITIONAL`. [FROZEN]
- **LOCKED unless explicitly authorized:** D2 · HYP_003 · ReInceptionGate · R1 · Phase 6
  qualification · trading · paper trading · live trading · broker · capital (=$0.00) · backtests ·
  optimization · parameter search · empirical performance/alpha/profitability claims.
  [FROZEN — all]
- **Cost rule:** DATA COST = `$0.00`; free tiers only if genuinely non-billable. [FROZEN]

**Repository state (§4/§5 — read-only verification, 2026-09-10):**
- `git status --short --branch` → `## main...origin/main` (clean before this document existed). `[VERIFIED FACT]`
- `git rev-parse HEAD` → `7d71223fb8e275cc9ee981f3754fe45483b18dcf`. `[VERIFIED FACT]`
- `git branch --show-current` → `main`. `[VERIFIED FACT]`
- `git rev-parse origin/main` → `7d71223fb8e275cc9ee981f3754fe45483b18dcf`. `[VERIFIED FACT]`
- `git log --oneline --decorate -10` → HEAD/main/origin/main/decor at **7d71223** on top of 0668b8c. `[VERIFIED FACT]`
- **7d71223 IS present locally and on origin/main.** The prior blocker-resolution ledger's statement
  ("HEAD 0668b8c unchanged / NO add/commit/push performed") is an accurate description of the state
  **at completion of that task**. It was followed by an explicit human instruction to publish the
  blocker-resolution doc, producing commit **7d71223** (`docs(phase14): add F-1 D1 blocker resolution
  research audit`) and a push to main (`0668b8c..7d71223`). The two statements are therefore
  consistent **in sequence**, not contradictory. No history divergence: 0668b8c remains in ancestry;
  no revert/replacement/force-push was performed then or now. This task performs NO git mutation.
  `[VERIFIED FACT — sequencing reconciles the records; nothing is remediated]`

**Conflict check (§3):** no conflicts found among the three baseline documents on frozen terms,
statuses, or classifications. Terminology is preserved. `[VERIFIED FACT]`

---

## 3. EVIDENCE BASELINE

Carried forward (documented, not re-derived):

1. **S&P 500 events/membership:** fja05680/sp500 1996+ (MIT, commit-pinnable); pitindex sp500 2005+;
   NYU Wurgler 1976–2000 additions / 1979–2000 deletions. `[CONDITIONAL]` `[PIT UNPROVEN]` deep.
   [VERIFIED FACT — feasibility §9/§10/§23]
2. **S&P 400 membership:** pitindex sp400 from 2011-11-20; Wikipedia changes ~2014+ (removals
   incomplete). Pre-2011: none free. `[UNVERIFIED]`. [VERIFIED FACT — feasibility §9.4/§11]
3. **S&P 600 membership:** pitindex sp600 floor 2021-03-26 (pre-2021 Wikipedia roster corrupt,
   "no free source"); **now extended by the blocker-resolution findings** — quarterly S&P DJI
   announcement PDFs archived in Wayback from 2013-12-11 onward + S&P DJI index-page snapshots from
   2012 + EDGAR fund-holdings (N-PORT/N-CSR) roster snapshots. [VERIFIED FACT — blocker §4]
4. **Announcement PIT:** S&P DJI quarterly press PDFs/press releases for recent years content-verified
   (2023-06-02, 2026-06-05, 2026-09-04, 2023-09-01); Wayback corpus 2013-12→2022-06 present at URL
   level. [VERIFIED FACT — blocker §4.1/§6]
5. **Prices:** Stooq/AV/yfinance active-name free OHLCV; vendor-EOD close (not certified official
   close); delisted prices not free from any audited API. `[CONDITIONAL]`/`[NOT SUFFICIENT AT $0]`.
   [VERIFIED FACT — feasibility §8/§17]
6. **CA:** SEC EDGAR Form 25/25-NSE delistings (May 2006+) `[ACCEPT]`; free structured
   splits/dividends NOT certified (securitiesdb `[CONDITIONAL]/[UNVERIFIED]`). [VERIFIED FACT — feasibility §15, blocker §7]
7. **Free-float PIT:** NOT available free (historical IWF/float); SEC shares-outstanding ≠ float.
   `[UNVERIFIED]`. [VERIFIED FACT — feasibility §14, blocker §8]
8. **Provenance/reproducibility:** pinned commits/oldids/accession numbers + archive-at-retrieval =
   `[CONDITIONAL]`; mutable sources otherwise `[REPRODUCIBILITY RISK]`. [VERIFIED FACT — feasibility §18/§19]

**New verification performed this audit (2026-09-10):**
- Kaggle "Arandkei: Historical Delisted Assets Archive" page re-requested → **page again failed to
  render license/description** (title only returned). License therefore remains **`[UNVERIFIED]`**
  (§24/§25 rule: do NOT promote to ACCEPT). [VERIFIED FACT — fetch attempt]
- Wayback artifact `20131211/67155_fbshuf252426100.pdf` (S&P DJI December 2013 quarterly) → **3
  captures exist** (2021-02-25, 2021-12-28, 2026-06-01 WBM range noted). Presence `[VERIFIED FACT]`;
  per-document announcement/effective-date CONTENT `[UNVERIFIED]` (not extractable this session —
  outstanding per-event verification). [VERIFIED FACT — capture presence only]

---

## 4. D1-A — CONSTRAINED WINDOW DECISION

**Proposed window:** `~2013-12 → present`, quarterly reconstitution events, S&P Composite 1500
identity. [PROPOSED / PENDING HUMAN RATIFICATION]

**4.1 Logical compatibility with the frozen candidate (§6 test).**

| Frozen element | Must preserve | Compatibility |
|----------------|---------------|---------------|
| Universe identity | S&P Composite 1500 | ✅ preserved — window does not drop 400/600, no F-1-Free swap. All 3 legs retained. |
| Event family | QUARTERLY RECONSTITUTION ONLY | ✅ preserved — exactly the quarterly corpus; month-end/special excluded. |
| Event identity | as-announced add/delete, effective T0 | ✅ preserved — same semantics; only the date range is constrained. |
| PIT methodology | announcement vs effective; no look-ahead | ✅ preserved — per-event artifacts carry both dates. |
| Mechanism | forced-flow at effective close | ✅ preserved — mechanism untouched. |
| Signal / Return / Horizons | +1/−1/0; `R(h)=Close(T0+h)/Close(T0)−1`; {1,5,10} | ✅ preserved — unchanged. |
| Cost model | fixed + 1×/2×/5× | ✅ preserved — no change. |
| Kill conditions | 9 pre-specified | ✅ preserved. |

→ The window constrains **TEMPORAL COVERAGE ONLY**; it does not silently change universe, event
family, signal, return, horizons, cost, or kill conditions. [MODEL INFERENCE — from the element-by-element
mapping above; verdict-supporting]

**4.2 Window justification.** Earliest quarterly announcement artifact verified archived =
**2013-12-11** (`67155_fbshuf252426100.pdf`, 3 Wayback captures). CDX content-floor for the
announcements folder observed at 2013-04-16 (a floor, not coverage). Quarterly `shuf`/`migr`/`shuffle`
documents verified at URL-level through 2022-06 and live 2023/2026 samples content-verified.
[VERIFIED FACT — blocker §4.1] `2013-12 → present` is therefore an **artifact-anchored** start;
earlier dates remain `[UNVERIFIED]` at `$0`.

**4.3 What D1-A ACCEPT (if ratified) DOES and DOES NOT mean.**

- DOES mean → the window MAY be used for **further DATA FEASIBILITY validation** (corpus-completeness
  reconciliation, roster-parity check, provenance build planning). [PROPOSED]
- DOES NOT mean → `D1 = READY` · dataset complete · PIT fully proven · delisted prices solved ·
  free-float PIT solved · `HYP_003` authorized · R1 authorized · gate invoked. [NON-NORMATIVE — clear]

**4.4 Default decision:** `D1-A = ACCEPT AS A CONDITIONAL RESEARCH WINDOW` — **PROPOSED / PENDING
HUMAN RATIFICATION** (no actual acceptance record exists; this document does NOT accept on the
human's behalf). **If evidence shows even this window cannot preserve frozen semantics → D1-A =
NOT FEASIBLE.** The current evidence does not force that classification. [NON-NORMATIVE]

---

## 5. D1-B — FILTER SEMANTICS DECISION

**Frozen proxies (unchanged, human-frozen 2026-09-07):** `ADV ≥ US$5M/day` (60-day pre-event) and
`Free Float ≥ 20%` (PIT by effective date). [FROZEN — [VERIFIED FACT] candidate review §30 rows 5/6]

**Methodological caveat (recorded, NOT a spec change):** the official S&P U.S. Indices Methodology
(July 2026, `spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf`;
2012/2013 snapshot at `spice-indices.com`) uses **FALR ≥ 0.1** (annual dollar value traded / FMC,
composite pricing, 365-day window, evaluation at open two business days prior to announcement) and
**IWF/float** gates for current constituents (1500: IWF ≥ 0.1), with a vintage-dependent rule
(2012/2013-era: FALR ≥ 1.00 plus 250k-share/6-month test). **Frozen F-1 filter ≠ exact S&P
methodology reproduction.** This is a documented methodological distinction only. [SOURCE CLAIM — cited
from the methodology PDF; the numeric rule text read from the cited document 2026-09-10]

**Default decision:** `D1-B = RETAIN FROZEN PROXY`. The proxies remain unchanged. The official
methodology difference is recorded as a **KNOWN METHODOLOGICAL CAVEAT** (flagged in §14/§15 for
explicit human acknowledgment). Exact S&P methodology reproduction, if ever desired, is a SEPARATE
specification-change decision — NOT implemented here. [NON-NORMATIVE — PROPOSED default; the proxy
itself is already frozen and stays frozen regardless]

---

## 6. B1 — S&P 600 MEMBERSHIP

**Assessment under D1-A window (~2013-12 → present, quarterly reconstitution only).**

| Evidence strand | Status under 2013+ window | Class |
|-----------------|----------------------------|-------|
| Quarterly reconstruction add/delete announcements in Wayback/PRNewswire | Quarterly docs verified 2013-12-11, … , 2022-06-03 (URL level), 2023/2026 (content level) | `[CONDITIONAL]` |
| Announcement→effective dates per event | Proven for 2023/2026 samples; per-event proof for 2013–2022 outstanding | `[CONDITIONAL]` |
| Full-roster snapshots (EDGAR N-PORT/N-CSR fund holdings; archived S&P DJI 600 page 2012+) | Filing series `[ACCEPT]`; roster↔official-index PARITY `[UNVERIFIED]` | `[CONDITIONAL]` |
| Composite 1500 identity (500/400/600 union) | Reconstructable in principle 2013+ via announcements + rosters | `[CONDITIONAL]` |
| Pre-2013 S&P 600 membership | No verified free source | `[UNVERIFIED]` |
| **Corpus completeness (every quarterly + special add/delete present)** | **NOT executed; cannot be assumed** | `[UNVERIFIED]` |

**Verdict: `B1 ≠ ACCEPT`.** Completeness of the event corpus and of the roster reconstruction is NOT
proven; therefore, per the frozen PIT hard rule and the prompt's B1 acceptance bar, B1 = `CONDITIONAL`
for the 2013+ window and `[UNVERIFIED]` for anything before it. The acceptance condition to reach
`ACCEPT` is explicit — execute the full reconciliation and demonstrate zero unexplained missingness
against the announcement corpus. [NON-NORMATIVE]

---

## 7. B2 — HISTORICAL DELISTED PRICES

**7.1 Re-filtered candidates under `$0` (2026-09-10).**

| Source | Coverage | License | Verdict |
|--------|----------|---------|---------|
| Kaggle Arandkei delisted archive | Daily OHLCV for delisted names; created 2026; coverage/age `[UNVERIFIED]` | **`[UNVERIFIED]`** (page fails to render license, re-verified today) | `[CONDITIONAL]` research path / **`[NOT SUFFICIENT AT $0]`** as certified |
| tenicho/data-cleaning | Delistings concentrated 2021–2026; pre-2016 absent (self-disclosed) | `[UNVERIFIED]` | `[NOT SUFFICIENT AT $0]` |
| historicaldata.net | full history = paid | — | `[NOT SUFFICIENT AT $0]` |
| Wayback Machine Stock Scraper (Acelogic) | Archived old-Yahoo pages; fragile/non-contractual | `[UNVERIFIED]` | `[CONDITIONAL]`/`[UNVERIFIED]` |
| AV LISTING_STATUS&state=delisted | delisted ROSTER metadata (ipoDate/delistingDate) only; NO OHLCV | registered | `[ACCEPT]` metadata only |
| SEC EDGAR Form 25/25-NSE | delisting EVENTS May 2006+ | public | `[ACCEPT]` events only |
| EODHD / Sharadar / Norgate / CRSP / QC+AlgoSeek delisted products | paid | — | `[REJECT]` |

**B2 verdict: `NOT SUFFICIENT AT $0`** (certifiable). Existence of a free-looking dataset ≠
license-cleared + complete + reproducible; the one genuinely free delisted-OHLC candidate (Kaggle)
has an `[UNVERIFIED]` license and unverified coverage. Not promoted. [VERIFIED FACT — re-checked today]

**7.2 What "solved" would require:** verified historical OHLCV fields for the delisted universe with
security identity, date ranges, CA treatment, reproducible retrieval, and compatible license. [NON-NORMATIVE]

**7.3 Delisting fallback analysis (§12 test) — "quarterly deletion PIT + EDGAR Form 25 dates +
'unavailable forward price ⇒ exclude'".** The exclude rule is **already frozen** (candidate review
§21/Dimension 21 §27G, Item 6/17: missing forward price ⇒ invalid, excluded — no synthetic return).
Analysis against the six criteria:

1. Preserves frozen return definition — **YES**: `R(h)` computed only on valid prints; no synthetic
   delisting return. [VERIFIED FACT — frozen rule]
2. Preserves PIT integrity — **YES**: deletion identity is as-announced (PIT) and Form 25 timestamps
   are filing-stamped; no look-ahead. [VERIFIED FACT]
3. Avoids survivorship bias — **PARTIAL**: event identity avoids survivor-list look-ahead; but names
   without forward prints leave the deletion-leg composite, and no certified price history exists for
   them at `$0` → the leg's coverage cannot be certified, which is a material gap, not a guarantee of
   no bias. [MODEL INFERENCE]
4. Selection bias — **POSSIBLE at the coverage level**: exclusion is deterministic (not
   outcome-based) per the frozen rule, but the deletion-leg sample composition is reduced vs. the
   as-announced list; must be reported as a limitation. [MODEL INFERENCE]
5. Alters the event sample — **YES** at the deletion-leg composite level (same as consequence #4);
   this is the frozen missing-price behavior, not a new spec change. [VERIFIED FACT + inference]
6. Alters the candidate definition — **NO**: no rule change; the fallback is an operationalization of
   the frozen §27G missing-price rule plus the already-`[ACCEPT]` Form 25 delisting events.
   [VERIFIED FACT]

→ **No frozen-spec change is required to adopt the fallback; it is already the frozen behavior.**
What the human MUST ratify is the **research-scope consequence**: whether the reduced/uncertified
deletion-leg coverage is acceptable for the constrained window's feasibility objective, and whether
`T_eff(leg) ≥ 25` remains plausible for the deletion leg under it (data-dependent, `[UNVERIFIED]`).
This ratification is recorded in §14 (decision R-2). [NON-NORMATIVE]

---

## 8. B3 — ANNOUNCEMENT PIT

**Terminology (required distinction):** announcement timestamp/date ≠ publication date ≠ effective
date ≠ official-close anchor. A Wayback **capture date** proves only that the artifact was archived
by then — it is NOT the original announcement time (prompt §22, honored). [VERIFIED FACT — rule]

**Evidence (2026-09-10):**
- **Live press releases (dated, primary):** 2023-09-01 (`press.spglobal.com/2023-09-01-Blackstone-and-Airbnb-Set-to-Join-S-P-500-…`), 2026-09-04 (`prnewswire.com/news-releases/bloom-energy-illumina-and-everpure-set-to-join-sp-500-…-302870517.html`), plus 2026-07/08 single-addition releases. [VERIFIED FACT — content read]
- **Quarterly announcement PDFs:** 2023-06-02 (`1464356_shufjun23.pdf`), 2026-06-05 (`1483743_shuffle546-june2026.pdf`) — content-verified, each with announcement + effective dates + add/del + ticker + GICS. [VERIFIED FACT — blocker §4.1]
- **Wayback corpus 2013-12→2022-06:** artifact **presence** `[VERIFIED FACT]`; **per-event content
  verification `[UNVERIFIED]`** (outstanding). [VERIFIED FACT — capture presence]
- `T_announcement < T_effective` for the verified samples (release issued ~1.5–3 weeks before
  effective). [VERIFIED FACT for samples]

**Verdict: `B3 = CONDITIONAL`.** For each event, announce < effective is `[PIT PROVEN]` only when the
responsible dated artifact is individually retrieved and timestamped. Full-corpus chronology is
`[PIT UNPROVEN]` until that per-event pass executes. [NON-NORMATIVE]

---

## 9. B4 — CORPORATE ACTIONS

| Component | Source | Evidence | Class |
|-----------|--------|----------|-------|
| **Delistings (event)** | SEC EDGAR Form 25/25-NSE, May 2006+ | Filing-stamped, accession-numbered | `[ACCEPT]` |
| **Splits / reverse / dividends / ex-dates** | securitiesdb free API — terms verified ("as-is", third-party feed, may be rate-limited/changed/discontinued); depth/coverage/adjustment semantics | `[UNVERIFIED]` | `[CONDITIONAL]`/`[UNVERIFIED]` |
| **Splits/dividends deep free** | EODHD free tier ≈1yr dividends; TIing/stockanalysis `[UNVERIFIED]`; Zacks/FirstRate paid | — | `[NOT SUFFICIENT AT $0]`/`[REJECT]` |
| **Adjustment algorithm provenance** | opaque in all free vendors | — | `[UNVERIFIED]` |
| **Ticker changes (identity)** | ticker ≈ identity (frozen); OpenFIGI/SEC CIK identity | — | `[CONDITIONAL]`/`[ACCEPT]` |

**Verdict: `B4 = CONDITIONAL`** — delisting/identity events are solid; structured split/dividend PIT
history is NOT certified at `$0`. [NON-NORMATIVE]

---

## 10. B5 — FREE FLOAT / ADV PIT

- **ADV ≥ $5M/day (60-day pre-event):** computable from free OHLCV volume for **active** names
  (`[CONDITIONAL]`); vendor volume is mutable and delisted names are absent (`[NOT SUFFICIENT AT $0]`
  for the deletion leg). [VERIFIED FACT]
- **Free Float ≥ 20% (PIT):** **no free historical PIT float dataset exists.** SEC filings give total
  shares outstanding (PIT) but float ≠ outstanding (closely-held/control blocks are not in free
  historical form). Current float is NOT usable for historical eligibility (prompt §10/§B5 rule).
  Official S&P IWF is NOT equivalent to a `Free Float ≥ 20%` cut — it is a different gate (per
  methodology, §5). [VERIFIED FACT — absence; [SOURCE CLAIM] for methodology numbers]
- **Verdict: `B5 = UNVERIFIED`** overall; ADV-portion `CONDITIONAL`. **This alone prevents D1 from
  becoming `READY`** for the frozen design. [NON-NORMATIVE]

---

## 11. B6 — PROVENANCE / LICENSE / REPRODUCIBILITY

Per-source provenance/license (2026-09-10), research/archive level only:

| Source | Provenance mechanism | License | Class |
|--------|------------------------|---------|-------|
| S&P DJI announcement PDFs (live) | stable URLs; archive-at-retrieval | S&P DJI; research OK; redistribution review | `[CONDITIONAL]` |
| S&P DJI announcements (Wayback) | CDX capture timestamp + URL — capture ≠ announcement time | S&P DJI content | `[CONDITIONAL]` |
| press.spglobal.com / PRNewswire | dated slugs; bulk-harvest terms `[UNVERIFIED]` | S&P/PRNewswire terms | `[CONDITIONAL]` |
| SEC EDGAR (Form 25, N-PORT/N-CSR, company_tickers) | accession numbers + filing date | public / fair-access | `[ACCEPT]` |
| **Kaggle Arandkei** | Kaggle version pin possible | **`[UNVERIFIED]`** (page unrenderable 2026-09-10) | `[UNVERIFIED]` |
| **securitiesdb** | none (API) | "as-is, may change/discontinue"; upstream terms unknown | `[UNVERIFIED]` |
| pitindex / fja05680 / Wikipedia / NYU | SHA / `oldid` / static file | MIT / MIT / CC BY-SA / academic | `[CONDITIONAL]` |
| Stooq / AV / yfinance | archive-at-retrieval (mutable) | personal-use / registered / ToS risk | `[CONDITIONAL]`/`[REJECT]` deep |

**Verdict: `B6 = CONDITIONAL`**, with **two `[UNVERIFIED]` licenses** (Kaggle, securitiesdb) that a
build must clear first, plus mandatory human/legal review before any derivation/publication of
S&P-related data. No license is inferred from "free/public/downloadable/API available" (prompt §25).
[VERIFIED FACT — no license invented]

---

## 12. SOURCE EVIDENCE MATRIX

| Source | Role | $0? | Earliest verified date | Latest verified date | PIT? | Announce. date? | Effective date? | Delisted coverage? | Corporate actions? | Free float? | ADV? | Provenance | License | Reproducibility | Classification | Blocking issue |
|--------|------|-----|------------------------|-----------------------|------|-----------------|-----------------|--------------------|--------------------|-------------|------|------------|---------|-----------------|--------------------|-----------------|----------------|
| S&P DJI quarterly PDFs (live) | Events/PIT | Yes | 2023-06-02 | 2026-06-05 | Per-event | Yes | Yes | No | No | No | No | Stable URL | S&P; review | URL+archive | `[CONDITIONAL]` | content for full history |
| S&P DJI corpus (Wayback) | Events/PIT | Yes | 2013-12-11 (artifact); CDX floor 2013-04-16 | 2022-06-03 (URL level) | Not yet per-event | Artifact-bound | Artifact-bound | No | No | No | No | CDX ts (floor) | S&P content | capture-ts pin | `[CONDITIONAL]` | per-event content `[UNVERIFIED]`; corpus completeness |
| press.spglobal.com + PRNewswire | Events/PIT | Yes | 2023-09-01 | 2026-09-04 | Yes | Yes | Yes | No | No | No | No | dated URL | S&P/PRN; bulk terms `[UNVERIFIED]` | URL pin | `[CONDITIONAL]` | harvest terms |
| S&P 600 index page (live + Wayback) | Membership roster | Yes | 2012-09-17 (snapshot) | 2026-09-10 | Snapshot-only | No | No | No | No | No | No | capture | S&P terms | capture pin | `[CONDITIONAL]` | roster completeness in old snapshots |
| SEC EDGAR N-PORT (iShares Trust 0001100663) | Roster snapshot | Yes | ~2019 (N-PORT regime) | 2026-08-27 (filed) | Filing-ts | No | No | No | No | No | No | accession | public | accession pin | `[CONDITIONAL]` | roster↔index parity `[UNVERIFIED]` |
| SEC EDGAR N-CSR/N-Q (pre-2019) | Roster snapshot | Yes | regime-level `[UNVERIFIED]` | 2019 | Filing-ts | No | No | No | No | No | No | accession | public | accession pin | `[CONDITIONAL]` | per-fund depth `[UNVERIFIED]` |
| pitindex | Membership/events | Yes | sp500 2005, sp400 2011-11, sp600 2021-03 | present | Upper-bound dates | No | Upper-bound | No | No | No | No | repo | MIT+CC BY-SA | SHA pin | `[CONDITIONAL]` | pre-2021 600 absent; removals gap |
| fja05680/sp500 | Membership | Yes | 1996 | present | Diffs | No | Yes (diff) | No | No | No | No | repo | MIT | SHA pin | `[CONDITIONAL]` | S&P 500 only |
| NYU Wurgler | Events | Yes | 1976 | 2000 | Two dates | No | Yes | No | No | No | No | static | academic | static | `[ACCEPT]/[CONDITIONAL]` | 500 only; ends 2000 |
| Wikipedia changes tables | Membership/events | Yes | ~2014 | present | Effective-only | No | Yes | No | No | No | No | `oldid` | CC BY-SA | oldid | `[CONDITIONAL]` | deletions incomplete |
| Stooq / AV / yfinance | Prices/ADV (active) | Yes (tiers) | vendor-dependent | present | Mutable | — | — | No | No | No | Partial | archive-at-retrieval | personal/registered/ToS | archive | `[CONDITIONAL]`/`[REJECT]` deep | vendor close; mutable |
| Kaggle Arandkei | Delisted OHLCV | Yes | created 2026; range `[UNVERIFIED]` | n/a | n/a | — | — | Claimed but `[UNVERIFIED]` | No | No | No | Kaggle version | **`[UNVERIFIED]`** | version pin possible | `[UNVERIFIED]` | license + coverage + provenance |
| SEC EDGAR Form 25/25-NSE | Delisting events | Yes | 2006-05 | present | Filing-ts | — | Delist-date | events only | Yes (delist) | No | No | accession | public | accession pin | `[ACCEPT]` | no prices |
| securitiesdb splits/dividends | CA | Yes | n/a | 2026-06-11 (update stamp) | None | — | ex-date field | No | splits/dividends | No | No | none | as-is; upstream unknown | none | `[UNVERIFIED]` | depth/coverage/adjustment |
| S&P U.S. Indices Methodology | Filter rule reference | Yes | 2012/2013 era | Jul 2026 | defines window | evaluation date | — | — | — | IWF/FALR rule | — | static | S&P | doc pin | `[ACCEPT]` (reference) | not a data source |
| OpenFIGI / SEC CIK | Identity | Yes | current | current | current only | — | — | No | No | No | No | versioned | MIT/Apache / public | pin | `[CONDITIONAL]`/`[ACCEPT]` | not historical PIT |
| Paid providers (EODHD/Sharadar/…, CRSP, Norgate, QC+AlgoSeek, Siblis) | All missing layers | **No** | — | — | — | — | — | Paid | Paid | Paid | Paid | — | — | paid | — | `[REJECT]` (at $0) | $0 budget |

---

## 13. FINAL D1 READINESS CHECKLIST

Semantics (§15): `READY` = all critical requirements demonstrated · `CONDITIONAL` = plausible route,
material requirement unresolved · `NOT READY` = critical requirement not demonstrated ·
`NOT SUFFICIENT AT $0` = no credible free path · `UNVERIFIED` = insufficient evidence.

| # | Requirement (frozen design) | Status | Impact |
|---|------------------------------|--------|--------|
| 1 | Composite 1500 identity reconstructable | `CONDITIONAL` (2013+ union reconstructable in principle; completeness unproven) | Critical |
| 2 | S&P 600 coverage sufficient | **OPEN** — 2013+ conditional and partial; pre-2013 `[UNVERIFIED]`; corpus completeness unproven | Critical |
| 3 | Event additions reconstructable | `CONDITIONAL` (announcements 2013+ + rosters) | Critical |
| 4 | Event deletions reconstructable | `CONDITIONAL` (announcements + Form 25; delisted-price gap) | Critical |
| 5 | Announcement/effective chronology proven | `CONDITIONAL` — per-event proof outstanding (2013–2022) | Critical |
| 6 | PIT requirements satisfied | **OPEN** — full-corpus PIT not executed; hard rule ⇒ invalid otherwise | Critical |
| 7 | Delisted-security price coverage sufficient | **OPEN** — `NOT SUFFICIENT AT $0` certifiable; frozen §27G exclude mitigant in place but coverage consequence unratified | Critical |
| 8 | Corporate actions sufficient | `CONDITIONAL` (delistings `[ACCEPT]`; splits/dividends `[UNVERIFIED]`) | Critical |
| 9 | ADV eligibility reproducible | `CONDITIONAL` (active names, free OHLCV) | Non-critical/partial |
| 10 | **Free-float PIT eligibility reproducible** | **OPEN** — `UNVERIFIED`; no free historical float ⇒ blocks `READY` | **Critical — decisive** |
| 11 | Provenance established | `CONDITIONAL` (archive-at-retrieval + pinned artifacts not yet executed) | Critical |
| 12 | License/access established | **OPEN** — 2 `[UNVERIFIED]` licenses (Kaggle, securitiesdb) + S&P publication review | Critical |
| 13 | Reproducibility established | `CONDITIONAL` (requires archival discipline) | Critical |
| 14 | No survivorship-bias breach | **OPEN** — delisted prices absent at $0; exclude-rule reduces, does not certify | Critical |
| 15 | No unresolved source-binding issue | **OPEN** — NO source formally bound; no P-IT ingestion contract exists | Critical |
| 16 | Quarantine disjointness enforceable | `CONFIRMED` (structural; no dates chosen yet) | Non-critical |
| 17 | Blind window establishable later | `CONFIRMED` (conceptually) | Non-critical |
| 18 | No specification drift | `CONFIRMED for this task` (nothing changed); at dataset level subject to 1–15 | Non-critical |

**Multiple CRITICAL items are OPEN (2, 6, 7, 10, 12, 14, 15). Therefore: `D1 = NOT READY /
CONDITIONAL`.** No "mostly ready" state is created; `READY` is not claimed. [NON-NORMATIVE — decision-grounding]

---

## 14. HUMAN DECISION REGISTER

All statuses: **`PROPOSED / PENDING HUMAN RATIFICATION`** — nothing is marked HUMAN-ACCEPTED unless an
actual human acceptance record exists. Proposed defaults are this document's recommendation ONLY.

| Decision ID | Decision | Proposed default | Governance impact | Current status | Evidence required | Can implementation proceed? |
|-------------|----------|------------------|-------------------|----------------|-------------------|-----------------------------|
| **D1-A** | Constrained research window (~2013-12 → present, quarterly reconstitution, Composite 1500) | ACCEPT **as a CONDITIONAL research window** for DATA-FEASIBILITY validation only | Narrows temporal scope; changes NOTHING else; does NOT make D1 READY; does NOT authorize HYP_003/R1 | `PROPOSED / PENDING HUMAN RATIFICATION` | Corpus-completeness reconciliation + roster-parity validation, then re-audit | NO — data-feasibility engineering only, after ratification |
| **D1-B** | Filter semantics (frozen ADV/float proxies vs. S&P FALR/IWF methodology) | RETAIN FROZEN PROXY (`ADV ≥ $5M`, `Free Float ≥ 20%`); record official-methodology difference as KNOWN METHODOLOGICAL CAVEAT | No spec change now; any future FALR/IWF adoption = separate spec-change decision | FROZEN (2026-09-07); caveat acknowledgment `PROPOSED` | Human acknowledgment of the caveat (no new evidence) | NO — no implementation relevant; proxy stays frozen |
| **R-1 (B2)** | Accept reduced/uncertified deletion-leg coverage under frozen §27G exclude rule for the constrained window | ACCEPT the exclude-rule consequence as documented limitation for feasibility purposes (no spec change) | Affects D1 READY-ness of the deletion leg; must not be framed as "delisted prices solved" | `PROPOSED / PENDING HUMAN RATIFICATION` | `T_eff(leg) ≥ 25` feasibility on the deletion leg from reconstructed events | NO — measurement only, after ratification |
| **R-2 (B2 alt)** | Authorize paid delisted-price path (crucial gap) | NOT RECOMMENDED at this step (violates `$0`); listed as Human Governance Option B (§15) | Spec/cost change if chosen | `PROPOSED / PENDING HUMAN RATIFICATION` | Cost + license + coverage from vendor | NO until ratified |
| **R-3 (B5)** | Free-float PIT treatment | Keep filter FROZEN → B5 stays `UNVERIFIED` → D1 stays NOT READY; OR ratify a spec change (e.g., documented float-proxy or filter relaxation) — human-only | Directly decides whether D1 can become READY at $0 | `PROPOSED / PENDING HUMAN RATIFICATION` | Free historical IWF/float existence (unlikely) OR explicit spec-change ratification | NO — data/build cannot proceed on float until ratified |
| **R-4 (B6)** | License/provenance gate | Require (a) archive-at-retrieval + provenance manifest engineering, (b) human/legal clearance for Kaggle, securitiesdb, and any S&P-derived publication, before any build | Provenance/license/reproducibility of the eventual dataset | `PROPOSED / PENDING HUMAN RATIFICATION` | License evidence per cleared source | NO until ratified |

No alternative data source, event window, narrower universe, different date range, different cost
model, or improved design discovered here is implemented (§17 rule); all remain HUMAN GOVERNANCE
OPTIONS below. [NON-NORMATIVE]

---

## 15. REMAINING BLOCKING CONDITIONS

| # | Blocking condition | Evidence gap | Why it matters | What would resolve it | Plausible at $0? | Human Governance Options (NOT selected here) |
|---|--------------------|--------------|----------------|-----------------------|------------------|----------------------------------------------|
| 1 | **B5 free-float PIT** | No free historical PIT float/IWF. Current float unusable for history | Frozen eligibility filter cannot be reproduced → dataset fails PIT hard rule | Free historical float source (unlikely) OR specification change for the float filter | NO (source); YES is a human decision | Option A/C/D |
| 2 | **B2 delisted-price coverage** | Certified free delisted OHLCV absent; Kaggle license/coverage `[UNVERIFIED]` | Deletion-leg `T0+h` coverage cannot be verified; survivorship-bias breach risk | License-cleared + coverage-verified free delisted dataset; or frozen exclude-rule acceptance (unresolves the *certification*, not the gap) | PARTIAL (frozen §27G mitigant) / NO (certification) | Option A/B (paid), D |
| 3 | **Pre-2013 S&P 600 (and pre-2011 400) membership** | No verified free source before 2013-12 (600) | Composite 1500 identity not reconstructable before window start | Free archive discovery; or move window start (a temporal spec choice) | UNVERIFIED | Option C (narrower window), D |
| 4 | **Announcement-corpus completeness + per-event PIT (2013–2022)** | Per-document content/chronology not individually verified | `PIT PROVEN` cannot be claimed for unreviewed events; hard rule ⇒ invalid obs | Execute full retrieval + parse + a no-missingness reconciliation | YES (effort, not money) | Option A/C |
| 5 | **Fund-holdings ↔ index parity (B1 roster leg)** | EDGAR rosters = ETF holdings, not certified index membership | Roster reconstruction validity for 400/600 not demonstrated | Parity validation vs announcement deltas + page snapshots | YES (effort) | Option A/C |
| 6 | **Structured split/dividend CA history (B4)** | Free APIs `[UNVERIFIED]` depth/coverage/adjustment | CA ordering + adjusted-price PIT requirement | Verify securitiesdb/alternative free records; or exclude affected windows | PARTIAL | Option A, D |
| 7 | **License/provenance (B6)** | Kaggle + securitiesdb licenses `[UNVERIFIED]`; S&P-derived publication terms | B6 gate fails; redistribution/derivation legally unsafe without review | Human/legal clearance or substitute sources | YES (there is a legal-review cost but no data cost) | Option A |
| 8 | **No source binding / no ingestion contract** | None of the events/prices/CA sources is formally bound | Unbound sources cannot support `planned_trial_count == grid_cardinality` or reproduceability | Human ratification of bindings + canonical P-IT ingestion contract | YES (engineering) | Option A |

**Human Governance Options (per §31 — NOT selected by this document):**
- **Option A — retain full Composite 1500 + seek additional free data** (continue source hunting).
- **Option B — authorize a paid data path** (violates `$0`; requires human budget change).
- **Option C — authorize a narrower historical window** (e.g. start later than 2013-12; temporal-only).
- **Option D — authorize a specification change** (universe, filters incl. float, event definitions).
- **Option E — terminate/archive F-1.**
- (Any combination ratified by the human.)

---

## 16. GOVERNANCE BOUNDARY / STOP

- This document is `[NON-NORMATIVE]` `[DOCUMENTATION-ONLY]` `[D1 FINAL FEASIBILITY REASSESSMENT]`
  `[HUMAN GOVERNANCE REQUIRED]`. It performs NO implementation, NO analysis of results, NO gate
  invocation, NO trading authorization, NO spend.
- **No empirical strategy work was produced:** zero backtests, returns, Sharpe, IC, HAC,
  optimization, parameter search, cost testing, alpha/performance/profitability numbers. Only data
  coverage, archive counts, date ranges, and source-completeness evidence appear. [VERIFIED]
- **No code/schema/gate/ROADMAP/registry/manifest change:** `src/`, `tests/`, `schemas/`, `gates/`,
  ROADMAP, register, runtime all untouched. Single new file: this document. [VERIFIED]
- **D1-A (window) and D1-B (filters) are PROPOSED defaults; neither is binding.** No decision in
  this register is marked HUMAN-ACCEPTED. [VERIFIED]
- **`D1 READY` is NOT authorized** — the checklist (§13) has open critical items; and per §32,
  even a future `READY` would NOT itself authorize D2. Human Governance must explicitly authorize the
  next stage.
- **Git policy honored:** NO add/commit/push/fetch/pull/merge/rebase/reset/revert/stash this task.
  Final expected state: repository unchanged + one new untracked
  `docs/phase14/f1_d1_final_feasibility_reassessment.md`. [VERIFIED at completion]

**Canonical governance state at completion (unchanged):**
`F-1 = S&P Composite 1500 (CAND-FLOW-CALENDAR-REBALANCE-001) · D1 = NOT READY / CONDITIONAL ·
D2 = LOCKED · HYP_003 = NOT AUTHORIZED · R1 = NOT AUTHORIZED · GATE = NOT AUTHORIZED · TRADING =
LOCKED · CAPITAL = $0.00`

### Verification Ledger (this document)
- Implementation Status: NONE (documentation-only; single new untracked file; `src/` untouched).
- Contract Enforcement: STRICT FAIL-CLOSED — every unverifiable claim `[UNVERIFIED]`; Kaggle license
  re-checked and NOT promoted; no freeze inference "free/public/download → licensed"; no
  PIT claim beyond artifact-presence; no [VERIFIED FACT] without a primary artifact.
- Mathematical Authority: N/A for data feasibility; canonical gate floors untouched.
- Evidence Baseline: carried from the three phase-14 documents (no conflicts found, §2); new
  verification today: Kaggle page (unrenderable → `[UNVERIFIED]`), Wayback 2013-12-11 capture
  presence (3 captures, 2021-02-25 → 2026-06-01).
- Local Test Suite: NOT RUN (documentation-only convention).
- Remote CI Status: NOT AVAILABLE.
- Methodological Caveats: Wayback depth is a floor not a ceiling; per-event PIT (2013–2022),
  fund↔index roster parity, free-float PIT, delisted-price certification, and two undetermined
  licenses remain open; any 2013+ reconstruction is DATA-FEASIBILITY scope only and stays outside
  HYP_003/R1/gate authority until human ratification.

STOP — F-1 D1 FINAL FEASIBILITY REASSESSMENT COMPLETE. NO D2 / HYP_003 / R1 / GATE / TRADING AUTHORIZATION.
HUMAN GOVERNANCE DECISIONS (D1-A, D1-B, R-1…R-4) REMAIN PENDING RATIFICATION.