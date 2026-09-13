# ACASH Agent Engineering & Research Operating System (AGENTS.md)

This document establishes the project-wide, non-negotiable engineering, verification, and mathematical guidelines for all AI agents, human contributors, and automated systems interacting with the **ACASH** quantitative research and execution engine.

---

## 1. Core Principles (Non-Negotiable)

1. **Zero Unverified Claims**: Never declare an issue resolved, a test passed, or a finding closed based solely on walkthrough text, summaries, or assumption. Always verify through raw source code, git diffs, and executed test suites.
2. **Implementation Correctness $\neq$ Mathematical Validity**: Passing a unit test proves only that the code executes according to its written assertion; it does NOT prove that the formulation is canonical literature, unbiased, or stationary.
3. **Strict Fail-Closed Contract**: Never apply silent artificial floors (`max(1e-12, val)`), fabricated neutral outcomes ($p=1.0$, $SR=0.0$), silent lag truncations, or magic constants when encountering invalid, zero-variance, or undefined mathematical states. Raise `DataContractError` immediately.
4. **Single Canonical Authority**: Every derived parameter ($K$, $p\text{-value}$, $\text{Sharpe}$, $\text{config\_sha256}$, $\text{return\_sha256}$) must have a single authoritative point of origin bound by cryptographic lineage.
5. **Separation of Concerns**:
   - $\text{Implementation Correctness} \neq \text{Contract Correctness}$
   - $\text{Contract Correctness} \neq \text{Statistical Validity}$
   - $\text{Statistical Validity} \neq \text{Empirical Characterization}$
   - $\text{Empirical Admission} \neq \text{Future Tradeable Profitability}$
6. **Literature Alignment**: Never attach literature names (e.g. "Newey-West 1994 automatic plug-in bandwidth", "Bailey CSCV") to implementations without verifying that every algorithmic step matches the canonical paper. When using approximations or heuristics, explicitly name them as heuristics.
7. **Unit & Space Discipline**: Maintain strict separation between:
   - Period return space vs. Annualized space ($\sqrt{252}$)
   - Simple returns vs. Log returns
   - Sample variance vs. Long-run variance vs. Candidate trial variance
   - Raw bar count ($T$) vs. Independent effective observations ($T_{\text{eff}}$)
8. **Statistical Dependence Awareness**: Treat candidate models, multi-gate layers, and sequential tests that share underlying data as **statistically dependent**. Never label dependent controls as "orthogonal" or "independent".
9. **Marginal vs. Conditional Distinction**: Distinguish individual layer marginal pass rates $P(L_j)$ from sequential conditional admission probabilities $P(L_j \mid \bigcap_{i<j} L_i)$.
10. **Permutation & Tie Invariance**: All ranking algorithms, median splits, and IS/OOS comparisons must have deterministic, tie-symmetric policies.
11. **Never Broaden Scope Without Authorization**: Fix only the audited finding. Do not opportunistically redesign adjacent components unless the change is strictly required to preserve the stated invariant.
12. **Search Before Inventing a Helper**: Before creating new conversion routines, serializers, hash utilities, or statistical functions, search the existing codebase to prevent duplicate, divergent, or fragmented canonicalization logic.
13. **Every Derived Field Needs Exactly One Single Authority**: Every mathematical or cryptographic field must have a single authoritative calculation point:
    - $p\text{-value} \to$ derived canonically from empirical return series
    - $\text{Trial count } K \to$ sealed ledger
    - $\text{Manifest hash} \to$ execution manifest
    - $\text{DSR probability} \to$ Deflated Sharpe engine
    - $\text{PBO} \to$ CSCV Sharpe matrices
    - Never implement dual functions that calculate the same quantity with slight variations.
14. **Tests Must Attack Assumptions, Not Only Happy Paths**: Prioritize tests in the following order:
    $$\text{Happy Path} \to \text{Boundary} \to \text{Malformed} \to \text{Contradictory} \to \text{Adversarial} \to \text{Permutation} \to \text{Numerical Stability} \to \text{Golden Reference}$$
15. **Do Not Optimize for Green CI**: A passing test suite is an output, not the objective. The objective is the unyielding preservation of the mathematical, architectural, and governance contract.
16. **Warnings Are Evidence, Not Noise**: Every test, compiler, or runtime warning must be explicitly inspected and classified as actionable defect, dependency compatibility debt, expected behavior, or accepted risk. Never silently suppress or ignore warnings simply to produce cosmetically clean test logs.
17. **Repository Documentation Must Be Portable**: All repository-internal references must use repository-relative paths (`./path/to/file.md` or `path/to/file.md`). Never commit machine-specific `file:///` paths, absolute local filesystem paths, IDE-specific URLs, or workstation-specific references into canonical documentation.




---

## 2. Mandatory Verification Workflow

When addressing any quantitative, architectural, or audit finding:

```text
1. Inspect Source Code & Current Implementation
2. Inspect Existing Unit, Integration, and Invariant Tests
3. Identify Precise Data Contract & Invariants
4. Identify Canonical Literature & Mathematical Formulation
5. Formulate Fail-Closed Error Boundaries
6. Implement Changes (Zero Magic Floors / Silent Fallbacks)
7. Write Adversarial Tests (Boundary, Degenerate, Zero-Variance, NaN/Inf)
8. Run Golden Numerical Reference Benchmarks
9. Run Targeted Test Suite
10. Run Full Repository Test Suite (`uv run pytest`)
11. Run Full Type Checker (`uv run mypy src/ tests/`)
12. Inspect Git Diff (`git diff`)
13. Report Verified Status Honestly (distinguishing Verified vs. Self-Reported vs. CI)
```

---

## 3. Reporting Standards & Verification States

All agent reports must conclude with an explicit verification ledger:

```markdown
### Verification Ledger
- Implementation Status: [COMPLETE / PARTIAL]
- Contract Enforcement: [STRICT FAIL-CLOSED / N/A]
- Mathematical Authority: [CANONICAL SPEC / HEURISTIC SPEC]
- Local Test Suite: [VERIFIED (X passed) / NOT RUN]
- Type Checker (MyPy): [VERIFIED (X files clean) / NOT RUN]
- Remote CI Status: [VERIFIED (run id) / PENDING / NOT AVAILABLE]
- Methodological Caveats: [EXPLICIT BOUNDARY STATEMENTS]
```

---

## 4. Session Start, Authority, and Reusable Workflows

- Establish the actual checkout with `git status --short --branch`, `git branch -vv`,
  `git log -5 --oneline`, `git diff`, and `git diff --cached`. Local tracking refs
  are not proof of current remote state. Preserve existing work; never pull,
  reset, stash, or overwrite merely to make an audit look clean.
- Read the relevant source and decision records using the
  [agent workflow and source map](docs/engineering/agent-workflow.md). Handoffs,
  dashboards, other agents' memories, and this bootstrap's audit snapshot are
  navigation aids, not new governance authority. Resolve conflicts by decision
  scope and explicit supersession; unresolved authority stays blocked.
- Infrastructure readiness != strategy qualification != paper authorization !=
  live authorization. AI has no sovereign authority. Keep canonical capital at
  $0.00 and `NO_REAL_ORDERS=true` unless the required explicit human authorization
  changes that specific boundary. Synthetic cash in fixtures is not live capital.
- Before a mutation involving hypotheses, strategy, research admission, data
  authority, gates, capital, paper/live access, or governance, classify the
  required human authority and verify the applicable authorization. A task request
  or profitable result alone does not satisfy a separate ratification contract.
  Continue safe inspection and preparation; stop the dependent mutation if its
  required authority is absent. Do not ask again for authorization already
  established for the same action and scope.
- Preserve historical governance and phase records. New operating instructions
  cannot create HYP_003, start R1, unlock backtests, grant trading authority, or
  amend acceptance criteria. Record a separately authorized amendment with its
  lineage rather than silently rewriting history.
- Feed policy and G7 acceptance come from their human decision records. An audit
  is not a launch/resume request. Reconnect != trading resume; G7 audit != G7 PASS.
- Treat `inspect`, `audit`, and `check` requests as read-only. For authorized
  implementation, use the smallest safe change and the verification workflow
  above. Do not commit, push, create a PR, or mutate remote branches without an
  explicit request covering that action. No blind resets, force pushes, history
  rewrites, or discarding uncommitted work.
- Report facts with evidence, separate inference and proposals, state changes,
  tests, risks, unresolved items, authorization status, and the next step; finish
  with the verification ledger. Prefer direct, technically precise communication
  in the user's language. Do not infer production stack components from personal
  interests; inspect project manifests.
- Repository skills live in `.agents/skills/`. Use the workflow map to select
  only the relevant skill. They are instructions, not runtime enforcement or a
  guarantee of model behavior; do not load every skill into every task.
