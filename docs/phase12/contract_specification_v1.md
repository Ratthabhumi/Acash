# Phase 12 Canonical Contract Specification v1.0
## Multi-Venue Execution Topology, MetaTrader 5 (MT5) Adapter & TradingView Integration

> **Document:** `docs/phase12/contract_specification_v1.md`  
> **Status:** FINAL DRAFT — PENDING FINAL AUDIT APPROVAL  
> **Baseline Commit:** `959d771` (`HEAD == origin/main`, 1,020 collected: 1,017 passed, 3 skipped, 0 failed, MyPy clean)  
> **Frozen Baselines:** Phase 7 (Frozen), Phase 8 (`e6f1d04`), Phase 8.5 (`9ce1365`), Phase 9 (`6bd40d8`), Phase 10 (`3955bf6`), Phase 11 (`092a2b1`)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Sovereign Authority Separation)

---

## 1. Scope, Mission & Non-Goals

### 1.1 Scope & Mission
Phase 12 expands the sovereign execution framework established in Phase 7 by implementing:
1. **Multi-Venue Execution Topology:** Decoupled broker routing infrastructure operating under the Phase 7 `ExecutionCoordinator`.
2. **MetaTrader 5 (MT5) Execution Adapter (#1):** High-fidelity, local IPC bridge communicating directly with official MetaTrader 5 Windows terminal instances.
3. **Immutable Contract Normalization (`BrokerSymbolSpec`):** Versioned broker instrument specifications, deterministic Decimal volume quantization with positive preconditions, tick-grid price alignment, and stop-level enforcement.
4. **Authoritative 6-Dimensional Reconciliation Engine:** Shadow ledger reconciliation across Balances, Equity, Margin, Positions, Resting Orders, and Historical Deals, emitting evidence for `ExecutionCoordinator` lifecycle governance.
5. **TradingView Decoupled Auxiliary Ingress & Visualization Gateway:** Native HTTP POST ingress with IP allowlisting, payload token validation, deterministic event canonicalization, replay/freshness decoupling, and read-only charting telemetry.

### 1.2 Explicit Non-Goals
- **No Direct Strategy Execution from TradingView:** TradingView alerts are strictly candidate proposals; they never bypass research, tournament, risk, or execution admission gates.
- **No Critical Execution Dependency on Third-Party Webhooks:** The core ACASH execution pipeline is self-contained and local-first ($\text{ACASH} \to \text{MT5} \to \text{Broker}$).
- **No Direct Broker Sockets in Upstream Layers:** Phase 8 (Portfolio), Phase 8.5 (Research), Phase 9 (Risk), Phase 10 (Supervisor), and Phase 11 (Monitoring) maintain **ZERO direct broker sockets**.
- **No Live Capital Trading Wire in Phase 12:** Phase 12 targets paper/demo accounts and simulated execution environments; live capital authorization remains hard-locked ($CapitalAuthorityUSD \equiv 0.00$).

---

## 2. Sovereign Authority Hierarchy

$$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Monitoring\ (11)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Supervisor\ (10)} \neq \mathbf{Risk\ (9)} \neq \mathbf{ExecutionCoordinator\ (7)} \neq \mathbf{BrokerAdapter\ (12)} \neq \mathbf{BrokerServer}}$$

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ACASH SOVEREIGN AUTHORITY MATRIX                               │
├───────────────────────────┬─────────────────────────────────┬───────────────────────────────┤
│ System Component          │ Sovereign Authority             │ Strictly Prohibited           │
├───────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ ExecutionCoordinator (7)  │ State Machine Authority         │ Direct Socket I/O, Wire Proto │
│                           │ (`transition_order`, Ledger)    │ Strategy Generation           │
├───────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ MT5BrokerAdapter (12)     │ Command Sink + Observation Source│ Order State Mutation,         │
│                           │ (Translates MT5 reality to DTOs)│ Risk Sizing, Capital Decision │
├───────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ ReconciliationEngine (12) │ Evidence Emission Authority     │ Direct State Mutation         │
│                           │ (Emits ReconciliationEvidence)  │ (`transition_order` bypass)   │
├───────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ TradingView Ingress (12)  │ Auxiliary Proposal Buffer       │ Order Submission, Risk Veto,  │
│                           │ (IP & Token Verified Ingress)   │ Execution Authority ($0.00)   │
├───────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ Broker Trade Server (Ext) │ Final External Matching Reality │ Internal State Governance     │
└───────────────────────────┴─────────────────────────────────┴───────────────────────────────┘
```

### Invariant: BrokerAdapter $\neq$ StateAuthority
$$\boxed{\mathbf{BrokerAdapter} \neq \mathbf{StateAuthority} \quad \land \quad \mathbf{ReconciliationEngine} \neq \mathbf{StateAuthority}}$$
- The broker adapter and reconciliation engine **never** mutate `OrderLifecycleState` or position tables directly.
- The adapter communicates observations strictly by emitting canonical `BrokerRawEvent` records to the `ExecutionCoordinator`.
- The reconciliation engine emits `ReconciliationEvidence` records.
- `ExecutionCoordinator` / `transition_order()` in Phase 7 remains the **sole state transition authority**.

---

## 3. Canonical Domain Objects & Data Transfer Objects (DTOs)

```python
class MT5OrderType(str, Enum):
    """Canonical MT5 order types supported by adapter."""
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"
    BUY_STOP_LIMIT = "BUY_STOP_LIMIT"
    SELL_STOP_LIMIT = "SELL_STOP_LIMIT"


class MT5FillingMode(str, Enum):
    """Canonical filling mode policies."""
    ORDER_FILLING_FOK = "ORDER_FILLING_FOK"
    ORDER_FILLING_IOC = "ORDER_FILLING_IOC"
    ORDER_FILLING_RETURN = "ORDER_FILLING_RETURN"
    ORDER_FILLING_BOC = "ORDER_FILLING_BOC"


class MT5ExecutionPolicy(str, Enum):
    """ACASH intent execution policy."""
    DEFAULT = "DEFAULT"
    TAKER_SWEEP = "TAKER_SWEEP"
    PASSIVE_MAKER = "PASSIVE_MAKER"


class BrokerSymbolSpec(BaseModel):
    """Immutable, versioned specification of broker-side instrument mechanics."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_symbol: str
    broker_symbol: str
    contract_size: Decimal              # e.g. Decimal("100000") for EURUSD, Decimal("1") for BTCUSD
    volume_min: Decimal                 # e.g. Decimal("0.01")
    volume_max: Decimal                 # e.g. Decimal("100.00")
    volume_step: Decimal                # e.g. Decimal("0.01")
    digits: int                         # Price decimal precision (e.g. 5)
    point_size: Decimal                 # e.g. Decimal("0.00001")
    tick_size: Decimal                  # Minimum price movement (e.g. Decimal("0.00001"))
    trade_execution_mode: str           # 'MARKET', 'INSTANT', 'REQUEST', 'EXCHANGE'
    allowed_filling_flags: Tuple[str, ...] # ('SYMBOL_FILLING_FOK', 'SYMBOL_FILLING_IOC', 'SYMBOL_FILLING_BOC')
    allowed_order_modes: Tuple[str, ...]   # ('SYMBOL_ORDER_LIMIT', 'SYMBOL_ORDER_STOP_LIMIT', etc.)
    stops_level_points: int             # Minimum distance for SL/TP and pending orders in points
    margin_currency: str
    profit_currency: str
    spec_digest: str                   # SHA-256 of canonical fields


class MT5DealReality(BaseModel):
    """Authoritative fill observation corresponding to an MT5 deal ticket."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    deal_ticket: int
    order_ticket: int
    position_ticket: int
    symbol: str
    deal_type: str                     # 'DEAL_TYPE_BUY', 'DEAL_TYPE_SELL'
    volume: Decimal
    price: Decimal
    commission: Decimal
    fee: Decimal
    swap: Decimal
    profit: Decimal
    deal_time_utc: datetime
    comment: str
    magic: int


class MT5OrderReality(BaseModel):
    """Authoritative resting/historical order observation."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    order_ticket: int
    position_ticket: Optional[int]
    symbol: str
    order_type: MT5OrderType
    state: str                         # 'ORDER_STATE_PLACED', 'ORDER_STATE_FILLED', etc.
    volume_initial: Decimal
    volume_current: Decimal
    price_open: Decimal
    price_stoplimit: Optional[Decimal]
    sl: Decimal
    tp: Decimal
    time_setup_utc: datetime
    time_done_utc: Optional[datetime]
    magic: int
    comment: str


class MT5PositionReality(BaseModel):
    """Authoritative broker-side position snapshot."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    position_ticket: int
    symbol: str
    position_type: str                 # 'POSITION_TYPE_BUY', 'POSITION_TYPE_SELL'
    volume: Decimal
    price_open: Decimal
    price_current: Decimal
    sl: Decimal
    tp: Decimal
    swap: Decimal
    profit: Decimal
    magic: int
    comment: str
    time_open_utc: datetime
```

---

## 4. MT5 Entity Hierarchy & Multi-Deal Partial-Fill Lifecycle

MT5 strictly decouples requests from execution transactions and resulting exposures:

```
ACASH OrderIntent (intent_id, intent_digest)
        │
        ▼
MT5 Order / TradeRequest (order_ticket)
        │
        ├───────────────────────────────────────┐
        ▼                                       ▼
  MT5 Deal #1 (deal_ticket_1)             MT5 Deal #2 (deal_ticket_2)
  [Volume: 0.4 Lot, Price: 1.0850]        [Volume: 0.6 Lot, Price: 1.0851]
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                            ▼
                  Position State Snapshot
                 (position_ticket / symbol)
                            │
                            ▼
             ReconciliationEvidence vs ACASH
```

### 4.1 Multi-Deal Accumulation Semantics
When an `OrderIntent` generates $N \ge 1$ deals (e.g. sweeping multiple price levels or partial executions), the `ExecutionCoordinator` accumulates all linked deals into the `ExecutionManifest`:
$$\text{Realized VWAP} = \frac{\sum_{i=1}^N \text{volume}_i \cdot \text{price}_i}{\sum_{i=1}^N \text{volume}_i}$$
$$\text{Total Realized Commission} = \sum_{i=1}^N (\text{commission}_i + \text{fee}_i)$$

---

## 5. 9-Tuple Lineage & Nullability Specification

To prevent entity collisions across multi-account and multi-strategy deployments, every execution observation is bound to the immutable 9-tuple:
$$\boxed{(\text{broker\_id}, \text{account\_id}, \text{terminal\_instance\_id}, \text{strategy\_id}, \text{cycle\_id}, \text{intent\_id}, \text{mt5\_order\_ticket}, \text{mt5\_deal\_ticket}, \text{position\_id})}$$

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                       9-TUPLE LIFECYCLE & NULLABILITY SPECIFICATION                         │
├──────────────────────────┬───────────────────┬─────────────────────────┬────────────────────┤
│ Lifecycle Stage          │ `mt5_order_ticket`│ `mt5_deal_ticket`       │ `position_id`      │
├──────────────────────────┼───────────────────┼─────────────────────────┼────────────────────┤
│ 1. Pre-Submission        │ `None`            │ `None`                  │ `None` / `pos_ref*`│
│ 2. Order Placed/Resting  │ `int` (ticket > 0)│ `None`                  │ `None` / `pos_ref*`│
│ 3. Single Complete Fill  │ `int` (ticket > 0)│ `(int,)` (single deal)  │ `int` (pos_ticket) │
│ 4. Partial / Multi-Fill  │ `int` (ticket > 0)│ `(int, int, ...)` (>=1) │ `int` (pos_ticket) │
│ 5. Position Close/Reduce │ `int` (ticket > 0)│ `(int, ...)` (close deal│ `int` (pos_target) │
│ 6. Order Rejected/Expired│ `int` or `None`   │ `None`                  │ `None`             │
└──────────────────────────┴───────────────────┴─────────────────────────┴────────────────────┘
* Note: When an order is intentionally closing or reducing an existing position, position_id contains
  the target position reference; for new opening positions, position_id is None until first deal creation.
```

---

## 6. BrokerRawEvent Contract & `order_send()` Observation Semantics

$$\boxed{\mathbf{order\_send()\ response} \equiv \text{Transport / Request-Processing Observation} \neq \mathbf{Terminal\ Lifecycle\ Event}}$$

```
mt5.order_send() Result (Observation)
           │
           ▼
BrokerRawEvent (SUBMISSION_ACKNOWLEDGED / FILL_OBSERVED / REJECT_OBSERVED)
           │
           ▼
ExecutionCoordinator.apply()  [Phase 7 Engine]
           │
           ▼
transition_order()  [SOLE State Machine Authority]
```

### 6.1 Return Code Mapping & Requote Semantics
| MT5 Retcode | Meaning | Emitted `BrokerRawEvent` | Coordinator Action |
| :--- | :--- | :--- | :--- |
| `10009` (`TRADE_RETCODE_DONE`) | Server processed request | `SUBMISSION_ACKNOWLEDGED` / `FILL_OBSERVED` | Reconcile deals $\to$ `FILLED` |
| `10010` (`TRADE_RETCODE_DONE_PARTIAL`)| Partial execution | `PARTIAL_FILL_OBSERVED` | Reconcile deal $\to$ `PARTIALLY_FILLED` |
| `10004` (`TRADE_RETCODE_REQUOTE`) | Price moved | `REJECT_OBSERVED` (`REQUOTE_OBSERVED`) | **Request rejected; ZERO realized execution drag recorded without deal** |
| `10006` (`TRADE_RETCODE_REJECT`) | Server rejected request | `REJECT_OBSERVED` | Transition to `REJECTED` |
| `10018` (`TRADE_RETCODE_MARKET_CLOSED`)| Market is closed | `REJECT_OBSERVED` | Transition to `REJECTED` |
| `10027` (`TRADE_RETCODE_AUTOTRADING_DISABLED`)| Terminal autotrading off | `CONNECTION_LOST` / `UNHEALTHY` | Block cycle pulse |
| `10031` (`TRADE_RETCODE_CONNECTION`) | Connection lost | `CONNECTION_LOST` | Transition in-flight orders to `UNKNOWN` |

---

## 7. MQL5 Canonical Filling-Mode Resolution Contract

Selecting a filling mode evaluates official MQL5 trade execution rules across 4 dimensions:
$$\text{Filling Mode} = f(\text{Symbol Trade Execution Mode}, \text{Symbol Filling Flags}, \text{Order Type}, \text{Execution Policy})$$

### 7.1 MQL5 Matrix Specification
```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            MT5 FILLING MODE RESOLUTION MATRIX                               │
├────────────────────────────┬─────────────────────────────┬──────────────────────────────────┤
│ Symbol Execution Mode      │ Order Category & Type       │ MQL5 Allowed Filling Modes       │
├────────────────────────────┼─────────────────────────────┼──────────────────────────────────┤
│ Any Execution Mode         │ Generic Pending Orders      │ `ORDER_FILLING_RETURN` strictly  │
│                            │ (Limit, Stop, Stop-Limit)   │ (*Standard pending baseline)     │
├────────────────────────────┼─────────────────────────────┼──────────────────────────────────┤
│ Exchange Execution Mode    │ Passive Maker Limit Orders  │ `ORDER_FILLING_BOC`              │
│ (with `SYMBOL_FILLING_BOC`)│ (`BUY/SELL_LIMIT`,          │ (*Explicit Maker-only exception) │
│                            │  `BUY/SELL_STOP_LIMIT`)     │                                  │
├────────────────────────────┼─────────────────────────────┼──────────────────────────────────┤
│ `SYMBOL_TRADE_EXEC_MARKET` │ Market Orders (`BUY`/`SELL`)│ `ORDER_FILLING_FOK` (if flag),   │
│ (Market Execution)         │                             │ `ORDER_FILLING_IOC` (if flag)    │
│                            │                             │ (*RETURN strictly forbidden)     │
├────────────────────────────┼─────────────────────────────┼──────────────────────────────────┤
│ `SYMBOL_TRADE_EXEC_REQUEST`│ Market Orders (`BUY`/`SELL`)│ `ORDER_FILLING_RETURN`, `_FOK`,  │
│ / `INSTANT`                │                             │ or `_IOC` (all available)        │
├────────────────────────────┼─────────────────────────────┼──────────────────────────────────┤
│ `SYMBOL_TRADE_EXEC_EXCHANGE`│ Market Orders (`BUY`/`SELL`)│ `ORDER_FILLING_RETURN` (always), │
│ (Exchange Execution)       │                             │ `_FOK` (if flag), `_IOC` (if flag│
└────────────────────────────┴─────────────────────────────┴──────────────────────────────────┘
```

### 7.2 Deterministic Resolution Algorithm
```python
def resolve_filling_mode(
    symbol_spec: BrokerSymbolSpec,
    order_type: MT5OrderType,
    execution_policy: MT5ExecutionPolicy,
    limit_price: Optional[Decimal] = None,
    trigger_price: Optional[Decimal] = None,
    current_bid: Optional[Decimal] = None,
    current_ask: Optional[Decimal] = None,
) -> MT5FillingMode:
    """Deterministic, fail-closed filling mode resolution algorithm."""
    # 1. Explicit Passive Maker Path (BOC Exception)
    if execution_policy == MT5ExecutionPolicy.PASSIVE_MAKER:
        if order_type not in {
            MT5OrderType.BUY_LIMIT,
            MT5OrderType.SELL_LIMIT,
            MT5OrderType.BUY_STOP_LIMIT,
            MT5OrderType.SELL_STOP_LIMIT,
        }:
            raise DataContractError("BOC_INVALID_FOR_ORDER_TYPE")
        if symbol_spec.trade_execution_mode != "EXCHANGE":
            raise DataContractError("BOC_REQUIRES_EXCHANGE_EXECUTION_MODE")
        if "SYMBOL_FILLING_BOC" not in symbol_spec.allowed_filling_flags:
            raise DataContractError("SYMBOL_DOES_NOT_SUPPORT_BOC")
        if order_type in {MT5OrderType.BUY_LIMIT, MT5OrderType.SELL_LIMIT}:
            if "SYMBOL_ORDER_LIMIT" not in symbol_spec.allowed_order_modes:
                raise DataContractError("SYMBOL_ORDER_LIMIT_NOT_PERMITTED")
        if order_type in {MT5OrderType.BUY_STOP_LIMIT, MT5OrderType.SELL_STOP_LIMIT}:
            if "SYMBOL_ORDER_STOP_LIMIT" not in symbol_spec.allowed_order_modes:
                raise DataContractError("SYMBOL_ORDER_STOP_LIMIT_NOT_PERMITTED")

        # Price-side passive verification (MQL5 DOM Rule)
        if current_bid is None or current_ask is None:
            raise DataContractError("BOC_PRICE_CHECK_MISSING_MARKET_QUOTES")

        if order_type == MT5OrderType.BUY_LIMIT:
            if limit_price is None or limit_price >= current_ask:
                raise DataContractError("BOC_PRICE_NOT_PASSIVE_BUY_LIMIT")
        elif order_type == MT5OrderType.SELL_LIMIT:
            if limit_price is None or limit_price <= current_bid:
                raise DataContractError("BOC_PRICE_NOT_PASSIVE_SELL_LIMIT")
        elif order_type == MT5OrderType.BUY_STOP_LIMIT:
            if trigger_price is None or limit_price is None:
                raise DataContractError("BOC_STOP_LIMIT_MISSING_PRICES")
            if trigger_price <= current_ask or limit_price >= trigger_price:
                raise DataContractError("BOC_PRICE_NOT_PASSIVE_BUY_STOP_LIMIT")
        elif order_type == MT5OrderType.SELL_STOP_LIMIT:
            if trigger_price is None or limit_price is None:
                raise DataContractError("BOC_STOP_LIMIT_MISSING_PRICES")
            if trigger_price >= current_bid or limit_price <= trigger_price:
                raise DataContractError("BOC_PRICE_NOT_PASSIVE_SELL_STOP_LIMIT")

        return MT5FillingMode.ORDER_FILLING_BOC

    # 2. Generic Pending Orders Path (Universal Standard)
    if order_type in {
        MT5OrderType.BUY_LIMIT,
        MT5OrderType.SELL_LIMIT,
        MT5OrderType.BUY_STOP,
        MT5OrderType.SELL_STOP,
        MT5OrderType.BUY_STOP_LIMIT,
        MT5OrderType.SELL_STOP_LIMIT,
    }:
        return MT5FillingMode.ORDER_FILLING_RETURN

    # 3. Market Orders Path (BUY, SELL)
    if order_type in {MT5OrderType.BUY, MT5OrderType.SELL}:
        mode = symbol_spec.trade_execution_mode
        if mode in {"REQUEST", "INSTANT"}:
            if execution_policy == MT5ExecutionPolicy.TAKER_SWEEP:
                return MT5FillingMode.ORDER_FILLING_IOC
            return MT5FillingMode.ORDER_FILLING_RETURN

        if mode == "MARKET":
            # RETURN is strictly forbidden under MARKET execution
            if execution_policy == MT5ExecutionPolicy.TAKER_SWEEP and "SYMBOL_FILLING_IOC" in symbol_spec.allowed_filling_flags:
                return MT5FillingMode.ORDER_FILLING_IOC
            if "SYMBOL_FILLING_FOK" in symbol_spec.allowed_filling_flags:
                return MT5FillingMode.ORDER_FILLING_FOK
            if "SYMBOL_FILLING_IOC" in symbol_spec.allowed_filling_flags:
                return MT5FillingMode.ORDER_FILLING_IOC
            raise DataContractError("NO_COMPATIBLE_MARKET_FILLING_MODE")

        if mode == "EXCHANGE":
            if execution_policy == MT5ExecutionPolicy.TAKER_SWEEP and "SYMBOL_FILLING_IOC" in symbol_spec.allowed_filling_flags:
                return MT5FillingMode.ORDER_FILLING_IOC
            return MT5FillingMode.ORDER_FILLING_RETURN

    raise DataContractError(f"UNRESOLVABLE_FILLING_MODE: order_type={order_type}, mode={symbol_spec.trade_execution_mode}")
```

---

## 8. Deterministic Decimal Unit, Volume & Price Normalization Contract

### 8.1 Input Sizing Semantics & Lot Quantization
- **Strict Precondition:** `target_units: Decimal` represents the desired base asset quantity (e.g. `Decimal("100000")` EUR for EURUSD, `Decimal("1.5")` BTC for BTCUSD) and **MUST be strictly positive** ($\text{target\_units} > 0$).
  - If $\text{target\_units} \le 0 \implies$ raise `DataContractError("TARGET_UNITS_MUST_BE_POSITIVE")`.
- **Lot Sizing Conversion:**
  $$\text{raw\_lots} = \frac{\text{target\_units}}{\text{spec.contract\_size}}$$
- **Deterministic Step Quantization:**
  With the strict invariant $\text{raw\_lots} > 0$, Python Decimal `ROUND_DOWN` (truncation towards zero) matches mathematical $\lfloor x \rfloor$ exactly:
  $$\text{steps} = \left\lfloor \frac{\text{raw\_lots}}{\text{spec.volume\_step}} \right\rfloor \quad (\text{via Decimal } \texttt{ROUND\_DOWN})$$
  $$\text{quantized\_lots} = \text{steps} \cdot \text{spec.volume\_step}$$
- **Fail-Closed Boundary Invariants:**
  - If $\text{quantized\_lots} < \text{spec.volume\_min} \implies$ raise `DataContractError("VOLUME_BELOW_MINIMUM")`.
  - If $\text{quantized\_lots} > \text{spec.volume\_max} \implies$ raise `DataContractError("VOLUME_ABOVE_MAXIMUM")`.
  - If $(\text{quantized\_lots} \pmod{\text{spec.volume\_step}}) \neq 0 \implies$ raise `DataContractError("VOLUME_STEP_MISMATCH")`.

### 8.2 Deterministic Price & Tick-Grid Quantization Pipeline
$$\boxed{\mathbf{Price\ Normalization} \neq \mathbf{Passivity\ Validation}}$$
Price normalization aligns raw price inputs to discrete broker tick boundaries, but **normalization does not guarantee passivity**. A normalized price can still cross the market spread and violate BOC policies.

Execution normalization follows a strict 5-stage sequential pipeline:
```
Raw Input Price
      │
      ▼
1. Tick-Grid Snapping: ticks = quantize(raw_price / spec.tick_size)
      │
      ▼
2. Side-Aware Directional Rounding:
   - BUY_LIMIT  -> Decimal ROUND_FLOOR   (downwards into resting DOM)
   - SELL_LIMIT -> Decimal ROUND_CEILING (upwards into resting DOM)
   - BUY_STOP   -> Decimal ROUND_CEILING
   - SELL_STOP  -> Decimal ROUND_FLOOR
      │
      ▼
3. Stop-Level Distance Validation:
   - Verify |order_price - market_price| / spec.point_size >= spec.stops_level_points
   - If closer -> raise DataContractError("STOP_LEVEL_VIOLATION")
      │
      ▼
4. Market-Reference Spread Validation (prevents immediate taker fill)
      │
      ▼
5. BOC Passive Invariant Validation:
   - BUY_LIMIT: limit_price < current_ask
   - SELL_LIMIT: limit_price > current_bid
   - BUY_STOP_LIMIT: trigger_price > current_ask AND limit_price < trigger_price
   - SELL_STOP_LIMIT: trigger_price < current_bid AND limit_price > trigger_price
   - If any condition fails -> raise DataContractError("BOC_PRICE_NOT_PASSIVE")
```

---

## 9. Non-Cryptographic Magic Numbers vs Tier-1 Cryptographic Lineage

$$\boxed{\mathbf{Tier\ 1:\ Canonical\ SHA-256\ Digest} \equiv \mathbf{Cryptographic\ Lineage\ Authority}}$$
$$\boxed{\mathbf{MT5\ Magic\ Number} \equiv \mathbf{Non-Authoritative\ Subsystem\ Routing\ Namespace}}$$
$$\boxed{\mathbf{MT5\ Comment} \equiv \mathbf{Transport\ Correlation\ Metadata\ Only}}$$

- `magic` (32-bit uint): Routing namespace partition inside the local MT5 terminal.
- `comment` (string, max 31 chars): `intent_digest[:16]` + sequence ID for human inspection.
- Collisions or truncations in MT5 magic/comment fields do **not** compromise ACASH authorization or cryptographic state integrity.

---

## 10. Security & Windows DPAPI Operational Identity Architecture

- **Windows DPAPI Vault Scope:**
  - Credentials (`login`, `password`, `server`, `terminal_path`) are encrypted via **Windows DPAPI** (`CurrentUser` scope) and saved strictly at `$env:USERPROFILE\.acash\mt5_credentials.dpapi`.
  - **Identity Triad Requirement:**
    $$\boxed{\text{Credential Owner Identity} \equiv \text{Adapter Runtime Identity} \equiv \text{Terminal Process Owner}}$$
  - **Fail-Closed Decryption:** If DPAPI decryption fails (e.g. running under unauthorized service context), startup halts immediately with `DataContractError("CREDENTIAL_VAULT_DECRYPTION_FAILED")`.
- **Zero Plaintext Leakage:**
  - `BrokerCredentials` always emits `********` in `__repr__` and `__str__`. Plaintext secrets never appear in exceptions, logs, or git commits.

---

## 11. Multi-Account Isolation & Terminal Process Topology

- Multiple MT5 terminals run concurrently via distinct file system paths (`terminal_path`) and port configurations.
- Each account binds to an isolated `ExecutionCoordinator` instance keyed by `(broker_id, account_id)`.
- **Cross-Account Lockout:** An adapter instance bound to `Account A` is strictly prohibited from executing commands or querying status on `Account B`.

---

## 12. Fail-Closed Resilience & Authoritative 6-Dimensional Reconciliation Loop

### 12.1 Disconnect & Unknown State Handling
- If `mt5.terminal_info().connected == False` or IPC socket times out:
  1. In-flight orders immediately transition to `OrderLifecycleState.UNKNOWN`.
  2. Adapter Health transitions to `UNHEALTHY`.
  3. All future cycle pulses are blocked until terminal reconnection.
  4. Mandatory **6-Dimensional Reconciliation** must succeed before restoring normal operations.

### 12.2 6-Dimensional Reconciliation Contract
$$\text{Reconciliation} = (\text{Balance}, \text{Equity}, \text{Margin}, \text{Positions}, \text{Resting Orders}, \text{Historical Deals})$$
- The reconciliation engine compares broker reality against the ACASH shadow ledger and produces an immutable `ReconciliationEvidence` record.
- **Authority Discipline:** The reconciliation engine **never** mutates state machine tables directly; it delivers evidence to `ExecutionCoordinator.apply_reconciliation()`, which performs authoritative lifecycle reconciliation.
- If any discrepancy exceeds configured numeric tolerance thresholds, `ExecutionCoordinator` halts trading immediately with `MT5ReconciliationError`.

---

## 13. TradingView Native Ingress, Replay Decoupling & $0.00 Capital Boundary

### 13.1 Native Webhook Ingress Authentication Protocol
TradingView webhook dispatch uses standard HTTP POST containing alert text in the body without arbitrary custom header injection. Authentication and ingress integrity are enforced via a defense-in-depth hierarchy:
1. **Transport Security:** Mandatory TLS/HTTPS encryption (`https://...`).
2. **Origin IP Allowlisting:** Ingress filters incoming TCP connections against official TradingView source IP ranges (`52.89.214.238`, `34.212.75.30`, `54.218.53.128`, `52.32.178.7`). Non-allowlisted connections are dropped with `403 Forbidden`.
3. **Payload Token & Dedicated Ingress Path:** Webhooks include a pre-shared strategy authentication token embedded in the JSON payload (`"passphrase": "..."`) or via a dedicated webhook path (`/api/v1/ingress/tv/{secret_webhook_token}`). Custom outbound HTTP headers (such as `X-TradingView-Signature`) are **strictly not assumed**.
4. **Server Certificate Verification:** TradingView verifies the recipient server's TLS certificate.

### 13.2 Deterministic Event Identity & Idempotent Ingress Pipeline
TradingView documentation specifies that if an endpoint returns a `5xx` error (excluding `504`), the server automatically retries sending the alert after **5 seconds**, up to **4 total attempts**.

To accommodate legitimate retries without allowing duplicate processing, ACASH enforces a deterministic canonical identity specification:
- **Event Identity Specification:**
  - `strategy_id`: Canonical strategy identifier string.
  - `event_timestamp`: UTC ISO-8601 string (`YYYY-MM-DDTHH:MM:SS.ffffffZ`) representing the exact alert trigger timestamp.
  - `bar_timestamp`: UTC ISO-8601 string representing the bar open/close timestamp.
  - `nonce`: **PRODUCER-SUPPLIED UNIQUE STRING**. The producer MUST preserve the identical nonce across retransmissions of the same logical alert. Receiver-generated nonces are **strictly forbidden** for event identity.
- **Canonical Serialization & Event ID Derivation:**
  $$\text{canonical\_form} = \text{strategy\_id} + \text{"|"} + \text{event\_timestamp} + \text{"|"} + \text{bar\_timestamp} + \text{"|"} + \text{nonce}$$
  $$\text{event\_id} = \text{SHA256}(\text{UTF8}(\text{canonical\_form}))$$

### 13.3 Sequential Ingress Pipeline Ordering
$$\boxed{\text{Receive} \longrightarrow \text{IP/Token Auth} \longrightarrow \text{Parse} \longrightarrow \text{Canonical event\_id} \longrightarrow \mathbf{Idempotency\ Lookup} \longrightarrow \mathbf{Freshness\ Validation} \longrightarrow \text{Candidate Signal}}$$

1. **Transport & IP Allowlist Validation:** Reject unauthorized source IPs (`403 Forbidden`).
2. **Payload Token Validation:** Verify pre-shared passphrase (`401 Unauthorized`).
3. **Canonical Event ID Derivation:** Calculate deterministic `event_id`.
4. **Idempotency Lookup (Executed PRE-Freshness):**
   - Query durable disk-backed receipt ledger (with bounded in-memory LRU cache acceleration) for `event_id`.
   - **Durable Persistence Invariant:** Idempotency receipts MUST survive process crashes and coordinator restarts. In-memory-only cache implementations that lose idempotency history on restart are strictly prohibited.
   - If `event_id` was previously processed successfully $\implies$ **Return HTTP 200 Idempotent ACK** (`status="IDEMPOTENT_ACK_DUPLICATE_DROPPED"`) without generating duplicate candidate signals.
5. **Freshness Validation (For New Events Only):**
   - Evaluate $\text{received\_at} - \text{event\_timestamp} \le T_{\text{max}} = 60\text{s}$.
   - If $\text{age} > 60\text{s} \implies$ reject with `400 Bad Request` (`TRADINGVIEW_STALE_PAYLOAD`).
6. **Candidate Signal Emission:**
   - Emit `TradingViewCandidateSignal` with **0.00 USD Capital Authority**.

### 13.4 Ingress Synchronous Response SLA & Asynchronous Queue Isolation
- **Documented TradingView Timeout Window:** Official TradingView documentation states that if webhook processing exceeds **approximately 3 seconds**, the request is cancelled / aborted on the sender side.
- **Strict Prohibition of Synchronous Pipeline Execution:**
  The synchronous webhook HTTP request thread **MUST NEVER** execute:
  $$\text{Webhook Request Thread} \quad \centernot\longrightarrow \quad \{\text{Research (8.5)}, \text{Validation (8.5)}, \text{Tournament (8)}, \text{Risk (9)}, \text{MT5 Execution (12)}\}$$
- **Fast-ACK + Durable Enqueue Pattern:**
  The synchronous request path is strictly constrained to:
  $$\text{Receive} \to \text{Auth} \to \text{Parse} \to \text{Canonical ID} \to \text{Idempotency Lookup} \to \text{Freshness} \to \text{Durable Enqueue} \to \text{HTTP 200 Fast-ACK}$$
- **ACASH Internal Ingress SLA:** Ingress synchronous processing must complete with target latency $t_{\text{resp}} < 50\text{ms}$ (and hard internal timeout at $1500\text{ms}$). This internal performance SLA ensures deterministic delivery completion well before TradingView's ~3-second request abort threshold. All econometric research, tournament evaluation, risk gating, and broker routing occur strictly asynchronously on downstream worker cycles.

---

## 14. Deterministic Error Taxonomy

| Error Code | Exception Class | Fail-Closed Trigger |
| :--- | :--- | :--- |
| `CREDENTIAL_VAULT_DECRYPTION_FAILED` | `BrokerAdapterError` | DPAPI decryption failure on startup |
| `TERMINAL_NOT_CONNECTED` | `MT5ConnectionError` | MT5 IPC socket disconnect |
| `NO_COMPATIBLE_FILLING_MODE` | `DataContractError` | Incompatible filling mode resolution |
| `BOC_PRICE_NOT_PASSIVE` | `DataContractError` | BOC limit/stop-limit price crosses market spread |
| `TARGET_UNITS_MUST_BE_POSITIVE` | `DataContractError` | Requested units are <= 0 |
| `VOLUME_BELOW_MINIMUM` | `DataContractError` | Sized volume is below broker symbol `volume_min` |
| `VOLUME_ABOVE_MAXIMUM` | `DataContractError` | Sized volume is above broker symbol `volume_max` |
| `VOLUME_STEP_MISMATCH` | `DataContractError` | Sized volume is not an integer multiple of `volume_step` |
| `STOP_LEVEL_VIOLATION` | `DataContractError` | Order price is closer than `stops_level_points` from quote |
| `RECONCILIATION_STATE_MISMATCH` | `MT5ReconciliationError` | Internal shadow ledger deviates from broker reality |
| `TRADINGVIEW_AUTH_FAILED` | `TradingViewIngressError` | IP not allowlisted or passphrase invalid |
| `TRADINGVIEW_STALE_PAYLOAD` | `TradingViewIngressError` | Webhook alert timestamp older than 60s window |

---

## 15. Explicit Prohibitions

1. **NO Direct State Mutation:** The broker adapter and reconciliation engine shall NEVER call `transition_order()` directly.
2. **NO Synthetic Fills:** The adapter shall NEVER manufacture synthetic fills on timeout or connection loss.
3. **NO Execution via TradingView:** TradingView shall NEVER be placed in the critical execution chain ($\text{ACASH} \to \text{TradingView} \to \text{MT5} \to \text{Broker}$ is strictly prohibited).
4. **NO Market RETURN Orders:** `ORDER_FILLING_RETURN` shall NEVER be submitted for market orders under `SYMBOL_TRADE_EXECUTION_MARKET`.
5. **NO Aggressive BOC Orders:** `ORDER_FILLING_BOC` shall NEVER be submitted with prices that cross or touch the prevailing market quote.
6. **NO Plaintext Secrets:** Passwords and keys shall NEVER be serialized or logged in plaintext.
7. **NO Silent Fallbacks:** Ambiguous or failing execution states shall NEVER use default or fabricated responses.
8. **NO Synthetic Drag on Requotes:** Retcode 10004 REQUOTE shall NEVER generate execution drag records without confirmed deal evidence.
9. **NO Synchronous Strategy Execution in Webhook:** Webhook ingress handlers shall NEVER synchronously execute research, risk, or execution pipelines.

---

## 16. Proposed Implementation Slices

```
Slice 1: MT5 Domain Schemas, Enums & Broker Mapping (BMAP-MT5)
   │
   ▼
Slice 2: Symbol Specification Normalizer (BrokerSymbolSpec) & Unit Sizer
   │
   ▼
Slice 3: MT5 Terminal Driver & IPC Transport Bridge (Windows Local)
   │
   ▼
Slice 4: MT5 Broker Adapter (MT5BrokerAdapter) & 6-D Reconciliation Engine
   │
   ▼
Slice 5: TradingView Ingress Gateway (IP/Token Sanitizer & Candidate Signal DTO)
   │
   ▼
Slice 6: Full Multi-Venue Integration, 31-Vector Red-Team & Freeze
```

---

## 17. Verification Ledger & Audit Signoff

- **Active Baseline Commit:** `959d771` (`HEAD == origin/main`)
- **Full Test Suite:** 1,020 collected (1,017 passed, 3 skipped, 0 failed, exit code 0).
- **Static Type Checker:** MyPy clean across all active modules (0 errors in 245 files).
- **Rule:** Do NOT write production code for Phase 12 until this Contract Specification v1.0 and the accompanying Red-Team Adversarial Matrix are reviewed and locked.
