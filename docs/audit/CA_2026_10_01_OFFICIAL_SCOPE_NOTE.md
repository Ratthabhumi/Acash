# Official Corporate-Action Scope Note — Session 2026-10-01 (Research Only)

**Date Context**: 2026-10-01 (retrieval day; all timestamps UTC)
**Purpose**: F10 evidence research for a future operator-prepared intake.
**Not a determination file. Not a dispatch authorization. OBSERVATION_0002 remains NOT_AUTHORIZED.**

All fetches below are unauthenticated read-only HTTPS GETs of official
sponsor pages/PDFs (no Alpaca, no broker, no credentials, no orders).
Third-party dividend calendars were NOT used as authority.

---

## 1. Retrieved Official Sources (Preserved Evidence References)

| # | Symbol / Scope | Official URL | Retrieved (UTC) | Raw bytes | Raw SHA-256 |
|---|---|---|---|---|---|
| 1 | AGG product + distributions table | `https://www.ishares.com/us/products/239458/ishares-core-us-aggregate-bond-etf` | 2026-10-01T08:02:53Z | 1,902,351 | `3b54109fa410becf0417291e58d44ef6e4910a5a6f0049176313aa1a0bf2da5c` |
| 2 | ACWI product + distributions table | `https://www.ishares.com/us/products/239707/ishares-msci-acwi-etf` | 2026-10-01T08:02:53Z | 1,728,971 | `a49a3a593960f2ab8217e30347268acc76ee7ffb70b18515f0bac64ad0e83039` |
| 3 | SPY product page (frequency only) | `https://www.ssga.com/us/en/institutional/etfs/spdr-sp-500-etf-trust-spy` | 2026-10-01T08:02:53Z | 235,867 | `19bdb2d1b23d76a555e1bb80627014892d6a3abde374f534596d0ed79152c7b3` |
| 4 | SSGA historical-distributions library (JS index, no static rows) | `https://www.ssga.com/us/en/institutional/resources/documents/etf-dividend-distributions` | 2026-10-01T08:04:59Z | 79,998 | `89cdb28f0fe2ac6748ecc3448883c55f4d7af9bedd8e018925ead4da3ffd3b19` |
| 5 | iShares/BlackRock ETF distribution schedule (PDF) | `https://www.ishares.com/us/literature/shareholder-letters/isharesandblackrocketfsdistributionschedule.pdf` | 2026-10-01T08:06:21Z | 219,995 | `3aae43b85793cbf68e3d9c16a3106a647b62f24222d62ba13a7f05acdba55834` |

Source identities: rows 1–2, 5 = `BLACKROCK_ISHARES_OFFICIAL`; rows 3–4 =
`STATE_STREET_SPDR_OFFICIAL`.

---

## 2. Scope Interpretations (Session 2026-10-01)

### AGG — HAS_EVENT = true (exact official amount established)

Official distributions table (row 1) lists, latest-first:

```text
Record Date   Ex-Date       Payable Date   Total         Income
Oct 01, 2026  Oct 01, 2026  Oct 06, 2026   $0.334142     $0.334142 ($0 cap gains, $0 ROC)
Sep 01, 2026  Sep 01, 2026  Sep 04, 2026   $0.337062     (prior month — NOT reused)
```

- `has_event = true`, `ex_date = 2026-10-01`, `payable_date = 2026-10-06`,
  `amount_per_share = 0.334142` (income; exact, from the official table —
  distinct from September's `0.337062`, confirming no prior-month reuse).
- Embedded page data independently confirms `Oct 01, 2026` as the latest
  ex-date entry. Distribution frequency: Monthly.
- **F10 consequence**: the exact official AGG amount for 2026-10-01 is now
  establishable from sponsor evidence. No production determination file is
  created by this note; binding the amount into an intake document remains an
  operator dispatch-time act under a future Obs #2 authorization.

### ACWI — HAS_EVENT = false (scope-supported no-event)

Official distributions history embedded in row 2 lists 2026 ex-dates
`Mar 17, Jun 15, Sep 15` (preceded by 2025 `Dec 16` pattern) with **zero**
`Oct 01, 2026` entries anywhere on the page. No October 2026 ex-date exists
in the official record. Combined with the official schedule PDF (row 5),
this supports a scope-evidenced no-event determination for 2026-10-01.
(No frequency characterization beyond the observed rows is claimed.)

### SPY — HAS_EVENT = false (scope support partial; operator research noted)

- Row 3 confirms SPY `Distribution Frequency = Quarterly` on the official
  product page, but static content carries no distribution rows.
- Row 4 (official historical-distributions library) is JS-rendered with no
  static ex-date rows retrievable.
- Operator's schedule research (recorded here as operator research, NOT as
  bytes-verified by this note): State Street 2026 cycle ex-dates Sep 18 and
  Dec 18, hence no scheduled Oct 1 ex-date.
- **Honesty boundary**: Sep-18/Dec-18 dates were NOT independently confirmed
  from the fetched bytes in this task. A scope-evidenced SPY no-event intake
  for 2026-10-01 should cite the State Street schedule source directly at
  dispatch-preparation time.

---

## 3. Calendar Basis (F14)

Canonical CA-1 authority (local, no fetch): 2026-10-01 and 2026-10-02 are
both REGULAR sessions (`open_utc` 13:30Z, `close_utc` 20:00Z). The F14 rule
(target expires at next-session open) therefore has a concrete calendar
basis for the 2026-10-01 → 2026-10-02 transition.

---

## 4. Conclusion (Evidence ≠ Authorization)

- F10 factual posture as of this note: AGG event evidence (exact amount)
  available; ACWI no-event scope available; SPY no-event scope partially
  available (operator schedule research to be bound at preparation time).
- **OBSERVATION_0002 remains NOT_AUTHORIZED.** Still required: F14/F15
  human ratification, exact-amount intake binding by the operator at
  dispatch time, and an explicit Obs #2 dispatch authorization. No timer
  has been set by this task.

---

## 5. CORRECTION — ACWI Product-Identity Invalidation (2026-10-01, F19)

**Row 2 of §1 is INVALID as ACWI authority and MUST NOT be used.**

The URL `https://www.ishares.com/us/products/239707/ishares-msci-acwi-etf`
identifies iShares product **239707 = IWB (iShares Russell 1000 ETF)**,
not ACWI. Any digest or claim derived from row 2 (`a49a3a59…`) is
disqualified as ACWI evidence. This incident is recorded as the motivating
case for F19 source-identity verification (digests alone cannot detect a
wrong-product page).

Official identity (verified 2026-10-01 from the live official page below):
**239600 = ACWI / iShares MSCI ACWI ETF** (ticker ACWI, Semi-Annual
distribution frequency). The prior §2 claim of 2026 ex-dates
"Mar 17, Jun 15, Sep 15" is WITHDRAWN as unattributed (it cannot be traced
to the correct 239600 record).

## 6. Corrected Evidence (raw bytes preserved in-repo, F19-grade)

Retrieval method (2026-10-01, read-only): unauthenticated official-page
retrieval; exact received bytes preserved under
`docs/audit/ca_evidence_2026_10_01/`; SHA-256 recomputed over those bytes.
No Alpaca, no broker, no credentials. No production determination or Obs #2
authority is created by this correction.

| # | Symbol / Scope | Official URL | Preserved file | Bytes | SHA-256 |
|---|---|---|---|---|---|
| 6 | ACWI product + embedded distribution history | `https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf` | `acwi_239600_product_page.html` | 1,693,738 | `1369c71a839491fea0916f0c6ce2ce3a2697d13022093793a88f67a2c4ff1b56` |
| 7 | AGG product + distributions table | `https://www.ishares.com/us/products/239458/ishares-core-us-aggregate-bond-etf` | `agg_239458_product_page.md` | 65,362 | `67de92612aa60bf08b9df2cc6f00cb99074835c84e286d951f5bf17524d9eacb` |
| 8 | SPY product page (identity + frequency) | `https://www.ssga.com/us/en/institutional/etfs/spdr-sp-500-etf-trust-spy` | `spy_ssga_product_page.txt` | 98,089 | `2d981beb17945b304b7f9ee188c151eeec43e009d33eef92ea6095474069ba05` |

### ACWI — corrected scope (from row 6 bytes)

- Page identity: `portfolioId 239600`, ticker `acwi`, canonical URL
  `.../products/239600/ishares-msci-acwi-etf`, `Distribution Frequency:
  Semi-Annual`. Zero mentions of product 239707 anywhere in the bytes.
- Embedded official ex-date history (latest-first): `20260615, 20251216,
  20250616, …` — i.e. latest ex-date **2026-06-15** (Jun/Dec semi-annual
  pattern). **No 2026-10-01 ex-date exists** in the official record.
- Supports a scope-evidenced ACWI no-event determination for 2026-10-01
  once bound through the F19 bundle path with these exact bytes.

### AGG — event reconfirmed (from row 7 bytes)

- Latest-first table row: Record `Oct 01, 2026` / Ex `Oct 01, 2026` /
  Payable `Oct 06, 2026` / Total `$0.334142` / Income `$0.334142`
  ($0 gains/ROC), vs prior `Sep 01, 2026 / $0.337062` (not reused).
- `has_event = true`, `ex_date = 2026-10-01`, `payable_date = 2026-10-06`,
  `amount_per_share = 0.334142`. Product 239458 confirmed by URL.

### SPY — identity confirmed, schedule still partial (from row 8 bytes)

- Page identity: ticker SPY, CUSIP `78462F103`,
  `Distribution Frequency: Quarterly`, sponsor State Street.
- Static bytes carry no distribution rows (JS-rendered table, same boundary
  as before). The Sep-18/Dec-18 2026 schedule remains operator research,
  NOT bytes-verified here; a scope-evidenced SPY no-event intake must cite
  the State Street schedule source directly at preparation time.

### Revised F10 posture

- AGG = OFFICIAL EVENT ESTABLISHED (row 7 bytes).
- ACWI = CORRECTED SCOPE EVIDENCE AVAILABLE (row 6 bytes; row 2 void).
- SPY = OFFICIAL SCHEDULE/IDENTITY AVAILABLE, rows still partial.
- **F10 = NOT YET CLOSED END-TO-END** (pending F17/F18/F19 tooling +
  operator dispatch-time binding + explicit Obs #2 authorization).
