# ACASH Research & Validation Dashboard (Phase A Foundation)

## 1. Overview & Architectural Boundaries

The **ACASH Research & Validation Dashboard** is a dedicated research observability and empirical evidence visualization interface for the ACASH quantitative research platform. It is located strictly inside `./dashboard/` to maintain absolute isolation from the ACASH Python core runtime (`src/acash/`).

### Strict Epistemic & Operational Invariants
1. **Research Observability Only**: The dashboard provides read-only visualization of research sessions, backtests, and paper simulation runs.
2. **Zero Trading Capability**: The dashboard possesses **no order execution, broker integration, capital allocation, or trading capability**.
3. **Runtime Invariant Authority**: `NO_REAL_ORDERS=true` remains strictly enforced by the existing ACASH Python execution/runtime layer. The dashboard frontend is **not** an authority over runtime invariants; it simply has zero trading controls.
4. **Mock Data Conspicuity**: All mock and prototype data is prominently marked with:
   ```
   DEMO DATA · SIMULATED RESEARCH RUN · NOT ACASH RESEARCH EVIDENCE
   ```
   Mock strategies strictly use synthetic identifiers (`MOCK-RESEARCH-001`), never canonical research hypothesis IDs (`HYP_001`, `HYP_002`, `HYP_003`).
5. **Zero Fake Pass**: Mock validation gates must never display fake `PASS` statuses. Default criteria are explicitly classified as `NOT_EVALUATED`, `DEMO`, `PENDING`, or `FAIL` (Hard-Locked).
6. **Human Authorization**: Human research director authorization is permanently bound to `NOT AUTHORIZED` with `$0.00` capital allocation.

---

## 2. Evidence Lineage (11 Canonical Stages)

The dashboard renders an interactive Directed Acyclic Graph (DAG) visualizing the exact 11-stage causal pipeline:

```
[1. Market Data]
       ↓
[2. Normalized Data]
       ↓
[3. Feature State]
       ↓
[4. Signal]
       ↓
[5. Risk Decision]
       ↓
[6. Order Intent]
       ↓
[7. Simulated Execution]
       ↓
[8. Position]
       ↓
[9. Portfolio]
       ↓
[10. Metrics]
       ↓
[11. Validation]
```

Every stage exposes:
- **Authority Rule Contract**: The formal governance specification governing the step.
- **Source Module**: Python module responsible for the computation.
- **Artifact & Cryptographic Digest**: Immutable SHA-256 hash verifying data integrity.
- **Structured Evidence Payload**: Exact machine-readable parameters.

---

## 3. Technology Stack & Design System

- **Framework**: React 18 + TypeScript 5
- **Build Tool**: Vite 5
- **Styling**: Tailwind CSS 3 with an **EIMS-inspired muted enterprise palette**:
  - Background: Neutral slate-50 (`#f8fafc`) and crisp card whites (`#ffffff`)
  - Typography: Inter (UI text) + JetBrains Mono (cryptographic hashes, prices, metrics)
  - Borders: Muted enterprise border (`#e2e8f0` / `#cbd5e1`)
  - Accents: Low-saturation emerald (gains), rose (drawdowns/locks), amber (warnings), slate (neutral)
- **Icons**: Lucide React
- **Navigation Shell**: Lightweight `Ctrl+K` / `⌘K` command palette for rapid keyboard switching between:
  - **Overview**: 90-day simulation metrics, dual SVG equity/drawdown chart, interactive milestone timeline, friction attribution.
  - **Simulated Trades**: Filterable, sortable audit table with 6-stage trade evidence drill-down.
  - **Evidence Lineage**: 11-stage causal DAG node inspector.
  - **Validation & Gates**: Multi-gate statistical checks, blind out-of-sample isolation, and governance locks.

---

## 4. Local Development & Verification

### Running the Dashboard Locally
```bash
cd dashboard
npm install
npm run dev
```
Access the dashboard at `http://localhost:3000`.

### Typecheck & Production Build
```bash
npm run typecheck    # Strict TypeScript verification
npm run build        # Production bundle build
```

### Running Contract Tests
```bash
npm test             # Validates data contracts, 11 stages, and zero-fake-pass invariants
```
