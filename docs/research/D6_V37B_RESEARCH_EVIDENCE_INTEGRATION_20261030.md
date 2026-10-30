# D6 V37B — Research Evidence Integration, Corporate-Action Reconciliation & Scientific Readiness (2026-10-30)

**Governance Label:** `LOCAL_EXPLORATORY` · **Lineage Authority:** V37B Read-Only Evidence Overlay  
**Legal & Fiduciary Boundaries:** Not investment, legal, or tax advice. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`, `LANE_A/B = UNISSUED`.  
**D5 Real Admission:** `NOT_ADMITTED` (0/40 symbol-year cells).  
**Execution Authority:** Owner Execution Directive for ACASH V37B.  
**Machine-Readable Overlay Artifacts:**
- Overlay JSON: [v37b_evidence_overlay_20261030.json](evidence/v37b_evidence_overlay_20261030.json) (SHA256: `7500046c78c057f896d4d4457c2a129dc50d8eb4bcb83ae95b04697243c7ec8f`)
- Overlay CSV: [v37b_evidence_overlay_20261030.csv](evidence/v37b_evidence_overlay_20261030.csv)
- Proposed Payable Deltas: [v37b_proposed_payable_deltas_20261030.csv](evidence/v37b_proposed_payable_deltas_20261030.csv) (0 unverified modifications proposed)

---

## 1. Executive Summary & Verification Ledger

V37B integrates the completed 27–30 October 2026 external research sprint into the ACASH quantitative engine through an independent, deterministic, read-only **Evidence Overlay**. It establishes field-by-field provenance across primary SEC filings, Vanguard annual reports, Form 1042-S foreign tax supplements, and OCC information memos without modifying the frozen canonical D6 accounting datasets, NAV curves, or cash ledgers.

### Final Verification Ledger

```markdown
### Verification Ledger
- Implementation Status: COMPLETE
- Contract Enforcement: STRICT FAIL-CLOSED
- Mathematical Authority: CANONICAL SPEC
- Local Test Suite: VERIFIED (18 passed in test_d6_v37b_evidence_overlay.py; 101 passed across D6 regression suites)
- Type Checker (MyPy): VERIFIED (330 source files clean)
- Remote CI Status: PENDING (to be verified upon PR opening)
- Methodological Caveats:
  1. The Evidence Overlay is strictly read-only and does NOT feed the backtest execution engine.
  2. Retrospective financial statements corroborate economic event amounts, but do not provide contemporaneous Point-In-Time (PIT) timestamps.
  3. Vanguard website terms prohibit automated bulk extraction or public dataset redistribution without written license.
  4. QSG is a tax classification for withholding relief under IRC §871(k), not an additional cash entitlement.
  5. Absence from a QSG list does NOT prove zero capital gains or zero cash distributions.
  6. Imputed payable dates (63 rows) remain unpromoted; 0/63 are altered in canonical data.
```

---

## 2. Deliverable A: V37B Source-Backed Evidence Index

| Source ID | Document Title & Description | Exact Primary URL / Access Point | Historical Vintage / Period | Retained Data Rights Status | Verified Role |
|---|---|---|---|---|---|
| `SEC-0000932471-19-006953` | Vanguard Bond Index Funds SEC Form 485BPOS | [SEC EDGAR 485BPOS](https://www.sec.gov/Archives/edgar/data/794105/000093247119006953/bondindex485bfinal.htm) | 2016–2019 Financial Highlights | `RIGHTS_PERMITTED` (US Public Record) | Corroborates annual BND per-share capital gains for 2016 ($0.036/0.0357), 2017 ($0.037), 2018 ($0.019/0.01916), 2019 ($0.00). |
| `SEC-0000794105-26-000106` | Vanguard Bond Index Funds Post-Effective Filing | [SEC EDGAR 2026 Filing](https://www.sec.gov/Archives/edgar/data/794105/000079410526000106/f45031d1.htm) | 2020–2025 Financial Highlights | `RIGHTS_PERMITTED` (US Public Record) | Corroborates annual BND capital gains: 2020 ($0.1436), 2021 ($0.1834), 2022 ($0.0593), 2023 ($0.00), 2024 ($0.00), 2025 ($0.00). |
| `VANGUARD-AR-Q840` | Vanguard Bond Index Funds Annual Report | [Vanguard fund-docs q840.pdf](https://fund-docs.vanguard.com/q840.pdf) | Period ended Dec 31 | `RIGHTS_PERMITTED` (Public Regulatory Shareholder Report) | Corroborates financial reporting separation of net investment income vs realized capital gains. |
| `OCC-48045` | OCC Information Memo #48045 | [OCC InfoMemo 48045](https://infomemo.theocc.com/infomemos?number=48045) | Ex-date 2020-12-23 | `RIGHTS_PERMITTED` (Public Clearing Memo) | Corroborates BND capital gain split: LTCG $0.1064 + STCG $0.0372 = $0.1436, payable 2020-12-29. |
| `OCC-49819` | MIAX Alert / OCC Information Memo #49819 | [MIAX BND Alert](https://www.miaxglobal.com/sites/default/files/alert-files/BND_Distribution_49819.pdf) | Ex-date 2021-12-23 | `RIGHTS_PERMITTED` (Public Clearing Notice) | Corroborates BND LTCG $0.13, payable 2021-12-29. |
| `VANGUARD-1042S-2020` | Vanguard Form 1042-S Foreign Tax Supplement 2020 | [1042sb-022021.pdf](https://investor.vanguard.com/content/dam/retail/us/en/pdfs/taxes/1042sb-022021.pdf) | Tax Year 2020 (Pub Feb 2021) | `RIGHTS_PERMITTED` (Public Tax Reference) | Corroborates BND presence in QSG fund schedule for 2020 (qualifies 2020-12-23 STCG $0.0372). |
| `VANGUARD-1042S-2021` | Vanguard Form 1042-S Foreign Tax Supplement 2021 | [1042sb-022022.pdf](https://investor.vanguard.com/content/dam/retail/us/en/pdfs/taxes/1042sb-022022.pdf) | Tax Year 2021 (Pub Feb 2022) | `RIGHTS_PERMITTED` (Public Tax Reference) | Corroborates BND presence in QSG fund schedule for 2021 (qualifies 2021-04-01 STCG $0.0034). |
| `VANGUARD-1042S-2022` | Vanguard Form 1042-S Foreign Tax Supplement 2022 | [1042sb-022023.pdf](https://investor.vanguard.com/content/dam/retail/us/en/pdfs/taxes/1042sb-022023.pdf) | Tax Year 2022 (Pub Feb 2023) | `RIGHTS_PERMITTED` (Public Tax Reference) | Confirms BND absence from QSG list. (Consistent: 2022 distribution was 100% Long-Term Capital Gain $0.0593, which is not QSG). |
| `VANGUARD-1042S-2023` | Vanguard Form 1042-S Foreign Tax Supplement 2023 | [1042sb-022024.pdf](https://investor.vanguard.com/content/dam/retail/us/en/pdfs/taxes/1042sb-022024.pdf) | Tax Year 2023 (Pub Feb 2024) | `RIGHTS_PERMITTED` (Public Tax Reference) | Confirms BND absence from QSG list (no capital gains paid). |
| `VANGUARD-1042S-2024` | Vanguard Form 1042-S Foreign Tax Supplement 2024 | [1042sb-022025.pdf](https://investor.vanguard.com/content/dam/retail/us/en/pdfs/taxes/1042sb-022025.pdf) | Tax Year 2024 (Pub Feb 2025) | `RIGHTS_PERMITTED` (Public Tax Reference) | Confirms BND absence from QSG list (no capital gains paid). |
| `VANGUARD-WEB-BND` | Vanguard BND Product Distribution History Page | [Advisors BND Page](https://advisors.vanguard.com/investments/products/bnd/vanguard-total-bond-market-etf) | 2016–2026 Rolling Display | `RIGHTS_RESTRICTED` (Terms Prohibit Automated Extraction) | Source identified for event-level BND ordinary distributions; bulk export restricted by terms. |
| `VANGUARD-WEB-VOO` | Vanguard VOO Product Distribution History Page | [Advisors VOO Page](https://advisors.vanguard.com/investments/products/voo/vanguard-sp-500-etf) | 2016–2026 Rolling Display | `RIGHTS_RESTRICTED` (Terms Prohibit Automated Extraction) | Source identified for event-level VOO ordinary distributions; bulk export restricted by terms. |

---

## 3. Deliverable B: Annual BND Capital-Gain Reconciliation (2016–2025)

The table below reconciles official Vanguard/SEC annual reported capital gains per share against event-level records in the ACASH dataset:

| Calendar Year | SEC/Vanguard Annual Per-Share (USD) | Event-Level Component Sum (USD) | Delta (USD) | Reconciled Ex-Date(s) | Evidence Class | Audit Status & Lineage |
|---|---:|---:|---:|---|---|---|
| **2016** | 0.036 (0.0357) | 0.0357 | 0.0000 | 2016-12-22 | `ISSUER_ANNUAL_TOTAL_CORROBORATED` | Corroborates provider row 2016-12-22 ($0.0357). Provider mislabeled event as `DIVIDEND_CASH`; SEC highlights confirm capital gain. |
| **2017** | 0.037 | 0.0370 | 0.0000 | 2017-12-26 | `ISSUER_ANNUAL_TOTAL_CORROBORATED` | Corroborates provider row 2017-12-26 ($0.037). Provider mislabeled event as `DIVIDEND_CASH`; SEC highlights confirm capital gain. |
| **2018** | 0.019 (0.01916) | 0.01916 | 0.0000 | 2018-04-02 | `ISSUER_ANNUAL_TOTAL_CORROBORATED` | Corroborates provider row 2018-04-02 ($0.01916). Provider mislabeled event as `DIVIDEND_CASH`; SEC highlights confirm capital gain. |
| **2019** | 0.000 | 0.0000 | 0.0000 | None | `ISSUER_ANNUAL_TOTAL_CORROBORATED` | No capital gains shown in SEC highlights; matches provider having 0 capital gain rows in 2019. |
| **2020** | 0.143 (0.1436) | 0.1436 | 0.0000 | 2020-12-23 | `OCC_EVENT_CORROBORATED` | 2020-12-23 event split into LTCG $0.1064 + STCG $0.0372 = $0.1436. Corroborated by OCC InfoMemo 48045 and SEC 2026 highlights. |
| **2021** | 0.183 (0.1834) | 0.1834 | 0.0000 | 2021-04-01, 2021-12-23 | `OCC_EVENT_CORROBORATED` | Sum of 2021-04-01 ($0.0534 = $0.0034 STCG + $0.05 LTCG) and 2021-12-23 ($0.13 LTCG) = $0.1834. Corroborated by OCC 49819 and SEC highlights. |
| **2022** | 0.059 (0.0593) | 0.0593 | 0.0000 | 2022-04-01 | `ISSUER_ANNUAL_TOTAL_CORROBORATED` | 2022-04-01 LTCG $0.0593 matches SEC financial highlights. |
| **2023** | 0.000 | 0.0000 | 0.0000 | None | `ISSUER_ANNUAL_TOTAL_CORROBORATED` | Corroborates 0 capital gain events in 2023. |
| **2024** | 0.000 | 0.0000 | 0.0000 | None | `ISSUER_ANNUAL_TOTAL_CORROBORATED` | Corroborates 0 capital gain events in 2024. |
| **2025** | 0.000 | 0.0000 | 0.0000 | None | `ISSUER_ANNUAL_TOTAL_CORROBORATED` | Corroborates 0 capital gain events in 2025. |

---

## 4. Deliverable C: Event & Component Discrepancy Report

Critical candidate dates examined:

1. **2016-12-22 (BND):**
   - *Provider Row:* Gross $0.0357, labeled `DIVIDEND_CASH`, payable date imputed as 2016-12-28 (ex+6d).
   - *Issuer Corroboration:* SEC Form 485BPOS Financial Highlights reports $0.036 net realized capital gains. The regular monthly dividend was on 2016-12-01 ($0.160291).
   - *Discrepancy:* Alpaca provider labeled the capital gain distribution as `DIVIDEND_CASH`.
   - *Cash Impact:* **$0.00**. The cash was received by the broker. Reclassification from dividend to capital gain changes tax/reporting classification, but creates NO extra cash.
2. **2017-12-26 (BND):**
   - *Provider Row:* Gross $0.037, labeled `DIVIDEND_CASH`, payable date imputed as 2018-01-01 (ex+6d).
   - *Issuer Corroboration:* SEC Form 485BPOS reports $0.037 net realized capital gains. Regular monthly dividend was on 2017-12-01 ($0.168434).
   - *Discrepancy:* Provider mislabeled as `DIVIDEND_CASH`.
   - *Cash Impact:* **$0.00**. Cash received is identical.
3. **2018-04-02 (BND):**
   - *Provider Row:* Gross $0.01916, labeled `DIVIDEND_CASH`, payable date imputed as 2018-04-08 (ex+6d).
   - *Issuer Corroboration:* SEC Form 485BPOS reports $0.019 net realized capital gains.
   - *Discrepancy:* Provider mislabeled as `DIVIDEND_CASH`.
   - *Cash Impact:* **$0.00**.
4. **2020-12-23 (BND):**
   - *Provider Rows:* Provider included ordinary dividend $0.1471819, plus a capital gain row of $0.1436 split in V34 into $0.1064 LTCG and $0.0372 STCG based on OCC Memo 48045.
   - *Issuer Corroboration:* Matches SEC 2026 filing ($0.1436 capital gains).
   - *Cash Impact:* **$0.00**.
5. **2021-04-01 & 2021-12-23 (BND):**
   - *Provider Rows:* 2021-04-01 ordinary dividend $0.139053 + capital gain $0.0534 ($0.0034 STCG + $0.05 LTCG); 2021-12-23 ordinary dividend $0.140851 + LTCG $0.13.
   - *Issuer Corroboration:* Total 2021 capital gains = $0.0534 + $0.13 = $0.1834, matching SEC financial highlights.
   - *Cash Impact:* **$0.00**.
6. **2022-04-01 (BND):**
   - *Provider Rows:* Ordinary dividend $0.138738 + LTCG $0.0593.
   - *Issuer Corroboration:* Matches SEC financial highlights ($0.0593).
   - *Cash Impact:* **$0.00**.

---

## 5. Deliverable D: BND/VOO Payable-Date Status Matrix (63 Imputed Rows)

V36 recorded 63 distributions where the provider omitted `payable_date`, resulting in the `IMPUTED_EX_PLUS_6D_MAX_OBSERVED_LAG` policy:
- **BND:** 47 rows (all occurring in 2016, 2017, 2018, 2019)
- **VOO:** 16 rows (all occurring in 2016, 2017, 2018, 2019)

### Status Matrix Summary

| Category | Initial Imputed Count | Confidently Matched | Conflicted | Ambiguous | Unresolved (Gap) | Delta Proposed |
|---|---:|---:|---:|---:|---:|---:|
| **BND (2016–2019)** | 47 | 0 | 0 | 0 | 47 | 0 |
| **VOO (2016–2019)** | 16 | 0 | 0 | 0 | 16 | 0 |
| **Total** | **63** | **0** | **0** | **0** | **63** | **0** |

### Rigorous Audit Finding
1. **Event Identity vs Payable Date:** While SEC Form 485BPOS and annual reports corroborate the *existence and amount* of the capital gain distributions and fiscal annual totals, SEC Financial Highlights do NOT report individual ex-date/payable-date payment schedules for monthly ordinary dividends.
2. **Data Rights Boundary:** Vanguard's website terms (`investor.vanguard.com/terms-conditions`) restrict automated scraping and non-permitted dataset extraction. Because no licensed, authenticated bulk export file has been deposited in the repository, claiming that any of the 63 payable dates have been verified by an official file would violate AGENTS.md Principle 1 ("Zero Unverified Claims").
3. **Immateriality Established in V35:** Sensitivity tests in V35 demonstrated that the difference between minimum lag (0 days), median lag (3 days), and maximum lag (6 days) moved portfolio NAV by $\le 0.0001\%$.
4. **Action Taken:** All 63 rows remain classified as `UNRESOLVED` (`SOURCE_NOT_AVAILABLE`). The proposed delta file [v37b_proposed_payable_deltas_20261030.csv](evidence/v37b_proposed_payable_deltas_20261030.csv) is published with zero unverified rows, ensuring no unratified modifications occur.

---

## 6. Deliverable E: QSG Classification Evidence Matrix

Vanguard Form 1042-S Foreign Tax Supplements (published each February for the preceding tax year) list funds paying Qualified Short-Term Capital Gain (QSG) under IRC §871(k):

| Tax Year | Supplement Document | BND on QSG List? | Verified Financial Capital Gains | Interpretation & Tax Treatment |
|---|---|---|---|---|
| **2020** | `1042sb-022021.pdf` | **YES** | $0.1436 ($0.0372 STCG + $0.1064 LTCG) | Corroborates QSG status for the 2020-12-23 STCG ($0.0372). Eligible for US withholding tax exemption for qualified foreign investors. |
| **2021** | `1042sb-022022.pdf` | **YES** | $0.1834 ($0.0034 STCG + $0.1800 LTCG) | Corroborates QSG status for the 2021-04-01 STCG ($0.0034). Eligible for US withholding tax exemption. |
| **2022** | `1042sb-022023.pdf` | **NO** | $0.0593 (100% LTCG) | **Absence is consistent:** The 2022 gain was 100% Long-Term Capital Gain ($0.0593 LTCG on 2022-04-01). LTCGs are not short-term gains, so they do not appear on QSG schedules. Absence does NOT mean zero cash or zero capital gain! |
| **2023** | `1042sb-022024.pdf` | **NO** | $0.0000 | Consistent: No capital gains distributed in 2023. |
| **2024** | `1042sb-022025.pdf` | **NO** | $0.0000 | Consistent: No capital gains distributed in 2024. |

### Key Tax Architecture Principles
- **No Cash Creation:** Qualified Short-Term Gain (QSG) and Interest-Related Dividends (IRD / QII) are tax classifications for withholding tax exemptions; they do NOT generate additional cash to shareholders.
- **Withholding Sensitivity Bounds:** In V36, withholding sensitivity was tested under W0 (0%), W15 (15%), W30 (30%), and WT_LOW (where BIL/BND are partially exempt). The QSG evidence confirms that BND STCG components enjoyed withholding relief, supporting the WT_LOW scenario as a plausible theoretical bound.

---

## 7. Deliverable F: Data Rights, Point-In-Time (PIT) & Lineage Analysis

| Evaluation Dimension | Status | Governing Invariant & Rationale |
|---|---|---|
| **A. Official-Source Authenticity** | `VERIFIED` | SEC EDGAR Form 485BPOS, Vanguard fund reports, Form 1042-S supplements, and OCC memos are authenticated official primary sources. |
| **B. Retrospective Economic Correctness** | `VERIFIED` | Cash amounts received by shareholders match SEC financial highlights and clearing memos across all audited years ($0.00 discrepancy). |
| **C. Point-in-Time (PIT) Availability** | `RETROSPECTIVE_ONLY` | SEC filings and annual reports were published months after the historical ex-dates (e.g. 2016 financial highlights published in 2019/2020 filings). They provide retrospective corroboration, NOT contemporaneous PIT evidence. |
| **D. Private Retention Rights** | `PERMITTED` | Fair use and personal research retention for quantitative analysis without public distribution of third-party raw copyrighted text. |
| **E. Automated Retrieval Rights** | `RESTRICTED` | Vanguard website terms prohibit automated scraping or bulk download scripts without written authorization. |
| **F. Public Redistribution Rights** | `FORBIDDEN` | Third-party full distribution history archives cannot be redistributed in public git repositories. Only concise authored indices and hashes are committed. |
| **G. D5 Empirical Admission** | `BLOCKED` | D5 admission requires contemporaneous PIT proof, clean redistributable licensing, and sealed admission authority. Current status remains `SCOPE_NOT_ADMITTED`. |

---

## 8. Deliverable G: Targeted Tests & Invariant Verification

New unit and adversarial tests implemented in [test_d6_v37b_evidence_overlay.py](../tests/unit/research/test_d6_v37b_evidence_overlay.py):
- **18/18 Targeted Tests Passed:**
  1. Aggregate distribution matched to multiple documented components.
  2. Component already included in aggregate; zero double counting.
  3. Identical cash amounts with distinct CUSIPs strictly separated.
  4. Same ex-date with multiple economic components.
  5. Same payable date across multiple events.
  6. Financial statement rounding differences verified.
  7. Tax year different from calendar ex-date year.
  8. Tax designation without additional cash.
  9. Ambiguous matching rejection.
  10. Conflicting payable date detection.
  11. Missing timestamp fails closed.
  12. Unsupported evidence class fails closed (`OVERLAY_UNKNOWN_EVIDENCE_CLASS`).
  13. Unknown source rights fails closed (`OVERLAY_UNKNOWN_RIGHTS_STATUS`).
  14. Deterministic output across reordered rows.
  15. Tampered identifier rejection.
  16. Invalid date, negative amount, and duplicate ID rejection.
  17. Canonical frozen D6 input hashes unchanged.
  18. Full overlay reconciliation of 78 records.

### Frozen Input Data Hashes (Unchanged)
- `data/local_research/v36/reconciled_max/bars_raw.csv`: `b86f73a69eff2cb9a81131dfa8b4b6d4cf32979be0a2ffcb8cd5e02058b0ff91` (MATCH)
- `data/local_research/v36/reconciled_max/distributions.csv`: `9885fcb8258dcd6dc8f944776834d49f3c6f914d260e5bdc7cd29ae1a1726ca0` (MATCH)
- `data/local_research/v36/reconciled_max/splits.csv`: `c9b9d95cedd8479118b2a0489f665d81f035d790739a56dc7f844fca5001588d` (MATCH)

---

## 9. Deliverable H: D7 Scientific Readiness Decision

### Audit of D7 Capabilities & Research Archive

1. **Statistical Validation Capabilities Already Implemented:**
   - Deflated Sharpe Ratio (DSR) engine (`acash.validation.deflated_sharpe`)
   - Bailey-Lopez de Prado CSCV / Probability of Backtest Overfitting (PBO) (`acash.validation.multiple_testing`)
   - Combinatorial Purged Cross-Validation (CPCV) with embargo (`acash.validation.cpcv`)
   - Model Selection Tournament with deterministic tie-breaking (`acash.portfolio.tournament`)
   - Newey-West / HAC variance estimation (`acash.validation.hac`)
2. **Corporate-Action Uncertainties Affecting Historical Strategy Research:**
   - Imputed payable date lag (0 to 6 sessions) has an immaterial impact on historical NAV ($\le 0.0001\%$).
   - BND capital-gain component mislabeling in 2016–2018 does NOT change the total cash received by the portfolio ($0.0357 in 2016, $0.037 in 2017, $0.01916 in 2018).
   - Therefore, corporate-action timing uncertainties do NOT materially distort baseline strategy comparisons.
3. **Uncertainties Affecting Only Tax or Reporting Classification:**
   - QSG status, IRD/QII status, and LTCG/STCG splits affect only withholding tax scenarios (e.g. W15 vs WT_LOW) and Thai tax treatment under Por. 161/162/2566. They do not alter gross broker cash receipts.
4. **Data-Rights & PIT Gaps Blocking Formal D5 Admission:**
   - Formal D5 qualification requires commercially licensed redistributable market data and verified contemporaneous PIT publication timestamps. Public SEC filings provide retrospective verification, not PIT feeds.
5. **Exploratory Analysis That Can Continue Safely:**
   - Retrospective funding cadence (F0 vs F1 vs F2 vs F3), fixed vs tiered commission modeling, and whole-share cash drag can continue under `LOCAL_EXPLORATORY`.
6. **Highest Economic Value & Lowest Cost Next Research Question:**
   - **Thai Remittance Cadence & Friction Optimization:** At small portfolio sizes ($50 to $250/month), funding cadence and bank wire frictions swing annualized returns by **300 to 500 basis points**, completely dominating multi-asset selection and minor dividend timing differences.
7. **Owner Decision Required:**
   - Yes. Transitioning from exploratory research to formal strategy pre-registration (D7) or live data acquisition (D3) requires explicit owner authority.

### Prioritized Recommendation: `PROCEED_EXPLORATORY`

- **Scope of Recommendation:**
  Proceed with exploratory research on funding friction mitigation, domestic FCD / licensed money transfer operator channels, and cash-conserving rebalancing rules under `LOCAL_EXPLORATORY`.
- **Governance Gate:**
  `HOLD_FOR_DATA_RIGHTS` for any formal D5 qualification or hypothesis pre-registration. No live capital, no paper trading, no new HYP IDs, and no software purchases (e.g. ATrain or GEX feeds) authorized.
