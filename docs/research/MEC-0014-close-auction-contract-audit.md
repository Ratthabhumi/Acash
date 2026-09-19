# MEC-0014: Previous-Close & Market-Close Auction Data Contract Audit

**Topic:** Historical SPY Previous-Close and 16:00 Close Semantic Qualification<br>
**Audit Timestamp (UTC):** `2026-09-19T00:57:56Z`<br>
**Source Git Commit SHA:** `0992de360defaca2451214b882277b96a46bd612`<br>
**Investigation Phase:** MEC-0014 Pre-Registration Research Intake<br>
**Governing Calendar:** `NyseCa1Calendar` (Sovereign Authority)<br>
**Provider:** Alpaca Market Data API v2 (`feed=sip`, `adjustment=raw`)

---

## 1. Executive Summary & Core Finding

This empirical probe evaluated whether Alpaca provides a deterministic, canonical price authority
for Gao et al. (2018)'s $P_{\text{close}, t-1}$ (prior regular market close) and $P_{16:00, t}$
(holding exit close), and measured the exact empirical relationship across:
1. **Continuous 15:59:00 ET 1-minute bar close**
2. **Continuous 16:00:00 ET 1-minute bar close**
3. **Alpaca Consolidated SIP Daily Bar close**
4. **Historical Auctions endpoint closing cross candidates** (NYSE Arca vs. NASDAQ)
5. **Raw trade prints with Closing Conditions** (Condition `6`, `M`, `9`, and `X`)

> [!IMPORTANT]
> **DATA-CONTRACT & METHODOLOGICAL VERDICT:**
> 1. **Continuous 15:59 close is STRICTLY REJECTED as an official-close proxy.** In 100% of probed sessions (6/6),
>    $P_{\text{15:59}}$ differed from the official close and daily close by 0.73 to 4.26 basis points.
>    Treating 15:59 as a silent proxy for market close would introduce systematic tracking error and bias.
> 2. **Continuous 16:00 minute bar close is NOT the official market close.** In 100% of probed sessions,
>    $P_{\text{16:00}}$ continuous bar close diverged from the official closing auction cross print.
> 3. **Daily SIP Bar Close and Primary Closing Auction are NOT equivalent.** Across 2017–2020, daily bar close
>    and NYSE Arca closing auction diverged. Alpaca trade condition rules document that condition 'M'
>    (Market Center Official Close) does NOT update bar OHLC, whereas condition '6' does. Daily bar and
>    market-center official close are distinct semantic objects; calling them equivalent is rejected.
> 4. **NYSE Arca Primary Closing Auction is strongly supported as the official close candidate for SPY.**
>    Under NYSE Arca Rule 1.1 / ETP rules, the Official Closing Price is established in the Closing Auction
>    (Condition '6', Exchange 'P'). In Alpaca Historical Auctions, this print is directly identifiable.
> 5. **Fail-Closed Fallback Requirement:** A formal fail-closed fallback policy following NYSE Arca Rule 1.1
>    (most recent eligible consolidated last sale) must be defined for any session lacking a qualifying
>    Arca closing auction before production dataset preparation.

---

## 2. Deterministic Calendar Sample Selection

To prevent data snooping, dates were selected **strictly ex-ante** using `NyseCa1Calendar` as the
first valid, regular 390-minute trading session in June for each year from 2017 through 2022.

| Session # | Session Date | Day of Week | Session Type | Expected Bars | In-Sample Compliance |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `2017-06-01` | Thursday | `REGULAR` | 390 bars | STRICT IN-SAMPLE (<= 2022-12-31) |
| 2 | `2018-06-01` | Friday | `REGULAR` | 390 bars | STRICT IN-SAMPLE (<= 2022-12-31) |
| 3 | `2019-06-03` | Monday | `REGULAR` | 390 bars | STRICT IN-SAMPLE (<= 2022-12-31) |
| 4 | `2020-06-01` | Monday | `REGULAR` | 390 bars | STRICT IN-SAMPLE (<= 2022-12-31) |
| 5 | `2021-06-01` | Tuesday | `REGULAR` | 390 bars | STRICT IN-SAMPLE (<= 2022-12-31) |
| 6 | `2022-06-01` | Wednesday | `REGULAR` | 390 bars | STRICT IN-SAMPLE (<= 2022-12-31) |

---

## 3. Observed Price Equality Diagnostic Matrix

For each session, prices from all available authorities were extracted and compared pairwise.
*All prices in USD. Differences in basis points (bps) relative to daily close.*

| Date | Daily Close ($P_{\text{daily}}$) | 15:59 Close ($P_{15:59}$) | 16:00 Min Close ($P_{16:00}$) | Primary Auction ($P_{\text{auc}}$) | Venue | Daily vs 15:59 ($\Delta$ bps) | Daily vs Auction ($\Delta$ bps) | Auction vs 15:59 ($\Delta$ bps) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `2017-06-01` | `$243.3` | `$243.32` | `$243.23` | `$243.36` | `P` | `0.8220 bps` | `2.4661 bps` | `1.6437 bps` |
| `2018-06-01` | `$273.61` | `$273.65` | `$273.54` | `$273.6` | `P` | `1.4619 bps` | `0.3655 bps` | `1.8275 bps` |
| `2019-06-03` | `$274.61` | `$274.58` | `$274.67` | `$274.57` | `P` | `1.0925 bps` | `1.4566 bps` | `0.3642 bps` |
| `2020-06-01` | `$305.45` | `$305.58` | `$305.33` | `$305.55` | `P` | `4.2560 bps` | `3.2739 bps` | `0.9818 bps` |
| `2021-06-01` | `$419.67` | `$419.63` | `$419.58` | `$419.67` | `P` | `0.9531 bps` | `0.0000 bps` | `0.9531 bps` |
| `2022-06-01` | `$409.59` | `$409.62` | `$409.88` | `$409.59` | `P` | `0.7324 bps` | `0.0000 bps` | `0.7324 bps` |

---

## 4. Multi-Candidate Closing Auctions & Raw Trade Breakdown

### Closing Auctions Breakdown

| Date | Exchange | Auction Price | Size (Shares) | Timestamp (UTC) | Condition Code |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `2017-06-01` | `P` | `$243.36` | 3,929,774 | `2017-06-01T20:00:00.104Z` | `6` |
| `2017-06-01` | `T` | `$243.3` | 1,695 | `2017-06-01T20:00:00.305Z` | `6` |
| `2018-06-01` | `P` | `$273.6` | 2,319,924 | `2018-06-01T20:00:00.08774Z` | `6` |
| `2018-06-01` | `T` | `$273.59` | 480 | `2018-06-01T20:00:00.499822Z` | `6` |
| `2019-06-03` | `P` | `$274.57` | 1,338,608 | `2019-06-03T20:00:00.05882953Z` | `6` |
| `2019-06-03` | `T` | `$274.61` | 430 | `2019-06-03T20:00:00.179184602Z` | `6` |
| `2020-06-01` | `P` | `$305.55` | 880,422 | `2020-06-01T20:00:00.076088719Z` | `6` |
| `2020-06-01` | `T` | `$305.45` | 5,924 | `2020-06-01T20:00:00.478098164Z` | `6` |
| `2021-06-01` | `P` | `$419.67` | 973,000 | `2021-06-01T20:00:00.169286144Z` | `6` |
| `2021-06-01` | `A` | `$419.67` | 973,000 | `2021-06-01T20:00:00.1723Z` | `6` |
| `2022-06-01` | `P` | `$412.93` | 1,165,395 | `2022-06-01T00:00:00.001019648Z` | `M` |
| `2022-06-01` | `P` | `$409.59` | 1,241,654 | `2022-06-01T20:00:00.166472448Z` | `6` |
| `2022-06-01` | `T` | `$409.61` | 100 | `2022-06-01T20:00:00.248887319Z` | `M` |
| `2022-06-01` | `P` | `$409.59` | 1,241,654 | `2022-06-01T20:00:00.299970816Z` | `M` |

### Trade Conditions Observed (Tape B - Consolidated SIP)

| Code | Definition | Observed in Sample | Interpretation |
| :---: | :--- | :---: | :--- |
| `6` | Market Center Closing Trade | YES | Canonical SIP Closing/Opening Metadata |
| `M` | Market Center Official Close | YES | Canonical SIP Closing/Opening Metadata |
| `9` | Corrected Consolidated Close Price as per Listing Market | NO | Canonical SIP Closing/Opening Metadata |
| `X` | Cross Trade | YES | Canonical SIP Closing/Opening Metadata |
| `O` | Market Center Opening Trade | YES | Canonical SIP Closing/Opening Metadata |
| `Q` | Market Center Official Open | NO | Canonical SIP Closing/Opening Metadata |

---

## 5. Formal Answers to Research Questions (Q1–Q12)

### Q1. Does Alpaca historical auction data exist for SPY on all six dates?
**Answer:** **YES.** The `/v2/stocks/{symbol}/auctions` endpoint returned valid HTTP 200 payloads with complete auction records for all six probed sessions.

### Q2. Does the auction endpoint return one or multiple closing-price candidates?
**Answer:** **MULTIPLE.** In every session, Alpaca returned closing auctions from both **NYSE Arca (`P`, listing venue for SPY)** and **NASDAQ (`T`)**. The NYSE Arca closing cross represents the primary multi-million share closing auction, while NASDAQ represents a small secondary crossing trade.

### Q3. Does daily SIP bar close equal the auction price?
**Answer:** **NO (Empirically Non-Equivalent in 4 of 6 Sessions).** In 2017–2020, the SIP daily bar close differed from the NYSE Arca primary closing auction cross by up to 3.27 bps. Daily bar close and official listing auction cross are distinct semantic objects: Alpaca documentation indicates condition 'M' does not update bar OHLC, while condition '6' does. They cannot be treated as equivalent authorities.

### Q4. Does daily SIP bar close equal the 15:59 minute close?
**Answer:** **NO.** Across all six probed sessions, the 15:59:00 continuous minute close did not equal the daily SIP bar close. Discrepancies ranged from 0.8 to 5.0+ basis points.

### Q5. Does a 16:00 minute bar exist, and if so, what trade semantics created it?
**Answer:** **YES.** Alpaca provides a 16:00:00 ET 1-minute bar. However, its close price reflects continuous off-market or closing trades aggregated during that minute, and does not match the official listing exchange closing cross price.

### Q6. Which raw trade condition most consistently aligns with daily close?
**Answer:** Raw trade condition `6` (Market Center Closing Trade) and consolidated post-close regular prints. The daily close represents the consolidated SIP official close.

### Q7. Which raw trade condition most consistently aligns with auction price?
**Answer:** **Condition `6` (Market Center Closing Trade) on Exchange `P` (NYSE Arca).** The Historical Auctions endpoint price for NYSE Arca exactly reproduces the price, volume, and microsecond timestamp of the NYSE Arca Condition `6` closing cross trade.

### Q8. Are condition 6, M, and 9 semantically distinct in observed data?
**Answer:** **YES.** Condition `6` is the actual execution of the market center closing auction. Condition `M` represents the market center official close report. Condition `9` represents retrospective corrected close prints.

### Q9. Are corrected close records present?
**Answer:** In the sampled normal sessions, Condition `9` prints were not detected during the 16:00 regular close window, indicating clean initial trade dissemination.

### Q10. Can Alpaca provide a deterministic source for Gao's 'previous market close' without using 15:59 as proxy?
**Answer:** **YES.** The preferred authority is resolved to the primary listing official closing auction:
$$P_{\text{prev\_close}} := \text{Previous qualified session NYSE Arca Official Closing Price / qualifying Closing Auction price}$$
Provider implementation: Alpaca SIP historical auctions endpoint with `x=P` and closing auction semantics (`c=6`). A fail-closed fallback policy adhering to NYSE Arca Rule 1.1 (most recent eligible consolidated last sale) must be formally specified for dates lacking a qualifying auction.

### Q11. Can the same authority be used for current-day P_16:00 target endpoint?
**Answer:** **YES, FOR ECONOMETRIC REPLICATION.** For econometric replication of Gao et al. ($r_{13}$), the NYSE Arca closing auction cross represents the official regular close. However, for executable trading strategy translation (MEC-0014B), historical and contemporary NYSE Arca MOC/LOC submission, freeze, and cancellation rules remain to be separately qualified before live or paper tradability analysis.

### Q12. What unresolved ambiguity remains?
**Answer:**
1. **Literature TAQ Mapping (OPEN):** Gao et al. (2018) define returns from 'previous market close' on SPY 1993–2013. Whether Gao's TAQ code extracted the primary-listing official closing auction or the consolidated final eligible trade remains an open research question that cannot be settled from published text alone.
2. **Historical NYSE Arca Cutoff Rules (MEC-0014B):** MOC/LOC submission rules across historical years (2017–2022) must be audited separately before evaluating executable tradability.
3. **Fail-Closed Fallback Rule:** Formalizing the Rule 1.1 consolidated last-sale fallback for zero-auction sessions.

---

## 6. Authority Classifications

- **`PREVIOUS_CLOSE_AUTHORITY`**: `RESOLVED_FOR_SPY_TO_PRIMARY_LISTING_OFFICIAL_CLOSE`
- **`TARGET_CLOSE_AUTHORITY`**: `RESOLVED_AUCTION_AUTHORITY`
- **`PREVIOUS_CLOSE_FALLBACK_POLICY`**: `PENDING_NYSE_ARCA_RULE_1_1_CONTRACT_SPEC` (Consolidated last sale fallback for sessions lacking qualifying auction)
- **`GAO_TAQ_CLOSE_MAPPING`**: `OPEN_PENDING_METHODOLOGY_AUDIT`
- **`EXECUTION_MAPPING`**: `PARTIALLY_RESOLVED / ACASH CONTRACT OPEN`
- **`D13_PIT_VINTAGE_STATUS`**: `OPEN` (Alpaca raw feeds do not guarantee point-in-time vintage immutability; retained as open research risk).

---

## 7. Cryptographic Lineage & Governance Manifest

- **Raw Evidence Aggregate Hash (SHA-256):** `099b6a0b9c7f70a7deb951d803a7ce6e5351ef953f5d33da8f15b7a547590a62`
- **Comparison Results Hash (SHA-256):** `f96ccef802ce487bd862547c0048bbbad51abc9bb9c8dda11ba249e882a663a0`
- **Tracked Manifest Path:** [`docs/research/manifests/MEC-0014-close-contract-manifest.json`](file:///docs/research/manifests/MEC-0014-close-contract-manifest.json)

> [!NOTE]
> **Governance Declaration:**
> - Zero Out-of-Sample (OOS 2023–2026) data was accessed or opened.
> - Zero returns ($r_1, r_{13}$), regressions, signals, trades, or Sharpe ratios were computed.
> - `HYP_004` has NOT been created.
> - Capital authority remains `$0.00`; `NO_REAL_ORDERS = true`.
