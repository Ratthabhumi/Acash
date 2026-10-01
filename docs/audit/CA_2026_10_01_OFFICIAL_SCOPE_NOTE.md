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
