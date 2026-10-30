# V37A fixed-THB funding: executed results (2026-10-27)

Fixed monthly THB savings now enter the existing D6 remittance, contribution, accounting, FX and attribution path. No second execution engine was added. Legacy USD-native behavior and frozen V35/V36 results are preserved.

Owner-authorized PR67 was merged at `499a3a751e22c46d0a2ac22bf7d8a35247630512`; post-merge CI [40384005612](https://github.com/Ratthabhumi/Acash/actions/runs/40384005612) succeeded. The [20-cell freeze](V37A_FIXED_THB_FROZEN_SPEC_20261027.md) was committed as `bddb1e4` before implementation and outcomes. Execution source: `d1a2216aaa03f442dcbe988ef93b248a231dbb8d`. Later reporting commits do not change that runtime.

## Results and interpretation

VOO/BND 60/40, 2016–2025, initial USD1,000 plus 119 monthly saving events. Base sender fee THB400, spread 0.5%, intermediary USD0. E1/E3/E6/E12 remit every 1/3/6/12 savings events; CTRL is monthly zero-fee/spread with real cent rounding retained. Fees are scenario assumptions, not verified historical retail quotes. Household terminal value includes broker value and external savings; contributions are not investment returns. XIRR is money-weighted household THB performance; TWR below is broker USD time-weighted annualized performance.

At THB3,000/month, sender fees total THB47,600 monthly versus THB15,600 quarterly. Household THB XIRR is 6.50% monthly, 7.96% quarterly, 8.15% half-yearly and 8.10% annually. The latter two retain THB15,000 and THB33,000 outside the broker at the end. Lower fees trade off against delayed market exposure. The largest observed result is not evidence of an optimal future cadence; no grid or assumptions were changed after outcomes.

## 20 frozen primary cells

| Case | Household terminal THB | Household THB XIRR | Broker USD TWR/yr | Sender fees THB | End external THB | Mean external THB |
|---|---:|---:|---:|---:|---:|---:|
| THB1000_E1 | 191,729.55 | 3.39% | 9.70% | 47,600.00 | 0.00 | 0.00 |
| THB1000_E3 | 241,016.14 | 6.99% | 9.68% | 15,600.00 | 2,000.00 | 1,001.19 |
| THB1000_E6 | 250,992.12 | 7.62% | 9.64% | 7,600.00 | 5,000.00 | 2,509.55 |
| THB1000_E12 | 254,834.28 | 7.86% | 9.67% | 3,600.00 | 11,000.00 | 5,545.35 |
| THB1000_CTRL | 267,275.90 | 8.60% | 9.66% | 0.00 | 0.00 | 0.00 |
| THB3000_E1 | 564,882.55 | 6.50% | 9.58% | 47,600.00 | 0.00 | 0.00 |
| THB3000_E3 | 614,194.95 | 7.96% | 9.65% | 15,600.00 | 6,000.00 | 3,003.58 |
| THB3000_E6 | 620,877.67 | 8.15% | 9.68% | 7,600.00 | 15,000.00 | 7,528.64 |
| THB3000_E12 | 619,109.92 | 8.10% | 9.70% | 3,600.00 | 33,000.00 | 16,636.04 |
| THB3000_CTRL | 642,333.53 | 8.75% | 9.57% | 0.00 | 0.00 | 0.00 |
| THB5000_E1 | 938,264.83 | 7.33% | 9.53% | 47,600.00 | 0.00 | 0.00 |
| THB5000_E3 | 989,770.60 | 8.29% | 9.70% | 15,600.00 | 10,000.00 | 5,005.97 |
| THB5000_E6 | 991,107.92 | 8.32% | 9.70% | 7,600.00 | 25,000.00 | 12,547.73 |
| THB5000_E12 | 983,417.69 | 8.18% | 9.70% | 3,600.00 | 55,000.00 | 27,726.73 |
| THB5000_CTRL | 1,017,730.21 | 8.80% | 9.53% | 0.00 | 0.00 | 0.00 |
| THB10000_E1 | 1,878,489.04 | 8.09% | 9.57% | 47,600.00 | 0.00 | 0.00 |
| THB10000_E3 | 1,928,781.31 | 8.58% | 9.74% | 15,600.00 | 20,000.00 | 10,011.93 |
| THB10000_E6 | 1,916,762.29 | 8.46% | 9.72% | 7,600.00 | 50,000.00 | 25,095.47 |
| THB10000_E12 | 1,894,272.85 | 8.24% | 9.71% | 3,600.00 | 110,000.00 | 55,453.46 |
| THB10000_CTRL | 1,963,410.91 | 8.91% | 9.58% | 0.00 | 0.00 | 0.00 |

## 7 frozen one-at-a-time sensitivities

| Case | Household terminal THB | Household THB XIRR | Broker USD TWR/yr | Sender fees THB | End external THB | Mean external THB |
|---|---:|---:|---:|---:|---:|---:|
| SENS_cost_row_R2F | 610,298.91 | 7.85% | 9.47% | 15,600.00 | 6,000.00 | 3,003.58 |
| SENS_delay_sessions_1 | 614,294.83 | 7.97% | 9.68% | 15,600.00 | 6,000.00 | 3,003.58 |
| SENS_delay_sessions_3 | 613,143.69 | 7.93% | 9.62% | 15,600.00 | 6,000.00 | 3,003.58 |
| SENS_intermediary_fee_usd_15 | 583,139.47 | 7.05% | 9.65% | 15,600.00 | 6,000.00 | 3,003.58 |
| SENS_sender_fee_thb_250 | 623,478.84 | 8.23% | 9.65% | 9,750.00 | 6,000.00 | 3,003.58 |
| SENS_sender_fee_thb_550 | 604,911.99 | 7.70% | 9.65% | 21,450.00 | 6,000.00 | 3,003.58 |
| SENS_whole_shares_True | 595,987.54 | 7.44% | 9.14% | 15,600.00 | 6,000.00 | 3,003.58 |

Sensitivities use THB3,000/E3. Whole shares lower observed terminal wealth to THB595,987.54; intermediary USD15 lowers it to THB583,139.47. These are separate one-factor scenarios, not additive forecasts. All 27 actual cases end with zero USD in transit; dedicated boundary tests exercise nonzero terminal transit. Mean external cash is the inherited end-session average.

## Lineage and reproduction

[Machine-readable aggregate results](evidence/v37a_result_summary_20261027.json) retain full-precision CSV fields, the execution manifest and input hashes. They contain derived scenario aggregates, not raw market bars or credentials. Raw licensed inputs and full local execution files remain ignored. All five original input hashes and five original V36 output hashes were rechecked unchanged after execution.

| Digest object | SHA-256 |
|---|---|
| Frozen config, canonical JSON | `d482c9dfb3adfe961ae784ec892ba6cb0f17b24b6efbdddf5dfd5624ff4ada51` |
| Run manifest, literal formatted UTF-8 bytes | `9df68c296d6e443efff23261c05a63ebe9fb7c7c596967602b01b76a6816bd93` |
| Run manifest, canonical JSON | `c017ac204410fd2d3a48afbab3d4e408a313fdccd7f66988cc64227f56fc20ad` |
| v37a_attribution.csv, literal CSV bytes | `ec0766c281ecf8af85100a30ab9fee538afc47eef7dccbccfdab1c6f71507bd6` |
| v37a_grid.csv, literal CSV bytes | `e1872fdcabb061e3ad7cd165f2a1170b5a2aead6a1c607d5a1590234d4ae8bb8` |

Both executions produced byte-identical grid, attribution and manifest files. The runner stdout field `manifest_sha256` is the literal file digest returned by `write_immutable_json`, not the canonical JSON digest. The enclosing published summary is a separate document.

Reproduce with the pinned inputs and clean execution commit, using fresh output directories. Existing directories deliberately fail closed:

```powershell
uv run python -m scripts.run_d6_v36_study --data data/local_research/v36/reconciled_max --h10 data/local_research/fx/h10_dat00_th_20261025.txt --v35-grid data/local_research/v35/v35_grid.csv --out data/local_research/v37a/v36_regression_20261027
uv run python -m scripts.run_d6_v37a_study --out data/local_research/v37a/run1 --baseline-rerun data/local_research/v37a/v36_regression_20261027
uv run python -m scripts.run_d6_v37a_study --out data/local_research/v37a/run2 --baseline-rerun data/local_research/v37a/v36_regression_20261027
```

A rerun at another source commit must report that new runtime identity; numerical CSV digests should remain the comparison target. Public CI cannot reproduce ignored local inputs.

## Verification and limitations

- Targeted tests: 84 passed, including 39 new cases. Tests cover changing FX with exactly fixed THB, 12 USD/THB metamorphic schedule cases, constant-FX controls, fee insufficiency, rounding, delay/transit, malformed values, missing/stale/future FX, ordering and tampered cash partitions.
- Actual full V36 study rerun: all five CSV files byte-identical; 80 V35 comparison cells unchanged. Funding, broker cash and household attribution identities passed all 27 V37A cells.
- Prescribed full hermetic suite: 4,135 passed, 20 skipped, 56 deselected (110.73 seconds). This does not certify excluded native, sealed-data, dashboard or non-hermetic tiers.
- Strict MyPy: 652 source/test files clean; standalone study runner also clean. Unused optional-package configuration notes are compatibility/configuration debt.
- Twelve test warnings inspected: two Nautilus timestamp deprecations (dependency compatibility debt), ten existing tar extraction warnings (security/compatibility debt; unresolved). No warning was suppressed.
- Skips: two Windows symlink privileges, one B23 Windows enforcement status 0 (enforced-host behavior unverified), three optional skfolio/cvxpy dependencies, fourteen unavailable Bash-wrapper cases.

```powershell
uv run pytest -q --tb=line -rs -m "not non_hermetic and not native_mt5 and not sealed_data and not dashboard" --ignore=tests/unit/execution/mt5
uv run mypy src/ tests/
uv run mypy --explicit-package-bases scripts/run_d6_v37a_study.py
```

PIT and data admission remain unresolved. H.10 uses observation-date same-day/prior values, not verified publication-time availability or retail executable FX. Existing distribution payable-date imputations and source coverage limitations are inherited. BIL is absent from this grid; its unresolved cash-in-lieu guard is preserved. Existing V36 helpers and metric authorities are reused; passing accounting tests does not establish investment validity or tradeable profitability.

## Research handoff and next step

ChatGPT Research should complete the existing [Research handoff](PLUGIN_RESEARCH_HANDOFF_20261027.md): BND/VOO issuer corporate-action evidence and payable dates, point-in-time/release timestamps, licensing/redistribution rights, independently sourced broker/remittance eligibility and costs, and D7 literature. Return dated primary-source links, coverage, contradictions and unresolved gaps. Do not automatically ingest those outputs into D5 or retroactively tune this frozen study.

Next executable step: review the dedicated implementation PR and its exact-head CI. A separate owner merge decision is required. Rollback is a scoped revert of the funding extension and its runner; preserve historical data and evidence. D5=NOT_ADMITTED; LANE_A/B=UNISSUED; REAL_CAPITAL_AUTHORITY=USD0.00; NO_REAL_ORDERS=true. No provider refetch, orders, remittances, subscriptions, deployment or production activation occurred.

### Verification Ledger
- Implementation Status: COMPLETE (engineering scope).
- Contract Enforcement: STRICT FAIL-CLOSED.
- Mathematical Authority: CANONICAL SPEC for existing project accounting; HEURISTIC SPEC for retrospective cost/FX scenarios, not a new literature claim.
- Local Test Suite: VERIFIED (4,135 passed; exclusions above).
- Type Checker (MyPy): VERIFIED (652 source/test files and standalone runner).
- Remote CI Status: PR67 post-merge VERIFIED (40384005612); implementation PR PENDING at report creation, inspect its exact-head checks.
- Methodological Caveats: LOCAL_EXPLORATORY; retrospective FX, inherited data gaps and hypothetical costs; no D5 admission or capital authority.
