# MEC-0011: $0 GOLD / DXY DATA FEASIBILITY AUDIT

**Document ID:** `docs/phase14/mec_0011_gold_dxy_data_feasibility_audit.md`
**Object:** Feasibility audit of genuinely free, reproducible, legally usable historical Gold + DXY datasets for future MEC-0011 research (price divergence, relative-movement divergence, volume/liquidity divergence).
**Status:** `[DOCUMENTATION-ONLY]` `[DATA FEASIBILITY STAGE]` `[NOT EMPIRICAL VALIDATION]` `[NOT HYP_003]` `[NOT R1]` `[NOT A CANDIDATE]`
**Date:** 2026-09-10 (retrieval date for all claims; evidence fetched from provider/authoritative pages on this date)
**ASCII-only:** YES (no non-ASCII bytes)

---

## 1. Objective

Audit whether a genuinely free ($0), reproducible, legally usable, historical Gold + U.S. Dollar Index (DXY) dataset can support FUTURE research of:

1. Cross-asset price divergence (Gold return <-> DXY return)
2. Gold/DXY relative-movement divergence
3. Volume/liquidity divergence

This audit is a FEASIBILITY question only. It is NOT empirical validation, NOT signal testing, and NOT a strategy.

## 2. Scope

- Instrument families audited: Gold (spot/fix, COMEX futures, gold ETF, spot proxy, synthetic) and US dollar index (ICE DXY index, DX futures, dollar ETF/proxy, official alternative USD indexes).
- Source classes audited: Stooq, FRED, Yahoo-derived endpoints, LBMA/IBA, World Gold Council, CME Group/COMEX, CFTC, Shanghai Gold Exchange, ECB, World Bank, plus secondary aggregators evaluated for completeness (Barchart, investing.com, MarketWatch, MacroTrends, FreeGoldAPI, DataHub).
- Explicitly OUT of scope: any download, any correlation/return calculation, any specification, any validation, any registry promotion.

## 3. Governance Boundary

MEC-0011 remains:

```
RESEARCH INTAKE ONLY
NOT AUTHORIZED FOR EMPIRICAL VALIDATION
```

STRICTLY PROHIBITED by this audit and by the underlying intake:
- backtest, signal testing, correlation testing, predictive testing
- parameter optimization, performance claims, strategy construction
- HYP_003 creation, R1 invocation, gate invocation, candidate authorization
- modifying MACRO-001, modifying F-1, modifying canonical source registries
- inventing data coverage, assuming any source is PIT without proof
- treating ETF volume, futures volume, spot volume, or synthetic volume as interchangeable

## 4. Current Source-Registry Status

Source document inspected: `docs/phase14/free_data_source_registry.md` (read-only; NOT modified).

- Registry contains S-01..S-28 (Tier 1 authoritative, Tier 2 quality secondary, Tier 3 community-with-provenance, Tier 4 unverified aggregation).
- **No Gold or DXY source is currently ACCEPTED or registered as such.**
- Closest existing entries (relevant but NOT gold/DXY-specific):
  - S-04 FRED `[ACCEPT]` (official macro/VIXCLS daily; vintage `[CONDITIONAL]`).
  - S-10 Stooq `[CONDITIONAL]` (daily OHLCV active names; personal-use-only license; `[PIT UNPROVEN]`).
  - S-18 yfinance (Yahoo wrapper) `[CONDITIONAL]` active / `[REJECT]` deep delisted; ToS risk.
  - S-26 historicaldata.net `[NOT SUFFICIENT AT $0]`; S-28 stockanalysis.com `[UNVERIFIED]`.
- Conclusion: this audit changes nothing in the registry. Any future promotion requires a separate, evidence-backed registry update by the human operator.

## 5. Gold Price Candidates

Each candidate field map: 01 Provider, 02 Dataset/series, 03 Instrument identity, 04 Start, 05 End, 06 Granularity, 07 OHLC, 08 Volume, 09 Adjustment, 10 Corporate actions, 11 Survivorship, 12 PIT/vintage, 13 Timestamp/TZ, 14 Revisions, 15 Reproducibility, 16 API/accessibility, 17 Rate limits, 18 Cost $0, 19 License/terms, 20 Commercial/research restrictions, 21 Provenance docs, 22 Archive-at-retrieval.

### 5.1 Stooq XAUUSD (spot-style Gold/USD pair) - Classification: VERIFIED series / CONDITIONAL start+license
- 01 Stooq.com. 02 `XAUUSD` daily historical OHLCV ("Gold (ozt) / U.S. Dollar"). 03 Spot gold quoted USD/ozt, FX-pair bar format.
- 04 Start ~1968 (CONDITIONAL; indexed page shows ~15.2k daily rows through 2026-03; chart advertises "Max (from 1793)"; early values fix-era, not tick tape). 05 Present.
- 06 Daily OHLC bars (weekly/monthly derivable). 07 OHLC = YES. 08 Volume = NO (FX pair; CSV volume field empty/zero).
- 09 No adjustment (raw market prices). 10 N/A. 11 N/A (single continuous pair). 12 No vintage ids; pre-1990s OHLC likely fix-derived, treat as approximate `[PIT UNPROVEN]`.
- 13 Bars stamped with close at ~22:00 CET/CEST (Warsaw wall-clock) which equals ~16:00 ET (US session close). 14 Silent corrections possible; no changelog.
- 15 Deterministic CSV URL `stooq.com/q/d/l/?s=xauusd&i=d&d1=YYYYMMDD&d2=YYYYMMDD`. 16 CSV endpoint + website download link; bulk ZIP is CAPTCHA-gated; API key CAPTCHA-issued (CONDITIONAL).
- 17 Daily hit quota; 429 on exceed; bulk throttled. 18 $0. 19 Personal-use only; redistribution requires Stooq consent (ToS section 5.3 direction unambiguous; literal English page 404 - CONDITIONAL). 20 Commercial prohibited; internal academic research typically tolerated.
- 21 Minimal provenance; early values likely LBMA-fix-derived (inference, not documented). 22 Feasible (per-symbol CSV snapshots archived at retrieval).

### 5.2 Stooq GC.F (COMEX gold futures continuous) - Classification: REJECTED
- Historical CSV download absent for `gc.f` (since ~Jan 2022; confirmed in pandas-datareader issue #925 and Fund Manager forum 2024). Quote page live but no volume. Moot at $0.

### 5.3 FRED GOLDAMGBD228NLBM / GOLDPMGBD228NLBM (London AM/PM fixing) - Classification: REJECTED (DELISTED)
- Deleted from FRED 2022-01-31 (IBA licensing action; official announcement 2022-01-10). API returns 400. ALFRED vintage layer purged too.
- Method note: formerly daily London business-day fix values, single value per session (no OHLC, no volume), start ~1968-04. Recoverable only via Internet Archive snapshots - reproducibility CONDITIONAL, licence question remains (IBA values).
- Lesson recorded: "free government-hosted" does not imply permanent availability - canonical survivorship-analog event for this audit.

### 5.4 LBMA / IBA LBMA Gold Price (auction benchmark) - Classification: CONDITIONAL
- Today's price free with delay-to-midnight; historical tables moved to MyLBMA Portal (2025-11-24 onward), non-members register and confirm IBA licence or non-commercial/educational use; commercial/redistribution requires paid IBA licence.
- Daily auction fix (10:30/15:00 London), no OHLC, no public volume; series back to ~1919/1968+ regime shifts (Fixing->Auction 2015-03-20). $0 only for today or licensed non-commercial access. Not a bulk-free historical source.

### 5.5 World Gold Council GoldHub - Classification: VERIFIED (monthly only) / daily REJECTED
- Monthly/quarterly/annual free aggregates since 1978; daily LBMA history REMOVED 2025-03-18 "at the request of the ICE Benchmark Administration". Not usable for daily research.

### 5.6 CME Group / COMEX gold futures settlements - Classification: REJECTED (historical at $0)
- Today's settlement free (delayed to midnight CT); historical EOD (OHLC + volume + OI) requires paid DataMine subscription. FTP `cmegroup.com/settle` being decommissioned (migrating to DataMine). Historical at $0 = NO.

### 5.7 Yahoo Finance GC=F / XAUUSD=X - Classification: CONDITIONAL (grey)
- Functionally free via unofficial `yfinance`; ~Aug 2000+ continuous front-month OHLCV with volume; official CSV download paywalled (Yahoo Finance Gold tier). ToS prohibits automated collection/commercial use; unlicensed; silent chain logic. Not defensible for archives.

### 5.8 World Bank Pink Sheet (Gold, monthly) - Classification: VERIFIED (monthly only)
- Monthly gold $/oz since Jan 1960, free downloadable xlsx/PDF, public-domain-style usage. Monthly, not daily. Anchor for long-horizon only. DataHub mirror `core/gold-prices` (monthly, 1833+, PDDL) also verified monthly.

### 5.9 Aggregator fringe (FreeGoldAPI; MacroTrends; investing.com) - Classification: REJECTED for this audit
- FreeGoldAPI: ~1,678 rows, daily only 2025+, Yahoo-contaminated, "educational purposes". MacroTrends daily CSV is a paid SKU. investing.com prohibits scraping/redistribution. Not feasible at $0 / not clean.

## 6. DXY Price Candidates

### 6.1 FRED Federal Reserve dollar indexes - Classification: ACCEPT / CONDITIONAL (official)
- Exact series available (official, free, deterministic):
  - `TWEXBGS` Nominal Broad U.S. Dollar Index (daily, 2006-01-02+).
  - `DTWEXBGS` predecessor Nominal Broad index (1971+ daily; discontinued/deprecated ~2019-12-31; splice required - annotate regime/method change).
  - `TWEXMTHY` (major currencies variant, daily, ~1973+).
- 06 Daily. 07 No OHLC (index level per day). 08 No volume. 09 No adjustment. 11 Index-level continuity requires explicit handling of the DTWEXBGS->TWEXBGS replacement. 12 ALFRED vintage layer exists for many Fed series (CONDITIONAL; archive-to-prove). 13 Daily values stamped on US business days (noon ET convention). 15 Deterministic: `fredgraph.csv?id=...` (keyless) or FRED API (free key; ~120 req/min). 18 $0. 19 Federal data, permissive (FRED ToS free for research). 20 Redistribution generally permitted for Fed-computed series, subject to FRED terms. 22 Archive-at-retrieval feasible.
- CRITICAL identity note: FRED dollar indexes are the Federal Reserve's OWN effective-exchange-rate indexes (broad/major-currencies baskets), NOT the ICE DXY index. They are dollar-strength measures but do not equal DXY.

### 6.2 ECB eurofxref (DXY reconstruction from six constituents) - Classification: VERIFIED license / CONDITIONAL as DXY proxy
- `eurofxref-hist.zip` / daily XML reference rates, 29 currencies, history 1999-01-04+, daily TARGET working days, published ~16:00 CET.
- Reuse policy VERIFIED (ECB Disclaimer page): free of charge, attribution required, modifications must be disclosed, programmatic access not restricted.
- DXY proxy feasibility: DXY = geometric basket of 6 currencies (EUR, JPY, GBP, CAD, SEK, CHF). Reconstructing a DXY-like level from ECB reference rates is executable from one free endpoint (6/6 constituents confirmed present in fetched 2026-09-09 cube).
- Conditionality: (a) reconstruction is `[MODEL INFERENCE]`, NOT the ICE DXY; (b) DXY basket weights are NOT constant over history (EUR introduced 1999; periodic weight updates) - a historical DXY-proxy must either freeze current weights (modern window only) or track published weight vintages (research burden); (c) ECB reference rates are ECB-style reference mid-rates at ~14:10 concertation, not DXY trading levels; (d) start 1999, DXY itself starts ~1973.

### 6.3 Stooq ^DXY / DX.F - Classification: CONDITIONAL (access flaky)
- Symbols exist (index / continuous futures); direct CSV attempts returned a JS proof-of-work challenge (2026-09-10), so programmatic bulk not reliably verifiable; personal-use license. Deprioritize for deterministic pipelines.

### 6.4 Yahoo Finance DX-Y.NYB / ^DXY (ICE DXY index) - Classification: CONDITIONAL (grey)
- Actual ICE DXY level, daily, back to ~1973 via unofficial `yfinance`; free in practice, ToS-violating for archival/automated use. Not defensible for distributed archives.

### 6.5 MarketWatch DXY CSV - Classification: CONDITIONAL (shallow only)
- Free recent ~30 trading days of DXY OHLC verified (`daterange=d30`); deeper/custom ranges blocked by anti-bot captcha. Not a historical source.

### 6.6 ICE official DXY index data - Classification: REJECTED at $0
- ICE Data Services distributes index data as a paid data product; no free historical bulk download.

## 7. Gold Volume Candidates

- 7.1 CME DataMine (COMEX GC daily Volume + Open Interest) - Classification: REJECTED at $0 (historical paid; today-only free). Gold-standard exchange volume is proprietary.
- 7.2 CFTC Commitments of Traders (GC) - Classification: CONDITIONAL (weekly OI, NOT volume). Free since 1986 (legacy) / 2006 (disaggregated), weekly Tuesday data, public domain. Provides open interest and position concentrations - a positioning metric, NOT trading volume, and NOT daily.
- 7.3 Gold ETF daily volume (GLD 2004-11-18+, IAU 2005-01-21+) - Classification: CONDITIONAL. Daily share-turnover volume. Free channels: SPDR official XLSX archive (most reproducible), Stooq (non-commercial), yfinance (ToS grey). NOT physical/spot/futures volume; secondary-market share turnover only. NYSE 4pm ET timestamp.
- 7.4 LBMA clearing statistics - Classification: CONDITIONAL (monthly). Free, Oct 1996+; daily averages within month; net end-of-day clearings which per LBMA's own methodology underreport true turnover. Not daily-alignable.
- 7.5 Shanghai Gold Exchange daily reports - Classification: CONDITIONAL (daily but restricted). Free web query limited to 1-month windows, no bulk API, CST timezone, Chinese venue (not COMEX/London), two-way-counted volume. Not an accessible deep archive.
- 7.6 WGC Goldhub trading volumes - Classification: REJECTED for primary use. Derived multi-venue estimate, monthly, redistribution-restricted, methodology-dependent composite.

## 8. DXY Volume Candidates

- 8.1 DXY index itself - Classification: VERIFIED - has NO native volume. ICE U.S. Dollar Index is a computed geometric benchmark; official index data is paid; no volume concept exists for the index level.
- 8.2 ICE DX (USDX) futures volume - Classification: CONDITIONAL / UNVERIFIED at free. DX trades on ICE Futures U.S. (NOT CME); ICE publishes daily exchange statistics but a free, reproducible, full-history DX volume/OI download was NOT verified. Third-party mirrors (Barchart, Stooq DX.F) are personal-use or unlicensed; investing.com scraping prohibited.
- 8.3 UUP / UDN (Invesco DB USD Index funds) - Classification: CONDITIONAL. Inception/trading Feb 2007; returns driven by long/short DX futures + Treasury collateral (NOT DXY spot). Daily ETF share volume obtainable via Stooq/Yahoo (free channels, license caveats); Yahoo/UUP unofficial paths not PIT-clean.
- 8.4 Alternative dollar-liquidity proxies (CME FX futures volume, BIS triennial swap volumes) - noted only: different semantics (currency futures turnover / 3-year survey), NOT comparable to daily gold volume.

## 9. Cross-Source Timestamp Compatibility

- Gold price (Stooq XAUUSD): daily bar closes ~22:00 CET/CEST = ~16:00 ET -> aligns to the US-session daily boundary.
- Dollar index (FRED Fed indexes): daily value on US business days (noon ET convention); Yahoo ^DXY daily close aligned to US session; ECB reference rates published ~16:00 CET with 14:10 concertation values.
- Gold ETF volume (GLD/IAU), dollar ETF volume (UUP/UDN): NYSE 4:00 PM ET.
- Verdict: CONDITIONAL - a COMMON DAILY TIMESTAMP is achievable if the shared trading calendar is defined as US/NYSE trading days and both legs archive at the daily boundary (16:00 ET). SEAM: gold trades on sessions the US market is closed (e.g., some London-only days); such days must be defined/merged deterministically in a future pre-registration, not silently dropped. ECB-based DXY proxy uses TARGET working days - a different calendar than US equity days -> needs explicit calendar conversion (seek "latest available common day").

## 10. Adjustment Semantics

- Gold spot/fix (Stooq XAUUSD, FRED historical, LBMA): raw levels, no corporate actions, no adjustment. No adjustment pipeline needed for the price leg.
- Dollar indexes (FRED TWEX*, ICE DXY): index levels, no corporate actions. Method/series replacements exist (DTWEXBGS->TWEXBGS; London Fixing->Auction) - treat as SERIES/METHOD CHANGES, never splice silently.
- ETFs (GLD, UUP): share-volume series; adjust for splits if any (GLD largely unsplit; UUP has had share issuance) - an archive-time check, not a research-time fabrication.
- No adjustment transformation may be introduced as a silent parameter (per AGENTS.md #3 fail-closed discipline).

## 11. PIT / Vintage

- MEC-0011 does NOT require a scheduled-event PIT calendar (unlike MACRO-001). But revision-aware handling is required:
- Stooq: mutable DB, no vintage ids `[PIT UNPROVEN]` unless archived at retrieval.
- FRED: ALFRED vintage layer exists for many Fed series; the near-real-time values are the current vintage `[CONDITIONAL]`. DTWEXBGS->TWEXBGS replacement introduces a discontinuity that must be versioned.
- ECB: reference rates are final for posted dates (historical values not revised). `[CONDITIONAL-PROVABLE via archive]`.
- Yahoo: silent revision/chain churn; no vintage. `[PIT UNPROVEN]`.
- Dolt-style versioning must NOT automatically be called PIT (mirrors readiness doctrine): PIT is proven by construction/archive evidence, not by tooling.

## 12. Survivorship / Instrument Continuity

- Index-level continuity (dollar): DXY continuous since 1973 but its level is ICE-proprietary; FRED Fed indexes require explicit DTWEXBGS->TWEXBGS method-change handling. FRED gold deletion (2022) is direct evidence that even government-hosted series can die -> all legs need archive-at-retrieval.
- Gold reference continuity: spot price continuous 1968+; the London Fixing->Auction regime shift (2015-03-20) is a method change, not survivorship.
- Futures rollover: NOT used in this audit (no futures leg selected). If ever promoted to futures-based designs, continuous-chain construction and roll-over policy become a specification responsibility.
- ETF lifecycle: GLD (2004+), UUP (2007+) both alive and liquid; any future ETF-based volume leg must treat lifecycle/halt/issuance events explicitly.
- No silent substituting between futures / ETF / spot / index.

## 13. Reproducibility

- Deterministic at $0: FRED (`fredgraph.csv?id=...`, or free API key) - HIGH; ECB (`eurofxref-hist.zip`) - HIGH; Stooq single-symbol CSV (`q/d/l/?s=xauusd&i=d&d1=...`) - MEDIUM (quota + CAPTCHA + JS challenge; archive immediately); World Bank Pink Sheet - HIGH (monthly).
- LOW/UNVERIFIED: Yahoo/yfinance (endpoint churn, IP-bans), MarketWatch (captcha for depth), Barchart (personal-use, no bulk), SGE (1-month window only), CME DataMine (paid).
- Reproducibility rule for any future ingest: raw bytes + fetch timestamp + provider version archived at retrieval for EVERY leg (per registry terms-of-use).

## 14. Licensing

- FRED: permissive - free for research; Fed-computed series generally redistributable under FRED terms. `[VERIFIED]`.
- ECB: free reuse with attribution + disclosure of modifications; programmatic access unrestricted. `[VERIFIED]` (ECB Disclaimer page).
- Stooq: personal/non-commercial only ($5.3 redistribution needs consent); commercial prohibited. `[VERIFIED direction / CONDITIONAL literal text]`.
- World Bank Pink Sheet: freely available, public-domain-style usage; DataHub copy PDDL. `[VERIFIED]`.
- Yahoo (yfinance): ToS bar automated collection and commercial use; distribution of archived Yahoo data is not clean. `[VERIFIED as risk]`.
- LBMA/IBA: benchmark IP; commercial use and redistribution require IBA licence; non-commercial portal use is conditional-granted. `[VERIFIED]`.
- CME DataMine: exchange-data licence + subscription; redistribution agreement required. `[VERIFIED]`.
- CFTC COT: US government public domain. `[VERIFIED]`.
- WGC: free for limited review/commentary; redistribution needs written consent. `[VERIFIED]`.
- Barchart/investing.com/MarketWatch: personal-use or scraping-prohibited. `[VERIFIED as unsuitable]`.

## 15. Cost / Access

- All accepted/conditional candidates are $0 at the point of access.
- Historical gold volume (COMEX), historical ICE DXY data, historical CME EOD, MacroTrends daily CSV, and any paid benchmark licence are NOT $0 and are out of scope pending a Human-Governance-funded acquisition queue (no such authorization exists).
- No download was performed during this audit; no API keys were created.

## 16. Price-Only Feasibility

Question: are {Gold price series, DXY price series, common daily timestamp, sufficient historical depth, reproducible retrieval} jointly feasible at $0?

Assessment:
- Gold price at $0: only Stooq XAUUSD offers deep daily (OHLC, ~1968+) among clean $0 paths; its license is personal/non-commercial. FRED gold is gone; LBMA historical is licence/portal-gated; CME historical is paid; Yahoo is grey. Monthly-only alternatives cannot support daily research.
- DXY-like price at $0: FRED Fed dollar indexes (official, free, deterministic, 1971/2006+) OR ECB-eurofxref DXY-proxy reconstruction (1999+, verified executable, needs weight-vintage handling) OR grey Yahoo ^DXY. Longest official continuous dollar index: Fed broad index (1971 splice required).
- Common daily timestamp: achievable on a US/NYSE-trading-day calendar (both legs archive at ~16:00 ET); calendar seams (gold London-only days; TARGET-vs-NYSE for ECB) must be handled by a pre-registered merge policy.
- Historical depth: gold ~1968+, dollar index ~1971+/1999+ -> sufficient for decadal research, CONDITIONAL on the DXY-leg method-change splice and on early-gold fix-derived OHLC caveats.
- Reproducible retrieval: FRED (DETERMINISTIC), ECB (DETERMINISTIC), Stooq (CONDITIONAL - archive-at-retrieval mandatory).

```
PRICE-ONLY: CONDITIONAL
```

- Feasible at $0 in-principle. NOT classified ACCEPT because:
  1. The only deep daily gold price leg (Stooq XAUUSD) carries a non-commercial/personal-use license - archiving into a redistribution-free private research corpus is consistent with that license, but must be explicit.
  2. Early gold history is fix-derived approximate OHLC (1968-~1990s), not tick-grade.
  3. The DXY leg is either a Fed-computed index (NOT ICE DXY) or a model-inference proxy (ECB) - both require pre-registered identity + weight-vintage handling.
- No return/correlation is computed here; this is a pure availability statement.

## 17. Volume-Divergence Feasibility

Question: can we obtain Gold_volume_t and DXY_volume_t with ECONOMICALLY COMPARABLE semantics at $0?

- Gold volume at $0, exchange-grade, daily: NO (COMEX history is DataMine-paid; CFTC is weekly OI, not volume; SGE daily is shallow/restricted and a different venue). Nearest daily free proxy: GLD/IAU ETF share volume (CONDITIONAL, license caveats).
- DXY volume at $0: the DXY index has NO volume (verified - it is a computed benchmark). DX futures volume has no verified free reproducible full-history source (Barchart/Stooq personal-use; investing.com scraping-prohibited). Nearest daily free proxy: UUP/UDN ETF share volume (CONDITIONAL; and UUP is DX-futures-based, not DXY-spot).
- Comparable semantics: the strongest $0 candidate pair (GLD vs UUP) is "ETF secondary-market daily share turnover" on both legs - comparable to each other in the weak sense, but NOT comparable to exchange-grade futures volume, NOT the video's implied "volume mismatch", and NOT independent across legs (UUP is a fund, GLD is a trust; both are NYSE-listed US ETFs - common market microstructure confounds the "mismatch" interpretation).
- Bonus hazard: DXY has no volume by construction -> any formulation that literally maps the video's "DXY volume" is unsatisfiable, not merely expensive.

```
VOLUME-DIVERGENCE: NOT SUFFICIENT AT $0 (exchange-grade / canonical semantics)
                 CONDITIONAL (only as a GLD-vs-UUP ETF-volume reformulation with major caveats)
```

Therefore, per the intake instruction:

```
VOLUME-DIVERGENCE SUB-MECHANISM =
NOT FEASIBLE AT $0 / NOT OPERATIONALIZED
```

MEC-0011 itself is NOT terminated by this finding. The PRICE / RELATIVE-MOVEMENT divergence track remains conditional-feasible (Section 16).

Future consideration (variant NOT created here): a liquidity-based formulation could be evaluated as a NEW mechanism variant (e.g., golden-ETF vs dollar-ETF share-turnover divergence, or gold-futures OI change via CFTC weekly vs dollar OI) - semantics, frequency-mismatch, and confound handling would need a fresh intake/decision. Do not create this variant without human instruction.

## 18. Blockers

- B1 (licensing): only deep daily gold price is Stooq XAUUSD - personal/non-commercial use. Archive-and-private-research usage is consistent; distribution/commercial use is NOT. Human decision required on the usage frame (private research vs. anything broader).
- B2 (DXY identity): there is no free official ICE DXY level. Options are Fed-computed dollar indexes (different instrument) or an ECB proxy reconstruction (model inference + weight-vintage burden) or grey Yahoo. A pre-registered DXY-leg identity decision is required - selection is a specification choice the agent must NOT make (per instruction: do not select the instrument/proxy yourself).
- B3 (vintage/method-change): DTWEXBGS->TWEXBGS splice; London Fixing->Auction regime shift; early-gold fix-derived OHLC. All require pre-registered handling.
- B4 (volume): the literal "volume mismatch" is not satisfiable at $0 because DXY has no native volume and exchange-grade gold volume is paid. Only the GLD-vs-UUP ETF reformulation is conditionally possible, carrying structural confounds.
- B5 (registry): no Gold/DXY source is ACCEPTED in `free_data_source_registry.md`. Promotion requires a separate, human-authorized, evidence-backed update - not performed here.

## 19. Source-by-Source Classification

| source | family | granularity | $0? | daily? | license | classification |
|---|---|---|---|---|---|---|
| Stooq XAUUSD | gold spot-style | daily OHLCV | yes | yes | non-commercial | VERIFIED / CONDITIONAL (start+license) |
| Stooq GC.F | gold futures | daily | yes | download-blocked | non-commercial | REJECTED |
| FRED GOLDAMGBD228NLBM/PM | gold fix | daily level | gone | gone | n/a | REJECTED (DELISTED 2022) |
| LBMA/IBA LBMA Gold Price | gold fix | daily | today-only | hist-gated | IBA licence | CONDITIONAL |
| WGC GoldHub | gold aggregate | monthly | yes | no | limited reuse | VERIFIED (monthly) / daily REJECTED |
| CME/COMEX settlements | gold futures | daily | no (hist) | yes | paid | REJECTED (hist at $0) |
| Yahoo GC=F/XAUUSD=X | gold futures/spot | daily OHLCV | grey | yes | ToS-restricted | CONDITIONAL (grey) |
| World Bank Pink Sheet | gold | monthly | yes | no | free/PD-ish | VERIFIED (monthly only) |
| FRED TWEXBGS/DTWEXBGS/TWEXMTHY | USD index (Fed) | daily | yes | yes | permissive | ACCEPT / CONDITIONAL (vintage+splice) |
| ECB eurofxref | exchange rates | daily | yes | yes | free+attribution | VERIFIED (license) / CONDITIONAL (proxy) |
| Stooq ^DXY / DX.F | USD index/futures | daily | yes | access flaky | non-commercial | CONDITIONAL |
| Yahoo DX-Y.NYB / ^DXY | ICE DXY index | daily | grey | yes | ToS-restricted | CONDITIONAL (grey) |
| MarketWatch DXY | USD index | daily | yes | 30-day only | personal-view | CONDITIONAL (shallow) / REJECTED (deep) |
| ICE DXY official | USD index | daily | no | yes | paid | REJECTED at $0 |
| CME DataMine GC VOI | gold futures vol | daily | no | yes | paid | REJECTED at $0 |
| CFTC COT (GC) | gold futures OI | weekly | yes | no | public domain | CONDITIONAL (OI, not volume) |
| GLD/IAU volume | gold ETF | daily | yes | yes | mixed (Stooq/SPDR/yfinance) | CONDITIONAL |
| LBMA clearing | gold spot proxy | monthly | yes | no | free | CONDITIONAL (monthly, underreporting) |
| SGE daily | gold physical | daily | yes | yes | unclear / restricted | CONDITIONAL (shallow access) |
| WGC Goldhub volumes | gold synthetic | monthly | partial | no | restricted | REJECTED (primary) |
| ICE DX futures volume | USD futures vol | daily | no verified free full-history | yes | conditional/paid-grey | CONDITIONAL / UNVERIFIED at free |
| UUP / UDN volume | USD ETF | daily | yes | yes | mixed (Stooq/Yahoo) | CONDITIONAL |
| investing.com / Barchart | agg | - | view-free | - | personal/scrape-prohibited | REJECTED |

## 20. Overall Classification

```
PRICE-ONLY:                    CONDITIONAL
  - Gold daily price leg:       CONDITIONAL (Stooq XAUUSD; license frame = human decision)
  - Dollar-index daily leg:     ACCEPT (FRED Fed indexes) / CONDITIONAL (ECB DXY-proxy; grey Yahoo)
  - Common daily timestamp:     CONDITIONAL-ACHIEVABLE (US/NYSE-trading-day calendar)
  - Depth:                      sufficient (gold ~1968+, dollar ~1971+/1999+) with method-splice handling
  - Reproducible retrieval:     yes (FRED, ECB deterministic; Stooq archive-at-retrieval)

VOLUME-DIVERGENCE:             NOT SUFFICIENT AT $0 (canonical/exchange-grade semantics)
                               CONDITIONAL only as GLD-vs-UUP ETF-volume reformulation (unverified, confounded)
```

MEC-0011 continues to carry the classification:

```
RESEARCH INTAKE ONLY
NOT AUTHORIZED FOR EMPIRICAL VALIDATION
```

No candidate status, no registry promotion, no HYP_003, no R1, no validation authorization.

## 21. Recommended Next Stage

Recommended sequence for HUMAN decision (agent does not self-authorize):

1. Human decision #1 - usage/license frame for the gold leg: is MEC-0011 price research confined to PRIVATE, non-commercial, archive-at-retrieval use (Stooq-compatible), or does it require redistribution-safe data (=> no free daily gold exists; would require paid/academic licence or monthly-only design)?
2. Human decision #2 - DXY-leg identity (specification choice; NOT an agent decision): (a) Fed-computed dollar index (official, non-ICE, method-splice required), (b) ECB-reconstructed DXY proxy (1999+, weight-vintage handling, `[MODEL INFERENCE]`), or (c) ICE DXY via grey Yahoo (ToS-limited private archive only). If a literal "DXY level" is required, only (c) or a paid ICE licence approximates it.
3. Human decision #3 - volume branch disposition given the verdict: (a) park volume sub-mechanism and pursue PRICE-ONLY Track A; (b) declare the literal volume-mismatch sub-mechanism terminated as informationally unsatisfiable at $0 (DXY has no volume), keeping price/relative-movement track alive; (c) commission evaluation of the GLD-vs-UUP ETF-volume reformulation as a NEW mechanism variant (fresh intake required, variant NOT created by this audit).
4. If the human keeps Track A: the next audit step (STILL not validation) is a $0 source-INITIALIZATION feasibility pass - deterministic retrieval POC of exactly two series (e.g., Stooq XAUUSD + one chosen dollar leg) with an archive-manifest, then STOP before any statistical object is built.
5. Live-schema integrity: this document introduces NO parameters, NO thresholds, NO formulas, NO direction, NO weights beyond citing published DXY basket composition for feasibility. No field was added to any registry.

### Verification Ledger
- Implementation Status: N/A (documentation-only feasibility audit; no code, no data ingest, no download)
- Contract Enforcement: STRICT FAIL-CLOSED - no source promoted; no PIT assumed; no license inferred; no series selected by the agent; no authorization granted
- Mathematical Authority: N/A (no formulation claimed; ECB-DXY reconstruction framed as MODEL INFERENCE only)
- Local Test Suite: NOT RUN (no code touched)
- Type Checker (MyPy): NOT RUN (no code touched)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats:
  - All classifications are VERIFIED/CONDITIONAL/REJECTED per evidence fetched 2026-09-10; provider terms can change post-retrieval (FRED gold deletion 2022 is the standing cautionary example).
  - Stooq literal English ToS page was 404 - license characterization relies on direction-consistent secondary recordings plus Stooq OpenAPI metadata.
  - ECB-DXY reconstruction is MODEL INFERENCE (not the ICE DXY); FRED Fed indexes are NOT ICE DXY.
  - No volume series is interchangeable across instrument families.
  - This audit performs NO empirical work; nothing here authorizes validation or strategy construction.