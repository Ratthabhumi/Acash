# MEC-0011: HUMAN DECISION SURFACE - POST $0 DATA FEASIBILITY AUDIT

**Document ID:** `docs/phase14/mec_0011_human_decision_surface.md`
**Object:** Explicit Human-only decision surface converting the completed MEC-0011 $0 Gold/DXY data-feasibility audit into recorded, ratifiable decisions. No decision is resolved by the agent in this document.
**Status:** `[HUMAN DECISION REQUIRED]` `[DOCUMENTATION-ONLY]` `[NOT EMPIRICAL VALIDATION]` `[NOT HYP_003]` `[NOT R1]` `[NOT A CANDIDATE]`
**Date:** 2026-09-10 (retrieval date for all carried-forward claims)
**ASCII-only:** YES (no non-ASCII bytes)

## Classification labels in use

- `[VERIFIED]` - confirmed by fetched evidence (provider/official pages) on the audit date.
- `[ACCEPT]` - registry-grade acceptance classification (none granted by this document).
- `[CONDITIONAL]` - feasible under explicit conditions; conditions must each be met and documented.
- `[UNVERIFIED]` - not independently confirmed; never upgraded merely because accessible.
- `[NOT FEASIBLE AT $0]` - feasibility verdict at zero cost (volume-divergence branch).
- `[MODEL INFERENCE]` - agent/human model-level construction, NOT a documented fact.
- `[HUMAN DECISION REQUIRED]` - unresolved; a Human must select without an implied default.

No finding status from the audit is upgraded by this document.

---

## 1. SCOPE AND NON-AUTHORIZATION

- This document is the explicit decision surface for MEC-0011 following completion of:
  - `docs/phase14/mec_0011_gold_dxy_relative_movement_intake.md` (intake record), and
  - `docs/phase14/mec_0011_gold_dxy_data_feasibility_audit.md` (feasibility audit).
- MEC-0011 remains: **RESEARCH INTAKE ONLY / NOT AUTHORIZED FOR EMPIRICAL VALIDATION**.
- This document does NOT perform, authorize, or imply: backtest, empirical validation, parameter optimization, signal testing, performance calculation, or strategy execution.
- This document does NOT: create HYP_003; modify HYP_001/HYP_002 status; invoke ResearchReInceptionGate; authorize R1; modify canonical trading/gate governance; modify capital state; modify phase-6 gate.
- This document does NOT modify any canonical registry `docs/phase14/free_data_source_registry.md` (or any other registry), MACRO-001 documents, F-1 documents, HYP registries, or any source/code/test files. Expected scope: documentation-only.

---

## 2. AUDIT FINDINGS BEING CARRIED FORWARD

Carried forward verbatim-classified from `mec_0011_gold_dxy_data_feasibility_audit.md` (2026-09-10). No status upgraded.

| # | Finding | Classification (carried forward) |
|---|---|---|
| F1 | Gold/DXY inverse relationship; nonlinear/regime-dependent; dollar-channel incremental explanatory power for gold returns | `[VERIFIED]` (background) |
| F2 | DXY -> gold lead-lag direction and stability | `[VERIFIED]` mixed / remains a research question; classed `[UNVERIFIED]` for any stable tradable rule |
| F3 | "small DXY pullback -> massive gold push" as a repeatable rule; volume-mismatch predictive power; profitability | `[UNVERIFIED]` (source claim only) |
| F4 | Stooq XAUUSD = only deep daily ($0) gold price leg: OHLC ~1968+, run present | `[VERIFIED]` series / start + license `[CONDITIONAL]` |
| F5 | FRED gold fix series (GOLDAMGBD228NLBM/PM) deleted 2022-01-31 (IBA licensing) | `[NOT FEASIBLE AT $0]` / `[VERIFIED]` delisted |
| F6 | LBMA/IBA historical daily fix: licence/portal-gated; IBA licence for commercial/redistribution | `[CONDITIONAL]` (not a bulk-free historical source) |
| F7 | CME/COMEX historical settlement/volume: paid (DataMine); today-only free | `[NOT FEASIBLE AT $0]` for historical |
| F8 | FRED Fed dollar indexes (TWEXBGS / DTWEXBGS / TWEXMTHY family): official, free, deterministic; DTWEXBGS->TWEXBGS splice required; NOT ICE DXY | `[ACCEPT]`-class official / splice `[CONDITIONAL]` / identity = Fed index `[VERIFIED]` |
| F9 | ECB eurofxref reconstruction of a DXY-like level: free, attribution; historical 1999+; weight-vintage burden; is NOT ICE DXY | `[VERIFIED]` licensing / `[MODEL INFERENCE]` as DXY proxy |
| F10 | ICE DXY official index data = paid product | `[NOT FEASIBLE AT $0]` officially |
| F11 | Yahoo CUY-NYB/^DXY (ICE DXY level) via unofficial endpoints: ToS-violating for automated/archival use | `[CONDITIONAL]` grey only |
| F12 | DXY index has NO native volume (computed benchmark) | `[VERIFIED]` |
| F13 | Daily exchange-grade gold volume (COMEX): no free full history; CFTC COT = weekly open interest only (not volume); SGE daily shallow/restricted; LBMA clearing monthly | `[NOT FEASIBLE AT $0]` for daily exchange-grade volume |
| F14 | GLD/IAU ETF daily volume and UUP/UDN ETF daily volume: obtainable via Stooq/Yahoo/SPDR channels; ETF share-turnover semantics; license caveats; not futures/OI/spot semantics | `[CONDITIONAL]` |
| F15 | GLD vs UUP pair = only near-$0 daily volume-pair candidate; both NYSE-listed US ETFs -> common microstructure confound; NOT the video's "volume mismatch" | `[CONDITIONAL]` (proxy, unverified as a mechanism) |
| F16 | Common daily timestamp achievable on a US/NYSE-trading-day calendar; calendar seams (gold London-only days; TARGET-vs-NYSE for ECB) need pre-registered merge policy | `[CONDITIONAL]`-achievable |
| F17 | No Gold or DXY source is ACCEPTED in free_data_source_registry.md; promotion requires a separate human-authorized registry update | `[VERIFIED]` (registry unchanged) |
| F18 | Overall verdicts: PRICE-ONLY = CONDITIONAL; VOLUME-DIVERGENCE = NOT SUFFICIENT AT $0 (canonical semantics) / CONDITIONAL only as GLD-vs-UUP reformulation | carried forward as above |

---

## 3. D1 - HUMAN DECISION: GOLD LEG LICENSE / USAGE FRAME

### DATA-1 (D1)

**DECISION ID:** D1
**QUESTION:** Under what licensing/usage frame is the gold price leg allowed (if pursued)?
**FACTS ESTABLISHED BY AUDIT:**
- Stooq `XAUUSD` is the strongest free Gold price candidate: daily OHLC, ~1968+, single continuous spot-style pair `[VERIFIED]` series; start and license `[CONDITIONAL]`.
- License: personal/non-commercial use; redistribution requires Stooq consent (literal English ToS page 404 - direction unambiguous across Stooq OpenAPI metadata and independent recordings) `[CONDITIONAL]`.
- Early history (1968-~1990s) is fix-derived approximate OHLC, not tick-grade `[CONDITIONAL]`.
- PIT: Stooq is a mutable DB with no vintage ids `[PIT UNPROVEN]`; archive-at-retrieval is mandatory (raw bytes + fetch timestamp) to make any later dataset reproducible.
- Method-history: London Gold Fixing -> IBA LBMA Gold Price auction (2015-03-20) is a regime/method change to be flagged, never silently spliced.
- FRED gold series are dead (2022); LBMA historical is licence/portal-gated; CME historical is paid. No redistribution-safe free daily gold series exists at $0.
- Number of viable streams at $0: exactly one (Stooq) for deep daily gold OHLC.

**OPTIONS:**
- A = accept Stooq under an explicitly documented non-commercial research frame (private research, archive-at-retrieval, no redistribution, no commercial use; document Stooq terms as a standing condition).
- B = reject Stooq and defer the gold leg until another compliant free source is found (no current $0 candidate; would require a future audit).
- C = other Human-specified source/frame (Human names the source and the terms they accept).

**HUMAN SELECTION:** `[HUMAN DECISION REQUIRED]`
**RATIONALE:** `[HUMAN DECISION REQUIRED]`
**DATE:** `[HUMAN DECISION REQUIRED]`
**AUTHORITY:** `[HUMAN DECISION REQUIRED]` (Human operator ratification)
**DOWNSTREAM EFFECT:**
- If A: gold leg qualified for private, non-commercial, archive-manifested research; next step is D2 (DXY leg) then a retrieval POC (still not validation).
- If B: the MEC-0011 price/relative-movement track is blocked on the gold leg until a compliant source appears; no empirical work possible on the price track.
- If C: mold to the specified frame with an explicit provenance/terms note; no changes to any registry by this document.

---

## 4. D2 - HUMAN DECISION: DXY LEG IDENTITY

### DATA-2 (D2)

**DECISION ID:** D2
**QUESTION:** Which dollar-index series becomes the DXY leg (or none this round)?
**FACTS ESTABLISHED BY AUDIT:**
- There is NO free official ICE DXY index level at $0. The three candidates are materially different instruments; substitution between them is a specification decision, NOT a convenience option.
- Explicit identity statements (do not conflate):
  - Fed dollar index != ICE DXY. (F8)
  - ECB reconstruction != ICE DXY. (F9)
  - ICE DXY via grey source is the only level close to the literal "DXY" the video references, and it is ToS-restricted. (F11)
- FRED Fed index (F8): official, deterministic download, free; requires documented DTWEXBGS->TWEXBGS splice and vintage handling; history 1971+ (with splice) / 2006+ (TWEXBGS alone).
- ECB eurofxref reconstruction (F9): free with attribution; 1999+; is a `[MODEL INFERENCE]` proxy; historical basket weights are not constant (EUR introduced 1999; periodic updates) - either freeze current weights for a modern-window study or track weight vintages (research burden); ECB reference rates are ECB-style reference mid-rates (~14:10 concertation, published ~16:00 CET), not DXY trading levels; TARGET working-day calendar differs from US/NYSE trading days.
- ICE DXY grey (F11): actual ICE DXY level via unofficial Yahoo endpoints; free in practice; ToS-barred for automated collection and distribution; only a private archive could be defensible, and only if Human explicitly accepts provenance and licensing.
- Timestamp: all candidates are daily; common-timestamp alignment is `[CONDITIONAL]`-achievable on a US/NYSE-trading-day calendar (F16).

**OPTIONS:**
- A = FRED Fed dollar index (TWEXBGS/TWEXBTHL family) with documented splice and method-change notes.
- B = ECB constituent reconstruction / DXY proxy (explicit `[MODEL INFERENCE]` framing; weight-vintage handling declared).
- C = ICE DXY grey source, ONLY if Human explicitly accepts its provenance/licensing and a private-archive-only constraint.
- D = defer DXY-leg selection to a later round (price track remains blocked on this leg in the meantime).

**HUMAN SELECTION:** `[HUMAN DECISION REQUIRED]`
**RATIONALE:** `[HUMAN DECISION REQUIRED]`
**DATE:** `[HUMAN DECISION REQUIRED]`
**AUTHORITY:** `[HUMAN DECISION REQUIRED]` (Human operator ratification)
**DOWNSTREAM EFFECT:**
- If A: the DXY leg is official and deterministic but is a Fed dollar index (study object must be re-labeled relative to the video's "DXY" claims; splice pre-registered).
- If B: a DXY-proxy object exists from 1999+; every downstream claim must be stamped `[MODEL INFERENCE]` (proxy, not DXY).
- If C: the literal DXY level is available only under an accepted grey/provenance burden and private-archive constraint; distribution/exports restricted.
- If D: price track waits; no later step that needs a dollar series can begin.

---

## 5. D3 - HUMAN DECISION: VOLUME BRANCH DISPOSITION

### DATA-3 (D3)

**DECISION ID:** D3
**QUESTION:** What happens to the literal volume-divergence branch of MEC-0011?
**FACTS ESTABLISHED BY AUDIT:**
- DXY has NO native volume by construction (computed benchmark) (F12).
- Daily exchange-grade gold volume (COMEX) has no free full history; the free alternatives are weekly OI (CFTC), monthly clearing (LBMA), or shallow/different-venue daily (SGE) (F13).
- Verdict carried: VOLUME-DIVERGENCE = NOT SUFFICIENT AT $0 (canonical/exchange-grade semantics); the sub-mechanism is NOT OPERATIONALIZED (F18).
- The only near-$0 daily volume-pair candidate is GLD (gold ETF) vs UUP (dollar ETF) share turnover (F14/F15). That pair is a DIFFERENT mechanism from the video's DXY-vs-Gold volume claim: ETF share turnover on both legs, both NYSE-listed US ETFs (common microstructure confound), and not futures/OI/physical volume. It may not silently substitute the video claim.
- No GLD/UUP intake exists; none is created by this document.

**OPTIONS:**
- A = PARK the literal volume-divergence branch; keep it as an unoperationalized research claim (no work, no claim of feasibility).
- B = TERMINATE the literal-volume branch as `[NOT FEASIBLE AT $0] / NOT OPERATIONALIZED`, while retaining the MEC-0011 price/relative-movement track (which stays subject to D1/D2).
- C = commission a NEW standalone GLD-vs-UUP volume-variant intake (distinct mechanism/variant; fresh intake + new Human decision surface; NOT silent substitution for the video claim). This document does NOT create that intake.
- D = defer.

**HUMAN SELECTION:** `[HUMAN DECISION REQUIRED]`
**RATIONALE:** `[HUMAN DECISION REQUIRED]`
**DATE:** `[HUMAN DECISION REQUIRED]`
**AUTHORITY:** `[HUMAN DECISION REQUIRED]` (Human operator ratification)
**DOWNSTREAM EFFECT:**
- If A: volume branch stays parked; MEC-0011 progress limited to the price track.
- If B: literal volume-divergence is closed as unsatisfiable at $0 (DXY has no volume); the price/relative-movement track remains the only active MEC-0011 line; no further volume work is performed unless a variant intake is later commissioned.
- If C: a new intake is authorized to be drafted (as a distinct mechanism, e.g., MEC-0011-variant), inheriting the same governance boundary; it does not modify MEC-0011's status.
- If D: no disposition; both branches stay as-is pending a later Human instruction.

---

## 6. DECISION DEPENDENCIES

- D1 and D2 are independent of each other in choice but COUPLED in the pipeline: BOTH must resolve before the MEC-0011 price/relative-movement track can take any data step. Neither is a precondition of the other.
- D3 (volume branch) is independent of D1 and D2 for dispositions A/B/D. If D3 = C (new GLD-vs-UUP variant), the variant inherits the SAME license-frame problem as D1 (Stooq/Yahoo/SPDR channels) - the variant intake must carry its own license/provenance decision, not silently reuse D1.
- D1/D2 do not unlock D3. D3 does not unlock D1/D2.
- No decision in this surface is a precondition of any empirical-validation request by itself (see Section 11).

## 7. WHAT REMAINS BLOCKED AFTER EACH POSSIBLE CHOICE

| Decision -> choice | Unblocked | Remains blocked |
|---|---|---|
| D1=A | gold leg usable privately (non-commercial, archived) for study design/POC | empirical validation, distribution, commercial use, HYP_003 |
| D1=B | nothing on the gold leg | price track gold leg until a compliant source exists |
| D1=C | gold leg per Human frame (as specified) | everything not specified by Human frame |
| D2=A | official deterministic daily dollar index (as Fed index, with splice) | ICE-DXY-literal claims; validation |
| D2=B | ECB-based DXY-proxy object 1999+ (as model inference) | DXY-literal claims; validation |
| D2=C | literal ICE DXY level (if Human accepts grey provenance) | distribution/exports; validation |
| D2=D | nothing on the dollar leg | price track dollar leg until later selection |
| D3=A | nothing new | literal volume branch remains unoperationalized (parked) |
| D3=B | price/relative-movement track as the only active MEC-0011 line | literal volume-divergence permanently (at $0) |
| D3=C | authority to draft a new standalone variant intake | all empirical work for the variant; validation |
| D3=D | nothing new | both branches pending later instruction |

## 8. NO-SILENT-SUBSTITUTION RULES

- Fed dollar index must never be labeled ICE DXY. (F8 identity)
- ECB reconstruction must never be labeled ICE DXY or Fed index; every downstream artifact must carry `[MODEL INFERENCE]`. (F9)
- ICE DXY grey must be labeled as to provenance/licensing whenever used; private-archive-only unless Human relaxes it. (F11)
- GLD/UUP volume must never be presented as the video's "DXY-vs-Gold volume mismatch". (F14/F15)
- Gold volume instrument families (COMEX futures / gold ETF / spot proxy / synthetic) are not interchangeable; cross-family comparison requires explicit semantics documentation. (F13/F14)
- No source is promoted into `free_data_source_registry.md` by this document; promotion requires a separate Human-authorized evidence update. (F17)
- Fix-derived early gold OHLC and the Fixing->Auction method change are flagged, never silently spliced. (D1 facts)

## 9. PIT / PROVENANCE IMPLICATIONS

- Every leg used later must be archived at retrieval (raw bytes + fetch timestamp + provider version). This is mandatory, not optional.
- Stooq `[PIT UNPROVEN]`; provenance = your own archive manifest. (D1 facts)
- FRED `[CONDITIONAL]` via ALFRED vintage layer; DTWEXBGS->TWEXBGS discontinuity must be versioned. (F8)
- ECB historical reference rates are final for posted dates; `[CONDITIONAL-PROVABLE]` via archive. (F9)
- Yahoo grey `[PIT UNPROVEN]` and silently mutable - if ever used, provenance rests entirely on your archive. (F11)
- Dolt-style versioning must not automatically be called PIT; PIT is proven by construction/archive evidence.

## 10. LICENSING IMPLICATIONS

- Stooq: personal/non-commercial; redistribution requires consent. D1 frame must name Stooq terms as a standing condition (option A) or replace it (B/C).
- FRED: permissive (Fed-computed series research-free); Fed index material generally redistributable under FRED terms.
- ECB: free reuse with attribution + disclosure of modifications (verified).
- ICE official: paid; not usable at $0.
- ICE DXY grey (Yahoo): ToS-bar automated collection/commercial use; private archive only, Human-accepted (D2=C).
- LBMA/IBA: benchmark IP; commercial/redistribution requires licence; non-commercial portal is conditional.
- CME DataMine: exchange licence + subscription; historical at $0 = not feasible.
- CFTC: public domain (weekly OI only; not volume).
- Any licensing decision made here applies to documented research use only; commercial use requires separate Human authorization.

## 11. CONDITIONS REQUIRED BEFORE ANY FUTURE EMPIRICAL-VALIDATION REQUEST

A future validation request for the MEC-0011 price/relative-movement track may be submitted (still not authorized here) only when ALL of the following are met:

1. D1, D2 selects are RECORDED with RATIONALE / DATE / AUTHORITY in this surface (or a successor surface). No implied default.
2. D3 disposition recorded (park / terminate / variant-intake / defer).
3. The chosen gold and dollar legs have a registered, evidence-backed source entry (separate Human-authorized registry update - NOT done by this document).
4. A pre-registered specification exists: instrument identity (whether Fed index / ECB proxy / grey ICE-DXY), calendar and merge policy (F16 seams handled), series-splice/method-change handling, K and multiple-testing doctrine (per canonical lineage or a declared separate doctrine), statistical protocol, IS/OOS/Blind split, cost model, and a fail-closed PASS/FAIL/INVALID rule.
5. Archive-at-retrieval manifest for every leg, before any analysis object is built.
6. No performance number, no signal test, no optimized parameter exists at the time of the request.
7. Human ratification of each of conditions 1-6 documented in writing.
- Nothing in this section authorizes any validation; it defines the entry conditions for a future REQUEST.

## 12. FINAL HUMAN RATIFICATION BLOCK

| DECISION ID | QUESTION | HUMAN SELECTION | RATIONALE | DATE | AUTHORITY |
|---|---|---|---|---|---|
| D1 | Gold-leg license/usage frame (A/B/C) | `[HUMAN DECISION REQUIRED]` | | | Human operator |
| D2 | DXY-leg identity (A/B/C/D) | `[HUMAN DECISION REQUIRED]` | | | Human operator |
| D3 | Volume-branch disposition (A/B/C/D) | `[HUMAN DECISION REQUIRED]` | | | Human operator |

Rules for completion:
- No implied default exists. `[HUMAN DECISION REQUIRED]` stays until a Human explicitly fills SELECTION / RATIONALE / DATE / AUTHORITY.
- After Human ratification, this surface may be updated in-place (recording selections) by the agent under explicit Human instruction; until then nothing is recorded as decided.
- This document does not modify any registry, and no empiricism is authorized by any selection above.

### Verification Ledger
- Implementation Status: N/A (documentation-only decision surface; no code, no data, no download, no computation)
- Contract Enforcement: STRICT FAIL-CLOSED - no decision resolved; no default implied; no registry promotion; no finding upgraded
- Mathematical Authority: N/A (carries only audit classifications; ECB proxy remains `[MODEL INFERENCE]`)
- Local Test Suite: NOT RUN (no code touched)
- Type Checker (MyPy): NOT RUN (no code touched)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: all carried-forward findings retain their audit-date (2026-09-10) classification; provider terms can change post-retrieval; no selection recorded; MEC-0011 remains RESEARCH INTAKE ONLY / NOT AUTHORIZED FOR EMPIRICAL VALIDATION.