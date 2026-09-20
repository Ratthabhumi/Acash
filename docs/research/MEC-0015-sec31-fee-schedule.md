# MEC-0015 Historical SEC Section 31 Transaction Fee Schedule

## 1. Executive Summary & Legal Authority

Under Section 31 of the Securities Exchange Act of 1934, national securities exchanges and FINRA pay transaction fees to the SEC based on the aggregate dollar amount of covered sales of securities. While the statutory obligation rests on self-regulatory organizations (SROs), member broker-dealers pass these transaction costs through to the selling client on covered equity sales.

In accordance with ACASH quantitative research standards:
- **Authority Distinction:**
  - `SEC31_RATE_AUTHORITY = OFFICIAL_SEC_FEE_RATE_ADVISORY` (Sovereign regulatory rate schedule published pursuant to Section 31).
  - `SEC31_CUSTOMER_PASS_THROUGH = ACASH_CONSERVATIVE_OPERATIONALIZATION` (Broker pass-through practice).
  - The SEC does not directly impose a customer fee nor prescribe customer-level rounding; historical SEC rulemaking (e.g. Release No. 34-49928) notes that broker-dealers typically round customer pass-through charges up to the next whole cent.
- **Rounding Policy:**
  - `SEC31_ROUNDING = ROUND_CEILING_TO_CENT`.
  - ACASH operationalizes customer pass-through using ceiling rounding to the nearest cent (`ROUND_CEILING`). This conservative model ensures friction is never underestimated and naturally produces `$0.01` for any positive sub-cent fee without an artificial special case.
  - Rounding itself is classified as an **ACASH conservative operationalization**, not an SEC statutory mandate.
- **No Retroactive Contemporary Rates:** Historical backtests must NEVER apply modern rates (e.g. FY2026 $20.60/million) retroactively across 2007–2024.
- **Fail-Closed Contract:** Any covered trade date outside the authoritative schedule raises `DataContractError`.
- **Side Discipline:** Section 31 fees apply **strictly to covered SELL transactions**. Buy transactions incur exactly `$0.00`.
- **Pure Arithmetic:** Fee calculations use `Decimal` arithmetic exclusively; floating-point representation is prohibited.

---

## 2. Historical Effective Schedule (2007-05-01 to 2024-04-30)

The canonical Section 31 schedule comprises exactly **20 effective schedule segments** covering the MEC-0015 M1 replication window:

| Seg | Effective Start | Effective End | Rate ($ / $1M) | Rate ($ / $1) | Official SEC Source | SEC Release / Reference |
|---|---|---|---|---|---|---|
| 1 | 2007-03-17 | 2008-01-24 | $15.30 | 0.00001530 | SEC Fee Rate Advisory #4 for FY 2007 | Rel. No. 34-55365 |
| 2 | 2008-01-25 | 2008-03-31 | $11.00 | 0.00001100 | SEC Fee Rate Advisory #3 for FY 2008 | Rel. No. 34-57142 |
| 3 | 2008-04-01 | 2009-04-09 | $5.60 | 0.00000560 | SEC Fee Rate Advisory #4 for FY 2008 (Mid-Year) | Rel. No. 34-57419 |
| 4 | 2009-04-10 | 2010-01-14 | $25.70 | 0.00002570 | SEC Fee Rate Advisory #4 for FY 2009 (Mid-Year) | Rel. No. 34-59543 |
| 5 | 2010-01-15 | 2010-03-31 | $12.70 | 0.00001270 | SEC Fee Rate Advisory #2 for FY 2010 | Rel. No. 34-61268 |
| 6 | 2010-04-01 | 2011-01-20 | $16.90 | 0.00001690 | SEC Fee Rate Advisory #4 for FY 2010 (Mid-Year) | Rel. No. 34-61614 |
| 7 | 2011-01-21 | 2012-02-20 | $19.20 | 0.00001920 | SEC Fee Rate Advisory #2 for FY 2011 | Rel. No. 34-63595 |
| 8 | 2012-02-21 | 2012-03-31 | $18.00 | 0.00001800 | SEC Fee Rate Advisory #5 for FY 2012 | Rel. No. 34-66205 |
| 9 | 2012-04-01 | 2013-05-24 | $22.40 | 0.00002240 | SEC Fee Rate Advisory #6 for FY 2012 (Mid-Year) | Rel. No. 34-66490 |
| 10 | 2013-05-25 | 2014-03-17 | $17.40 | 0.00001740 | SEC Fee Rate Advisory #3 for FY 2013 | Rel. No. 34-69446 |
| 11 | 2014-03-18 | 2015-02-13 | $22.10 | 0.00002210 | SEC Fee Rate Advisory #2 for FY 2014 | Rel. No. 34-71556 |
| 12 | 2015-02-14 | 2016-02-15 | $18.40 | 0.00001840 | SEC Fee Rate Advisory #3 for FY 2015 | Rel. No. 34-74070 |
| 13 | 2016-02-16 | 2017-07-03 | $21.80 | 0.00002180 | SEC Fee Rate Advisory #3 for FY 2016 | Rel. No. 34-76852 |
| 14 | 2017-07-04 | 2018-05-21 | $23.10 | 0.00002310 | SEC Fee Rate Advisory #3 for FY 2017 | Rel. No. 34-80830 |
| 15 | 2018-05-22 | 2019-04-15 | $13.00 | 0.00001300 | SEC Fee Rate Advisory #2 for FY 2018 | Rel. No. 34-83083 |
| 16 | 2019-04-16 | 2020-02-17 | $20.70 | 0.00002070 | SEC Fee Rate Advisory #2 for FY 2019 | Rel. No. 34-85377 |
| 17 | 2020-02-18 | 2021-02-24 | $22.10 | 0.00002210 | SEC Fee Rate Advisory #2 for FY 2020 | Rel. No. 34-88062 |
| 18 | 2021-02-25 | 2022-05-13 | $5.10 | 0.00000510 | SEC Fee Rate Advisory #2 for FY 2021 | Rel. No. 34-90924 |
| 19 | 2022-05-14 | 2023-02-26 | $22.90 | 0.00002290 | SEC Fee Rate Advisory #2 for FY 2022 | Rel. No. 34-94420 |
| 20 | 2023-02-27 | 2024-05-21 | $8.00 | 0.00000800 | SEC Fee Rate Advisory #2 for FY 2023 | Rel. No. 34-96791 |

---

## 3. Mathematical Formula & Implementation Contract

For any executed order on trade date $t$:
$$\text{Fee}_{\text{SEC31}}(t) = \begin{cases} 0.00 & \text{if BUY} \\ \text{ceil}_{\text{cents}}\left(\text{Principal} \times r(t)\right) & \text{if SELL and Principal} > 0 \\ 0.00 & \text{if SELL and Principal} = 0 \end{cases}$$

Where:
- $\text{Principal} = \text{shares} \times \text{fill\_price}$
- $r(t)$ is the exact statutory rate per dollar from the sovereign schedule above.
- $\text{ceil}_{\text{cents}}$ rounds up to the next whole cent (`ROUND_CEILING_TO_CENT`).
- Machine-readable definition: [MEC-0015-sec31-fee-schedule.json](./manifests/MEC-0015-sec31-fee-schedule.json).
- Executable Python function: `acash.execution.regulatory_fees.compute_sec31_fee`.
