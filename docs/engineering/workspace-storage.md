# Workspace storage policy

Local checkout size is dominated by research data and toolchains, not by source. This note records
what may be deleted automatically, what must be preserved, and how to propose a larger cleanup.

## Measured once (2026-11-04, this machine)

| Area | Size | Category |
|---|---|---|
| `data/raw` | ~66 GB | D — research datasets: **preserve**, deletion needs an explicit Owner decision |
| `data/hyp_007`, `data/hyp_009`… | tens of MB | D — historical hypothesis evidence: preserve |
| `.venv` | ~709 MB | B — reinstallable dependency: keep for daily use |
| `dashboard/node_modules` | ~100 MB | B — reinstallable dependency: keep |
| `var/` | ~70 MB | C — local runtime data: preserve, inspect before any action |
| `docs/`, `src/`, `tests/` | ~64 MB | tracked source: never a cleanup target |
| `__pycache__`, `.mypy_cache`, `.pytest_cache` | ~112 MB | A — regenerable cache |
| `dashboard/dist` | < 1 MB | A — regenerable build output |

## Category A — safe to delete automatically

Only these, and only when they are inside the checkout, are not symlinks/junctions, and no process
holds them:

- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `dashboard/dist/` (the launcher runs Vite in dev mode; CI rebuilds it)

After deleting, run one import and one focused test, and rebuild the dashboard before packaging.

## Category B — keep

`.venv/` and `dashboard/node_modules/` are large but required for convenient daily operation.
Reinstall plans must be tested before either is removed.

## Category C — Owner-private, preserve

`data/private/` (snapshot, capacity, backups) and anything under `data/private/transactions/`.
Never delete, never copy into Git, never print contents. Backups are the recovery path for the
authorized FX/HOOD corrections.

## Category D — research and governance, preserve

`data/raw/`, `data/parquet/`, `data/manifests/`, `data/local_research/`, historical hypothesis
folders, `docs/`, and the transaction/governance records. Old-looking files are not obsolete: the
research pipeline and CI may reference them.

## Category E — unknown

Anything not classified above is left untouched.

## Prohibited without a new explicit Owner decision

`git clean -fdx`, `git reset --hard`, `git prune`, reflog expiry, aggressive GC, recursive deletion
of `data/`, `var/`, `logs/`, `.venv/` or `node_modules/`, and moving tracked research trees. Git
history is never rewritten to save space.

## Larger cleanup proposal

`data/raw` alone is ~66 GB. Any reduction needs a reviewable proposal that lists the exact folder,
size, dependents (research steps, manifests, CI, tests) and the recovery method, and it requires the
Owner's explicit approval. Until then it is treated as important research data.
