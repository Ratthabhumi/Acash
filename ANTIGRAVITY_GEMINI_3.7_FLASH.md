# Antigravity Gemini 3.7 Flash — ACASH Engineering & Research Guardrails

This document records institutional memory, model-specific behavioral guardrails, and recurring cognitive anti-patterns identified during the ACASH quantitative validation and architectural hardening process.

---

## 1. Recurring Behavioral Failure Modes & Priorities

| Priority | Recurring Anti-Pattern | Root Cause | Impact | Mandatory Remediation |
| :--- | :--- | :--- | :--- | :--- |
| 🔴 **P0** | **Trusting Walkthrough / Self-Claims** | Believing prior text without reading source | Declaring finding closed when code is broken | Must view raw file lines and inspect git diff before confirming. |
| 🔴 **P0** | **Attaching Canonical Names to Approximations** | Assuming formula matches paper without line-by-line verification | Methodological overclaim in literature alignment | Explicitly declare heuristic vs. canonical algorithms. |
| 🔴 **P0** | **Silent Fallbacks & Magic Floors** | Inserting `max(1e-12, x)` or returning `p=1.0` on degenerate states | Corrupting statistical inference and hiding data anomalies | Strictly raise `DataContractError` on degenerate states. |
| 🔴 **P0** | **Ambiguous Parameter Authority** | Deriving $K$, $p$-values, or Sharpes in multiple places | Contract divergence and untracked search opportunities | Single canonical authority enforced by cryptographic hash. |
| 🟠 **P1** | **Marginal vs. Conditional Confusion** | Treating $P(L_j)$ as conditional filter $P(L_j \mid \bigcap_{i<j} L_i)$ | Misidentifying the bottleneck layer in multi-gate funnels | Compute sequential survival and conditional transition rates. |
| 🟠 **P1** | **Labeling Dependent Controls as "Orthogonal"** | Using casual engineering vocabulary for statistical concepts | Falsely claiming statistical independence of DSR and PBO | Use "complementary but statistically dependent controls". |
| 🟠 **P1** | **Period vs. Annualized Confusion** | Mixing daily $SR$ with annualized $SR \sqrt{252}$ in variance equations | Multi-order of magnitude errors in EVT hurdles | Keep explicit `SharpeSpace` and convert strictly at boundaries. |
| 🟠 **P1** | **Overclaiming from Empirical Benchmarks** | Claiming $0/100 \implies \text{FPR}=0\%$ | Epistemological overconfidence | Report observed point estimate with Wilson 95% Confidence Intervals. |
| 🟡 **P2** | **Tie-Breaking & Permutation Asymmetry** | Relying on dictionary ordering or non-symmetric comparisons | Flawed PBO logits under tied candidate returns | Enforce explicit mid-rank and symmetric tie-breaking policies. |
| 🟡 **P2** | **Modifying Code Before Reading Architecture** | Jumping directly to implementation | Breaking existing contracts and causing regressions | Read relevant schemas, contracts, and existing test suites first. |

---

## 2. Forensic Lessons from Historical Remediation Commits

1. **Commit `55f56bc` $\to$ `68e0b29` (Universe & DSR Authority Separation)**:
   - *Lesson*: General CPCV and Balanced CSCV must have isolated parameter universes ($N=10, k=2$ vs $N=10, k=5$). Never route governance PBO through unbalanced partition generators.
2. **Commit `68e0b29` $\to$ `d41593b` (Partition Verification & Runtime Spies)**:
   - *Lesson*: Never trust incoming partitions blindly. Validate uniform test group count $k$, combination uniqueness, contiguous group labels $\{0, \dots, N-1\}$, and exact combination count $\binom{N}{k}$ in a fail-closed validator.
3. **Commit `d41593b` $\to$ `4741608` (Epistemological Boundaries)**:
   - *Lesson*: $\text{PASS\_TRADEABLE\_ALPHA}$ is a governance policy compliance verdict, not a mathematical certificate of future market profitability or alpha stationarity.
4. **Commit `4741608` $\to$ `4c0e075` (In-Repo Reproducible Artifacts)**:
   - *Lesson*: Experiments must exist as reproducible code and persistent machine-readable artifacts inside the repository with deterministic seeds, sample sizes, and Wilson confidence intervals.
5. **Commit `4c0e075` $\to$ `c73ddf1` (HAC Fail-Closed Remediation)**:
   - *Lesson*: Eliminating magic floors (`max(1e-12, lr_var)`) and fabricated neutral values ($p=1.0$) is non-negotiable. An invalid mathematical state must always result in a fail-closed error.
6. **Commit `c73ddf1` $\to$ `93ade20` $\to$ `3038315` (Sequential Funnel & Terminology Precision)**:
   - *Lesson*: DSR and PBO are statistically dependent controls evaluating distinct failure modes. Measuring multi-gate policy detection requires sequential conditional funnels $P(L_j \mid \bigcap_{i<j} L_i)$, not just marginal pass rates.

---

## 3. Agent Operating Heuristics & Epistemic Stance

1. **Be Epistemologically Humble**: State uncertainty immediately. If an observation count is small ($N=50$), acknowledge wide error bands; do not make grandiose claims about continuous curves.
2. **Always Distinguish Output Levels**:
   - `VERIFIED`: Proven by direct source code inspection, exact diff review, and locally executed test runs.
   - `SELF-REPORTED`: Executed in current session but unconfirmed by independent CI pipeline.
   - `NOT RUN`: Deferred or awaiting external execution.
3. **Never Fabricate Test Output**: Report the exact pytest summary line, warning counts, execution wall-clock time, and MyPy result.
4. **Anti-Hype Epistemic Discipline**:
   $$\boxed{\text{IMPLEMENTED} \neq \text{VALIDATED} \neq \text{PRODUCTION-PROVEN}}$$

---

## 4. Progressive Context Navigation Protocol

To prevent cognitive overload and context fragmentation, agents must follow the **Progressive Disclosure Protocol** via [`ATLAS_CONTEXT_MAP.md`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/ATLAS_CONTEXT_MAP.md):

```text
AGENTS.md
   │
   ▼
ATLAS_CONTEXT_MAP.md
   │
   ├──► docs/atlas/graph/architecture.md             (Graph State & Node/Edge Contracts)
   ├──► docs/atlas/events/event_model.md             (Canonical Event Lifecycle & Ingestion)
   ├──► docs/atlas/visualization/event_driven_rendering.md (Particle Propagation Invariants)
   ├──► docs/atlas/market/microstructure.md          (Order-Flow Taxonomies & Rule Provenance)
   ├──► docs/atlas/reasoning/epistemic_model.md      (Epistemic Levels & Evidence Envelopes)
   └──► docs/atlas/infrastructure/runtime.md         (High-Throughput IPC & Storage)
```

### Non-Negotiable Domain Invariants:
1. **The Particle Invariant**: *"Particle movement represents real information propagation, not decoration."*
2. **Canonical vs. Projection Separation**: Graph state & events are durable core truth; 3D renderers, embeddings, and layout coords are disposable, rebuildable projections.
3. **Rule Provenance**: Inferred events must carry explicit `rule_id`, `epistemic_level`, `evidence`, and `confidence`. Never generate freeform ungrounded classification strings.
