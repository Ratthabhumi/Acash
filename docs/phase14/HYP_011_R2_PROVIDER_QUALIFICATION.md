# HYP_011 R2 Provider Qualification (TINY PROBE — PASS)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_R2_PROVIDER_AND_SPONSOR_QUALIFICATION]
[STARTING_SHA: 4bedcc6cbb3b6136442e9ed66ca4e5e83d563c31]
[CLASSIFICATION: PROVIDER_PROBE_PASS]
```

- **Manifest:** `docs/phase14/manifests/HYP_011_R2_PROVIDER_QUALIFICATION.json`
- **Runner:** `scripts/execute_hyp_011_r2_provider_probe.py --execute-network`
- **Local evidence (gitignored):** `data/hyp_011/probe_evidence.json`
  (`65a51047f59ad242739067057756f03dceb290dfe002b7e797e7ab4dddfe8298`)

## 1. Pre-Flight

HEAD == origin/main == `4bedcc6…`, tree clean. R1 + post-R1 contract hashes
recomputed MATCH. Credentials True/True (booleans only).

## 2. Probe Contract (Frozen, Verified Pre-Network)

ACWI/AGG/SPY, 1Day, SIP, split+raw, sessions 2016-01-04..2016-01-07
(Mon–Thu, calendar-verified), bounds via the audited inclusive-date helper
(`2016-01-04T00:00:00Z`..`2016-01-07T23:59:59.999999Z`).

## 3. Observed Results (All Three Symbols)

- HTTP attempts: **6** (one per symbol/adjustment; no retries/pages needed).
- Per symbol/adjustment: **4 rows**, sessions exactly Jan 4/5/6/7 2016, spill 0,
  duplicates 0, split/raw alignment PASS, OHLCV valid.
- Page SHAs pinned in the manifest (6 pages; split==raw bytes per symbol —
  expected with no applicable splits in-window).

## 4. Governance

No broader dates/symbols/feeds. No HYP_003 runner. No performance computed.
M2/M3/quarantine/prospective/HYP_007 reads: 0.
