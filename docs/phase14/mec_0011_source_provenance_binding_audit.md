# MEC-0011: SOURCE / PROVENANCE BINDING AUDIT

**Document ID:** `docs/phase14/mec_0011_source_provenance_binding_audit.md`
**Object:** Resolution of the SOURCE / PROVENANCE layer for MEC-0011: B1 (gold licensing binding), B2 (ICE DXY provenance/licensing), B3 (ICE DXY historical archive/reproducibility). Feasibility-state assessment only.
**Status:** `[DOCUMENTATION-ONLY]` `[SOURCE LAYER AUDIT]` `[NOT EMPIRICAL VALIDATION]` `[NOT HYP_003]` `[NOT R1]` `[NOT A CANDIDATE]`
**Date:** 2026-09-10 (retrieval date for all evidence)
**Authority:** Human operator (decisions per `mec_0011_human_ratification.md`)
**ASCII-only:** YES (no non-ASCII bytes)

## 1. SCOPE

- Resolve ONLY the source/provenance layer of MEC-0011: B1, B2, B3.
- Research/documentation of public source metadata, licensing, provenance, and archive/access
  characteristics is permitted. NO empirical activity: no download or processing of market data for
  analysis, no returns/correlations/lead-lag/IC/Sharpe/p-values/performance, no backtest, no
  parameter optimization.
- This document does NOT proceed into empirical validation and does NOT authorize it.

## 2. RATIFIED DECISIONS (CARRIED FORWARD)

- D1 = A: Gold leg = Stooq XAUUSD under documented private/non-commercial research usage, subject
  to licensing documentation and archive-at-retrieval. `[HUMAN-ACCEPTED]` `[CONDITIONAL]`
- D2 = C: DXY identity = ICE U.S. Dollar Index. ICE DXY is the selected research identity; it is
  NOT an ACCEPTED data source; it remains a GREY SOURCE with provenance/licensing/access blockers.
  `[HUMAN-ACCEPTED AS RESEARCH IDENTITY]` `[NOT DATA-VALIDATION-READY]` `[GREY SOURCE]`
- D3 = B: Literal volume-divergence branch TERMINATED; price/relative-movement track retained.
  `[HUMAN-ACCEPTED]` `[TERMINATED SUB-MECHANISM]`
- Source documents: intake, feasibility audit, decision surface, ratification record,
  post-decision feasibility update.

---

## 3. B1 - GOLD LEG (STOOQ XAUUSD) BINDING

Direct fetch of `stooq.com/terms.html` on 2026-09-10 returned a JavaScript challenge; the literal
terms are therefore established via a Wayback Machine capture dated 2025-12-05
(`web.archive.org/web/20251205061217/https://stooq.com/terms.html`).

Facts now independently established from the archived literal text:
- 1.1: Terms may be changed at any time without notifying users. (Terms are time-bound to the
  capture; re-verify at retrieval.)
- 5.1: Stooq does not guarantee validity/error-free data; users responsible for own decisions.
- 5.2: Continuous access cannot be guaranteed.
- 5.3: "Redistribution of data found on the website is not allowed without the consent of Stooq."
- 6.1: S&P/DJ index data limited to personal, non-commercial purposes (clause pertains to S&P/DJ
  index data; NOT to the XAUUSD FX-pair series directly).
- 6.2: LME data: distribution/redistribution prohibited without prior written consent of LME.
- 7: Polish law governs cases not covered.
- Prior-audit note carried: Stooq OpenAPI metadata + independent community recordings characterize
  the service as free for non-commercial use; the literal all-data "personal-use only" wording was
  not present in this archived capture - the redistribution-consent rule (5.3) is the operative
  restriction.

Assessment against the ratified D1 frame (private research, non-commercial, archived, no
redistribution, archive-at-retrieval):
- Frame does NOT redistribute -> compatible with 5.3 (no Stooq consent needed for non-redistribution).
- Frame is non-commercial -> no conflict with any literal clause.
- Frame commits to archive-at-retrieval -> mitigates 5.2 (access not guaranteed) and 5.1 (no-guarantee).
- Frame does NOT rely on S&P/DJ or LME assets -> 6.1/6.2 irrelevant here.

PIT: `[PIT UNPROVEN]` (mutable DB, no vintage ids). Reproducibility: single-symbol CSV endpoint
`stooq.com/q/d/l/?s=xauusd&i=d&d1=YYYYMMDD&d2=YYYYMMDD` deterministic in form; subject to daily
quota, CAPTCHA/JS challenge behavior, and mandatory archive-at-retrieval. Method caveat carried:
early history fix-derived approximate OHLC.

B1 classification: `[CONDITIONAL]` - usable under the ratified frame; license wording now
independently established via archived capture (redistribution-consent rule verified); PIT remains
unproven; no upgrade to `[ACCEPT]`. No substitution of another gold source was considered.

## 4. B2 - ICE DXY PROVENANCE / LICENSING (HIGHEST PRIORITY)

Identity (official, verified from ICE published documents):
- Official name: ICE U.S. Dollar Index (trademark USDX). Administrator: ICE Data Indices, LLC.
  Base date March 1973 = 100.00; formula constant 50.14348112; geometric mean of six currencies
  (EUR 57.6%, JPY 13.6%, GBP 11.9%, CAD 9.1%, SEK 4.2%, CHF 3.6%); weights unchanged since the
  January 1999 Euro substitution (the ONLY basket change). DX futures launched 1985-11-20; index
  level backfilled to 1973.
- Distinct from: DX futures (derivative, basis to index), UUP (futures-tracking ETF with roll
  costs and expenses), Fed Trade-Weighted indexes (26 currencies, annually rebalanced, different
  base), ECB rates (single bilateral rates). These are NOT the ICE DXY identity.

Official access routes (verified from ICE developer catalog, IDI Terms & Conditions, methodology):
- Product: ICE Data Indices - Currency Indices (includes DXY). Delivery: ICE Connect, ICE Global
  Index Feed, ICE Consolidated History, ICE Data API, ICE Data Files. History since 1996 intraday,
  daily backfill to 1973. Distribution: subscription-based, per-contract pricing; no public price
  list for raw index data (indicative: $10K-25K+/yr per product for derived-data licenses; raw
  index subscription terms bilateral). Redistribution: prohibited without prior written consent of
  ICE Data (IDI T&C sections 10-11); IP notice: any use of USDX without express written consent
  is strictly prohibited.
- NO free official historical index-level download exists on ICE pages; ICE Report Center serves
  futures volume/OI (contract counts), not index levels.
- NO free institutional-research program was identified.

Fee status at $0: OFFICIAL ICE = NOT FREE. Third-party grey paths exist (Section 5) but carry
unresolved terms.

B2 classification: `[BLOCKED]` at $0 under current decisions. Official access is licensed/paid;
no legitimate $0 research-compatible ICE DXY license identified; grey sources remain
ToS-restricted/terms-unresolved.

## 5. B3 - ICE DXY HISTORICAL ARCHIVE / ACCESS

Free candidates and their binding characteristics (2026-09-10 evidence):

- Yahoo DX-Y.NYB / ^DXY: actual ICE DXY level via secondary distributor; history back to
  1971-01-04 (verified; pre-1985 values are back-calculated/reconstructed index levels, futures
  launched 1985); daily OHLC + AdjClose (AdjClose = Close); NY timezone. `[GREY]`: Yahoo ToS
  restricts automated extraction/commercial use; API endpoints historically changed; no
  deterministic archival; not PIT-safe. Archive: must self-archive at retrieval.
- Stooq DX.F: DXY-futures-derived continuous daily series (OHLC + Volume + OI), ~14k daily rows;
  close semantics at the free source unresolved (index close 7:15pm ET / 5pm ET Fridays since 2021
  vs DX futures settlement 14:59-15:00 ET VWAP). Personal-use license; redistribution per Stooq 5.3;
  provenance of the series not disclosed; CSV endpoint JS-challenged as of 2026-09-10. `[GREY]`.
- Barchart $DXY: actual DXY; free depth = ~2 years only; deep history (to 1980s daily) = paid
  Premier. `[REJECTED at $0]`.
- MarketWatch: 30-day free window only. `[REJECTED at $0]`.
- FRED: NO ICE DXY series exists (Fed-computed indexes only). `[REJECTED - identity mismatch]`.
- ECB eurofxref: exchange rates; DXY value only via reconstruction. `[REJECTED as substitute]
  [MODEL INFERENCE]`.
- UUP: DX-futures ETF; not index. `[REJECTED as substitute]`.
- Kaggle DXY datasets: user-contributed, provenance unknown (likely scraped), CC0 covers
  compilation only. `[REJECTED - provenance]`.
- Statista: paid. `[REJECTED at $0]`.
- Archive.org/Wayback: opportunistic captures, non-deterministic, not reproducible. `[REJECTED]`.
- Academic DOI'd DXY datasets: none found. `[REJECTED]`.

Close/session semantics (official): DXY calculated every 1 second, session ~Mon 6:00pm ET (T-1) to
Fri 7:15pm ET; since March 2021 calculation stops at 5:00pm ET Fridays. The trusted "daily close"
differs across sources; whether free sources serve the index close or the futures settlement is
undocumented -> close definition is an unresolved binding item.

B3 classification: `[BLOCKED]`. No free, deterministic, reproducible archive of genuine ICE DXY
historical daily index level exists at $0. The question "can this source be bound as a reproducible
research input?" has answer NO for currently-identifiable $0 paths without Human acceptance of a
grey/ToS-borne or reconstruction-formulation route.

---

## 6. SOURCE CANDIDATE MATRIX

| Candidate | Identity | Actual ICE DXY? | Authority | Historical depth | Access | License | Archive | PIT | Reproducibility | Status | Reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ICE Data Indices - Currency Indices | ICE U.S. Dollar Index | YES (official) | ICE Data Indices LLC | daily backfill 1973+; intraday 1996+ | paid subscription (ICE Connect/GIF/History/API/Files) | licensed; no redistribution w/o consent; trademarked | contractual archival allowed w/ subscription | official final values (post-1973 reconstructed) | HIGH via licensed channels | `[BLOCKED at $0]` | paid |
| ICE website / Report Center | index levels absent | n/a | ICE | n/a | free but no index-level data | n/a | n/a | n/a | n/a | `[REJECTED]` | futures volume/OI only, no levels |
| Yahoo DX-Y.NYB / ^DXY | ICE DXY level | YES (secondary) | Yahoo Finance | ~1971-01+ (pre-1985 reconstructed) | free/grey | ToS restrict automated/commercial; distribution barred | self-archive only; non-deterministic | `[PIT UNPROVEN]` | CONDITIONAL (endpoint churn) | `[CONDITIONAL GREY]` | ToS-borne |
| Stooq DX.F | DXY futures-derived | YES (futures close, semantics unclear) | Stooq | ~14k daily rows | $0 CSV (JS-challenged 2026-09-10) | personal use; redistribution per 5.3 (consent) | self-archive only | `[PIT UNPROVEN]` | CONDITIONAL | `[CONDITIONAL GREY]` | provenance undisclosed |
| Barchart $DXY | ICE DXY level | YES | Barchart | 2y free; deep paid (1980s+) | free shallow / paid deep | paid for depth | vendor archive | none | n/a at $0 | `[REJECTED at $0]` | deep history paid |
| MarketWatch DXY | ICE DXY level | YES | MarketWatch | 30-day window | free display | grey for download | self-archive | none | n/a | `[REJECTED at $0]` | shallow |
| FRED (TWEXBGS/DTWEXBTHL) | Fed trade-weighted indexes | NO | Federal Reserve | 1971/2006+ | free | permissive | deterministic | conditional vintage | HIGH | `[REJECTED-substitute]` | NOT ICE DXY |
| ECB eurofxref | spot FX reference rates | NO | ECB | 1999+ | free | attribution | deterministic | final for posted dates | HIGH | `[REJECTED-substitute] [MODEL INFERENCE]` | proxy only |
| UUP | DX-futures ETF | NO | Invesco | 2007+ | free/grey | ETF terms | self-archive | none | conditional | `[REJECTED-substitute]` | roll costs, not index |
| DX futures settlement | DX futures | NO (near-proxy, basis) | ICE Exchange | paid backfill | paid/vendor | exchange license | vendor | n/a | via vendor | `[REJECTED-substitute at $0]` | basis to index |
| Kaggle DXY datasets | DXY (scraped, unknown) | unclear | user-contributed | variable | free | CC0 on compilation only | self-archive | none | conditional | `[REJECTED]` | provenance unknown |
| Statista DXY | DXY | YES | Statista | monthly 1973+ | paid | subscription | vendor | none | n/a | `[REJECTED at $0]` | paid |
| Archive.org / Wayback | archived DXY pages | indirect | Archive.org | opportunistic | free | archive ToU | non-deterministic | none | POOR | `[REJECTED]` | not reproducible |
| Academic DOI'd datasets | DXY | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | `[REJECTED]` | none found |
| 6-FX reconstruction (formula) | DXY-equivalent | mathematically equivalent, NOT official | derived | 1973+ if FX history exists | $0 possible | depends on FX-leg licenses | self-archive | depends on legs | PROVABLE if legs bound | `[MODEL INFERENCE] path` | requires Human decision + 6 FX legs |

## 7. LICENSE ANALYSIS

- ICE official: paid + trademarked; redistribution and product use require written consent; no free
  research tier. `[VERIFIED]`
- Yahoo (^DXY/DX-Y.NYB): ToS bar automated extraction and commercial use; distribution barred;
  private non-commercial archival is the defensible reading, subject to Human acceptance. `[VERIFIED-as-risk]`
- Stooq (XAUUSD, DX.F): literal terms now archived-verified (2025-12-05 capture): 5.3 redistribution
  requires consent; 5.1/5.2 no data/access guarantee; terms changeable without notice. `[VERIFIED]
  [time-bound]`
- Barchart: personal-view free; deep history paid; Premier terms apply. `[VERIFIED]`
- FRED: Fed-computed indexes permissive - IRRELEVANT to ICE DXY identity (wrong index). `[VERIFIED]`
- ECB: free reuse with attribution - proxy identity only. `[VERIFIED]`
- LME clause (Stooq 6.2) and S&P/DJ clause (Stooq 6.1): pertain to other asset classes, noted to be
  out of scope for XAUUSD/DXY use.

## 8. PIT ANALYSIS

- No candidate provides true vintage-based PIT in the Dolt sense. PIT for MEC-0011 is defined as
  the ability to reconstruct values "as known at a past date."
- DXY official post-1973 values are currently published backwards-looking index levels; the
  pre-1985 segment is reconstructed (not as-published at the time). No free archive offers
  vintage-specific DXY levels.
- Stooq/Yahoo are mutable, revision-prone, no vintage -> `[PIT UNPROVEN]`; archive-at-retrieval is
  the only path to any provenance claim.
- Confirmed requirement: for whichever source is eventually bound, capture raw bytes + timestamp +
  source version at retrieval; PIT must be proven by archive evidence, never by assertion.

## 9. REPRODUCIBILITY

- Deterministic at $0: NOT met for any ICE DXY candidate. Yahoo (endpoint churn), Stooq (JS
  challenge + quota), Barchart (paid deep), MarketWatch (shallow), archive.org (opportunistic).
- Deterministic via licensed channels: ICE Data Files/API (not $0).
- The 6-FX reconstruction path could be made reproducible if (and only if) its six FX input legs
  are each individually bound to a free licensed source and archived; that path is a future
  formulated candidate, NOT a current data source.
- Archive-at-retrieval remains mandatory for whatever leg(s) become bound.

## 10. NO-SILENT-SUBSTITUTION ENFORCEMENT

Repeated and enforced (binding governance rule):
- The selected research identity is ICE DXY.
- Fed dollar indexes (TWEXBGS/DTWEXBTHL) != ICE DXY.
- ECB reconstruction != ICE DXY.
- UUP != ICE DXY.
- DX futures != ICE DXY.
- Any other dollar proxy != ICE DXY.
- Gold spot/XAUUSD level != COMEX gold futures volume != GLD volume.
- No substitution is permitted without a NEW explicit Human decision. None may be introduced to
  overcome data availability.
- This audit did not adopt any substitute; grey/rejected candidates appear above only to document
  their identity status and exclusion.

## 11. BLOCKER CLASSIFICATION

- B1 Gold licensing/usage binding: `[CONDITIONAL]` - frame compatible with archived literal terms
  (no redistribution, non-commercial, archive-at-retrieval); Stooq terms time-bound; PIT unproven.
- B2 ICE DXY provenance/licensing: `[BLOCKED]` - official access licensed/paid; no free
  research-compatible license identified; grey routes terms-unresolved and ToS-borne.
- B3 ICE DXY historical archive/access: `[BLOCKED]` - no free deterministic reproducible historical
  archive of genuine ICE DXY index level exists at $0.

### ICE DXY BLOCKER REPORT

Exact unresolved issues (B2+B3):
- I1: No free, license-clean source of ICE DXY index LEVELS for historical research (official = paid;
  grey = ToS-borne/unproven provenance).
- I2: Close/session definition ambiguity across free sources (index close 7:15pm ET / 5pm ET Fridays
  since 2021 vs DX futures settlement 14:59-15:00 ET VWAP); which level free sources serve is
  undocumented.
- I3: Pre-1985 values are reconstructed index backfill; reconstruction methodology not published by
  free sources.
- I4: 1999 basket change (EUR replaced DEM/FRF/ITL/NLG/BEF) discontinuity handling by free archives
  is unverified.

Evidence required to resolve:
- E1: A source with (a) verified ICE DXY identity, (b) documented license terms compatible with
  the research frame, (c) a deterministic retrieval contract, (d) documented close/session and
  method-change semantics, (e) stable archiving.
- E2: OR a Human-accepted Grey path with explicit documented acceptance of ToS risk, private
  archive-only constraint, and provenance labeling.
- E3: OR a resource to license official ICE data (budget authorization per program charter).

Possible legitimate resolution paths (NOT selected for the Human):
- P1: ICE Data Indices subscription (paid; institutional/commercial research; requires Human budget
  authorization; redistribution restricted). Requires Human decision. PAID.
- P2: Authorized redistributor already accessible to Human (e.g., Bloomberg/Refinitiv/FactSet-type
  terminal or Databento-type API, if present) - licensed vendor route. Requires Human decision;
  requires existing vendor access. PAID/VENDOR.
- P3: Human-accepted Grey path (e.g., Yahoo ^DXY) under private, non-commercial, no-redistribution,
  archive-at-retrieval frame with explicit ToS-risk acceptance and `[GREY SOURCE]` labeling on all
  downstream artifacts. Requires Human decision (this is the open option-C condition from the
  decision surface). $0, ToS-borne.
- P4: Stooq DX.F under a ratified grey frame (futures-derived; close semantics must be resolved;
  provenance undisclosed). Requires Human decision. $0, ToS-borne.
- P5: 6-FX reconstruction from licensed free FX rate legs using the ICE-published formula, producing mathematically equivalent values, NOT official ICE data; would become a new formulated reconstruction object requiring its own binding of six FX legs and explicit `[MODEL INFERENCE]` identity framing. Requires Human decision; may still need paid/licensed FX history for deep depth. $0-possible in principle, multi-leg.
- Paths not recommended are: Kaggle (provenance), archive.org (non-deterministic), Barchart/
  Statista (paid depth), FRED/ECB/UUP/DX (identity-excluded).

This report does not choose any path. Each requires an explicit Human decision; P1/P2 require
licensed/paid data or budget authorization.

## 12. DOWNSTREAM IMPACT (REMAIN BLOCKED / NOT PREMATURELY RESOLVED)

- B4 Timestamp/calendar binding: BLOCKED - depends on the bound ICE DXY source's session/close
  semantics and on a US/NYSE-vs-session merge policy; no solution invented here.
- B5 Method-history/splice handling: BLOCKED - 1999 basket change, pre-1985 reconstruction, close
  convention, gold Fixing->Auction (2015-03-20); none resolved.
- B6 PIT/archive methodology: BLOCKED - archive-at-retrieval mandatory but no source archived yet;
  no PIT claimed.
- B7 Deterministic research specification: BLOCKED - not started; would depend on the resolved
  DXY binding.
- B8 Pre-registration: BLOCKED - not started.
- B9 Archive + manifest: BLOCKED - no manifest exists; mandatory for every future bound leg.
- B10 Explicit Human empirical-validation authorization: BLOCKED - NOT granted; D1-D3 do not
  constitute it.

None of B4-B10 is resolved by this audit. They are downstream of B2/B3.

## 13. HUMAN DECISIONS STILL REQUIRED

- HD-1: Confirm the B1 gold-frame documentation (this audit section 3 + ratification record) as the
  binding usage/license record for Stooq XAUUSD. `[HUMAN DECISION REQUIRED]`
- HD-2: Select the B2/B3 resolution path among P1-P5 (or defer). `[HUMAN DECISION REQUIRED]` - no
  path selected by this audit.
- HD-3: If P3/P4 chosen: explicit Human acceptance of the grey provenance/licensing burden and the
  private-archive-only constraint. `[HUMAN DECISION REQUIRED]`
- HD-4: If P5 chosen: Human acceptance of the `[MODEL INFERENCE]` identity framing and the
  multi-leg FX binding requirement. `[HUMAN DECISION REQUIRED]`
- HD-5: Any future source-registry promotion of the bound source requires a separate,
  Human-authorized, evidence-backed `free_data_source_registry.md` update. `[HUMAN DECISION REQUIRED]`

## 14. FINAL SOURCE-LAYER CLASSIFICATION

- B1 (Gold binding): `[CONDITIONAL]`
- B2 (ICE DXY provenance/licensing): `[BLOCKED]`
- B3 (ICE DXY archive/access): `[BLOCKED]`

- **SOURCE LAYER STATUS = BLOCKED** (for the ICE DXY leg under current ratified decisions at $0).

Meaning: the MEC-0011 price/relative-movement track cannot advance to B4-B7 until B2/B3 are
resolved by an explicit Human path selection. This is a data-layer blockage, NOT a research
dead-end and NOT a green light. MEC-0011 is NOT empirically ready in any sense.

MEC-0011 remains: **RESEARCH INTAKE ONLY / NOT AUTHORIZED FOR EMPIRICAL VALIDATION**.

## 15. VERIFICATION LEDGER

- Implementation Status: N/A (documentation-only source/provenance binding audit; no code, no data,
  no download, no computation)
- Contract Enforcement: STRICT FAIL-CLOSED - no source accepted for the ICE DXY leg; no substitution;
  no registry promotion; no PIT claimed; no path selected for the Human
- Mathematical Authority: CANONICAL SPEC cited for ICE DXY formula/methodology (ICE published docs);
  no formulation claimed by MEC-0011
- Local Test Suite: NOT RUN (no code touched)
- Type Checker (MyPy): NOT RUN (no code touched)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: Stooq terms established from 2025-12-05 Wayback capture (time-bound; re-verify
  at retrieval); ICE official data products verified from ICE public catalog/T&C with pricing partly
  conditional (raw index subscription terms bilateral; derived-data figures indicative); Yahoo/Stooq grey
  paths are ToS-borne; pre-1985 DXY values are reconstructed backfill; SOURCE LAYER STATUS = BLOCKED;
  all downstream binding items (B4-B10) remain open; MEC-0011 remains RESEARCH INTAKE ONLY /
  NOT AUTHORIZED FOR EMPIRICAL VALIDATION.