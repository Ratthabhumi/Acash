# ODR_UPI_MARKET_DATA_004 — Market price and reference FX retrieval (RATIFIED 2026-11-03; provider scope expanded by AMENDMENT_001 with every right UNKNOWN)

Ratified by the OWNER on 2026-11-03 through a conditional instruction ("ODR-004, ODR-005 ผมอนุมัติ
ถ้ามันถูกต้องแล้ว"), applied by the coding agent after the checks in
`ODR_UPI_MARKET_DATA_004_ACCEPTANCE.json` passed. `scope_providers` stays empty, so no provider is
enabled and no outbound request is possible; enabling a provider is a separate scope change.

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

`scope_providers` is empty: ratifying this record alone enables no provider. Each later entry
is an object `{"provider_id", "entitlement_verified", "display_permitted", "cache_permitted",
"evidence"}` recorded by the Owner; `acash.invest.market_authority` treats a provider as READY
only when it appears exactly once with `entitlement_verified` and `display_permitted` both
`true` and a local credential `ACASH/MARKET_DATA/<PROVIDER_ID>` exists. Adding an entry is a
scope change and is recorded with its own lineage.

Fixed endpoints (`acash.market_data.providers.ENDPOINTS`), GET only, no redirects or proxies:

| Provider | Host | Path | Query keys |
|---|---|---|---|
| `ALPACA_BASIC` | `data.alpaca.markets` | `/v2/stocks/trades/latest` | `symbols`, `feed=iex` |
| `MASSIVE_BASIC` | `api.massive.com` | `/v2/aggs/ticker/{TICKER}/prev` | `adjusted=false` |
| `BOT_REFERENCE_FX` | `gateway.api.bot.or.th` | `/Stat-ReferenceRate/v2/DAILY_REF_RATE/` | `start_period`, `end_period` |

The BOT host, path, header and fields are taken from research and are not yet confirmed
against a live response. `WEBULL_TH_OPENAPI` has no adapter.

Implementation note (2026-11-03, no scope change): the code now applies stricter conditions
than the paragraph above. A scope entry must also attest `calculation_permitted` and
`derived_value_permitted`, and a provider whose contract is unverified in
`market_authority.REGISTRY` stays `CONTRACT_UNVERIFIED` and is never READY. The BOT path is
`/Stat-ReferenceRate/v2/DAILY_REF_RATE/get`, but BOT is still contract-unverified, so it cannot
be enabled by a scope entry alone. Without `cache_permitted`, valuations live only in memory and
are discarded when authority is withdrawn.

## 4. Valuation rules already enforced in code

One market date per valuation; holdings without a price on that date, value-only holdings and
total-only accounts are excluded and reported (`PARTIAL_INDICATIVE_VALUATION`), never counted as
zero; reference FX is labelled as not executable; broker totals from another time are
marked `TIME_MISALIGNED_COMPARISON` and never reconciled against new prices.

## 5. Ratify, revoke, rollback

The Owner sets `status` to `RATIFIED`, `ratified_by` to `OWNER`, `ratified_on` to the date and
adds each verified provider to `scope_providers`, then commits. Any other status closes the gate;
revert that commit to roll back. Removing a provider from the list disables it.

## 6. Not authorized by this record

Trading (paper or live), broker account connectivity or synchronization, credentials for
trading, capital or currency transfers, paid subscriptions, native broker import, transaction
authoring and D5 admission.
