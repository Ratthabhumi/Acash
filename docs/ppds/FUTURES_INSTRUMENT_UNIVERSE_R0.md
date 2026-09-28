# ACASH Futures Instrument Universe Specification R0 (CME Micro Contracts)

**Document:** `docs/ppds/FUTURES_INSTRUMENT_UNIVERSE_R0.md`
**System Module:** Derivatives Product Specifications & Contract Lineage
**Exchange Authority:** Chicago Mercantile Exchange Group (CME, CBOT, NYMEX, COMEX)
**Stage:** R0 Technical Contract Specification
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 2, 6, 7

---

## 1. Executive Summary & Exchange-Traded Discipline

The **Futures / Macro Trading Book** utilizes centrally cleared, exchange-traded futures contracts governed by the rules of the CME Group.

### Non-Negotiable Contract Axioms:
1. **Centralized Futures $\neq$ Retail CFDs:** Retail CFDs (e.g. broker-created "NAS100 CFD", "XAUUSD OTC", "USOIL CFD") are bilateral, over-the-counter contracts where the retail broker acts as counterparty and market-maker, creating severe conflict of interest, unhedgeable spread widening, and liquidation slippage. ACASH enforces exchange-cleared CME derivatives.
2. **Micro Contracts as the Default Production Vehicle:** Standard full-size contracts (`NQ`, `ES`, `GC`, `CL`, `6E`) carry massive notional exposures ($200k–$400k+ per contract), making risk budgeting impossible for personal capital accounts. Production research restricts live candidate models to **CME Micro Contracts**.

```text
CME Standard Contract (e.g. NQ)      ──► Multiplier: $20.00 / pt (Notional: ~$400,000)
CME Micro Contract   (e.g. MNQ)     ──► Multiplier:  $2.00 / pt (Notional:  ~$40,000) [1/10th Size]
```

---

## 2. CME Micro Contract Specifications (Primary CME Group Authority)

| Contract Symbol | Underlying Benchmark | Exchange Division | Contract Multiplier | Minimum Price Fluctuation (Tick) | Dollar Value Per Tick | Settlement Type | Roll Cycle |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`MNQ`** | Nasdaq-100 Index | **CME** | **$2.00** $\times$ Index | 0.25 Index pts | **$0.50** | **Financial (Cash)** | Quarterly (H, M, U, Z) |
| **`MES`** | S&P 500 Index | **CME** | **$5.00** $\times$ Index | 0.25 Index pts | **$1.25** | **Financial (Cash)** | Quarterly (H, M, U, Z) |
| **`MGC`** | Gold (Troy Ounces) | **COMEX** | **10** Troy Ounces | $0.10 / troy oz | **$1.00** | **Physical Delivery\*** | Bi-Monthly (G, J, M, Q, V, Z) |
| **`MCL`** | WTI Crude Oil | **NYMEX** | **100** Barrels | $0.01 / barrel | **$1.00** | **Financial (Cash)** | Monthly (All 12 months) |
| **`M6E`** | Euro / US Dollar | **CME** | **12,500** EUR | $0.0001 / EUR | **$1.25** | **Physical Delivery\*** | Quarterly (H, M, U, Z) |

*\*Critical Operational Rule on Physically Delivered Contracts (`MGC`, `M6E`):* Retail accounts must **never** take physical delivery of commodities or foreign currency. ACASH enforces an automated roll or liquidation cutoff at least **3 business days prior to First Notice Date (FND)** or First Position Day.

---

## 3. Product Comparisons: CME Futures vs Retail OTC / CFDs

| Dimension | CME Exchange Micro Futures (`MNQ`, `MES`, `MGC`, `MCL`) | Retail Broker CFD / OTC (`NAS100`, `XAUUSD`, `USOIL`) |
| :--- | :--- | :--- |
| **Counterparty Risk** | Central Clearing House (CME Clearing). Zero broker credit risk. | Direct exposure to broker solvency (B-book market maker). |
| **Price Transparency** | Single centralized order book (CME Globex). Visible L2/L3 depth. | Synthetic price stream constructed by broker dealing desk. |
| **Spread Dynamics** | Tight exchange-traded tick spreads (e.g. 1 tick on `MES`/`MNQ`). | Arbitrary, unannounced spread expansion during news/volatility. |
| **Holding Costs** | Explicit risk-free rate implied in basis; zero overnight "swap fees". | Daily compounded financing / swap fees charged to trader. |
| **Regulatory Protections**| CFTC / NFA oversight; mandatory customer segregated funds. | Offshore regulations (CySEC, FSA, SVG) with minimal recourse. |

---

## 4. Contract Expiration & Rollover Protocol

Futures contracts expire on fixed calendar dates. To maintain uninterrupted time-series data and active positions:
1. **Quarterly Equity Roll Schedule:** Equity index micros (`MNQ`, `MES`) follow the March (H), June (M), September (U), December (Z) cycle.
2. **Rollover Trigger:** Positions must roll when open interest and volume on the lead contract shift to the next deferred month (typically the **second Thursday** of the contract expiration month).
3. **Continuous Synthetic Lineage:** Historical research manifests must document the exact stitching methodology (Panama back-adjustment, ratio splicing, or perpetual unadjusted series) to prevent artificial return jumps across roll dates.

---

## 5. Verification Ledger

- Specifications Verified: CME GROUP PRIMARY CONTRACT RULES
- Asset Class Coverage: Equity Indexes (`MNQ`, `MES`), Metals (`MGC`), Energy (`MCL`), Currencies (`M6E`)
- Settlement Firewalls: Physical delivery prevention protocols codified
- Sizing Discipline: Tied to point value multiplier ($2/pt, $5/pt, $1/tick)
