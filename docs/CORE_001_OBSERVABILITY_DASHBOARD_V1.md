# CORE-001 Observability Dashboard v1

Read-only observability for CORE-001 / HYP_011. Reference:
`docs/CORE_001_STAGED_EVIDENCE_FRAMEWORK_V1.md` (governance authority —
this document duplicates none of it).

## Start

```powershell
# 1. Generate the derived snapshot (reads canonical artifacts, zero network)
uv run python scripts/generate_core001_dashboard_snapshot.py `
  --state-dir data/hyp_011/prospective `
  --out dashboard/public/data/core001-status.json

# 2. Run the dashboard (existing stack: React/Vite/TS, port 3002)
cd dashboard
npm run dev
```

Open the **CORE-001 HYP_011** tab. Without step 1 the tab renders the
explicit EMPTY PRE-S1 state (normal before Observation #0001).

## Route / page

Tab `core001` → `dashboard/src/pages/Core001Page.tsx` (wired in `App.tsx`
+ `Sidebar.tsx`). Reuses `AppShell`, `MetricCard`, `StatusBadge`,
`EmptyState`, `EquityDrawdownChart`. No new framework.

## Data source

- Canonical: `data/hyp_011/prospective/state.json` + sealed
  `observations/*.json` (HYP_011 prospective implementation; inspected, not
  guessed).
- Python adapter `src/acash/observability/core001_dashboard.py` derives the
  view model; the generator script emits ONE derived file
  `dashboard/public/data/core001-status.json` (gitignored derived
  presentation, never authority).
- TS repository `dashboard/src/services/core001Repository.ts` fetches the
  snapshot same-origin and falls back to EMPTY PRE-S1 when absent.

## Read-only invariant

Adapter opens artifacts with read-only file reads only (static-scan test
forbids write/network/credential tokens). The generator refuses `--out`
inside the state directory. The page and repository contain zero
POST/PUT/PATCH/DELETE and zero order/authorization/backfill controls
(contract-tested). No SSH, no systemctl, no credential access. Runtime
status displays `UNAVAILABLE FROM DASHBOARD` by design.

## Zero-observation behavior

Stage PRE-S1; progress 0/20, 0/60, 0/504, rebalances 0/2; portfolio shows
canonical all-cash initial state; S2 metrics N/A
(`INSUFFICIENT_OBSERVATIONS`); paper NOT AUTHORIZED; live LOCKED; real
capital $0.00; `NO_REAL_ORDERS` TRUE. Missing evidence renders
NOT YET OBSERVED / N/A — never ERROR.

## After observations arrive

Regenerate the snapshot; the page shows sealed holdings, equity/drawdown
charts (no interpolation, misses stay missing), evidence panel (ordinal,
session, SHA chain, provenance, CA status), and S2 diagnostics labeled
"Diagnostic only until Observation 60". Counts alone never yield
`OPERATIONALLY_SANE` or `PAPER_ELIGIBLE` (review-required states instead).

## What the dashboard cannot do

Observe, authorize, execute, mutate, backfill, SSH/systemctl, touch
credentials, access market data, commit/push. It reflects authority; it
never creates it.
