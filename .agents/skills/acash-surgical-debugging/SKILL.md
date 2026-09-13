---
name: acash-surgical-debugging
description: Investigate an ACASH defect and implement an authorized minimal fix with regression evidence; use for root-cause debugging, contract failures and numerical regressions.
---

# ACASH surgical engineering and root-cause debugging

Read root `AGENTS.md`, the relevant source-map rows in
`docs/engineering/agent-workflow.md`, the implementation and existing tests.
Preserve user work and the exact authorized scope.

Follow symptom -> evidence -> reproduction -> root cause -> containment ->
minimal fix -> regression test -> prevention -> governance impact.

- Label PROVEN ROOT CAUSE, LIKELY CAUSE and POSSIBLE CAUSE separately. A failing
  assertion or timeout names a symptom until the causal path is demonstrated.
- Identify the data contract, callers, canonical helpers and human-governed
  boundaries before editing. Search before adding converters, serializers,
  hashes or statistical functions. Do not add a second authority for a quantity.
- Prefer the smallest safe fix with explicit typed boundaries and deterministic
  behavior. If a broader refactor is explicitly requested, compare the narrow
  alternative and its tradeoffs without silently replacing the user's scope.
- Invalid mathematical states must raise the established `DataContractError`;
  no fabricated probabilities, Sharpe values, floors or silent lag truncation.
  Do not weaken tests, acceptance thresholds or governance to remove a failure.
- Add regression checks that attack the demonstrated failure and affected
  assumptions: boundary/degenerate/nonfinite inputs, contradictions, adversarial
  ordering/ties/permutations and numerical stability as relevant. Avoid tests
  that merely restate instruction wording or implementation structure.
- Use primary literature and independent numerical references for mathematical
  changes. Code execution and a matching test assertion do not prove canonical
  methodology. Run the targeted suite, root full tests and MyPy required by
  AGENTS.md, then inspect the entire diff and warnings.

Report cause, evidence, minimal change, executed checks, remaining uncertainty
and governance impact. Do not patch unrelated baseline failures without scope
authorization. End with the root verification ledger.
