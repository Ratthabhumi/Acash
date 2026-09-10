# MEC-0011: RESEARCH AUDIT CLOSEOUT

**Document ID:** `docs/phase14/mec_0011_research_audit_closeout.md`
**Object:** Formal closeout of the current MEC-0011 Gold/DXY research intake and source/provenance audit as a clean governance checkpoint, before returning to the CAND-FREE-MACRO-001 mainline.

```
[RESEARCH CHECKPOINT]
[SOURCE / PROVENANCE AUDIT]
[NON-AUTHORIZATION RECORD]
```

**Status:** `[RESEARCH CHECKPOINT]` `[SOURCE / PROVENANCE AUDIT]` `[NON-AUTHORIZATION RECORD]` `[DOCUMENTATION-ONLY]` `[NOT EMPIRICAL VALIDATION]` `[NOT HYP_003]` `[NOT R1]` `[NOT A CANDIDATE]`
**Date:** 2026-09-10
**Authority:** Human operator (decisions per `mec_0011_human_ratification.md`); this closeout records state only and grants nothing.
**ASCII-only:** YES (no non-ASCII bytes)
**Traceability:** every claim below is traceable to the existing MEC-0011 audit chain:
- `mec_0011_gold_dxy_relative_movement_intake.md` (intake)
- `mec_0011_gold_dxy_data_feasibility_audit.md` (feasibility audit)
- `mec_0011_human_decision_surface.md` (decision surface)
- `mec_0011_human_ratification.md` (Human decisions D1 = A / D2 = C / D3 = B)
- `mec_0011_post_decision_feasibility.md` (post-decision feasibility update)
- `mec_0011_source_provenance_binding_audit.md` (source / provenance binding audit: B1 / B2 / B3, P1-P5)

---

## 1. PURPOSE

- Close out the current MEC-0011 research intake and source/provenance audit stage as a clean, verifiable governance checkpoint.
- Record, without modification, the claim classification, blocker status, resolution-path status, and non-authorization state established by the existing MEC-0011 audit chain.
- Explicitly mark where MEC-0011 stands so that the CAND-FREE-MACRO-001 mainline can resume without ambiguity.
- This closeout performs NO empirical work, NO candidate creation, and NO governance change. It is a state recording only.

## 2. MEC-0011 CURRENT STATUS

MEC-0011 remains:

```
RESEARCH INTAKE ONLY
NOT AUTHORIZED FOR EMPIRICAL VALIDATION
```

- No empirical result exists. No data was downloaded or processed. No backtest, signal test, correlation, returns, IC, Sharpe, or p-value computation was performed.
- No candidate was created. No registry promotion occurred. `free_data_source_registry.md` is unchanged; no Gold/DXY source is ACCEPTED.
- The price/relative-movement track remains the only active MEC-0011 line (literal volume branch terminated by Human decision D3 = B).
- The ICE DXY leg remains a `[GREY SOURCE]` research identity under decision D2 = C; it is NOT `[ACCEPT]` and NOT data-validation-ready.
- `SOURCE LAYER STATUS = BLOCKED` (for the ICE DXY leg under current ratified decisions at $0).

## 3. CLAIM CLASSIFICATION

The underlying source observation must remain separated into three classes, per the intake doctrine. No claim is upgraded by any later audit document.

### VERIFIED BACKGROUND
- Gold and the US dollar index commonly exhibit an inverse relationship on average. `[VERIFIED BACKGROUND]`
- The relationship is non-linear / regime-dependent / time-varying, and crisis-intensified; asymmetry (dollar downside moves influencing gold more than upside) is documented in the literature. `[VERIFIED BACKGROUND]`
- A dollar-channel incremental explanatory power of DXY-type measures for gold returns is documented on average. `[VERIFIED BACKGROUND]`

### RESEARCH QUESTION
- Whether a DXY -> Gold lead/lag for RETURNS exists, and in which direction and with what stability across time/horizons, remains MIXED and UNRESOLVED. `[RESEARCH QUESTION]`

### UNVERIFIED CLAIMS
- (a) A small DXY pullback causes a large Gold move (a repeatable timing rule). `[UNVERIFIED CLAIM]`
- (b) A "volume mismatch" / relative-movement divergence between DXY and Gold predicts the direction of Gold "every day". `[UNVERIFIED CLAIM]`
- (c) The pattern represents a profitable / tradeable edge (after costs and multiple-testing discipline). `[UNVERIFIED CLAIM]`

None of the unverified claims has been confirmed, falsified, or authorized for testing.

## 4. SOURCE / PROVENANCE AUDIT SUMMARY

Source layer assessed in `mec_0011_source_provenance_binding_audit.md` (2026-09-10). Classifications carried unchanged.

### B1 - GOLD LEG (LICENSING / USAGE FRAME): `[CONDITIONAL]`
- Stooq terms were independently established from an archived capture (Wayback 2025-12-05), because the live terms page presented a JavaScript challenge on 2026-09-10.
- Operative literal restriction (5.3): redistribution of site data is not allowed without Stooq consent. No all-data "personal-use only" wording was present in that capture (terms are time-bound; re-verify at retrieval).
- The ratified D1 = A frame (private research, non-commercial, archived, no redistribution, archive-at-retrieval) is POTENTIALLY COMPATIBLE with the current research frame: it does not redistribute (5.3-compatible), is non-commercial, and archive-at-retrieval mitigates the no-guarantee clauses (5.1/5.2).
- PIT remains `[PIT UNPROVEN]` (Stooq is a mutable database with no vintage ids).
- No upgrade to `[ACCEPT]`; Stooq gold is NOT canonical institutional data.

### B2 - ICE DXY PROVENANCE / LICENSING: `[BLOCKED]`
- Identity is the ICE U.S. Dollar Index (administrator ICE Data Indices, LLC; base March 1973 = 100; formula constant 50.14348112; six-currency geometric basket; weights unchanged since the January 1999 Euro substitution; DX futures launched 1985-11-20; index backfilled to 1973).
- Official ICE DXY historical access is PAID / subscription (ICE Connect, ICE Data API, ICE Global Index Feed, ICE Consolidated History, ICE Data Files) with redistribution prohibited without prior written consent of ICE Data; any use of USDX without express written consent is strictly prohibited. No free institutional-research program was identified.
- Free grey paths remain ToS-borne and unresolved.
- Fee status at $0: OFFICIAL ICE = NOT FREE.

### B3 - ICE DXY HISTORICAL ARCHIVE / ACCESS: `[BLOCKED]`
- No free deterministic reproducible ICE DXY daily archive has been established at $0.
- Candidate free sources were evaluated and rejected or downgraded for identity / provenance / depth / determinism reasons (Yahoo grey; Stooq DX.F grey with undisclosed provenance; Barchart paid depth; MarketWatch shallow; FRED identity mismatch; ECB proxy only; UUP/DX futures substitutes; Kaggle provenance unknown; Statista paid; archive.org non-deterministic; no academic DOI'd datasets found).
- Close/session semantics remain unresolved: index close 7:15pm ET (5pm ET Fridays since March 2021) vs DX futures settlement 14:59-15:00 ET VWAP; which level free sources serve is undocumented.
- Historical/reconstructed-index issues remain unresolved: pre-1985 values are reconstructed backfill; 1999 basket-change discontinuity handling by free archives is unverified.

### B4 - B10: `[UNRESOLVED / BLOCKED]` (as previously documented)
- B4 Timestamp/calendar binding: OPEN - depends on the bound ICE DXY source's session/close semantics and a US/NYSE-vs-session merge policy; no solution invented.
- B5 Method-history/splice handling: OPEN - 1999 basket change, pre-1985 reconstruction, close convention, gold Fixing->Auction (2015-03-20); none resolved.
- B6 PIT/archive methodology: OPEN - archive-at-retrieval mandatory; no source archived; no PIT claimed.
- B7 Deterministic research specification: OPEN - not started.
- B8 Pre-registration: OPEN - not started.
- B9 Archive + manifest: OPEN - no manifest exists.
- B10 Explicit Human empirical-validation authorization: OPEN - NOT granted; D1-D3 do not constitute it.

None of B4-B10 is resolved by any audit document. They are downstream of B2/B3.

## 5. RESOLUTION PATHS P1-P5

Paths reproduced from the binding audit exactly as classified. **NO PATH HAS BEEN HUMAN-SELECTED.**

| Path | Description | Status / Constraints |
|---|---|---|
| P1 | ICE Data Indices subscription (paid) | `[PAID]`; institutional/commercial research; requires Human budget authorization; redistribution restricted per IDI terms. Requires explicit Human decision. |
| P2 | Authorized redistributor / vendor access (e.g., Bloomberg / Refinitiv / FactSet-type terminal, or Databento-type API, if present) | `[PAID/VENDOR]`; licensed route; requires existing vendor access to the Human; requires explicit Human decision. |
| P3 | Human-accepted grey path (e.g., Yahoo ^DXY / DX-Y.NYB) | `[GREY]`; $0; ToS-borne (automated extraction/commercial use barred; private archive only); requires explicit Human acceptance of ToS risk, private-archive-only constraint, and `[GREY SOURCE]` labeling on all downstream artifacts. |
| P4 | Stooq DX.F (DXY-futures-derived) | `[GREY]`; $0; futures-derived, NOT the index; close semantics unresolved (futures settlement vs index close); provenance of the series undisclosed; personal-use license, redistribution per Stooq 5.3. Requires explicit Human decision under a ratified grey frame. |
| P5 | Six-FX reconstruction using the ICE-published formula | `[MODEL INFERENCE]`; $0-possible in principle; mathematically equivalent values, NOT official ICE data; requires binding of six FX legs (each individually licensed/archived) and explicit Human acceptance of the `[MODEL INFERENCE]` identity framing; may still need paid/licensed FX history for deep depth. |

Paths explicitly NOT recommended in the binding audit: Kaggle (provenance), archive.org (non-deterministic), Barchart/Statista (paid depth), FRED/ECB/UUP/DX futures (identity-excluded).

The binding audit does not choose any path, and this closeout does not choose any path. Each requires an explicit Human decision; P1/P2 require licensed/paid data or budget authorization.

## 6. WHAT HAS BEEN ESTABLISHED

- The research object identity of the dollar leg is fixed by ratified decision D2 = C: the ICE U.S. Dollar Index. No Fed / ECB / ETF / DX-futures substitute may be silently introduced.
- The gold leg research frame is fixed by ratified decision D1 = A: Stooq XAUUSD under a documented private / non-commercial / archived / no-redistribution frame, archive-at-retrieval mandatory, `[PIT UNPROVEN]`.
- The literal volume-divergence sub-mechanism is TERMINATED by ratified decision D3 = B; no operational volume mechanism remains within MEC-0011 (DXY has no native volume; daily exchange-grade gold volume is not free at $0).
- The price/relative-movement track is the only active MEC-0011 line, and it is `BLOCKED` at the source layer: B2 (ICE DXY provenance/licensing) and B3 (ICE DXY archive/access) are `[BLOCKED]`; B1 is `[CONDITIONAL]`.
- Five resolution paths (P1-P5) are documented with exact status/constraints; NONE is selected.
- MEC-0011 is a documentation-only research intake; no source is ACCEPTED in any registry.

## 7. WHAT HAS NOT BEEN ESTABLISHED

The audit does NOT establish:
- empirical predictive power
- causality
- a profitable / tradeable edge
- volume-divergence alpha
- a valid trading strategy
- a candidate
- a research hypothesis
- HYP_003 readiness
- R1 readiness

None of these is implied by the existence of the intake, the audits, the ratified identity/termination decisions, or this closeout.

## 8. DATA FEASIBILITY BOUNDARY

The following are distinct research-input classes. They must be distinguished at every future stage and must never be silently substituted for one another.

- **Gold price data:** Stooq XAUUSD (daily OHLC, ~1968+, continuous spot-style pair; CSV volume field empty/zero; license frame per D1; `[PIT UNPROVEN]`; early history fix-derived approximate OHLC; London Gold Fixing -> LBMA Gold Price auction on 2015-03-20 is a method/regime change). Feasibility of the price leg alone: `CONDITIONAL`.
- **ICE DXY (the research identity):** official index level is a paid ICE product; no free compliant historical archive established at $0; grey sources are ToS-borne. `[BLOCKED]`.
- **DXY futures (DX.F / DX):** derivative of the index with basis; settlement ~14:59-15:00 ET VWAP vs index close 7:15pm ET (5pm ET Fridays since 2021). A futures series is NOT the index.
- **ETF proxies (UUP/UDN; GLD/IAU):** UUP/UDN are DX-futures-based funds with roll costs/expenses, NOT DXY spot; GLD/IAU daily share-turnover volume is secondary-market ETF turnover, NOT exchange-grade gold volume. Neither is interchangeable with spot/futures/index data.
- **Reconstructed six-FX index (P5):** computed with the ICE-published formula from six FX legs (EUR/JPY/GBP/CAD/SEK/CHF); `[MODEL INFERENCE]`; mathematically equivalent values are NOT official ICE data; basket weights non-constant over history (Euro introduced 1999; periodic weight updates); not doctoral substitute for a real ICE DXY archive.
- **Volume semantics:** the ICE DXY is a computed index and has NO native volume; daily exchange-grade gold volume is not free at $0. The "volume mismatch" construct is therefore unsatisfiable in its literal form and is TERMINATED (D3 = B).

Mandatory no-silent-substitution rule (binding, from the ratification and post-decision documents): FRED Fed dollar indexes, ECB reconstruction, UUP, DX futures, and any other dollar proxy are NOT substitutes for ICE DXY; gold spot/XAUUSD level is NOT exchangeable with COMEX futures volume, GLD volume, or any gold-volume proxy. Any substitution requires a NEW explicit Human decision recorded in a ratification record, and must never be introduced to compensate for a data-availability gap.

## 9. GOVERNANCE BOUNDARY

This closeout records, explicitly:

- NO empirical validation is performed or authorized.
- NO candidate is created or promoted.
- NO HYP_003 is created. HYP_003 remains ABSENT.
- NO ResearchReInceptionGate is invoked.
- NO R1 is started.
- NO trading authorization is granted (no paper, no live).
- NO capital change occurs (Live Capital Authority remains $0.00 / Hard-Locked).
- NO registry, source registry, candidate registry, gate, schema, test, or source-code change occurs.
- No previously frozen governance decision is rewritten or "improved."

## 10. RELATIONSHIP TO ACASH MAINLINE

- **CAND-FREE-MACRO-001 remains the MAINLINE.** It is `CONDITIONALLY READY`; PRE-REGISTRATION is NOT FULLY FROZEN; EMPIRICAL VALIDATION and BACKTEST are NOT AUTHORIZED. Its binding progress (Rounds 0-3B recorded; S-2 / S-7 T_eff formula / S-9 open) is unchanged by MEC-0011 - MEC-0011 is a SEPARATE research family and must not be merged into it.
- **MEC-0011 remains a PARALLEL research intake** (RESEARCH INTAKE ONLY), closed here as a checkpoint.
- **F-1 remains parked/blocked according to its existing governance state** (D1 final verdict NOT READY / CONDITIONAL at $0; PENDING HUMAN RATIFICATION). F-1 is unchanged by this closeout.
- MEC-0011 does NOT alter: MACRO-001, F-1, HYP_001, HYP_002, R1, any gate, tracker, or candidate state.

## 11. RE-ENTRY CONDITIONS

MEC-0011 may only move forward when the following conditions are satisfied. This list defines necessary conditions only; it does NOT authorize any empirical step, and it does NOT invent numerical thresholds.

1. **Human selection of a legitimate data/provenance path** for the ICE DXY leg (one of P1-P5 or a new explicitly named path), recorded in a Human ratification record.
2. **Deterministic source / version / access record:** a specific, reproducibly retrievable source with documented access contract; grey paths additionally require explicit Human acceptance of ToS risk, private-archive-only handling, and `[GREY SOURCE]` labeling on downstream artifacts.
3. **Timestamp / session semantics binding:** a pre-registered, deterministic, tie-symmetric calendar/merge policy covering session/close semantics (index close vs futures settlement) and calendar seams (London-only days, NYSE trading days), never a silent gap-drop.
4. **Comparable Gold/DXY data definitions:** gold price data and the ICE DXY identity defined with matched granularity and boundary; no silent substitution of Fed/ECB/ETF/futures proxies.
5. **PIT / provenance resolution:** archive-at-retrieval with raw bytes + fetch timestamp + source version for every bound leg, and a provenance manifest; PIT proven by archive evidence, never asserted.
6. **Explicit specification and human authorization:** a frozen deterministic research specification (identity, comparator, horizon, direction, K / multiple-testing doctrine, statistical protocol, IS/OOS/Blind, cost model, fail-closed PASS/FAIL/INVALID), a pre-registration, and a separate explicit Human empirical-validation authorization.

Satisfying these conditions permits ONLY entry into the next governance stage; it never, by itself, constitutes empirical-validation authorization.

## 12. FINAL DECISION

```
MEC-0011 = CLOSED AS A RESEARCH CHECKPOINT
NOT VALIDATED
NOT A CANDIDATE
NOT HYP_003
NOT AUTHORIZED FOR EMPIRICAL VALIDATION
```

- This is a checkpoint closure, NOT a rejection of the underlying research question.
- MEC-0011 remains documentation-only and may be re-entered only through Section 11 re-entry conditions.
- The CAND-FREE-MACRO-001 mainline can now resume without any MEC-0011 interference.

## 13. STOP

No empirical step is recommended. No MACRO-001 implementation proceeds in this task. This document is the terminal deliverable of the MEC-0011 closeout.

### Verification Ledger
- Implementation Status: N/A (documentation-only closeout; no code, no data ingest, no download, no computation)
- Contract Enforcement: STRICT FAIL-CLOSED - no candidate created; no path selected; no claim upgraded; no registry/gate/code change; no authorization granted
- Mathematical Authority: N/A (no formulation claimed; no thresholds introduced)
- Local Test Suite: NOT RUN (no code touched)
- Type Checker (MyPy): NOT RUN (no code touched)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: this closeout carries all classifications verbatim from the existing MEC-0011 chain; SOURCE LAYER STATUS = BLOCKED for the ICE DXY leg; B1 CONDITIONAL, B2/B3 BLOCKED, B4-B10 OPEN; no path selected; MEC-0011 remains RESEARCH INTAKE ONLY / NOT AUTHORIZED FOR EMPIRICAL VALIDATION.