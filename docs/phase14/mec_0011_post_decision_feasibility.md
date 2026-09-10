# MEC-0011: POST-DECISION FEASIBILITY UPDATE

**Document ID:** `docs/phase14/mec_0011_post_decision_feasibility.md`
**Object:** Reassessment of MEC-0011 feasibility AFTER the ratified Human decisions D1=A, D2=C, D3=B. Documents what became possible vs. impossible after ratification. Purely a feasibility-state update; no data processed.
**Status:** `[POST-DECISION FEASIBILITY]` `[DOCUMENTATION-ONLY]` `[NOT EMPIRICAL VALIDATION]` `[NOT HYP_003]` `[NOT R1]` `[NOT A CANDIDATE]`
**Date:** 2026-09-10
**Authority:** Human operator (decisions per `docs/phase14/mec_0011_human_ratification.md`)
**ASCII-only:** YES (no non-ASCII bytes)

## 1. Purpose and Method

- This document reassesses MEC-0011 strictly from the existing audit
  (`docs/phase14/mec_0011_gold_dxy_data_feasibility_audit.md`) and the ratified decisions
  (`docs/phase14/mec_0011_human_ratification.md`).
- NO empirical activity of any kind was performed: no download, no data processing, no
  correlations, no lead-lag statistics, no returns, no Sharpe, no IC, no p-values, no backtest,
  no parameter optimization. Feasibility here means only "what is now permitted/possible to bind
  as research inputs" - not readiness for measurement.

## 2. Ratified Decisions Applied to the State

| Decision | Ratified selection | Effect on feasibility state |
|---|---|---|
| D1 = A | Stooq XAUUSD under documented non-commercial/private research frame | Gold leg may be BOUND into the research frame under the documented conditions; not globally/commercially accepted |
| D2 = C | ICE DXY as research identity (grey source) | Research object is fixed as ICE DXY; no Fed/ECB substitution; not data-validation-ready |
| D3 = B | Terminate literal-volume branch; retain price/relative-movement track | No operational volume sub-mechanism remains; MEC-0011 remains alive via price track |

---

## 3. ASSESSMENT 1 - GOLD PRICE LEG

- Series: Stooq `XAUUSD` (daily OHLC, ~1968+, continuous spot-style pair). Audit classification
  unchanged: `[VERIFIED]` series / start + license `[CONDITIONAL]`.
- License frame: D1=A binds the leg to a documented non-commercial/private research frame:
  private research use, non-commercial, archived data, no redistribution. The frame must be written
  down as a standing condition to the research (it is NOT an inferred right). Stooq remains
  `[CONDITIONAL]`; not `[ACCEPT]`; not canonical institutional data.
- Archive-at-retrieval: mandatory, unchanged. Raw bytes + fetch timestamp + provider version must
  accompany any stored series.
- PIT status: unchanged `[PIT UNPROVEN]` (Stooq is a mutable DB with no vintage ids). Provenance =
  the researcher's own archive manifest; nothing else counts.
- Reproducibility: single-symbol CSV endpoint is deterministic in form
  (`stooq.com/q/d/l/?s=xauusd&i=d&d1=YYYYMMDD&d2=YYYYMMDD`); subject to daily quota, CAPTCHA/JS
  challenge behavior, and mandatory archive-at-retrieval. `[CONDITIONAL]`.
- Remaining caveats: early history (1968-~1990s) is fix-derived approximate OHLC; London Gold
  Fixing -> LBMA Gold Price auction (2015-03-20) is a method/regime change to be surfaced, never
  silently spliced.

## 4. ASSESSMENT 2 - ICE DXY LEG

- Identity: now Human-selected as the **ICE U.S. Dollar Index** (research object of MEC-0011).
  This fixes WHAT is studied.
- Provenance/licensing: STILL UNRESOLVED. ICE DXY remains a `[GREY SOURCE]` with unresolved
  provenance/licensing constraints. The audit recorded that official ICE index data is a paid
  product and that a Yahoo-based grey level is ToS-restricted for automated/archival use
  (F10/F11). Selecting identity C does NOT resolve which (if any) compliant free archive supplies
  the level.
- Historical free-access status: STILL UNRESOLVED. The audit did not establish that a free,
  compliant, reproducible, historically deep ICE DXY archive exists at $0. Nothing in this update
  asserts that one does.
- No silent substitution: FRED Fed dollar indexes and ECB reconstructed DXY are categorically NOT
  the ICE DXY identity; they may not be substituted to make the data problem easier.
- What must be resolved before validation (exact list for the ICE DXY leg):
  1. Identify a specific, compliant, reproducibly retrievable source of ICE DXY historical levels
     (or a Human-accepted grey path with documented provenance + private-archive constraint).
  2. Document that source's license/terms and the private-archive-only handling.
  3. Bind the exact series identity, timestamp semantics, and any indexes continuity (DXY trades on
     its own session; DXY is continuous since ~1973 - binding to an archive must state the same).
  4. Resolve historical start/end, granularity, and revision behavior of the chosen archive.
  5. Record the above in an archive manifest (B9) before any analysis object exists.

## 5. ASSESSMENT 3 - TIMESTAMP / CALENDAR COMPATIBILITY

- Assessed ONLY from the existing audit (F16). No novel solution is invented here; no empirical
  readiness is declared.
- Audit finding carried: a common daily timestamp is `[CONDITIONAL]`-achievable on a US/NYSE
  trading-day calendar; both gold (Stooq ~22:00 CET close = ~16:00 ET) and US-listed series share a
  daily boundary.
- Seams identified by the audit (must be bound, not invented): gold trades on sessions the US
  market is closed (London-only days); an ECB-based calendar is TARGET-based (not applicable now,
  since D2=C picks ICE DXY, but the seam rule is general); any calendar merge policy must be
  pre-registered, deterministic, tie-symmetric - never a silent gap-drop.
- Status: timestamp BINDING remains an open requirement (B4). This document does not declare that a
  compatible timestamp solution exists.

## 6. ASSESSMENT 4 - METHOD-HISTORY / SPLICE ISSUES

- Gold: London Gold Fixing -> LBMA Gold Price auction (2015-03-20) is a regime/method change
  within the gold price history; early gold OHLC is fix-derived and approximate. Any future use
  must flag these, not splice silently.
- DXY leg: D2=C means the research object is ICE DXY. The FRED `DTWEXBGS`/`TWEXBGS` splice is
  IRRELEVANT as a substitute for the ICE DXY leg - it belongs to a different index identity
  (Fed-computed effective exchange rates). Explicitly: choosing ICE DXY means the FRED splice is
  NOT a substitute for ICE DXY, and it is not a workaround for an ICE DXY archive gap.
- Any ICE DXY historical archive still has its own continuity semantics (session-based, index level
  since ~1973) which must be documented from the chosen archive; no survivorship guarantee is
  assumed.

## 7. ASSESSMENT 5 - PIT / ARCHIVAL REQUIREMENTS

- Distinction maintained: DATA IDENTITY (what the series is = ICE DXY, gold spot-style level) is
  separate from HISTORICAL POINT-IN-TIME (whether a value was knowable at its own date without
  lookahead/revision).
- D1 leg: Stooq `[PIT UNPROVEN]`; archive-at-retrieval is the ONLY route to provenance.
- D2 leg: whichever ICE DXY archive is eventually bound must be reviewed for revision behavior,
  retrieval timestamp, and vintage availability. No PIT claim is made for any grey path.
- Archive-at-retrieval remains mandatory for EVERY leg (B9). Dolt-style versioning must not
  automatically be labeled PIT; PIT is proven by construction/archive evidence, not by tooling.

## 8. ASSESSMENT 6 - SURVIVORSHIP / CONTINUITY

- Audit finding retained: even official, government-hosted series can be deleted (FRED gold
  fix series removed 2022-01-31 under IBA licensing). This is the standing cautionary example.
- Consequence: no survivorship/continuity guarantee may be invented. Every leg requires
  archive-at-retrieval so the research corpus is not destroyed by a future provider deletion.
- Gold leg: single continuous spot-style pair; no futures-rollover leg is used (none selected).
- DXY leg: ICE DXY identity is an index level; its archive continuity depends on the chosen source.
  No claim of archival completeness is made.
- No silent substitution across futures / ETF / spot / index.

## 9. ASSESSMENT 7 - VOLUME BRANCH

- Status: LITERAL-VOLUME BRANCH = **TERMINATED** (D3 = B, ratified).
- Why no operational volume mechanism remains: the audit established that DXY has no native volume
  (computed benchmark) and that daily exchange-grade gold volume is not free at $0 (COMEX history
  is paid; CFTC is weekly open interest, not volume; SGE daily is shallow/restricted; LBMA clearing
  is monthly). A "DXY volume vs Gold volume mismatch" cannot be operationalized at $0.
- GLD-vs-UUP: NOT authorized, NOT created, NOT substituted. ETF volume is not DXY volume; ETF
  volume is not gold market volume. No new intake/candidate was created.
- Predictive power: none is inferred from the original volume claim; the term is closed as a
  sub-mechanism, and the price/relative-movement track is the only active MEC-0011 line.

---

## 10. FINAL CLASSIFICATION (post-decisions, deterministic)

- **PRICE-ONLY TRACK:** `CONDITIONAL` (unchanged from audit) - and **BLOCKED** pending:
  (a) ICE DXY provenance/licensing binding (B2), (b) ICE DXY historical archive/access binding (B3),
  (c) the remaining data-binding requirements (B4-B10). The gold leg is conditionally usable under
  D1's documented frame, but the DXY leg is not data-bound.
- **LITERAL-VOLUME TRACK:** `TERMINATED` / `NOT FEASIBLE AT $0` / `NOT OPERATIONALIZED`.
- **MEC-0011 OVERALL:** `RESEARCH INTAKE ONLY / NOT AUTHORIZED FOR EMPIRICAL VALIDATION`.

Any classification more precise than the above is not supported by the audit and is NOT asserted.
MEC-0011 is NOT: READY, VALIDATED, EMPIRICALLY READY, or AUTHORIZED FOR BACKTEST.

---

## 11. MANDATORY NO-SILENT-SUBSTITUTION RULE (GOVERNANCE)

The selected research identity is **ICE DXY**.

The following are NOT equivalent substitutes and must not be introduced merely to overcome data
availability:

- FRED Fed dollar indexes (TWEXBGS / DTWEXBGS / TWEXMTHY family)
- ECB reconstructed DXY proxy
- UUP (and any other dollar ETF)
- DX futures
- any other dollar proxy

Any substitution requires a NEW explicit Human decision, recorded in a ratification record, and
must never be introduced to compensate for a data-availability gap.

Likewise (gold side):

- Gold spot / XAUUSD level
- is NOT exchangeable with COMEX gold futures volume
- is NOT exchangeable with GLD volume
- is NOT exchangeable with any gold-volume proxy

No substitution without explicit Human authorization. This rule applies to every future stage of
MEC-0011.

---

## 12. PRE-VALIDATION BLOCKER TABLE (OPEN)

| ID | Blocker | State after D1/D2/D3 | Evidence basis |
|---|---|---|---|
| B1 | Gold licensing/usage documentation | OPEN - D1=A conditions must be documented as a standing frame (private, non-commercial, archived, no redistribution) | audit F4/stooq license `[CONDITIONAL]`; D1 record |
| B2 | ICE DXY provenance/licensing | OPEN - grey source; unresolved terms; not `[ACCEPT]` | audit F10/F11; D2 boundary |
| B3 | ICE DXY historical archive/access | OPEN - no compliant free deep archive established; may be Human-accepted grey path with documented provenance | audit F10/F11; D2 boundary |
| B4 | Timestamp/calendar binding | OPEN - merge policy must be pre-registered, deterministic, tie-symmetric; seams (London-only days, sessions) must be bound | audit F16; Assessment 5 |
| B5 | Method-history / splice handling | OPEN - gold Fixing->Auction flagging; ICE DXY archive continuity; FRED splice NOT a substitute for ICE DXY | audit F8 note; Assessment 6 |
| B6 | PIT/archive methodology | OPEN - Stooq `[PIT UNPROVEN]`; grey DXY `[PIT UNPROVEN]`; PIT = archival evidence only | audit F4/F11; Assessment 7 |
| B7 | Deterministic research specification | OPEN - instrument identity, calendar/merge, direction/horizon, K/multiple-testing doctrine, statistical protocol, IS/OOS/Blind, cost model - none specified yet | decision-surface Section 11 |
| B8 | Pre-registration | OPEN - no pre-registration exists | governance pipeline |
| B9 | Archive + manifest | OPEN - no archive-at-retrieval manifest exists (mandatory for every future leg) | registry terms; Assessment 5 |
| B10 | Explicit Human empirical-validation authorization | OPEN - NOT granted; none of D1/D2/D3 constitutes it | non-authorization list |

No blocker above is marked resolved; no existing evidence supports resolution. `[HUMAN DECISION REQUIRED]`
for the binding decisions each blocker depends on.

---

## 13. NON-AUTHORIZATIONS (REPEATED FOR THIS STAGE)

- D1-D3 are NOT authorization for: backtesting, empirical validation, signal testing, parameter
  search, hypothesis registration, HYP_003, R1, or trading.
- No registry promotion occurs: `free_data_source_registry.md` is not modified; no Gold/DXY source
  is added as ACCEPTED; MEC-0011 is not promoted to a candidate registry; no CAND-FREE or HYP
  identifier is created.
- No modification of F-1, MACRO-001, HYP-001, HYP-002, HYP registries, Phase-6, gate logic,
  trading authorization, capital state, or R1.

---

## 14. NEXT STAGE (GOVERNANCE PIPELINE - NOT COMMENCED)

The next governance stage, in binding order, is:

1. **SOURCE / PROVENANCE BINDING** - bind the actual ICE DXY archive source (with Human acceptance
   of any grey path's provenance/licensing), document its license/terms, continuity and revision
   behavior; bind Stooq XAUUSD under the documented D1 frame.
2. **DETERMINISTIC SPECIFICATION** - fix instrument identities, calendar/merge policy, splice/
   method-change handling, direction/horizon, K and multiple-testing doctrine, statistical
   protocol, IS/OOS/Blind, cost model; fail-closed PASS/FAIL/INVALID rules.
3. **PRE-REGISTRATION / ARCHIVE / MANIFEST** - pre-register the frozen specification; archive every
   leg at retrieval; build the provenance manifest.
4. **EXPLICIT HUMAN EMPIRICAL-VALIDATION AUTHORIZATION** - a separate, explicit Human authorization.

Only after each stage is independently satisfied may empirical work even be considered. No part of
this stage sequence is initiated by this document.

---

## 15. FINAL STATUS STATEMENT

MEC-0011 remains:

```
RESEARCH INTAKE ONLY
NOT AUTHORIZED FOR EMPIRICAL VALIDATION
```

No empirical result exists. No data was processed. No backtest was run. No HYP_003. No R1. No
registry change. No candidate promotion. No substitution was made.

### Verification Ledger
- Implementation Status: N/A (documentation-only post-decision feasibility update; no code, no data, no download, no computation)
- Contract Enforcement: STRICT FAIL-CLOSED - no evidence upgraded; no PIT claimed; no timestamp solution invented; no survivorship guaranteed; no substitution performed
- Mathematical Authority: N/A (no formulation claimed)
- Local Test Suite: NOT RUN (no code touched)
- Type Checker (MyPy): NOT RUN (no code touched)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: feasibility state is derived strictly from the 2026-09-10 audit and the ratified D1=A/D2=C/D3=B; ALL pre-validation blockers (B1-B10) remain OPEN; D2 selects identity only and leaves ICE DXY provenance/licensing/access unresolved (grey); literal-volume branch terminated without retroactive claims; no empirical readiness is declared.