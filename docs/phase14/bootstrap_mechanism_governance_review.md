# ACASH V5 — BOOTSTRAP MECHANISM GOVERNANCE REVIEW

**Document ID:** `docs/phase14/bootstrap_mechanism_governance_review.md`
**Object:** Governance review of the Free-Data Capital Bootstrap mechanisms — identify the recommended FIRST candidate for Human authorization toward a future empirical-validation phase under the $0 Free-Data lane
**Status:** `[DOCUMENTATION-ONLY]` · `[GOVERNANCE REVIEW]` · `[NOT HYP_003]` · `[NOT R1]` · `[NOT D2]` · `[NOT F-1]`
**Date:** 2026-09-10
**Authority:** explicit Human Governance review instruction of 2026-09-10 (mandated 22-dimension A–V rubric); `AGENTS.md`; `./research_doctrine.md`; `./free_data_capital_bootstrap_program.md` (charter); companion registries (`./free_data_source_registry.md`, `./free_data_research_registry.md`); SSRN mechanism research (`./ssrn_mechanism_research.md`); F-1 D1 baseline docs.
**Mode:** DOCUMENTATION-ONLY GOVERNANCE REVIEW. **No backtest. No empirical validation. No returns / Sharpe / CAGR / win-rate calculation. No parameter optimization. No strategy mining. No new candidate creation. No HYP_003. No R1. No Gate. No trading. No paid data. F-1 unchanged.**

> [!CAUTION]
> **This document decides nothing. It recommends.** Human Governance retains the exclusive authorization authority. Every recommendation here inherits the STOP boundary from the program charter (§16/§21/§22/§29): no candidate may proceed to empirical validation without an explicit Human Governance authorization per candidate.

**Epistemic discipline (doctrine §16 inherited):** literature-reported figures = `[SOURCE CLAIM]` (EXTERNAL CLAIM); `[MODEL INFERENCE]` = this review's reasoning; factual repository/git/doc states = `[VERIFIED FACT]` only where directly verified here; anything else = `[UNVERIFIED]`. A `[SOURCE CLAIM]` is never promoted to `[VERIFIED FACT]` and never becomes ACASH evidence.

---

## 1. OBJECTIVE

Determine which existing ACASH mechanism / registered candidate is the strongest **FIRST candidate for Human authorization** to proceed toward a **future empirical-validation phase** in the $0 Free-Data Capital Bootstrap lane — using the mandated ranking rule: mechanism clarity, $0 data availability, PIT integrity, survivorship control, reproducibility, cost-model defensibility, implementation simplicity, literature quality, low governance conflict, low leakage risk. **NOT by reported performance.** [MANDATED]

The review is documentation-only and produces **this single new document**. It recommends a candidate for a **future** authorization decision; it does not, and cannot, authorize empirical work.

---

## 2. GOVERNANCE BOUNDARY

Nothing in this review authorizes or performs: [FROZEN — all]

- Any empirical test, backtest, reproduction, simulation, optimization, parameter search, strategy or feature mining.
- Any `HYP_003` creation or registry write, `R1` start, ReInceptionGate / ValidationGate / AlphaQualificationGate invocation.
- Any `src/` / `tests/` / `schemas/` / `gates/` change.
- Any paper trading, live trading, broker connection, or capital deployment (`CAPITAL = $0.00`).
- Any paid data subscription, paid plan, payment detail, premium endpoint, or vendor contact. (Charter §3, §27.)
- Any modification of F-1, of the registered `CAND-FREE-*-001` specifications, or any status promotion in any registry. Any candidate specification change → `SPECIFICATION GAP`, requires a NEW version + Human Governance decision.
- Any creation of a new `CAND-*` ID, and any promotion of a `MEC-XXXX` literature concept into a `CAND-*`. (MEC = literature concept record; CAND = formally registered candidate. See §5/§6.)
- Any re-interpretation or reopening of the terminally falsified `HYP_001` / `HYP_002` (EURUSD TSMOM families; quarantined windows preserved).

A Human decision is required before any of the above may change.

---

## 3. VERIFIED GIT BASELINE

Verified immediately before and after this task with `git status --short --branch`, `git rev-parse HEAD`, `git rev-parse origin/main`: [VERIFIED FACT]

```
## main...origin/main
HEAD       = fff20b9
origin/main = fff20b9
working tree = clean (apart from THIS new untracked file after creation)
```

- HEAD == origin/main == `fff20b9` (commit `docs(phase14): add free-data bootstrap program governance, source/research registries, and SSRN mechanism research (literature only)`). No divergence; history intact.
- Git policy for this task: **READ-ONLY** except creating `docs/phase14/bootstrap_mechanism_governance_review.md` (UNTRACKED). No `add / commit / push / fetch / pull / merge / rebase / reset / revert / stash`. No push is performed. [VERIFIED]

---

## 4. SOURCE DOCUMENTS REVIEWED

Read in full for this review: [VERIFIED FACT — reads performed 2026-09-10]

1. `docs/phase14/free_data_capital_bootstrap_program.md` (charter, 30 sections)
2. `docs/phase14/free_data_source_registry.md` (S-01 … S-28)
3. `docs/phase14/free_data_research_registry.md` (5 CAND-FREE proposals)
4. `docs/phase14/ssrn_mechanism_research.md` (MEC-0001 … MEC-0010)
5. `docs/phase14/research_doctrine.md`
6. `docs/phase14/research_candidates.md` (F-1…F-6; HYP_001/HYP_002 quarantine)
7. `docs/phase14/acash_market_research_ontology_v1.md` (non-normative ontology)
8. `docs/phase14/candidate_f1_flow_calendar_rebalance_review.md` (F-1 specification freeze)
9. `docs/phase14/f1_d1_free_data_feasibility.md` (D1 free-first audit)
10. `docs/phase14/f1_d1_blocker_resolution.md` (D1 B1–B6)
11. `docs/phase14/f1_d1_final_feasibility_reassessment.md` (D1 final re-assessment; 18-item readiness checklist)
12. `docs/phase14/f1_d1_human_governance_ratification.md` (D1-A / D1-B human decisions)

---

## 5. MECHANISMS UNDER REVIEW

Primary mechanisms (mandated input set; literature-concept records `MEC-XXXX` from the SSRN research — **not candidates, not CAND-***): [MANDATED]

| MEC | Mechanism (abbrev.) | SSRN classification | SSRN shortlist rank |
|---|---|---|---|
| **MEC-0001** | Scheduled macro-announcement premium conditioning | `[ACCEPT]` | 1 |
| **MEC-0005** | Variance Risk Premium conditioning | `[ACCEPT]` | 2 |
| **MEC-0004** | Time-Series Momentum (index-level, SPX) | `[ACCEPT]` | 3 |
| **MEC-0003** | Short-term reversal (correctly measured weekly) | `[CONDITIONAL]` | 4 |
| **MEC-0009** | Aggregate opportunity-aware insider Form-4 flows | `[CONDITIONAL]` | 5 |

Boundary rules applied to this review: [MANDATED]

- **No new `MEC-*` mechanism is created by this review.**
- **No `MEC-*` is promoted to `CAND-*`.** Reclassification or intake = `MECHANISM INTAKE REQUIRES HUMAN GOVERNANCE`.
- **MEC-0007 (index reconstitution / rebalance demand pressure) is EXCLUDED from this Bootstrap review** — it is the F-1-lane native family (charter §2 lane separation; SSRN §13). Stated here once: MEC-0007 stays in the F-1 lane, D1 = NOT READY / CONDITIONAL, B2 = BLOCKED, B5 = UNVERIFIED. See §22.
- MEC-0002, MEC-0006, MEC-0008, MEC-0010 remain analysis layers or deferred/unranked concepts from the SSRN work; they are not part of this review's candidate recommendation. MEC-0008 (cost layer) is referenced as the cost-defensibility tool.

Cross-referenced registered candidates (research registry): `CAND-FREE-PEAD-001`, `CAND-FREE-MACRO-001`, `CAND-FREE-VOL-001`, `CAND-FREE-MOM-001`, `CAND-FREE-REV-001` — all at `SPEC_FREEZING` and stopped at `HUMAN_REVIEW_REQUIRED` (empirical validation `NOT AUTHORIZED`). [VERIFIED FACT — registry]

---

## 6. EXISTING CANDIDATE MAPPING

| MEC (concept) | Registered candidate | Registry data-feasibility | Mechanism↔candidate relationship |
|---|---|---|---|
| MEC-0001 (M-V1) | **CAND-FREE-MACRO-001** | `[ACCEPT]` | Overlay: the macro-announcement concept sits on the existing MACRO candidate family. |
| MEC-0005 (M-V2) | **CAND-FREE-VOL-001** | `[ACCEPT]` (vintage conditional) | Overlay: VRP conditioning on the existing VOL candidate family. |
| MEC-0004 (M-T1) | **NONE registered** | — | No registered candidate overlays index-level TSMOM. Nearest neighbor `CAND-FREE-MOM-001` is **cross-sectional** 12-1/6-1 momentum (family 3) — a DIFFERENT construct (cross-section over names vs. time-series on an index). |
| MEC-0003 (M-R1) | **CAND-FREE-REV-001** | `[CONDITIONAL]` (survivorship + cost) | Partial overlay. CAUTION: `CAND-FREE-REV-001` is frozen as 5-day formation / 5-day hold (family 4). M-R1 is a "correctly measured weekly" construct (Stosik-Zaremba measure, SSRN 6630998). If the weekly measure differs from the frozen REV spec ⇒ **`SPECIFICATION GAP`** ⇒ do NOT edit `CAND-FREE-REV-001`; a new candidate/version requires Human Governance. |
| MEC-0009 (M-I1) | **NONE registered** | — | No registered candidate. Shares $0 source S-01 (EDGAR) with `CAND-FREE-PEAD-001` but the mechanism is distinct (aggregate insider timing vs. single-name earnings drift). |

Mapping conclusion [MODEL INFERENCE]: two of the five primary mechanisms (MEC-0001, MEC-0005) already have **registered, specification-frozen, `[ACCEPT]`-rated candidates** — i.e., the lowest-governance-friction path to a first Human empirical-validation authorization. The other three (MEC-0004, MEC-0003 corrected-measure, MEC-0009) are concept-level and would additionally require mechanism intake / candidate proposal / spec freeze before any empirical step.

---

## 7. $0 DATA FEASIBILITY AUDIT

Classification labels inherited: `[ACCEPT]` `[CONDITIONAL]` `[UNVERIFIED]` `[NOT SUFFICIENT AT $0]` `[REJECT]`. Sources per `free_data_source_registry.md` (S-XX). [VERIFIED FACT — source registry classifications]

| Mechanism | $0 data inputs (registry sources) | $0 verdict | Binding constraint |
|---|---|---|---|
| MEC-0001 | BLS CPI/NFP schedule (S-05 `[ACCEPT]`); FOMC calendar/statements (S-08 `[ACCEPT]`); Treasury schedule (S-06 `[ACCEPT]`); SPX index (S-04 FRED `[ACCEPT]`); SPY robustness (S-10/S-18 active `[CONDITIONAL]`) | **`[ACCEPT]`** | None structural |
| MEC-0005 | VIXCLS (S-04 `[ACCEPT]`, vintage `[CONDITIONAL]`); CBOE VIX daily (S-07 `[CONDITIONAL]`); SPX (S-04/S-10) | **`[ACCEPT]`** | VRP estimator definition; as-published vintage discipline |
| MEC-0004 | Index value close archives (S-04 FRED SP500 `[ACCEPT]`; S-10 `^spx` `[CONDITIONAL]`) | **`[ACCEPT]`** | Provider rebasing must be PIT-audited; index chosen must not be a backtest-mined survivor |
| MEC-0003 | Active-name daily OHLCV (S-10/S-18 `[CONDITIONAL]`); pinned roster as-of (S-13/S-14 `[CONDITIONAL]`); delisted identities (S-01/S-02 `[ACCEPT]`, no prices) | **`[CONDITIONAL]`** | Delisted OHLCV leg `[NOT SUFFICIENT AT $0]` (charter B-2); cost model dominates |
| MEC-0009 | EDGAR Form 3/4/5 + accession stamps (S-01 `[ACCEPT]`); aggregate index series (S-04) | **`[CONDITIONAL]`** | Parser/schema effort; evidence base single-record (`EVIDENCE = UNVERIFIED`) |

Cross-cutting `[VERIFIED FACT]`: no WRDS / CRSP / Bloomberg / Refinitiv / Compustat / TAQ / provider membership lists are assumed (SSRN §6; charter §3). Delisted OHLCV has **no certified $0 path** (source registry §4: S-19 exploratory-only, S-21 `[NOT SUFFICIENT AT $0]`, S-23 license `[UNVERIFIED]` — do NOT promote).

---

## 8. PIT AUDIT

Seven-question PIT audit operationalized from the frozen PIT hard rule (charter §10: unprovable PIT ⇒ `PIT = UNVERIFIED`; F-1 PIT hard rule extended to this track) and the source-registry PIT fields. Each question must pass **before** an observation is research-eligible. [MANDATED — derived from doctrine/charter; no observation is claimed eligible here]

**PIT audit questions:**
1. **Observability before decision** — is the information knowable strictly before the decision time (no backdating of current information)?
2. **Immutable timestamp** — does each observation carry an immutable, versioned timestamp (acceptance / accession / publish)?
3. **Event ordering** — is the signal anchored to an official publication so that signal-time < effective/decision-time (announce < effective)?
4. **Source mutation / vintage** — is the source immutable or does it expose vintage IDs; if mutable, is archive-at-retrieval (as-published capture + fetch timestamp) required/documented?
5. **Roster / universe pinning** — are universe/roster snapshots pinned as-of the decision date (no current-membership backfill)?
6. **Trailing estimators** — do all lookbacks, rolling windows, and estimators use only data available at construction time?
7. **Revision / lag handling** — are revisions (index rebasing, realized-vol revisions, fund-lag, filing-acceptance lag) explicitly ordered so the later value never leaks backward?

| Mechanism | PIT verdict | Notes per question set |
|---|---|---|
| MEC-0001 | **PIT SECURE** | Q1/Q3 pass — calendars pre-announced and versioned (S-05/S-08 `[ACCEPT]`); Q4 — archive release times; rare early-release count adjustments must be archived; no roster (Q5 N/A); index closes dated (Q6/Q7 fine). |
| MEC-0005 | **PIT SECURE (modulo as-published)** | Q1/Q3 pass (daily official closes); Q4 — vintage discipline for VIXCLS; Q7 — realized-vol revisions: use as-published values only. |
| MEC-0004 | **PIT SECURE (careful sourcing)** | Q1/Q7 — must use **published-at-date** index values; current-index-with-rebased-history from a provider is a lookahead trap (S-10 `[PIT UNPROVEN]` unless archived). |
| MEC-0003 | **PIT SECURE for price inputs; roster-PIT CONDITIONAL** | Q1/Q6 pass (lag constructed from past closes); Q5 binding — roster pinning via S-13/S-14 as-of; delisted identity leg (S-01/S-02) for disclosure only, price leg absent at $0. |
| MEC-0009 | **PIT SECURE** | Q2 pass (immutable accession stamps); Q6 pass (trailing-only aggregation windows); Q5 N/A (aggregate index level). |

---

## 9. SURVIVORSHIP AUDIT

Survivorship classification inherited: `CLEAN` / `SURVIVORSHIP_LIMITED` / `UNVERIFIED`. Charter §9: any survivorship limitation is never concealed. [VERIFIED FACT — SSRN §8; registry §4]

| Mechanism | Survivorship exposure | Verification |
|---|---|---|
| MEC-0001 | **CLEAN** — index-level; current index value archive | Index-level (S-04/S-10 `^spx`/`^spy`) |
| MEC-0005 | **CLEAN** — index-level (VIX/SPX official series) | S-04/S-07 |
| MEC-0004 | **CLEAN** — index value archive used as-is (published-index-level history) | S-04/S-10 |
| MEC-0003 | **SURVIVORSHIP_LIMITED** — delisted-name prices absent (B-2) | Mandatory delisted-price audit at $0; currently `[NOT SUFFICIENT AT $0]` |
| MEC-0009 | **LOW at index level** — delisted firms' filings persist (addressable by CIK, S-01); aggregate only | Aggregate index-level overlay |

Registry-wide `[VERIFIED FACT]` (source registry §4): active-name OHLCV + delisted identities (S-01/S-02) exist; **delisted OHLCV has no certified $0 path** ⇒ any single-name equity candidate is `SURVIVORSHIP_LIMITED` unless a survivorship-free leg is added. **Index-level mechanisms are the survivorship-clean class at $0.**

---

## 10. CORPORATE ACTION / SECURITY MASTER AUDIT

| Mechanism | Corporate-action dependency | Security-master dependency | Audit verdict |
|---|---|---|---|
| MEC-0001 | Near-none at index level; dividend/split treatment is internal to the official index series; TR-vs-price-index is a spec choice (frozen pre-run) | None beyond index symbology | **LOW** |
| MEC-0005 | None (VIX/SPX official daily) | None | **LOW** |
| MEC-0004 | Near-none (index-level; dividend treatment = spec choice) | None beyond index symbology (S-12 for mapping if needed) | **LOW** |
| MEC-0003 | MODERATE — vendor-adjusted closes (S-10) adjustment method `[UNVERIFIED]`; structured split/dividend history free = `[UNVERIFIED]` (S-22 securitiesdb `[UNVERIFIED]`; S-20 businessquant `[CONDITIONAL]/[UNVERIFIED]`) | Delisted identities via S-01/S-02 `[ACCEPT]`; **delisted price coverage `[NOT SUFFICIENT AT $0]`** | **MODERATE — binding via $0 price leg** |
| MEC-0009 | None (filings, not prices) | N/A (aggregate) | **LOW** |

CAUTION note consistent with F-1 B4/B6 [VERIFIED FACT]: free structured split/dividend masters remain `[UNVERIFIED]`; no CA provenance is claimed at $0 for single-name constructs.

---

## 11. COST / EXECUTION FEASIBILITY

No profitability estimate is made anywhere in this review (prohibited). Cost realism is assessed qualitatively for feasibility. [MANDATED — cost defensibility, not returns]

| Mechanism | Cost profile | Cost-model defensibility at $0 |
|---|---|---|
| MEC-0001 | LOW–MODERATE — index instruments (SPY/index futures); event-day spread/whipsaw | Defensible: index-level fee/impact from public schedules; 0DTE microstructure shift (SSRN 5641974) noted for intraday framing |
| MEC-0005 | LOW — low-turnover daily conditioning, index-level | Defensible: public fee schedules; index-level |
| MEC-0004 | LOW at index-futures level; monthly rebalance | Defensible: index-level, low frequency |
| MEC-0003 | **HIGH sensitivity** — costs are the primary reversal-killer (Avramov/Chordia/Goyal lineage) | Weakest: conservative modeled costs can exceed edge at $0; registry flags `REJECT`-likely at validation unless the mechanism holds after costs |
| MEC-0009 | LOW — regime switch, not high-turnover | Defensible: low-frequency aggregate overlay |

Cross-cutting: MEC-0008 (illiquidity/spread-cost layer, `[ACCEPT]`) provides the $0 cost estimator — Abdi-Ranaldo OHLC spread proxy (SSRN 2725981) and Amihud ratio (SSRN 1295244). No fill-realism claim is made (registry convention).

---

## 12. LITERATURE QUALITY AND CRITICISM

Literature = `[SOURCE CLAIM]` (EXTERNAL CLAIM), never ACASH evidence. Evidence labels: `STRONG` / `MIXED` / `LIMITED` / `UNVERIFIED`. [VERIFIED FACT — SSRN §4/§12; criticism feeds from §12 of the SSRN doc]

| Mechanism | Evidence label | Key literature | Principal criticism / contradictory evidence |
|---|---|---|---|
| MEC-0001 | **`MIXED`** (STRONG corpus, contested persistence) | Savor & Wilson (SSRN 2024422, 1786308); Lucca & Moench pre-FOMC drift; FEDS 2026023 survey | Pre-FOMC drift **attenuated post-2015** (FEDS survey); EAP = priced risk, not automatable alpha; publication-decay literature (Schwert SSRN 338080; Jones & Pomorski SSRN 357860) |
| MEC-0005 | **`MIXED`** | Bekaert & Hoerova (SSRN 2431301); VIX term structure / basis (SSRN 3723837) | VRP-return link is state-dependent and crash-sensitive — conditioning layer, not standalone alpha |
| MEC-0004 | **`MIXED`** | Moskowitz, Ooi & Pedersen (SSRN 2089463); Barroso & Santa-Clara (SSRN 2041429) | Momentum crashes ("elephant in the room"); raw TSMOM alpha contested; decay/crowding literature |
| MEC-0003 | **`MIXED`** | Da, Liu & Schaumburg (SSRN 2022061); Stosik & Zaremba 2026 (SSRN 6630998) — "persists if properly measured" | Transaction-cost critiques (cost studies lineage) show naive reversal profits vanish net of costs; measurement-construction sensitivity |
| MEC-0009 | **`UNVERIFIED`** | Huang, Lin & Zheng (SSRN 4294492) — single record | Single-record evidence; AMH-sensitive timing effects; no independent corroboration screened |

Review inference [MODEL INFERENCE]: no mechanism in the review set reaches `STRONG` persistence, because the anomaly-decay corpus (Schwert; Jones & Pomorski) applies to all. That is a governance feature, not a defect: it is why the program rules rank **clarity, feasibility, and falsifiability** above reported performance.

---

## 13. LEAKAGE / ANTI-HARKING AUDIT

Anti-HARKing (charter §12): each registered candidate's spec is **frozen before any empirical test**; any post-result change = NEW candidate + documented reason + Human review. All `CAND-FREE-*` are `SPEC_FREEZING`. [VERIFIED FACT]

| Mechanism | Leakage vector | Control | Verdict |
|---|---|---|---|
| MEC-0001 | Release times vs. archive capture; rare early-release count adjustments | Calendars pre-announced (S-05/S-08); archive release time at retrieval | **LOW** |
| MEC-0005 | Realized-vol revisions | Use as-published VIXCLS/SPX; no revised-value leakage | **LOW** |
| MEC-0004 | Provider index rebasing (backfilled values) | Use published-at-date index values only | **LOW** (control mandatory) |
| MEC-0003 | Roster/survivorship exclusion (counted in §9); lag construction | As-of roster pinning; past-only lag; mandatory delisted-price disclosure | **MODERATE** (survivorship-dominated) |
| MEC-0009 | Filing-acceptance vs. trade-date lag (informational, not leakage if trailing-only) | Trailing-only aggregation windows | **LOW** |

Dependence discipline (doctrine 8) [MODEL INFERENCE]: MACRO and VOL share the SPX price leg, and any sequential validation on the same SPX series makes the two candidates **statistically dependent** on that shared data. They must never be labeled "orthogonal" or "independent" controls. Blind-window / IS-OOS isolation and no-OOS-reuse rules apply unchanged (charter §24).

---

## 14. GOVERNANCE CONFLICT AUDIT

| Mechanism | Conflict check | Verdict |
|---|---|---|
| MEC-0001, MEC-0005 | Family 7 index/rebalance? No (macro/vol family). F-1 overlap? None. HYP_001/HYP_002 overlap? None (no EURUSD, no TSMOM construct). | **NO CONFLICT** |
| MEC-0004 | F-1 overlap? None (not family 7). **HYP_001/HYP_002 adjacency:** HYP_001 (`HYP_TSMOM_EURUSD_001`, M5) and HYP_002 (`HYP_TSMOM_EURUSD_HTF_002`, H4) are **EURUSD unconditional time-series momentum**, terminally falsified, quarantined windows `2026-08-18..2026-09-04` and `2023-05-29..2024-12-31`. MEC-0004 = **SPX index-level TSMOM**: distinct market, distinct (no-FX) universe, no window reuse, no evidence reuse. **Mechanism-family name adjacency only.** | **NO MATERIAL OVERLAP.** Recorded: family-adjacency does NOT confer validity (research_candidates §6: "conceptually orthogonal ≠ valid"). Flagged below for Human acknowledgment (§20.6). |
| MEC-0003 | F-1 overlap? None. Corrected-weekly-measure vs. frozen `CAND-FREE-REV-001` 5-day/5-day: if different ⇒ `SPECIFICATION GAP`. | **NO CONFLICT**; spec-gap risk documented (§6). |
| MEC-0009 | F-1 overlap? None. EDGAR source shared with PEAD — mechanism distinct. | **NO CONFLICT** |
| MEC-0007 | Family-7 native mechanism. | **EXCLUDED — F-1 LANE ONLY** (§22). |

Conclusion [MODEL INFERENCE]: none of the five mechanisms conflicts materially with F-1 or with the terminally falsified HYP_001/HYP_002 evidence; MEC-0004 carries a family-adjacency note requiring Human acknowledgment but no data/evidence overlap. **No `GOVERNANCE CONFLICT / REQUIRES HUMAN REVIEW` declaration is warranted by material overlap.** (Had MEC-0004 reused any EURUSD window or evidence, it would have been declared.)

---

## 15. DECISION MATRIX (ORDINAL ONLY)

Ratings are ordinal categories — **VERY STRONG / STRONG / MODERATE / WEAK / BLOCKED** — assigned by this review from the evidence in §7–§14. **Ordinal only; no fabricated numeric scores; no performance metrics.** Dimension V is descriptive (human decisions still required), not ordinal. [MANDATED]

| # | Dimension (A–V) | MEC-0001 MACRO | MEC-0005 VRP | MEC-0004 TSMOM@index | MEC-0003 Rev(wk) | MEC-0009 Insider |
|---|---|---|---|---|---|---|
| A | Mechanism clarity | VERY STRONG | VERY STRONG | VERY STRONG | STRONG | STRONG |
| B | Economic rationale | VERY STRONG | VERY STRONG | VERY STRONG | STRONG | STRONG |
| C | Observable definition | VERY STRONG | VERY STRONG | VERY STRONG | STRONG | MODERATE |
| D | Data availability at $0 | VERY STRONG | VERY STRONG | STRONG | STRONG | STRONG |
| E | Data source quality | VERY STRONG | VERY STRONG | STRONG | MODERATE | VERY STRONG |
| F | PIT feasibility | VERY STRONG | VERY STRONG | STRONG | STRONG | VERY STRONG |
| G | Survivorship control | VERY STRONG | VERY STRONG | VERY STRONG | **WEAK** | VERY STRONG |
| H | Delisted/security-master dependency | VERY STRONG | VERY STRONG | VERY STRONG | **BLOCKED** (at $0) | VERY STRONG |
| I | Corporate-action dependency | VERY STRONG | VERY STRONG | VERY STRONG | MODERATE | VERY STRONG |
| J | Timestamp/event-ordering risk | STRONG | STRONG | STRONG | VERY STRONG | STRONG |
| K | Cost-model feasibility | STRONG | VERY STRONG | VERY STRONG | **WEAK** | VERY STRONG |
| L | Implementation complexity | VERY STRONG | VERY STRONG | VERY STRONG | STRONG | MODERATE |
| M | Reproducibility | VERY STRONG | VERY STRONG | VERY STRONG | VERY STRONG | MODERATE |
| N | Literature support | STRONG | STRONG | STRONG | STRONG | **WEAK** |
| O | Literature criticism/contradiction | MODERATE | MODERATE | MODERATE | MODERATE | **WEAK** |
| P | Known anomaly decay risk | MODERATE | MODERATE | MODERATE | MODERATE | MODERATE |
| Q | Data licensing/access risk | STRONG | STRONG | STRONG | MODERATE | VERY STRONG |
| R | Leakage risk | VERY STRONG | VERY STRONG | VERY STRONG | STRONG | STRONG |
| S | Governance complexity | VERY STRONG | VERY STRONG | MODERATE | MODERATE | MODERATE |
| T | Separation from F-1 / HYP_001 / HYP_002 | VERY STRONG | VERY STRONG | STRONG* | VERY STRONG | VERY STRONG |
| U | Empirical-validation readiness | STRONG | STRONG | MODERATE | MODERATE | WEAK |
| V | Human decisions still required | Authorize MACRO-001 validation; data-audit + manifest + auth note | Authorize VOL-001 validation; vintage discipline | Mechanism intake + candidate proposal + spec freeze + replication arm | Decide REV-001 disposition / corrected-measure intake | Replication arm (CONDITIONAL) + intake decision |

\* MEC-0004 (T): STRONG because of the documented family-adjacency to terminally falsified HYP_001/HYP_002 (see §14) — no evidence overlap, acknowledgment required.

**Matrix reading (ordinal, no arithmetic):** MEC-0001 records the most VERY-STRONG/STRONG cells with no WEAK or BLOCKED cell; MEC-0005 is a near-tie with a minor PIT-vintage caveat; MEC-0004 is strong but requires governance intake (S) and family-adjacency acknowledgment (T); MEC-0003 carries WEAK/BLOCKED cells in survivorship, delisted-price, and cost dimensions; MEC-0009 is data/PIT-clean but literature-weak (N/O = WEAK).

---

## 16. CANDIDATE-BY-CANDIDATE ASSESSMENT

- **MEC-0001 / CAND-FREE-MACRO-001.** Highest combined clarity; only PIT-clean pre-announced calendar at $0 (S-05/S-08); survivor-clean index-level; leakage minimal; spec frozen; data feasibility `[ACCEPT]`. Sole marked criticism: post-2015 pre-FOMC attenuation (`EVIDENCE = MIXED`). No `SPECIFICATION GAP`. **Strongest first-candidate posture.**
- **MEC-0005 / CAND-FREE-VOL-001.** Compares almost equally; VRP = clearly priced insurance premium; survivor-clean index-level; `[ACCEPT]` with vintage conditional. Slightly weaker only on realized-vol revisions (as-published discipline) and crash-dependence criticism. **Runner-up posture.**
- **MEC-0004 / M-T1 (no registered candidate).** Simplest executable (published index closes), survivor-clean, low cost. But governance path requires intake → proposal → spec freeze first, plus the HYP_001/HYP_002 family-adjacency acknowledgment. TSMOM replication on SPX is `[ACCEPT]` as a REPLICATION_ONLY control arm today.
- **MEC-0003 / CAND-FREE-REV-001.** Mechanically strong after the 2026 correct-measure revival, but the $0 delisted-price leg is absent (B-2), survivorship is `LIMITED`, and cost realism is the known killer. Registry already warns `REJECT`-likely at validation.
- **MEC-0009 / M-I1 (no registered candidate).** Data/PIT ideal (EDGAR), but **single-record** literature → `EVIDENCE = UNVERIFIED`; first empirical step, if any, is a REPLICATION_ONLY control arm, not a candidate validation.

**Input-set members not primary mechanisms** [VERIFIED FACT — registry]: `CAND-FREE-PEAD-001` (`[CONDITIONAL]`, SURVIVORSHIP_LIMITED), `CAND-FREE-MOM-001` (`[CONDITIONAL]`, SURVIVORSHIP_LIMITED) are in the cross-reference set; neither is improved on by this review's recommendation logic; PEAD's SUE variant remains Future-Queue (analyst consensus, B5-flagged).

---

## 17. RECOMMENDED FIRST VALIDATION CANDIDATE

> **RECOMMENDED FOR HUMAN CONSIDERATION AS FIRST EMPIRICAL-VALIDATION AUTHORIZATION: `CAND-FREE-MACRO-001` (mechanism MEC-0001 / concept M-V1).**
> This is a recommendation for **Human consideration**, not an authorization, and not a claim that the candidate "will make money". [MANDATED language]

**Why first (decision rule, NOT performance):**
- **Mechanism clarity / economic rationale:** priced regime-risk around scheduled macro announcements (Savor-Wilson); mechanism-first, pre-specified, direction deferred to empirical spec. `[SOURCE CLAIM]`
- **$0 data availability:** strongest class — pre-announced, versioned, official calendars (BLS S-05, FOMC S-08, Treasury S-06) + official index series (S-04/SPX) = `[ACCEPT]`.
- **PIT integrity:** calendar known in advance; event-time ordering trivial to enforce; no revision/lag complexity beyond archived release times. **PIT SECURE** — the strongest PIT at $0 in the set.
- **Survivorship control:** `CLEAN` (index-level) — no delisted-price dependence, no roster pinning. Solves the $-0 survivorship problem by construction.
- **Reproducibility:** high (open BLS/Fed schedules, open methodology).
- **Cost-model defensibility:** LOW–MODERATE at index level; public fee schedules; MEC-0008 cost layer available.
- **Implementation simplicity:** event-conditioned calendar split on an index series; simplest in the set.
- **Literature quality / criticism:** strong corpus; `EVIDENCE = MIXED` (post-2015 attenuation) — recorded, not hidden.
- **Governance complexity:** NOT LOWEST possible (F-1 would be lowest but is FAMILY-7-EXCLUDED and data-blocked); MACRO-001 is the **lowest-friction registered candidate** — one of only two `[ACCEPT]` candidates, spec already frozen at `HUMAN_REVIEW_REQUIRED`.
- **Leakage risk:** minimal (pre-announced times); no unintended-information spill.
- **Tie-break:** vs. VOL-001, MACRO-001 wins the PIT-integrity and leakage margins (pre-announced immutable schedule vs. as-published vintage discipline) and holds SSRN shortlist rank #1.

**Exact data path (to be executed only after Human authorization):** S-08 FOMC statement calendar (2011+; press-conference schedule 2019+) + S-05 BLS CPI/NFP schedule + S-06 Treasury (secondary) → **event-conditioned SPX/SPY daily series** (S-04 FRED official SP500 index as primary; S-10/S-18 SPY as robustness cross-check under personal-use terms), centered on the frozen spec (event-day ± 1 trading day; 1-day held window), archive-at-retrieval, manifest + data-audit + authorization note per registry STEP-8 requirements.

**Status summary for this candidate:** PIT = SECURE · survivorship = CLEAN · cost = defensible (LOW–MODERATE) · $0 verdict = `[ACCEPT]`. **Unresolved risks:** (a) post-2015 pre-FOMC attenuation (FEDS survey `[SOURCE CLAIM]`) — a persistence question, not a data blocker; (b) SPY price leg terms (personal-use) — mitigate with S-04 official index as primary; (c) dependence with future VOL-001 validation on the shared SPX leg (doctrine 8) — must be declared, not labeled independent.

**What Human must authorize:** (1) `CAND-FREE-MACRO-001` leaves `HUMAN_REVIEW_REQUIRED` into a bounded empirical-validation phase under its frozen spec; (2) the prerequisite data-audit + experiment manifest + authorization note; (3) the IS/OOS blind-window design. **What remains prohibited after any single authorization:** everything not explicitly authorized (D2, HYP_003, R1, GATE, trading, capital, paid data, spec changes).

---

## 18. RUNNER-UP

> **RUNNER-UP FOR HUMAN CONSIDERATION: `CAND-FREE-VOL-001` (mechanism MEC-0005 / concept M-V2).**

A near-tie with MACRO-001: `[ACCEPT]` data feasibility (vintage conditional), `CLEAN` survivorship, index-level, clear insurance-premium rationale (Bekaert & Hoerova), low cost. It loses the #1 slot on: (a) PIT — realized-vol construction requires as-published vintage discipline whereas MACRO's schedule is pre-announced; (b) leakage/criticism — crash- and state-dependence of the VRP-return link; (c) a slightly heavier implementation (rolling realized-vol estimation). Recommendation: **authorize MACRO-001 first; treat VOL-001 as the second authorization candidate**, and if both are eventually validated, **declare their statistical dependence** on the shared SPX leg rather than treating them as independent discoveries (doctrine 8).

---

## 19. MECHANISMS REQUIRING MORE DATA

| Mechanism | Missing element at $0 | Status | Future-queue link |
|---|---|---|---|
| MEC-0003 (M-R1) | Certified delisted-OHLCV leg for survivorship control | `SURVIVORSHIP_LIMITED`; deletion-leg coverage `[NOT SUFFICIENT AT $0]` | Future Premium Data Queue §27: (c) delisted-price history (charter B2-adjacent); exploratory-only S-19/S-23 today |
| MEC-0009 (M-I1) | Not data — **evidence**: single-record literature (`EVIDENCE = UNVERIFIED`) | Replication arm required before candidate validity is assessable | EDGAR parsing pipeline (effort, not money); source S-01 `[ACCEPT]` |
| MEC-0004 (M-T1) | Not data — **governance**: no registered candidate | Needs mechanism intake + candidate proposal + spec freeze | Data sufficient at $0; TSMOM SPX replication arm `[ACCEPT]` |
| CAND-FREE-PEAD-001 (SUE variant) | Historical analyst-consensus estimates | `[NOT SUFFICIENT AT $0]` (B5-flagged) | Future Premium Data Queue §27: (b) consensus estimates |
| MEC-0007 (F-1 lane only) | PIT membership-change intent lists (provider-furnished, not free) | `[NOT SUFFICIENT AT $0]`; `PIT UNVERIFIED` | Future Premium Data Queue §27: (a) PIT index-membership lists |

---

## 20. HUMAN GOVERNANCE DECISIONS REQUIRED

Prepared for the Human. **Nothing is selected, started, or authorized here.** [MANDATED]

1. **First-candidate disposition (OPTION A surface):** authorize `CAND-FREE-MACRO-001` to proceed from `HUMAN_REVIEW_REQUIRED` to a bounded empirical-validation phase under its frozen spec — or not.
2. **Decision surface (choose or decline; do not let the system choose):** OPTION A — authorize empirical validation of `CAND-FREE-MACRO-001` under frozen spec · OPTION B — additional data-feasibility research (e.g., SPY price-leg terms resolution, early-release-count archival protocol) · OPTION C — reject/defer MACRO-001 and take another candidate · OPTION D — mechanism intake for an unregistered concept (M-T1 / M-I1 / corrected-weekly measure) WITHOUT validation · OPTION E — STOP.
3. **Runner-up sequencing:** whether `CAND-FREE-VOL-001` becomes the second authorization candidate and under what vintage-discipline protocol.
4. **`CAND-FREE-REV-001` disposition:** given §6 spec-gap risk and `REJECT`-likely-at-validation warning — keep, reposition to M-R1 corrected measure (NEW candidate/version + reason), or defer to the B-2 queue.
5. **Replication arms:** authorize the SSRN §9 REPLICATION_ONLY control runs (TSMOM-12-1-on-SPX; VRP decomposition; macro announcement-day spread) as control arms only.
6. **Family-adjacency acknowledgment (MEC-0004):** explicit Human acknowledgment that index-level TSMOM is mechanism-fAMILY-adjacent to the terminally falsified HYP_001/HYP_002 while using no FX window and no reused evidence (dependency-free note, `research_candidates.md` §6).
7. **Future Premium Data Queue §27 confirmation:** (a) PIT index-membership lists, (b) consensus SUE estimates, (c) delisted-price history — confirm queueing; no purchase authority.
8. **F-1 lane confirmation:** F-1 remains UNCHANGED; MEC-0007 stays in the F-1 lane (§22).

---

## 21. EXPLICIT NON-DECISIONS

This review explicitly does NOT: [MANDATED]

- Decide which OPTION the Human selects on any decision surface.
- Authorize empirical validation of ANY candidate (including the recommended one).
- Create `HYP_003`, start `R1`, invoke any gate, or modify D2 / HYP_003 / R1 / GATE / TRADING / CAPITAL state.
- Create a new `CAND-*` or promote any `MEC-*` to `CAND-*`.
- Reopen or reinterpret HYP_001/HYP_002; reuse their windows or evidence.
- Modify F-1 or any registered candidate specification.
- Issue a claim of profitability, persistence, or tradeability for any mechanism — even implicitly.
- Select any paid vendor or authorize any purchase (charter §3/§27).

---

## 22. F-1 ISOLATION STATEMENT

- F-1 (`CAND-FLOW-CALENDAR-REBALANCE-001`) is **UNCHANGED** by this review and by the entire Bootstrap program (charter §2). [VERIFIED FACT]
- F-1 canonical state: universe = S&P Composite 1500; frozen filters `ADV ≥ $5M/day` (60-day pre-event), `Free Float ≥ 20%` (PIT, no look-ahead — D1-B ratified); event family = quarterly reconstitution only; horizons {1,5,10}, PRIMARY 5; direction = SHORT composite; feasibility window ~2013-12→present **accepted for feasibility only** (D1-A); `T_eff ≥ 25/leg`; `N_valid ≥ 250`. [VERIFIED FACT — ratification doc]
- `D1 = NOT READY / CONDITIONAL` — retained. Blockers carried verbatim: **B2** delisted OHLCV = `NOT SUFFICIENT AT $0`; **B5** free-float PIT = `UNVERIFIED`; B1/B3/B4/B6 = `CONDITIONAL`. No status promoted. [VERIFIED FACT]
- **MEC-0007 / family 7 (index/rebalance)** is reserved to the F-1 lane and EXCLUDED from this Bootstrap review's candidate set (charter §2 lane separation; SSRN §13). No Bootstrap-track result may claim F-1 passed D1 (charter §2). [VERIFIED FACT]
- **The recommended first candidate (MACRO-001) is unrelated to family 7** — it conditions on the macro-announcement calendar, not on index membership changes; no overlap with F-1's thesis. [MODEL INFERENCE]

---

## 23. FINAL GOVERNANCE STATE

```text
F-1       = S&P Composite 1500 (CAND-FLOW-CALENDAR-REBALANCE-001) — UNCHANGED
D1        = NOT READY / CONDITIONAL  (D1-A window accepted for feasibility only; D1-B filters retained)
D1-A      = window ~2013-12 → present (feasibility only; NOT data-construction authorization)
D1-B      = retain frozen proxy: ADV ≥ $5M/day; Free Float ≥ 20% (PIT, no look-ahead)
B2        = BLOCKED (delisted OHLCV NOT SUFFICIENT AT $0)
B5        = UNVERIFIED (free-float PIT)
D2        = LOCKED
HYP_003   = NOT AUTHORIZED
R1        = NOT AUTHORIZED
GATE      = NOT AUTHORIZED
TRADING   = LOCKED
CAPITAL   = $0.00
Free-Data Capital Bootstrap Program = ACTIVE (research program only)
Research Registry = 5 CAND-FREE-* proposals, all SPEC_FREEZING → HUMAN_REVIEW_REQUIRED; empirical validation NOT AUTHORIZED
Recommended first candidate (Human consideration only) = CAND-FREE-MACRO-001
```

### Verification Ledger (this document)
- Implementation Status: COMPLETE (documentation-only review; 24 sections; single new untracked file; `src/` untouched).
- Contract Enforcement: STRICT FAIL-CLOSED — no status promotion, no license inference, no candidate/mec promotion, no spec change, no performance claim.
- Mathematical Authority: N/A (no statistics computed; ordinal decision matrix only).
- Local Test Suite: NOT RUN (documentation-only convention).
- Remote CI Status: NOT AVAILABLE.
- Git Policy: READ-ONLY — no add/commit/push; verified HEAD = origin/main = `fff20b9`; this file remains UNTRACKED.
- Methodological Caveats: (1) decision-matrix ratings are this review's ordinal judgments grounded in §7–§14 evidence — NOT mandated numeric scores and NOT performance; (2) the 22-dimension A–V rubric is the exact rubric mandated by Human Governance on 2026-09-10; (3) the 7-question PIT audit was operationalized from the frozen PIT hard rule / charter §10 / source-registry PIT fields (documents), since the verbatim question list from the original prompt was not retained; (4) literature evidence = `[SOURCE CLAIM]` (EXTERNAL CLAIM); `EVIDENCE = MIXED`/`UNVERIFIED` never upgraded; (5) recommendation ≠ authorization; Human retains authority.

---

## 24. STOP

```text
STOP — BOOTSTRAP MECHANISM GOVERNANCE REVIEW COMPLETE.
NO EMPIRICAL VALIDATION AUTHORIZED.
F-1 UNCHANGED. D1 = NOT READY / CONDITIONAL.
NO HYP_003 / R1 / GATE / TRADING AUTHORIZATION.
RECOMMENDED FOR HUMAN CONSIDERATION (ONLY): CAND-FREE-MACRO-001 (MEC-0001 / M-V1).
DECISION SURFACE (§20) REMAINS WITH HUMAN GOVERNANCE.
```