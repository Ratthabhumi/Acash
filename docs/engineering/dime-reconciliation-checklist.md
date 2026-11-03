# Dime! reconciliation checklist (sanitized, Owner-private)

Status of the 2026-11-02 → 2026-11-03 reconciliation. Codes and statuses only: no quantity,
price, balance, cost basis or account figure appears here by design. The read-only audit that
produced this lives in `src/acash/invest/reconciliation.py` and prints codes only.

## Readiness

| State | Value | Basis |
|---|---|---|
| `BASELINE_EVIDENCE_AVAILABLE` | YES | saved snapshot with quantity positions and a frozen-baseline workflow |
| `POST_BASELINE_TRADING_OCCURRED` | YES | Owner confirmed securities trading on 2026-11-03 |
| `POST_BASELINE_TRANSACTION_HISTORY_COMPLETE` | UNKNOWN | the 2026-11-03 trade list has not been supplied yet |
| `NOV2_FCD_BALANCE_VERIFIED` | NO | 2 Nov FCD is approximate, not confirmed |
| `NOV3_FCD_BALANCE_OBSERVED` | YES | 3 Nov FCD screenshot observed; a separate observation, not a reconciliation |
| `CURRENT_HOLDINGS_CONFIRMED` | NO | holdings screenshot is 2026-11-03 20:40, not an independent confirmation |
| `OWNER_PRIVATE_PORTFOLIO_RECONCILED` | NO | material evidence still missing |

## Applied Owner-authorized corrections (2026-11-03)

Both changes are local to `data/private/`; the originals were copied to
`data/private/backups/pre-correction-<timestamp>/` before writing, and the patched document was
validated by the real snapshot parser before the write became visible.

| Correction | Result |
|---|---|
| FX pair | The date-matched USD→THB entry is the anchor; the reverse direction is now `1 / rate` computed with `Decimal` to 12 decimals, carrying the same valuation date. The two 3 Nov Dime! directional quotes were **not** inserted into a 2 Nov snapshot |
| HOOD | Added to the Newwave grouping (four → five securities) as a quantity position with its cost basis; exactly one position row; no cash line changed |
| BUY replay | Not recorded — the order predates the cutoff, so no journal event and no second cash debit |
| Quantity precision | The holdings figure is used; the order figure and the 1e-7-share difference stay recorded as evidence, neither rounded nor overwritten |
| Price provenance | The position carries the broker's pre-open last price labelled `DIME_SCREENSHOT_PREOPEN_LAST`; it is a broker observation, not a canonical feed price, and is not presented as a 2 Nov close measurement |

Preflight after the correction: `READY_WITH_WARNINGS` (warnings: the pre-existing
`DIME_SECURITIES` unexplained difference, unverified security identity for securities without
MIC/ISIN, and an unverified market session — none of them are new).

## Real provider pilot (2026-11-03)

Owner accepted the Alpaca and MarketData.app account terms and confirmed personal, local,
noncommercial use. Each right was then attested only where the documented plan and the accepted
terms support it, and the pilot used one bounded request per provider with public symbols only.

| Provider | Rights attested | Real request | Observation |
|---|---|---|---|
| FRANKFURTER_ECB_FX | entitlement, display, calculation, derived, cache, retention | PASS | ECB reference USD/THB dated 2026-11-03, labelled reference-only |
| ALPACA_BASIC | entitlement, display, calculation, derived (cache and retention **denied**) | PASS | IEX last trades for AAPL and VOO on 2026-11-03 |
| ALPACA_HISTORICAL | same as Basic, delayed SIP only | PASS | delayed 1-minute bar closes, `INTRADAY_BAR_CLOSE` |
| MARKETDATA_APP_FREE | all six rights (terms permit local storage while the account is open) | PASS | delayed last trades dated 2026-11-02, labelled `HISTORICAL_DELAYED_LAST` |
| MASSIVE_BASIC / BOT / WEBULL | none | not attempted | outside scope; Massive derived-NAV rights unresolved |

Defect found and fixed by the pilot: MarketData.app received `Bearer` with the credential's
username half, so the first attempt was refused with `PROVIDER_ACCESS_DENIED`. The token is stored
in the secret half, the adapter now reads that half first (with a fallback), and a regression test
pins both layouts. The retry then returned a real delayed observation.

Portfolio refresh through the same handler the dashboard button calls: `REFRESHED`,
`PARTIAL_INDICATIVE_VALUATION`, reference FX resolved on the market date, every requested position
priced, HOOD present exactly once from the Newwave position, and the weight basis reported as
`SHARE_OF_PRICED_SUBTOTAL_NOT_TOTAL_PORTFOLIO`. The generation is **memory-only** because Alpaca's
cache right is denied, so a restart does not preserve it; the statement snapshot and journal are
never overwritten.

## Corrected valuation (2026-11-04)

The large Owner-private overstatement was traced to the **input**, not to PPDS: the reverse FX
direction had been entered as a THB-per-USD figure while labelled as USD-per-THB, so a
THB-denominated mutual fund was converted twice. For the fund this produced a value roughly
1,136x its THB NAV (33.8 x 33.65), which matches the figure that had been displayed. The
reciprocal correction recorded above removed it: the fund now values at units x THB NAV with no
FX multiplier, and a regression test pins that behaviour (`test_thb_fund_inside_a_usd_account_is
_not_multiplied_by_fx`).

| Component | Status after the correction |
|---|---|
| Thai mutual fund (THB NAV per unit, held in a USD-base account) | Correct: units x NAV, no FX applied |
| US securities | Priced from the 2 Nov statement prices; a real refresh replaces them with authorised observations |
| Cash, three accounts | Statement balances; FCD and securities cash stay separate |
| Gold (oz, USD/oz) | Separate instrument, converted under the FX policy |
| Total | Still **not** synchronised with the broker screenshot: the statement is valued 2026-11-02 while the screenshot is 2026-11-03 23:38, so market movement and the FX date explain the residual. No balancing cash or adjustment event was added to force a match |

Bridge verdict: the residual is classified as observation-timing plus FX-date difference, not as a
data-entry error. A same-moment comparison needs a snapshot taken from the broker at the same time
as the statement; until then the total is an indicative valuation, never a verified NAV.

The production Dashboard now opens in Owner-private mode only and hides the synthetic demo behind
an explicit test-harness flag, so the figures above are what an ordinary launch shows.

## Baseline status

No frozen baseline exists yet (`data/private/transactions/baseline.json` is absent) and no
journal exists, so there is no `BASELINE_V1` to preserve or amend. The corrected snapshot is the
provisional baseline source; the first recorded transaction freezes it as `BASELINE_V1`, inside
which HOOD is already present exactly once. A later `BASELINE_V2` is only needed if the baseline
must move again, and it goes through the existing previewed, confirmed rebase.

## Audit result for the newly observed security (HOOD)

| Check | Result |
|---|---|
| Present in the saved snapshot's securities | NO before the correction; **YES** after it |
| Present in the snapshot's quantity positions | NO before; **YES**, once, in Newwave |
| Present in the transaction journal | NO — no journal exists yet |
| Order timestamp vs opening cutoff | order is **before** the cutoff |
| Classification | `OPENING_BASELINE_POSITION_OMITTED` before the correction; now `PRE_BASELINE_IN_BASELINE` |
| Cash effect | `NONE_EVIDENCE_ONLY` — the order must not debit cash a second time |
| Fee | `FEE_NOT_ESTABLISHED` — no fee was invented |
| Order quantity vs holdings quantity | `DISPLAY_PRECISION_DIFFERENCE` at 1e-7 shares — both values preserved, neither rounded |
| Requires Owner confirmation | YES (versioned baseline amendment) |

Interpretation: the purchase precedes the frozen baseline, so it belongs to the *opening*
holdings, not to the journal. Recording it as a post-baseline transaction would double-count it.

## Other visible history

The META, ACHR and GEV purchases are dated before the opening cutoff as well. They are historical
evidence for cost basis and quantity review; they are **not** post-baseline events and must not be
appended to the journal. One of them does not expose an executed quantity, so its quantity stays
`NOT ESTABLISHED` rather than inferred from an amount and a price.

## FX finding (blocks preflight)

The stored FX pair fails the reciprocal check. Both stored directions are above 1 and their
product is far above 1, which is the signature of two *directional* broker quotes (buy/sell
spread) entered as if they were one reciprocal pair. Broker directional quotes are time-specific
and not reciprocals.

Recommended: store **one** canonical direction (THB per USD) or a reference rate, and let ACASH
derive the reciprocal. Do not enter both broker directions. Distinguish:

- broker directional quote → evidence only, not canonical,
- ECB/reference FX → canonical reference, not executable,
- executed broker FX → the only true confirmation of a conversion.

## What still needs the Owner

1. The 2026-11-03 securities trade list after the cutoff (side, security, quantity, fill price,
   date/time, currency, fee, settlement) — the only item that can move
   `POST_BASELINE_TRANSACTION_HISTORY_COMPLETE`.
2. A decision on the missing opening position: add it to the snapshot and confirm a previewed
   baseline rebase (a new versioned baseline), or explain why the 2 Nov 22:57 screenshot omitted
   it. Both leave the original baseline record intact.
3. A corrected FX entry (one direction) so the snapshot passes preflight.
4. Confirmation of current quantities and the securities-account settled cash, kept separate from
   the FCD balance.

No file under `data/private/` was modified by this audit and no figure from it appears in this
document or in Git.
