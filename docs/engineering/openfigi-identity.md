# OpenFIGI identity provider (candidates, never prices)

OpenFIGI answers one question — *which instrument is this?* — and nothing else. It is not a price,
FX, broker or execution provider, and it cannot change a valuation on its own.

## Credential and endpoint

- Windows Credential Manager target: `ACASH/IDENTITY/OPENFIGI_IDENTITY` (secret half holds the key).
- Configure it from `SETUP-MARKET-DATA.bat` → option 3 (hidden input, secure read-back).
- One HTTPS host: `api.openfigi.com`, one path: `POST /v3/mapping`.
- The key travels only in `X-OPENFIGI-APIKEY`; it is never a URL parameter, log line or JSON file.
- Local limiter plus batched jobs (100 per request, the documented authenticated maximum).

## Identity states

`NO_CANDIDATE` · `SINGLE_CANDIDATE` · `MULTIPLE_CANDIDATES` → `CANDIDATE_REVIEW_REQUIRED` →
`OWNER_CONFIRMED`, with `UNVERIFIED` whenever the evidence is missing or contradictory.

A single API hit is **not** Owner confirmation. `confirm_candidate()` only returns
`OWNER_CONFIRMED` when the Owner explicitly confirms and the FIGI belongs to the returned candidate
set. Ambiguous results never merge securities or change aggregation silently.

## Deliberately out of scope

- SCBSET50 (Thai mutual fund) and MTS-GOLD (gold, oz/USD) are not ordinary US equities and are not
  forced through OpenFIGI matching.
- No identity result feeds PPDS, the portfolio total or the provider-rights matrix.
- No private instrument universe is sent during a connectivity test: it uses the public ticker IBM.

## Gating

Installing the key does not authorise network use. The connectivity test runs only when the key is
present and the Owner selects it explicitly; automated tests use a synthetic key and a mocked POST
transport. A real OpenFIGI response remains `LIVE_NOT_OBSERVED` until the Owner runs that test.

## Conditional bulk review

`market_data/identity_review.py` turns candidate evidence into a reviewable decision without
auto-confirming anything:

- `AUTO_VALIDATED_CANDIDATE` — exactly one candidate, a valid `BBG` FIGI, a matching ticker, a venue
  and an instrument type, and no FIGI shared with another ticker.
- `REVIEW_REQUIRED` — ambiguous result, missing venue/type, or a non-single status.
- `BLOCKED_CONFLICT` — invalid FIGI, ticker mismatch, or a duplicate FIGI.

`confirm_bulk(path, revision, confirm=True)` accepts only the revision the Owner actually reviewed
(stale revisions fail closed), confirms only the auto-validated set, records the excluded tickers,
the timestamp and the previous revision, and writes atomically. Ambiguous or contradictory rows stay
out of the bulk action. Identity confirmation never changes quantities, prices, FX, cash or cost
basis, and a later API response cannot silently rewrite a confirmed mapping.
