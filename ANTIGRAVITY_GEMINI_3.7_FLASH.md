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

## 3. Agent Operating Heuristics

1. **Be Epistemologically Humble**: State uncertainty immediately. If an observation count is small ($N=50$), acknowledge wide error bands; do not make grandiose claims about continuous curves.
2. **Always Distinguish Output Levels**:
   - `VERIFIED`: Proven by direct source code inspection, exact diff review, and locally executed test runs.
   - `SELF-REPORTED`: Executed in current session but unconfirmed by independent CI pipeline.
   - `NOT RUN`: Deferred or awaiting external execution.
3. **Never Fabricate Test Output**: Report the exact pytest summary line, warning counts, execution wall-clock time, and MyPy result.

---

## 4. CRITICAL DIRECTION — EVENT-DRIVEN VISUALIZATION CORE

This is a non-negotiable architectural direction for Atlas.

Do NOT begin by optimizing for visual beauty, 3D effects, or decorative animation.

The implementation priority is:
```text
Atlas event → Graph state → Event particle → Node reaction
```

The particle is a semantic representation of a real Atlas event.

A particle MUST NOT move merely because animation makes the graph look alive.

Every particle movement must correspond to an actual event or state transition received by Atlas.

### Conceptual Pipeline
1. Atlas receives event $X$.
2. Event $X$ is normalized into the event model.
3. Graph state is updated.
4. Event $X$ creates an event-particle.
5. The particle propagates from source entity $A \to$ target entity $B$.
6. When it reaches $B$, entity $B$ reacts.
7. If the event contains a propagation path, the particle may continue $A \to B \to C$.

### Semantic Invariant
> **"Particle movement represents information propagation, not decoration."**

### Example Execution
```text
Atlas receives:
    Event X at t = now - 300ms

Graph:
    A --MENTIONS--> B

Visualization:
    Particle X travels A → B
    B briefly reacts when X arrives
```

### Architectural Guardrails

#### DO:
- Model events explicitly.
- Keep event identity and timestamps immutable.
- Derive particles strictly from real events.
- Derive node reactions from event arrival.
- Keep graph state strictly independent from rendering layer.
- Preserve the event model if rendering technology changes.

#### DO NOT:
- Create random or decorative particles.
- Use `setInterval()` to invent synthetic activity.
- Animate edges without an underlying verified event.
- Fabricate graph updates just to make the scene look alive.
- Couple business/event logic directly to Three.js / WebGL components.

### Architectural Decoupling Goal
The event/data architecture must remain completely valid even if the renderer changes later:
```text
react-force-graph → custom Three.js → WebGPU → another visualization engine
```
* The renderer is replaceable.
* The semantic event pipeline is **NOT**.

### Implementation Hierarchy
1. **Priority 1**: Correct event $\to$ graph-state propagation
2. **Priority 2**: Correct particle/event identity
3. **Priority 3**: Correct node/edge reaction semantics
4. **Priority 4**: Real-time update behavior
5. **Priority 5**: Performance
6. **Priority 6**: Visual polish

