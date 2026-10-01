# ACASH Research Utilization Matrix (Point-in-Time Survey)

**Date Context**: 2026-10-01
**Scope**: read-only survey of where existing research assets stand. No new
research claims, no backtests, no empirical use beyond what is recorded.
**Status key**: `USED_IN_RUNTIME` / `USED_IN_GOVERNANCE` / `USED_AS_NEGATIVE_CONTROL` /
`READY_FOR_DATA_FEASIBILITY` / `RESEARCH_ONLY` / `BLOCKED` / `STALE_OR_SUPERSEDED`

> Do not treat HYP_011 as the definition of ACASH. HYP_011 is one
> baseline/control experiment proving the research platform works.

---

## 1. Hypotheses HYP_001 – HYP_011

| Asset | Location / Branch | Status | Note |
|---|---|---|---|
| HYP_001, HYP_002 | historical refs | `RESEARCH_ONLY` | No sealed phase14 JSON found on `main`; verify lineage before any use |
| HYP_003 | `docs/phase14/` + terminal falsification dossier | `USED_AS_NEGATIVE_CONTROL` | Terminal dossier recorded; failure-decomposition method reused as control discipline |
| HYP_004 | `docs/phase14/` + terminal closure dossier | `USED_AS_NEGATIVE_CONTROL` | Closed; log-return robustness method retained as reference |
| HYP_005 | `docs/phase14/HYP_005_DATA_ENTITLEMENT_BLOCK_001.md` | `BLOCKED` | Data entitlement block; non-falsifying |
| HYP_006 | `docs/phase14/` R1 quote-provenance amendment | `RESEARCH_ONLY` | Amendment track; not yet empirical |
| HYP_007 | `docs/phase14/` terminal M1 decision dossier | `USED_AS_NEGATIVE_CONTROL` | Closed; partition/governance method retained |
| HYP_008 | `docs/phase14/HYP_008_PRE_R1_RETIREMENT.md` | `STALE_OR_SUPERSEDED` | Retired pre-R1 by design |
| HYP_009 | `docs/phase14/` entitlement block + daily SIP path (`hyp_009_daily_client`) | `BLOCKED` + `USED_IN_RUNTIME` (infra only) | Hypothesis blocked; daily provider/contract machinery reused as platform capability |
| HYP_010 | `docs/phase14/` R1 area | `RESEARCH_ONLY` | Early R1; verify current standing before use |
| HYP_011 historical replication | `docs/phase14/` R3 seals | `USED_IN_GOVERNANCE` | Gating authority for prospective shadow arming |
| HYP_011 prospective shadow | `src/acash/research/hyp_011/` + runner | `USED_IN_RUNTIME` | Baseline/control experiment; Obs #1 `COMMITTED_AND_RECONCILED`, S1=1/20 |

## 2. R0 Intake Mechanisms RI-01 – RI-15 (`origin/research/r0-intake-v1-20260927`)

R0 governance permits ONLY a Zero-Outcome Data Feasibility Audit next (separate
authorization required). No mechanism has empirical use.

| Mechanism | Status | Note |
|---|---|---|
| RI-01 opening-state momentum | `READY_FOR_DATA_FEASIBILITY` | Shortlist A |
| RI-02 opening-range breakout | `RESEARCH_ONLY` | Advanced sleeve / on hold per R0 |
| RI-03 order-flow imbalance | `READY_FOR_DATA_FEASIBILITY` | Shortlist B |
| RI-04 absorption/impact efficiency | `READY_FOR_DATA_FEASIBILITY` | Shortlist B |
| RI-05 dealer gamma/GEX regime | `READY_FOR_DATA_FEASIBILITY` | Shortlist C |
| RI-06 option OI changes | `READY_FOR_DATA_FEASIBILITY` | Shortlist C |
| RI-07 intraday option flow | `RESEARCH_ONLY` | On hold per R0 |
| RI-08 IV expected-move regime | `READY_FOR_DATA_FEASIBILITY` | Shortlist C |
| RI-09 time-series momentum | `USED_AS_NEGATIVE_CONTROL` | `DO_NOT_RECYCLE` into CORE-002 (HYP_009/HYP_010 contamination) |
| RI-10 volume-spike breakout | `RESEARCH_ONLY` | On hold per R0 |
| RI-11 mean-reversion overreaction | `RESEARCH_ONLY` | On hold per R0 |
| RI-12 calendar/weekday seasonality | `RESEARCH_ONLY` | On hold per R0 |
| RI-13 relative-value pairs | `RESEARCH_ONLY` | On hold per R0 |
| RI-14 FVG/SMC | `RESEARCH_ONLY` | Not shortlisted |
| RI-15 EMA/chart/candlestick features | `RESEARCH_ONLY` | Not shortlisted |

## 3. PPDS (`origin/research/ppds-r0-capital-broker-architecture-20260928`)

| Asset | Status | Note |
|---|---|---|
| PPDS architecture/data-contract drafts | `RESEARCH_ONLY` | Runtime 0%; read-only decision-support direction proposed in VNext doc |
| Broker adapter contract draft | `RESEARCH_ONLY` | No endpoint wired |
| Dime/Webull/IBKR/futures due diligence | `RESEARCH_ONLY` | Feeds VNext read-only ingestion proposal |
| Thai tax ledger requirements | `USED_IN_GOVERNANCE` | Compliance boundary reference |
| Personal capital governance draft | `BLOCKED` | Unresolved policy; no allocation authority |

## 4. Governance & Platform
| Asset | Location | Status | Note |
|---|---|---|---|
| Operator decision charter v1 | `origin/governance/operator-decision-charter-v1` | `USED_IN_GOVERNANCE` | Active principles reference |
| Operator charter audit | `origin/governance/operator-charter-audit-v1-20260928` | `USED_IN_GOVERNANCE` | Audit lineage |
| CORE-001 observability dashboard | `origin/feature/core001-observability-dashboard-v1` | `RESEARCH_ONLY` | Branch-only; not canonical |
| Research-foundation review | `origin/review/research-foundation-pre-empirical` | `USED_IN_GOVERNANCE` | Pre-empirical gate record |
| CI / branch protection | repo settings | `BLOCKED` | Zero runs; human review only |
| Broker/API transport research | PPDS docs | `RESEARCH_ONLY` | Not connected to any runtime |
| Corporate-action sponsor research | this pack §E + F10 tooling | `USED_IN_RUNTIME` (tooling) / `USED_IN_GOVERNANCE` (scope) | AGG amount established; intake enforced end-to-end on repair branch |
| F11 Docker provenance | finding register | `BLOCKED` | Unresolved |
| F12 deployment/network isolation | finding register | `BLOCKED` | No live host audit performed |
| F13 public/proprietary policy | finding register | `BLOCKED` | Undecided |

---

## 5. Standing Rule

New empirical use of any `READY_FOR_DATA_FEASIBILITY` asset requires a
separate explicit human authorization scoped to zero-outcome feasibility
only. Matrix status changes only via committed evidence, never by assertion.

---

## 6. Addendum 2026-10-01 — Evidence-Kernel Hardening Pack (repair branch)

| Asset | Status | Note |
|---|---|---|
| F17 registered-intent tooling | `USED_IN_RUNTIME` (tooling) | Create-once registry + dispatch binding; honest privileged-host boundary documented |
| F18 attempt-boundary reorder + `--local-preflight` | `USED_IN_RUNTIME` (tooling) | Local failure burns nothing; post-consume crash burns; preflight proves green with zero network |
| F19 evidence-bundle tooling | `USED_IN_RUNTIME` (tooling) | Raw-byte digests + frozen product identity (239600=ACWI); row-2 239707 attribution void |
| ACWI/AGG/SPY corrected raw evidence | `USED_IN_GOVERNANCE` (scope) | `docs/audit/ca_evidence_2026_10_01/` + corrected scope note §§5–6; no Obs #2 determination created |
| Evidence Kernel extraction plan | `RESEARCH_ONLY` | `docs/audit/EVIDENCE_KERNEL_EXTRACTION_PLAN.md`; design only, no package move |
| RI-01 Zero-Outcome Data Feasibility Pack | `READY_FOR_DATA_FEASIBILITY` | Questions pack prepared; execution needs separate authorization |
| PPDS Read-Only Runtime Skeleton Pack | `READY_FOR_DATA_FEASIBILITY` | Synthetic-fixture skeleton prepared; no credentials/statements/orders |
