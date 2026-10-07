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
| PPDS architecture/data-contract drafts | `RESEARCH_ONLY` | Read-only decision-support direction proposed in VNext doc |
| PPDS synthetic read-only runtime (`src/acash/ppds/`, 12 tests) | `USED_IN_RUNTIME` (tooling, repair branch) | Statement ingestion, Position/Cash lots, hash-chained ledger, exact reconciliation, exposure/overlap/FX, read-only surface; synthetic fixtures only |
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
| CI / branch protection | repo settings + `.github/workflows/ci.yml` (repair branch) | `USED_IN_RUNTIME` (CI green: runs 37029140943 + 37029592071) / `BLOCKED` (branch protection ruleset not yet configured) |
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

**Capability scope**: `CANONICAL_MAIN_CAPABILITY` (merged to `origin/main`
at `becec27`) vs `REPAIR_BRANCH_CAPABILITY` (exists only on
`fix/hyp011-post-obs1-integrity-continuation-20261001` until merged).
Nothing on the repair branch becomes canonical merely by existing.

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
| PPDS Read-Only Runtime Skeleton Pack | `USED_IN_RUNTIME` (tooling, repair branch) | Implemented synthetic runtime (see §3); real statements/broker/credentials/orders still forbidden |

---

## 7. Addendum 2026-10-07 — Evidence Plane V1.1 / Canonical Main Checkpoint

**Date Context**: 2026-10-07
**Parent Canonical Merges**: PR #8 (`fcd3256f884829ceb0cfa5be30840496ce11fc65`), PR #9 (`9ed7751e05a50f2a335feebbd260da85a87654f8`)
**Active Working Branch**: PR #10 (`fix/evidence-plane-v11-prelive-correctness-20261007`)

### A. Current Asset Classification Matrix

| Asset | Status | Authority & Scientific Lineage |
|---|---|---|
| **RI-01** (Opening-State Momentum) | `FEASIBILITY_IMPLEMENTED` / `PROVIDER_PROBE_PREPARED` | Bounded probe harness implemented (`src/acash/research/ri01/probe.py`). Pre-live corrections integrated (V1.1). `NETWORK_REQUESTS_PERFORMED = 0`. Status: `PRE_LIVE_CORRECTION_REQUIRED`. No empirical provider qualification yet. |
| **RI-03A / RI-04A** (SIP / L1 Observable Proxy) | `READY_FOR_DATA_FEASIBILITY` | Alpaca historical trades/quotes proxy research. Scientific constraint: SIP lacks order IDs, true depth, and explicit aggressor tags (inference required). Must NOT be labeled "true OFI" or "true book absorption". |
| **RI-03B / RI-04B** (Direct-Feed Microstructure) | `READY_FOR_DATA_FEASIBILITY` | Direct-feed / depth research (e.g. Databento). Full book depth, explicit aggressor side, odd lots, and auction imbalances. Gated by provider entitlement / subscription cost. |
| **RI-05** (Gamma Exposure Proxy) | `READY_FOR_DATA_FEASIBILITY` | **Renamed from 'Dealer Gamma / GEX' to 'Gamma Exposure Proxy'**. Public open interest alone does not identify dealer inventory long/short positioning or customer flow direction. |
| **RI-06 / RI-08** (Options OI / IV Regimes) | `READY_FOR_DATA_FEASIBILITY` | Data feasibility path identified (Databento OPRA historical back to 2013; Alpaca options historical delayed/limited to Feb 2024). Feasibility gated by licensing/cost policy (F13). |
| **RI-09** (Time-Series Momentum) | `USED_AS_NEGATIVE_CONTROL` | `DO_NOT_RECYCLE`. Explicitly quarantined to prevent hypothesis contamination. |
| **PPDS** (Portfolio Decision Support) | `CANONICAL_SYNTHETIC_READONLY_RUNTIME` / `CANONICAL_PROVENANCE_CONSUMER` | Merged to canonical `main` in PR #9. Evidence Plane V1.1 consumer. Decoupled from RI-01; imports runtime identity from `acash.core.runtime_identity`. Synthetic read-only runtime only. Real credentials/orders forbidden. |
| **HYP_011 V1 Obs #1** | `COMMITTED_AND_RECONCILED` | Validated 2026-09-30 session. Historical V1 milestone. |
| **HYP_011 V2 Obs #1** | `MISSED_UNOBSERVED_DUE_TO_HOST_OFFLINE_AT_DISPATCH` | Scheduled 2026-10-06 03:20 ICT (session 2026-10-05). Closed via physical host boot telemetry (~71h outage from 2026-10-04 21:38 to 2026-10-07 21:06 ICT). Zero network requests, zero attempts consumed, sample advancement = 0. See `docs/audit/HYP011_V2_OBS1_FORENSIC_CLOSURE_20261007.md`. |

### B. Platform & Governance Invariants

- `REAL_CAPITAL_AUTHORITY` = `$0.00` (Strictly enforced).
- `NO_REAL_ORDERS` = `true`.
- `PAPER_TRADING_AUTHORITY` = `false`.
- `LIVE_TRADING_AUTHORITY` = `false`.
- `NETWORK_REQUESTS_PERFORMED` = `0`.
- GitHub Merge Enforcement: Repository settings (`allow_squash_merge=false`, `allow_rebase_merge=false`, `allow_merge_commit=true`) and Ruleset 24409400 strictly enforce `MERGE COMMIT` only.
