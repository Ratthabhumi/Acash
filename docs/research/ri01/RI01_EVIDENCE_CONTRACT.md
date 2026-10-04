# RI-01 Raw-Data Evidence Contract (proposal, no lake built)

No data lake is implemented in this pack. This contract defines what a future
authorized acquisition MUST record so that every byte is attributable,
re-fetchable, and hash-pinned.

## 1. Per-retrieval evidence envelope (mandatory fields)

| Field | Purpose |
| :--- | :--- |
| `raw_response_bytes` | Exact provider payload bytes (never normalized before hashing) |
| `content_sha256` | SHA-256 over `raw_response_bytes` |
| `provider_identity` | Vendor + feed (e.g. `ALPACA_SIP`) |
| `endpoint` | Full path (e.g. `/v2/stocks/{symbol}/bars`) |
| `parameters` | Exact query params (symbols, timeframe, adjustment, feed, sort, pagination tokens) |
| `retrieved_at_utc` | Timezone-aware retrieval instant |
| `canonical_session` | CA-1 session the payload is attributed to |
| `symbol_identity` | Ticker + product/CUSIP identity as returned |
| `timezone` | Wall-time zone of payload timestamps + UTC storage rule |
| `adjustment_mode` | `raw` (required) — adjusted payloads rejected for opening attribution |
| `pagination` | Page index, `next_page_token` chain to exhaustion proof |
| `error_or_missing` | Explicit `DATA_UNAVAILABLE` record incl. HTTP status / empty-page proof |

## 2. Evidence Kernel reuse assessment (RI-01 as prospective second consumer)

Reusable WITHOUT modification (candidate):
- Canonical JSON serialization (`CanonicalConfigSerializer.to_canonical_json`)
- SHA-256 content digest over raw bytes
- `DATA_UNAVAILABLE`-style fail-closed missing-data representation
- O_EXCL create-once registry semantics (for future intent/attempt ledgers)

NOT reusable as-is (gaps a future phase must close):
- HYP_011-specific chain/state schema (activation, recovery authority, ordinal
  ledger) — RI-01 needs its own coverage-ledger schema, not a fork of it.
- DispatchAuthority/intent binding shape (bound to HYP_011 ordinals/sessions).

**No extraction/refactor is performed here.** The finding is recorded so that
when RI-01 becomes a real consumer, only the proven-generic pieces are
lifted — behind their own tests, never by editing HYP_011 semantics.

## 3. Coverage ledger (future, not built)

Session × symbol × field availability table with per-cell evidence digest
references. A cell is `COVERED` only when its envelope exists and its digest
verifies; otherwise `DATA_UNAVAILABLE`. Coverage statistics are the ONLY
quantitative output authorized at feasibility stage — never returns.
