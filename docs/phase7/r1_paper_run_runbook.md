# R1-REAL Paper Exercise — Runbook (Order 003 Candidate) (DRAFT — NOT AUTHORIZED)

Status: **DRAFT / NOT AUTHORIZED**. This runbook defines the sovereign execution,
observation, and safety protocols for the first real Paper order candidate (`Order 003`).
`P = 0` until an actual Paper runtime run completes and satisfies all Conjunctive P criteria.

This document is a **precondition and plan only**. It must be reviewed and explicitly
approved by the operator before any command in it is executed.

---

## 0. Evidence Semantics & Invariants

- **E (Empirical / Test Evidence):** Verified by the offline 610-test suite and AST structural guards. E **never** proves P.
- **P (Paper Runtime Evidence):** Actual Paper runtime observation — a real directive accepted by `ALPACA_PAPER`, observed through real broker lifecycle (SSE primary / REST recovery), and reconciled with broker reality. Current status: `P = 0`.
- **Core Invariant (Learned from Order 002 Incident):**
  $$\boxed{\text{Driver Timeout} \neq \text{Broker Order Finished}}$$
  Driver timeout does NOT imply the order stopped working on the broker. A timeout leaves the order active on the venue unless explicitly canceled and position-reconciled.

---

## 1. Exact Execution Script

Run via `run_paper.ps1` from the repository root:

```powershell
.\scripts\run_paper.ps1 uv run python -c "
import time
from decimal import Decimal
from acash.execution.alpaca.credentials import paper_credential_provider
from acash.execution.alpaca.venue import paper_endpoint
from acash.execution.alpaca.transport import PaperHttpAlpacaTransport, AlpacaOrderStatus
from acash.execution.alpaca.adapter import AlpacaPaperAdapter
from acash.execution.alpaca.real_driver import R1RealOrderExerciseDriver

# 1. Connect Transport
provider = paper_credential_provider()
endpoint = paper_endpoint()
transport = PaperHttpAlpacaTransport(provider=provider, endpoint=endpoint)
transport.connect()

# 2. Mandatory Preflight: Market Clock
clock = transport.query_clock()
print(f'CLOCK_STATUS: is_open={clock.is_open}, next_close={clock.next_close}, next_open={clock.next_open}')
if not clock.is_open:
    raise RuntimeError(f'[FAIL-CLOSED] Market is CLOSED. Next open at: {clock.next_open}')

# 3. Mandatory Preflight: Zero Starting Position
pos = transport.query_position('SPY')
start_qty = pos.quantity if pos else Decimal('0')
print(f'STARTING_SPY_POSITION: {start_qty}')
if start_qty != Decimal('0'):
    raise RuntimeError(f'[FAIL-CLOSED] Account not flat: SPY position is {start_qty}. Must be 0 before starting.')

# 4. Mandatory Preflight: Live Market Quote Benchmark Derivation (No Placeholders)
quote = transport.query_quote('SPY')
benchmark_mid = quote.mid_price
print(f'BENCHMARK_QUOTE: symbol={quote.symbol}, bid={quote.bid_price}, ask={quote.ask_price}, mid={benchmark_mid}')

# 5. Execute R1-REAL Driver (SSE Primary + REST Recovery)
client_order_id = 'acash-r1-paper-20260901-003'
quantity = Decimal('1')
adapter = AlpacaPaperAdapter(transport)
driver = R1RealOrderExerciseDriver(adapter, transport=transport)

print(f'LAUNCHING ORDER 003: client_order_id={client_order_id}, qty={quantity} SPY')
evidence = driver.submit_and_observe(
    client_order_id=client_order_id,
    symbol='SPY',
    quantity=quantity,
    benchmark_mid_price=benchmark_mid,
    timeout_seconds=30.0,
    poll_interval_seconds=0.5,
)

print('--- R1 LIFECYCLE EVIDENCE ---')
print(f'broker_order_id: {evidence.broker_order_id}')
print(f'final_state: {evidence.final_state}')
print(f'final_terminal: {evidence.final_terminal}')
print(f'filled_qty: {evidence.filled_qty}')
print(f'disputed: {evidence.disputed}')
print(f'is_in_parity: {evidence.reconciliation_report and evidence.reconciliation_report.is_in_parity}')
print(f'manifest_digest: {evidence.manifest and evidence.manifest.execution_digest}')
print(f'report_digest: {evidence.reconciliation_report and evidence.reconciliation_report.report_digest}')

# 6. Hardened Post-Timeout Active-Order Cleanup Policy
if not evidence.final_terminal:
    print('[INCIDENT] Driver timed out in non-terminal state. Initiating Active-Order Resolution...')
    # Check if order is still active on broker
    try:
        broker_snap = transport.query_order(evidence.broker_order_id)
        if broker_snap.status in {AlpacaOrderStatus.NEW, AlpacaOrderStatus.ACCEPTED, AlpacaOrderStatus.PENDING_NEW, AlpacaOrderStatus.PARTIALLY_FILLED}:
            print(f'Order is active on broker ({broker_snap.status.value}). Sending cancel request...')
            transport.cancel_order(evidence.broker_order_id)
            for _ in range(15):
                time.sleep(1)
                poll_snap = transport.query_order(evidence.broker_order_id)
                if poll_snap.status in {AlpacaOrderStatus.CANCELED, AlpacaOrderStatus.FILLED, AlpacaOrderStatus.REJECTED, AlpacaOrderStatus.EXPIRED}:
                    print(f'Broker reached terminal state: {poll_snap.status.value}')
                    break
    except Exception as exc:
        print(f'Resolution error: {exc}')

    # Final Position Audit
    end_pos = transport.query_position('SPY')
    end_qty = end_pos.quantity if end_pos else Decimal('0')
    print(f'POST_TIMEOUT_SPY_POSITION: {end_qty}')
    if end_qty != Decimal('0'):
        print('[ALERT] Cleanup NOT complete! Active position remains on broker. Incident remains OPEN.')
    else:
        print('[CLEANUP_OK] Account is flat. No active position remains.')
"
```

---

## 2. Pre-Run Checklist & Authorization Gates

Before execution, ALL of the following must hold:

1. **Git Commit State:** Head is at verified checkpoint.
2. **Paper Credential Venue:** Loaded from Windows DPAPI vault (`~/.acash/paper_credentials.dpapi`), pinned to `ALPACA_PAPER`.
3. **Endpoint Authority:** Pinned to `https://paper-api.alpaca.markets/v2`.
4. **Market Open Gate:** `clock.is_open == True` (US regular session 9:30–16:00 ET).
5. **Clean Account Starting State:** `SPY` position is strictly `0 / None`.
6. **No Placeholder Economics:** `benchmark_mid_price` is computed directly from `transport.query_quote('SPY').mid_price` (`(bid + ask) / 2`).
7. **Single Order Scope:** Exactly 1 market order for `1 SPY`. No retries, no second order.
8. **Live Execution:** `HARD-LOCKED (OFF)`.

---

## 3. Post-Timeout Safety & Incident Resolution

If the 30-second observation window expires without reaching a verified terminal state:

1. **State Safety:** Internal coordinator state transitions to `UNKNOWN`, `final_terminal = False`, `P = 0`.
2. **Active Order Inquiry:** Query `transport.query_order(broker_order_id)`.
3. **Cancel Directive:** If status is `NEW`, `ACCEPTED`, or `PARTIALLY_FILLED`, send `DELETE /v2/orders/{id}` via `transport.cancel_order()`.
4. **Polling for Absorption:** Poll broker snapshot until terminal confirmation (`CANCELED`, `FILLED`, etc.).
5. **Position Audit:** Query `transport.query_position('SPY')`.
   - If `position == 0`: Cleanup complete, account is flat, incident closed with $P = 0$.
   - If `position != 0` (e.g. cancel raced with fill): **Incident remains OPEN**. The run stops immediately, requiring explicit operator flatten.

---

## 4. Conjunctive P Acceptance Audit

$$\boxed{P = \text{TerminalVerified} \land \text{EvidenceLineageComplete} \land \text{ReconciliationVerified} \land \text{NoDispute} \land \text{BrokerSnapshotBound}}$$

A run is accepted as the first **P** evidence if and only if:

- [ ] **Terminal Verified:** `evidence.final_terminal is True` and `evidence.final_state == "FILLED"`
- [ ] **Evidence Lineage Complete:**
  - `evidence.manifest.execution_digest` is a 64-hex SHA-256 string
  - `evidence.reconciliation_report.report_digest` is a 64-hex SHA-256 string
- [ ] **Reconciliation Verified:** `evidence.reconciliation_report.is_in_parity is True`
- [ ] **No Dispute:** `evidence.disputed is False`
- [ ] **Broker Snapshot Bound:**
  - `broker_snapshot.status == AlpacaOrderStatus.FILLED`
  - `broker_snapshot.filled_qty == Decimal("1")`
  - `broker_snapshot.filled_avg_price == evidence.manifest.average_fill_price`
  - `broker_snapshot.filled_at is not None`

If any criterion fails $\implies$ **$P = 0$**, recorded as an incident report, and no promotion occurs.

---

## 5. Historical Incidents Log

### 5.1 Incident 001 (`INCIDENT-20260831-R1-SYNTHETIC-FILL`)
- **Root Cause:** Synthetic event pump used after real HTTP POST wire submission.
- **Remediation:** Implementation of `R1RealOrderExerciseDriver` with real SSE/REST observation.

### 5.2 Incident 002 (`INCIDENT-20260831-R1-MARKET-CLOSED-FILL`)
- **Root Cause:** Order submitted outside regular market hours; driver timeout disconnected observation while broker kept order active and filled at market open.
- **Remediation:**
  1. Mandatory Preflight Market Clock Gate (`is_open == True`).
  2. Hardened Post-Timeout Active-Order Cancellation & Position Audit.
