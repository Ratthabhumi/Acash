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
