# Research utilization checkpoint — 2026-10-09

Base: canonical main `1362395e8463be13a8e75a5d9ef07da660f56ade` (post-PR #13 merge).
This additive checkpoint updates and supersedes the current-status interpretations of
[the 2026-10-08 checkpoint](RESEARCH_UTILIZATION_CHECKPOINT_20261008.md) and
[the older matrix](RESEARCH_UTILIZATION_MATRIX.md), while preserving all historical
snapshots, seals, and decision records intact. It issues no scientific or runtime authority.

Evidence method: inspect tracked source, governing closure records, result manifest verdict fields,
and locally audited immutable disk artifacts. A recorded historical result is not an independent
numerical replication in this task. No profitability or alpha is newly certified.

Independent dimensions:
- **RO**: Research-only (no canonical execution target)
- **I**: Implementation exists (can be bounded contract/client, not full strategy)
- **C**: Canonical source consumer/tooling use
- **D**: Actual data feasibility (observed and locally verified under strict data contract)
- **O**: Outcome tested (predictive edge / PnL / Sharpe evaluated)
- **N**: Negative-control / reference-baseline standing
- **B**: Blocked / parked progression
- **T**: Retired / terminal

Codes: `1` source/disk-verified, `0` no affirmative evidence in inspected scope, `R` governing record says yes, `?` unknown/unverified.

## Hypotheses

| Asset | RO | I | C | D | O | N | B | T | Primary source/evidence and canonical interpretation |
|---|---|---|---|---|---|---|---|---|---|
| HYP_001 | 0 | ? | ? | R | R | ? | 0 | R | [Phase 8.5 closure](../phase8.5/phase8_5_hyp_tsmom_eurusd_001_terminal_falsification_dossier.md): terminal falsification. Terminal status does not automatically grant negative-control standing. |
| HYP_002 | 0 | ? | ? | R | R | ? | 0 | R | [Phase 8.5 closure](../phase8.5/phase8_5_hyp_tsmom_eurusd_002_terminal_falsification_dossier.md): terminal falsification; quarantined samples preserved. |
| HYP_003 | 0 | 1 | ? | R | R | R | 0 | R | [Terminal dossier](../phase14/hyp_003_terminal_falsification_dossier.md), `src/acash/research/step_r3_hyp_003.py`; rejected registered mechanism; verified negative reference baseline. |
| HYP_004 | 0 | 1 | ? | R | R | R | 0 | R | [Terminal closure](../phase14/hyp_004_terminal_closure_dossier.md), `src/acash/research/step_r4_hyp_004.py`; replication not supported; sealed external holdout preserved; reference baseline. |
| HYP_005 | 0 | 1 | ? | 0 | 0 | 0 | R | 0 | [Entitlement block](../phase14/HYP_005_DATA_ENTITLEMENT_BLOCK_001.md), `src/acash/data/qualification/mec_0015_bar_contract.py`; contract code exists; data entitlement blocked; non-falsifying. |
| HYP_006 | 0 | 1 | ? | 0 | 0 | 0 | R | 0 | [Quote provenance amendment](../phase14/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.md), `src/acash/data/qualification/mec_0016_early_quote_contract.py`; quote provenance unresolved, not disproven. |
| HYP_007 | 0 | 1 | ? | R | R | ? | 0 | R | [Post-R4 closure](../phase14/HYP_007_POST_R4_OPERATIONAL_CLOSURE.md), `src/acash/research/step_r4_hyp_007.py`; **registered M1 historical replication supported**, **M2 current edge not supported**; combined standing `HISTORICAL_REPLICATION_SUPPORTED_BUT_CURRENT_EDGE_NOT_SUPPORTED`. Negative-control designation is not established by this closure. |
| HYP_008 | R | 0 | 0 | 0 | 0 | 0 | 0 | R | [Pre-R1 retirement](../phase14/HYP_008_PRE_R1_RETIREMENT.md); **administrative priority retirement**, NOT an empirical falsification. |
| HYP_009 | 0 | 1 | 1 | R | R | ? | 0 | R | [Terminal M2 decision](../phase14/HYP_009_TERMINAL_M2_DECISION.md) + result manifest, `src/acash/research/hyp_009/`; terminal lifecycle; negative-control standing unverified. |
| HYP_010 | 0 | 1 | ? | R | 0 | 0 | R | 0 | [Qualification summary](../phase14/HYP_010_R2_QUALIFICATION_SUMMARY.md), [parked decision](../phase14/HYP_010_PARKED_NON_FALSIFIED_BLOCKER.md); **PARKED_NON_FALSIFIED**; blocked by VEU data authority, not strategy failure. |
| HYP_011 hist | 0 | 1 | 1 | R | R | R | 0 | 0 | [Corrected result manifest](../phase14/manifests/HYP_011_R3_CORRECTED_REPRODUCIBILITY_RESULT.json): platform/control baseline only, not live eligibility. |
| HYP_011 V1 | 0 | 1 | R | R | R | ? | 0 | R | [Segment policy](../phase14/HYP_011_PROSPECTIVE_SEGMENT_POLICY_V1_V2.md): Obs1 reconciled, segment closed incomplete; negative-control designation not verified for this segment. |
| HYP_011 V2 | 0 | 1 | R | 0 | 0 | ? | R | R | [Forensic closure](HYP011_V2_OBS1_FORENSIC_CLOSURE_20261007.md): **MISSED_UNOBSERVED_DUE_TO_HOST_OFFLINE**; 0 observations, 0 samples; authority retired; produced no market observation or verified negative-control sample. |
| HYP_011 V3 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | [Preparation](../operations/HYP011_V3_PREPARATION_20261008.md): offline proposal only; requires preregistered dispatch-window availability and rehearsal; host availability unverified. |

## Research intake mechanisms

| Asset | RO | I | C | D | O | N | B | T | Scope / evidence |
|---|---|---|---|---|---|---|---|---|---|
| RI-01 opening state | 0 | 1 | 1 | **1** | 0 | 0 | 1 | 0 | `src/acash/research/ri01/{probe,feasibility}.py`; **Canary 1 DATA_FEASIBILITY_PASS** (2021-06-01 SIP 1Min raw, 390 RTH grid verified on disk); Canary 2 unissued; **NOT STRATEGY_VALIDATED**. |
| RI-02 opening range | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake, advanced sleeve on hold. |
| RI-03A SIP/L1 proxy | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | Feasibility design only; SIP/L1 does not reveal full book or ground-truth aggressor side. |
| RI-03B direct-feed OFI | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | Depth/venue/time coverage, entitlement, licensing and cost unresolved. |
| RI-04A SIP/L1 impact proxy | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | Observable proxy design, not full-book absorption. |
| RI-04B depth absorption | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | Provider depth/venue feasibility and cost unresolved. |
| RI-05 gamma exposure proxy | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | OI does not identify dealer signed inventory; PIT options dataset unqualified. |
| RI-06 option OI change | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | PIT snapshots, publication times and licensing unresolved. |
| RI-07 option flow | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake on hold; no mechanism-specific empirical evidence. |
| RI-08 IV regime | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | PIT options/IV methodology and data scope unqualified. |
| RI-09 time-series momentum | 1 | ? | 0 | 0 | 0 | R | R | 0 | DO_NOT_RECYCLE; lineage contamination constraint; no new experiment. |
| RI-10 volume spike | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake on hold. |
| RI-11 overreaction | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake on hold. |
| RI-12 seasonality | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake on hold. |
| RI-13 relative-value pairs | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake on hold. |
| RI-14 FVG/SMC | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Not shortlisted; retail/social-media framing without empirical grounding. |
| RI-15 chart features | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Features are not evidence of edge; not shortlisted. |

## Platform and independent tooling

| Asset | RO | I | C | D | O | N | B | T | Evidence / remaining boundary |
|---|---|---|---|---|---|---|---|---|---|
| PPDS | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | `src/acash/ppds/`; canonical synthetic read-only tests pass; strictly decoupled from live brokers and personal tax workflow. |
| Evidence Plane | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | `src/acash/evidence/` V1.1 active; immutable digest lineage enforced for RI-01 and PPDS. |
| CI/merge controls | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | Historical checkpoint: PR #12 and #13 merged; CI run `37793131851` recorded 5/5 SUCCESS; 0 open PRs at that checkpoint. This does not certify a later PR or current ruleset configuration. |
| Homelab pin | 0 | 1 | R | 0 | 0 | 0 | 1 | 0 | Recorded pin `6395b384893ac0160b4ce8df3f4bcc0d332b3d9e`; current host runtime not independently inspected here; no deployment performed. |

## Data privacy and metadata redaction boundaries

- **Raw SIP Market Data**: File `page_0000.bin` contains raw Consolidated Tape minute bars subject to Alpaca redistribution restrictions. It must remain strictly in local external evidence storage and must never be committed to public Git.
- **Metadata Sanitization**: Manifests and approval receipts contain machine-local paths, user paths, and authorization identifiers. All summaries shared across environments or committed to Git must be sanitized and free of host-private or credential artifacts.
- **Fail-Closed Principle**: Zero live orders, zero real capital ($0.00), zero paper/live trading authority.

## Publication verification boundary — 2026-10-11

This checkpoint was recovered from unpublished V8.1 local work. Publication
does not issue Canary 2 authority or change a hypothesis standing. Canary 1
immutable local evidence is retained outside Git; only its bounded audited
interpretation belongs here. Canonical manifest/qualification JSON digests
must not be described as hashes of their formatted file bytes.

Canary 2 remains **CANARY2_AWAITING_OPERATOR_AUTHORIZATION**. See the
[review runbook](../research/ri01/RI01_CANARY2_READINESS_20261009.md).
The unissued JSON is deliberately non-executable. Synthetic HTTP transport
tests establish software contracts only; they are not observed provider data,
strategy validation, capital authority, or future dispatch reliability.
