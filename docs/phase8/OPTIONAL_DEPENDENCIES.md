# Phase 8 Portfolio Engine: Optional Dependency Policy & Provenance Specification

> **Document:** `docs/phase8/OPTIONAL_DEPENDENCIES.md`  
> **Status:** APPROVED & LOCKED (Batch 3D)  
> **Scope:** External Level 3 Portfolio Optimizer Adapters (`skfolio`, `cvxpy`)

---

## 1. Architectural Philosophy: Strict Optionality & Zero Core Bloat

The ACASH core portfolio engine operates fully deterministically without requiring any external optimization libraries. Core allocators (100% Cash, Equal Weight, Inverse Volatility, Native HRP, Native ERC) rely solely on the core mathematical substrate (`numpy`, `scipy`).

External optimizers (`skfolio`, `cvxpy`) are integrated via decoupled, lazy-loaded adapters under `src/acash/portfolio/adapters/`:
1. **Zero Core Import-Time Dependency:** If an optional package is not installed, importing `acash.portfolio` succeeds without error.
2. **Fail-Closed Execution:** If an optional adapter is invoked when its dependency is missing, it immediately raises a `DataContractError`. There is **zero silent fallback** to native optimizers.
3. **Pure Candidate Generation:** Adapters emit strictly `AllocationCandidate` and never bypass governance, evaluation, or rebalance planning.

---

## 2. Version Specification: Policy Range vs. Locked Tested Versions

ACASH maintains a strict separation between supported compatibility ranges and reproducible production execution:

$$\boxed{\textbf{Supported Compatibility Policy Range (pyproject.toml)}} \neq \boxed{\textbf{Locked Tested Environment (uv.lock)}}$$

### A. Supported Compatibility Policy (`pyproject.toml`)
Defines the permissible version envelope for optional dependency groups:

```toml
[project.optional-dependencies]
portfolio-skfolio = [
    "skfolio>=1.0.3",
]
portfolio-cvxpy = [
    "cvxpy>=1.9.2",
]
portfolio-all = [
    "skfolio>=1.0.3",
    "cvxpy>=1.9.2",
]
```

### B. Locked Tested Production Stack (`uv.lock`)
`uv.lock` freezes the resolved package artifacts for the tested environment; numerical reproducibility is verified for the declared runtime configuration:

| Package | Locked Tested Version | Primary Role / Backend |
| :--- | :--- | :--- |
| **`skfolio`** | `1.0.3` | Hierarchical clustering & Mean-Risk portfolio estimators |
| **`cvxpy`** | `1.9.2` | Domain-specific language for convex optimization |
| **`cvxpy-base`** | `1.9.2` | Core C++ canonical expression tree engine (`_cvxcore`) |
| **`clarabel`** | `0.11.1` | Conic interior-point solver (Rust/C extension) |
| **`osqp`** | `1.1.3` | Operator splitting quadratic program solver |
| **`scs`** | `3.2.11` | Splitting conic solver |
| **`highspy`** | `1.15.1` | HiGHS linear/mixed-integer/quadratic solver |
| **`scikit-learn`** | `1.9.0` | Clustering and machine learning substrate for `skfolio` |
| **`numpy`** | `2.2.3` / `2.5.2` | Numerical array substrate |
| **`scipy`** | `1.15.2` / `1.18.1` | Hierarchical linkage and SLSQP optimizer |

> [!WARNING]
> **No Claim of Universal Future-Version Compatibility:**  
> While `pyproject.toml` permits versions satisfying `>=1.0.3` and `>=1.9.2`, mathematical determinism and cross-model parity are guaranteed only under the exact environment frozen in `uv.lock`. Upstream solver algorithm revisions, heuristic changes, or floating-point accumulator shifts in newer releases require explicit re-verification before production deployment.

---

## 3. Numeric Boundary & Provenance Tracking

All external optimizers operate in **IEEE 754 float64** space. The ACASH domain operates in **arbitrary-precision financial Decimal**.

$$\boxed{\text{Decimal Input} \xrightarrow{\text{projection}} \text{IEEE 754 float64} \xrightarrow{\text{solver}} \text{float64 weights} \xrightarrow{\text{projection}} \text{Canonical Decimal Representation}}$$

Every candidate produced by an optional adapter records its complete provenance:
- `backend_package`: Package name (`skfolio`, `cvxpy`, `acash_native`)
- `backend_version`: Exact runtime package version
- `solver`: Mathematical solver identity (`CLARABEL`, `OSQP`, `SCH_LINKAGE`, etc.)
- `solver_version`: Version of the underlying solver engine
- `solver_status`: Solver termination status (`OPTIMAL`, `CONVERGED`)
- `config_fingerprint`: Deterministic SHA-256 hash of all material model settings
- `numeric_backend`: `IEEE_754_FLOAT64`
- `conversion_policy`: `CANONICAL_DECIMAL_REPRESENTATION_FLOAT64`
