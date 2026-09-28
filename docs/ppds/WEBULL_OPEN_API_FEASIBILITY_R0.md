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

## 2. Webull Thailand Open API Architecture & Transport Layer

Based on official Webull Securities (Thailand) developer documentation (`developer.webull.co.th`, retrieved 2026-09-28), the API suite enforces discrete transport protocols:

1. **REST Request / Response Layer:**
   - Account balances, positions, historical order queries, and order management.
   - Standard official endpoint patterns:
     - `GET /trading/accounts/list` (Query accounts under credential)
     - `GET /trading/assets/balances/get` (Account cash balance & purchasing power)
     - `GET /trading/orders/historical-orders/list` (Historical order records)
     - `/trading/orders/...` (Order submission, cancellation, status)
   - *Query Horizon Constraint:* Historical order queries on specific endpoints are constrained to limited rolling windows (e.g. past 7 days where applicable). Consequently, OpenAPI telemetry alone is insufficient to reconstruct multi-year tax ledgers without statement ingestion.
2. **Trade Events Streaming Layer (gRPC Server-Streaming):**
   - Official Webull Thailand documentation implements order status callbacks and fill execution feeds via **server-streaming gRPC**, NOT WebSocket.
   - Requires gRPC client stub generation, proto contract alignment, and TLS channel management.
3. **Market Data Streaming Layer (WebSocket):**
   - High-frequency Level 1 quotes and discrete candlestick bar streams operate over WebSocket.
   - *Entitlement Boundary:* Official terms state that market-data subscriptions purchased in the Webull retail mobile/desktop app are independent from OpenAPI market-data permissions:
     ```text
     WEBULL_OPENAPI_MARKET_DATA_ENTITLEMENT = SEPARATE_SUBSCRIPTION_OR_PERMISSION_REQUIRED
     ```
4. **Commercial Pricing:** Currently advertised with **zero developer or API maintenance fees**.

---

## 3. Authentication, Token Lifecycle & Signature Specification

### 3.1 Individual Onboarding & Credential Generation
- **Prerequisite:** Individual applicant must already hold an active, verified Webull Thailand brokerage account.
- **Application Review:** Developer API access requires submission and approval of an application form.
- **Credential Issuance:** Approved developers generate an **App Key** and **App Secret** via the developer console, requiring multi-factor security verification (SMS OTP / transaction password).

### 3.2 Token Lifecycle & 2FA
- Official documentation designates the session credential as an **access Token** (not dynamic JWT).
- **Initial Production Token Authentication:** Requesting an access token in the production environment requires interactive **2FA verification** (e.g. SMS OTP / PIN), establishing an authenticated session.
- Tokens carry an explicit time-to-live (TTL) and must be refreshed before expiry.

### 3.3 Request Signing Algorithm
Payload signing is version- and endpoint-dependent:
```text
WEBULL_SIGNATURE_ALGORITHM = VERSION_OR_ENDPOINT_DEPENDENT
```
The client contract must parameterize:
- `signature_version`: Documented version identifier (e.g. v1, v2).
- `signature_algorithm`: Cryptographic hash mechanism (HMAC-SHA1 or HMAC-SHA256, depending on endpoint family and version).
- `timestamp`: Monotonic millisecond request timestamp.
- `nonce`: Unique UUID/random string per request.

---

## 4. Technical Due-Diligence Matrix

| Due-Diligence Item | Technical Specification (Primary Source) | R0 Assessment | Research Status |
| :--- | :--- | :--- | :--- |
| **Legal / Regulated Entity** | Webull Securities (Thailand) Co., Ltd. (SEC Thailand licensed broker). | High statutory regulatory standing under Thai law. | **CONFIRMED** |
| **Authentication Flow** | App Key + App Secret $\to$ Access Token (with initial production 2FA). | Standard financial-grade authentication. | **CONFIRMED** |
| **Signature Protocol** | Endpoint- and version-dependent signing (HMAC-SHA1 / HMAC-SHA256). | Parameterized signature engine required. | **CONFIRMED (VERSION_DEPENDENT)** |
| **Trade Event Transport** | Server-streaming **gRPC** for order callbacks and execution events. | Requires dedicated gRPC client implementation. | **CONFIRMED (gRPC)** |
| **Market Data Transport** | WebSocket for real-time quotes; separate entitlement required. | Independent from retail mobile app subscriptions. | **CONFIRMED (SEPARATE_ENTITLEMENT)** |
| **Historical Query Horizon**| Rolling window limitations on historical order endpoints (e.g. 7 days). | Cannot serve as sole source for historical tax ledger. | **CONFIRMED (LIMITED_HORIZON)** |
| **Broker-Side Read-Only Key**| Permission to generate key with `Trading:Write` permanently disabled. | **UNVERIFIED in official Thailand individual portal**. | **BLOCKED** |
| **UAT / Test Environment** | Dedicated test base endpoint with synthetic test data and isolated state. | Documented in official docs; not authorized for use. | **DOCUMENTED_NOT_AUTHORIZED** |

---

## 5. The Read-Only Credential Isolation Mandate & UAT Status

### 5.1 The Read-Only Security Gate
In ACASH, automated execution authority is strictly separated from decision support. To safely ingest Webull telemetry into PPDS:
- **Broker-Side Scopes:** The preferred safety control is a broker-side API key configuration where `Account:Read` and `MarketData:Read` are enabled while `Trading:Write` is hard-disabled.
- **Current Evidence:** Current public Thailand documentation indicates that individual API keys can reach trading endpoints after authorization. There is **no primary-source proof** that an individual retail key can be provisioned with broker-side order-writing capability permanently disabled:
  ```text
  WEBULL_BROKER_SIDE_READ_ONLY_KEY = NOT_PRIMARY_SOURCE_CONFIRMED
  WEBULL_READ_ONLY_INTEGRATION     = BLOCKED_PENDING_SECURITY_DESIGN
  ```
- **Local Proxy Boundary:** Researching a local proxy / credential guard daemon with strict HTTP GET allowlisting may be pursued as a future defense-in-depth measure, but:
  $$\text{LOCAL\_PROXY} \neq \text{BROKER\_SIDE\_READ\_ONLY\_PERMISSION}$$
  A local proxy cannot substitute for broker-level privilege isolation. No Webull credentials may be generated or ingested in R0.

### 5.2 UAT / Test Sandbox Environment
- Official documentation references a test/UAT environment with a dedicated base endpoint, test token behavior, and simulated order execution.
- **Classification:**
  ```text
  WEBULL_UAT_FEASIBILITY = DOCUMENTED_NOT_AUTHORIZED_FOR_USE
  ```
- Testing in UAT or production is strictly forbidden in R0. Zero credentials may be requested.

---

## 6. Verification Ledger

- Custodian Profile: WEBULL SECURITIES (THAILAND) COMPLETE
- Transport Protocols: REST (Query), gRPC (Trade Events), WebSocket (Market Data)
- Token Model: ACCESS TOKEN (Initial Production 2FA Required; Not JWT)
- Signature Scheme: `WEBULL_SIGNATURE_ALGORITHM = VERSION_OR_ENDPOINT_DEPENDENT`
- Market Data Entitlement: `SEPARATE_SUBSCRIPTION_OR_PERMISSION_REQUIRED`
- Historical Horizon: RESTRICTED ROLLING WINDOWS (Requires Statement Ingestion)
- Broker-Side Read-Only Key: `NOT_PRIMARY_SOURCE_CONFIRMED`
- Integration Status: `BLOCKED_PENDING_SECURITY_DESIGN`
- UAT Status: `DOCUMENTED_NOT_AUTHORIZED_FOR_USE`
