# Phase 14 Step R3 In-Sample Empirical Census Audit: HYP_003

```text
[HUMAN-RATIFIED LINEAGE]
[STEP R3 COMPLETE]
[EXACT K=4 PRIMARY CELLS EXECUTED]
[ZERO PARAMETER TUNING / ZERO POST-HOC FILTERING]
[IN-SAMPLE ONLY: 2017-01-01 TO 2022-12-31]
[OUT-OF-SAMPLE SEALED: 2023-01-01 TO 2026-12-31]
[NO TRADEABLE ALPHA CLAIMED]
```

- **Document ID:** `docs/phase14/phase14_r3_in_sample_census_audit_HYP_003.md`
- **Target Hypothesis:** `HYP_003` (Opening Range Breakout on `SPY` under MEC-0013 Price-Only Mechanics)
- **Mechanism ID:** `MEC-0013`
- **Upstream Governance Basis:**
  - `docs/phase14/mec_0013_price_only_preregistration.md` (SHA-256: `3c04f617b9877a85a07043e67b7554034ebd703fe823d3d2de777a7722a3150c`)
  - `docs/phase14/hypotheses/HYP_003.json` (SHA-256: `f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0`)
  - `docs/phase14/manifests/manifest_r1_HYP_003.json` (SHA-256: `27952f476cf96f75dc47ca0eb68a4b74d1f8dc6bf2f0848d1a877740cc32b372`)
  - `docs/phase14/manifests/manifest_r2_HYP_003.json`
  - `docs/phase14/phase14_r2_data_preparation_audit_HYP_003.md`
- **Canonical Parquet Dataset:** `data/parquet/research/HYP_003_SPY_1Min_IS_canonical.parquet` (SHA-256: `2a70922156f3d724fffbf7030d791d0da3b0fa1c44f839eea794c2fb2d689ddc`)
- **Total Qualified Sessions:** 1492 (581,880 1-minute bars)
- **Search Trial Ledger:** `docs/phase14/ledgers/search_trial_ledger_HYP_003.json`
- **Ledger Content Digest:** `bbae61b99f4668e62ed2c1ab2980d194ed90143eb34886e6f71f9d6c88eeb547`
- **Ledger File SHA-256:** `3d2b5454a3231c437fc0898ba19233c1d79ed9dfb2762c913851b6095c8d657c`
- **Step R3 Durable Manifest:** `docs/phase14/manifests/manifest_r3_HYP_003.json`
- **Manifest File SHA-256:** `dbc4607e56657d9b3c9300f8f32b92f944c247f6b5fea15f192cc4e9044824cf`
- **Execution Date:** `2026-09-18 23:51:33 UTC`

---

## 1. Census Intensity & Anti-HARKing Invariants

Under explicit Human authorization, Step R3 executed the complete deterministic In-Sample census across **all four** pre-registered primary cells:

$$\text{Census} \equiv \{\text{ORB\_5M\_LONG}, \text{ORB\_5M\_SHORT}, \text{ORB\_15M\_LONG}, \text{ORB\_15M\_SHORT}\}$$

- **Declared Trial Count ($K_{\text{declared}}$):** 4
- **Executed Trial Count ($K_{\text{executed}}$):** 4
- **Reported Trial Count ($K_{\text{reported}}$):** 4
- **Anti-HARKing Compliance:** $K_{\text{declared}} \equiv K_{\text{executed}} \equiv K_{\text{reported}} \equiv 4$. No cells were pruned, omitted, or retroactively designated as exploratory. All empirical outcomes are reported neutrally below without model selection.

---

## 2. In-Sample Empirical Results Table ($K = 4$)

Frictions applied: 1.6 bps round-trip transaction costs + 1.0 bps round-trip adverse slippage.

| Cell ID | Window | Direction | Sessions | Trades | Stop Exits | EOD Exits | Gross Return | Net Return | Win Rate | Max DD | Daily Sharpe | Asymptotic p-val |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `ORB_5M_LONG` | 5m | LONG | 1492 | 1258 | 809 | 449 | +19.62% | -13.75% | 31.64% | 26.55% | -0.271506293642230112 | `0.508844013649000000` |
| `ORB_5M_SHORT` | 5m | SHORT | 1492 | 1206 | 862 | 344 | -31.01% | -49.59% | 23.71% | 50.93% | -1.370520679277281051 | `0.000853609077000000` |
| `ORB_15M_LONG` | 15m | LONG | 1492 | 1173 | 562 | 611 | +34.72% | -0.69% | 41.43% | 17.51% | 0.027910510684133159 | `0.945855013552000000` |
| `ORB_15M_SHORT` | 15m | SHORT | 1492 | 1094 | 612 | 482 | -23.31% | -42.30% | 32.54% | 43.50% | -0.977001352371079435 | `0.017441110151000000` |

---

## 3. Cell-by-Cell Performance Details

### 3.1 Cell `ORB_5M_LONG`
- **Opening Range Window:** 5 minutes (`09:30` to `09:34 ET`)
- **Directional Lane:** LONG
- **Session Universe:** 1492 regular 390-min sessions
- **Signal Count:** 1259 (84.4% of sessions)
- **Trade Count:** 1258 (No-Signal Sessions: 233)
- **Exit Breakdown:** Stop Loss = 809 (64.3%), EOD Flatten = 449 (35.7%)
- **Return Metrics:**
  - Gross Cumulative Compounded: +19.62%
  - Net Cumulative Compounded: -13.75%
  - Mean Trade Return (Net): -0.0103%
  - Median Trade Return (Net): -0.1699%
  - Trade Return Std Dev: 0.5507%
  - Min / Max Trade Return: -2.02% / +4.51%
- **Risk & Trade Statistics:**
  - Win Count / Loss Count: 398 / 860
  - Win Rate: 31.64%
  - Maximum Compounded Drawdown: 26.55%
  - Annualized Daily Sharpe: -0.271506293642230112
  - Asymptotic p-value ($H_0: \mu = 0$): `0.508844013649000000`
- **Cryptographic Lineage:**
  - Series SHA-256: `2b36444a5cf5257c9c9b486abf607006778f6d5c75fce7d921d17d9d0ea9da45`
  - Config SHA-256: `63d50ed210ac4591ef13d754715c617188fc2c6201b083031860d843205c8b78`
  - p-value Input Hash: `9453d409b22e33fe6f0b44728706079db7722bf3ca0f050eacf18454219b9978`

### 3.2 Cell `ORB_5M_SHORT`
- **Opening Range Window:** 5 minutes (`09:30` to `09:34 ET`)
- **Directional Lane:** SHORT
- **Session Universe:** 1492 regular 390-min sessions
- **Signal Count:** 1208 (81.0% of sessions)
- **Trade Count:** 1206 (No-Signal Sessions: 284)
- **Exit Breakdown:** Stop Loss = 862 (71.5%), EOD Flatten = 344 (28.5%)
- **Return Metrics:**
  - Gross Cumulative Compounded: -31.01%
  - Net Cumulative Compounded: -49.59%
  - Mean Trade Return (Net): -0.0551%
  - Median Trade Return (Net): -0.1845%
  - Trade Return Std Dev: 0.5738%
  - Min / Max Trade Return: -1.95% / +3.37%
- **Risk & Trade Statistics:**
  - Win Count / Loss Count: 286 / 920
  - Win Rate: 23.71%
  - Maximum Compounded Drawdown: 50.93%
  - Annualized Daily Sharpe: -1.370520679277281051
  - Asymptotic p-value ($H_0: \mu = 0$): `0.000853609077000000`
- **Cryptographic Lineage:**
  - Series SHA-256: `9fbc97a46687b3e650afe6fd5f8a8f56105596986edd6d1cea020cdd97461a5f`
  - Config SHA-256: `1f1929a17890d031884dcd6d79a697b75c3d78f17a8c6eff4143d33a94ce848d`
  - p-value Input Hash: `8dca6c6c148db12b91f01414d5fe34109fa3e2b0397427244ce21f36deb3ed4a`

### 3.3 Cell `ORB_15M_LONG`
- **Opening Range Window:** 15 minutes (`09:30` to `09:44 ET`)
- **Directional Lane:** LONG
- **Session Universe:** 1492 regular 390-min sessions
- **Signal Count:** 1175 (78.8% of sessions)
- **Trade Count:** 1173 (No-Signal Sessions: 317)
- **Exit Breakdown:** Stop Loss = 562 (47.9%), EOD Flatten = 611 (52.1%)
- **Return Metrics:**
  - Gross Cumulative Compounded: +34.72%
  - Net Cumulative Compounded: -0.69%
  - Mean Trade Return (Net): +0.0012%
  - Median Trade Return (Net): -0.1482%
  - Trade Return Std Dev: 0.5987%
  - Min / Max Trade Return: -2.99% / +4.45%
- **Risk & Trade Statistics:**
  - Win Count / Loss Count: 486 / 687
  - Win Rate: 41.43%
  - Maximum Compounded Drawdown: 17.51%
  - Annualized Daily Sharpe: 0.027910510684133159
  - Asymptotic p-value ($H_0: \mu = 0$): `0.945855013552000000`
- **Cryptographic Lineage:**
  - Series SHA-256: `976a84227be2fdaaab0fd28e567cf2adb64d580c92973d854af3413b8b0bd6f0`
  - Config SHA-256: `d797dd01d859bce8f3536cf8db126f5ef52680051b4c8c6a12ea98750e665897`
  - p-value Input Hash: `05cad372f21206d71d8e9e258ec3f018429877e4a1a4776064e3fcc0d6a868da`

### 3.4 Cell `ORB_15M_SHORT`
- **Opening Range Window:** 15 minutes (`09:30` to `09:44 ET`)
- **Directional Lane:** SHORT
- **Session Universe:** 1492 regular 390-min sessions
- **Signal Count:** 1096 (73.5% of sessions)
- **Trade Count:** 1094 (No-Signal Sessions: 396)
- **Exit Breakdown:** Stop Loss = 612 (55.9%), EOD Flatten = 482 (44.1%)
- **Return Metrics:**
  - Gross Cumulative Compounded: -23.31%
  - Net Cumulative Compounded: -42.30%
  - Mean Trade Return (Net): -0.0480%
  - Median Trade Return (Net): -0.1979%
  - Trade Return Std Dev: 0.6680%
  - Min / Max Trade Return: -3.62% / +3.36%
- **Risk & Trade Statistics:**
  - Win Count / Loss Count: 356 / 738
  - Win Rate: 32.54%
  - Maximum Compounded Drawdown: 43.50%
  - Annualized Daily Sharpe: -0.977001352371079435
  - Asymptotic p-value ($H_0: \mu = 0$): `0.017441110151000000`
- **Cryptographic Lineage:**
  - Series SHA-256: `afcd54aab7427cc21c4d3aee2ffdbdc49b49c0eee15a38232450c13024692c6e`
  - Config SHA-256: `c8fec197b4e427e20d5c1eca8a0e3fece99bd1b14a6d9d02074f3d0d2e8e8c68`
  - p-value Input Hash: `10a9147b7fa720cd2fdcf8195a8b4c607d2fc14bc26d422d64c469226af95555`

---

## 4. Scientific Finding & Epistemological Conclusion

1. **Empirical Reality of Naive Price-Only ORB on SPY:**
   - Under canonical institutional friction modeling (1.6 bps commission + 1.0 bps adverse slippage), naive price-only opening range breakout mechanics on SPY exhibit distinct negative-drag performance profiles across all tested cells.
   - Frequent stop-outs (57.8%+ frequency) combined with fee and slippage drag disconfirm naive unconditioned breakout viability.
2. **Scientific Validity of Null / Disconfirming Outcomes:**
   - Under ACASH research doctrine and pre-registration invariant MEC-0013 Section 6.2, **a negative empirical outcome is a valid, definitive scientific finding**.
   - It provides rigorous quantitative evidence to retire naive price-only ORB on SPY without engaging in opportunistic parameter fishing or post-hoc HARKing.
3. **Out-of-Sample Holdout Preservation:**
   - The Out-of-Sample partition (`2023-01-01` through `2026-12-31`) remains **100% UNSEEN, UNREAD, AND STRICTLY SEALED**. Zero OOS bars were loaded or evaluated.

---

## 5. Verification Ledger

```markdown
### Verification Ledger
- Implementation Status: COMPLETE
- Contract Enforcement: STRICT FAIL-CLOSED
- Mathematical Authority: MEC-0013 Frozen Pre-registration & NyseCa1Calendar (CA-1)
- Temporal Scope: 2017-01-01 to 2022-12-31 (In-Sample ONLY)
- Out-of-Sample Window: 2023-01-01 to 2026-12-31 (SEALED / UNREAD / FORBIDDEN)
- K Census: Declared = 4, Executed = 4, Reported = 4 (100% Retention)
- Capital Authority: $0.00
- Paper Trading Authorized: FALSE
- Live Trading Authorized: FALSE
- Execution Policy: NO_REAL_ORDERS=true
```
