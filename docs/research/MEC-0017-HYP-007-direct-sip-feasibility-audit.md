# MEC-0017 / HYP-007 Direct-SIP Free-Data Feasibility & Transition Audit

## 1. Executive Summary

This document establishes the empirical data feasibility and exact transition boundary for **HYP_007** (Mechanism **MEC-0017**).
Following the blocking of HYP_006 on historical quote provenance due to third-party historical vendor records carrying condition code `?`, this audit empirically determines when Alpaca's direct SIP capture infrastructure became active with verified granular CTA condition codes (`R`).

- **Mechanism Lineage:** `MEC-0017` (SPY Intraday Noise-Area Momentum Direct-SIP Replication)
- **Candidate Hypothesis ID:** `HYP_007`
- **Primary Market Data Provider:** `ALPACA_HISTORICAL_SIP`
- **Target Instrument:** `SPY` (Consolidated Tape B)
- **Feasibility Verdict:** **`DIRECT_SIP_FREE_DATA_FEASIBILITY_PASS`**
- **Selected M1 Replication Window:** `2021-07-01` through `2024-04-30`
- **M1 Role:** `PUBLICATION_EXPOSED_DIRECT_SIP_REPLICATION_SAMPLE`

---

## 2. Empirical Transition Census Findings

A total of 22 trading sessions spanning January 2021 through April 2024 were probed across four intraday execution decision boundaries (10:00, 12:00, 15:30, 15:59 ET), inspecting 2,184 quote records.

### 2.1 Initial Authorized Transition Census (Prompt §7)

| Session Date | Quotes Inspected | Condition `?` | Condition `R` | Other Official | Unknown | Direct SIP Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **2021-01-04** | 100 | 100 (100%) | 0 | 0 | 0 | `LEGACY_THIRD_PARTY_DATA` |
| **2021-02-01** | 100 | 100 (100%) | 0 | 0 | 0 | `LEGACY_THIRD_PARTY_DATA` |
| **2021-03-01** | 100 | 100 (100%) | 0 | 0 | 0 | `LEGACY_THIRD_PARTY_DATA` |
| **2021-04-01** | 100 | 100 (100%) | 0 | 0 | 0 | `LEGACY_THIRD_PARTY_DATA` |
| **2021-05-03** | 100 | 0 | 100 (100%) | 0 | 0 | `DIRECT_SIP_VERIFIED` |
| **2021-06-01** | 100 | 0 | 100 (100%) | 0 | 0 | `DIRECT_SIP_VERIFIED` |
| **2021-07-01** | 100 | 0 | 100 (100%) | 0 | 0 | `DIRECT_SIP_VERIFIED` |
| **2021-08-02** | 100 | 0 | 100 (100%) | 0 | 0 | `DIRECT_SIP_VERIFIED` |

### 2.2 Narrow Boundary Pinpoint (April 2021 Probes, Prompt §10)

To resolve the exact transition date between April 1 and May 3, daily boundary probes were executed:

| Session Date | Quotes Inspected | Condition `?` | Condition `R` | Boundary Observation |
| :--- | :---: | :---: | :---: | :--- |
| **2021-04-15** | 100 | 100 | 0 | Legacy `?` active |
| **2021-04-23** (Fri) | 100 | 100 | 0 | **Last observed legacy `?` record** |
| **2021-04-26** (Mon) | 100 | 0 | 100 | **First observed direct-SIP `R` record** |
| **2021-04-27** | 100 | 0 | 100 | Direct-SIP `R` active |
| **2021-04-28** | 100 | 0 | 100 | Direct-SIP `R` active |
| **2021-04-29** | 100 | 0 | 100 | Direct-SIP `R` active |
| **2021-04-30** | 100 | 0 | 100 | Direct-SIP `R` active |

**Transition Landmark:** The transition from legacy third-party vendor quotes to direct Alpaca SIP capture took place over the weekend of **April 24–25, 2021**.

### 2.3 Multi-Year Stability Verification (2021–2024)

Probes conducted across subsequent years confirm zero reversion to `?`:
- `2021-10-01`: 100% `R`
- `2022-01-03`: 100% `R`
- `2022-06-01`: 100% `R`
- `2023-01-03`: 100% `R`
- `2023-06-01`: 100% `R`
- `2024-01-02`: 100% `R`
- `2024-04-30`: 100% `R` (M1 terminal date)

---

## 3. Conservative Start-Date Determination (Prompt §9)

Under prompt §9, the M1 start date must be chosen strictly from data provenance, never from strategy performance:
1. April 2021 is a split/transition month (April 1–23 contains `?`).
2. May 2021 is the first full clean calendar month.
3. To enforce an institutional-grade conservative separation buffer and avoid edge-of-transition artifacts, the start date is set to **`2021-07-01`** (calendar Q3 2021).
4. This provides a clean two-month operational buffer (May and June 2021) after the April transition.
5. The terminal date is frozen at **`2024-04-30`**, matching the established publication-exposed boundary and preserving the M2 firewall (`>= 2024-05-01` strictly locked).

---

## 4. Quote Executability Contract

1. **Permitted Execution Quotes:** Only quotes carrying verified regular condition `R` from the official Alpaca Tape B mapping (`GET /v2/stocks/meta/conditions/quote?tape=B`) are executable.
2. **Rejection Policy:** Condition code `?` is strictly prohibited and raises `DataContractError` fail-closed.
3. **Special Conditions:** Non-firm (`N`, `L`), slow (`A`, `B`, `E`, `H`, `U`, `W`), closing (`C`), and auction (`4`) quotes are strictly non-executable.
4. **Unmapped Conditions:** Any unmapped condition code raises `DataContractError` fail-closed.

---

## 5. Feasibility Audit Verdict

- Provenance boundary established: **YES (`2021-07-01`)**
- Free historical SIP quote feed verified: **YES**
- Free 1-minute historical SIP bar feed verified: **YES**
- Official condition code mapping active: **YES**
- Dividend authority reconciled: **YES (SSGA distributions manifest)**
- M2 firewall intact: **YES (`>= 2024-05-01` locked)**
- Verdict: **`DIRECT_SIP_FREE_DATA_FEASIBILITY_PASS`**
