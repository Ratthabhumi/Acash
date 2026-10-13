# Lane B: Corporate-Action Qualification Specification (Offline, Unissued)

**Status:** SPECIFICATION ONLY — NO AUTHORITY ISSUED, NO DATA ACQUIRED
**Date:** 2026-10-13
**Relation to Lane A:** Lane A is the bounded daily-bars feasibility canary (VOO/BND/GLD/BIL, 1Day, 2026-09-28..2026-10-02, adjustments raw+all). Lane B is the subsequent, separately-gated corporate-action (dividend/split) qualification phase. Lane B is NOT authorized by any Lane A issuance and requires its own explicit operator authority.

## 1. Purpose

Qualify a corporate-action data path (dividend cash amounts and split factors for the ACASH ETF universe) to the same fail-closed standard as the price pipeline, so that adjusted-return construction is admissible for research. This is a qualification, not an ingestion: no vendor is subscribed, no HTTP request has been made, and no corporate-action record exists in the repository as of this specification.

## 2. Canonical Universe and Window

| Field | Value | Authority |
| :--- | :--- | :--- |
| Symbols | ACWI, AGG, SPY, BIL, VEU (sponsor-dividend panel); VOO/BND/GLD/BIL remain price-canary universe | Sponsor authority model in `src/acash/data/qualification/hyp_010_sponsor_authority.py` |
| Window | 2016-01-01 .. 2024-12-31 (HYP_010 panel) or Lane A window 2026-09-28..2026-10-02 (price-only cross-check) | Existing authority periods |
| Event types | Cash dividends (ex-date, pay-date, record-date, amount per share); forward/reverse splits (ex-date, numerator, denominator) | — |
| Adjustment semantics | Provider `adjustment=raw` prices + explicit corporate-action factors; NEVER accept provider-adjusted prices without the underlying factors | ACASH unit-space discipline |

## 3. Preselected Real-Event Validation Anchors

Validation uses **preselected, externally documented real corporate actions** — never vendor data self-certified by the same provider that serves prices. Each anchor must be independently confirmable from sponsor-official sources (fund distributor declarations, SEC filings) and carries a mandatory SOURCE-SPECIFIC EVIDENCE BINDING recorded before first use: the exact sponsor document/source name, the window that source covers, and the source's date-field conventions (distributor distribution tables and SEC filings may use different date-field semantics; they are not interchangeable). An anchor whose binding is incomplete may not be used for validation, and disagreement between admissible sources falls to rule 5 (quarantine), never to a silent choice of source:

1. **SPY quarterly cash distribution** (State Street SPDR official declaration; one ex-date per calendar quarter in 2016–2024).
2. **AGG monthly distribution** (iShares official distribution history; Feb–Dec plus December extra; January absent across the 2016–2024 HYP_010 panel — an observed empirical pattern within that cited window, NOT a guaranteed schedule law for any other window).
3. **ACWI semi-annual distribution** (June and December halves each contain >= 1 ex-date).
4. **A known ETF split or reverse split** in the universe (if none exists in-window, the split path is validated against a synthetic-but-documented case and labeled HEURISTIC, never presented as empirical coverage).

## 4. Qualification Rules (Fail-Closed)

1. **UNKNOWN-basis rejection:** any corporate-action record whose source identity cannot be bound to a sponsor-official or explicitly licensed authority is classified `UNKNOWN_BASIS` and REJECTED. There is no implied-zero: an absent record is a coverage gap, never a zero dividend (inherited from `hyp_010_sponsor_authority.py`).
2. **Schedule-pattern deviations quarantine, never auto-absorb, never auto-reject canonical data:** sponsor-schedule *patterns* evidenced within a cited window (e.g., January AGG/BIL ex-dates absent in the 2016–2024 HYP_010 panel) are empirical heuristics, not canonical law. An event deviating from such a pattern must be classified `PATTERN_DEVIATION` and quarantined (as `CONTRADICTORY`) for human adjudication against the sponsor-official source for that record's window; it is neither silently absorbed nor raised as an automatic `DataContractError` against otherwise admissible data. Sponsor-official confirmation admits the record, and the pattern update is recorded in a NEW additive document. An event whose source cannot be verified remains `UNKNOWN_BASIS` and is REJECTED (rule 1).
3. **Amount sign and type bounds:** cash amounts must be finite, >= 0, and within `validate_decimal128_bounds`; splits must be positive rational factors. Violations raise, never clamp.
4. **Date ordering:** ex-date <= record-date <= pay-date per record; violations are contradictions.
5. **Dual-source disagreement:** if two admissible authorities disagree on an event, the event is quarantined `CONTRADICTORY` until a human adjudicates. No silent majority rule.
6. **Manifest lineage:** every accepted artifact receives page-level SHA-256 plus a framed composite digest via `compute_framed_composite_sha256` (`src/acash/data/qualification/manifest.py`), bound to the authority record's approval reference.

## 5. Explicitly Out of Scope (This Specification)

- Any network request to a corporate-action vendor or provider endpoint.
- Any subscription, trial signup, or paid data agreement.
- Any decision to adopt Alpaca `adjustment=all` bars as an implicit substitute for explicit factors.
- Any modification of HYP_003/HYP_009/HYP_010/HYP_011 evidence.

## 6. Gate Dependencies

```
Human issues Lane B authority (symbols, window, vendor, budget)
  -> offline authority validation (lane_a_authority.py patterns, extended)
  -> zero-network dry run (plan = allowlisted events x budget check)
  -> [separately authorized network execution]
  -> manifest + anchor comparison -> qualification verdict
```

Lane B execution, if ever authorized, MUST reuse the Lane A authority/ledger/dry-run primitives (`src/acash/data/qualification/lane_a_authority.py`) with a distinct scope constant; it MUST NOT extend `LANE_A_SYMBOLS` or the Lane A window in place.
