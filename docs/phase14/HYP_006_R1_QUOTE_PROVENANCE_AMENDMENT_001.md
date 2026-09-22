# Phase 14 HYP_006 Step R1 Quote-Provenance Amendment 001

```text
[GOVERNANCE ARTIFACT: ADDITIVE R1 QUOTE-PROVENANCE AMENDMENT]
[AMENDMENT_ID: HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001]
[CANONICAL STARTING HEAD: 3234af16349483539fae67ba27e1b8f3d08dcb72]
[ORIGINAL_R1_COMMIT: 3234af16349483539fae67ba27e1b8f3d08dcb72]
[HYPOTHESIS_ID: HYP_006]
[MECHANISM_ID: MEC-0016]
[SCIENTIFIC_HYPOTHESIS_CHANGED: NO]
[M1_SAMPLE_WINDOW_CHANGED: NO]
[STRATEGY_PARAMETERS_CHANGED: NO]
[FRICTION_STACK_CHANGED: NO]
[ACCEPTANCE_GATES_CHANGED: NO]
[QUESTION_MARK_CLASSIFICATION: STRUCTURALLY_USABLE_BUT_CONDITION_PROVENANCE_UNRESOLVED]
[QUOTE_PROVENANCE_AMENDMENT: UNRESOLVED]
[HYP_006_STATUS: BLOCKED_NON_FALSIFIED_BY_EXECUTION_DATA_PROVENANCE]
[R2_READINESS: BLOCKED]
[HYPOTHESIS_FALSIFIED: NO]
[HYPOTHESIS_REJECTED: NO]
[STRATEGY_PNL_OBSERVED: NO]
[BACKTEST_STARTED: NO]
[RESUMABLE: TRUE]
[M2_ACCESS: ZERO]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.md`
- **Subject:** Additive execution-data provenance amendment for sealed hypothesis `HYP_006` (MEC-0016: SPY Noise-Area Intraday Momentum Post-2016 Free-Data Net-Profitability Replication).
- **Governing Standard:** ACASH `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed Contract, Single Canonical Authority).
- **Original R1 Inception Token:** `AUTH_INCEPTION_HYP_006_00e1d4caec97aa6c`

---

## 1. Upstream R1 Lineage & Immutability Ledger

This amendment is **strictly additive**. Original sealed R1 artifacts remain byte-for-byte unmodified and immutable:

| Original R1 Artifact | Tracked Path | Canonical SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- |
| **Original Sealed Spec (Phase 8.5)** | `docs/phase8.5/hypotheses/HYP_006.json` | `aba1dfa9bd54e42722c7cd160214632aea7eb0c5545808e8fe03208996478a30` | `VERIFIED_UNTOUCHED` |
| **Original Sealed Spec (Phase 14)** | `docs/phase14/hypotheses/HYP_006.json` | `aba1dfa9bd54e42722c7cd160214632aea7eb0c5545808e8fe03208996478a30` | `VERIFIED_UNTOUCHED` |
| **Original Preregistration Spec** | `docs/research/MEC-0016-HYP-006-strategy-preregistration.md` | `18fb66bf0ac2d41e207ec677b6773f447168e7e7a9c23747de2307f7fd5c8c0f` | `VERIFIED_UNTOUCHED` |
| **Original R1 Manifest** | `docs/phase14/manifests/manifest_r1_HYP_006.json` | `bf2c1dd43de3aa8d8fdfcb23717e9aec454dbbc1e0d4be5ef9a70b40088fbba8` | `VERIFIED_UNTOUCHED` |

- **Original R1 Registration Commit:** `3234af16349483539fae67ba27e1b8f3d08dcb72`

---

## 2. Provenance Defect Discovery & Technical Investigation

### 2.1 Issue Discovered Post-R1
In the sealed R1 specification of `HYP_006`, the quote conditions policy stated:
$$\text{acceptable\_conditions} = [``\text{R}", ``?"]$$
This classification treated `?` as an acceptable executable condition alongside `R` (Regular Market Maker Open).

However, an independent post-R1 provenance audit revealed:
1. The official Alpaca Market Data quote conditions metadata endpoint (`GET /v2/stocks/meta/conditions/quote?tape=B`) catalogs 13 official CTA Tape B condition codes (`4, A, B, C, E, F, H, L, N, O, R, U, W`). **The code `?` is NOT an official CTA condition code and does not exist in Alpaca's official condition catalog.**
2. Official Alpaca community and staff statements clarify that historical quote records displaying `?` originate from third-party historical market data files ingested by Alpaca before its own direct SIP capture infrastructure went live (< 2021). During this third-party ingestion, granular exchange quote conditions were omitted or unmapped and replaced by the single placeholder character `?`.
3. Consequently, the assertion that `?` is an executable regular quote is stronger than the provider evidence. One cannot verify from `?` alone whether a quote was regular, non-firm (`N`), slow (`A/B/H`), or closing (`C`).

### 2.2 Separation of Inquiries: Q1 vs. Q2

#### Q1: Feed Semantics (Consolidated NBBO Construction)
- **Question:** Does Alpaca guarantee that historical `feed=sip` records in `/v2/stocks/quotes` represent consolidated best bid/offer (NBBO) state irrespective of the granular condition field?
- **Finding:** **ESTABLISHED**.
  Alpaca official documentation confirms that `feed=sip` provides consolidated US exchange data, where `bp`/`ap` are the National Best Bid and Offer prices, `bs`/`as` are the aggregate round-lot sizes, and `bx`/`ax` identify the respective best bid and best ask participant exchange venues (e.g. `bx=K, ax=P`). The pricing structure reflects consolidated top-of-book market state.

#### Q2: Condition Semantics (Actionability & Firmness)
- **Question:** Does `?` contain enough information to distinguish regular actionable quotes from non-firm (`N`), slow (`A/B/H`), closing (`C`), auction (`4`), or other non-executable CTA states?
- **Finding:** **NOT ESTABLISHED**.
  `?` is an undifferentiated placeholder indicating missing condition metadata. It carries zero granular flags to verify whether the quote satisfied SEC Rule 602 firm quote obligations or was subject to a manual/slow/closing condition.

---

## 3. Reassessment of '?' Policy & Classification

Under Section 10 of the human governance mandate, the evidence must be assigned to exactly one of three deterministic categories:

- **Option A (ESTABLISHED_EXECUTABLE_INDEPENDENT_OF_CONDITION):**
  *Disqualified.* Neither Alpaca documentation nor CTA regulations certify that legacy historical records with unmapped condition flags (`?`) are guaranteed to be actionable regular quotes. Declaring them actionable by assertion violates ACASH `AGENTS.md` Principle 1 ("Zero Unverified Claims").

- **Option B (STRUCTURALLY_USABLE_BUT_CONDITION_PROVENANCE_UNRESOLVED):**
  *Selected.* The returned historical quotes are structurally consolidated NBBO records (positive prices, positive sizes, valid exchange venues, millisecond timestamps, tight $0.01–$0.02 spreads), but the inability to distinguish non-firm, slow, or auction quote conditions remains a material scientific and execution contract defect.

- **Option C (NOT_QUALIFIED_FOR_EXECUTION):**
  *Not applied as total disqualification.* The records are not fabricated or malformed; their structural prices and sizes are valid historical prints, but their execution actionability cannot be verified without independent condition provenance.

**Final Determination:**
$$\text{QUESTION\_MARK\_CLASSIFICATION} = \text{STRUCTURALLY\_USABLE\_BUT\_CONDITION\_PROVENANCE\_UNRESOLVED}$$
$$\text{QUOTE\_PROVENANCE\_AMENDMENT} = \text{UNRESOLVED}$$

---

## 4. Impact on HYP_006 Scientific Status & R2 Readiness

Under ACASH strict fail-closed governance:
1. **Scientific Hypothesis Status:**
   - `HYP_006` is formally marked:
     $$\text{HYP\_006\_STATUS} = \text{BLOCKED\_NON\_FALSIFIED\_BY\_EXECUTION\_DATA\_PROVENANCE}$$
   - `HYPOTHESIS_FALSIFIED = NO`
   - `HYPOTHESIS_REJECTED = NO`
   - `STRATEGY_PNL_OBSERVED = NO`
   - `BACKTEST_STARTED = NO`
   - `RESUMABLE = TRUE`
2. **Step R2 Dataset Construction:**
   - `R2_READINESS = BLOCKED`
   - `R2_DATASET_BUILD = NOT_STARTED`
   - No empirical strategy dataset may be constructed, no signals computed, and no P&L generated while condition provenance is unresolved.
3. **Execution Qualification Layer Update:**
   - The pre-R2 quote qualification parser (`src/acash/data/qualification/mec_0016_early_quote_contract.py`) is updated to reject `?` fail-closed (`DataContractError: UNRESOLVED_QUOTE_CONDITION_PROVENANCE`) for actual dataset execution. Only authoritatively verified conditions (`{'R'}`) remain executable.

---

## 5. Read-Only Free Alternative Provider Audit

As mandated by governance §16, a read-only survey of existing zero-cost market data alternatives was conducted to assess whether any public free provider supplies consolidated SPY tick/quote NBBO with granular CTA condition codes for `2016-01-01` through `2020-12-31`:

1. **HF Data Library (`hfdatalibrary.com`):**
   - Supplies SPY 1-minute OHLCV bars back to 2002.
   - *Limitation:* Does NOT provide tick-level NBBO bid/ask quotes or condition codes.
2. **IEX Free Feeds (TOPS/DEEP):**
   - Supplies free orderbook data for IEX-traded symbols.
   - *Limitation:* Single-venue orderbook (~2–3% market volume); strictly prohibited from substituting for consolidated SIP NBBO under SEC Reg NMS and ACASH research rules.
3. **ThetaData / FirstRate Data:**
   - Free tiers provide only aggregate daily or recent sample data. Multi-year historical tick/quote feeds require paid institutional subscriptions.
4. **Polygon / Massive US Stocks SIP:**
   - Fully qualifies for both bars and nanosecond quotes with complete CTA condition codes back to 2003-09-10.
   - *Limitation:* Commercial subscription required (Stocks Advanced, $199/month). Not zero-cost.

**Audit Finding:**
There is currently **NO known zero-cost public provider** that supplies consolidated US equity (SPY) tick-level SIP NBBO quotes with granular, actionable CTA condition codes for the 2016–2020 window. The data barrier is structural: SIP redistribution licensing fees imposed by CTA/UTP plans prevent commercial redistributors from offering tick-level NBBO with condition codes at zero cost.

---

## 6. Prohibitions & Anti-Contamination Invariants

- **No Bar-Based Execution Fallback:** Strategy execution will NOT be modified to use next-minute Open, bar Close, midpoint, or synthetic fixed spreads. The registered NBBO execution model cannot be modified without a new hypothesis.
- **No Splicing with IEX:** IEX top-of-book will NOT be substituted for SIP NBBO.
- **Zero P&L Contamination:** No backtest, signals, or performance metrics were calculated during this audit.
- **Capital & Trading Boundary:** Capital remains `$0.00`, `NO_REAL_ORDERS = true`, paper and live trading remain locked.
