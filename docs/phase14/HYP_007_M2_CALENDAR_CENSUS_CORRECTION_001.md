# HYP_007 M2 Calendar Census Correction 001
## Unscheduled Full Market Closure of 2025-01-09 and Fail-Closed Data Qualification

```text
[CORRECTION_ID: HYP_007_M2_CALENDAR_CENSUS_CORRECTION_001]
[CORRECTION_TYPE: DATA_QUALIFICATION_CENSUS_CORRECTION (ADDITIVE)]
[UPSTREAM_CANONICAL_HEAD: 4e4841063d0be611ca8a306baa4473e605ad97f8]
[TARGET_HYPOTHESIS_ID: HYP_007]
[TARGET_MECHANISM_ID: MEC-0017]
[HUMAN_AUTHORIZATION: AUTHORIZE_AMEND_CENSUS_TO_568_AND_FIX_NULL_BARS_CRASH]
[GOVERNANCE_FREEZE: HYP_007_POST_M1_PARTITION_AND_R4_GOVERNANCE_FREEZE_001 (IMMUTABLE)]
[M2_WINDOW: UNCHANGED 2024-05-01 THROUGH 2026-08-14]
[M2_REGULAR_SESSIONS: CORRECTED 569 -> 568]
[M2_SIMULATED_STARTING_AUM_USD: UNCHANGED 100000.00]
[R4_GATES: UNCHANGED (G1 > 0, G2 >= 0.50, G3 <= 0.35, G4 >= 0)]
[STRATEGY_EQUATIONS: UNCHANGED]
[CAPITAL_AUTHORITY: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/HYP_007_M2_CALENDAR_CENSUS_CORRECTION_001.md`
- **Governing Standard:** ACASH `AGENTS.md` (Strict Fail-Closed Contract, Single Canonical Authority, Zero Unverified Claims, No Silent Data Fabrication).

---

## 1. Executive Summary & Defect Statement

During Stage B data qualification for the frozen M2 stress window (`2024-05-01` through
`2026-08-14`), the SIP bar acquisition pipeline crashed on session **`2025-01-09`**.

Direct evidence from the Alpaca SIP feed (verified across multiple probes and multiple
`adjustment` values; all other 568 window sessions return exactly 390 1-minute bars):

```json
{"bars": null, "next_page_token": null, "symbol": "SPY"}
```

**Root cause:**
`2025-01-09` was a **full NYSE market closure** — a National Day of Mourning observed by the
NYSE and Nasdaq for President Jimmy Carter. The frozen `NyseCa1Calendar` (CA-1) maps this date
to a `REGULAR` session because the Nov-2024-published NYSE calendar artifact could not contain
an unscheduled closure announced in December 2024. Consequently:

1. `build_m2_calendar_census()` counted **569** regular sessions including the closure day,
   but the market genuinely traded **568** regular sessions in M2.
2. The acquisition code executed `payload.get("bars", [])`, which yields `None` when the SIP
   returns `"bars": null`, and then `len(None)` raised an **unclassified `TypeError`
   (NoneType has no len)** — a fail-closed contract violation instead of `DataContractError`.

---

## 2. Correction Scope (Additive, Fail-Closed)

### 2.1 Calendar Census Correction (569 -> 568)

The CA-1 calendar sovereign authority is extended additively to record the unscheduled closure,
following the exact precedent already pinned in `nyse_ca1.py` for the National Day of Mourning
for President George H.W. Bush (`2018-12-05`).

- Added to `NYSE_OFFICIAL_HOLIDAYS`:
  `date(2025, 1, 9): "National Day of Mourning for President Jimmy Carter"`
- **Net effect on frozen census data:**

| Field | Before | After |
| :--- | :---: | :---: |
| Calendar days covered (`M2_START`..`M2_END`) | 836 | 836 (UNCHANGED) |
| Regular M2 sessions | 569 | **568** |
| Early closes excluded | 6 | 6 (UNCHANGED) |
| Holidays / closures | 23 | **24** |

- **Partition boundaries UNCHANGED:** M2 = `2024-05-01`..`2026-08-14`; quarantine gap
  `[2026-08-15, 2026-09-23)`; M3 `>= 2026-09-23` LOCKED_ZERO_ACCESS.
- **No sample truncation or whitewashing:** the correction removes an erroneous non-trading day
  from the frozen census; it does NOT shrink, extend, or re-draw the M2 window, and it does not
  delete any legitimately traded session.

### 2.2 Fail-Closed Null Bars Handling

New single-authority extractor `extract_m2_bars_list(payload, session_date) ->
List[Dict[str, Any]]` in `step_r4_hyp_007.py`:

- SIP payloads with `"bars": null` or an absent `"bars"` key raise
  `DataContractError("Null bars payload ...")` — never a `TypeError`.
- Payloads with a non-list `"bars"` value raise `DataContractError("Malformed bars payload ...")`.
- Both the fresh-fetch and the checkpoint-read code paths route through this one extractor
  (single canonical authority; no dual implementations).

---

## 3. Governance Assertions (Invariants Preserved)

| Invariant | Status |
| :--- | :--- |
| Stage A freeze manifest/document | BYTE-FOR-BYTE IMMUTABLE |
| M2 window `[2024-05-01, 2026-08-14]` | UNCHANGED |
| M2 simulated AUM `$100,000.00` baseline + stress | UNCHANGED |
| Frozen strategy equations (Noise Area, VWAP/HLC3, 15d sizing, EOD flatten) | UNCHANGED |
| Frozen R4 gates (G1/G2/G3/G4 + conjunction) | UNCHANGED |
| Sealed M1 warm-up state (14 Noise-Area, 16 closes, zero M2 P&L contribution) | UNCHANGED |
| Quarantine gap access | STRICTLY ZERO_ACCESS |
| M3 access | LOCKED_ZERO_ACCESS |
| Paper / Live authority | LOCKED |
| Real capital | `$0.00` / `NO_REAL_ORDERS=true` |
| Correlation with later verdicts | No economic result is altered; census inputs are corrected before any M2 result is observed |

---

## 4. Immutability of Sealed Artifacts

The following pre-existing governance artifacts are preserved byte-for-byte (NOT modified by
this correction):

- `docs/phase14/HYP_007_POST_M1_PARTITION_AND_R4_GOVERNANCE_FREEZE_001.md`
- `docs/phase14/manifests/HYP_007_POST_M1_PARTITION_AND_R4_GOVERNANCE_FREEZE_001.json`
- `docs/research/manifests/MEC-0017-HYP-007-M2-dividend-projection-manifest.json`

## 5. Effective Authority After Correction

- `docs/phase14/HYP_007_M2_CALENDAR_CENSUS_CORRECTION_001.md` (this document)
- `docs/phase14/manifests/HYP_007_M2_CALENDAR_CENSUS_CORRECTION_001.json`
- Census authority: `NyseCa1Calendar` with the `2025-01-09` unscheduled closure pinned.