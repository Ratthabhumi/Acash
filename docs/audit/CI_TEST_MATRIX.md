# ACASH CI & Test Tier Partitioning Matrix

**Date Context**: 2026-09-30  
**Scope**: Repository-Wide Test Organization & CI Tier Decoupling  
**Audited Finding Reference**: F08 (Monolithic Test Suite Lacks Tier Partitioning)

---

## 1. Problem Statement & Motivation

Prior to this audit, `uv run pytest` executed all 3,269 collected tests indiscriminately in a single monolithic run. This caused spurious failures when running in standard development or CI environments because tests with divergent prerequisites were co-located:
1. **Hermetic core logic** was mixed with **non-hermetic Git repository ancestry checks**.
2. **Proprietary sealed datasets** were expected on environments without mounted research data volumes.
3. **Windows-native MetaTrader 5 (MT5) binaries** were required on Linux headless CI nodes.
4. **Interactive dashboards** and reporting tools competed with numerical regression suites.

To establish reproducible, deterministic verification, tests must be explicitly partitioned into five distinct operational tiers.

---

## 2. Test Tier Definitions

| Tier ID | Tier Name | Purpose & Scope | Execution Preconditions | CI Frequency | Pytest Marker / Filter |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **T1** | **Hermetic Unit & Contract** | Core mathematical formulation, domain models, state engines, parsers, and schema validation. Zero network, zero OS binary dependency. | Python virtualenv, temp filesystem only. | Every commit / PR gate. | `pytest -m "not non_hermetic and not native_mt5 and not sealed_data and not dashboard"` |
| **T2** | **Optional Native MT5** | MT5 execution driver, Windows IPC bridge, broker protocol qualification. | Windows OS, MT5 terminal installed, demo broker credentials. | On-demand / Windows execution runner. | `pytest -m "native_mt5"` |
| **T3** | **Authorized Sealed Data** | High-density historical simulation, multi-year SIP tick validation, Gate 6/7 empirical replay. | Mounted encrypted data partition (`data/historical/`). | Nightly research qualification. | `pytest -m "sealed_data"` |
| **T4** | **Dashboard & Visualization** | Streamlit ops consoles, evidence viewers, flight recorder visualizers. | UI dependencies, headless browser if E2E. | On UI changes / release candidates. | `pytest -m "dashboard"` |
| **T5** | **Git-History & Lineage Audit** | Repository ancestry checks, commit message audits, tag lineage verification. | Live `.git` repository with full history (unshallow). | Post-merge / Release audit gate. | `pytest -m "non_hermetic"` |

---

## 3. Tier Details & Environment Contracts

### Tier 1: Hermetic Unit & Contract Tests
- **Directory Scope**: `tests/unit/core/`, `tests/unit/domain/`, `tests/unit/math/`, `tests/unit/research/` (offline components).
- **Contract**:
  - Must complete in $< 60$ seconds.
  - Zero disk state persistence beyond `tmp_path`.
  - Zero Git subprocess queries against the parent working tree (all Git behavior mocked or using synthetic temp repos).
  - Deterministic random seed and time freezing where applicable.

### Tier 2: Optional Native MT5
- **Directory Scope**: `tests/unit/execution/mt5/`, `tests/integration/execution/mt5/`.
- **Contract**:
  - Automatically skip with `pytest.skip("MT5 terminal not available")` if `MetaTrader5` package or terminal is absent.
  - Never fail closed on Linux or cloud CI runners.

### Tier 3: Authorized Sealed Data
- **Directory Scope**: `tests/integration/data/`, `tests/integration/research/sealed/`.
- **Contract**:
  - Must verify manifest signatures and data integrity digests before consumption.
  - Gracefully skip if data store path is unpopulated, but fail closed if data is present but corrupted.

### Tier 4: Dashboard & Visualization
- **Directory Scope**: `tests/unit/ui/`, `tests/integration/dashboard/`.
- **Contract**:
  - Validate schema generation, component rendering, and JSON telemetry endpoints without opening browser windows unless run in `--e2e` mode.

### Tier 5: Git-History & Lineage Audit
- **Directory Scope**: `tests/unit/research/test_phase14_hyp_011_sip_recovery.py::test_builder_historical_git_audit`, `tests/governance/`.
- **Contract**:
  - Explicitly marked `@pytest.mark.non_hermetic`.
  - Requires full Git clone (`depth != 1`).
  - Verifies canonical merge commits (`08530b1...`), manifest addition commits (`becec27...`), and GPG/author signatures.

---

## 4. Pytest Configuration Recommendations (Post-Freeze)

When runtime configuration unfreezes post-Attempt #2, `pyproject.toml` should register these standard markers:
```toml
[tool.pytest.ini_options]
markers = [
    "non_hermetic: marks tests that require live git repository history or external host state",
    "native_mt5: marks tests that require native Windows MetaTrader 5 installation",
    "sealed_data: marks tests that require mounted authorized historical data fixtures",
    "dashboard: marks tests that require dashboard or UI rendering dependencies",
]
```
*(Currently dynamically registered via `tests/conftest.py:pytest_configure` to strictly respect `pyproject.toml = NO MODIFICATION` during Phase A freeze).*
