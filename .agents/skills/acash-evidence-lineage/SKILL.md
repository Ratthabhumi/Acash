---
name: acash-evidence-lineage
description: Trace ACASH research claims, return series, trial counts and cryptographic provenance to their single authority; use for evidence admission and lineage audits.
---

# ACASH research evidence and lineage

Read root `AGENTS.md`, the research rows in
`docs/engineering/agent-workflow.md`, then the claim-specific contract and callers.

Trace the operational chain: MARKET INPUT -> FEATURE STATE -> SIGNAL -> RISK
DECISION -> ORDER INTENT -> SIMULATED EXECUTION -> POSITION -> PORTFOLIO -> SYSTEM
HEALTH. Trace research admission separately: narrative -> measurable definition
-> hypothesis -> authorized data -> falsification -> statistical evidence ->
robustness -> friction/capacity -> independent review -> human authorization.

- For each claim, identify raw input, producer, schema, units, timestamps, dataset
  version, configuration, code version and verification result. A missing link
  is missing evidence; never fill it with an invented value or provenance hash.
- Find the existing canonical authority before adding any helper. Follow return
  series to canonical p-values, sealed trial ledger to K, execution manifest to
  its hash, DSR engine to DSR probability, and CSCV matrices to PBO. Verify actual
  fields and scope; do not conflate research and paper manifest schemas.
- Inspect period/annualized and simple/log spaces, variance type, dependence,
  effective observations, ties and permutation behavior. Invalid mathematical
  states must fail closed through the existing contract, not floors or neutral
  fabricated results. Verify named algorithms against primary literature before
  claiming canonical equivalence; explicitly label heuristics.
- Preserve D17 source identity, PIT/as-published history, coverage, licensing and
  archive requirements. Feed availability is not D17 authority. Do not acquire
  data or run empirical validation just to complete an audit.
- Dashboard `MOCK-RESEARCH-001`, fixtures, simulations and infrastructure tests
  remain their stated evidence class. Their metrics cannot qualify a strategy or
  authorize paper/live. Hash integrity alone does not establish truth, unbiased
  methodology or human approval.

Report a claim-to-source table with verification and missing links. Separate
implementation correctness, contract enforcement, statistical validity, empirical
characterization, admission and future profitability. Run relevant existing
golden tests when authorized verification is in scope; report their actual
coverage and finish with the root ledger.
