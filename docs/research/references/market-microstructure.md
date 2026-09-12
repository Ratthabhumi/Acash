# Market Microstructure & Order Flow Architecture

**Status:** ARCHITECTURAL_CONCEPT — Feature Engineering & Microstructure Taxonomy  
**Canonical Governance Authority:** Non-Executable Research Reference. Does NOT authorize backtest, paper trading, or live execution. Does NOT create HYP_003. Preserves Canonical Capital = $0.00 and NO_REAL_ORDERS = true.

---

## 1. Core Axiom & Epistemic Boundary

> [!IMPORTANT]
> **Core Axiom:**
> **ORDER FLOW IS INFORMATION. ORDER FLOW IS NOT AUTOMATICALLY AN EDGE.**

In retail and social-media trading lore, order flow is often treated as a direct deterministic signal (e.g., *"Large order flow detected → Smart money is buying → Market must go up"*). 

In institutional quantitative finance, order flow represents the raw transactional mechanics of market participants executing trades against available liquidity. It provides information regarding instantaneous liquidity consumption, inventory rebalancing, and execution urgency, but it **does NOT guarantee future directional price movement**.

The ACASH research transformation pipeline strictly enforces:
```text
MARKET DATA (L1/L2/Trades)
            ↓
       OBSERVATION
            ↓
    MEASURABLE FEATURE
            ↓
    FORMAL HYPOTHESIS
            ↓
     STATISTICAL TEST
            ↓
   OUT-OF-SAMPLE / OOS
            ↓
  EMPIRICAL VALIDATION
```

---

## 2. The Semantic Rule: Observable Quantities vs. Narrative Lore

To maintain absolute scientific and epistemic integrity, ACASH strictly prohibits subjective anthropomorphic labels as ground truth in research documents, code, or data schemas:

| Prohibited Narrative Label | Why Prohibited | Required Observable Mathematical Variable |
|---|---|---|
| `SMART_MONEY_BUYING` | Unobservable mental state / narrative fallacy | `aggressive_buy_volume_ratio = buy_vol / total_vol` |
| `WHALE_SELLING` | Unverified identity / speculative attribution | `large_trade_count_sell = count(trade_size > 95th_percentile)` |
| `INSTITUTIONAL_INTENT` | Psychological conjecture | `volume_weighted_average_price_deviation = price - vwap` |
| `HIDDEN_ORDER` | Unconfirmed assumption without native exchange flag | `executed_volume_exceeding_displayed_depth_delta` |
| `MANIPULATION` | Non-falsifiable conspiracy theory | `rapid_quote_cancellation_rate = canceled_quotes / added_quotes` |
| `STOP_HUNT` | Narrative attribution to natural liquidity clearance | `liquidity_absorption_at_prior_extrema` |

---

## 3. Taxonomy of Measurable Order Flow & Microstructure Features

### 3.1 Order Book (L2 / L3 Depth)
- **`bid_depth_usd` / `ask_depth_usd`:** Total cumulative dollar depth within $N$ basis points of the mid-price.
- **`bid_ask_imbalance`:** Ratio quantifying depth asymmetry:
  $$I_{OB} = rac{	ext{Bid Depth} - 	ext{Ask Depth}}{	ext{Bid Depth} + 	ext{Ask Depth}} \in [-1, 1]$$
- **`bid_ask_spread_bps`:** Instantaneous difference between best ask and best bid normalized by mid-price.
- **`depth_concentration`:** Percentage of total book depth concentrated at the top 3 levels vs. deep book levels.
- **`book_resiliency`:** Time required for book depth to replenish following a market order sweep.

### 3.2 Trade Flow (Tape / Tick Analytics)
- **`aggressive_buy_volume`:** Volume executed at the ask or higher (buyer-initiated).
- **`aggressive_sell_volume`:** Volume executed at the bid or lower (seller-initiated).
- **`volume_delta`:** Net directional aggressive trading pressure over a given window:
  $$\Delta V = V_{	ext{aggressive\_buy}} - V_{	ext{aggressive\_sell}}$$
- **`cumulative_volume_delta (CVD)`:** Running integral of $\Delta V$ over a defined session or lookback.
- **`trade_count_ratio`:** Ratio of unique buyer-initiated transactions to seller-initiated transactions.

### 3.3 Liquidity Dynamics
- **`displayed_liquidity_additions`:** Volume added as passive limit orders.
- **`displayed_liquidity_cancellations`:** Volume canceled before execution.
- **`cancellation_to_trade_ratio`:** Ratio of canceled volume to executed volume (proxy for quote fleetingness).
- **`liquidity_absorption`:** High aggressive volume executed at a specific price level without advancing the price (passive limit absorption).

### 3.4 Footprint / Order Flow Clusters
- **`volume_at_price`:** Total volume transacted at each discrete tick level.
- **`delta_at_price`:** Net aggressive volume ($\Delta V$) at each discrete tick level.
- **`high_volume_node (HVN)`:** Price levels with statistically dominant transacted volume (fair value agreement).
- **`low_volume_node (LVN)`:** Price levels with thin transacted volume (rapid price rejection or vacuum).
- **`diagonal_bid_ask_imbalance`:** Comparison of aggressive buying at price $P$ vs. aggressive selling at price $P - 1	ext{ tick}$.

---

## 4. The Critical Reality: Displayed Liquidity != True Liquidity

A fundamental trap in order flow analysis is treating displayed order book depth as guaranteed execution availability:

```text
DISPLAYED ASK WALL DETECTED
            ↓
       OBSERVATION
            ↓
  PRICE RESPONSE IN SPECS
            ↓
  STATISTICAL TEST
```

**Why Displayed Liquidity is Non-Deterministic:**
1. **Fleeting Orders & Spoofing:** Large limit orders can be canceled milliseconds before incoming trades arrive.
2. **Iceberg & Hidden Orders:** Exchanges support native hidden or partially displayed orders; displayed depth represents only a fraction of resting interest.
3. **Algorithmic Liquidity Provision:** Market makers dynamically pull quotes across correlated venues when latency or adverse selection increases.
4. **Hedging & Cross-Market Arbitrage:** A large resting order on an exchange may be an arbitrage leg hedging a position on another venue, not an outright speculative directional bet.

**ACASH Analytical Rule:**  
Never conclude *"A large ask wall means the market cannot rise."*  
Instead formulate: *"When ask depth exceeds bid depth by $3:1$ within $10	ext{ bps}$ during Asian hours, what is the empirical probability distribution of 15-minute forward price returns across a 1-year sample?"*
