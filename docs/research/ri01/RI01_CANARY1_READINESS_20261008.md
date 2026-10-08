# RI01 Canary 1: prepared, empirical acquisition not authorized

Software checkpoint: PR #12, runtime `cf63f15800099967f4c45d3df66e87a66a012eac`.
This is an additive readiness checkpoint, preserving the historical
[R1 design](RI01_PROBE_R1_DESIGN.md). It does not ratify network access.

## Candidate and contract

The exact [unissued candidate](RI01_CANARY1_UNISSUED_AUTHORITY.json) deliberately
has an invalid authority prefix and unresolved UTC windows. The executable
parser rejects it. An operator must approve a unique issued identity, exact
runtime SHA, resolved external root and bounded future window separately.
The proposed Windows root is external configuration, not a repository reference;
another OS requires an explicitly reviewed root substitution. Do not create or
reuse an occupied root. The harness writes immutable pages and manifests; a
root collision is a stop, never permission to delete or overwrite evidence.

Scope: SPY, session 2021-06-01, historical 1Min SIP bars, raw adjustment,
NYSE RTH `[2021-06-01T13:30:00Z, 2021-06-01T20:00:00Z)`, 390 distinct grid
positions, request budget 3. No returns, PnL, Sharpe, signals, predictive tests,
lookahead, sealed 2023+ holdout, automatic retry, interpolation or missing-bar
fabrication. Success measures data availability for this endpoint/session/account
only; it cannot establish predictive value or broad historical coverage.

Request: GET `https://data.alpaca.markets/v2/stocks/bars` with `symbols=SPY`,
`start=2021-06-01T13:30:00+00:00`, `end=2021-06-01T20:00:00+00:00`,
`timeframe=1Min`, `feed=sip`, `adjustment=raw`, `sort=asc`, `limit=1000`.
Follow only returned page tokens until exhausted, bounded by 3 invocations.
Alpaca documents the request end as inclusive; consumer qualification selects
the exclusive-close RTH grid. A returned 20:00 bar is preserved in raw retrieval
but excluded from qualified RTH bars; retrieved and qualified counts can differ.
Do not assume one page or assume request invocation proves provider receipt.
Credentials are loaded from the existing environment provider; never paste
values into this document, authority JSON, terminal history or evidence files.

## Observed evidence taxonomy

| Observation | Retrieval evidence | Qualification / interpretation |
|---|---|---|
| 200, exhausted pages, exact 390 grid | RETRIEVED | QUALIFIED |
| 200, no bars | RETRIEVED | DATA_UNAVAILABLE |
| 200, incomplete/duplicate/off-grid or invalid bar | Contract failure | Inspect actual raw evidence and qualification where emitted; never call covered |
| 401 | AUTHENTICATION_FAILED | Credential rejection; no entitlement inference |
| Generic 403 | ACCESS_FORBIDDEN | Reason unconfirmed |
| 403/422 + allowlisted code 42210000 or 40010001 + exact SIP restriction message | ENTITLEMENT_DENIED | Confirmed recent SIP subscription restriction only |
| Generic 422 or other non-200 | HTTP_FAILED | No detailed reason inferred |
| Invalid response structure/JSON | MALFORMED_RESPONSE where handled | Not qualified |
| RequestError, including timeout/connect/read | TRANSPORT_FAILED | Invocation initiated, provider acceptance UNKNOWN, no response observed for failed invocation |
| Pagination still incomplete at budget | PARTIAL | Stop; no automatic retry or budget extension |

Successful retrieval and consumer qualification are distinct. Some existing
per-bar validation exceptions occur before qualification or a terminal manifest;
operators must treat any raw-page-only run as **INCOMPLETE_EVIDENCE**, never
success, and retain it for inspection. This pack does not claim all possible
provider corruption paths produce a complete terminal artifact.

Official sources reviewed 2026-10-08:
[historical bars](https://docs.alpaca.markets/us/reference/stockbars),
[Market Data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq),
[official error guide](https://alpaca.markets/learn/how-to-fix-common-trading-api-errors-at-alpaca).
The FAQ's example is a recent SIP restriction, not proof that this account can
retrieve 2021 SIP. Code 42210000 alone is ambiguous; both code and exact
allowlisted message are required. Arbitrary error bodies are not persisted.

## Operator runbook (review only; network command not executed)

1. Explicitly authorize **only** this Canary 1 scope and budget after reviewing
   PR #12 and its post-merge CI. Use an isolated checkout of the exact candidate
   SHA, outside the armed Homelab checkout. Do not pull/restart Homelab.
2. Review the resolved external root for repository/HYP011/symlink collision,
   uniqueness and permissions. Use the existing `validate_external_evidence_root`;
   do not modify its protected-path policy or store credentials with evidence.
3. Copy the candidate outside the repo; operator issues a unique
   `AUTHORIZE_RI01_PROBE_R1_...` ID and explicit timezone-aware UTC validity window.
   Preserve a record of human approval, runtime and authority digest. The hash
   binding is not a PKI signature and does not authenticate the human by itself.
4. Confirm checkout SHA and clean diff; load credentials through the existing
   local secret mechanism. A different runtime requires a reviewed re-binding,
   not editing the JSON merely to bypass the check.
5. Run the scope-only dry run (no authority/credential/HTTP validation):

   ```powershell
   uv run python -m acash.research.ri01.probe --session 2021-06-01 --capability bars
   ```

6. Only after separate human network approval, the exact proposed command is:

   ```powershell
   uv run python -m acash.research.ri01.probe --execute-network --authority-file C:/ACASH-Evidence/ri01/authority-canary1-issued.json
   ```

   This command is **unexecuted**. It must run from the isolated checkout pinned
   to `cf63f15800099967f4c45d3df66e87a66a012eac`, not whichever main is newest.
7. Preserve raw bytes; recompute each page SHA with `content_sha256`, ordered
   chain with `ordered_page_chain_digest`, and manifest with
   `canonical_manifest_sha256`. Decode via `RetrievalRunManifest.from_dict`.
   Check authority hash/runtime binding, token continuity, operation count <=3,
   exhausted pagination, immutable files and exact grid qualification using the
   existing `require_complete_rth_grid`. `RETRIEVED` alone is insufficient.
8. Report observed statuses and invocation count even on failure. Any missing
   terminal/qualification evidence is incomplete. Stop after this session;
   do not escalate to trades, older sessions or outcomes without another decision.

Readiness verdict: **SOFTWARE_READY_FOR_OPERATOR_REVIEW**; real SIP feasibility
**UNVERIFIED**, network authority **UNISSUED**, live requests in this task **0**.
