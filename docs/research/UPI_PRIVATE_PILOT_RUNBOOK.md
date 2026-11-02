# UPI Private Snapshot Pilot — Runbook (V1_2)

Status: engineering ready, synthetic only. Owner-private runs stay disabled until the
owner ratifies `docs/governance/ODR_UPI_PRIVATE_OBSERVATION_001.json`. ODR-002
(transaction histories) is not needed for this pilot. Nothing here connects to a broker,
places orders, moves money or uses the network. All commands are for Windows PowerShell,
run from the repository root.

## 1. Synthetic smoke test (works now)

```powershell
Set-Content -Path tmp_targets.json -Value '{"CORE_DIVERSIFIED": "0.7", "CASH": "0.3"}' -Encoding ascii
uv run python -m acash.invest.preflight --snapshot docs/research/evidence/upi_v1_2_synthetic_snapshot.json --capacity docs/research/evidence/upi_v1_synthetic_capacity.json
uv run python -m acash.invest.wealth_pack --snapshot docs/research/evidence/upi_v1_2_synthetic_snapshot.json --target-weights-file tmp_targets.json --output tmp_pilot
```

The preflight should report `READY_WITH_WARNINGS` (the fixture contains deliberate
gaps). `tmp_pilot/upi_v1_pack.{json,md}` should be byte-identical to
`docs/research/evidence/upi_v1_2_synthetic_pack/`. The THB values are synthetic, not the
owner's:

| Field | Value |
|---|---|
| Computed NAV (PPDS quantity x price + settled cash) | 77220.00 |
| Observed value-only positions | 8250.00 |
| UNCLASSIFIED_HOLDINGS_VALUE | 10280.00 |
| Total best evidence | 95750.00 |

A totals-only snapshot (`upi_v1_2_synthetic_totals_only.json`) gives
`EVIDENCE_ONLY_REPORT`: no computed NAV, and allocation, concentration, P&L, stress and
contribution-first are not computed. Totals are reported as observed and unclassified
(THB 90750.00 in that fixture).

## 2. Snapshot contents (`ACASH_PRIVATE_PORTFOLIO_SNAPSHOT_V1_2`)

Copy `docs/research/evidence/upi_v1_2_synthetic_snapshot.json` as the template. Every
amount is a decimal string such as `"123.45"`, typed exactly as the app displays it (the
displayed precision sets the rounding tolerance).

| What the app shows | How to enter it | Evidence level |
|---|---|---|
| Account total only | `reported_total: {"amount", "currency"}` with no lines | ACCOUNT_TOTAL_ONLY |
| Sub-portfolio totals only | `sub_portfolio_totals: [{"sub_portfolio", "amount", "currency"}]` | SUBPORTFOLIO_TOTAL_ONLY |
| Holding value but no share count | position with `observed_market_value` + currency, no `quantity` | POSITION_MARKET_VALUE_ONLY |
| Shares and price | position with `quantity`, plus the price in `prices` dated `valuation_date` | QUANTITY_AND_PRICE_OBSERVED |
| Cash | `cash: [{"currency", "amount", "kind": "SETTLED"}]`; interest not yet paid uses `"ACCRUED_INTEREST"` (excluded from NAV) | — |

### Dime! accounts: one account per real balance, never twice

- Dime! securities account (e.g. `DIME_MAIN`, role `LONG_TERM`, base `USD`): holdings,
  sub-portfolio totals, its USD cash, and the account total shown on the portfolio screen.
- Dime! FCD (e.g. `DIME_FCD`, role `CASH_RESERVE` or `OTHER`): the FCD balance only.
  Dime!'s guide distinguishes FCD from another Dime! USD account type. Enter a USD figure
  under one account only, unless the app shows it as two separate balances.
- Bank savings or the emergency reserve (e.g. `BANK_SAVINGS`, `CASH_RESERVE`, `THB`).
- If the portfolio screen's total already includes the USD cash, enter the cash as a line
  in the same account. The total is compared with its lines and never added to them.
- The preflight warns `POSSIBLE_DUPLICATE_CASH_ACROSS_ACCOUNTS` when two accounts of one
  broker carry identical cash amounts. This is a heuristic, and you must confirm or fix it.

### Dates and identifiers

- `observed_at` is when you read the app, with offset, e.g. `2026-11-02T08:15:00+07:00`.
- `valuation_date` is the US session date of the prices. A Monday-morning Bangkok reading
  shows Friday's close. The US open moves with US daylight saving (21:30 ICT in November
  2026). Session validity is reported as `MARKET_SESSION_NOT_VERIFIED`, because no exchange
  calendar is bundled.
- FX: add both directions (`USD->THB` and `THB->USD`) with the source and the same `as_of`.
  Do not reuse an app's FX conversion quote as a reference rate unless you label its
  `source_id` accordingly.
- Use opaque references (`DIME_MAIN`, not account numbers; 6+ digit runs are rejected).
- Optional identifiers: `instrument_type`, `exchange_mic`, `isin`, `figi`, `trading_currency`.
  Without them a holding stays `SECURITY_IDENTITY_UNVERIFIED` and is not merged across accounts.
- Leave out cost basis if unknown. Never estimate it.

## 3. Owner activation (only after you ratify ODR-001)

1. Ratify: in `docs/governance/ODR_UPI_PRIVATE_OBSERVATION_001.json`, set `status` to
   `RATIFIED`, `ratified_by` to `OWNER` and `ratified_on` to the date. Keep
   `scope_schemas`. Commit this yourself.
2. Make sure the repository is not inside OneDrive, Dropbox, iCloud or Google Drive
   (`(Get-Location).Path` must not contain such a folder). Then:
   ```powershell
   New-Item -ItemType Directory -Force data/private | Out-Null
   git check-ignore -v data/private/snapshot.json
   ```
   The second command must print a `.gitignore` rule. If it prints nothing, stop.
3. Copy the templates and set `"data_class": "OWNER_PRIVATE_OBSERVATION"` in both:
   ```powershell
   Copy-Item docs/research/evidence/upi_v1_2_synthetic_snapshot.json data/private/snapshot.json
   Copy-Item docs/research/evidence/upi_v1_synthetic_capacity.json data/private/capacity.json
   ```
   Replace every synthetic figure with what the app shows on the same day. Delete the
   lines you cannot see. Do not keep synthetic values.
4. Preflight (read-only; prints statuses, never amounts):
   ```powershell
   uv run python -m acash.invest.preflight --snapshot data/private/snapshot.json --capacity data/private/capacity.json --output data/private/out --report-date 2026-11-02
   ```
5. Report:
   ```powershell
   uv run python -m acash.invest.wealth_pack --snapshot data/private/snapshot.json --capacity data/private/capacity.json --report-date 2026-11-02 --output data/private/out
   ```
   This writes `data/private/out/upi_v1_pack.json`, `upi_v1_pack.md` and
   `upi_run_manifest.json`. The manifest holds the commit and input digests; keep it private.
6. Reconcile: in the Markdown section "Evidence and observed totals", each account should
   read `RECONCILED` or `CONSISTENT_WITH_DISPLAY_ROUNDING`. `UNEXPLAINED_DIFFERENCE` means a
   holding or cash line is missing or mistyped. A negative difference with
   `KNOWN_VALUE_EXCEEDS_REPORTED_TOTAL` usually means a duplicated line. Fix the snapshot
   and rerun; the same input always gives the same pack.

Revoke: set `status` to anything other than `RATIFIED` (e.g. `REVOKED`) and commit; the
gate closes immediately. Remove private data: `Remove-Item -Recurse -Force data/private`
(this also deletes reports and manifests). Check the recycle bin and any backups yourself.

## 4. Troubleshooting

| Code | Meaning / fix |
|---|---|
| PRIVATE_OBSERVATION_NOT_AUTHORIZED | ODR-001 not ratified, or `scope_schemas` lacks the file's schema |
| PRIVATE_LOCATION_NOT_IGNORED | input/output inside the repo but not under `data/private/` |
| PRIVATE_REF_NOT_OPAQUE | reference has lowercase letters or 6+ digits |
| PRIVATE_NUMBER_MUST_BE_STRING | write `"123.45"`, not `123.45` |
| PRIVATE_POSITION_EVIDENCE_MISSING | position has neither `quantity` nor `observed_market_value` |
| PRIVATE_PRICE_MISSING / PRIVATE_UNUSED_PRICE | quantity line without a price, or a price for nothing held by quantity |
| PRIVATE_PRICE_DATE_MISMATCH / PRIVATE_FX_DATE_MISMATCH | price/FX `as_of` must equal `valuation_date` |
| PRIVATE_FX_RATE_MISSING | add both directions of each currency pair |
| PRIVATE_DUPLICATE_CASH_LINE / PRIVATE_DUPLICATE_POSITION_LINE | same line entered twice in one account |
| PRIVATE_ISIN_INVALID | ISIN check digit wrong |
| RESIDUAL_NOT_ESTABLISHED (status) | a total's currency cannot be converted with the supplied FX |
| TARGET_WEIGHTS_* | target weights file is not a JSON mapping of decimal strings |

## 5. Not supported in this pilot

Native Dime!/Webull CSV/PDF import (`BROKER_NATIVE_IMPORT_NOT_ESTABLISHED`),
screenshots/OCR, performance from a snapshot, ETF look-through, exchange-calendar
validation, tax computation, and any order or transfer.
