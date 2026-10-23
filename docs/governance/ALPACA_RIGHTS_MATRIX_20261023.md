# Alpaca Data Rights Matrix (Evidence-Bounded)

**Date:** 2026-10-23
**Status:** `EVIDENCE_BOUNDED_RIGHTS_MATRIX`
**Acquisition status:** `UNISSUED`
**Real-data admission:** `NOT_ADMITTED`

This matrix separates what ACASH has actually observed from what it has not. It is not
legal advice and it does not replace a written provider answer. No row below authorizes
a request, credential use, raw-data retention or redistribution.

## 1. Evidence Base

- `docs/phase14/HYP_009_R2_LIVE_PROVIDER_QUALIFICATION_RESUME.md`: prior account
  authentication and SIP access passed; 2 HTTP attempts; 4/4 sessions.
- `docs/phase14/HYP_009_R2_M1_DATA_QUALIFICATION.md`: 2 requests returned 1,259 split
  bars and 1,259 raw bars; zero missing, duplicate or extra sessions; dataset SHA-256
  `1dc231d9eb36c8f0a2ebd0b8b4f5d20b8bca343eed406b3b11a5744fc7cc8ba7`.
- `docs/phase14/manifests/HYP_009_R2_M1_DATASET.json`: recorded dataset identity.
- Public Alpaca documentation reviewed 2026-10-14: inclusive `start`/`end`,
  `next_page_token` pagination, page `limit` counts total observations, explicit
  `feed`/`adjustment`, Basic USD 0 historical coverage since 2016, and a recent-data
  delay guard.

The HYP_009 evidence proves historical retrieval for that prior account and window. It
does **not** prove the current account tier, current token scope, current 2026 access,
raw-retention permission, derived-use permission, redistribution permission or PIT
vintage policy.

## 2. Eight-Dimension Matrix

| # | Dimension | Status | Evidence / limitation |
| :--- | :--- | :--- | :--- |
| 1 | Historical bars retrieval mechanics | `PROVEN` | Prior 2-request M1 retrieval with pagination and raw/split series; public API contract. |
| 2 | SIP feed entitlement | `PROVEN_WITH_LIMITATIONS` | Prior SIP access passed; not rechecked against the current account or 2026 entitlement. |
| 3 | Historical window 2016-2020 | `PROVEN_WITH_LIMITATIONS` | 1,259-bar HYP_009 window recovered; this is not a full multi-year ETF study and not 2026 access. |
| 4 | Current account tier / 2026 access | `UNKNOWN` | No current credentials or account-specific written confirmation in scope. |
| 5 | Raw response retention / archival | `UNKNOWN` | No written provider permission establishing permanent raw storage. |
| 6 | Derived internal research use | `PROVEN_WITH_LIMITATIONS` | Analytical use of returned data is contemplated by research use, but no account-specific written grant. |
| 7 | Redistribution / external sharing | `PROVEN_WITH_LIMITATIONS` | Public terms restrict redistribution; no permission to publish or share raw or derived data. |
| 8 | Corporate actions, adjustment and PIT vintage | `PROVEN_WITH_LIMITATIONS` | Raw/split bars are retrievable; issuer/sponsor corporate-action authority and PIT vintage remain separate. |

Summary: **1 `PROVEN`, 5 `PROVEN_WITH_LIMITATIONS`, 2 `UNKNOWN`, 0 `DENIED`.**

## 3. What Each Status Means

- `PROVEN`: directly evidenced for the recorded scope.
- `PROVEN_WITH_LIMITATIONS`: directly evidenced only within a narrower recorded scope,
  or subject to an unresolved written-permission question.
- `UNKNOWN`: not evidenced either way.
- `DENIED`: an authoritative source explicitly refuses the use.

`UNKNOWN` is not permission. `PROVEN_WITH_LIMITATIONS` is not a general license.

## 4. Required Operator Actions

Before any real acquisition, the operator must obtain and retain a written answer
covering, at minimum:

1. Current plan/tier and the exact historical window available to this account.
2. Whether SIP and/or IEX is authorized for the intended ETF universe.
3. Whether raw responses may be retained, for how long, and under what access controls.
4. Whether derived research outputs may be stored and used internally.
5. Whether any raw or derived data may be shared externally.
6. The applicable adjustment, corporate-action and point-in-time vintage policy.

Until those answers exist, the only truthful state is `UNKNOWN` and the Lane A/B
authorities remain `UNISSUED`.

## 5. Boundaries

No provider request, credential use, subscription purchase, protected dataset access or
raw-data retention is authorized by this matrix. Capital authority remains USD 0.00 and
`NO_REAL_ORDERS=true`.
