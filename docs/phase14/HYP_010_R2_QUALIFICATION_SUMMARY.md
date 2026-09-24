# HYP_010 R2 Qualification Summary

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_010_R2_PROVIDER_AND_SPONSOR_AUTHORITY_QUALIFICATION]
[OVERALL: R2_PROVIDER_QUALIFIED_SPONSOR_AUTHORITY_BLOCKED]
```

- **Manifest:** `docs/phase14/manifests/HYP_010_R2_QUALIFICATION_SUMMARY.json`
- **Starting SHA:** `2653c2564e8ab0216183d9bd5773670bddb27020`

## 1. Provider (PASS)

Alpaca 1Day SIP tiny probe 2017-01-03..06: SPY/VEU/AGG/BIL × split/raw all
4/4 rows, aligned, no spill/duplicates. 8 HTTP attempts. Evidence
`data/hyp_010/probe_evidence.json`. Detail:
`docs/phase14/HYP_010_R2_PROVIDER_QUALIFICATION.md`.

## 2. Sponsor Authorities (3 PASS, 1 BLOCKED)

- SPY: QUALIFIED (36 quarterly, sealed composite + workbook corroboration).
- BIL: QUALIFIED (108 monthly official SSGA workbook records, affirmed zeros flagged).
- AGG: QUALIFIED (108 monthly official iShares page records, Feb–Dec schedule).
- VEU: BLOCKED (no obtainable official machine-readable authority; interactive
  ten-year export cannot prove 2016–2019 coverage; no substitution performed).

## 3. Prospective Start (Calendar-Only, Zero Price Access)

- R1 commit timestamp authority: `2026-09-24T20:00:10Z`.
- First NYSE regular-session open strictly after: **2026-09-25T13:30:00Z**
  (regular 390-minute session, CA-1 authority). Prospective prices: 0 reads.

## 4. Performance / Access Locks

- Full historical bar acquisition: NOT executed. Momentum/signals/trades/P&L/
  Sharpe/MDD/benchmark: NOT computed. Recent-stress/quarantine/prospective
  price access: 0. Paper NOT_AUTHORIZED, live LOCKED, capital 0.00,
  NO_REAL_ORDERS=true.

## 5. Next Human Action

Vanguard-official VEU 2016-covering authority research (separate human
research), then re-authorization. No historical dataset build until all four
sponsor authorities pass.
