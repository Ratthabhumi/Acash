# HYP_011 R2 Provider Defect Adjudication

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_R2_PROVIDER_DEFECT_ADJUDICATION_AND_CLEAN_REQUALIFICATION]
[ORIGINAL_PROVIDER_QUALIFICATION: R2_PROVIDER_QUALIFICATION_INVALIDATED_BY_IMPLEMENTATION_DEFECT]
[SPONSOR_AUTHORITY: PRESERVED_VALID_SUBCOMPONENT]
[SCIENTIFIC_HYPOTHESIS_FALSIFIED: false]
[PERFORMANCE_OBSERVED: false]
```

- **Manifest:** `docs/phase14/manifests/HYP_011_R2_PROVIDER_DEFECT_ADJUDICATION.json`
- **Original authorization:** `AUTHORIZE_CORE_001_HYP_011_R2_PROVIDER_AND_SPONSOR_QUALIFICATION`
- **Original artifacts preserved:** `docs/phase14/HYP_011_R2_PROVIDER_QUALIFICATION.md`
  + manifest (commit `2c50cbb`, NOT overwritten or deleted)

## 1. Defect

- **Cause:** `INCLUSIVE_END_BOUND_SENT_AS_MIDNIGHT_EXCLUDED_FINAL_DAILY_BAR`.
  The first live probe revision sent provider end `2016-01-07T00:00:00Z`
  instead of end-of-day; Alpaca compares bar timestamps against the bound, so
  the final session bar was excluded.
- **First live result observed:** true — 3 rows per series (all symbols).
- **Defect discovered after live result observation:** true.
- **Corrected rerun under the same authorization:** true (returned 4/4 rows).
- The 3-row observation counts as an observed live qualification result even
  though no artifact was sealed from it. The same-authorization correction +
  rerun therefore violates the frozen implementation-defect rule.

## 2. Procedural Adjudication

- Original provider qualification: `R2_PROVIDER_QUALIFICATION_INVALIDATED_BY_IMPLEMENTATION_DEFECT`.
- Sponsor-authority qualification (SPY 36 / AGG 108 / ACWI 20, official
  provenance): `PRESERVED_VALID_SUBCOMPONENT` — unaffected by the provider
  timestamp bug; no refetch required.
- Scientific contract unchanged. HYP_011 intact, not falsified.
- Historical full acquisition: NOT executed. No third provider run under the
  old authorization was or will be performed.

## 3. Path Forward

One NEW clean provider requalification is authorized separately by the present
authorization. It must reproduce 4/4 rows per symbol/adjustment with the
corrected end-of-day bounds before any historical build.
