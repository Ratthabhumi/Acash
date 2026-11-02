# UPI Private Snapshot Pilot — Runbook (V1_2)

Status: engineering ready, synthetic only. Owner-private runs stay disabled until the
owner ratifies `docs/governance/ODR_UPI_PRIVATE_OBSERVATION_001.json`. Nothing here
connects to a broker, places orders, moves money or uses the network.

## 1. Synthetic smoke test (works now)

```powershell
uv run python -m acash.invest.wealth_pack --snapshot docs/research/evidence/upi_v1_2_synthetic_snapshot.json --target-weights '{\"CORE_DIVERSIFIED\": \"0.7\", \"CASH\": \"0.3\"}' --output tmp_pilot
```

(The escaped quotes are for Windows PowerShell 5.1. In PowerShell 7.3+ or bash, use
`'{"CORE_DIVERSIFIED": "0.7", "CASH": "0.3"}'`.)

Expected output: `tmp_pilot/upi_v1_pack.json` and `tmp_pilot/upi_v1_pack.md`, byte-identical
to `docs/research/evidence/upi_v1_2_synthetic_pack/`. Expected values in THB:

| Field | Value |
|---|---|
| Computed NAV (PPDS quantity x price + settled cash) | 77220.00 |
| Observed value-only positions | 8250.00 |
| UNCLASSIFIED_HOLDINGS_VALUE | 10280.00 |
| Total best evidence | 95750.00 |
| Known-value / position-level coverage | 0.8926 / 0.7622 |

## 2. What a snapshot may contain (schema `ACASH_PRIVATE_PORTFOLIO_SNAPSHOT_V1_2`)

Copy the synthetic file as a template. Every amount is a decimal string.

| Evidence level | How to enter it |
|---|---|
| ACCOUNT_TOTAL_ONLY | `reported_total: {"amount", "currency"}` with no lines |
| SUBPORTFOLIO_TOTAL_ONLY | `sub_portfolio_totals: [{"sub_portfolio", "amount", "currency"}]` |
| POSITION_MARKET_VALUE_ONLY | a position with `observed_market_value` + currency and **no** `quantity` |
| QUANTITY_AND_PRICE_OBSERVED | a position with `quantity` plus a dated price in `prices` |
| TRANSACTION_HISTORY_RECONCILED | only through V2 replay (needs ODR 002); never from a snapshot |

Rules the validator enforces:
- A broker total is compared with its lines and never added to them. Its positive
  unexplained remainder is reported as UNCLASSIFIED_HOLDINGS_VALUE, never as cash or a holding.
- If an account has a total, its sub-portfolio totals are informational only.
- Optional identifiers per security: `instrument_type` (ETF, COMMON_STOCK, ADR, DR, CFD,
  MUTUAL_FUND, OTHER), `exchange_mic`, `isin` (check digit verified), `figi`, `trading_currency`.
  Without them a holding is SECURITY_IDENTITY_UNVERIFIED and is not merged across accounts.
- `valuation_date` is the US session date of the prices (for example, a Monday-morning
  Bangkok screenshot shows Friday's close). Session validity is reported as
  MARKET_SESSION_NOT_VERIFIED because there is no exchange calendar in the repository.
- `observed_at` needs a timezone offset, for example `2026-11-02T08:15:00+07:00`.
- Use opaque references such as `DIME_MAIN`, never account numbers (6+ digit runs are rejected).

## 3. Owner-local preparation (after ratification only)

1. Ratify: in `docs/governance/ODR_UPI_PRIVATE_OBSERVATION_001.json`, set `status` to
   `RATIFIED`, `ratified_by` to `OWNER` and `ratified_on` to the date, and keep
   `scope_schemas`. Commit this yourself.
2. Create `data/private/` (git-ignored). Confirm with `git check-ignore -v data/private/snapshot.json`.
   Do not put it in OneDrive, Dropbox or any other synced folder.
3. Copy the synthetic snapshot to `data/private/snapshot.json`, set
   `"data_class": "OWNER_PRIVATE_OBSERVATION"` and type your figures.
4. Copy `docs/research/evidence/upi_v1_synthetic_capacity.json` to `data/private/capacity.json`,
   set the same data class and type your figures.

## 4. Private command

```powershell
uv run python -m acash.invest.wealth_pack --snapshot data/private/snapshot.json --capacity data/private/capacity.json --report-date 2026-11-02 --output data/private/out
```

Output files: `data/private/out/upi_v1_pack.json`, `upi_v1_pack.md` and
`upi_run_manifest.json` (code commit, working-tree state and digests; keep it private).
Compare `evidence.THB.accounts[].account_total` against what the broker app shows. If
the totals differ, fix the snapshot and rerun. The same input always gives the same pack.

## 5. Troubleshooting

| Error code | Meaning / fix |
|---|---|
| PRIVATE_OBSERVATION_NOT_AUTHORIZED | ODR not ratified, or its `scope_schemas` lacks the file's schema |
| PRIVATE_LOCATION_NOT_IGNORED | input/output path is inside the repo but not under `data/private/` |
| PRIVATE_REF_NOT_OPAQUE | account/snapshot reference contains 6+ digits or lowercase letters |
| PRIVATE_NUMBER_MUST_BE_STRING | write amounts as `"123.45"`, not `123.45` |
| PRIVATE_POSITION_EVIDENCE_MISSING | position has neither `quantity` nor `observed_market_value` |
| PRIVATE_PRICE_MISSING / PRIVATE_UNUSED_PRICE | quantity line without a price, or a price for nothing held by quantity |
| PRIVATE_PRICE_DATE_MISMATCH / PRIVATE_FX_DATE_MISMATCH | price/FX `as_of` must equal `valuation_date` |
| PRIVATE_FX_RATE_MISSING | add both directions of each currency pair used |
| PRIVATE_NAV_NONPOSITIVE | the snapshot has no cash or quantity line at all; add at least one (totals-only snapshots support the evidence report but not the full pack) |
| PRIVATE_ISIN_INVALID | wrong ISIN check digit |

## 6. Not supported in this pilot

Native Dime!/Webull CSV/PDF import (BROKER_NATIVE_IMPORT_NOT_ESTABLISHED), screenshots/OCR,
historical performance from a snapshot, ETF look-through, tax computation, and any order
or transfer.
