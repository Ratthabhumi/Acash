# MEC-0014A Transaction Contract Qualification Audit

```text
[GOVERNANCE ARTIFACT: DATA CONTRACT QUALIFICATION]
[GENERATED: 2026-09-19T03:54:31Z]
[BASE CANONICAL COMMIT: 793f018b0a06167599a37986c8f280459cf9f120]
[CANONICAL COMMIT: 0590301b180389a15f598903425132b9b0386897]
[STATUS: HUMAN-AUDITED / CANONICAL PROVIDER CONTRACT]
[ZERO RETURN COMPUTATION]
[ZERO OOS ACCESS]
[HYP_004: NOT CREATED]
```

- **Document ID:** `docs/research/MEC-0014-transaction-contract-audit.md`
- **Mechanism:** `MEC-0014A` — Market Intraday Momentum: Econometric Replication
- **Base Canonical Commit:** `793f018b0a06167599a37986c8f280459cf9f120` (probe generation base)
- **Canonical Commit:** `0590301b180389a15f598903425132b9b0386897` (canonical provider contract commit)
- **Generated:** 2026-09-19T03:54:31Z
- **Governing Standard:** ACASH AGENTS.md (Zero Unverified Claims; Strict Fail-Closed)
- **Manifest SHA-256:** `d1ebb09dc3103054bc5b9da09dfb4a8d4d84ff61f02f254583689cac64cd537c`

---

## 1. Scope & Execution Invariants

| Parameter | Value |
| :--- | :--- |
| Symbol | `SPY` |
| Feed | `sip` |
| Endpoint | `/v2/stocks/SPY/trades` |
| Calendar authority | `NyseCa1Calendar` regular 390-minute sessions |
| Probe dates | ['2017-06-01', '2018-06-01', '2019-06-03', '2020-06-01', '2021-06-01', '2022-06-01'] |
| IS window | `2017-01-01` — `2022-12-31` |
| OOS boundary | `2023-01-01` (STRICTLY SEALED) |
| Gao trade filter | `DAILY_SPY_TRADE_COUNT >= 500` |
| Trade ID ordering authority | `NOT_ESTABLISHED` |
| Exact transport duplicates observed | `0` |
| Execution mode | Strict zero-network replay from local cache |
| Return computed | **ZERO** |
| OOS data accessed | **ZERO** |
| HYP_004 created | **NO** |

---

## 2. Provider Mapping Proposed Classifications

| Mapping | Proposed Classification | Authority / Semantic |
| :--- | :--- | :--- |
| `ALPACA_INTRADAY_ENDPOINT_MAPPING` | `QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY` | Price-Authority Contract: $T^* = \max(t \le B)$, distinct prices in tie set $S^*$ |
| `ALPACA_DAILY_TRADE_COUNT_MAPPING` | `QUALIFIED_PROVIDER_OPERATIONALIZATION` | Raw regular-session SIP trade count compared to Gao filter $\ge 500$ |

| Parameter | Value | Description |
| :--- | :--- | :--- |
| `session_interval_predicate` | `09:30:00 <= timestamp <= 16:00:00 America/New_York` | Closed interval inclusive of scheduled 16:00:00 close boundary |
| `session_interval_classification` | `ACASH_PROVIDER_OPERATIONALIZATION_CHOICE` | Explicit operationalization choice for regular-session trades |

> [!IMPORTANT]
> **Scope Distinction: Qualified Provider Rule vs Full-Sample Coverage Census**
> The six-session probe qualifies provider mapping semantics and proves that the deterministic
> price rule functions with fail-closed behavior. It does NOT prove that all 1,498 candidate
> regular sessions in 2017–2022 will produce a deterministic price. Future dataset construction
> MUST apply this rule session-by-session and fail closed on: (1) missing pre-boundary trades,
> (2) multiple distinct prices at T*, (3) incomplete pagination, or (4) transport corruption.

> [!NOTE]
> **Operationalization Limitation (Daily Trade Count):**
> The Alpaca SIP operationalization is intended to reproduce the Gao trade-count screen
> using consolidated historical trade records, but exact database-record equivalence to
> the original historical TAQ extraction is not proven.

---

## 3. 12-Boundary Endpoint Evaluation (Price-Authority Contract)

| Session Date | Boundary | T* (America/New_York) | Exact Match | Dist to Boundary | Ties (len S*) | Distinct Prices | Selected Price | Exchanges | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `2017-06-01` | `10:00` | `2017-06-01T09:59:59.858000 EDT` | `false` | `0.142000s` | `2` | `1` | `$241.96` | `K` | `UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE` |
| `2017-06-01` | `15:30` | `2017-06-01T15:29:58.587000 EDT` | `false` | `1.413000s` | `1` | `1` | `$242.875` | `D` | `UNIQUE_BOUNDARY_PRICE` |
| `2018-06-01` | `10:00` | `2018-06-01T09:59:59.971279 EDT` | `false` | `0.028721s` | `1` | `1` | `$272.94` | `T` | `UNIQUE_BOUNDARY_PRICE` |
| `2018-06-01` | `15:30` | `2018-06-01T15:29:59.487894 EDT` | `false` | `0.512106s` | `1` | `1` | `$273.285` | `D` | `UNIQUE_BOUNDARY_PRICE` |
| `2019-06-03` | `10:00` | `2019-06-03T09:59:59.305392 EDT` | `false` | `0.694608s` | `1` | `1` | `$274.59` | `T` | `UNIQUE_BOUNDARY_PRICE` |
| `2019-06-03` | `15:30` | `2019-06-03T15:29:59.919685 EDT` | `false` | `0.080315s` | `1` | `1` | `$273.59` | `P` | `UNIQUE_BOUNDARY_PRICE` |
| `2020-06-01` | `10:00` | `2020-06-01T09:59:59.897925 EDT` | `false` | `0.102075s` | `1` | `1` | `$304.2` | `K` | `UNIQUE_BOUNDARY_PRICE` |
| `2020-06-01` | `15:30` | `2020-06-01T15:29:59.643608 EDT` | `false` | `0.356392s` | `1` | `1` | `$305.84` | `D` | `UNIQUE_BOUNDARY_PRICE` |
| `2021-06-01` | `10:00` | `2021-06-01T09:59:59.879858 EDT` | `false` | `0.120142s` | `1` | `1` | `$421.3` | `U` | `UNIQUE_BOUNDARY_PRICE` |
| `2021-06-01` | `15:30` | `2021-06-01T15:29:59.727781 EDT` | `false` | `0.272219s` | `1` | `1` | `$419.86` | `D` | `UNIQUE_BOUNDARY_PRICE` |
| `2022-06-01` | `10:00` | `2022-06-01T09:59:59.777231 EDT` | `false` | `0.222769s` | `1` | `1` | `$414.81` | `D` | `UNIQUE_BOUNDARY_PRICE` |
| `2022-06-01` | `15:30` | `2022-06-01T15:29:59.986903 EDT` | `false` | `0.013097s` | `1` | `1` | `$411.71` | `B` | `UNIQUE_BOUNDARY_PRICE` |

### Detailed Notes on Special Boundaries

- **2017-06-01 10:00 ET Reclassification:**
  - Maximal timestamp: `2017-06-01T09:59:59.858000-04:00 EDT` (0.142000s before boundary)
  - Tie-set size: 2 records
  - Exchange: `x='K'` (both trades)
  - Distinct prices: 1 (`$241.96` for both trades)
  - Trade IDs: `27997`, `27998`
  - Classification: `UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE`
  - Deterministic price authority is preserved without relying on unverified `trade_id` sequencing.

---

## 4. Session Trade Count & Census Diagnostics

| Session Date | Raw Records | Regular Session Records | Gao Filter (≥500) | Exact Transport Dups | Diagnostic Global ID Collisions | Diagnostic Ex-Scoped ID Collisions |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `2017-06-01` | 224,090 | 224,090 | **PASS** (≥500) | `0` | 2 | 0 |
| `2018-06-01` | 265,979 | 265,979 | **PASS** (≥500) | `0` | 1 | 0 |
| `2019-06-03` | 478,814 | 478,814 | **PASS** (≥500) | `0` | 1 | 0 |
| `2020-06-01` | 291,770 | 291,770 | **PASS** (≥500) | `0` | 24,604 | 2 |
| `2021-06-01` | 366,954 | 366,954 | **PASS** (≥500) | `0` | 34,372 | 1 |
| `2022-06-01` | 677,263 | 677,263 | **PASS** (≥500) | `0` | 39,333 | 4 |

### Exchange Census (Regular Session)

| Session Date | Exchange Breakdown |
| :--- | :--- |
| `2017-06-01` | B: 9,433, D: 32,428, J: 7,109, K: 21,457, M: 462, P: 61,529, T: 40,526, V: 4,077, X: 3,522, Y: 11,556, Z: 31,991 |
| `2018-06-01` | A: 549, B: 15,819, C: 4, D: 31,444, J: 9,488, K: 20,712, M: 1,224, N: 11,108, P: 50,616, T: 75,095, V: 5,832, X: 8,788, Y: 5,824, Z: 29,476 |
| `2019-06-03` | A: 1,794, B: 5,105, C: 944, D: 66,567, J: 7,583, K: 51,618, M: 1,028, N: 20,136, P: 77,868, T: 139,701, V: 15,819, X: 12,691, Y: 21,910, Z: 56,050 |
| `2020-06-01` | A: 2,028, B: 3,997, C: 1,501, D: 56,325, J: 3,735, K: 37,481, M: 245, N: 9,547, P: 53,324, T: 60,193, V: 4,206, X: 9,621, Y: 12,272, Z: 37,295 |
| `2021-06-01` | A: 2,654, B: 7,908, C: 928, D: 87,015, H: 241, J: 8,143, K: 34,349, M: 74, N: 13,468, P: 67,466, T: 60,566, U: 3,717, V: 6,226, X: 13,619, Y: 19,203, Z: 41,377 |
| `2022-06-01` | A: 3,776, B: 14,367, C: 1,532, D: 169,902, H: 6,814, J: 11,204, K: 48,767, M: 96, N: 18,889, P: 116,184, T: 155,022, U: 18,145, V: 14,366, X: 13,997, Y: 29,047, Z: 55,155 |

### Condition Census (Regular Session — Diagnostic Only)

Condition codes are purely descriptive and NOT used to exclude records from the trade count.
Odd-lot condition `'I'` is retained in the raw daily count.

| Session Date | Condition Breakdown |
| :--- | :--- |
| `2017-06-01` | ` `: 224,067, `4`: 645, `7`: 76, `B`: 606, `C`: 5, `F`: 104,353, `I`: 30,976, `N`: 18, `O`: 3, `P`: 1, `T`: 9, `V`: 71, `Z`: 2 |
| `2018-06-01` | ` `: 265,957, `4`: 1,015, `7`: 78, `B`: 599, `C`: 10, `F`: 117,116, `I`: 62,351, `N`: 12, `O`: 1, `T`: 27, `V`: 74, `Z`: 1 |
| `2019-06-03` | ` `: 478,017, `4`: 1,180, `7`: 165, `B`: 541, `C`: 787, `F`: 215,390, `I`: 122,368, `N`: 9, `O`: 1, `R`: 1, `T`: 29, `V`: 164, `Z`: 3 |
| `2020-06-01` | ` `: 291,745, `4`: 762, `7`: 320, `B`: 358, `C`: 18, `F`: 128,492, `I`: 107,044, `N`: 7, `O`: 3, `T`: 2, `V`: 304, `Z`: 57 |
| `2021-06-01` | ` `: 366,924, `4`: 621, `7`: 287, `B`: 263, `C`: 22, `F`: 153,573, `I`: 133,610, `N`: 8, `O`: 4, `P`: 1, `T`: 87, `V`: 262, `Z`: 144 |
| `2022-06-01` | ` `: 677,240, `4`: 2,186, `7`: 563, `B`: 598, `C`: 13, `F`: 316,344, `I`: 339,639, `N`: 10, `O`: 4, `P`: 1, `Q`: 2, `T`: 133, `V`: 487, `Z`: 19 |

---

## 5. Raw Evidence Provenance (Disk Hashes)

All hashes computed directly from persisted disk files read back from disk.

| File | SHA-256 |
| :--- | :--- |
| `trades_SPY_2017-06-01_p1.json` | `b661f7bac26930cd9de851e933eec1974650a2eaeec56a80841d047b16198879` |
| `trades_SPY_2017-06-01_p10.json` | `61d4646392cff6d8746e7bdf975c25b1e0bd3ddb63ef06770adfebc146d445f1` |
| `trades_SPY_2017-06-01_p11.json` | `546cbde0d9c9f0de3e7aef824f19ac131cf4ca68873d9839919accc8119f7d41` |
| `trades_SPY_2017-06-01_p12.json` | `dd9fd10d860befd0d24c1827fe7e64067f0e0c02bb848ee0f912c99c470e0dec` |
| `trades_SPY_2017-06-01_p13.json` | `9d71d8a317d872ec15999d2ab07babaad41aaf6f5ee612d2e5d0d88bcf234824` |
| `trades_SPY_2017-06-01_p14.json` | `d00482bfbfe3b679fdb19f414e6af6ca1c19d194384ad750cb38925dfa0e9397` |
| `trades_SPY_2017-06-01_p15.json` | `93b6df77a7aedbeb47d6dcf6585cd29c77033d968efaadd434e88b0e7ea47073` |
| `trades_SPY_2017-06-01_p16.json` | `4578f06b32baf4fcc61b572dddd97412ea4a9a12f8d86a81dbf3b1955692c9f1` |
| `trades_SPY_2017-06-01_p17.json` | `9640ca49c4542a1d3b0e1a4009261c113cb5d89dfa8f84bd5337df4bd06cd294` |
| `trades_SPY_2017-06-01_p18.json` | `4e3976c662a815a4be86716d01bd6f71644791a3368cfb8e72a137747c90b5a8` |
| `trades_SPY_2017-06-01_p19.json` | `1df8efd823084622681bbfd805bca3b50fc6f5b04fb721592588bd9ce62df015` |
| `trades_SPY_2017-06-01_p2.json` | `99c02cc622a4ca4d61d2d06697ef02b853131c42d60b9421a7555fe215c02859` |
| `trades_SPY_2017-06-01_p20.json` | `44e069d479afb280086d8d3067c6bdf307177d9a65f773c4c10f2e2659d143e4` |
| `trades_SPY_2017-06-01_p21.json` | `2ce885279fc75f3b37cf15383febe61befd4bb7b8199a16bc0a9a58c125b5cea` |
| `trades_SPY_2017-06-01_p22.json` | `f7ff2c23e74e6c53a4ffcda36293cfc42ff905c70a8da6cf3a5dc7e14a09b02d` |
| `trades_SPY_2017-06-01_p23.json` | `3aa7c06b89eb318147e19d18bde8fd03fc9701d03d4a376234d3a236f075091a` |
| `trades_SPY_2017-06-01_p3.json` | `2d0504edb56a5b33d98a98827ec2111d2cab8716f4b2c79676f6e728675dd92a` |
| `trades_SPY_2017-06-01_p4.json` | `073b85d9fd18a5772f3bedfa6f9dd182b3c57720d0bbe04dc6c7699619b87a17` |
| `trades_SPY_2017-06-01_p5.json` | `7e63b03be2002f9b9ce61f4db3bb7eacfd6af5c9e83df5d03c71d1ec28ddc0b9` |
| `trades_SPY_2017-06-01_p6.json` | `67e6f7984aac48855256c11eec252112a1c55c2b15b4803e1a26636c11013f32` |
| `trades_SPY_2017-06-01_p7.json` | `b952173c0475680797c23cfb68b484ad8c7b24608efce175578f7f523bc9723f` |
| `trades_SPY_2017-06-01_p8.json` | `3befd9bf8f92e6cfa12b655f54dac75f4cc4d9b1dd5efa8e92e28472a76b5e7c` |
| `trades_SPY_2017-06-01_p9.json` | `85026f2fdd6f9142741c1bd975407066495019eef01615fb3a9059b2169e977c` |
| `trades_SPY_2018-06-01_p1.json` | `ae59e2f7198762b358a761a23cc99d39d648de3197e7e3676caacfa1da1fdc11` |
| `trades_SPY_2018-06-01_p10.json` | `5fb863b04f12185f5b8b9d93675331b289946bbef8bb4aa2a16ed4323be1e785` |
| `trades_SPY_2018-06-01_p11.json` | `e0d6cf6b5700254d5d2a2b10ce505f1969ff1a87941b3aecc5f9d675d00ab112` |
| `trades_SPY_2018-06-01_p12.json` | `d4ea3856f547626dd65bdf7ed21725037a3efac5d60af1acc0dcf475bfec90af` |
| `trades_SPY_2018-06-01_p13.json` | `1ca52cbd6536774b8e409a73e2dcad60b3ebb7807cd74a59d1c5c39a951c7f5c` |
| `trades_SPY_2018-06-01_p14.json` | `8a2ca3b8fd8a19a40dcc14ece6aa4a751930e07b50e2c82f316d647e8b8c3c4c` |
| `trades_SPY_2018-06-01_p15.json` | `c1b33efb5b02ab5f8126dd2f47fd23c244105649e94b1562107876439ab16585` |
| `trades_SPY_2018-06-01_p16.json` | `ed0c6b6e1143a351a3f852c82dd5d16d30f2f16d19c93d05d573d336ca7e1c38` |
| `trades_SPY_2018-06-01_p17.json` | `be22d33d0ad07386f96d87fca88097b5eca866ea927676af2e39d0fca7f15827` |
| `trades_SPY_2018-06-01_p18.json` | `f3ce10e6165038a599b8ecc182e1b0f410b54f269e2a062d2a7f3d470e260466` |
| `trades_SPY_2018-06-01_p19.json` | `ef67baa0b235eae766bf651b846f642ca6b9213dea44a5622dbac0a156d5c6b1` |
| `trades_SPY_2018-06-01_p2.json` | `a8d0e283be98cb24c4442d483e4457ea42ea519c2aec42e256d16c436f061563` |
| `trades_SPY_2018-06-01_p20.json` | `4fd43a1c7b3dc9724ee6b5507d2754ba3689ec5b27dfe49b8e5780f6c871b629` |
| `trades_SPY_2018-06-01_p21.json` | `177c8f4d77329c2eea06ce9e10ff734b6fd0ae61d9911c10722b307621f7b139` |
| `trades_SPY_2018-06-01_p22.json` | `77ed29694b2020c0e9013b89b6ecba109cb94e5b0fcff96e5797cae697d42099` |
| `trades_SPY_2018-06-01_p23.json` | `1a46c5f5c42609b150624cc5552a9415e48dc3d4c7dc3892b2711199653a30a1` |
| `trades_SPY_2018-06-01_p24.json` | `bc2d817948abd53e38c9a19df01d98ab80ed144e22c875e36075d472cd236aab` |
| `trades_SPY_2018-06-01_p25.json` | `d05fc89db2e536df9dd21a856834954f7779cf5c7523a8503813f726d3083cdf` |
| `trades_SPY_2018-06-01_p26.json` | `5003d7639bbe62cc70495db390c9ff8122fd304ed3aaa8b8d46e11f30e86e306` |
| `trades_SPY_2018-06-01_p27.json` | `a1a9a035b19ebc8f58e4f8b13631f73606448bfe6b347d8e9b49a8194ec80f38` |
| `trades_SPY_2018-06-01_p3.json` | `a8545402fe63903ea92291e18c8e35fa2795ef8ef6a9a00892c8dbc2a66a76a6` |
| `trades_SPY_2018-06-01_p4.json` | `5a76b8d870dd46d0677d5b63f53705be819a77a06038cb5a5a0ee56386a07560` |
| `trades_SPY_2018-06-01_p5.json` | `1ee604064760475bb0b81189535e7bad1591253d4c3492a12ac85cabf547809c` |
| `trades_SPY_2018-06-01_p6.json` | `41aa67d39a87716c72e3170cd0cff3da406de3e8eeec99b9d519ee4adb8f89e1` |
| `trades_SPY_2018-06-01_p7.json` | `26ff32a10670e352c9bd151eddf0c2e0a0a1fa6a9ec479e8501a7edfbceb5330` |
| `trades_SPY_2018-06-01_p8.json` | `91a001ef0a14f7b4f227d18d2b0bf40e16bed12ebe425c74132cad885f9b7664` |
| `trades_SPY_2018-06-01_p9.json` | `312f736c40edfd6ac3ef85d524737d5d09f0078c0de3ad0c6c4478363e940cbe` |
| `trades_SPY_2019-06-03_p1.json` | `6ee1e7440d4f47914397ffe40b99368a3e85c98d489bc1ce5545c49d2ab18bf3` |
| `trades_SPY_2019-06-03_p10.json` | `f65b1fb0fbe0ef0c2b1aaa0d4fcf4ee4ace254c620807d95e17c68c8563b15d9` |
| `trades_SPY_2019-06-03_p11.json` | `bf5f9b115b60ee4973c1c40c6f4e4ad25a94efb7e14550460aa5e27e0307a453` |
| `trades_SPY_2019-06-03_p12.json` | `b35b60d53db60bea2e2ce27bf1bd0b47cf672eba63a17a034afcaed332a775c6` |
| `trades_SPY_2019-06-03_p13.json` | `047f2d38474d4910f73cd835e969d8da5f36223f128545f9894a064e693f347e` |
| `trades_SPY_2019-06-03_p14.json` | `67747879896b958f01b16652093a25ffe017dfd9d956dcbb4eae8ce1c0600d0f` |
| `trades_SPY_2019-06-03_p15.json` | `5d9d5b6de3e6ce90fcaadd46df4007bbf150c0625d568c0c426f66daf09bfe15` |
| `trades_SPY_2019-06-03_p16.json` | `4e878667547ac91fd063acd2ba746f08b23acca76252c9e791e0af2a6b584456` |
| `trades_SPY_2019-06-03_p17.json` | `c102d5ab7b108079962ecc764ab1bb5d42e2a687de2c145c326bfac5ea0bb7fa` |
| `trades_SPY_2019-06-03_p18.json` | `5afaed700e30c28a7e3398491e9fd0a5eee722665e77499cbc4b0380c104b890` |
| `trades_SPY_2019-06-03_p19.json` | `c1dd29509c1b631515a36bff1bf768b836c72680fe3f6e95c50bc416eab0eede` |
| `trades_SPY_2019-06-03_p2.json` | `ae7f604aa115e338c38314fd49a4d8f876a622b01988db6fdc33a13231a31115` |
| `trades_SPY_2019-06-03_p20.json` | `f3203d9618e42747bcddb27fc1d78429965bca2cc66cd9b187df37eb16ccc772` |
| `trades_SPY_2019-06-03_p21.json` | `2036b533c16aac0e580816f4c65f6a3d7a2eae93876444205c2f4a56b80e272b` |
| `trades_SPY_2019-06-03_p22.json` | `afb56da2445f26a616be933c03f04737f3abc8fbf7a247a561a4fd7cce5b4742` |
| `trades_SPY_2019-06-03_p23.json` | `5bb40081e6e5e9fc3783a04d9e4fd77fbb20b4004bbbad7d9c63f0c02d0dc27b` |
| `trades_SPY_2019-06-03_p24.json` | `3b601be757e9d7c1c4249cb16cd8265e0f0d644b9975184dd32468fa762d2bcf` |
| `trades_SPY_2019-06-03_p25.json` | `87f3f776ad693737fa1bbab4cc1b93b2ea35e19d9c418568be0a051b91e27b65` |
| `trades_SPY_2019-06-03_p26.json` | `df6b15b9d7e8d67c8fbaac9d142e11c511ee265440159c1f56016ed025b09534` |
| `trades_SPY_2019-06-03_p27.json` | `87b3a88996c23a0d8fb8d9296e84e3b2714efb5fc5d8ff255075621e226821ca` |
| `trades_SPY_2019-06-03_p28.json` | `a4e7c717f84e4d8f0bd6880d7d81ea87e80150d09affc5f31d88e74cb0df064f` |
| `trades_SPY_2019-06-03_p29.json` | `5d6ac2b622c7f3e6149c84863f8bf2ff912086cbee2549cfb02dcd6a8d8f3545` |
| `trades_SPY_2019-06-03_p3.json` | `6f44c519c7dc1aa91aaec4f5812c98eaf8e1d0123a2ec928729422063f995cb9` |
| `trades_SPY_2019-06-03_p30.json` | `57aa7f1fb5fde58e76f77b8426e442af670f3a2d29d3821dc601f8b6677357f3` |
| `trades_SPY_2019-06-03_p31.json` | `9bddfa7b2d43bb6dfc24b8643554758450c7d2ff619d9e00569d7348e97134be` |
| `trades_SPY_2019-06-03_p32.json` | `954bd5d5b5e514308d0391140f1f992feeaf363c6d033460741ec32747701507` |
| `trades_SPY_2019-06-03_p33.json` | `6bbcf4c644487eb43904d69998ad320885c6bb979bc3d33cd77ec2a053f84f54` |
| `trades_SPY_2019-06-03_p34.json` | `52af778d9f2df53f89d17ce30b6dc8f456954cdabcfc0fc4dd1aef9888be485a` |
| `trades_SPY_2019-06-03_p35.json` | `a0f6b6fc460aeac8efbd8aa89500f36818d1a1cc75e0c1b220396e9e29fb828e` |
| `trades_SPY_2019-06-03_p36.json` | `4c141c931806d4c49cd18cf81a30417ba4aa06c468317b0c979fc299a7500140` |
| `trades_SPY_2019-06-03_p37.json` | `cf9de7da6d123728284646dc9ea81a04ea945532408352b53c1bc62eb3beb8de` |
| `trades_SPY_2019-06-03_p38.json` | `6efb54e202cdfc7c20890c3973525d1c54a370b1b6712b979414df75bb2420ab` |
| `trades_SPY_2019-06-03_p39.json` | `e4876b13b90930f7d78293d5c6988d5aa9f57535a23cced5c8a0f8b461385e9f` |
| `trades_SPY_2019-06-03_p4.json` | `afad7fb3e4fe35214a6cb7fff2bc2226b28cc1c2aae4db1bc98c8e3d0b2e2e48` |
| `trades_SPY_2019-06-03_p40.json` | `d6e208c225115fc647a62b5dbe80d3037eb55416c4b8b7b9d677dece600f39a1` |
| `trades_SPY_2019-06-03_p41.json` | `93c91d2fc88cda98b6c6ee7d76fdb0d0304e3bb2225b36fafc6117d00d275bf1` |
| `trades_SPY_2019-06-03_p42.json` | `07f653abe641bf7054ba429184f0911d47e3cca4711e47c30c3c3f5b78c75279` |
| `trades_SPY_2019-06-03_p43.json` | `24123f2d07dab1179c72496f01270d383b811a8ab1bdb8a1b0a4c3bfb9d7e1b0` |
| `trades_SPY_2019-06-03_p44.json` | `cf1e834e74dd8613e50b9f5b86a24ec97c41e5634c351e5084a639d171609cdc` |
| `trades_SPY_2019-06-03_p45.json` | `b9259265cbd0e47f3d8c4e472307326e5b23c3bb77c4090678550c3a2547d2a0` |
| `trades_SPY_2019-06-03_p46.json` | `286133a664c531f5ac2cba6b0ec485dfca1d24808bc7b783e332482d9c38b1ca` |
| `trades_SPY_2019-06-03_p47.json` | `8ab6b6b3a588e8c229078371e4be5fa90035fe2f3f88989549c09a33417f4645` |
| `trades_SPY_2019-06-03_p48.json` | `1c1d773f2b96db029fa48d335c834a2b3f91c9e6367c0e909521e58eb2cec95a` |
| `trades_SPY_2019-06-03_p5.json` | `6f18b385a9e0a76d8459d132409732b5eaec051be5b969b1e5358c9e71655556` |
| `trades_SPY_2019-06-03_p6.json` | `44c428b5903185a23fc62739bef3b4b9953d011638c98acdc5b4093843b75f58` |
| `trades_SPY_2019-06-03_p7.json` | `af818c3006320f09bc74af96ba0938975d876d853cdb1cc558d535ce0b10e34d` |
| `trades_SPY_2019-06-03_p8.json` | `3de686fad2e3314ec31e459e5aaf730649a07261f13d1ad536ae5cc7223e6d00` |
| `trades_SPY_2019-06-03_p9.json` | `b3d0c61aab6531bcda169f0382ea777d8470c445df284f0d32fb45de15bc6ce2` |
| `trades_SPY_2020-06-01_p1.json` | `6a39f94c03a0d4bdc85969c29f23a33c4776e6ee43ad16987aa6c0d34571714f` |
| `trades_SPY_2020-06-01_p10.json` | `633db4d7a6b624e0687f34d91205f9992881f875737a7e3487331d0b9703c2e5` |
| `trades_SPY_2020-06-01_p11.json` | `ee4b85b0745704893b2370b52c5422255843b60e1ace1c439f8b758e3c9e00d9` |
| `trades_SPY_2020-06-01_p12.json` | `89eabc7cd5d5bb05fe46b42afc3d06594c41983ff609ce1cb59e59d93d219e38` |
| `trades_SPY_2020-06-01_p13.json` | `a8ac8468b5042923ded6b6eba2416bc97f1597a86bfcf2d8e85c275790e29b80` |
| `trades_SPY_2020-06-01_p14.json` | `5270f15fb97f188804ccc107b560c0b653f78916c69629298cc2a429ab8abc8e` |
| `trades_SPY_2020-06-01_p15.json` | `0f83f926b594c77e03d1f1abd9a2d3e29bf986168fbaea09e9c50dc54256e6b5` |
| `trades_SPY_2020-06-01_p16.json` | `513c1e69106592fddc64a509cb09121e0a194896c9ca1d9873d45d6622391526` |
| `trades_SPY_2020-06-01_p17.json` | `a7d738c0ef33fa7dec3b9a8ce7e6cfb9ff7f0aa013b3536f5f204ec5d509a83c` |
| `trades_SPY_2020-06-01_p18.json` | `192be9590b9d3800ec0ff6ac7fc0fcdd708988eaab18a8ece17abda19b837e33` |
| `trades_SPY_2020-06-01_p19.json` | `a6dea281936bf0c55a0850698c35364528bcc3d26ff519fa9cb7f0d2beb920b0` |
| `trades_SPY_2020-06-01_p2.json` | `899de7ff857118e674b6d5a91e1b7a376c27deb434cbea6b0c95a83bd4893d66` |
| `trades_SPY_2020-06-01_p20.json` | `999a7811b7eeadbca5400b6321f1600fa0076fbd50d21c6910b5245bc6e74ebf` |
| `trades_SPY_2020-06-01_p21.json` | `8fadcd7aeaa7f27ffd9643db8fc441313c3c6d5d39bac3c90e36f93a11ed19d9` |
| `trades_SPY_2020-06-01_p22.json` | `4d14bfe2af22373520109dcefe6710bd0714610e2cf9f76f2acb149e89c9d437` |
| `trades_SPY_2020-06-01_p23.json` | `ba094c9df0d9954418903e6fa34132e55b427bdcd979b678166cf9dd7eba389a` |
| `trades_SPY_2020-06-01_p24.json` | `435950c73a21c63bf9c6da24bb177b179c49a31fe71dff5abe419da496adb5ec` |
| `trades_SPY_2020-06-01_p25.json` | `4e755eae406698ba039b4f83e6a04abcf93531f08e4684cc1b86db1a829a22e5` |
| `trades_SPY_2020-06-01_p26.json` | `ba8a196d2e7c4111dfe8e962df6c3de9ad69d3508421192f7630b9d52874a7d1` |
| `trades_SPY_2020-06-01_p27.json` | `a98839fb231194d8089f2214b8c4ccbda2924e88f85f17bdc53ed9aeabf75c99` |
| `trades_SPY_2020-06-01_p28.json` | `2f928bc08f37ebc8caa1e971dac86aa9627a3e6eb484b2219d57e7b74bd987ab` |
| `trades_SPY_2020-06-01_p29.json` | `073cfc701a591c87aff9fe59e7dc47f1db525381be45cd67bf45ef0329e57e96` |
| `trades_SPY_2020-06-01_p3.json` | `9969ab9f236c6a1b75c0378b9183d706f345fa39cb5c1595cb8a8a6991578c52` |
| `trades_SPY_2020-06-01_p30.json` | `003b8afd2d30a6c59aef78c3cb2ee115b141c1ce26ac114615fd6c5e0de84c20` |
| `trades_SPY_2020-06-01_p4.json` | `6b0e61d3d361a1d9950f071a6a13e00bd621a0f4f01eea2b86ccf11cd2cb627a` |
| `trades_SPY_2020-06-01_p5.json` | `f03c822263d72675c981db587000de91f859800013e52fc36c4120726aad6c84` |
| `trades_SPY_2020-06-01_p6.json` | `bdea4747126f522ac4b8572b154d2c6b0197b13fd3b1a7c8f3c41e9fdee5dc67` |
| `trades_SPY_2020-06-01_p7.json` | `3af9e4bb75189891fc840f3aa1d86d5c09cb67672edcd7a97105684e361eeeb1` |
| `trades_SPY_2020-06-01_p8.json` | `402f9004c78a8f56c9b889f880fa3b35740e6b93a49c2e93ce25b9f2153e1853` |
| `trades_SPY_2020-06-01_p9.json` | `4b52cbc66fb80773b4eba5c2b98fa3e8f08c4fb460008fb609f2da35780f928f` |
| `trades_SPY_2021-06-01_p1.json` | `6816fd3002a407a03be8f9d3f6ef670dc68c069b96003b545b50955191c3d81a` |
| `trades_SPY_2021-06-01_p10.json` | `54d87c784dd20c470365ab000a25e2353e9ecf87649115bfc52529a5638207a8` |
| `trades_SPY_2021-06-01_p11.json` | `f90f3bb082050988a45ce94755cd1b982d90dd3d7310ae24f0d2a5556bb2aa2c` |
| `trades_SPY_2021-06-01_p12.json` | `d0eed8a60ce6db391af03075a95f66df88e0a55b7e1d7115880c4d3c703f0668` |
| `trades_SPY_2021-06-01_p13.json` | `8c9e53dbd5413152e486dcd17ffa9390c8ce9a925f4457b161d7927ecee3e7fe` |
| `trades_SPY_2021-06-01_p14.json` | `6ff58041b9fbcd3cb71df708019d653a166ad80e6ec0d9cdc4d779733c7915d8` |
| `trades_SPY_2021-06-01_p15.json` | `3c39623a0bfba86842803a840c078df448287373a6c6065d2ae4390e7259a05c` |
| `trades_SPY_2021-06-01_p16.json` | `1966c146b765330ed256a659b0e94f224cf03c2deb45033754bba45c8f420eb8` |
| `trades_SPY_2021-06-01_p17.json` | `84d46b42c52dc97d94487236a8a90efce91f71c3a53b20413d35038640dc0765` |
| `trades_SPY_2021-06-01_p18.json` | `d4adbdd8b3a73308a5f6e1b5e581292fbc9eabb5a6595ad6e6b610a58684ce1e` |
| `trades_SPY_2021-06-01_p19.json` | `02ae8db2f0964c5b0b99384f242e08494a184e4b88cf6974b508bb0f0da81853` |
| `trades_SPY_2021-06-01_p2.json` | `1430cf086fda312075a2ed2131463fd7803135c489280dad6ea01af52e948534` |
| `trades_SPY_2021-06-01_p20.json` | `5c943544d84b0906594954aa8f63940e8272c279f4260ff622685cf61d0ae844` |
| `trades_SPY_2021-06-01_p21.json` | `2bf632b14970d51e98338d5eaf9938b49b8e6f608e289d5313fd94d88d9aa4df` |
| `trades_SPY_2021-06-01_p22.json` | `193721c43f6be7767ba237fef8fe78e9ed94e12f2781b778e6e17574d4cef8fa` |
| `trades_SPY_2021-06-01_p23.json` | `b60e9b4f7d011e23de4d191be78fa28500add505ed759b44d18879130ef51d97` |
| `trades_SPY_2021-06-01_p24.json` | `45e5483e0a5ef7901cc108b7b24c430dabaa1db8c7a3165073d8aca0a164c6bc` |
| `trades_SPY_2021-06-01_p25.json` | `1ae6462d344eb83d33181b528f35f51775d71354e1a0049ea5cb89f547648875` |
| `trades_SPY_2021-06-01_p26.json` | `81420c18a95833911f6a8d7179729163de2eef8f7dac22752efc394ff05b801f` |
| `trades_SPY_2021-06-01_p27.json` | `154c4dbce8ceec5cff7b2e5decacc1b4b182d3c3b93a4a96ea2f7a44a1e8ea03` |
| `trades_SPY_2021-06-01_p28.json` | `c196f3e948972762e99c3b5a2fadb7959ee3acffc94ac0ccc501c60e5ba10aaf` |
| `trades_SPY_2021-06-01_p29.json` | `691d3cdd0fc46b54063592c962e39611113fde4c117947c4050b7281d205fef5` |
| `trades_SPY_2021-06-01_p3.json` | `cb43ad12c64f97f692c760cbb6756b30b69649c4c97f12af75c9fc75089759ee` |
| `trades_SPY_2021-06-01_p30.json` | `7104958f8452f89df7c443222c611e0f67e53e6bac6bb4d596a13e1c5dc3695e` |
| `trades_SPY_2021-06-01_p31.json` | `e7a985c0f3c4211c5bb57ad3bad16af4cb6a3c43b2741fe6b681c679876de1b6` |
| `trades_SPY_2021-06-01_p32.json` | `e4abfc72d76e301cb4b37773774a78e900d980b213b5e5378af96d5aa2f60a28` |
| `trades_SPY_2021-06-01_p33.json` | `52ff37761dc674d9c3b42ea30b95dd5fbc4635f1026b8ea9d0507d0ed5273574` |
| `trades_SPY_2021-06-01_p34.json` | `bacfcf16ffbc926ef9b007e3bc56e14167127a4df041abe82985f69c28cac3ed` |
| `trades_SPY_2021-06-01_p35.json` | `8cb598cec73a0ff94f154f9328f5d1564de33bd1e09c592615c82b2851cb5420` |
| `trades_SPY_2021-06-01_p36.json` | `c09b2359b18e8e130e6d479d3195a78f32f081e02b07874fc44d856089f4de2b` |
| `trades_SPY_2021-06-01_p37.json` | `6641514273fb1b64639f8beca1c5ef88f9b8d5c1c7003be6b912b4e6b12bba15` |
| `trades_SPY_2021-06-01_p4.json` | `82ca9bdcb62c20823d1c608c8c2d09e678cb68f079fa225f593f7f95ca6ebcdb` |
| `trades_SPY_2021-06-01_p5.json` | `66f22f9cec6bbfe31ef59dc0b914e2a38fe771f271f87c1c033d230959cdada0` |
| `trades_SPY_2021-06-01_p6.json` | `f3e734c280d144a2530d579486716781cca75f2af48b32b68f3f1c35eba5e519` |
| `trades_SPY_2021-06-01_p7.json` | `2be02cd0cd366cd485b00e8561a53c30d8fb34387724fe11775c708ba4ab1102` |
| `trades_SPY_2021-06-01_p8.json` | `4f45cf6da47c2f28029510789cd76c8d9f62e3ae3ecd8db541f1c0fba0cc2c0f` |
| `trades_SPY_2021-06-01_p9.json` | `cba844bea41f829bf675bb940068fe3691e8775295f1c62aa865caf84eb1e0a0` |
| `trades_SPY_2022-06-01_p1.json` | `3ba31e26503e072776f9b3a77111761550cceafc3120d78c53e6b70d1bfebfd7` |
| `trades_SPY_2022-06-01_p10.json` | `b6739d90b0042fe153a039b9b160a6924a4f6791e9c6f1289c80f5b255643834` |
| `trades_SPY_2022-06-01_p11.json` | `1c6d690c4b5816a564cd0389a05b9da75c5decac8e2dd9d6d0f51318beb24827` |
| `trades_SPY_2022-06-01_p12.json` | `ec86d2711aa2477e60375a81976bfc84cc4c315932ab81b6f3f6342a7d439f63` |
| `trades_SPY_2022-06-01_p13.json` | `7086d86ad5ad0dc9e13955441be4d408262ea02a8b8d4c89e34d391d359875a9` |
| `trades_SPY_2022-06-01_p14.json` | `33eb64d00c6f2b24689b0ade3688f1102cb4b2392082908ff024dad64f5fcb16` |
| `trades_SPY_2022-06-01_p15.json` | `a0ade9d4e17cd4b93d26a7ee261212fbec0b4b2271cf13e06d062c40ab3f09ad` |
| `trades_SPY_2022-06-01_p16.json` | `878d42da6e2ea7521a1d2ef68121680ae77aab2ab4204971a5181516487869e5` |
| `trades_SPY_2022-06-01_p17.json` | `09ad2674e3ce690dc4a66865d8f506b0c4c74e5224ea7745e27c499452c224ca` |
| `trades_SPY_2022-06-01_p18.json` | `b9f9c5dd527cdddd2e568c91a0f682f9ce5450bcd3a06fc13ac841b076cbacd1` |
| `trades_SPY_2022-06-01_p19.json` | `3bf2341157f929f8713cda9634d4fb6ac98bcf6e3d374b1582e1563f94bd668f` |
| `trades_SPY_2022-06-01_p2.json` | `b6ee725c3bdfe8564401fc0c2b5d7ec5249f0dc0ee5deba2ec652450f0bae962` |
| `trades_SPY_2022-06-01_p20.json` | `ebb27691b53331b21c22dc87a11609525929b8be9541e6bfdb16f870091f2768` |
| `trades_SPY_2022-06-01_p21.json` | `261439f64cf3e3b47febb530ccb5250caa7e62edcf0474ab3269c86c9e6f1588` |
| `trades_SPY_2022-06-01_p22.json` | `071439b6319f6610befe70564774bfb96fa7f723c7d5e49588f3df3077b1395c` |
| `trades_SPY_2022-06-01_p23.json` | `1595906858e6089e7cfceec5e1e920ef0cba814cf534f3e960743f4997c0b348` |
| `trades_SPY_2022-06-01_p24.json` | `9ecccaf82c9133e3ded69430dff670c27775bd2fbd57129be861914401c42735` |
| `trades_SPY_2022-06-01_p25.json` | `a4e63b8dfbc3c9c8fdf25d4d5d4ab659d73d6c6df4e9725acd2bb4ff710ae687` |
| `trades_SPY_2022-06-01_p26.json` | `71667ab29dd2935cf1229cc264703c5377cabb62c84a67552d87f67735afbd7a` |
| `trades_SPY_2022-06-01_p27.json` | `eb13c9849d5aa65d0fb5ce2a7797c323f75ebab7add51cce01378e18189ca48d` |
| `trades_SPY_2022-06-01_p28.json` | `5b1c5df83b5c4b90927159df58b49efefcc1b1c1bdd71fd567e334fc54d6b799` |
| `trades_SPY_2022-06-01_p29.json` | `4e9008c349690b6bf25885d260606e4bd267b5749aebefed0ebda266768acfc1` |
| `trades_SPY_2022-06-01_p3.json` | `344f3dcaf998c6dd85ac5b395ab47ebba63d08d52aa988f816da6246ff67f26a` |
| `trades_SPY_2022-06-01_p30.json` | `f81473b480599c792d84159a01817c6af88133f9135c4de07818241101747f59` |
| `trades_SPY_2022-06-01_p31.json` | `abbd86b039443b635f2e6249654c438eff001d4f26b8fddc84090412d778a12e` |
| `trades_SPY_2022-06-01_p32.json` | `789235d0f666f74550d2ec6cfd4571258a5938d1f90f699b5c80cd70efff33bc` |
| `trades_SPY_2022-06-01_p33.json` | `e5f93cd8b41303d94dcbb012546cc3441c23d719801f36f70dddb23d19e89bf4` |
| `trades_SPY_2022-06-01_p34.json` | `6d932d0b39ac352be3d92fe19299ba591e8ffccbf7f29f04d85fc5b8bb956404` |
| `trades_SPY_2022-06-01_p35.json` | `0320adb1d98722a0821fc26302f14650e2137a69a138f551f937d9e404b09d0a` |
| `trades_SPY_2022-06-01_p36.json` | `226a8618ab18320481894fa27975b7e6b344da18debf9892401ee9b5dd4b394c` |
| `trades_SPY_2022-06-01_p37.json` | `b16eb83cc20a6c432f1f3d2397beeca909a2ae3cdc249ed9a59d980d65c919df` |
| `trades_SPY_2022-06-01_p38.json` | `903db7ddbaea5848c3955989434deab68dfc12b6fb09a8b1f52b6717f248ef36` |
| `trades_SPY_2022-06-01_p39.json` | `0bb29a8962eb1ff6266bdbf71197c871ed9d1b8acaedc267d5aa4a4912cfe6d9` |
| `trades_SPY_2022-06-01_p4.json` | `a26b1bba65a415b4bf9e9033890764cd89ad9626e984f724a7fd324ef9bedb63` |
| `trades_SPY_2022-06-01_p40.json` | `55cc958da1234372a648f35e1da8b70a83fe05605e6352016486981b5128f00a` |
| `trades_SPY_2022-06-01_p41.json` | `483e9838deb0aaeb880ee459b6ae69e38728cf7b9d569882b1ca5ec9174f8a94` |
| `trades_SPY_2022-06-01_p42.json` | `1073b8c6f0f9d9e1e8d4523cddebecbd3fa4d25753ae76b654e68ee27b389821` |
| `trades_SPY_2022-06-01_p43.json` | `82203322f23d7f62760a5d9a9de59b70ad7b55fe272064a7cb51a6d43a9591a3` |
| `trades_SPY_2022-06-01_p44.json` | `0aef1d07a7f15087dd779c687254d9b6d1a1032230e1e11e5b97f433d55706bf` |
| `trades_SPY_2022-06-01_p45.json` | `dc7fec58d11e7b979ef2a92ec908f338d52acc53d595f1ade57958f3f2207587` |
| `trades_SPY_2022-06-01_p46.json` | `531977e10a984e31572c5417b2c20c45479d6b9f697b40d5cae964a524ef8451` |
| `trades_SPY_2022-06-01_p47.json` | `8a9d40b05908ded73fe97620264dbda382eb9ee4b84dfa3f0d011373e2117ff6` |
| `trades_SPY_2022-06-01_p48.json` | `9428e117f5ee9518f6737cfb29bdb2fb129217856b60c73fe1f213a18da1b1b3` |
| `trades_SPY_2022-06-01_p49.json` | `4fae3623e14b88b337e9f03105a3e91a628e14653da26af6bf54c118cf6b7439` |
| `trades_SPY_2022-06-01_p5.json` | `f05b048655861fa6882becef07ef0a16065446b8645048469b44548a3e14c672` |
| `trades_SPY_2022-06-01_p50.json` | `0f1aaf0139f59c78d4d8359fdc4ea731b19fde1996bf68620a60b6859f1a9651` |
| `trades_SPY_2022-06-01_p51.json` | `6af1f985f5b6822ff2dbb55842c2e34071ce6427be8a7ecde7e453f8abdbc94f` |
| `trades_SPY_2022-06-01_p52.json` | `ee16d0cf05ea1ea6cfe68e88a230747d78c6c2a7d45ba663cfcd6c2f4aa47afc` |
| `trades_SPY_2022-06-01_p53.json` | `31eb9faa0977b7161f411e38af2d28466f53fbce610fd055f15c063093f75405` |
| `trades_SPY_2022-06-01_p54.json` | `fd80ea791096be85cfbace2b66fa8d5bd21a4e69cd1faf3358d7f3ed84fd7741` |
| `trades_SPY_2022-06-01_p55.json` | `c027782c8d3e8a696f46c169fe9cc13856c3266a3fa474a5bbeda3eab99679ba` |
| `trades_SPY_2022-06-01_p56.json` | `ed05a9e707f79b0020b9b74028bf215162a5e05802a29128f0ea278781fd53a2` |
| `trades_SPY_2022-06-01_p57.json` | `03f29cd1e3f76039fb127843d5dff662868e6ddfaffb1b7fab031ce7829ac056` |
| `trades_SPY_2022-06-01_p58.json` | `81b0e4e6f9f6117bbdc3eedc0e6b7afb0215c298a1fa0fd28664177a5c637b94` |
| `trades_SPY_2022-06-01_p59.json` | `9b328d603b148658bea468c54cbe235149d942446457da80e233d169d02c7f7f` |
| `trades_SPY_2022-06-01_p6.json` | `9816ef458b694bdef0e5b6f9e74ca63119f04515b987b8ad55c1b8a3426f8f23` |
| `trades_SPY_2022-06-01_p60.json` | `3002d0a54f2d2e0b1ee8d315cc34ea03578e873c793baa3cd2b0146b9ed4acda` |
| `trades_SPY_2022-06-01_p61.json` | `6c76f1c4ec3afaddbcca0e9aef7c775b453e2ab64599a5f462570b4a5e8b84e3` |
| `trades_SPY_2022-06-01_p62.json` | `8422e5e29fd687a4d8aa42c350b4284b75cd6d30364cd10beed0d12b98dab347` |
| `trades_SPY_2022-06-01_p63.json` | `7c196c60189b95e3028abe9820d8278863723921ea3a80c3d5d05ab49076d7af` |
| `trades_SPY_2022-06-01_p64.json` | `30375908df352cf0985d218e3848f3a1bb251cc45a6bb037d2388cb46ddf9d07` |
| `trades_SPY_2022-06-01_p65.json` | `5c1e818b7dcacb17927a9750abfcb4c6827ee2f7972001b5a38ba426f60fadc0` |
| `trades_SPY_2022-06-01_p66.json` | `88a24e13e987a7efead60bf0e9dc3b1b670d92728f880f194ee8240fe7460b3c` |
| `trades_SPY_2022-06-01_p67.json` | `b387ce28135862c79e5bc950cb2000bbddb77c60ba4ff4c0b1cc2b5a208a8b91` |
| `trades_SPY_2022-06-01_p68.json` | `6d4c8851bfbbc3e7a538d1e2f922eb6e23d25ebc93e51c3ce3448a8d844a9f60` |
| `trades_SPY_2022-06-01_p7.json` | `29f369bd48595b0d86a92e8384a445a7f7b196a6b12f489ff338519d92ca4370` |
| `trades_SPY_2022-06-01_p8.json` | `f675e9d0aee43cfd31f1378d778ad4134126ce3675aca07ca98165980a840c93` |
| `trades_SPY_2022-06-01_p9.json` | `e7197214a824a116105d63e1740e73b00cc3f1c770ab6ebc261823859d0f352b` |

---

## 6. Governance Invariants

| Invariant | Status |
| :--- | :--- |
| `HYP_004` | NOT CREATED |
| `ResearchReInceptionGate` | NOT INVOKED |
| Empirical return computation | ZERO |
| OOS market data access | ZERO |
| Capital | `$0.00` |
| `NO_REAL_ORDERS` | `true` |
| Paper trading | NOT AUTHORIZED |
| Live trading | LOCKED |

---

```text
AUDIT_STATUS = HUMAN_AUDITED_CANONICAL_PROVIDER_CONTRACT
CANONICAL_COMMIT = 0590301b180389a15f598903425132b9b0386897
BASE_COMMIT = 793f018b0a06167599a37986c8f280459cf9f120
HYP_004 = NOT_CREATED
EMPIRICAL_EXECUTION = NOT_AUTHORIZED
```
