# ACASH Webull Securities (Thailand) Open API Feasibility Study R0

**Document:** `docs/ppds/WEBULL_OPEN_API_FEASIBILITY_R0.md`
**System Module:** Broker Integration & API Due Diligence
**Target Broker:** Webull Securities (Thailand) Co., Ltd.
**Stage:** R0 Technical Feasibility & Security Assessment
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 1, 3, 11

---

## 1. Executive Summary & Candidate Role

Webull Securities (Thailand) is a licensed broker-dealer regulated by the Securities and Exchange Commission (SEC) of Thailand. It is designated as the primary candidate broker for the **Equity Tactical / Sniper Trading Book** and the first potential API-native telemetry source for ACASH.

### Critical Safety Invariant
- **Zero Credentials in R0:** No live Webull API keys, secrets, or account numbers may be requested, stored, or utilized during R0.
- **Zero Order Endpoint Calls:** Testing order submission, modification, or cancellation endpoints is strictly prohibited.
- **Fail-Closed Security Gating:** Because official documentation has not yet conclusively proven that order-writing capability can be permanently disabled at the API key permission tier in the Webull Thailand developer portal, integration status is classified as:
  ```text
  WEBULL_READ_ONLY_INTEGRATION = BLOCKED_PENDING_SECURITY_DESIGN
  ```

---

## 2. Webull Open API Specification & Capabilities

Official primary documentation confirms that the Webull Open API suite provides:
1. **Account & Portfolio Telemetry:** Real-time account cash balance, purchasing power, net asset value (NAV), open positions, and margin status.
2. **Order & Trade Execution Data:** Real-time order status callbacks, historical order queries, and execution fill reports.
3. **Market Data Streaming:** High-frequency WebSocket feeds for real-time US quote quotes, Level 1 market data, and discrete candlestick bars.
4. **Historical Market Data:** Historical intraday and daily price series for backtesting and indicator initialization.
5. **Commercial Pricing:** Currently advertised with **zero developer or API maintenance fees**.

---

## 3. Technical Due-Diligence Checklist

| Due-Diligence Item | Technical Description | Preliminary Assessment | Research Status |
| :--- | :--- | :--- | :--- |
| **Legal / Regulated Entity** | Webull Securities (Thailand) Co., Ltd. (SEC Thailand licensed broker). | High institutional credibility under Thai jurisdiction. | **CONFIRMED** |
| **Authentication Protocol** | App Key + App Secret generating dynamic JWT/access tokens; HMAC-SHA256 request payload signing. | Standard financial-grade API security. | **CONFIRMED** |
| **Read-Only Key Permission** | Capability to generate an API key with `Account:Read` and `MarketData:Read` while omitting `Trading:Write`. | Crucial safety firewall. Must verify developer console UI options. | **UNRESOLVED** |
| **Multi-Factor Authentication (2FA)** | Trade PIN or TOTP required for high-risk actions / initial token exchange. | Required for account protection. | Pending verification |
| **Rate Limiting & Throttling** | REST endpoint limits (requests/second) and WebSocket connection limits. | Standard token-bucket throttling; requires backoff handler. | Detailed specs needed |
| **Idempotency & Order IDs** | Client order ID (`client_order_id`) support for duplicate submission protection. | Necessary for future execution safety. | API schema defined |
| **WebSocket Reconnect Semantics**| Automatic heartbeat ping/pong, session resumption, and missed message replay. | Necessary for uninterrupted telemetry. | Supported in SDK |
| **Simulation / Sandbox Mode** | Paper trading sandbox environment to test telemetry without capital risk. | Critical prerequisite before live credential issuance. | Under verification |

---

## 4. The Read-Only Credential Isolation Mandate

In ACASH, automated execution authority is strictly separated from decision support. To safely integrate Webull telemetry into PPDS:

```text
               ┌──────────────────────────────┐
               │ Webull Developer Console     │
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼───────────────┐
               │    Key Permission Selection  │
               └──────────────┬───────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
[ Read-Only Scopes ]                      [ Order-Writing Scopes ]
- Account Telemetry                       - Place Order
- Position Balances                       - Cancel / Replace Order
- Market Data Feeds                       - Transfer Cash
        │                                           │
        ▼                                           ▼
[ ALLOWED IN PPDS ]                       [ STRICTLY FORBIDDEN ]
- Zero trade capability                   - API key with write permission
- Hard security firewall                   cannot be loaded into ACASH
```

### Protocol:
If the Webull Thailand Open API portal requires issuing an omnipotent key that inherently bundles order-placement rights with account-reading rights, **ACASH will refuse to ingest the API key directly**. In that scenario, ACASH requires a local proxy / credential guard daemon that strips order capabilities before exposing telemetry to the application.

---

## 5. Preliminary Data Mapping to ACASH DTOs

Webull Open API JSON payloads map directly to proposed PPDS canonical data contracts:
- `v1/account/balance` $\longrightarrow$ `CashBalanceDTO` (THB cash, USD cash, buying power)
- `v1/account/positions` $\longrightarrow$ `PositionDTO` (symbol, quantity, average cost basis, market value)
- `v1/trade/orders` $\longrightarrow$ `OrderDTO` (order ID, state, submitted timestamp, limit price)
- `v1/trade/fills` $\longrightarrow$ `FillDTO` (fill ID, executed quantity, executed price, fee decomposition)

---

## 6. Verification Ledger

- Custodian Profile: WEBULL SECURITIES (THAILAND) COMPLETE
- Open API Scope: TRADING, ACCOUNT, MARKET DATA, WEBSOCKET
- Commercial Fee: $0.00 / FREE ADVERTISED
- Security Status: `BLOCKED_PENDING_SECURITY_DESIGN` (Read-only credential proof required)
