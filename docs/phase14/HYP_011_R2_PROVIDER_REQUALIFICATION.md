# HYP_011 R2 Provider Clean Requalification (PASS)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_R2_PROVIDER_DEFECT_ADJUDICATION_AND_CLEAN_REQUALIFICATION]
[CLASSIFICATION: PROVIDER_REQUALIFICATION_PASS]
[PRIOR_INVALIDATED_RUN: preserved at 2c50cbb, NOT overwritten]
```

- **Manifest:** `docs/phase14/manifests/HYP_011_R2_PROVIDER_REQUALIFICATION.json`
- **Runner:** `scripts/execute_hyp_011_r2_provider_probe.py --execute-network`
  (verified pre-network: inclusive end-of-day bounds via the audited helper)
- **Local evidence (gitignored):** `data/hyp_011/probe_evidence.json`
  (`65a51047f59ad242739067057756f03dceb290dfe002b7e797e7ab4dddfe8298` —
  byte-identical to the corrected prior run, as expected for deterministic
  identical requests)

## 1. Observed Results (All Three Symbols)

- HTTP attempts: **6** (one per symbol/adjustment; no retries/pages needed).
- Per symbol/adjustment: **4 rows**, sessions exactly Jan 4/5/6/7 2016, spill 0,
  duplicates 0, split/raw alignment PASS, OHLCV valid.
- Page SHAs pinned in the manifest (6 pages).

## 2. Defect Rule (§8)

No new implementation defect discovered after this clean result. No third
provider qualification under this authorization.

## 3. Governance

No broader dates/symbols/feeds. No performance computed. M2/M3/quarantine/
prospective/HYP_007 reads: 0. Paper NOT_AUTHORIZED, live LOCKED, capital
$0.00, NO_REAL_ORDERS=true.
