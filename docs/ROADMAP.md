# 🚀 ACASH — Unified Development Roadmap

*From Market Data to Evidence-Based Capital Allocation*

**Version:** 4.0.0 · **AS OF:** 2026-10-15 (Asia/Bangkok) · **Scope:** delivery taxonomy and capability reuse; no new scientific gate or operating authority.

> **V23 addendum - 2026-10-23 (additive; historical sections preserved):** D3 V2 is
> implemented but `PENDING_FORMAL_RATIFICATION`. The offline D5 real-input admission
> bridge is implemented in `src/acash/data/qualification/lane_b_d5_rehearsal.py` with
> `RETROSPECTIVE_QUALITY_QUALIFIED` and `PIT_EVIDENCE_QUALIFIED` gates; no real bundle is
> admitted. The consolidated owner decisions are in
> `docs/governance/OWNER_DECISION_PACKET_20261023.md`. Lane A/B remain `UNISSUED`,
> `REAL_CAPITAL_AUTHORITY = USD 0.00` and `NO_REAL_ORDERS=true`.

## 🎯 1. Vision & North Star

ACASH is a governed quantitative research, portfolio evaluation and capital-allocation system. Its purpose is to support evidence-based allocation decisions, including **CASH / NO TRADE**. The first hypothetical **USD 1,000** after-cost study is a practical milestone, not a permanent portfolio size or the final objective.

Scientific evidence, software readiness, data qualification, strategy qualification, operational readiness, human authorization and real-capital authority are separate requirements. Historical achievements retain their original scope; none grants admission to a new investment program.

## 🗺️ Unified Delivery D1–D10 — at a glance

| Stage | Capability already available | Current Invest / Lane A admission | Next delivery |
| --- | --- | --- | --- |
| **D1 🧱 Offline Data Foundation** | IMPLEMENTED · SYNTHETIC_TESTED | INTEGRATED (PR #32 merged); no executor/authority implied | D3 admission prerequisites next |
| **D2 🛡️ Real Data Acquisition Safety** | PARTIAL · SYNTHETIC_TESTED | INTEGRATED offline slice (PR #37/#39 merged); EVIDENCE_INCOMPLETE for dispatch | Close verifier, entitlement, byte and durability contracts |
| **D3 📡 Authorized Market Data Acquisition** | HISTORICALLY_EXECUTED in HYP_009/010/011 | AUTHORITY_UNISSUED · ENTITLEMENT_UNVERIFIED | Exact-scope operator decision after D2 acceptance |
| **D4 🔬 Data & Corporate-Action Qualification** | SCIENTIFICALLY_QUALIFIED_FOR_ORIGINAL_SCOPE | SCOPE_NOT_ADMITTED | Qualify new prices and issuer/sponsor evidence |
| **D5 🗃️ Qualified Historical Dataset** | SCIENTIFICALLY_QUALIFIED_FOR_ORIGINAL_SCOPE | SCOPE_NOT_ADMITTED | Separately authorize and seal new historical scope |
| **D6 💰 Investment Economics** | IMPLEMENTED · HISTORICALLY_EXECUTED | LOCAL_EXPLORATORY EXECUTED (V32–V37B); D5 UNADMITTED | Formal D5-qualified study pending data rights |
| **D7 🧠 Governed Strategy Research** | IMPLEMENTED tooling; historical research exists | SCIENTIFICALLY_BLOCKED for new candidates | Use qualified baseline or separately admitted hypothesis |
| **D8 👁️ Prospective Shadow Validation** | IMPLEMENTED · HISTORICALLY_EXECUTED | AUTHORITY_UNISSUED for new program | PROPOSED stage; resolve segment/continuation authority |
| **D9 🧪 Paper Trading & Operational Validation** | IMPLEMENTED · HISTORICALLY_EXECUTED | AUTHORITY_UNISSUED for ongoing program | PROPOSED stage; separate Human GO and paper gates |
| **D10 🔐 Human-Gated Live Capital Admission** | IMPLEMENTED risk/execution/recovery | CAPITAL_LOCKED | PROPOSED stage; explicit human decision, including NO-GO |

**One active sequence:** Unified Delivery D1–D10. Phase 0–23 labels describe historical architecture/capabilities. D8–D10 are proposed delivery extensions, not ratified operating transitions. Capability labels and admission labels are separate dimensions; combinations in a row are scope-specific, not a global PASS.

### Navigation

- [Verified current position](#verified-position)
- [Stage details D1–D10](#stage-details)
- [Legacy numbering and phase mapping](#legacy-mapping)
- [Research reuse](#research-reuse)
- [Dependencies and human authority](#dependencies)
- [Next actions and Research handoff](#next-actions)
- [Historical evidence and reference compatibility](#historical-evidence)

<a id="verified-position"></a>
## 📍 2. Verified Current Position

> **Status update 2026-10-16 (additive; the 2026-10-15 checkpoint below is preserved as history):** PR #32 (D1 canary), PR #37 (D2 safety), PR #39 (D2 composition), and PR #36 (docs consistency) are MERGED into canonical `main`. D1 offline foundation and D2 offline safety/composition are therefore **integrated offline software** — still with **no real executor, no entitlement, and no acquisition authority**. Verify live GitHub state before acting.

GitHub PR metadata and PR-triggered CI were read on 2026-10-15. This is a dated checkpoint, not a live status feed. Canonical `main` *then*: `250bf0304d763cb86f961ca26b5c5771421a23ab` (PR #35). Roadmap preparation is stacked on PR #36, `87e1176adb2f9541773b4b3d87c479691f5e11d2`; its documentation corrections are not yet on main.

| Work status at 2026-10-15 checkpoint (historical) | Exact HEAD then | GitHub state then / PR-triggered CI |
| --- | --- | --- |
| [PR #32: offline canary](https://github.com/Ratthabhumi/Acash/pull/32) | `49b86236796f859e2918cf4b9c228a8eff0b9fd1` | was OPEN/READY; **MERGED** (`bfffdb3`); [CI success](https://github.com/Ratthabhumi/Acash/actions/runs/38570998061) |
| [PR #36: documentation consistency](https://github.com/Ratthabhumi/Acash/pull/36) | `87e1176adb2f9541773b4b3d87c479691f5e11d2` | was OPEN/READY; **MERGED** (`16901bf`); [CI success](https://github.com/Ratthabhumi/Acash/actions/runs/38570849800) |
| [PR #37: legacy D1 safety slice, now Unified Delivery D2](https://github.com/Ratthabhumi/Acash/pull/37) | `3bc252d26fbefac6b7085a82cd46c2e00f6d037c` | was OPEN/DRAFT; **MERGED** (`3255da9`); [CI success](https://github.com/Ratthabhumi/Acash/actions/runs/38635592493) |

**Integrated:** M1.6 benchmark contracts, M1.7 planner, M1.8 rehearsal, M1.8.1 storage/evidence, PPDS and Invest V0. **Update 2026-10-16:** D1 canary (PR #32), D2 safety (PR #37), D2 composition (PR #39), and docs consistency (PR #36) are MERGED; only the roadmap PR #38 remains open. The PR #32 description reports 39 focused canary tests; PR #37 reports 14 MockTransport tests. These are historical reports, not local reruns in this documentation task; green CI does not prove live-dispatch safety or entitlement.

**Hard boundaries:** `REAL_CAPITAL_AUTHORITY = USD 0.00`; `NO_REAL_ORDERS=true`; Lane A **UNISSUED**. No provider HTTP, credential use, subscription purchase, protected dataset access, broker authentication, paper/live order, Homelab deployment or PR merge is authorized by this roadmap. Historical authorizations below remain bounded to their own decisions.

> **Status update 2026-10-30 — V37B Integration (additive; historical checkpoints preserved):**
> 1. **D6 Investment Economics Studies Executed (LOCAL_EXPLORATORY):**
>    The USD 1,000 after-cost baseline investment study was fully executed across four research cycles:
>    - [V35 Monthly Contribution Study](research/D6_V35_CONTRIBUTION_STUDY_RESULTS_20261025.md) (PR #65)
>    - [V36 Cost & Funding Audit](research/D6_V36_FUNDING_COST_AUDIT_RESULTS_20261026.md) (PR #66)
>    - [V37A Fixed-THB Funding](research/V37A_FIXED_THB_RESULTS_20261027.md) (PR #68)
>    - [V37B Research Evidence Integration](research/D6_V37B_RESEARCH_EVIDENCE_INTEGRATION_20261030.md)
>    - [V38 Retail Funding Feasibility & Investor Decision Core](research/D6_V38_RETAIL_FUNDING_FEASIBILITY_20261030.md) (PR #71; multi-broker comparison across IBKR, Dime!, Webull Thailand, CASH; pure Decimal fail-closed; unknown FX spread lower bounds; external research handed off to ChatGPT)
> 2. **Distinctions & Governance Boundary:**
>    - *Implemented engineering capabilities:* D6 portfolio execution engine (`run_d6_portfolio`), cash conservation reconciliation, dated THB savings ledgers, independent Evidence Overlay.
>    - *LOCAL_EXPLORATORY findings:* Retrospective sensitivity grids across 2016–2025 demonstrate funding cadence (monthly vs quarterly vs annual) and transaction frictions dominate asset-allocation differences at retail sizes; results are descriptive and exploratory.
>    - *V37B independent evidence observations (integrity-closed; PR #70 merged 2026-10-30 under owner conditional authority, merge `a6eae54`):* Read-only Evidence Overlay. 3 BND capital-gain components (2 events) match provider rows on OCC/MIAX event evidence; SEC ETF-share annual totals read from source: FY2019 and FY2021–2025 consistent, FY2016–2018 provider-classification differences (no cash difference), FY2020 unresolved 0.0006 presentation/basis difference; QSG listings are fund-level tax-year designations only; 63 imputed payable dates remain unverified; source rights `RIGHTS_UNVERIFIED`.
>    - *Formal D5 admission status:* **SCOPE_NOT_ADMITTED** (0/40 symbol-year cells admitted). No retrospective data is promoted to D5.
>    - *Strategy scientific qualification:* **SCIENTIFICALLY_BLOCKED** for new candidate strategies. SAT-OPTIONS-001 and ATrain IV Walls remain strictly research-intake concepts.
>    - *Operating authorities:* `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`, `LANE_A/B = UNISSUED`.
>    - *Pending owner decisions:* Clarification of corporate data rights / bulk export license; explicit ratification required before any D5 admission or D7 strategy initiative.

<a id="stage-details"></a>
## 🗺️ 3. Stage Details

Every stage records objective, source/tests, historical evidence and reuse, missing work, current admission, authority, acceptance and next action. Test links identify existing verification entry points, not freshly executed results.

### D1 — 🧱 Offline Data Foundation

**Objective / standing:** reuse a single canonical request planner and bounded offline evidence pipeline. IMPLEMENTED / SYNTHETIC_TESTED; integrated foundations, canary INTEGRATED (PR #32 merged `bfffdb3`). Historical mapping: Phase 2/3/14 and M1.7–M1.8.1.

**Source / tests:** [authority planner](../src/acash/data/qualification/lane_a_authority.py), [rehearsal](../src/acash/data/qualification/lane_a_rehearsal.py), [transport/evidence](../src/acash/data/qualification/lane_a_transport.py); [authority tests](../tests/unit/data/test_lane_a_authority.py), [rehearsal tests](../tests/unit/data/test_lane_a_rehearsal.py), [transport tests](../tests/unit/data/test_lane_a_transport.py). PR #32 added [canary source at reviewed HEAD](https://github.com/Ratthabhumi/Acash/blob/49b86236796f859e2918cf4b9c228a8eff0b9fd1/src/acash/data/qualification/lane_a_canary.py) and [tests](https://github.com/Ratthabhumi/Acash/blob/49b86236796f859e2918cf4b9c228a8eff0b9fd1/tests/unit/data/test_lane_a_canary.py), now integrated on `main`.

**Reuse / evidence:** nine-field request serialization, request budgets, reservation journals, fake transport, receipt/page hashing and offline runner. Offline pagination completion is not data qualification; file-sync evidence is not proven crash durability.

**Missing / authority / acceptance / next:** Preserve canonical request identity and fail-closed journals; no HTTP activation. **Do not rebuild** planner, journals, rehearsal or offline runner.

### D2 — 🛡️ Real Data Acquisition Safety

**Objective / standing:** prepare an auditable bounded executor without activation. PARTIAL / SYNTHETIC_TESTED; offline slice INTEGRATED (PR #37 merged `3255da9`, composition PR #39 merged `e61dd24`), production EVIDENCE_INCOMPLETE. Historical mapping: Phase 2/3/14 acquisition controls.

**Source / tests:** existing [SIP client and error taxonomy](../src/acash/data/qualification/client.py), M1.7 planner and M1.8.1 journal above. PR #37 contains [safety source](https://github.com/Ratthabhumi/Acash/blob/3bc252d26fbefac6b7085a82cd46c2e00f6d037c/src/acash/data/qualification/lane_a_d1_safety.py) and [MockTransport tests](https://github.com/Ratthabhumi/Acash/blob/3bc252d26fbefac6b7085a82cd46c2e00f6d037c/tests/unit/data/test_lane_a_d1_safety.py). Its legacy D1 identifier is retained in filenames.

**Reuse / evidence:** canonical requests, HTTPX exception classes, page SHA helpers, zero-retry and credential-isolation preparation. The draft demonstrates offline behavior, not production approval.

**Missing:** `destination_guard()` now enforces exact HTTPS origin/path with userinfo, port, encoding, query, and fragment rejection (merged PR #37; adversarial tests cover suffix, userinfo, and port variants). `iter_bytes()` counts decoded bytes: raw-versus-decoded budget semantics still need a decision. Durable reserve-before-real-dispatch linkage, independent production approval verifier/trust root, actual account/feed entitlement and audited activated production executor are not proven. The current disabled boundary always refuses real transport.

**Authority / acceptance / next:** independent software review must close these contracts and define evidence durability before any separately authorized acquisition. Keep HTTP blocked; review the draft in its own PR. **Do not rebuild** the existing SIP client core, planner, error taxonomy or hashing; legacy retry behavior must not silently enter Lane A's zero-retry scope.

### D3 — 📡 Authorized Market Data Acquisition

**Objective / standing:** obtain only exact-authorized provider evidence. HISTORICALLY_EXECUTED; new Lane A AUTHORITY_UNISSUED / ENTITLEMENT_UNVERIFIED. Historical mapping: Phase 14 provider qualification with Phase 2/3 adapters.

**Source / tests:** [HYP_009 client](../src/acash/data/qualification/hyp_009_daily_client.py), [HYP_010 client](../src/acash/data/qualification/hyp_010_qual_client.py), [HYP_011 client](../src/acash/data/qualification/hyp_011_qual_client.py); [HYP_011 qualification tests](../tests/unit/data/qualification/test_hyp_011_qualification.py) and D1/D2 suites.

**Historical evidence / reuse:** [HYP_009](phase14/HYP_009_R2_M2_DATA_QUALIFICATION.md): 2 Alpaca attempts, SPY 2021–2024; [HYP_010](phase14/HYP_010_R2_PROVIDER_QUALIFICATION.md): 8 SIP attempts, SPY/VEU/AGG/BIL January 2017; [HYP_011](phase14/HYP_011_R3_HISTORICAL_DATA_QUALIFICATION.md): 6 attempts, ACWI/AGG/SPY 2016–2024. [Observation #1](audit/OBSERVATION_0001_COMMITTED_RECONCILED_20260930.md) separately records 6 prospective requests under its own authority. Reuse pagination, session census and 15-minute guard methodology without transferring authority.

**Missing / authority:** [Lane A candidate packet](research/LANE_A_UNISSUED_AUTHORITY_PACKET_20261013.md) remains UNISSUED: Alpaca `GET /v2/stocks/bars`, VOO/BND/GLD/BIL, `1Day`, 2026-09-28 through 2026-10-02 inclusive, `raw` and `all`, one operator-selected IEX or SIP feed, at most 12 HTTP attempts and 524288 observed response bytes, USD 0 paid, no retry/fallback.

**Acceptance / next:** after D2 acceptance and exact-scope human issuance, preserve every attempt/outcome and payload lineage within bound budgets. Five-session retrieval proves feasibility only. No request is initiated by this documentation task.

### D4 — 🔬 Data & Corporate-Action Qualification

**Objective / standing:** qualify each symbol/session and corporate-action authority. SCIENTIFICALLY_QUALIFIED_FOR_ORIGINAL_SCOPE; new VOO/BND/GLD/BIL SCOPE_NOT_ADMITTED. Historical mapping: Phase 2/3/14.

**Source / tests:** [qualification validator](../src/acash/data/qualification/validator.py), [HYP_011 qualification client](../src/acash/data/qualification/hyp_011_qual_client.py), [benchmark contracts](../src/acash/data/contracts/etf_fx_benchmark.py); [qualification tests](../tests/unit/data/qualification/test_hyp_011_qualification.py), [benchmark tests](../tests/unit/data/test_etf_fx_benchmark_contracts.py).

**Historical evidence / reuse:** [HYP_011 R3 seal](phase14/HYP_011_R3_HISTORICAL_DATA_QUALIFICATION.md) records ACWI/AGG/SPY, 2016–2024, **2264 NYSE sessions**, zero missing/extra/duplicates, raw/split alignment, 164 in-scope dividend events, no split events in the authorized window and historical fee authority. HYP_009 has its own [qualification and dividend-coverage limitations](phase14/HYP_009_R2_M2_DATA_QUALIFICATION.md). Reuse validators, session census, raw/adjusted semantics and sponsor methodology.

**Missing / authority / acceptance / next:** new ETF price evidence and issuer/sponsor dividends/splits require their own authorized qualification. Lane B is [specified](research/LANE_B_SPEC_OFFLINE_QUALIFICATION.md), not admitted evidence. Reject incomplete coverage, ambiguous share basis, unverified corporate actions and PIT claims. Do not infer new issuer evidence from HYP_011 or promote old data to the new program.

### D5 — 🗃️ Qualified Historical Dataset

**Objective / standing:** reproducible, scope-sealed historical inputs. **HISTORICAL_QUALIFICATION_EXISTS / NEW_INVEST_SCOPE_NOT_ADMITTED**; capability SCIENTIFICALLY_QUALIFIED_FOR_ORIGINAL_SCOPE, new-scope admission SCOPE_NOT_ADMITTED. Historical mapping: Phase 2/3/14.

**Source / tests:** qualification and manifest pipeline above; [HYP_011 dataset manifest](phase14/manifests/HYP_011_R3_HISTORICAL_DATASET.json), [HYP_009 dataset manifest](phase14/manifests/HYP_009_R2_M2_DATASET.json); existing qualification and benchmark tests.

| Original-scope dataset | Recorded SHA-256 |
| --- | --- |
| `DS_CORE001_HYP011_ACWI_AGG_SPY_ALPACA_1DAY_SIP_2016_2024_001` | `4cf20b51c2e2be2bb629ba10be7c25b34e8259bd5549575156afe433fb16c3d5` |
| HYP_009 `DS_SPY_CORE001_HYP009_M2_ALPACA_1DAY_SIP` | `7961f19b6fa4cc752c1dae328001ea396f7b492b53f42d3898ae6b743f37c4d1` |

These identities are read from committed qualification records/manifests; protected dataset bytes were not opened or rehashed here. Raw dataset files are gitignored and are not guaranteed in a fresh checkout.

**Reuse / missing / authority / acceptance / next:** reuse dataset builders, provenance validation and sealing methodology. A new historical universe/window requires explicit authority, D4 evidence, inception/vintage/PIT limitations and its own immutable manifest. Do not gratuitously rebuild historical datasets or assume this five-session candidate qualifies a multi-year study.

### D6 — 💰 Investment Economics

**Objective / standing:** evaluate after-cost allocation choices on matched evidence. IMPLEMENTED / HISTORICALLY_EXECUTED; USD 1,000 study EVIDENCE_INCOMPLETE. Historical mapping: Phase 5/8/8.5/9, PPDS, Invest V0 and M1.6.

**Source / tests:** [backtest](../src/acash/backtest/), [portfolio](../src/acash/portfolio/), [PPDS](../src/acash/ppds/), [Invest V0](../src/acash/invest/v0_report.py), M1.6 benchmark contracts; [synthetic benchmark workflow](../tests/unit/data/test_synthetic_m1_5_workflow.py), [Invest V0 tests](../tests/unit/invest/test_v0_report.py).

**Historical evidence:** [HYP_011 execution](phase14/HYP_011_R3_HISTORICAL_EXECUTION_REPORT.md) records simulated USD **100000 → 218852.857740**, Sharpe approximately **0.7082**, MDD **0.27068**, dividends **28501.574104**, friction stress and SPY/ACWI comparisons. G1–G6 PASS applies only to the original frozen contract. [Corrected reproducibility](phase14/HYP_011_R3_CORRECTED_REPRODUCIBILITY_COMPARISON.md) preserves all seven ledger SHAs and economics with contract-correct MDD.

**Benchmark limitation:** SPY buy-and-hold ended at **USD 317645.2207582**, higher than HYP_011's **USD 218852.857740** on that historical comparison. PASS does not establish universal outperformance, Alpha or future profitability.

**Reuse / missing / authority / acceptance / next:** reuse accounting, valuation, holdings, dividends/splits, benchmarks and friction. Retrospective exploratory execution of the USD 1,000 study was conducted in V32–V37A ([V35](research/D6_V35_CONTRIBUTION_STUDY_RESULTS_20261025.md), [V36](research/D6_V36_FUNDING_COST_AUDIT_RESULTS_20261026.md), [V37A](research/V37A_FIXED_THB_RESULTS_20261027.md)) and corroborated in [V37B](research/D6_V37B_RESEARCH_EVIDENCE_INTEGRATION_20261030.md) under the strict `LOCAL_EXPLORATORY` label; formal D5 empirical admission remains unissued. After D5 and separate empirical authority, compare cash/no-trade, broad equity buy-and-hold, equity/bond and low-turnover diversification over matched periods. Disclose commissions, spreads, USD/THB FX, cash yield, funding, tax scenarios, drawdowns and evidence limits. No new empirical run here.

### D7 — 🧠 Governed Strategy Research

**Objective / standing:** evaluate an eligible baseline or hypothesis with existing scientific controls. IMPLEMENTED tools; new candidates SCIENTIFICALLY_BLOCKED pending scope-specific data/design/admission. Historical mapping: Phase 4/6/8.5/14; Phase 17 is a specified admission framework.

**Source / tests:** [research](../src/acash/research/), [validation](../src/acash/validation/), [portfolio tournament](../src/acash/portfolio/tournament.py); [DSR tests](../tests/unit/validation/test_deflated_sharpe.py), [PBO tests](../tests/unit/validation/test_multiple_testing_and_pbo.py), [CPCV tests](../tests/unit/validation/test_cpcv_purging.py), [tournament tests](../tests/unit/portfolio/test_model_selection_tournament.py).

**Historical dispositions:** [HYP_003](phase14/hyp_003_terminal_falsification_dossier.md) **TERMINALLY FALSIFIED**; [HYP_009](phase14/HYP_009_TERMINAL_M2_DECISION.md) **TERMINAL_NOT_SUPPORTED_AT_LOCKED_M2**; [HYP_010](phase14/HYP_010_PARKED_NON_FALSIFIED_BLOCKER.md) **PARKED / NON-FALSIFIED**; HYP_011 **HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW** in its original scope; [RI-01](audit/RI01_CHRONOLOGY_DISCREPANCY_REPORT_20261013.md) lineage decision unresolved.

**Reuse / missing / authority / acceptance / next:** reuse DSR/PBO/CPCV, backtest orchestration, OOS/provenance, governance and baselines. Require qualified data, eligible identity, sealed trial authority and independently authorized design before evaluation. Shared-data controls are statistically dependent. Phase 18–23 proposals are not proof of implemented runtime. **D7 does not require inventing Alpha:** an independently qualified simple baseline may answer the investment question, subject to unchanged admission and operating gates.

### D8 — 👁️ Prospective Shadow Validation

**Objective / standing:** measure forward behavior under exact prospective authority. IMPLEMENTED / HISTORICALLY_EXECUTED; new program AUTHORITY_UNISSUED. This roadmap stage is PROPOSED. Historical mapping: Phase 10/11, HYP_011 prospective modules and paper shadow tournament infrastructure.

**Source / tests:** [HYP_011 shadow/state/authority](../src/acash/research/hyp_011/), [runtime](../src/acash/runtime/), [monitoring](../src/acash/monitoring/); [prospective tests](../tests/unit/research/test_phase14_hyp_011_prospective_shadow.py), [operational tests](../tests/unit/research/test_phase14_hyp_011_shadow_ops.py).

**Historical evidence / reuse:** [Observation #1](audit/OBSERVATION_0001_COMMITTED_RECONCILED_20260930.md), target 2026-09-30, **COMMITTED_AND_RECONCILED**, records 29/29 checks and original S1 progress 1/20. Preserve this as **V1 platform-validation evidence**, not a current global counter. [Segment policy](phase14/HYP_011_PROSPECTIVE_SEGMENT_POLICY_V1_V2.md) and [ratification](audit/FINAL_RATIFICATION_RECORD.md) classify V1 **CLOSED_INCOMPLETE_GOVERNANCE_HARDENING**. V2 continuation/recovery and [V3 preparation](operations/HYP011_V3_PREPARATION_20261008.md) retain their separate scope and authority.

**Missing / authority / acceptance / next:** resolve the exact segment's continuation and reconciliation gates with explicit human authorization. Observation #2 is not automatically authorized; no fabricated sample, backfill or timer. One observation is not long-run forward qualification. Reuse engine, corporate-action adapters, accounting, persistent state, hash chain and reconciliation; do not rebuild them.

### D9 — 🧪 Paper Trading & Operational Validation

**Objective / standing:** validate operational broker behavior in an independently authorized paper program. IMPLEMENTED / HISTORICALLY_EXECUTED; ongoing program AUTHORITY_UNISSUED. This stage is PROPOSED. Historical mapping: Phase 7/12/13.

**Source / tests:** [execution coordinator/adapters](../src/acash/execution/), [MT5 reconciliation](../src/acash/execution/mt5/reconciliation.py), [paper runtime](../src/acash/paper/); [execution tests](../tests/unit/execution/), [paper tests](../tests/unit/paper/). Native MT5 tests require their optional environment.

**Historical evidence / reuse:** [Alpaca BMAP P-001](phase7/alpaca_bmap.md) records Paper Order 003 accepted, **FILLED**, reconciled and broker mapping verified. [Phase 13 readiness review](phase13/phase13_step7_paper_readiness_review.md) records Gate A certification, accepted 24-hour soak evidence and conditional infrastructure readiness, with Gate B / B23.2 host conditions unresolved. These are recorded historical exercises, not a fresh runtime audit.

**Missing / authority / acceptance / next:** Phase 13 Step 8 Human GO and Step 9 90-day paper remain locked under applicable decisions. Strategy qualification, human operating permission and paper authorization must each be independently established, including all conjunctive Step 9 prerequisites in the readiness review. Reuse broker event normalization/state machine, bridge, ledgers, rehydration and order reconciliation; do not start a paper clock from historical P-001.

### D10 — 🔐 Human-Gated Live Capital Admission

**Objective / standing:** present a human capital decision supported by accepted scientific and operational evidence. IMPLEMENTED infrastructure; **CAPITAL_LOCKED**. This stage is PROPOSED. Historical mapping: Phase 9/12/13 and explicit human authority.

**Source / tests:** [risk engine](../src/acash/risk/risk_engine.py), [kill switch](../src/acash/risk/kill_switch.py), execution/runtime/monitoring above; [risk tests](../tests/unit/risk/test_risk_engine.py), [kill-switch tests](../tests/unit/risk/test_kill_switch.py), [Gate B tests](../tests/unit/gate_b/test_gate_b_readiness.py).

**Historical evidence / reuse:** deterministic veto, persistent control records, admission gates, broker adapters, reconciliation, crash/restart recovery and telemetry exist. Phase 13 records identify unresolved host-enforcement conditions including B23.2; their current satisfaction is not proven by this task.

**Missing / authority / acceptance / next:** independently accepted scope-specific strategy/operational evidence and explicit human capital ratification; no automatic activation. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS=true`. CASH / NO-GO is valid. Reuse risk, execution, kill switch and recovery unless a reproducible deficiency warrants a separately scoped fix.

<a id="legacy-mapping"></a>
## 🏗️ 4. Legacy Numbering & Phase Mapping

**Migration rule:** legacy Delivery D0–D9 → Unified Delivery D1–D10, adding one. The former active D0–D6 definitions remain in the exact archived source; legacy D7–D9 are shadow/paper/live extensions, not ratified gates. Historical decision IDs named D1/D2/etc. in Phase records retain their own namespace and meaning. No Phase 0–23 renumbering or acceptance-criteria amendment occurs.

| Unified delivery | Previous delivery | Historical capability / verified standing | New-scope gap |
| --- | --- | --- | --- |
| D1 | D0 | Phase 2/3/14, M1.7–M1.8.1: implemented and synthetic-tested; canary review pending | Exact-reviewed integration |
| D2 | D1 | Phase 2/3/14 controls; PR #37 partial mocked safety | Audited verifier/executor/entitlement chain |
| D3 | D2 | Phase 14: HYP_009/010/011 provider exercises | New exact-scope authority |
| D4 | D3 | Phase 2/3/14: original-scope qualifications and session census | New ETF and sponsor evidence |
| D5 | D4 | Phase 14 sealed HYP_009/011 datasets | Separate Invest dataset admission |
| D6 | D5 | Phase 5/8/8.5/9, PPDS/Invest V0/M1.6; original HYP_011 economics | New USD 1,000 study |
| D7 | D6 | Phase 4/6/8.5/14 tools/tests; Phase 17 SPECIFIED_ONLY | Eligible scientific admission |
| D8 (PROPOSED) | D7 extension | Phase 10/11 and HYP_011 shadow code/tests; V1 observation exists | Segment-specific prospective permission |
| D9 (PROPOSED) | D8 extension | Phase 7/12/13 code/tests; P-001/soak historical evidence | Human GO, strategy and paper authority |
| D10 (PROPOSED) | D9 extension | Phase 9/12/13 risk/recovery code/tests | Explicit capital authority; host conditions |

Phase 0/1 foundation, all original phase titles/statuses, Phase 18–23 architecture proposals, and historical references to later architecture remain in the preserved historical section. Specification-only proposals do not become runtime capability through this mapping.

<a id="research-reuse"></a>
## ♻️ 5. Research Utilization

This is a delivery-use index into the existing [Research Utilization Matrix](audit/RESEARCH_UTILIZATION_MATRIX_20261013.md), not a replacement research inventory. Older counts/statuses in that dated matrix remain historical; the checkpoint above resolves the current PR metadata.

| Existing asset / authority record | Actual standing and original scope | Reuse → delivery | Missing new-scope qualification / authority |
| --- | --- | --- | --- |
| M1.6 [benchmark contracts](../src/acash/data/contracts/etf_fx_benchmark.py) | Integrated, synthetic lifecycle/accounting tests | Holdings/benchmark math → D4–D6 | Qualified prices, actions and empirical permission |
| [PPDS](../src/acash/ppds/) / [Invest V0](../src/acash/invest/v0_report.py) | Integrated read-only/synthetic reporting | Valuation/reporting → D6 | Admitted input dataset, cost scenarios |
| M1.7–M1.8.1 [authority](../src/acash/data/qualification/lane_a_authority.py) | Integrated offline planner/rehearsal/storage | Request/evidence integrity → D1–D3 | Production verifier and executor |
| PR #32 / PR #37 | Merged offline canary + safety (`bfffdb3` / `3255da9`) | Reuse integrated slices → D1/D2 | Independent acceptance; no new authority implied |
| [HYP_003 dossier](phase14/hyp_003_terminal_falsification_dossier.md) | TERMINALLY FALSIFIED | Negative evidence/governance → D7 | No resurrection or automatic promotion |
| [HYP_009 decision](phase14/HYP_009_TERMINAL_M2_DECISION.md) | TERMINAL_NOT_SUPPORTED_AT_LOCKED_M2; qualified SPY dataset in original scope | Qualification/accounting lessons → D3–D7 | No new strategy or dataset rights |
| [HYP_010 blocker](phase14/HYP_010_PARKED_NON_FALSIFIED_BLOCKER.md) | PARKED / NON-FALSIFIED; 8-attempt probe, VEU dividend-authority blocker | Probe/sponsor methodology → D3/D4 | Human resumption and sponsor authority |
| HYP_011 [data](phase14/HYP_011_R3_HISTORICAL_DATA_QUALIFICATION.md), [economics](phase14/HYP_011_R3_HISTORICAL_EXECUTION_REPORT.md), [shadow](audit/OBSERVATION_0001_COMMITTED_RECONCILED_20260930.md) | Original-scope qualification, G1–G6 PASS, V1 observation; no universal Alpha | Pipelines, ledgers, gates → D3–D8 | No transfer into Invest; continuation separately gated |
| [RI-01 chronology](audit/RI01_CHRONOLOGY_DISCREPANCY_REPORT_20261013.md) | Lineage decision unresolved | Evidence-review lessons → D3/D7 | Human lineage adjudication |
| [Lane A](research/LANE_A_UNISSUED_AUTHORITY_PACKET_20261013.md) / [Lane B](research/LANE_B_SPEC_OFFLINE_QUALIFICATION.md) | Unissued candidate / specification | Bounded prices / corporate actions → D3–D5 | Entitlement, issuance, issuer evidence |
| Cash / Equal Weight / Inverse Volatility; [tournament](../src/acash/portfolio/tournament.py) | Implemented transparent baselines and selection tooling | Qualified baseline comparisons → D6/D7 | Admitted matched inputs and test design |
| [DSR](../src/acash/validation/deflated_sharpe.py) / [PBO](../src/acash/validation/multiple_testing.py) / [CPCV](../src/acash/validation/cpcv.py) | Implemented validation tools, no new admitted candidate | Existing controls → D7 | Scientific/trial authority; dependence disclosure |
| [VIX / VIX1D note](research/volatility/VIX_DAILY_VOLATILITY_CONTEXT_RESEARCH_NOTE_20261013.md) | Research context only | Potential risk context → D7 | Separate empirical design and qualified inputs |
| FRED / BOT in [matrix](audit/RESEARCH_UTILIZATION_MATRIX_20261013.md) | Available/researched future inputs; outside Lane A | Potential PIT macro/FX → D6/D7 | Rights, vintage and scope-specific admission |
| IBKR-inspired friction in M1.6 | Synthetic modeled fees, **not account-verified**; no IBKR execution integration | Cost scenarios → D6 | Actual tariff/account/FX/tax evidence |
| [Execution](../src/acash/execution/) / [paper](../src/acash/paper/) infrastructure | Implemented, historical P-001 and soak evidence | Adapters, reconciliation/recovery → D8–D10 | Current operating and capital authority |

<a id="dependencies"></a>
## 🔗 6. Dependencies & Human Authority

| Readiness or authority | Required evidence / decision | Does not imply |
| --- | --- | --- |
| SOFTWARE_READY | Reviewed implementation and relevant executed checks | ACQUISITION_AUTHORIZED |
| ACQUISITION_AUTHORIZED | Exact scope/feed/budgets/time/runtime, trusted verifier and entitlement | DATA_QUALIFIED |
| DATA_QUALIFIED | Complete scope-specific price/actions/provenance qualification | ECONOMICS_EVALUATED |
| ECONOMICS_EVALUATED | Reproducible matched-period after-cost study | STRATEGY_QUALIFIED |
| STRATEGY_QUALIFIED | Applicable scientific contract and admission decision | PROSPECTIVE_AUTHORIZED |
| PROSPECTIVE_AUTHORIZED | Exact prospective segment, observations and operating decision | PAPER_AUTHORIZED |
| PAPER_AUTHORIZED | Phase 13/14 scientific, operational and Human GO prerequisites | LIVE_CAPITAL_AUTHORIZED |
| LIVE_CAPITAL_AUTHORIZED | Separate explicit human capital decision and all applicable gates | Autonomous capital expansion |

These are separate prerequisites, not automatic state transitions. A qualified simple baseline can be considered for separately authorized prospective testing without inventing a new Alpha hypothesis, only where applicable scientific and operating gates permit it. Phase 13/14 decisions continue to control.

<a id="next-actions"></a>
## 📍 7. Current Next Actions

1. **D1:** PR #32 merged (`bfffdb3`); D2 safety (PR #37, `3255da9`) and composition (PR #39, `e61dd24`) merged. No further offline-canary integration work is pending.
2. **Documentation:** PR #36 merged (`16901bf`); this roadmap PR #38 is the last open item — merge at its exact reviewed SHA under separate approval.
3. **D2:** offline safety/composition integrated; exact destination/port closed in merged code. Remaining: byte-unit ratification, durable dispatch/journal linkage proof, independent verifier/trust root, audited executor. Preserve the single planner and existing clients.
4. **D3:** operator binds entitlement/feed and issues Lane A only after the software gates are accepted. Until then: UNISSUED, no provider HTTP.
5. **D4–D6:** separately qualify the new ETF universe and corporate actions, admit the historical dataset, then authorize the USD 1,000 after-cost study. No dataset admission or economics claim follows from the offline canary.

### Research to hand off

Use the [ChatGPT Research brief](research/UNIFIED_ROADMAP_V4_RESEARCH_HANDOFF_20261015.md) for official-source questions on dataset rights/coverage, sponsor actions and small-portfolio economics. It requests research only, not downloads, credentials, paid services, empirical execution or trading. Engineering review above can proceed independently; no new comprehensive external research is required to write this roadmap.

Measure progression by accepted evidence and authority, not PR counts: software integrity → authorized acquisition evidence → qualified data → reproducible economic utility → separately governed prospective/paper/capital decisions.

<a id="historical-evidence"></a>
## 📚 8. Historical Evidence & Reference Compatibility

The [exact v3.7.0 archive](ROADMAP_v3.7.0_87e1176_ARCHIVE.md) preserves the chosen PR #36 base **byte-for-byte**, including its superseded delivery snapshot. It is historical, not a second active roadmap. The [preservation and citation map](audit/ROADMAP_V4_PRESERVATION_20261015.md) records commit, blob, byte count, SHA-256, fixed-line references and reference limitations. It also identifies checkpoint-main's original blob.

Historical Phase sections remain below with their exact source bytes, original titles, statuses, acceptance criteria, runbooks, evidence references and license. Their dated “CURRENT”, “NOW”, “NEXT” and proposal language is **historical evidence only**; the v4 delivery sequence above is the sole active presentation. No sealed scientific or ratified record is rewritten.

**Legacy line citations:** an unversioned `docs/ROADMAP.md:line` is not a stable current-file address. Resolve historical citations using their authoring commit/blob in the compatibility map; do not reinterpret them against new line numbers. The scanned fixed-line citations resolve at their authoring commit; the map records those frozen targets rather than assigning their line numbers to this file.

---

<a id="acash--system-development-roadmap-current-delivery--historical-phases-023"></a>
<a id="current-delivery-track--etf-evidence-to-economics-2026-10-14"></a>
<a id="1-north-star"></a>
<a id="2-verified-implementation-and-delivery-register"></a>
<a id="3-actual-roadmap-d0-to-d6"></a>
<a id="4-existing-research-reuse-vs-defer"></a>
<a id="5-progress-measurement"></a>
<a id="6-relationship-to-historical-phase-roadmap"></a>

## 📚 Preserved Historical Phase & Architecture Records

**Historical section begins here.** All source bytes from the original `ACASH CURRENT NORTH-STAR (2026-09-11)` heading to EOF are retained. Archived assertions are not current admission or new human authorization.


## ACASH CURRENT NORTH-STAR (2026-09-11)

**North Star.** Under strict scientific governance, answer *"where should capital be allocated?"* — including the valid governed answer **NOWHERE** — by progressing the Phase 14 research lanes (mainline `CAND-FREE-MACRO-001`, parallel `MEC-0011`, parallel `MEC-0013`) to a single canonical frozen pre-registration, then explicit Human authorization, then empirical validation and qualification. All trading / capital / broker authority remains **STRICTLY LOCKED** throughout.

```
CURRENT WORKING MILESTONE (replaces the older "Phase 13 Step 5 soak ACTIVE" framing;
Phase 13 Steps 1-7 are certified; Step 8 LOCKED; Step 9 NOT AUTHORIZED):

  MAINLINE .... CAND-FREE-MACRO-001    FREEDATA research lane; CONDITIONALLY READY;
                                       Rounds 0-3B (K=3), Round 3B remainder (S-2/S-7 F2/S-9),
                                       Round 4 (D14/D15/D16/EX/CO/CA-1), Round 5 (D19/D20) RATIFIED;
                                       D17 (SPX close authority) & D18 (manifest) OPEN / D17-E BLOCKED;
                                       PRE-REGISTRATION NOT FULLY FROZEN (24/26 checklist; D18 & Human Auth pending);
                                       EMPIRICAL VALIDATION NOT AUTHORIZED
  PARALLEL .... MEC-0011                Gold/DXY relative-movement; RESEARCH INTAKE ONLY;
                                       D1=A / D2=C / D3=B human-ratified 2026-09-10;
                                       DXY source layer BLOCKED (paths P1-P5 await Human);
                                       NOT AUTHORIZED FOR EMPIRICAL VALIDATION
  ARCHIVED .... MEC-0013                Opening Range Breakout (ORB); AUDITED RESEARCH ASSET ONLY;
                                       MEC-0013-D01 = OPTION C (Archived at $0; No commercial data;
                                       No 30-day sample; NOT a candidate; NOT HYP_003; Backtest LOCKED)
  PARKED ...... F-1 CAND-FLOW-CALENDAR-REBALANCE-001   NOT READY / CONDITIONAL at $0;
                                       PENDING HUMAN RATIFICATION
  INFRASTRUCTURE .. Gate G7 / Stage S11   HOMELAB 6-HOUR OPERATIONAL SOAK; CLOSED / PASS;
                                       Session E3.5-20260913-025117-de2762;
                                       Human Forensic Adjudication;
                                       Pi tooling remediation MERGED @ 68142ae;
                                       ZERO REAL ORDER SUBMISSIONS;
                                       NEXT GOVERNANCE TRANSITION: AWAITING HUMAN DECISION
  LOCKED ...... HYP_003 (NOT CREATED) / R1 (NOT AUTHORIZED) / empirical validation /
               backtest / trading (LOCKED) / capital ($0.00) / broker (DISCONNECTED) /
               quarantined HYP_001/HYP_002 data spans (PRISTINE / NOT REUSABLE BY DEFAULT)
```

### State Register (authoritative boundaries, verified 2026-09-11)

| Class | Lane / Item | State |
|---|---|---|
| CURRENT | `CAND-FREE-MACRO-001` (mainline) | `CONDITIONALLY READY`; Human binding Rounds 0-5 ratified (K = 3; S-2 S2-B, S-7 T2/F2, S-9 Q-1..Q-4, D14-D16, EX, CO, CA-1, D19, D20 bound); **D17 (SPX close authority) & D18 (reproducibility manifest) = OPEN / DATA-AUTHORITY BLOCKED**; PRE-REGISTRATION **NOT FULLY FROZEN** (24/26 checked; D18 & Human Auth pending); EMPIRICAL VALIDATION **NOT AUTHORIZED** |
| PARALLEL | `MEC-0011` Gold/DXY relative movement | RESEARCH INTAKE ONLY; D1=A / D2=C / D3=B human-ratified 2026-09-10; **source layer BLOCKED** (B1 CONDITIONAL; B2/B3 BLOCKED; B4-B10 open); DXY resolution path P1-P5 awaiting Human selection; no Gold/DXY source ACCEPTED in the registry; no GLD/UUP variant may be created without explicit Human selection |
| ARCHIVED | `MEC-0013` Opening Range Breakout (ORB) | AUDITED RESEARCH ASSET ONLY (`docs/phase14/mec_0013_orb_research_intake.md`, `mec_0013_orb_research_audit.md`); Human Ratification MEC-0013-D01 = OPTION C (Archived at $0; No commercial data; No 30-day sample; NOT promoted to candidate; NOT HYP_003; Backtest LOCKED; Zero ACASH empirical evidence) |
| COMPLETED | `Gate G7` / `Stage S11` (Homelab 6h Soak) | **CLOSED / PASS** (Session `E3.5-20260913-025117-de2762`; Human Forensic Adjudication; historical harness printed FAIL via `SESSION_ID=unknown` binding defect; verified evidence satisfies all G7 criteria: canonical manifest duration 21,639.30s, 361 M1 bars spanning 360 intervals, 0 restarts, 0 failure-shaped disconnects; Pi verifier remediation merged @ `68142ae`; ZERO REAL ORDER SUBMISSIONS) |
| PARKED / BLOCKED | `F-1` CAND-FLOW-CALENDAR-REBALANCE-001 | D1 final verdict **NOT READY / CONDITIONAL** (free-data feasibility not certifiable at $0); PENDING HUMAN RATIFICATION; NOT mainline; NOT HYP_003 |
| PARKED / BLOCKED | Other research directions/candidates (NY-open, prediction-market AI, session momentum, ...) | `UNVALIDATED PROPOSAL`; NOT REGISTERED; NOT SEALED; NOT HYP_003 |
| LOCKED | `HYP_003` | **NOT CREATED** (absent repo-wide) |
| LOCKED | `R1` / `ResearchReInceptionGate` | **NOT AUTHORIZED / NOT INVOKED** |
| LOCKED | Empirical validation / backtest | **NOT AUTHORIZED** for all candidates |
| LOCKED | Trading / Capital / Broker | **LOCKED / $0.00 / DISCONNECTED** (0 live orders; no live credential path) |
| LOCKED | Quarantined data | HYP_001 2026 M5 Holdout; HYP_002 H4 Validation + Blind OOS — PRISTINE / NOT REUSABLE BY DEFAULT |
| LOCKED | Phase 13 Step 8 (Human GO) / Step 9 (90-day paper) | **LOCKED / NOT AUTHORIZED** (no qualified strategy) |
| FUTURE | Phases 18-22 | UPCOMING (tournament / regime detection / selection / allocation solvers / orchestration) |

**Authorization ladder — never conflate:** `INFRASTRUCTURE READY != STRATEGY QUALIFIED != PAPER AUTHORIZED != LIVE AUTHORIZED`. Research capability != strategy qualification != execution authorization. The research lanes above are research configurations / candidates — **NOT** registered hypotheses, strategies, or tradeable configurations.

---

## ACASH NOW / NEXT / LATER (2026-09-13)

- **NOW** (governance & data-authority resolution; no empirical work):
  1. Gate G7 / Stage S11 — [COMPLETED / CLOSED] Infrastructure 6h continuous soak validated under session `E3.5-20260913-025117-de2762` via Human Forensic Adjudication; Pi tooling remediation merged @ `68142ae`; ZERO REAL ORDER SUBMISSIONS.
  2. MACRO-001 D17 — Human Decision on SPX close data authority (`docs/phase14/macro_001_data_authority_gap_register.md`). D17-E ($0 blocker) maintained.
  3. MACRO-001 D18 — Downstream reproducibility manifest schema specified (`docs/phase14/macro_001_d18_manifest_specification.md`); unsealed, dependency-blocked on D17.
  4. MEC-0013 — [COMPLETED / ARCHIVED] Claim-provenance audited, Option C ratified, archived as non-promoted research asset (`docs/phase14/mec_0013_orb_research_audit.md`).
  5. Data-plane test seam — [COMPLETED / VERIFIED] Offline integration validation of `DuckDBStorage` -> `ParquetMarketDataProvider` -> `ForwardMarketDataFeeder` verified (`tests/integration/test_parquet_feeder_seam.py`, 4/4 passing, zero alpha logic).
  6. MACRO-001 Pre-Registration Checklist — [RECONCILED] 24/26 items checked (`docs/phase14/cand_free_macro_001_human_specification_decision_surface.md` §28); Anti-HARKing template prepared (`docs/phase14/macro_001_anti_harking_audit_template.md`).
- **NEXT** (NEXT GOVERNANCE TRANSITION: AWAITING HUMAN DECISION; strict sequence; only after D17 / D18 are resolved):
  1. Complete pre-registration freeze checklist (26/26 items) -> Draft Freeze Candidate.
  2. Anti-HARKing review.
  3. Pre-registration Freeze.
  4. Data Archive / Reproducibility Manifest sealing.
  5. **Explicit Human Authorization** -> then empirical validation / backtest via Phase 5 Production Orchestrator.
- **LATER** (gated on a HUMAN-AUTHORIZED qualified strategy; nothing before):
  1. Phase 13 Step 8 Human GO -> Step 9 (90-day continuous paper run).
  2. Phases 18-22 upstream milestones (tournament, regime detection, selection, allocation solvers, orchestration). All currently LOCKED / NOT AUTHORIZED.

---

## Roadmap Overview

```
✅ Phase 0: Discovery & Architecture ──► [COMPLETED - PASSED]
   │
   ▼
✅ Phase 1: Foundation & Domain Core ──► Gate 1 [COMPLETED - PASSED — 27/27 Tests]
   │
   ▼
✅ Phase 2: Data Ingestion & Integrity Engine ──► Gate 2 [COMPLETED - PASSED — 57/57 Tests]
   │
   ▼
✅ Phase 3: Point-in-Time Microstructure & Feature Engine (3A/3B/3C) ──► Gate 3 [COMPLETED - PASSED — 122/122 Tests]
   ├─ ✅ Phase 3A: Canonical Trades Domain
   ├─ ✅ Phase 3B: Canonical Order Book Domain
   └─ ✅ Phase 3C: Microstructure Feature Engine
   │
   ▼
✅ Phase 4: Alpha Research Engine & Hypotheses ──► Gate 4 [COMPLETED - PASSED — 139/139 Tests]
   │
   ▼
✅ Phase 5: Backtesting Substrate & Simulation Engine ──► Gate 5 [COMPLETED - PASSED — 200/200 Tests]
   │
   ▼
✅ Phase 6: Statistical Validation & Overfitting Controls ──► Gate 6 [COMPLETED - PASSED — 252/252 Tests]
   │
   ▼

✅ Phase 7: Live Execution & Broker Mapping (Admission → Coordinator → BMAP → Alpaca Paper) ──► Gate 7 [COMPLETED - PASSED — 610/610 Tests, P = 1 (P-001)]
   │
✅ Phase 8: Portfolio Engine (skfolio & Baselines) ──► Gate 8 [COMPLETED - PASSED]
   │
   ▼
✅ Phase 8.5: Alpha Research & Economic Evidence Engine ──► Gate 8.5 [COMPLETED - PASSED]
   │
   ▼
✅ Phase 9: Deterministic Risk Engine & Kill Switch ──► Gate 9 [COMPLETED - PASSED]
   │
   ▼
✅ Phase 10: Runtime Orchestration & Continuous Paper Operations ──► Gate 10 [COMPLETED - PASSED]
   │
   ▼
✅ Phase 11: Forward Tracking, Online Drift Detection & Execution Reality Attribution ──► Gate 11 [COMPLETED - PASSED — 107 Tests, 26 Red Team, 9 Integration]
   │
   ▼
✅ Phase 12: MT5 & Venue Execution Adapters ──► Gate 12 [COMPLETED & FROZEN — 1240/1240 Tests, 1e1d154]
   │
   ▼
✅ Phase 13: Live Small Capital & Infrastructure ──► Gate 13 Steps 1–7 Certified; Gate G7 / Stage S11 CLOSED [PASS — Session E3.5-20260913-025117-de2762]
   ├─ ✅ Step 1: Implementation & Safety Envelopes [PASSED]
   ├─ ✅ Step 2: Code & Unit Audit [PASSED]
   ├─ ✅ Step 3: Integration Testing & Local Simulator [PASSED]
   ├─ ✅ Step 4: Restart, Recovery & Rehydration [PASSED]
   ├─ ✅ Step 5: 24-Hour Unattended Soak Test [VERIFIED COMPLETED]
   ├─ ✅ Step 6: Telemetry, Reconciliation & Forensic Audit [PASSED]
   ├─ ✅ Step 7: Continuous Paper Readiness Certification [CONDITIONALLY SATISFIED]
   ├─ ✅ Gate G7 / Stage S11: Homelab 6h Continuous Soak [CLOSED / PASS — Human Forensic Adjudication]
   ├─ 🔒 Step 8: Explicit Human GO Checkpoint [LOCKED]
   └─ 🔒 Step 9: 90-Day Continuous Paper Forward Run [LOCKED]
   │
   ▼
📐 Phase 14: AI Quantitative Research Layer ──► Gate 14 [PLAN APPROVED AT PLAN LEVEL — IMPLEMENTATION LOCKED]
   │
   ▼
⏳ Phase 15: Strategy Lifecycle Management [HARMONIZED INTO PHASE 17]
   │
   ▼
⏳ Phase 16: Performance Degradation & Data Flywheel [HARMONIZED INTO PHASE 17–22]
   │
   ▼
✅ Phase 17: Strategy Admission Standard & Regime-Aware Capital Allocation Framework [SPECIFIED — ADR-023]
   │
   ▼
⏳ Phase 18: Strategy Research & Tournament Pipeline [UPCOMING]
   │
   ▼
⏳ Phase 19: Empirical Regime Detection Engine [UPCOMING]
   │
   ▼
⏳ Phase 20: Regime × Strategy Selection & Decision Engine [UPCOMING]
   │
   ▼
⏳ Phase 21: Risk-Based Capital Allocation Solvers [UPCOMING]
   │
   ▼
⏳ Phase 22: Portfolio / Multi-Strategy Orchestration & Memory Flywheel [UPCOMING]
   │
   ▼
🏛️ Phase 23: Adaptive Multi-Horizon Strategy & Microstructure Architecture [ARCHITECTURAL RECORD — ADR-024/025]
```

---

## CURRENT STATE / NEXT STEP (Reconciliated 2026-09-10)

> **Current Repository Milestone:** Phase 14 Governance + Research Lanes (CAND-FREE-MACRO-001 mainline / MEC-0011 parallel). System: **RESEARCH STANDING BY**.  
> **Historical note:** the prior framing "Phase 13 Step 5 (24-Hour Soak) ACTIVE / IN PROGRESS under PID 41844, launched 2026-09-05T10:20:43Z" is a completed historical/snapshot event — Phase 13 Step 5 is VERIFIED COMPLETED (see Phase 13 detail below). Potentially obsolete section found — preserved intentionally.  
> **Live Capital Authority:** Strictly **$0.00 (Hard-Locked)**. Live Orders: **0**. Broker: **DISCONNECTED**.  

### Current Canonical Execution State:
- ✅ **Phases 0–12:** COMPLETED & FROZEN (Gates 1–12 certified, frozen contract baseline sealed).
- ✅ **Phase 13 (Live Small Capital / Forward Paper Validation): INFRASTRUCTURE READY / STRATEGY BLOCKED**
  - ✅ **Step 1 (Implementation & Safety Envelopes):** PASSED.
  - ✅ **Step 2 (Code & Unit Audit):** PASSED.
  - ✅ **Step 3 (Integration Testing & Local Simulator):** PASSED.
  - ✅ **Step 4 (Restart, Recovery & Rehydration):** PASSED.
  - ✅ **Step 5 (24-Hour Unattended Soak Test):** **VERIFIED COMPLETED** (86,400.21s runtime, 86,085 ledger events, 8,608 telemetry records, 0 errors, graceful exit; snapshot launched 2026-09-05T10:20:43Z under PID 41844).
  - ✅ **Step 6 (Telemetry, Reconciliation & Forensic Audit):** PASS (SHA-256 chained integrity, zero gaps >15s, RSS peak 175.29 MB, pulse reconciliation 100%).
  - ✅ **Step 7 (Continuous Paper Readiness Certification):** CONDITIONALLY SATISFIED (runtime infrastructure verified ready; blocked on strategy qualification; B23.2 VM deferred).
  - 🔒 **Step 8 (Explicit Human GO Checkpoint):** STRICTLY LOCKED (no qualified strategy).
  - 🔒 **Step 9 (90-Day Continuous Paper Forward Run):** STRICTLY NOT AUTHORIZED (clock has not started; $0.00 capital authority).
- 📐 **Phase 14 (AI Quantitative Research Layer): GATE 14 ACCEPTED — RESEARCH CAPABILITY — ZERO TRADING AUTHORITY**
  - Master Research Architecture Revision 1.2 approved at plan level by Human Auditor.
  - **Gate 14 = ACCEPTED** (2026-09-08) — technical acceptance of the Phase 14 research capability (G-2 CUSTOM-2 scope). **NOT** trading, runtime, or strategy authorization.
  - Implementation slices exist in the repository as **UNVALIDATED PROPOSALS** (research-AI assistant/converter/prompts/provider; slices 1-4; D6 Option A census sealing; Phase 5 production orchestrator; D8-B release gate, Seam A identity; D5 OOS provenance with PIT lineage). Phase 13 Steps 8-9 remain independently and strictly LOCKED (Human Ratification D1-D4, 2026-09-08).
  - Zero authority to register hypotheses (HYP_003 NOT CREATED), qualify alpha, certify validation, or trade. Capital and broker execution remain completely decoupled ($0.00 / DISCONNECTED).

### Repository Synchronization State:
- **Current Branch:** `main` (HEAD == origin/main == `c78d09c`)
- **Documentation Synchronization Date:** 2026-09-11
- **State Source:** Canonical repository contracts (`src/acash/`), Phase 13 audit records (`docs/phase13/`), and Phase 14 governance / research records (`docs/phase14/`). Older checkpoint snapshots (`docs/PROJECT_STATUS.md` dated 2026-09-04; `docs/README.md` dated 2026-09-07) are historical / checkpoint-only and may lag this file.

### Immediate Next Action:
- Resolve MACRO-001 D17 (SPX close data authority) and D18 (reproducibility manifest).
- Once D17/D18 are resolved, complete the 26-item pre-registration freeze checklist -> Draft Freeze -> Anti-HARKing review -> Pre-registration Freeze -> Data Archive / Manifest -> Explicit Human Authorization.
- ParquetMarketDataProvider implemented and verified on main (`b7e4d5e`); data-plane ready for offline replay when authorization occurs.
- MEC-0013 ORB remains isolated research intake (tracked research intake; non-authorizing; zero empirical authority).
- No empirical work of any kind until an explicit Human authorization follows a frozen pre-registration.

---

## Detailed Phase Breakdown

### ✅ Phase 0: Discovery & Architecture [COMPLETED - PASSED]
- **Objective:** Evaluate technologies, define domain architecture, produce ADRs, risk register, and establish project boundaries.
- **Deliverables:** Complete documentation suite in `docs/`.
- **Gate 0 Criteria:** Technology candidate matrix approved; architecture review signed off; Phase 1 implementation plan approved.

---

### ✅ Phase 1: Foundation & Domain Core [COMPLETED - PASSED]
- **Objective:** Establish the modular monolith structure, domain types, abstract interfaces, configuration management, structured logging, in-memory mock adapters, and correctness test harness.
- **Deliverables:**
  - Python project environment (`pyproject.toml`, virtual environment).
  - Core domain models (`Instrument`, `Bar`, `MarketDataSnapshot`, `Signal`, `TargetAllocation`, `RiskAssessment`, `Order`, `Fill`).
  - Core interface definitions (`IMarketDataProvider`, `IFeatureEngine`, `IStrategy`, `IPortfolioOptimizer`, `IRiskEngine`, `IBacktestEngine`, `IExecutionEngine`, `IDecisionLedger`).
  - Mock in-memory execution engine and market data provider for unit testing.
  - Structured JSON logger and typed configuration loader (`Pydantic` + `YAML`).
  - Unit and contract test suite verifying domain invariants, invalid states, interface contracts, serialization, and deterministic equivalent outcomes.
- **Gate 1 Criteria:** All unit tests pass (27/27); domain invariants verified; typing strictly enforced (`mypy` clean); zero live broker or Nautilus dependencies in core.

---

### ✅ Phase 2: Data Ingestion & Integrity Engine [COMPLETED - PASSED]
- **Objective:** Implement reliable ingestion for **one market** and **one primary data source** with strict point-in-time validation.
- **Deliverables:**
  - Ingestion adapter (`yfinance` research adapter / local Parquet for single liquid symbol).
  - Normalization pipeline with timestamp timezone enforcement (UTC only) and sequencing verification.
  - Automated data integrity checker (detects missing timestamps, impossible negative prices, duplicates, unit errors).
  - Provenance tracker recording dataset hash and retrieval metadata.
  - Recoverable Batch Commit Protocol (`PREPARED` $\to$ `PART_PUBLISHED` $\to$ `COMMITTED`).
  - DuckDB Point-in-Time qualification layer with multi-source isolation and lookahead prevention.
- **Gate 2 Criteria:** Data validation suite catches 100% of synthetic data corruption test cases (57/57 tests pass, `mypy` clean).

---

### ✅ Phase 3: Point-in-Time Feature Engine (3A/3B/3C) [COMPLETED - PASSED]
- **Objective:** Build modular, deterministic feature calculations with zero look-ahead bias across Trades, Order Book, and Microstructure.
- **Deliverables:**
  - **Phase 3A:** Canonical Trades Domain (Time & Sales, Aggressor Side flags, length-prefixed hashing).
  - **Phase 3B:** Canonical Order Book (L2 Depth Multi-Row Frames & Deltas, L3 MBO, deterministic 5-tuple order).
  - **Phase 3C:** Microstructure Feature Engine (Session VWAP, Volume Profile with POC lower-price tie-breakers, Value Area 70% bounds, Footprint Analytics, Depth-Weighted Micro-Price).
  - Dual-temporal point-in-time filtering ($T_{\text{event}} \le T_{\text{decision}} \land T_{\text{knowledge}} \le T_{\text{as\_of}}$).
- **Gate 3 Criteria:** Automated leakage unit tests verify zero future bar indexing; 122/122 tests pass, `mypy` clean.

---

### ✅ Phase 4: Alpha Research Engine & Baseline Hypotheses [COMPLETED - PASSED]
- **Objective:** Implement formal hypothesis registration, econometric OLS slope Beta HAC inference under Bartlett kernel, discrete forward returns, interval-based purging/embargo, and durable Blind OOS governance.
- **Deliverables:**
  - Hypothesis specification schema (`HypothesisSpecification`, `InvalidationCriteria`, parameter spaces).
  - Discrete bar-indexed forward returns ($R(t,H)$) with next-bar open entry alignment.
  - Econometric OLS slope $\hat{\beta}_H$ inference with Newey-West HAC covariance under Bartlett kernel.
  - Descriptive non-parametric association metrics: Pearson IC, Spearman Rank IC (fractional ties), autocorrelation.
  - 3-tier friction waterfall (Raw Edge $\to$ Net Edge $\to$ Economic Edge).
  - Interval-based boundary purging and unallocated embargo gaps ($\ge \max(H)$ bars).
  - Durable Blind OOS Governance Ledger (`data/manifests/research/governance_ledger.json`) with strict re-tuning locks (`UNEXPOSED` $\to$ `EVALUATED_LOCKED` $\to$ `EXHAUSTED`).
  - Baseline research models: Microstructure Imbalance Skew, VWAP Mean Reversion, Multi-Horizon Momentum.
- **Gate 4 Criteria:** Strategies generate reproducible signals on historical data without look-ahead errors; 139/139 unit tests pass, `mypy` clean.

---

### ✅ Phase 5: Backtesting Substrate & Simulation Engine [COMPLETED - PASSED]
- **Objective:** Establish the deterministic event-driven simulation backtest substrate preserving ACASH as the single source of truth for canonical data, features, accounting, and manifests.
- **Deliverables:**
  - Event-driven backtesting execution substrate with full simulated order lifecycle state machine.
  - Canonical Data Adapter with Phase 3B total ordering 5-tuple contract: $(T_{\text{event\_utc}}, \text{source\_order\_key}, \text{message\_rank}, \text{stream\_id}, \text{row\_sub\_index})$.
  - Realistic friction simulation (maker/taker fee tiers, bid/ask spread, fixed & dynamic slippage, causal dual-sided latency).
  - Independent double-entry shadow ledger decoupling Balance-Sheet View from Performance Attribution View ($|\text{AccountingResidual}| \le 10^{-10}$).
  - Deterministic content-derived `BacktestManifest` identity: $\text{manifest\_id} = \text{SHA256}(\text{canonical}(\text{hypothesis\_hash} + \text{data\_hashes} + \text{engine\_hash} + \text{strategy\_hash} + \text{seed}))[:32]$.
  - Reality Gap Telemetry Engine implementing disjoint non-overlapping reference-price decomposition: Spread Drag, Slippage Drag, Latency Drag, Fee Drag, Maker Adverse Selection Drag, and Unmodelled Residual.
  - Baseline strategy actors: Microstructure Imbalance (OBI) & Session VWAP Mean Reversion.
- **Gate 5 Criteria:** Bitwise-identical replay across identical inputs/configs, exact double-entry cash conservation, unmocked NautilusTrader integration, and zero phantom liquidity; 200/200 tests pass, `mypy` clean.



---

### ✅ Phase 6: Statistical Validation & Overfitting Controls [COMPLETED - PASSED]

- **Objective:** Enforce quantitative validation gates to eliminate data-snooping, selection bias, and backtest overfitting.
- **Deliverables:**
  - Combinatorial Purged Cross-Validation (CPCV) engine with contiguous $N$-group partitioning, exhaustive $\binom{N}{k}$ combinations, strict $[t+1, t+H]$ interval purging, post-test embargo buffers, and continuous pseudo-OOS path reconstruction ($\phi = \frac{k}{N}\binom{N}{k}$).
  - Deflated Sharpe Ratio (DSR) & Minimum Track Record Length (MinTRL) engine implementing Bailey & López de Prado (2014) non-normal asymptotic inference with Euler-Mascheroni constant $\gamma_E$, empirical trial variance $V$, Fisher-Pearson skewness $g_1$, and Pearson kurtosis $g_2$.
  - Multiple-testing accounting: Holm-Bonferroni step-down (FWER), Benjamini-Hochberg (FDR), and Harvey-Liu-Zhu (2016) Haircut Sharpe Ratio.
  - Probability of Backtest Overfitting (PBO) log-odds evaluation and parameter surface curvature / fragility testing across mandatory $\pm 25\%$ parameter grids.
  - Sovereign `StatisticalValidationGate` orchestrating multi-gate sequential evaluation, authoritative $K_{\text{ledger}} \equiv K_{\text{DSR}} \equiv K_{\text{Holm}} \equiv K_{\text{BH}}$ trial coupling, fail-closed missing data defense, and emitting immutable `ValidationReport` certificates with dual cryptographic lineage digests.
- **Gate 6 Criteria:** Strategies must satisfy DSR $\ge 0.95$, MinTRL, Holm-Bonferroni FWER significance, PBO $< 0.25$, flat parameter curvature, analytical friction monotonicity, and sealed OOS performance retention ($\text{SR}_{\text{OOS}} \ge 0.50 \cdot \text{SR}_{\text{IS}}$); 252/252 tests pass, `mypy` clean.

---

### 🟡 Phase 7: Live Execution & Broker Mapping [IN PROGRESS]
- **Specification & Evolution Proposal:** [`docs/phase7/phase_7_proposal.md`](phase7/phase_7_proposal.md)
- **Objective:** Build the sovereign execution stack from authorization/admission
  through broker-neutral semantic mapping to a concrete Alpaca Paper integration,
  and exercise a real (Paper) order lifecycle.
- **Explicit Paper-before-Live Execution Sequence:**
  $$\text{Phase 7 Implementation} \to \text{R0 (Read-Only)} \to \text{R1 (Lifecycle Harness)} \to \text{Security Preflight} \to \text{Paper Exercise} \to \text{P Evidence} \to \text{Readiness Review} \to \text{Live Authorization Hard-Lock}$$
- **Completed (LOCKED / E-reviewed — 588 tests passing):**
  - Admission/Authorization gate, Step 8 Execution Contract, Step 8B State
    Machine, Step 8C Broker Event Normalizer, Step 8D Mock Broker, Step 8E
    Execution Coordinator & Reconciliation Boundary, Operational Restriction,
    Real Broker Contract.
  - Vendor-Agnostic Broker Semantic Mapping Framework + Alpaca Concrete BMAP:
    `BMAP 01–10 = E`, `BMAP 11 = E*`, `BMAP 12 = D`.
  - Concrete Alpaca Paper Transport (`PaperHttpAlpacaTransport`), Paper
    Credential Boundary (venue-pinned `ALPACA_PAPER`), `AlpacaPaperAdapter`.
  - Local Windows User Vault & Launcher: `scripts/setup_paper_credentials.ps1` (DPAPI/SecretStore) and `scripts/run_paper.ps1` (Paper-only child process injection).
  - R0 read-only Paper Exercise harness; R1 order-lifecycle exercise harness
    (`run_order_exercise_verification`); R1 contract frozen.
  - R1 entry-point fixes: `4a92348` connect-before-submit; `8e92188` paper-only
    transport injection guard.
- **Evidence Model ($\text{Unit Tests} \neq E \neq P$):**
  - **Local Unit Tests:** 588/588 unit tests passing (automated regression & invariant protection).
  - **`D` (Design-Conformant):** Specification and schema match the canonical domain contracts.
  - **`E` (Broker Semantic Review):** Broker semantic mapping verified against official vendor documentation (`01–10 E`, `11 E*`, `12 D`).
  - **`E*` (Partially Bounded):** Bounded behavior with known vendor API caveats (e.g. BMAP-11 SSE replay gaps).
  - **`P` (Empirically Proven):** Real execution observed against live Paper venue satisfying full cryptographic lineage ($P = 0$).
  - $$\boxed{\text{588 Unit Tests} \neq E \text{ (Broker Semantic Review)} \neq P \text{ (Empirical Paper Execution)}}$$
- **Current milestone (in progress):** final Paper preflight via `run_paper.ps1 -PreflightOnly` → authorized single Paper run → first **P** evidence.
- **Blockers & Resolution Workflow:**
  1. Interactive local credential entry via `.\scripts\setup_paper_credentials.ps1` into Windows User Vault (DPAPI / SecretStore) outside Git.
  2. Safe preflight check via `.\scripts\run_paper.ps1 -PreflightOnly` (`ALPACA_PAPER` provider, `CREDENTIALS_LOADED=True`, `paper-api.alpaca.markets/v2` endpoint).
  3. Real Paper run is **NO-GO** until operator green-lights after a passing final preflight.
- **Approved run parameters (single order):** `SPY` / `quantity=1` /
  `client_order_id=acash-r1-paper-20260831-001`.
- **P acceptance (conjunctive — ALL must hold):**
  $$\text{P} = \text{TerminalVerified} \land \text{EvidenceLineageComplete} \land \text{ReconciliationVerified} \land \text{NoDispute}$$
  $E \neq P$; HTTP-success $\neq P$; FILLED alone $\neq P$; unit tests $\neq P$.
- **Gate 7 Criteria (design intent):** verified real Paper order-lifecycle
  evidence (P) through the canonical authority pipeline (`AlpacaPaperAdapter` →
  `normalize_broker_event()` → `to_coordinator_event()` →
  `ExecutionCoordinator.apply()/reconcile()` → `transition_order()`).
  (Original Regime-Engine content deferred to a later phase.)

---

### ✅ Phase 8: Portfolio Engine (Native Optimizers, Baselines & Governance) [COMPLETED & FROZEN]
- **Objective:** Allocate capital across candidate assets/signals and cash ("NOWHERE").
- **Deliverables:**
  - Transparent Baseline Allocators: Equal Weight (1/N), Inverse Volatility (1/$\sigma$), 100% Cash (`CashAllocator`, `EqualWeightAllocator`, `InverseVolatilityAllocator`).
  - Native Portfolio Optimizers: Hierarchical Risk Parity (HRP) and Equal Risk Contribution (ERC) with zero-leakage out-of-sample tournament (`AllocationTournamentRunner`).
  - Optional Adapters: `skfolio` and `cvxpy` adapters with graceful degradation when optional packages are not installed in clean core.
  - Sovereign Governance Gate: If net expected return fails risk-free rate + hurdle margin, sovereignly allocate 100% Cash via `GOVERNANCE_FALLBACK`.
- **Gate 8 Criteria:** Fully audited out-of-sample tournament (`Gate 8 Native Allocation Tournament`); Candidate $\neq$ Evaluation $\neq$ Decision; Ranking $\neq$ Approval; Policy-estimated friction (12 bps); Max Drawdown evaluated on net equity path. Commit: `e6f1d04`.

---

### ✅ Phase 8.5: Alpha Research & Economic Evidence Engine [COMPLETED & FROZEN]
- **Objective:** Establish formal alpha qualification, research lineage DTOs, and multi-horizon falsification hurdles with zero trading authority.
- **Deliverables:**
  - `AlphaQualificationDossier` and `AlphaEconomicDecomposition` DTOs enforcing $Net = Gross - Friction$.
  - Formal multi-hurdle qualification gate (`AlphaQualificationGate`) requiring positive net edge, Holm-Bonferroni FWER significance, and zero rebate-inflated edge.
  - Explicit forward lifecycle state machine (`HYPOTHESIS` $\to$ `CANDIDATE` $\to$ `RESEARCH_QUALIFIED` $\to$ `RETIRED_STRUCTURAL_BREAK`).
  - Strict boundary: $CapitalAuthorityUSD \equiv 0.00$.
- **Gate 8.5 Criteria:** 100% passing tests across 6 slices; cryptographic SHA-256 DAG binding hypothesis, trial ledger, and validation reports. Commit: `9ce1365`.
- **Track B (Strategy Qualification Pipeline — `STRAT-MOM-MULTI-HORIZON-V1` / `HYP_TSMOM_EURUSD_001`):**
  - **Status:** `CLOSED / TERMINALLY FALSIFIED` (Option B: Early Termination executed).
  - **Lineage Audit:**
    - Step R1 (Hypothesis Pre-Registration): `✅ PASS / SEALED` (SHA-256: `5afb92d...`).
    - Step R2 (Historical Data Preparation): `✅ PASS / SEALED` (10,000 bars EURUSD M5 canonical parquet; 16/16 gates passed).
    - Step R3 (In-Sample Search Census): `✅ PASS / SEALED` (Census of 9 trials, bars 0..5,999 complete).
    - Hypothesis `HYP_TSMOM_EURUSD_001`: `❌ TERMINALLY FALSIFIED` (9/9 negative Rank IC, negative net edge after friction, HAC $t < 2.0$, autocorrelation violations).
    - Steps R4–R7: `⛔ EARLY TERMINATED` (Discontinued to preserve OOS integrity and prevent multi-testing noise).
    - OOS Holdout: `UNEXPOSED_PRISTINE` (bars 6,060..9,999 100% untouched).
  - **Strategy Authority:** `STRAT-MOM-MULTI-HORIZON-V1` permanently `NOT QUALIFIED / NOT LIVE-ELIGIBLE`. Capital authority remains `$0.00`.
  - **Governing Dossier:** [`docs/phase8.5/phase8_5_hyp_tsmom_eurusd_001_terminal_falsification_dossier.md`](phase8.5/phase8_5_hyp_tsmom_eurusd_001_terminal_falsification_dossier.md).

---

### ✅ Phase 9: Deterministic Risk Engine & Sovereign Kill Switch [COMPLETED & FROZEN]
- **Objective:** Implement non-negotiable sovereign risk boundaries that overrule all upstream models.
- **Deliverables:**
  - `DeterministicRiskEngine` realizing `IRiskEngine` with multi-tier boundary evaluation (gross leverage, asset concentration, mandatory cash floor, drawdown, daily loss).
  - `DeriskEngine` implementing proven monotonic `EXACT_SCALE_DOWN` derisking and `BINARY_REJECT`.
  - `SovereignKillSwitchController` with append-only disk persistence, crash/restart recovery in `PERSISTENTLY_BLOCKED`, and multi-sig `Ed25519TrustStore` quorum reset verification.
  - `EmergencyFlattenGenerator` emitting zero-target liquidation intents ($q_{\text{target}} \equiv 0.0, \Delta q_i = -q_i$) and `EmergencyFlattenTracker` evaluating completion strictly against Phase 7 broker reconciliation.
  - `RiskStateBridge` ensuring type-safe, loss-bounded conversions across `PortfolioState`, `RiskSnapshot`, `CandidateRiskAllocation`, and `RiskState`.
- **Gate 9 Criteria:** 100% passing rate on 70 unit and integration tests; strict fail-closed contract; zero direct broker execution authority in Phase 9. Commit: `6bd40d8`.

---

### ✅ Phase 10: Runtime Orchestration & Continuous Paper Operations [COMPLETED & FROZEN]
- **Objective:** Establish the 5-stage authoritative runtime supervisor, operational scheduler, and append-only event ledger for continuous paper operations.
- **Deliverables:**
  - `RuntimeSupervisor`: 5-stage fail-closed pipeline orchestrator ($\text{Data} \to \text{Census} \to \text{Tournament} \to \text{Risk} \to \text{Admission}$).
  - `OperationalScheduler`: Dual-clock discipline ($as\_of\_utc \neq wall\_clock\_utc$), cadence evaluation, and concurrency lockout.
  - `OperationalLedger`: Append-only SHA-256 chained disk ledger (`OperationalCycleEvent`) with replay and tampering verification.
  - `ContinuousPaperDaemon`: Long-running paper harness loop with pre-flight fail-closed ledger checks and zero live capital authority.
- **Gate 10 Criteria:** 904 repository tests passing; full cross-phase integration suite; zero direct broker sockets in runtime layer. Commit: `3955bf6`.

---

### ✅ Phase 11: Forward Tracking, Online Drift Detection & Execution Reality Attribution [APPROVED & FROZEN]
- **Objective:** Provide an independent observational and evidence plane to monitor forward strategy decay and attribute realized execution drag from Phase 7 fills without mutating historical research or overwriting allocation policies.
- **Pre-Phase-11 Architecture Hygiene:** Source-of-truth documentation synchronized (`docs/architecture/system_architecture.md`), dual-clock determinism verified (`Supervisor cycle => explicit as_of_utc`), one-way Decimal precision boundary established, and 3-tier hashing authority classified.
- **Deliverables (Contract v1.1):**
  - **Track A (Strategy Drift):** `ForwardObservation`, `ForwardWindowMetrics`, `ForwardHealthPolicy` (with anti-whipsaw hysteresis $N_{\text{degrade}}, M_{\text{recover}}, T_{\text{cooldown}}$), `ForwardHealthState`, `ForwardGovernanceRecommendation`, `StrategyForwardDriftEvidence`.
  - **Track B (Execution Reality):** `ExecutionObservation`, `RealizedExecutionDrag` (explicit signed conventions: gross drag $\ge 0$, net realized drag = gross - rebate), `ExecutionAttributionPolicy`, `ExecutionCostEvidence` (with sample count, coverage ratio, and confidence interval metadata).
  - **Track C (Ingestion & Forensic Persistence):** `ForwardTelemetryIngestor` with decoupled Stream Integrity Plane (`VALID` $\leftrightarrow$ `BLOCKED`) vs Strategy Health Plane, explicit `reinitialize_stream()` epoch recovery without backfilling gaps, and `MonitoringEvidenceLedger` adapting Phase 10 `OperationalLedger`.
  - **Core Invariants:**
    - $\text{Historical Research Qualification } (\text{Phase 8.5}) \neq \text{Current Forward Health } (\text{Phase 11})$.
    - $\text{Detection } \neq \text{Governance } \neq \text{Eligibility}$ (Phase 11 recommends; Phase 10 Stage 2 Census decides).
    - $\text{No Evidence } \neq \text{Negative Evidence}$ (telemetry disruption $\implies \text{MONITORING\_BLOCKED}$, not strategy decay).
    - $\text{Zero Decimal } \to \text{float } \to \text{Decimal in Evidence Generation}$.
    - $\text{Tier 1 CanonicalConfigSerializer Authority for all Evidence Digests}$.
    - $\text{Taker-Only Execution Scope Guard in v1 (Maker execution strictly rejected fail-closed)}$.
- **Gate 11 Criteria:** 1,020 collected tests (1,017 passed, 3 skipped, 0 failed); 26/26 Red-Team Adversarial Vectors PASSED; 9/9 Cross-Phase Integration Tests PASSED; 107/107 Monitoring Unit Tests PASSED; MyPy 0 errors across 40 files; Git clean with zero modifications to Phases 1–10. Commit: `092a2b1`.
- **Release Caveats:**
  1. Authority decoupling ("no authority creep") is verified against current implementation behaviors and structural interfaces rather than an eternal mathematical impossibility against future arbitrary modification.
  2. Remote CI was not independently available/executed in this environment; all release guarantees are fully verified on local canonical execution.

---

### ✅ Phase 12: MT5 & Venue Execution Adapters [COMPLETED & FROZEN — `1e1d154`]
- **Objective:** Build thin, secure broker connectivity adapters with authoritative 6-D reconciliation.
- **Deliverables:**
  - **Slice 1:** MT5 Domain Schemas, Enums & Broker Mapping (BMAP-MT5)
  - **Slice 2:** `BrokerSymbolSpec` — Immutable instrument spec, Decimal volume quantization, tick-grid price alignment
  - **Slice 3:** MT5 Terminal Driver & IPC Transport Bridge (Windows Local `NativeMT5Transport`)
  - **Slice 4:** `MT5BrokerAdapter` & Authoritative 6-Dimensional Reconciliation Engine
  - **RECON-6D Rev1–7:** Reconciliation remediation (R4-FIX through R7-FIX, all fail-closed). Commit: `44202fe`
  - **Slice 5:** Execution Lifecycle Integration — `intent_id` as exclusive Gate 6 routing key; Two-Phase preflight atomicity routing (Phase A: duplicate/lineage/coordinator validation; Phase B: evidence delivery). Commit: `1e1d154`
  - **Slice 6 (Freeze):** Architecture conformance audit, safety gate verification, frozen contract inventory, TradingView deferred backlog. See: `docs/phase12/closeout_report.md`
- **Frozen Contracts:** `transition_order()` sole authority; `intent_id` sole routing key; `can_dispatch()` gate; UNKNOWN semantics; ACK≠FILLED; BLOCKED absorbing; $0.00 live capital
- **Deferred:** TradingView Ingress Gateway (signal ingress — separate independent backlog item; does NOT gate Phase 13)
- **Gate 12 Criteria Met:** 1240/1240 tests passed (1158 unit + 82 integration); MyPy 0 errors in 263 files; Architecture conformance audit passed; Full frozen contract inventory documented. Commit: `1e1d154`.

---

### 🟡 Phase 13: Live Small Capital Deployment [INFRASTRUCTURE READY / STRATEGY BLOCKED]
- **Objective:** Real-world execution validation with micro-capital and strict fail-closed telemetry.
- **Current Step Progress:**
  - **Slice 1 (Gate A Pre-Live Certification):** `✅ CERTIFIED` (Formal Human Sign-Off on 2026-09-04; A-1 through A-11 PASS; B-1/B-2 CLOSED; 0 Active Blockers; Demo `112040157` 100% Flat; Live Capital $0.00). See [`docs/phase13/consolidated_gate_a_audit.md`](phase13/consolidated_gate_a_audit.md).
  - **Step 1 (Implementation & Safety Envelopes):** `✅ PASS` (Bounded position limits, fail-closed kill switch).
  - **Step 2 (Code & Unit Audit):** `✅ PASS` (Full unit audit clean).
  - **Step 3 (Integration Testing):** `✅ PASS` (Integration pipeline verified).
  - **Step 4 (Restart & Recovery):** `✅ PASS` (Rehydration semantics and state reconstruction verified).
  - **Step 5 (24-Hour Unattended Soak):** `✅ VERIFIED COMPLETED` (86,400.21s runtime, 86,085 ledger events, 8,608 telemetry records, 0 errors, graceful exit).
  - **Step 6 (Telemetry Audit):** `✅ PASS` (Full forensic audit verified: SHA-256 chained integrity, zero gaps >15s, RSS peak 175.29 MB, pulse reconciliation 100%). See [`docs/phase13/phase13_step6_full_audit_report.md`](phase13/phase13_step6_full_audit_report.md).
  - **Step 7 (Continuous Paper Readiness):** `✅ CONDITIONALLY SATISFIED` (Runtime infrastructure verified ready; blocked on strategy qualification; B23.2 dedicated VM deferred). See [`docs/phase13/phase13_step7_paper_readiness_review.md`](phase13/phase13_step7_paper_readiness_review.md).
  - **Gate G7 / Stage S11 (Homelab 6-Hour Operational Soak):** `✅ CLOSED / PASS`
    - **Session ID:** `E3.5-20260913-025117-de2762`
    - **Adjudication Basis:** Explicit **Human Forensic Adjudication**
    - **Historical Harness Result:** `FAIL` (due to `SESSION_ID=unknown` evidence/session-binding defect in the runner script; post-run harness looked for `unknown.*` evidence files).
    - **Canonical Accepted Result:** `PASS` (actual sealed session artifacts independently recovered and verified; satisfies all ratified G7 criteria).
    - **Verified Evidence:**
      - *Duration:* $\ge 6.00$ hours continuous runtime (canonical manifest: 21,639.299524s [start `2026-09-13T02:51:17.970702Z`, end `2026-09-13T08:51:57.270226Z`]; host harness-loop: 21,624s).
      - *M1 Continuity:* 361 `MARKET_BAR_RECEIVED` events with unique timestamps (first `02:51:59.999000Z`, last `08:51:59.999000Z`) spanning 360 exact one-minute intervals (0 missing M1 slots, 0 duplicate timestamps, 0 non-60-second intervals).
      - *Process Stability:* Zero restarts (`RestartCount == 0`), zero OOM kills.
      - *Journal & Reconciliation:* Journal integrity PASS (chained SHA-256 event hashes), reconciliation PASS (100% pulse parity), sealed manifest.
      - *Feed Lifecycle:* Zero failure-shaped or unplanned feed interruptions; one final graceful shutdown disconnect (`FEED_CONNECTED=1`, `FEED_DISCONNECTED=1`, failure disconnects `0`). No recovery was used (`RECOVERY_ATTEMPTED=0`). Governance policy remained strictly Explicit Operator Resume Only / no automatic reconnect.
      - *Container Memory:* Observed container-memory samples were accepted as sufficient by explicit Human Forensic Adjudication (24 periodic docker stats samples: min 34.60 MiB, max 50.08 MiB vs 512 MiB limit, within expected operating envelope <150 MiB).
      - *VictoriaMetrics Scrape:* Continuous active-window telemetry (1,443 samples at 15s cadence, `up=1` and `acash_paper_up=1` throughout active window; zero active-window dropouts; teardown `up=0` belongs to post-session shutdown).
    - **Pi Tooling Remediation:** Verifier remediation merged into `Ratthabhumi/Pi_Personal-Infrastructure/main` at commit `68142aecdccf636912902bbfc4061895c877d195`. Verifier enforces canonical invariant: **ZERO REAL ORDER SUBMISSIONS** (`ORDER_SUBMITTED == 0`, `manifest.no_real_orders == true`, `manifest.simulated_fills_only == true`). Distinguishes allowed internal simulated paper order accounting (`ORDER_INTENT_CREATED`, `FILL_SIMULATED`, non-zero `total_order_count`) from prohibited real broker dispatches. Requirement `total_order_count == 0` eliminated.
    - **Known Non-Blocking Follow-Up Debt:**
      1. *Pi diagnostic formatting:* `jq -r ".${field} // empty"` may display boolean `false` as empty/missing in diagnostic logs; enforcement remains strict fail-closed.
      2. *ACASH manifest docstring:* `manifest.py` docstring states `total_order_count: Total orders submitted` while runtime behavior counts internal simulated order intents (documentation debt; does not represent real broker dispatches).
  - **Step 8 (Human GO Checkpoint):** `🔒 LOCKED` (Awaiting qualified strategy & explicit operator authorization).
  - **Step 9 (90-Day Continuous Paper Run):** `🔒 NOT AUTHORIZED` (Clock has not started; $0.00 capital authority).
- **Core Invariants:**
  - Live Capital Authority: **$0.00 (Hard-Locked)**.
  - Live Real Orders: **0 Orders** (`NO_REAL_ORDERS=true`, `simulated_fills_only=true`).
  - Strategy STRAT-MOM-MULTI-HORIZON-V1: **NOT QUALIFIED / TERMINALLY FALSIFIED**.
  - Broker Wire: **DISCONNECTED**.
  - Paper Trading: **NOT AUTHORIZED**.
  - Live Trading: **LOCKED**.
  - Backtesting: **LOCKED**.
  - HYP_003: **NOT CREATED**.
  - R1: **NOT STARTED**.
  - **NEXT GOVERNANCE TRANSITION: AWAITING HUMAN DECISION**.
- **Gate 13 Criteria:** **EXPLICIT HUMAN APPROVAL REQUIRED**; all safety gates, kill switches, and alerts verified operational; full completion of 24h soak evidence audit and subsequent steps.
- **Multi-Broker / Multi-Asset Roadmap (ADR-021):** While Phase 13 currently executes against the active MetaQuotes MT5 Demo baseline under Gate A, the long-term architecture is established as Asset-Agnostic and Multi-Venue (Pepperstone MT5 candidate, Alpaca US Equities/ETF candidate, OANDA API candidate, IBKR multi-asset candidate). See [`docs/architecture/multi_broker_multi_asset_decision.md`](architecture/multi_broker_multi_asset_decision.md).

---

### 📐 Phase 14: AI Quantitative Research Layer [GATE 14 ACCEPTED — RESEARCH CAPABILITY — UNVALIDATED PROPOSALS — ZERO TRADING AUTHORITY]
- **Objective:** Augment quant research with AI-driven hypothesis formulation, feature discovery, and automated research reporting conforming to Section 33.
- **Current Status:**
  - Master Research Architecture Revision 1.2: **APPROVED AT PLAN LEVEL** by Human Auditor (2026-09-08).
  - Gate 14: **ACCEPTED** (2026-09-08) — technical acceptance of the Phase 14 research capability under the G-2 CUSTOM-2 scope. **NOT** trading, runtime, or strategy authorization.
  - Governance records on file in `docs/phase14/`: Human Ratification D1–D4 (2026-09-08), D5/D6 ratification, D8-B acceptance, E1–E9 ratification, Gate 14 acceptance, S5 test-only and Seam B acceptance, evidence-bridge governance freeze.
  - Implementation slices exist in the repository as **UNVALIDATED PROPOSALS** (research-AI hypothesis assistant / converter / prompts / provider; slices 1–4; D6 Option A failed/invalid-trial census sealing; Phase 5 production orchestrator; D8-B release gate; Seam A identity; D5 OOS provenance with PIT lineage; committed 2026-09-07 / 2026-09-09). Zero authority to register hypotheses, qualify alpha, certify validation, connect brokers, or trade.
  - Runtime authorization remains bounded by ratified Human gate discipline (G-gates). Phase 13 Steps 8–9 remain independently and strictly LOCKED. HYP_003 NOT CREATED; R1 NOT INVOKED; capital $0.00; trading LOCKED; broker DISCONNECTED.
  - Governing Specification: [`docs/phase14/phase14_master_research_architecture_plan.md`](phase14/phase14_master_research_architecture_plan.md).
- **Deliverables:**
  - LLM hypothesis formulation assistant (`acash.research.ai.hypothesis`).
  - Automated research report generator conforming to Section 33 (`acash.research.ai.reporting`).
  - Exploratory feature discovery tools with causal AST validation (`acash.research.ai.features`).
  - Research corpus ingestion with tri-axial source epistemic metadata (`acash.research.ai.corpus`).
- **Gate 14 Criteria:** AI outputs are strictly unvalidated proposals; must pass full backtesting, statistical validation, and alpha qualification gates. Zero capital or broker authority.

---

### ⏳ Phase 15: Strategy Lifecycle Management [HARMONIZED INTO PHASE 17]
- **Harmonization Notice:** The original conceptual Phase 15 scope has been preserved and incorporated into the institutional Phase 17 Strategy Admission Standard and Lifecycle Architecture (ADR-023).
- **Preserved Scope:**
  - Strategy Lifecycle State Machine
  - Strategy admission status transitions (`StrategyAdmissionStatus`, `StrategyLifecycleState`)
  - Lifecycle gates and transition authority
  - Rolling strategy health / lifecycle monitoring
- **Canonical Home:** Phase 17 (`StrategyAdmissionStatus`, `StrategyLifecycleState`, ADR-023).
- **No Requirements Deleted:** All original Phase 15 requirements remain traceable in [`docs/architecture/strategy_admission_standard.md`](architecture/strategy_admission_standard.md).
- **Implementation Status:** `HARMONIZED / NOT A SEPARATE IMPLEMENTATION STEP`

---

### ⏳ Phase 16: Performance Degradation & Data Flywheel [HARMONIZED INTO PHASE 17–22]
- **Harmonization Notice:** The original conceptual Phase 16 scope has been redistributed across the institutional Phase 17–22 architecture sequence.
- **Preserved Scope:**
  - Statistical performance degradation detection → Phase 17 + Phase 11
  - Strategy selection and decision outcomes → Phase 20
  - Organizational memory / learning ledger → Phase 22
- **Canonical Traceability:** [`docs/architecture/strategy_admission_standard.md`](architecture/strategy_admission_standard.md) and ADR-023.
- **No Requirements Deleted:** Original Phase 16 concepts remain preserved and traceable.
- **Implementation Status:** `HARMONIZED / NOT A SEPARATE IMPLEMENTATION STEP`

---

### ✅ Phase 17: Strategy Admission Standard & Regime-Aware Capital Allocation Framework [SPECIFIED — ADR-023]
- **Objective:** Institutional governance foundation establishing the mandatory gateway before any strategy may enter the catalog or receive capital.
- **Deliverables:**
  - 11-Gate Admission Standard (Gate 0–10) incorporating the 20 Mandatory Admission Questions.
  - Epistemic Identity: $\text{Observed Profit} \neq \text{Proven Skill} \neq \text{Structural Edge} \neq \text{Luck-Free Performance}$.
  - Performance Attribution across 5 sources (Skill, Structural Edge, Beta/Factor, Regime Tailwind, Luck).
  - Multi-dimensional `SkillEvidence` vector DTO using `EvidenceSupportLevel` (scalar composite scores strictly forbidden).
  - `AlternativeExplanationRegister` tracking counter-hypotheses (Market Beta, Short Vol, Regime Tailwind, Selection Bias, Execution Fantasy).
  - `EffectiveEvidenceSample` ($N_{\text{eff}}$) with declared dependency assumptions (rejection of raw trade count & calendar duration as sole evidence).
  - Quant Candlestick Architecture: `PriceStructureMeasurements` (returns, range/ATR, body/range, wick asymmetry, close location, gap) feeding continuous `MarketStateVector`.
  - Decoupled `VolumeType` (`TICK_VOLUME`, `REAL_VOLUME`, `EXCHANGE_VOLUME`, `UNKNOWN`).
  - Decoupled `StrategyMechanism` (market interaction) vs `StrategyStyle` (behavioral style).
  - Bounded Capital Allocation contracts enforcing the core invariant: **`allocation = $0.00` is always valid and default**.
- **Governance:** Live capital remains hard-locked at $0.00; zero broker mutations; optimization solvers deferred to Phase 21; live regime engine deferred to Phase 19.

---

### ⏳ Phase 18: Strategy Research & Tournament Pipeline [UPCOMING]
- **Objective:** Automated, reproducible research execution, hypothesis evaluation, and fair tournament ranking with frozen prior criteria and winner's curse discounting.

---

### ⏳ Phase 19: Empirical Regime Detection Engine [UPCOMING]
- **Objective:** Empirical estimation and online classification of market states (orthogonal trend, volatility, liquidity, spread, and microstructure dimensions) with probabilistic confidence.

---

### ⏳ Phase 20: Regime × Strategy Selection & Decision Engine [UPCOMING]
- **Objective:** Dynamic strategy eligibility gating, state compatibility matching, and multi-horizon decision memory recording.

---

### ⏳ Phase 21: Risk-Based Capital Allocation Solvers [UPCOMING]
- **Objective:** Production mathematical solvers (Equal Risk Contribution, Volatility Targeting, Haircut Optimization) adhering to Phase 17 `IAllocationPolicy` and safety bounds.

---

### ⏳ Phase 22: Portfolio / Multi-Strategy Orchestration & Memory Flywheel [UPCOMING]
- **Objective:** Enterprise multi-strategy execution orchestration, aggregate exposure netting, cross-strategy margin monitoring, and long-term organizational decision memory ledger.

---

### 🏛️ Phase 23: Adaptive Multi-Horizon Strategy & Market-Regime Architecture [ARCHITECTURAL RECORD]
- **Objective:** Establish the foundational architectural principle that ACASH is a strategy-agnostic, risk-controlled trading infrastructure rather than a fixed-style bot (scalping, intraday, swing, long-term).
- **Core Governance & Decoupling:**
  - Decouple ACASH Core (Risk, Execution, Reconciliation, Governance) from Strategy Layer (Alpha models, horizons, styles).
  - Strategy $\neq$ Authority; Signal $\neq$ Order; Target Position $\neq$ Execution.
  - Rejection of global fixed slice allocations (e.g. 30/30/40) in favor of Target Position, Risk Budget, Entry Schedule, and Dynamic Recalculation.
  - Confirmation-driven pyramiding default; strict rejection of blind averaging down as core default.
  - Dynamic risk recalculation per entry tranche; position size strictly bounded by stop distance.
  - Formally specified in ADR-024 and [`docs/architecture/adaptive_multi_horizon_strategy_architecture.md`](architecture/adaptive_multi_horizon_strategy_architecture.md).
- **Phase 23 Amendment (Market Microstructure, Order-Book Intelligence & Shadow Decision Learning):**
  - Formally extends Phase 23 to incorporate Level 3 order-book event streams, temporal microstructure analysis, liquidity anomaly research, and shadow decision evaluation (ADR-025).
  - Documented in [`docs/architecture/phase23_amendment_microstructure_and_shadow_decisions.md`](architecture/phase23_amendment_microstructure_and_shadow_decisions.md).
  - Proposed future implementation phases (pending audit and roadmap approval):
    - *Phase 24 [Proposed]:* Market Microstructure Data Layer & L3 Event Normalization
    - *Phase 25 [Proposed]:* Deterministic Microstructure Replay Engine
    - *Phase 26 [Proposed]:* Temporal Microstructure Feature & Anomaly Research Engine
    - *Phase 27 [Proposed]:* Shadow Decision Evaluation & Counterfactual Learning System
    - *Phase 28 [Proposed]:* Adaptive Strategy Tournament & Multi-Horizon Integration

---

## Reality Gap Analysis & Execution Deviation

The core empirical objective of ACASH is measuring:
> *"How much does what we expected in simulation diverge from what actually happened in the live market?"*

```
                 BACKTEST SIMULATION
                          │
                          ▼
                 PAPER / SHADOW TRADING
                          │
                          ▼
                    LIVE EXECUTION
                          │
                          ▼
               REALITY GAP ATTRIBUTION
```

### Multi-Phase Reality Pipeline:
- **Phase 2+ (Data Quality):** Data fidelity matching strategy horizon, timestamp integrity, provenance, spread capture.
- **Phase 5+ (Backtest):** Tick-aware simulation, data-supported spread fidelity, graduated slippage models (simple $\to$ calibrated $\to$ liquidity-aware).
- **Phase 6+ (Validation):** OOS, walk-forward matrix, forward testing, stress testing, regime analysis.
- **Phase 12+ (Live):** Actual fills, realized spreads, actual slippage, latency, broker reconciliation.
- **Phase 13+ (Reality Gap Attribution):** Systematic deviation tracking attributed to: Data error, Model/alpha error, Execution error, or Venue conditions.

### Deviation Metrics & Example:
| Metric | Expected (Simulation) | Actual (Live) | Reality Gap Deviation |
| :--- | :--- | :--- | :--- |
| **Entry Price** | 100.00 | 100.07 | **+7 bps** |
| **Prevailing Spread** | 2 bps | 9 bps | **+7 bps** |
| **Execution Slippage** | 1 bp | 6 bps | **+5 bps** |
| **Trade PnL** | +$240 | +$181 | **-24.6%** |
| **Roundtrip Latency** | 15 ms | 120 ms | **+105 ms** |

---

## License Notice

**Copyright © 2026 Ratthabhumi & ACASH Contributors. All Rights Reserved.**  
Proprietary and Confidential. Unauthorized copying, distribution, modification, or extraction is strictly prohibited.
