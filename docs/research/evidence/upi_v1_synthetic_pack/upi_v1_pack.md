# ACASH Unified Portfolio Intelligence — SYNTHETIC_PUBLIC_FIXTURE

Snapshot `SYN_UPI_V1` valued 2026-10-30 (observed 2026-11-01T09:00:00+07:00) · support state **SNAPSHOT_ONLY** · performance **PERFORMANCE_NOT_ESTABLISHED** · pack `9722dabc916bbb01`

Read-only decision support. No orders, transfers, recurring plans or authority. Stress figures are illustrative, not forecasts.

## A. Total wealth
- NAV THB: **134691.50** (securities 97350.00, settled cash 37341.50; accrued interest excluded 13.20)
- NAV USD: **4081.56** (securities 2950.00, settled cash 1131.56; accrued interest excluded 0.40)

### By classification
| Bucket | Value | Weight |
|---|---:|---:|
| CASH | 37341.50 | 0.2772 |
| CORE_DIVERSIFIED | 70125.00 | 0.5206 |
| SPECULATIVE | 6600.00 | 0.0490 |
| THEMATIC | 17325.00 | 0.1286 |
| UNKNOWN | 3300.00 | 0.0245 |

### By broker
| Bucket | Value | Weight |
|---|---:|---:|
| BANK_B | 16500.00 | 0.1225 |
| BANK_C | 20000.00 | 0.1485 |
| BROKER_A | 98191.50 | 0.7290 |

### By currency
| Bucket | Value | Weight |
|---|---:|---:|
| THB | 20000.00 | 0.1485 |
| USD | 114691.50 | 0.8515 |

Concentration (DIRECT_HOLDINGS_ONLY; OVERLAP_NOT_ESTABLISHED): top1 0.5206, top5 0.7228, HHI 0.2906
Unrealized P&L (PARTIAL_COST_BASIS, cost-basis coverage 0.9661): {'USD': '30.00'} — UNREALIZED_PNL_NOT_ESTABLISHED for COST_BASIS_UNKNOWN lines; FX_COMPONENT_NOT_ESTABLISHED; ACQUISITION_HISTORY_NOT_ESTABLISHED

### Illustrative stress (not forecasts)
| Scenario | NAV delta | Share |
|---|---:|---:|
| EQUITY_DRAWDOWN_30 | -29205.00 | -0.2168 |
| THEMATIC_SPECULATIVE_DRAWDOWN_50 | -11962.50 | -0.0888 |
| REPORTING_CCY_APPRECIATION_10 | -11469.15 | -0.0852 |
| REPORTING_CCY_DEPRECIATION_10 | 11469.15 | 0.0852 |
Not evaluated: {'TECH_SELLOFF': 'NOT_EVALUATED_SECTOR_DATA_MISSING', 'SMALL_CAP_GROWTH_DRAWDOWN': 'NOT_EVALUATED_SIZE_STYLE_DATA_MISSING', 'LIQUIDITY_STRESS': 'NOT_EVALUATED_LIQUIDITY_DATA_MISSING'}

### Reconciliation (observed vs quantity x price)
- BROKER_A_MAIN SYNIDX Core: CONSISTENT_WITHIN_DISPLAY_ROUNDING
- BROKER_A_MAIN SYNIDX Theme: NOT_DISPLAYED
- BROKER_A_MAIN SYNMOON Theme: UNEXPLAINED_DIFFERENCE
- BROKER_A_MAIN SYNNEW Unsorted: CONSISTENT_WITHIN_DISPLAY_ROUNDING
- BROKER_A_MAIN SYNTECH Theme: CONSISTENT_WITHIN_DISPLAY_ROUNDING

## B. Long-term accounts
| Bucket | Value | Weight |
|---|---:|---:|
| BROKER_A_MAIN/(account cash) | 841.50 | 0.0062 |
| BROKER_A_MAIN/Core | 66000.00 | 0.4900 |
| BROKER_A_MAIN/Theme | 28050.00 | 0.2083 |
| BROKER_A_MAIN/Unsorted | 3300.00 | 0.0245 |

DESCRIPTIVE_ONLY: families are not ranked, not recommended and not suitability-assessed.
- A_HOLD_CURRENT: Keep current holdings; contribute to cash only. e.g. -
- B_GLOBAL_EQUITY: Single global equity index fund. e.g. VT
- C_US_CORE_PLUS_EX_US: US broad index plus ex-US index. e.g. VOO, VXUS
- D_EQUITY_PLUS_DEFENSIVE: Broad equity plus bonds or T-bills. e.g. VT, BND, BIL
- E_CASH_ACCUMULATION: Accumulate cash/reserve before any investing. e.g. BIL
- Contribution-first view: {'CASH': '878.73', 'CORE_DIVERSIFIED': '5121.27', 'SPECULATIVE': '0.00', 'THEMATIC': '0.00', 'UNKNOWN': '0.00'}

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
- OVERLAP_NOT_ESTABLISHED: no dated constituent weights.
- COST_BASIS_INCOMPLETE: PARTIAL_COST_BASIS; unrealized P&L only for the known-cost subset.
- UNKNOWN_CLASSIFICATION_PRESENT: evidence-backed classification missing for some holdings.
- RESERVE_SHORTFALL: rebuild emergency reserve before new risk.
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
