# MEC-0015 Historical FINRA Trading Activity Fee (TAF) Schedule

## 1. Executive Summary & Legal Authority

The Trading Activity Fee (TAF) is assessed by FINRA under Section 1 of Schedule A to the FINRA By-Laws to recover the costs of supervising and regulating member firms. Member broker-dealers pass this regulatory transaction fee through to customers on covered equity sales.

In accordance with ACASH quantitative research standards:
- **No Retroactive Contemporary Rates:** Historical backtests must NEVER apply modern rates (e.g. 2026 $0.000195/share, cap $9.79) retroactively across 2007–2024.
- **Fail-Closed Contract:** Any covered trade date outside the authoritative schedule raises `DataContractError`.
- **Side Discipline:** TAF applies **strictly to covered SELL transactions**. Buy transactions incur exactly `$0.00`.
- **Per-Trade Maximum Cap:** FINRA specifies a strict per-trade maximum fee cap for each historical period.
- **Statutory Rounding Rule:** Section 1(b)(1) of Schedule A to the FINRA By-Laws explicitly mandates: *"Each member shall round the fee up to the nearest cent."* Hence `ROUND_CEILING` to cents is statutory and strictly preserved.
- **Low-Price Exemption:** Under FINRA Schedule A Section 1(b)(2), transactions in covered equity securities where the execution price per share is less than the per-share TAF rate are exempt from the fee. Because SPY trades at hundreds of dollars per share (orders of magnitude above the sub-cent TAF rate), this MEC-0015 SPY-scoped function intentionally omits an execution price parameter. It is documented as a SPY-specific operationalization, not a generic statutory penny-stock engine.
- **Pure Arithmetic:** Calculations use pure `Decimal` arithmetic exclusively.

---

## 2. Historical Effective Schedule (2007-05-01 to 2024-04-30)

Under FINRA Rule Filing **SR-FINRA-2020-032** (approved by the SEC in Release No. 34-90176), FINRA adopted a phased implementation plan for TAF rate adjustments across 2022–2024:
- Implementation commenced on **January 1, 2022** (Phase 1).
- Staged increases took effect on **January 1, 2023** (Phase 2).
- Full implementation took effect on **January 1, 2024** (Phase 3).

The complete authoritative equity schedule spanning the MEC-0015 M1 sample (2007-05-01 through 2024-04-30) comprises 7 distinct tiers:

| Seg | Effective Start | Effective End | Rate ($ / Share) | Per-Trade Maximum Cap | Rounding Rule | Official FINRA Source | SEC Release / Reference |
|---|---|---|---|---|---|---|---|
| 1 | 2004-11-01 | 2011-06-30 | $0.000075 | $3.75 | Round UP to cent | FINRA Notice to Members 04-70 / Schedule A | Rel. No. 34-50485 |
| 2 | 2011-07-01 | 2012-02-29 | $0.000090 | $4.50 | Round UP to cent | FINRA Regulatory Notice 11-27 | Rel. No. 34-64590 |
| 3 | 2012-03-01 | 2012-06-30 | $0.000095 | $4.75 | Round UP to cent | FINRA Regulatory Notice 12-06 | Rel. No. 34-66099 |
| 4 | 2012-07-01 | 2021-12-31 | $0.000119 | $5.95 | Round UP to cent | FINRA Regulatory Notice 12-31 | Rel. No. 34-67242 |
| 5 | 2022-01-01 | 2022-12-31 | $0.000130 | $6.49 | Round UP to cent | FINRA SR-FINRA-2020-032 (Phase 1) | Rel. No. 34-90176 |
| 6 | 2023-01-01 | 2023-12-31 | $0.000145 | $7.27 | Round UP to cent | FINRA SR-FINRA-2020-032 (Phase 2) | Rel. No. 34-90176 |
| 7 | 2024-01-01 | 2024-12-31 | $0.000166 | $8.30 | Round UP to cent | FINRA SR-FINRA-2020-032 (Phase 3 Full Implementation) | Rel. No. 34-90176 |

*(Note: MEC-0015 M1 evaluation window concludes on 2024-04-30; the 2024 segment extends through 2024-12-31 to maintain full calendar-year fidelity).*

---

## 3. Mathematical Formula & Implementation Contract

For any executed order on trade date $t$:
$$\text{Fee}_{\text{TAF}}(t) = \begin{cases} 0.00 & \text{if BUY} \\ \text{ceil}_{\text{cents}}\left(\min\left(\text{shares} \times r_{\text{share}}(t), \text{Cap}(t)\right)\right) & \text{if SELL and shares} > 0 \\ 0.00 & \text{if SELL and shares} = 0 \end{cases}$$

Where:
- $r_{\text{share}}(t)$ is the statutory per-share fee.
- $\text{Cap}(t)$ is the statutory per-trade maximum cap.
- Machine-readable definition: [MEC-0015-finra-taf-fee-schedule.json](./manifests/MEC-0015-finra-taf-fee-schedule.json).
- Executable Python function: `acash.execution.regulatory_fees.compute_finra_taf`.
