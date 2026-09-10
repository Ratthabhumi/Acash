# ACASH V5 - Minimal External Research / Tooling Intake

## 0. Document Status

- Classification: **RESEARCH INTAKE ONLY / MINIMAL EXTERNAL KNOWLEDGE INTAKE**.
- Nature: documentation-only intake record. No authorization is granted by this document.
- Scope: records the minimal external research-skills and tooling items considered for ACASH, the
  verified facts about them, and the final disposition per the human's pre-classification.
- Effective date: 2026-09-10 (environment date).
- Non-ASCII: none (ASCII-only file).
- Repo status: **no commit, no push** for this document (explicit human instruction).
- Review requirement (AGENTS.md #1 Zero Unverified Claims): every external claim below carries an
  explicit evidence label. No screenshot, anecdote, or unverified video summary is treated as verified
  fact.

## 1. Purpose

This intake records a **minimal, bounded** evaluation of five external research / tooling items named
by the human. It does four things:

1. Preserves the human's pre-classification as the binding disposition (see Section 8).
2. Records the external facts that were actually verified in this session, each with a label.
3. States precisely what ACASH keeps, defers, or discards (Sections 8-10).
4. Re-confirms the governance boundary: this intake creates **no** hypothesis, **no** candidate,
   **no** empirical work, and **no** dependency.

It is **not** a research-assistance tool audit, a forecasting benchmark, or an integration request.

## 2. Source Material

- The supplied material is a topic list of five named items (human-provided, in-session):
  1. Academic Research Skills resources.
  2. OpenMAIC (open-source AI re-education platform).
  3. TimesFM (time-series foundation model).
  4. LSTM stock-price prediction content.
  5. A generic backtesting course.
- Provenance note: the referenced screenshots / video summaries were **not attached** in this session;
  no attachment was received by the agent. External facts below were verified from public sources
  during this session (see Section 4 and Section 5). `[SOURCE-DERIVED]` marks statements derived from
  the supplied topic list; `[VERIFIED EXTERNAL FACT]` marks statements verified from public sources;
  `[ACASH INFERENCE]` marks agent analysis.

## 3. Academic Research Skills

- Human disposition: **KEEP** - retain as methodology knowledge with ACASH-specific implementation.
- What the category generally covers (canonical research-methodology knowledge): falsifiable
  question formulation, literature review discipline, hypothesis testing logic, experimental design
  principles, reproducibility, provenance, and transparent reporting.
- Existing ACASH coverage (mapping, `[ACASH INFERENCE]`):
  - Zero Unverified Claims / verification workflow / reporting standards -> AGENTS.md, sections 1-3.
  - Falsification orientation -> `./research_doctrine.md` section 16 and the falsificationist
    orientation of `./acash_market_research_ontology_v1.md`.
  - Anti-HARKing / research-flexibility control -> freeze rules in the MACRO-001 binding worksheet
    (Group D) and F-1 freeze section 18.
  - Reproducibility / provenance -> D5 OOS provenance, phase5 orchestration readiness, data source
    registry, MEC-0011 provenance audit.
  - Adversarial / boundary / degenerate testing -> AGENTS.md section 1.14 and the accepted test
    suites.
  - Separation of observation vs. causal/predictive claims -> ACASH doctrine-5/6 and research_doctrine
    section 2.
- Assessment: the category is **almost entirely already represented** in ACASH governance. The only
  additive value is a compact **reinforcing checklist** that future research documentation may
  reference. `[ACASH INFERENCE]`
- Final classification: **KEEP (as confirmed methodology; zero governance change required)**.
- ACTUAL_USAGE_RULE: academic-research skills inform research methodology and documentation only.
  No tool integration, no new governance rule, no new process is introduced by this intake. `[ACASH INFERENCE]`

## 4. OpenMAIC

- Human disposition: **research-assistance tooling candidate** - keep only if verified to have real
  utility for ACASH research workflows.
- Verified external facts (`[VERIFIED EXTERNAL FACT]`, source:
  `https://github.com/THU-MAIC/OpenMAIC` and the associated MAIC paper):
  - OpenMAIC = "Open Multi-Agent Interactive Classroom" by THU-MAIC; source-code and paper open.
  - It is an AI **education / learning** platform: it converts a topic, document, or textbook chapter
    into an interactive multi-agent classroom (AI teacher, AI classmates, quizzes, slides, interactive
    simulations, whiteboard content, text-to-speech).
  - Orchestration is multi-agent (LangGraph-style), with model-provider abstraction, document parsing,
    and chat-bot integration (e.g., OpenClaw / messaging apps). Outputs include `.pptx` and `.html`
    materials.
  - Primary purpose: **teaching and learning**, not quantitative research assistance.
- ACASH relevance assessment (`[ACASH INFERENCE]`):
  - It is not a research-assistance tool in ACASH's sense: it does not do literature review,
  evidence synthesis, statistical analysis, model evaluation, or research-documentation governance.
  - ACASH already has its own intake pipeline and does not need an education-platform dependency.
  - No capability gap that OpenMAIC would fill within the current Phase 14 / MACRO-001 / MEC workflow.
- Final classification: **DISCARD** - verified as an education platform, not research-assistance
  tooling; **no material utility** for ACASH research/engineering workflows.

## 5. TimesFM / Forecasting

- Human disposition: **future forecasting benchmark / tool** - keep only as a future benchmark or
  research tool, never as a trading signal source.
- Verified external facts (`[VERIFIED EXTERNAL FACT]`, source:
  `https://github.com/google-research/timesfm` and the associated ICML 2024 paper):
  - TimesFM = a decoder-only time-series **foundation model** from Google Research for time-series
    forecasting.
  - Capabilities: zero-shot univariate and multivariate forecasting; support for covariates; context
    lengths up to 16k observations; calibrated/quantile point-plus-uncertainty forecast outputs;
    model sizes include a 200M-parameter variant.
  - Distribution: open-source inference/weights repository. Source code and weights up to v2.5 are
    Apache-2.0. **TimesFM 3.0 pretrained weights are distributed under a separate
    non-commercial license (`timesfm-non-commercial-license-v1.0`, non-commercial and
    non-production use only).** `[VERIFIED EXTERNAL FACT]`
- ACASH relevance assessment (`[ACASH INFERENCE]`):
  - Relevant only as a **number-generation benchmark** inside a future forecasting research slice
    that is not currently scoped.
  - The license split is material: ACASH is a quantitative research and (potentially) execution
    engine; adopting TimesFM 3.0 weights would carry a non-commercial constraint that must be
    resolved before any production/near-production use.
  - No connection to any BUY/SELL path. No integration is proposed. Nothing is downloaded.
- Final classification: **FUTURE RESEARCH** - registered as a benchmark candidate only, with an
  explicit license caveat.

## 6. LSTM

- Human disposition: **DISCARD** - not essential.
- Description from source: generic LSTM ("long short-term memory") neural-net approach for
  stock-price prediction, as commonly presented in retail material.
- Critical caveats (`[ACASH INFERENCE]`):
  - Sequence-model stock-price prediction content typically conflates in-sample fit / lookahead
    leakage with economic value, and prediction accuracy is not tradeable net edge (non-stationarity,
    costs, capacity).
  - ACASH's canonical philosophy (falsification orientation, anti-HARKing, provenance, fail-closed
    data contracts) already covers the failure modes; the method adds no missing capability.
- Final classification: **DISCARD AS NON-ESSENTIAL**.

## 7. Generic Backtesting

- Human disposition: **DISCARD** - not essential.
- Description from source: generic backtesting course / video material on running portfolio
  backtests with common libraries.
- ACASH assessment (`[ACASH INFERENCE]`): ACASH already operates a stronger, governed pipeline:
  Phase 5 production orchestration, D6 statistical semantics, D8-B OOS logic, Phase 6 gates
  (DSR / Holm FWER / PBO / MinTRL / SR_OOS retention), anti-HARKing grid cardinality, and manifest /
  hash provenance. A generic backtesting course is strictly below ACASH's existing standard and adds
  nothing.
- Final classification: **DISCARD AS NON-ESSENTIAL**.

## 8. ACASH Decision Matrix

Rows follow the allowed classification vocabulary:
`KEEP` | `KEEP AS OPTIONAL TOOL` | `FUTURE RESEARCH` | `DISCARD`.

| Item | Human pre-classification | Verified classification | Rationale (summary) |
| --- | --- | --- | --- |
| Academic Research Skills | KEEP | KEEP (reinforcing checklist; zero governance change) | Already represented in AGENTS.md + research_doctrine; additive value is documentation-only |
| OpenMAIC | research-assistance tooling candidate | DISCARD | Verified as education/learning platform; no research-assistance utility for ACASH workflows |
| TimesFM | future forecasting benchmark/tool | FUTURE RESEARCH | Valid forecasting benchmark candidate for a future slice; license split caveat (3.0 non-commercial) |
| LSTM stock-price prediction | DISCARD | DISCARD AS NON-ESSENTIAL | Methods already covered by ACASH philosophy; adds no missing capability |
| Generic backtesting course | DISCARD | DISCARD AS NON-ESSENTIAL | Strictly below existing Phase 5 / D6 / D8-B / Phase 6 gate infrastructure |

- ACADEMIC_RESEARCH_VALUE = KEEP.
- ACTUAL_USAGE_RULE: academic-research knowledge informs research methodology and documentation
  only; no forced integration of any external tool.

## 9. What Is Actually Added to ACASH

- Exactly one bounded documentation record (this file).
- A confirmed **reinforcing checklist** for research documentation (academic-skills mapping to
  existing governance).
- A labeled, provenance-aware record of two external tools (OpenMAIC, TimesFM) for future reference.
- Explicit license caveat for TimesFM 3.0 weights (non-commercial).
- No code, no schema, no dataset, no dependency, no configuration change. `[ACASH INFERENCE]`

## 10. What Is Explicitly NOT Added

- No new hypothesis (in particular, no HYP_003) - creating HYP_003 remains unauthorized.
- No new candidate registration in any canonical registry.
- No R1 research-project authorization.
- No empirical validation, backtest, forecast experiment, or optimization.
- No OpenMAIC integration and no OpenMAIC dependency.
- No TimesFM download, inference, or integration.
- No change to Trading state (Trading = LOCKED) and no change to Capital (CAPITAL = $0.00).

## 11. Governance Boundary

- This intake is documentation-only and changes no architectural or governance contract.
- Per AGENTS.md #1 (Zero Unverified Claims) and #6 (Literature Alignment): every external claim is
  labeled, and no capability, license, or API is asserted without a verified public source.
- Fail-closed rule: any item whose verified facts fall short of the human's initial expectation is
  classified honestly (see OpenMAIC) rather than padded to match the expectation.
- This document is not a source layer admission, not a data-source decision, and not a mechanism
  intake (MEC numbering is untouched; MEC-0011 stays CLOSED as a research checkpoint).

## 12. Final Decision

Summary for the human:

1. **Academic Research Skills - KEEP.** Already governed; recorded as a reinforcing checklist. No
   governance change.
2. **OpenMAIC - DISCARD.** Verified as an open-source multi-agent **education/learning** platform
   (THU-MAIC), not a research-assistance tool. No material utility for ACASH research/engineering
   workflows.
3. **TimesFM - FUTURE RESEARCH.** Valid forecasting benchmark candidate; registered with an explicit
   license caveat (source and weights up to v2.5 Apache-2.0; TimesFM 3.0 weights non-commercial).
   No integration.
4. **LSTM stock-price prediction - DISCARD AS NON-ESSENTIAL.**
5. **Generic backtesting course - DISCARD AS NON-ESSENTIAL** (below existing ACASH pipeline standard).

Net effect on ACASH: **zero** new code, **zero** new dependencies, **zero** governance change,
documentation-only intake.

Final confirmation statements (unchanged by this intake):
- HYP_003 NOT CREATED.
- R1 NOT AUTHORIZED.
- Trading LOCKED.
- Capital $0.00.
- No empirical validation, no forecast experiment, no backtest.
- No commit and no push were made for this document (per human instruction).