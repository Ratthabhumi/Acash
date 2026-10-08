# Research utilization checkpoint — 2026-10-08

Base: canonical main `cf63f15800099967f4c45d3df66e87a66a012eac` (PR #12).
This additive checkpoint supersedes **current-status interpretations** of
[the older matrix](RESEARCH_UTILIZATION_MATRIX.md), preserving all historical
snapshots and decision records. It issues no scientific or runtime authority.

Evidence method: inspect tracked source, governing closure records and result
manifest verdict fields. No underlying sealed datasets, real provider endpoints,
real statements or fresh Homelab telemetry were accessed. A recorded historical
result is not an independent numerical replication in this task. This distinction
applies to every `R` cell below; no profitability is newly certified.

Independent dimensions: RO research-only; I implementation exists (can be a
bounded contract/client, not full strategy); C canonical source consumer/tooling
use; D actual data feasibility; O outcome tested; N negative-control/reference
standing; B blocked/parked progression; T retired/terminal. `1` source-verified,
`0` no affirmative evidence in inspected scope, `R` governing record says yes,
`?` unknown/unverified. C does **not** certify current host deployment or trades.
Status dimensions can coexist. Negative findings are scoped to inspected paths,
not proof that no code exists anywhere in all historical branches.

## Hypotheses

| Asset | RO | I | C | D | O | N | B | T | Primary source/evidence and interpretation |
|---|---|---|---|---|---|---|---|---|---|
| HYP_001 | 0 | ? | ? | R | R | R | 0 | R | [Phase 8.5 closure](../phase8.5/phase8_5_hyp_tsmom_eurusd_001_terminal_falsification_dossier.md): terminal falsification, not merely missing Phase 14 JSON |
| HYP_002 | 0 | ? | ? | R | R | R | 0 | R | [Phase 8.5 closure](../phase8.5/phase8_5_hyp_tsmom_eurusd_002_terminal_falsification_dossier.md): terminal falsification; do not recycle quarantined samples |
| HYP_003 | 0 | 1 | ? | R | R | R | 0 | R | [Terminal dossier](../phase14/hyp_003_terminal_falsification_dossier.md), `src/acash/research/step_r3_hyp_003.py`; rejected registered mechanism |
| HYP_004 | 0 | 1 | ? | R | R | R | 0 | R | [Terminal closure](../phase14/hyp_004_terminal_closure_dossier.md), `src/acash/research/step_r4_hyp_004.py`; replication not supported; sealed external holdout preserved |
| HYP_005 | 0 | 1 | ? | 0 | 0 | 0 | R | 0 | [Entitlement block](../phase14/HYP_005_DATA_ENTITLEMENT_BLOCK_001.md), `src/acash/data/qualification/mec_0015_bar_contract.py`; contract code, no strategy outcome; non-falsifying |
| HYP_006 | 0 | 1 | ? | 0 | 0 | 0 | R | 0 | [Quote provenance amendment](../phase14/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.md), `src/acash/data/qualification/mec_0016_early_quote_contract.py`; execution-data provenance unresolved, not disproven |
| HYP_007 | 0 | 1 | ? | R | R | R | 0 | R | [Post-R4 closure](../phase14/HYP_007_POST_R4_OPERATIONAL_CLOSURE.md), `src/acash/research/step_r4_hyp_007.py`; M1 supported, M2 current edge not supported; not universally disproven |
| HYP_008 | R | 0 | 0 | 0 | 0 | 0 | 0 | R | [Pre-R1 retirement](../phase14/HYP_008_PRE_R1_RETIREMENT.md); administrative priority retirement, no empirical falsification |
| HYP_009 | 0 | 1 | 1 | R | R | R | 0 | R | [Terminal M2 decision](../phase14/HYP_009_TERMINAL_M2_DECISION.md) + result manifest, `src/acash/research/hyp_009/`, reused `hyp_009_daily_client.py`; latest lifecycle is terminal, superseding older entitlement-block wording |
| HYP_010 | 0 | 1 | ? | R | 0 | 0 | R | 0 | [Qualification summary](../phase14/HYP_010_R2_QUALIFICATION_SUMMARY.md), [parked decision](../phase14/HYP_010_PARKED_NON_FALSIFIED_BLOCKER.md), `hyp_010_qual_client.py`; tiny provider probe recorded, full economic dataset blocked by VEU authority |
| HYP_011 historical | 0 | 1 | 1 | R | R | R | 0 | 0 | [Corrected result manifest](../phase14/manifests/HYP_011_R3_CORRECTED_REPRODUCIBILITY_RESULT.json): historical replication supports prospective shadow only; platform/control baseline, not trading eligibility |
| HYP_011 V1 | 0 | 1 | R | R | R | R | 0 | R | [Segment policy](../phase14/HYP_011_PROSPECTIVE_SEGMENT_POLICY_V1_V2.md): Obs1 committed/reconciled, segment closed incomplete; one platform observation is not predictive qualification |
| HYP_011 V2 | 0 | 1 | R | 0 | 0 | R | R | R | [Forensic closure](HYP011_V2_OBS1_FORENSIC_CLOSURE_20261007.md): host offline, observation/sample 0, authority retired; live state not freshly inspected |
| HYP_011 V3 proposal | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | [Preparation](../operations/HYP011_V3_PREPARATION_20261008.md): offline proposal/preview checks only; session/runtime/ratification/runner integration unresolved |

## Research intake mechanisms

The intake names and prioritization come from the preserved
[R0 matrix](RESEARCH_UTILIZATION_MATRIX.md#2-r0-intake-mechanisms-ri-01--ri-15-originresearchr0-intake-v1-20260927).
They are navigation evidence, not ratification or empirical results. Source
inventory found the bounded RI01 implementation; do not infer a deployable
strategy from a research name or from unrelated indicators elsewhere in source.

| Asset | RO | I | C | D | O | N | B | T | Scope / evidence |
|---|---|---|---|---|---|---|---|---|---|
| RI-01 opening state | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | `src/acash/research/ri01/{probe,feasibility}.py`, mock tests; [Canary readiness](../research/ri01/RI01_CANARY1_READINESS_20261008.md); real acquisition authority absent |
| RI-02 opening range | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake, advanced sleeve on hold |
| RI-03A SIP/L1 proxy | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | Feasibility design only; SIP/L1 does not reveal full-book orders or ground-truth aggressor side |
| RI-03B direct-feed OFI | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | Depth/venue/time coverage, entitlement, licensing and cost unresolved |
| RI-04A SIP/L1 impact proxy | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | Observable proxy design, not full-book absorption |
| RI-04B depth absorption | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | Provider depth/venue feasibility and cost unresolved |
| RI-05 gamma exposure proxy | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | OI does not identify dealer signed inventory; PIT options dataset unqualified |
| RI-06 option OI change | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | PIT snapshots, publication times and licensing unresolved |
| RI-07 option flow | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake on hold; no mechanism-specific empirical evidence |
| RI-08 IV regime | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | PIT options/IV methodology and data scope unqualified |
| RI-09 time-series momentum | 1 | ? | 0 | 0 | 0 | R | R | 0 | DO_NOT_RECYCLE; HYP009/010 lineage contamination constraint; no new RI09 experiment |
| RI-10 volume spike | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake on hold |
| RI-11 overreaction | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake on hold |
| RI-12 seasonality | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake on hold |
| RI-13 relative-value pairs | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Intake on hold |
| RI-14 FVG/SMC | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Not shortlisted; no evidence upgrade from social-media framing |
| RI-15 chart features | 1 | ? | 0 | 0 | 0 | 0 | 1 | 0 | Features are not evidence of edge; not shortlisted |

## Platform and independent tooling

| Asset | RO | I | C | D | O | N | B | T | Evidence / remaining boundary |
|---|---|---|---|---|---|---|---|---|---|
| PPDS | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | `src/acash/ppds/statement_ingest.py`, `ledger.py`, `reconcile.py`, `surface.py`, `provenance.py`; canonical synthetic read-only tests, no observed real broker statement ingestion/tax use |
| Evidence Plane | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | `src/acash/evidence/` consumed by RI01 and PPDS, immutable writer/canonical digest tests; generic integrity is not empirical data qualification |
| CI/merge controls | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | Live GitHub inspected: ruleset 24409400, five required CI contexts, merge commits only; PR12 exact head and postmerge CI success |
| Existing operational monitoring | 0 | 1 | ? | 0 | 0 | 0 | 1 | 0 | `src/acash/monitoring/` exists; current host uptime/independent deployment unverified |
| V3 availability/miss preparation | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | Advisory offline classifier and external-observer design only; no production monitor installed |

No global claim of "all ACASH historical network requests = 0" is valid:
HYP010's qualification record explicitly reports 8 tiny probe HTTP attempts.
**This task's provider requests = 0**; RI01's actual account/session feasibility
remains unverified. Historical economic results do not transfer to RI01 or PPDS.

## Priority decision

1. RI01: obtain a separately approved Canary 1, distinguish retrieval from grid
   qualification, then decide whether more data feasibility is worth its cost.
   Do not implement predictive features before this resolves data availability.
2. RI03/04: only after a scientific question justifies it, review proxy vs depth
   data requirements, exact coverage and licensing/cost before acquisition.
3. RI05/06/08: later; options PIT feasibility and signed-inventory uncertainty
   can cost more than a useful test warrants. Do not buy a dataset on FOMO.
4. PPDS: independent synthetic read-only usability; a later separately approved
   real statement workflow can be useful without trading or HYP011 activation.
5. HYP011: availability first, fresh preregistration next. Platform engineering
   must not become a sunk-cost reason to restart unsupported mechanisms or
   scale capital. Additional framework PRs do not resolve empirical unknowns.

Unknowns: actual RI01 SIP availability, predictive value, PIT microstructure and
options completeness, actual host/power/BIOS/UPS bottleneck, real PPDS usability,
and future execution economics. No sealed holdout or live capital was used to
resolve them. Capital 0.00; paper/live false; NO_REAL_ORDERS true throughout.
