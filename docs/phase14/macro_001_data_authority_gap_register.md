# MACRO-001 DATA AUTHORITY GAP REGISTER

**Document ID:** `docs/phase14/macro_001_data_authority_gap_register.md`
**Object:** Formal governance closure record for the CAND-FREE-MACRO-001 D17/D18 data-authority blocker, plus a durable Data Authority Gap Register describing what remains blocked and what evidence would unblock it.
**Status:** `[DOCUMENTATION-ONLY]` `[GOVERNANCE PRESERVATION]` `[NO EMPIRICAL WORK]` `[NOT HYP_003]` `[NOT R1]` `[NOT EMPIRICAL VALIDATION]` `[NOT A CANDIDATE CREATION]`
**Date:** 2026-09-11
**Authority:** Human operator. This register records state only and grants nothing. It is NOT a ratification document; no Human decision is marked ratified here.
**ASCII-only:** YES (no non-ASCII bytes)
**Traceability:** every substantive claim below is traceable to the existing canonical MACRO-001 governance chain:
- `cand_free_macro_001_human_specification_decision_surface.md` (D17 row 196 / sec 24.2; D18 row 197 / sec 25.1; freeze checklist sec 28; governance options sec 30; final governance state sec 33)
- `cand_free_macro_001_human_binding_worksheet.md` (sec C D17/D18 derivation rows 154-155; O.10 = D19; O.11 = D20; ROUND 4 / ROUND 5 closures)
- `cand_free_macro_001_round4_specification.md` (D17/D18 structural derivation sec 3.7; conflict audit; STOP = ROUND 5 COMPLETE)
- `cand_free_macro_001_validation_readiness.md` (sec 11 PIT/archive; source-pin table)
- `free_data_source_registry.md` (S-04 FRED; S-10 Stooq; S-18 yfinance; tiers; archive-at-retrieval rule sec 11)
- `free_data_research_registry.md` (candidate evidence classification)
- External evidence channel (verified 2026-09-11, `EXTERNAL VERIFICATION - NOT HUMAN-RATIFIED`; detailed in the S-10 final evidence check transcript and FRED final evidence check transcript, both read-only runs)

---

## A. PURPOSE

- Formally record that the currently investigated `$0` SPX sources do NOT satisfy the already-frozen D17 authority contract for MACRO-001.
- Preserve the FAIL-CLOSED governance state without weakening any frozen requirement.
- Create a durable Data Authority Gap Register: exactly what remains blocked and what evidence would be required to unblock it in the future.
- This task does NOT seek another provider, does NOT select or ratify any provider, and performs NO empirical work.

## B. SCOPE

- Governance/documentation only. Nothing in this register changes methodology, data authority, licensing state, or authorization state.
- Covers the MACRO-001 SPX close-series authority blocker (D17) and its downstream dependency (D18).
- Relevant to the FREE-DATA TRACK: all referenced sources are `$0` sources already registered (S-04, S-10, S-18); no new source name is introduced.
- F-1 is explicitly OUT of scope and is NOT reopened, rewritten, or modified by this register.

## C. FROZEN D17 CONTRACT REFERENCE

The D17 contract is already frozen in canonical documents; this register does not modify it. Reference (verified facts only):

- D17 = Data vintage / archive / PIT (`decision_surface.md` row 196; `worksheet.md` sec C row 154).
- Required artifact set per source (never replaced/swallowed, `decision_surface.md` sec 24.2):
  - source identity (S-ID); retrieval timestamp; source version if available; raw archive; manifest; digest
  - timezone normalization; event timestamp provenance; index data provenance; SPY data provenance if used; corporate-action provenance if SPY used
  - no silent replacement of archived data (registry sec 107 archive-at-retrieval)
- If a source cannot establish the required PIT property, it must REMAIN `UNVERIFIED / CONDITIONAL`; the candidate run cannot silently proceed on the weaker basis (`decision_surface.md` sec 24.2; readiness sec 11; AGENTS.md fail-closed doctrine).
- Required research window: **2013-12-01 -> 2026-09-10** (IS 2013-12-01 -> 2021-12-31; OOS 2022-01-01 -> 2024-12-31; BLIND 2025-01-01 -> 2026-09-10), as bound in `round4_specification.md`.
- D18 = Reproducibility / manifest (`decision_surface.md` row 197; sec 25.1): candidate ID, spec version, source IDs/retrieval timestamps, event universe, timestamp convention, event window, return formula, baseline, instrument, cost assumptions, parameter grid, K, IS/OOS/blind dates, statistical protocol, kill conditions, PASS/FAIL/INVALID semantics.
- CA-1 (NYSE official calendar session authority) = HUMAN-RATIFIED at DECISION level + SOURCE-BINDING ARCHITECTURE ratified (2026-09-10). CA-1 is a session/calendar authority; it does NOT by itself establish the SPX close-series authority.
- GOVERNANCE INVARIANTS PRESERVED (unchanged, non-negotiable): D3, D4, D6, D7, D8, D19, D20, K = 3, IS/OOS/blind windows, CA-1, event definitions, event timestamp rules, session rules, return definition (= R-EC), statistical test, alpha (0.05), PASS/FAIL semantics, kill conditions, anti-HARKing rules, PIT doctrine, provenance doctrine, fail-closed doctrine.

## D. CURRENT SOURCE STATUS

Canonical/widely verified status (no new provider investigation; no promotion):

| Source | Registered identity | Classification (registry) | Latest evidence status (2026-09-11 external check) |
|--------|--------------------|---------------------------|-----------------------------------------------------|
| S-04 FRED SP500 | `fred.stlouisfed.org/series/SP500` | Not enumerated for SP500 in registry (S-04 record lists macro/VIXCLS only); series-level identity `EXTERNAL VERIFICATION - NOT HUMAN-RATIFIED` | **FAIL as sole D17 primary.** FRED's own data table: Date Range `2016-09-12 -> 2026-09-09`. Required window starts 2013-12-01 -> **2013-12-01 -> 2016-09-11 missing entirely**. PIT subject to revision; S&P reproduction/redistribution restriction present. |
| S-10 Stooq `^spx` | `stooq.com/q/d/?s=^spx` | TIER 2 `[CONDITIONAL]` (registry sec 89-95); `[PIT UNPROVEN]` unless archived | **NOT RATIFIED / CONDITIONAL with decisive FAIL-CLOSED blockers.** Series presently labelled "US LargeCap CFD"; official S&P 500 close identity NOT established; raw retrieval blocked by WAF / JS-PoW / "Access denied"; coverage and session completeness NOT byte-verified; PIT unproven; adjustment/rebase unverified; automated archive-at-retrieval not reliably reproducible at $0; personal-use non-redistribution license. |
| S-18 Yahoo/yfinance | unofficial Yahoo wrapper | TIER 3 `[CONDITIONAL]` active / `[REJECT]` deep delisted (registry sec 119) | **NOT PRIMARY / NOT SELECTED.** Mutable history, no vintage, Yahoo ToS bulk/redistribution risk. No new audit performed in this task (explicitly out of scope). |

**Conclusion:** There is currently **NO Human-ratified clean D17 primary SPX close authority** at `$0` under the frozen contract.

## E. GAP MATRIX

| Requirement | Current Status | Evidence State | What Would Unblock |
|-------------|----------------|----------------|---------------------|
| Official SPX identity | **BLOCKED** | Stooq identity not established as official S&P 500 close; FRED is official-series-labelled but unsuitable as sole source for the full required window | Authoritative source identity binding (source = the required SPX index close, single authority) |
| 2013-12-01 -> 2026-09-10 coverage | **BLOCKED** | FRED fails actual coverage (earliest 2016-09-12); Stooq depth only secondary-indicated (~39,700-row external indication), NOT byte-verified | Byte-verifiable complete-window data (first/last observation + full interval) |
| NYSE session coverage | **BLOCKED/UNVERIFIED at data-source level** | CA-1 calendar authority exists separately (Human-ratified); no source-series/session reconciliation performed for either FRED or Stooq | Complete source-series-to-CA-1 session reconciliation |
| Daily close semantics | **BLOCKED/UNVERIFIED** | D4 (R-EC) requires the correct daily close authority; not established for either provider at series level | Explicit source close-semantics binding |
| PIT / as-published | **BLOCKED** | No currently investigated `$0` source establishes historical vintages (FRED: subject to revision; Stooq: mutable, no vintage IDs) | Acceptable vintage / as-published evidence under frozen PIT doctrine |
| Archive-at-retrieval | **BLOCKED** | Stooq automated retrieval currently WAF / JS-PoW / API-key (CAPTCHA) gated; "Access denied" observed after PoW solve. Deterministic automated archive not reliable at $0 | Deterministic retrieval/archive procedure (raw bytes + timestamp) |
| Adjustment / rebasing | **BLOCKED/UNVERIFIED** | Stooq exposes skip-splits/dividends toggles; adjustment method undocumented; no byte-level verification done | Documented adjustment/rebase semantics + reproducible configuration |
| Provenance | **BLOCKED** | No archived source set with identity/version/retrieval-time/raw-artifact/digest lineage for the required window | Complete lineage per `decision_surface.md` sec 24.2 manifest set |
| Licensing | **BLOCKED/CONDITIONAL** | FRED: S&P reproduction restriction; Stooq: personal-use only / redistribution without consent prohibited | License/use basis compatible with the intended ACASH research artifact + governance requirements |
| Single official-close authority | **BLOCKED** | Current source set does not satisfy the frozen one-authority rule | Human-ratified authority (see Future Unblock Conditions) |

No PASS is invented where evidence supports only CONDITIONAL or UNVERIFIED. `[STRICT FAIL-CLOSED - no cell upgraded]`

## F. EVIDENCE CURRENTLY AVAILABLE

- FRED SP500 exact series metadata (Date Range `2016-09-12 -> 2026-09-09`; close semantics: daily index value at market close, 4 PM ET typical; price index, dividends excluded; S&P reproduction clause) - `EXTERNAL VERIFICATION`, access 2026-09-11.
- Stooq `^spx` identity label "US LargeCap CFD" and historical table pagination (~39,713-39,726 row numbers on 2026 dates) - `EXTERNAL VERIFICATION` (search-cache/quote-page snapshots), access 2026-09-11.
- Direct retrieval test: Stooq CSV endpoint (present-day URL `stooq.com/q/d/l/?s=^spx&i=d`) served a JS proof-of-work challenge; PoW solved (SHA-256 "0000" prefix, n=21274; `POST /__verify` returned 200); subsequent data requests returned **"Access denied"** (13 bytes) on 3 attempts. `EXTERNAL VERIFICATION - NOT HUMAN-RATIFIED`.
- Stooq bulk data page notice: "This data is intended solely for personal use. Any commercial use is prohibited." (multiple snapshots).
- APIs.io Stooq catalog (2026): API key obtained via CAPTCHA required; daily request quota applies ("Exceeded the daily hits limit").
- Canonical registry records: S-04 (sec 52-57), S-10 (sec 89-95), S-18 (sec 119); archive-at-retrieval rule (sec 11); tiers (sec 22).

## G. EVIDENCE STILL REQUIRED

To unblock D17 in the future, ALL of the following must be demonstrated ground-truth for any candidate authority:

1. Exact identity as the required SPX index close (one official authority).
2. Complete 2013-12-01 -> 2026-09-10 coverage (byte-verified first/last observation + full interval).
3. Session reconciliation against CA-1 (source session set == ratified CA-1 valid-session set over the window).
4. Explicit daily close semantics (what "Close" means; official daily close; timezone convention).
5. PIT / as-published provenance acceptable under the frozen doctrine (vintage / as-published evidence, not today's backfill).
6. Deterministic retrieval procedure (no WAF/CAPTCHA/non-deterministic manual step in the archive path).
7. Raw artifact archival.
8. Retrieval timestamp.
9. Source version/identity.
10. SHA-256 digest.
11. Adjustment/rebase semantics.
12. License/use rights compatible with the intended research artifact and governance requirements.
13. Reproducible manifest binding.
14. **Human ratification before becoming D17 primary** (this register does not ratify anything).

## H. FUTURE UNBLOCK CONDITIONS

- A future D17 authority must meet all items in section G. These conditions are generic; this register does NOT identify, select, purchase, or recommend any vendor.
- **A future paid or permissioned source is allowed as a future resolution path if separately Human-approved** (e.g., through the Future Data Acquisition Queue governance, registry sec 27; no purchase without Human Governance budget authorization). This register does NOT authorize any purchase.
- No provider is selected or promoted by this register.

## I. GOVERNANCE CONSEQUENCES

- MACRO-001 remains governance-complete but **data-authority blocked**.
- D17 = **OPEN / GROUP C** - reason: no currently investigated `$0` source satisfies the complete frozen D17 authority contract. The blocker is NOT simply "no free data"; it is a combination of official identity, full-window coverage, session completeness, PIT/as-published provenance, archive-at-retrieval reproducibility, adjustment semantics, licensing/redistribution, and the single-authority requirement.
- D18 = **OPEN / GROUP C** - D18 is **dependency-blocked** on a D17-bound data authority, NOT failed because of a schema defect. D18 cannot be finalized as a fully bound reproducibility manifest while D17 is unresolved.
- Draft Freeze = **NOT READY** (26-item checklist: 24/26 checked per surface §28 reconciliation; 1 item D18-dependent unsealed manifest; 1 item Human authorization). D17-E remains ratified.
- Empirical validation = **NOT AUTHORIZED**. Backtest = **NOT AUTHORIZED**. HYP_003 = **ABSENT**. R1 = **NOT STARTED**. ResearchReInceptionGate = **NOT INVOKED**. Trading/broker/capital = **LOCKED / $0.00**.
- FREE-DATA TRACK: the ACASH project may continue separate FREE-DATA TRACK / mechanism-first research without weakening MACRO-001 D17. Potential future research may use mechanisms whose data authority can satisfy the same governance standard. No new candidate is created by this register; no empirical validation of another candidate is authorized; no mechanism is converted into HYP_003.
- F-1 PRESERVATION: F-1 remains separate. Its existing D1 status and blockers remain unchanged. The MACRO-001 D17 blocker is NOT used as justification to modify F-1.

## J. EXPLICIT NON-AUTHORIZATIONS

This task does NOT authorize and did NOT perform:

- searching for another SPX provider
- auditing Yahoo/yfinance (S-18) as a new audit
- auditing another Stooq endpoint
- purchasing / selecting a vendor
- modifying D17 requirements
- modifying D18 requirements
- modifying D3/D4/D6/D7/D8/D19/D20
- modifying CA-1
- modifying K
- modifying IS/OOS/blind windows
- running a backtest
- downloading market data / ingesting data
- calculating statistics / creating empirical evidence
- creating HYP_003 / invoking ResearchReInceptionGate / starting R1
- authorizing paper trading or live trading
- modifying capital/trading state
- adding dependencies
- modifying `src/`, schemas, or gates
- modifying ROADMAP (not required)
- committing or pushing

This task is DOCUMENTATION-ONLY.

## K. HUMAN DECISION STATUS

**RECOMMENDED GOVERNANCE STATE (field for Human; NOT marked ratified by this register):**

```
C - KEEP D17 OPEN / GROUP C

Meaning:
- no provider selected
- no source promoted
- no D17 contract relaxation
- no D18 final binding
- no empirical authorization
```

Human-ratification template (supplied for Human Governance use; MUST NOT be treated as filled):

```
Decision ID:        D17 (and D18 dependency status)
Decision:           ______________________ (RECOMMENDED: C - KEEP D17 OPEN / GROUP C)
Rationale:          ______________________
Effective specification version:  ______________________
Decision date:      ______________________
Authority:          HUMAN GOVERNANCE
```

The repository must not claim Human acceptance unless it already exists in canonical evidence. No such acceptance is recorded by this register.

## L. CLOSURE / STOP STATEMENT

```
CLOSURE RECORD (SUMMARY)
- D17 = OPEN / GROUP C  (data-authority blocked; no investigated $0 source satisfies the frozen contract)
- D18 = OPEN / GROUP C  (dependency-blocked on D17; NOT a schema defect)
- Draft Freeze = NOT READY (24/26 freeze checklist; D18 unsealed template; Human Auth pending)
- Empirical validation = NOT AUTHORIZED
- No provider selected; no provider promoted; no D17/D18 contract relaxation
- No new provider investigated; S-18 not re-audited; no Stooq endpoint re-audited
- No empirical work; no data ingestion; no backtest; no statistics computed
- No HYP_003; no ResearchReInceptionGate; no R1; no paper/live trading; capital unchanged ($0.00)
- No commit; no push
- This document is a state record; it grants nothing and ratifies nothing
```

STOP - D17 DATA AUTHORITY REMAINS OPEN; D18 REMAINS DEPENDENT; NO PROVIDER SELECTED; NO EMPIRICAL AUTHORIZATION.

---

### Verification Ledger
- Implementation Status: NONE - documentation-only register; no code/data/schema/gate/ROADMAP change.
- Contract Enforcement: STRICT FAIL-CLOSED - no PASS invented for CONDITIONAL/UNVERIFIED states; ACCESS != PIT; DOWNLOADABLE != PROVENANCE; LONG HISTORY != OFFICIAL CLOSE; FREE != LICENSE-SAFE; ARCHIVABLE != AS-PUBLISHED; SECONDARY EVIDENCE != BYTE-VERIFIED EVIDENCE; no frozen rule modified.
- Mathematical Authority: CANONICAL SPEC / RATIFIED RECORDS referenced (decision surface rows/sec 8/24.2/25.1/28/30/33; worksheet sec C/O-series; round4 spec; registry); external evidence explicitly labelled `EXTERNAL VERIFICATION - NOT HUMAN-RATIFIED`.
- Local Test Suite / Remote CI: NOT RUN / NOT APPLICABLE (documentation-only convention).
- Methodological Caveats: the "US LargeCap CFD" Stooq label and APIs.io key/CAPTCHA note are externally-sourced observations dated 2026-09-11 and are not Human-ratified nor byte-verified; the FRED range comes from FRED's own series metadata page; all unblock conditions are generic and do not constitute a vendor recommendation; this register does not change any frozen governance state.