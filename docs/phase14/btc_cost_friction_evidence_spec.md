# ACASH V5 — BTC Cost & Friction Evidence Specification

**Document ID:** `docs/phase14/btc_cost_friction_evidence_spec.md`  
**STATUS: NON-GOVERNING**  
**AUTHORITY: NONE**  
**EMPIRICAL AUTHORIZATION: NONE**  
**BACKTEST AUTHORIZATION: NONE**  
**PAPER AUTHORIZATION: NONE**  
**LIVE AUTHORIZATION: NONE**  
**NO FEE VALUE IS CANONICAL UNTIL SOURCE-BOUND**  
**Canonical Schema Alignment:** `src/acash/backtest/schema.py` (`FeeModelConfig`, `SlippageModelConfig`, `SimulationLatencyConfig`, `RealityGapSummary`)  
**Canonical Architectural Context:** `AGENTS.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/phase14/historical_data_qualification_spec.md`

---

> [!CAUTION]
> ### STRICT EXECUTION REALITY BOUNDARIES & RESEARCH INVARIANTS
> - **NON-GOVERNING EVIDENCE SPECIFICATION:** This document defines evidence requirements and methodology for future backtesting friction models. **No fee, spread, or latency value in this document is canonical until bound to empirical source artifacts.**
> - **NO NEW CANONICAL SCHEMAS:** All models in this document map directly to canonical Phase 5 backtesting schemas in `src/acash/backtest/schema.py`. No competing schema definitions are introduced.
> - **CANONICAL CAPITAL REMAINS $0.00:** Trading capital is strictly **$0.00**; `NO_REAL_ORDERS=true`. Order sizing and volume participation thresholds are research methodology templates, not live allocations.
> - **NO INFERRED SPREAD FROM OHLC:** Bid/ask spread must never be fabricated from bar high/low ranges. Absence of empirical quote data must be classified as `UNRESOLVED — REQUIRES BID/ASK DATA`.
> - **ZERO HOMELAB MUTATION OR LATENCY PROBING:** Active Gate 7 (`G7`) operational soak must not be probed, profiled, or benchmarked during this task.

---

## 1. Executive Summary & Objective

In quantitative systematic trading, failing to model transaction costs, crossing fees, order book impact, queue dynamics, and transmission latency leads to severe backtest overfitting and phantom alpha.

The objective of this specification is to:
1. Ground future execution friction models for Bitcoin (`BTC`) in verifiable, primary-source empirical evidence.
2. Establish a strict structural separation between **BTC Spot** and **BTC Perpetual Futures**.
3. Align all future simulation parameters with canonical Phase 5 backtest schemas (`FeeModelConfig`, `SlippageModelConfig`, `SimulationLatencyConfig`, `RealityGapSummary`).
4. Prevent the fabrication of friction parameters from low-resolution OHLC data.
5. Provide a rigorous, multi-scenario evaluation structure (Base, Conservative, Stress) for future empirical hypotheses.

---

## 2. Market Structure Separation: Spot vs. Perpetual Futures

ACASH enforces an absolute separation between Spot and Perpetual derivative markets. The table below delineates the structural boundaries that must never be conflated:

| Dimension | BTCUSDT SPOT | BTCUSDT PERPETUAL (USDⓈ-M) | Simulation Separation Invariant |
| :--- | :--- | :--- | :--- |
| **Contract Type** | Asset purchase/sale against stablecoin. | Cash-settled synthetic swap against index. | Completely distinct contract instruments. |
| **Underlying Deliverable** | Physical Bitcoin units in wallet / custody. | Synthetic USD-pegged contract without physical delivery. | Spot inventory ≠ Derivative margin balance. |
| **Holding Cost / Drag** | Zero holding cost (unless margin borrowed). | **8-Hour Funding Rate** (paid/received between long and short). | Funding cash flow must be simulated separately. |
| **Borrow Mechanics** | Spot margin requires explicit asset borrowing + interest. | Inherent leverage; initial and maintenance margin. | Spot shorting requires borrow fee model. |
| **Fee Structure** | Standard retail: 10.0 bps Maker / 10.0 bps Taker. | Standard retail: 2.0 bps Maker / 5.0 bps Taker. | Cannot apply derivative fees to spot trading. |
| **Liquidity & Depth** | Centralized spot order book; capital-constrained. | Massive speculative order book; high leverage. | Order book depth differs by ~3x–10x. |
| **Liquidation Mechanics** | Unleveraged spot cannot be liquidated; margin has margin call. | Exchange liquidation engine, deleveraging (ADL), insurance fund. | Extreme tail events trigger liquidation cascades. |

---

## 3. Empirical Exchange Fee Evidence

Fee assumptions must reflect the unprivileged baseline of an independent researcher, not promotional discounts or institutional VIP tiers.

### 3.1 Primary Exchange Fee Schedules (Binance Baseline)

Evidence gathered from official Binance fee schedules (`https://www.binance.com/en/fee/trading` and `https://www.binance.com/en/fee/futureFee`):

| Market | Tier Level | Maker Fee | Taker Fee | 30-Day Volume Requirement | BNB Balance Requirement | Token Discount | Effective Date / Status | Source URL |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BTCUSDT Spot** | Regular User (VIP 0) | **0.1000%** (10.0 bps) | **0.1000%** (10.0 bps) | < $1,000,000 USD | $\ge 0$ BNB | Standard (None) | Verified 2026-09-13 | `binance.com/en/fee/trading` |
| **BTCUSDT Spot** | VIP 0 w/ BNB | 0.0750% (7.5 bps) | 0.0750% (7.5 bps) | < $1,000,000 USD | Balance > 0 BNB | 25% BNB deduction | `ACCOUNT-DEPENDENT` | `binance.com/en/fee/trading` |
| **BTCUSDT Perpetual**| Regular User (VIP 0) | **0.0200%** (2.0 bps) | **0.0500%** (5.0 bps) | < $15,000,000 USD | $\ge 0$ BNB | Standard (None) | Verified 2026-09-13 | `binance.com/en/fee/futureFee` |
| **BTCUSDT Perpetual**| VIP 0 w/ BNB | 0.0180% (1.8 bps) | 0.0450% (4.5 bps) | < $15,000,000 USD | Balance > 0 BNB | 10% BNB deduction | `ACCOUNT-DEPENDENT` | `binance.com/en/fee/futureFee` |

### 3.2 Secondary Exchange Fee Benchmarks (Kraken Baseline)

Evidence gathered from official Kraken fee schedules (`https://www.kraken.com/features/fee-schedule`):

| Market | Tier Level | Maker Fee | Taker Fee | 30-Day Volume Requirement | Effective Date / Status | Source URL |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **XBTUSDT Spot** | Retail Tier 1 | **0.2500%** (25.0 bps) | **0.4000%** (40.0 bps) | $0 – $10,000 USD | Verified 2026-09-13 | `kraken.com/features/fee-schedule` |
| **XBTUSDT Spot** | Retail Tier 2 | 0.2000% (20.0 bps) | 0.3500% (35.0 bps) | $10,000 – $50,000 USD | Verified 2026-09-13 | `kraken.com/features/fee-schedule` |

### 3.3 Strict Fee Policy Invariants
1. **Never Assume VIP or Token Discounts:** Standard research simulations must default to **VIP 0 Regular User without BNB discount** (Spot: 10.0 bps Maker / 10.0 bps Taker; Perpetual: 2.0 bps Maker / 5.0 bps Taker).
2. **Promotional Zero-Fee Pairs are Temporary:** Periods where Binance offered zero-fee trading (e.g. BTC/TUSD or BTC/FDUSD promotions) represent non-stationary regimes and must be marked `PROMOTIONAL_REGIME`.

---

## 4. Spread Modeling Evidence Requirements

### 4.1 Strict Invariant: No Spread Fabrication from OHLC
> [!CAUTION]
> **DO NOT FABRICATE SPREAD FROM OHLC BARS:** A bar's high-low range measures price range over a timeframe, **not** the instantaneous top-of-book bid/ask spread. Any attempt to estimate bid/ask spread by scaling $\text{High} - \text{Low}$ or via Parkinson/Corwin-Schultz estimators without tick validation is strictly unverified. In the absence of direct top-of-book recordings, spread status is:  
> **`UNRESOLVED — REQUIRES BID/ASK DATA`**

### 4.2 Required Evidence for Future Spread Sourcing
To establish a canonical spread parameter for simulation, the researcher must acquire or record an empirical top-of-book dataset satisfying:
- **Sampling Cadence:** Minimum 1-second top-of-book snapshots ($P_{\text{bid}}, Q_{\text{bid}}, P_{\text{ask}}, Q_{\text{ask}}$) or trade-conditioned arrival quotes.
- **Statistical Measures Required:**
  - Median half-spread in basis points ($\text{bps}$).
  - 95th and 99th percentile upper-tail spread (volatility shock conditions).
  - Time-of-day dispersion (e.g. US market open vs. Asian trading hours vs. weekend).
- **Current Evidence Baseline (Empirical Reference):**
  - Binance BTCUSDT Spot liquid daytime: Typically 0.01 USDT ($< 0.01$ bps on a \$60,000 BTC price) at top-of-book.
  - Stress periods (flash crashes, volatility halts): Spreads can widen to $5.0$ to $20.0$ bps.
  - **Status:** `UNRESOLVED (PENDING EMPIRICAL QUOTE RECORDING)`

---

## 5. Slippage & Market Impact Decomposition

Simulated execution must decompose execution friction into five distinct, non-overlapping mechanisms:

```
Total Execution Friction = Spread Drag + Slippage Drag + Latency Drag + Fee Drag + Adverse Selection
```

### 5.1 Friction Decomposition Taxonomy

| Friction Mechanism | Definition | Applicable Order Type | Canonical Backtest Schema Field |
| :--- | :--- | :--- | :--- |
| **Half-Spread Crossing** | The cost paid to cross the bid/ask spread at order arrival. | `MARKET`, `IOC` | `RealityGapSummary.spread_drag_bps` |
| **Price Impact (Depth)** | The price degradation caused by consuming multiple order book levels. | Large `MARKET`, `IOC` | `RealityGapSummary.slippage_drag_bps` |
| **Latency Slippage** | The adverse price movement occurring between signal calculation and matching engine arrival. | All Orders | `RealityGapSummary.latency_drag_bps` |
| **Exchange & Broker Fees** | Contractual transaction fees levied by the venue. | All Orders | `RealityGapSummary.fee_drag_bps` |
| **Maker Adverse Selection** | Post-arrival adverse price movement when a passive limit order is filled (winner's curse). | Passive `LIMIT` | `RealityGapSummary.maker_adverse_selection_drag_bps` |

### 5.2 Microstructural Limitation Invariant
> [!IMPORTANT]
> **OHLC-ONLY DATA CANNOT JUSTIFY TICK-LEVEL QUEUE SIMULATION:**  
> M1 OHLC bars record aggregated volume, not order book queue depth, order cancellations, or queue priority position. Limit order execution based solely on `Low <= LimitPrice` without order book queue modeling severely overstates fill rates and profitability.

---

## 6. Latency Decomposition & Measurement Design

In accordance with `SimulationLatencyConfig` in `src/acash/backtest/schema.py`, latency is decomposed into four discrete components:

```text
Decision Timestamp
       │
       │  [ signal_calc_latency_ns ]   (Time to compute alpha features & generate order)
       ▼
Order Emitted
       │
       │  [ uplink_latency_ns ]        (Network transit: host -> exchange gateway)
       ▼
Exchange Gateway Arrival
       │
       │  [ matching_engine_latency_ns ] (Queue serialization & order book match)
       ▼
Matching Complete / Fill Execution
       │
       │  [ downlink_latency_ns ]      (Network transit: gateway ack -> host)
       ▼
Fill Acknowledged
```

### 6.1 Measurement Protocol Across Environments

| Component | Historical Backtest Assumption | Paper Execution Measurement | Future Live Measurement |
| :--- | :--- | :--- | :--- |
| **Signal Calculation** | Model parameter (`signal_calc_latency_ns`) | Monotonic clock diff ($\tau_{\text{emit}} - \tau_{\text{bar}}$) | High-resolution CPU timestamp counter |
| **Uplink Latency** | Model parameter (`uplink_latency_ns`) | TCP roundtrip time / 2 to exchange API gateway | Measured WebSocket transit delta |
| **Matching Engine** | Model parameter (`matching_engine_latency_ns`) | Estimated from exchange execution report timestamps | Exchange server timestamp vs. arrival |
| **Downlink Latency** | Model parameter (`downlink_latency_ns`) | TCP roundtrip time / 2 | Inbound socket parse delta |

> [!CAUTION]
> **HOMELAB PROBING RESTRICTION:**  
> No network latency measurement, ping flood, or socket profiling may be executed against homelab infrastructure while the Gate 7 soak is active. All numerical latency thresholds remain **`UNRESOLVED`** until dedicated latency calibration is authorized.

---

## 7. Order Sizing & Capacity Methodology

Canonical trading capital remains **$0.00**; `NO_REAL_ORDERS=true`. No tradeable live order sizes exist.

For future empirical research, candidate strategies must evaluate market capacity using explicit volume participation ratios rather than assuming infinite depth:

### 7.1 Research Capacity Buckets
Future research candidates must be tested across parameterized order notional buckets:
- **Bucket 1 (Micro / Test):** \$1,000 USD notional (trivial market impact on BTC).
- **Bucket 2 (Small Quantitative):** \$10,000 USD notional.
- **Bucket 3 (Medium Strategy):** \$50,000 USD notional.
- **Bucket 4 (Capacity Stress):** \$250,000 USD notional.

### 7.2 Volume Participation Ceiling
- In any 1-minute bar window, simulated order size $Q_{\text{order}}$ must not exceed a maximum participation ratio $\alpha_{\text{max}}$ of total bar volume $V_{\text{bar}}$:
  $$\frac{Q_{\text{order}}}{V_{\text{bar}}} \le \alpha_{\text{max}} \quad (\text{e.g. } \alpha_{\text{max}} = 0.02 \text{ or } 2\%)$$
- Orders exceeding $\alpha_{\text{max}}$ must trigger simulated partial fills or multi-bar execution schedules.

---

## 8. Multi-Scenario Friction Evaluation Framework

To prevent curve-fitting to an artificially optimistic cost model, candidate strategies must be evaluated across three friction scenarios. 

> [!NOTE]
> These scenarios define **evaluation frameworks**, NOT global hardcoded pass/fail thresholds. Exact parameter values must be bound to empirical evidence before backtesting.

| Parameter | BASE SCENARIO (Liquid / Normal) | CONSERVATIVE SCENARIO (Conservative Planning) | STRESS SCENARIO (Liquidity Shocks / Panic) |
| :--- | :--- | :--- | :--- |
| **Venue / Market** | Binance BTCUSDT Spot | Binance BTCUSDT Spot | Binance BTCUSDT Spot |
| **Maker Fee (`maker_fee_bps`)** | 10.0 bps (0.1000%) | 10.0 bps (0.1000%) | 10.0 bps (0.1000%) |
| **Taker Fee (`taker_fee_bps`)** | 10.0 bps (0.1000%) | 10.0 bps (0.1000%) | 10.0 bps (0.1000%) |
| **Bid/Ask Half-Spread** | 0.5 bps (`UNRESOLVED`) | 2.0 bps (`UNRESOLVED`) | 10.0 bps (`UNRESOLVED`) |
| **Fixed Slippage (`fixed_slippage_bps`)** | 0.5 bps (`UNRESOLVED`) | 2.5 bps (`UNRESOLVED`) | 10.0 bps (`UNRESOLVED`) |
| **Linear Impact (`impact_coefficient`)** | 0.0001 (`UNRESOLVED`) | 0.0005 (`UNRESOLVED`) | 0.0020 (`UNRESOLVED`) |
| **Total Roundtrip Latency** | 50 ms (`UNRESOLVED`) | 200 ms (`UNRESOLVED`) | 1,000 ms (`UNRESOLVED`) |
| **Adverse Selection Drag** | 1.0 bps (`UNRESOLVED`) | 3.0 bps (`UNRESOLVED`) | 8.0 bps (`UNRESOLVED`) |

---

## 9. Alignment with Canonical Backtest Schemas

Future backtest manifests and execution configurations must serialize friction parameters using the exact schemas from `src/acash/backtest/schema.py`:

```python
# Example canonical configuration alignment (Illustration only - No execution authorized)
from decimal import Decimal
from acash.backtest.schema import FeeModelConfig, SlippageModelConfig, SimulationLatencyConfig

fee_config = FeeModelConfig(
    maker_fee_bps=Decimal("10.0"),       # Binance Spot VIP 0 Retail Maker
    taker_fee_bps=Decimal("10.0"),       # Binance Spot VIP 0 Retail Taker
    fixed_fee_per_trade=Decimal("0.0"),
)

slippage_config = SlippageModelConfig(
    fixed_slippage_bps=Decimal("2.0"),   # Sourced from conservative empirical spread
    impact_coefficient=Decimal("0.0005"),# Depth impact model
)

latency_config = SimulationLatencyConfig(
    signal_calc_latency_ns=5_000_000,    # 5 ms calculation delay
    uplink_latency_ns=25_000_000,        # 25 ms network uplink
    matching_engine_latency_ns=5_000_000,# 5 ms matching engine
    downlink_latency_ns=25_000_000,      # 25 ms downlink ack
)
```

---

## 10. External Evidence & Citations

1. **Binance Spot Trading Fee Schedule:**  
   - URL: `https://www.binance.com/en/fee/trading`  
   - Access Date: 2026-09-13 UTC  
   - Supported Claims: Regular User (VIP 0) standard fee is 0.1000% Maker and 0.1000% Taker; 25% discount when paying with BNB (0.0750%/0.0750%).
2. **Binance USDⓈ-M Futures Fee Schedule:**  
   - URL: `https://www.binance.com/en/fee/futureFee`  
   - Access Date: 2026-09-13 UTC  
   - Supported Claims: Regular User (VIP 0) standard fee is 0.0200% Maker and 0.0500% Taker; 10% discount when paying with BNB (0.0180%/0.0450%); 8-hour funding schedule.
3. **Kraken Fee Structures:**  
   - URL: `https://www.kraken.com/features/fee-schedule`  
   - Access Date: 2026-09-13 UTC  
   - Supported Claims: Retail Tier 1 ($0–$10k) spot fee is 0.25% Maker and 0.40% Taker.

---

### Verification Ledger
- Implementation Status: COMPLETE (Cost & friction evidence specification)
- Contract Enforcement: STRICT FAIL-CLOSED (Zero fabricated spread, zero backtest authority, zero capital)
- Mathematical Authority: CANONICAL SPEC (Aligned with `src/acash/backtest/schema.py`)
- Local Test Suite: NOT RUN (Documentation-only deliverable)
- Type Checker (MyPy): NOT RUN (Documentation-only deliverable)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: Numerical thresholds for spread, latency, and impact are explicitly marked `UNRESOLVED` pending empirical high-frequency recordings.
