# V110 Engineering Handoff — Portfolio Intelligence & Forward Shadow

Status: engineering complete for the scope the evidence supports. No investment result is claimed, no
order path exists, and `EXECUTION_AUTHORITY = NONE`.

## Implemented in this cycle

| Area | Module | What it does |
| --- | --- | --- |
| Point-in-time identity | `acash.invest.security_identity` + `docs/research/evidence/security_identity_registry.json` | ticker validity intervals, CUSIP/ISIN evidence, single-identity gate, `pit_qualified` separate from legacy eligibility |
| Inception evidence | `warehouse.coverage(..., inception=…)` | pre-inception gaps are `NOT_APPLICABLE` only with listing evidence; otherwise `PARTIAL_INCEPTION_UNVERIFIED` |
| Readiness | `acash.invest.readiness` | 13 independently gated components; a number being present never promotes a category |
| Forward shadow | `acash.invest.shadow` + `scripts/shadow_eval.py` | frozen protocol (SHA-256), append-only journal, prospective-only signals, forward outcomes, no duplication |
| Delta sync | `scripts/deploy/Sync-WarehouseFromHomelab.ps1` | manifest-first diff, changed partitions only, verified cutover with `.previous` rollback |
| Windows schedule | `scripts/deploy/Register-AcashSyncTask.ps1` | registered task "ACASH Warehouse Sync", 13:30 Tue–Sat, `StartWhenAvailable` |

## Evidence state (2026-11-05)

- SPCX: official CUSIP `84615Q103` / ISIN `US84615Q1031`, first session 2026-06-12, recorded with sources.
  The owner's position still carries FIGI `BBG000NQF3Z5`, which does not match the new listing, so the
  position is **not** reconciled to SpaceX and the series remains quarantined (`MULTI_IDENTITY`).
- NASA: verified inception 2026-03-30 → 349 pre-inception dates are `NOT_APPLICABLE`.
- CRWV: no listing evidence → 98 early gaps are `PARTIAL_INCEPTION_UNVERIFIED`, not excused.
- Research cohorts (identity-filtered): ESTABLISHED 24 / 404 sessions, RECENT 25 / 152; both price-return,
  hypothesis-only, current weights applied historically.
- Readiness: valuation QUALIFIED · reconciliation PARTIAL · identity BLOCKED · transactions PARTIAL ·
  realized performance INSUFFICIENT · ETF look-through BLOCKED · fees INSUFFICIENT · quant validation
  INSUFFICIENT. Overall decision: **BLOCKED**.
- Realized performance: **PERFORMANCE_NOT_ESTABLISHED** (no complete post-baseline external flows).
- Shadow: protocol `ACASH_SHADOW_V1` hash `35a7e812…bf46bf5f`, registered 2026-11-05; the first eligible
  observation must be strictly after registration, so there are **0 forward observations** today and the
  evaluation refuses retroactive sessions by contract.

## Data paths

```
data/private/market_warehouse/         partitions, manifest, health, sync_state
data/private/out/upi_view.json         authoritative portfolio view (28 position rows)
data/private/shadow/protocol_v1.json   frozen protocol + hash
data/private/shadow/journal.json       append-only signals and outcomes
docs/research/evidence/security_identity_registry.json   public identity registry
```

## Activation

```bash
# one manual sync + shadow pass (no provider calls)
powershell -NoProfile -File scripts/deploy/Sync-WarehouseFromHomelab.ps1
uv run python scripts/shadow_eval.py --evaluate     # refuses until a session after registration exists
uv run python scripts/shadow_eval.py --observe
uv run python scripts/shadow_eval.py --report
```

The scheduled task only runs the sync; shadow evaluation is intentionally manual until the protocol has
proven it can observe a full session without duplication.

## Governance boundaries

- `NO_REAL_ORDERS=true`, capital authority USD 0.00.
- A shadow signal is a research observation, never an order or a target price.
- Withholding/tax liability stays `NOT_ESTABLISHED`; no filing is produced.
- ETF look-through stays `OVERLAP_NOT_ESTABLISHED` until dated issuer holdings with permitted use exist.
- The Homelab collector is untouched by this cycle.

## Owner decisions still required

1. Reconcile the SPCX holding with CUSIP `84615Q103` (broker confirmation), then re-admit only sessions
   from 2026-06-12.
2. Provide the life-of-account transaction and cash-flow evidence for since-baseline performance.
3. Supply dated ETF holdings if look-through is wanted.
4. Decide whether to keep the 13:30 sync schedule as configured.
