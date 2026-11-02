# ODR_UPI_MARKET_DATA_004 — Market price and reference FX retrieval (PROPOSED, NOT RATIFIED)

## 1. Capability

`OWNER_MARKET_DATA_RETRIEVAL_AUTHORIZED`: the local ACASH service may request price and
reference-FX observations from providers the Owner lists in `scope_providers`, store them under
`data/private/market/` and revalue the Owner's saved quantities through
`acash.invest.market_valuation` and PPDS.

## 2. Why a separate decision

ODR-001/002/003 allow no outbound network access and no provider credentials. A price refresh
sends instrument identifiers to a third party and needs a locally stored API key.

## 3. Scope

| Included | Excluded |
|---|---|
| Providers named in `scope_providers` after the Owner verifies entitlement and display rights for each | Any provider not listed; paid plans (`MARKET_DATA_SUBSCRIPTION`) |
| Sending symbols, exchanges and dates | Sending account refs, quantities, cost, cash, names or files |
| Market-data endpoints only | Trading, order, account, position or transfer endpoints of the same vendor |
| API keys in the Windows user credential store | Keys in the repository, frontend, URLs, logs, fixtures or AI context |
| Observations cached under `data/private/market/` as the provider's terms allow | Publishing or syncing observations |

`scope_providers` is empty: ratifying this record alone enables no provider.

## 4. Valuation rules already enforced in code

One market date per valuation; unknown or value-only holdings stop the revaluation instead of
counting as zero; reference FX is labelled as not executable; broker totals from another time are
marked `TIME_MISALIGNED_COMPARISON` and never reconciled against new prices.

## 5. Ratify, revoke, rollback

The Owner sets `status` to `RATIFIED`, `ratified_by` to `OWNER`, `ratified_on` to the date and
adds each verified provider to `scope_providers`, then commits. Any other status closes the gate;
revert that commit to roll back. Removing a provider from the list disables it.

## 6. Not authorized by this record

Trading (paper or live), broker account connectivity or synchronization, credentials for
trading, capital or currency transfers, paid subscriptions, native broker import, transaction
authoring and D5 admission.
