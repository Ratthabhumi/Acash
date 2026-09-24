# HYP_010 R2 Provider Qualification (TINY PROBE — PASS)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_010_R2_PROVIDER_AND_SPONSOR_AUTHORITY_QUALIFICATION]
[STARTING_SHA: 2653c2564e8ab0216183d9bd5773670bddb27020]
[CLASSIFICATION: PROVIDER_PROBE_PASS]
```

- **Manifest:** `docs/phase14/manifests/HYP_010_R2_PROVIDER_QUALIFICATION.json`
- **Runner:** `scripts/execute_hyp_010_r2_provider_probe.py --execute-network`
- **Local evidence (gitignored):** `data/hyp_010/probe_evidence.json`
  (`81fa66896ae62df3f0ce6aee4218d1cb91f1a517a4acf714addff8f4a8245737`)

## 1. Pre-Flight

- HEAD == origin/main == `2653c25…`, tree clean. R1 + post-R1 contract hashes
  recomputed MATCH. Credentials True/True (booleans only).

## 2. Probe Contract (Frozen, Verified Pre-Network)

SPY/VEU/AGG/BIL, 1Day, SIP, split+raw, sessions 2017-01-03..2017-01-06,
bounds `2017-01-03T00:00:00Z`..`2017-01-06T23:59:59.999999Z` via the audited
inclusive-date helper. (An initial script revision passed midnight end bounds
and returned 3 rows; root-caused as a script bound defect pre-seal — provider
compares bar timestamps against the end bound — corrected to end-of-day bounds
before any artifact seal. No sealed evidence derives from the buggy run.)

## 3. Observed Results (All Four Symbols)

- HTTP attempts: **8** (one per symbol/adjustment; no retries/pages needed).
- Per symbol/adjustment: **4 rows**, sessions exactly Jan 3/4/5/6, spill 0,
  duplicates 0, split/raw alignment PASS, OHLCV valid.
- Page SHAs pinned in the manifest (8 pages).

## 4. Governance

No broader dates/symbols/feeds. No HYP_003 runner. No performance computed.
M2/M3/quarantine/prospective/HYP_007 reads: 0.
