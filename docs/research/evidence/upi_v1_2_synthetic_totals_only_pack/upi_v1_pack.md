# ACASH Unified Portfolio Intelligence — SYNTHETIC_PUBLIC_FIXTURE

Snapshot `SYN_TOTALS_ONLY_V1_2` valued 2026-10-30 (observed 2026-11-02T08:15:00+07:00) · support state **SNAPSHOT_ONLY** · performance **PERFORMANCE_NOT_ESTABLISHED** · pack `50ab73b40a7dcdd2`

Read-only decision support. No orders, transfers, recurring plans or authority. Stress figures are illustrative, not forecasts.

## A. Total wealth
**EVIDENCE_ONLY_REPORT**: computed analytics are not produced. Not supported: ALLOCATION_BY_CLASSIFICATION, COMPUTED_CONCENTRATION, UNREALIZED_PNL, ILLUSTRATIVE_STRESS, CONTRIBUTION_FIRST_ALLOCATION, PERFORMANCE.

### Evidence and observed totals (THB)
- Computed (PPDS quantity x price + settled cash): 0.00; observed value-only positions: 0.00; UNCLASSIFIED_HOLDINGS_VALUE: 90750.00; total best evidence: **0.00**
- Coverage: known value NOT_APPLICABLE_NO_VALUE, position level NOT_APPLICABLE_NO_SECURITIES, cash observed accounts 0/2, totals reconciled NOT_APPLICABLE_NO_VALUE, cost basis NOT_APPLICABLE_NO_VALUE, history NOT_ESTABLISHED_SNAPSHOT_ONLY
- Concentration (COMPLETE): top1 0.0000, unclassified share 0.0000, HHI 0.0000; market session MARKET_SESSION_NOT_VERIFIED
| Account | Evidence level | Account total | Difference | Flags |
|---|---|---|---:|---|
| BROKER_D_FCD | ACCOUNT_TOTAL_ONLY | INSUFFICIENT_EVIDENCE | 500.00 | - |
| BROKER_D_MAIN | SUBPORTFOLIO_TOTAL_ONLY | INSUFFICIENT_EVIDENCE | 2250.00 | SUBPORTFOLIO_TOTALS_INFORMATIONAL_ACCOUNT_TOTAL_GOVERNS |

## B. Long-term accounts
| Bucket | Value | Weight |
|---|---:|---:|
| BROKER_D_MAIN/(account):UNCLASSIFIED_HOLDINGS_VALUE | 74250.00 | 0.0000 |

DESCRIPTIVE_ONLY: families are not ranked, not recommended and not suitability-assessed.
- A_HOLD_CURRENT: Keep current holdings; contribute to cash only. e.g. -
- B_GLOBAL_EQUITY: Single global equity index fund. e.g. VT
- C_US_CORE_PLUS_EX_US: US broad index plus ex-US index. e.g. VOO, VXUS
- D_EQUITY_PLUS_DEFENSIVE: Broad equity plus bonds or T-bills. e.g. VT, BND, BIL
- E_CASH_ACCUMULATION: Accumulate cash/reserve before any investing. e.g. BIL
- Contribution-first view: NOT_EVALUATED_EVIDENCE_ONLY_REPORT

## C. Quant research workspace
- Status: RESEARCH_ONLY_NOT_AUTHORIZED; budget 8000.00 THB (HYPOTHETICAL_RESEARCH_BUDGET, NOT_AUTHORIZED, reserve funding FORBIDDEN)
- Benchmarks required: CASH, BUY_AND_HOLD, EQUAL_WEIGHT; validation DSR, CPCV, PBO
- Webull OpenAPI: INTERFACE_NOT_DOCUMENTED: EXTERNAL_RESEARCH_REQUIRED (no credentials, no endpoints called)

## D. Financial capacity
- Monthly surplus 15000.00 THB; reserve 20000.00 / target 30000.00 (2.00 months, RESERVE_SHORTFALL)
| Contribution | Residual | Months to reserve target | Status |
|---:|---:|---:|---|
| 5000.00 | 10000.00 | 1 | RESERVE_SHORTFALL_PRIORITY |
| 7500.00 | 7500.00 | 2 | RESERVE_SHORTFALL_PRIORITY |
| 10000.00 | 5000.00 | 2 | RESERVE_SHORTFALL_PRIORITY |
| 6000.00 | 9000.00 | 2 | RESERVE_SHORTFALL_PRIORITY |

V38 route costs for 5000 THB (MANUAL, 1 month; unranked):
| Route | Investable USD | Cost status | Decision |
|---|---:|---|---|
| IBKR Pro via K PLUS SWIFT SHAR | 138.89 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| IBKR Pro via K PLUS SWIFT DEBT | 118.42 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| IBKR Pro via K PLUS SWIFT CRED | 134.32 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| Dime! Thailand (KKP) | 147.57 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| Webull Thailand (Manual) | 147.50 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| Webull Thailand (DCA - currently advertised 0%) | - | NOT_EVALUATED | NOT_ELIGIBLE |
| Webull Thailand (DCA - 0.10% conflict sensitivity) | - | NOT_EVALUATED | NOT_ELIGIBLE |
| CASH / NO TRADE | 0 | NOT_APPLICABLE | CASH_NO_TRADE |

V38 route costs for 7500 THB (MANUAL, 1 month; unranked):
| Route | Investable USD | Cost status | Decision |
|---|---:|---|---|
| IBKR Pro via K PLUS SWIFT SHAR | 212.49 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| IBKR Pro via K PLUS SWIFT DEBT | 191.94 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| IBKR Pro via K PLUS SWIFT CRED | 207.90 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| Dime! Thailand (KKP) | 221.35 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| Webull Thailand (Manual) | 221.26 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| Webull Thailand (DCA - currently advertised 0%) | - | NOT_EVALUATED | NOT_ELIGIBLE |
| Webull Thailand (DCA - 0.10% conflict sensitivity) | - | NOT_EVALUATED | NOT_ELIGIBLE |
| CASH / NO TRADE | 0 | NOT_APPLICABLE | CASH_NO_TRADE |

V38 route costs for 10000 THB (MANUAL, 1 month; unranked):
| Route | Investable USD | Cost status | Decision |
|---|---:|---|---|
| IBKR Pro via K PLUS SWIFT SHAR | 285.88 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| IBKR Pro via K PLUS SWIFT DEBT | 265.33 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| IBKR Pro via K PLUS SWIFT CRED | 281.30 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| Dime! Thailand (KKP) | 295.14 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| Webull Thailand (Manual) | 295.01 | LOWER_BOUND_ONLY | COST_EVIDENCE_INCOMPLETE |
| Webull Thailand (DCA - currently advertised 0%) | - | NOT_EVALUATED | NOT_ELIGIBLE |
| Webull Thailand (DCA - 0.10% conflict sensitivity) | - | NOT_EVALUATED | NOT_ELIGIBLE |
| CASH / NO TRADE | 0 | NOT_APPLICABLE | CASH_NO_TRADE |

## E. Decision status
**NO_ACTION_PENDING_EVIDENCE** (orders generated: 0)
- PERFORMANCE_NOT_ESTABLISHED: snapshot only, no cash-flow history.
- EVIDENCE_ONLY_REPORT: no cash or quantity line carries value; allocation, concentration, P&L and stress are not computed.
- RESERVE_SHORTFALL: rebuild emergency reserve before new risk.
- UNCLASSIFIED_HOLDINGS_PRESENT: broker totals exceed identified lines; concentration is a lower bound.
- ACCOUNT_TOTALS_NOT_FULLY_RECONCILED: see evidence.accounts.
- MARKET_SESSION_NOT_VERIFIED: the pack applies no exchange calendar; preflight checks XNYS price times against the 2026-2028 NYSE fixture only.
- V38_ROUTE_EVIDENCE_INCOMPLETE: FX spread and per-symbol eligibility remain owner-evidence items.
- PRIVATE_OBSERVATION_AUTHORIZATION_NOT_REQUIRED: synthetic fixture; no trading or capital authority.
- V38 pack reference `31d381a296303aaf` (docs/research/evidence/v38_investor_decision_pack_20261101.json)

## Governance
- NO_REAL_ORDERS: True
- REAL_CAPITAL_AUTHORITY_USD: 0.00
- D5_REAL_ADMISSION: NOT_ADMITTED
- LANE_A_B: UNISSUED
- HYP_003: TERMINALLY_FALSIFIED
- EXECUTION_AUTHORITY_FROM_EVIDENCE: NONE
- research_admission: NOT_ADMITTED_PRIVATE_OBSERVATION
- d5_eligible: False
- trading_authority: NONE
- capital_authority_usd: 0.00
- order_controls: None
