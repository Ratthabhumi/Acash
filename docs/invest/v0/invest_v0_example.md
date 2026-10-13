# ACASH Invest V0 — Read-Only Investment Report (SYNTHETIC)

- As of: `2026-10-02`
- Base currency: `USD`
- Evidence: `SYNTHETIC_DEMONSTRATION`
- Total NAV: `1000` USD
- Cash total: `150`

## Allocation (NAV-inclusive)

| Holding | Kind | Market value | NAV weight |
|---|---|---|---|
| ETF_A | POSITION | 400 | 0.4 |
| ETF_B | POSITION | 450 | 0.45 |
| CASH:USD | CASH | 150 | 0.15 |

## Invested-only exposure (cash excluded by construction)
- Status: `ESTABLISHED`
- ETF_A: value `400`, weight `0.4705882352941176470588235294`
- ETF_B: value `450`, weight `0.5294117647058823529411764706`

## Reconciliation
- Status: `ESTABLISHED`
- Matched: `True`
- Independent: `False`

## Costs
- commission_floor [MODELLED]: IBKR Tiered-style per-order minimum assumption; NOT account-verified. (amount: 0.35)
- withholding_tax [UNKNOWN]: Owner-specific tax treatment unestablished; never assumed zero. (amount: None)
- Total: `None` (NOT_ESTABLISHED)

## Missing data and uncertainty
- No qualified historical ETF price history.
- No expected returns, risk forecasts, or drawdown estimates.
- No independent broker reconciliation.
- No account-verified fees; all costs are assumptions unless stated.
- No tax, FX funding, or market-impact evidence.

## Execution
- Order submission authorized: `False`
- Capital authority (USD): `0.00`
- Recommendation: BLOCKED: synthetic demonstration only. No investment recommendation is authorized. NO_REAL_ORDERS.

Ledger head: `3f5a0e327d76c2650f1a8df4fc614fdf5526a3e47bfe6f71489c51091b39c2c7` (3 entries)
