# Phase 14 HYP_009: R2 Live Provider Qualification Outcome

```text
[QUALIFICATION RECORD: HYP_009 R2 LIVE PROVIDER PROBE OUTCOME]
[ARTIFACT_ID: HYP_009_R2_LIVE_PROVIDER_QUALIFICATION]
[STARTING_GIT_SHA: 0c4fe751f95c395062c3484a8d6826ffd297a2cd]
[HYPOTHESIS_ID: HYP_009]
[CORE_ID: CORE-001]
[SCIENTIFIC_STATUS: UNMODIFIED / INTACT]
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_R2_LIVE_PROVIDER_QUALIFICATION]
[CLASSIFICATION: BLOCKED_PRE_ENTITLEMENT_CHECK_MISSING_CREDENTIALS]
[NETWORK_REQUESTS_ISSUED: 0]
[LIVE_PROVIDER_QUALIFICATION_PERFORMED: false]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/HYP_009_R2_LIVE_PROVIDER_QUALIFICATION.md`
- **Associated Manifest:** `docs/phase14/manifests/HYP_009_R2_LIVE_PROVIDER_QUALIFICATION.json`
- **Governing Standard:** ACASH `AGENTS.md` (Zero Unverified Claims, Strict
  Fail-Closed).
- **Scope:** frozen tiny live probe ONLY (SPY 1Day SIP, split+raw,
  2016-11-01..2016-11-04). No M1 acquisition, no dataset sealing, no strategy
  execution, no P&L, no M2/M3/quarantine/prospective access, no paper/live,
  no capital.

---

## 1. Frozen Contract (Verified Unchanged Before the Run)

| Field | Value |
| :--- | :--- |
| CORE / HYPOTHESIS | CORE-001 / HYP_009 |
| symbol / timeframe / feed | SPY / 1Day / sip |
| Request A adjustment | split |
| Request B adjustment | raw |
| Scientific probe sessions | 2016-11-01, 2016-11-02, 2016-11-03, 2016-11-04 |
| Authorized R2 window | 2016-01-01 .. 2020-12-31 inclusive |
| Provider start UTC | 2016-11-01T00:00:00Z |
| Provider end UTC | 2016-11-04T23:59:59.999999Z |

---

## 2. Credential Precheck (Booleans Only — No Values Recorded)

```text
KEY_ID_PRESENT = False
SECRET_PRESENT = False
```

No API keys, secrets, headers, or secret-bearing dumps appear in any artifact.

---

## 3. Runner Execution (Exact Command, No Substitution)

```text
uv run python scripts/execute_hyp_009_r2_provider_qualification.py --execute-network
```

No curl/httpx reproduction. No HYP_003/HYP_005/HYP_006/HYP_007 runners.

### 3.1 First attempt (Windows console encoding observation)

The runner engaged its fail-closed credential gate correctly (zero network),
but verdict printing crashed with
`UnicodeEncodeError: 'charmap' codec can't encode character '\xa7'`
because the credential error message cites contract `§6 C-4`
(`src/acash/execution/alpaca/credentials.py`) and this machine's console
charmap lacks `§`. Exit code was 1 via the runner's generic error path.
**No code was changed in response** (mid-flight repair is forbidden); the run
was repeated with `PYTHONUTF8=1`, an environment-level invocation setting
that alters no qualification semantics.

### 3.2 Authoritative run output

```text
Probe sessions: 2016-11-01 .. 2016-11-04 inclusive
Provider start UTC: 2016-11-01T00:00:00+00:00
Provider end UTC:   2016-11-04T23:59:59.999999+00:00
Authorized window: 2016-01-01 .. 2020-12-31
Network Execution Flag: True
Git HEAD: 0c4fe751f95c395062c3484a8d6826ffd297a2cd
CREDENTIAL_KEY_PRESENT = False
CREDENTIAL_SECRET_PRESENT = False
VERDICT = BLOCKED_MISSING_CREDENTIALS (AlpacaCredentialProvider: API key id
is absent; refusing to construct a credential handle (fail-closed, §6 C-4).)
NETWORK_REQUESTS_ISSUED = 0
Exit code: 2
```

---

## 4. Classification (§6 rules + §3 pre-entitlement rule)

```text
BLOCKED_PRE_ENTITLEMENT_CHECK_MISSING_CREDENTIALS
```

Runner verdict string: `BLOCKED_MISSING_CREDENTIALS` (same terminal meaning
under the §3 rule). This is **not** hypothesis falsification, not a provider
authentication failure against live credentials, not an entitlement denial,
and not a data-contract violation — the probe never reached the network
because no credentials exist in this execution environment. Per §11: strategy
specification, gates, provider, dates, and feed are all unaltered; no
fallback, no IEX, no substitution attempted.

Success-shape fields (split/raw rows, session sets, spill/duplicate counts,
alignment) are **not applicable**: zero requests were issued, so no values
are recorded or fabricated.

---

## 5. State & Boundary Invariants

```text
M1_FULL_ACQUISITION_EXECUTED = false
M2_ACCESS_COUNT = 0
M3_ACCESS_COUNT = 0
QUARANTINE_ACCESS_COUNT = 0
PROSPECTIVE_ACCESS_COUNT = 0
HYP_007_EMPIRICAL_READ_COUNT = 0
HYP_003_SCIENTIFIC_FILES_MODIFIED = NO
HYP_003_RUNNER_EXECUTED = NO
NETWORK_REQUESTS_ISSUED = 0
LIVE_PROVIDER_QUALIFICATION_PERFORMED = false
PAPER_AUTHORIZED = false
LIVE_AUTHORIZED = false
CAPITAL_AUTHORITY_USD = 0.00
NO_REAL_ORDERS = true
```

Known minor robustness note (no repair made in this task): runner verdict
printing assumes the console can encode exception text (contract citations
contain `§`). A future authorized round may render verdicts ASCII-safe.

Next human action: provide HYP_009 R2 Alpaca credentials in the execution
environment and re-authorize the live provider probe; full M1 remains a
separate later gate.

---

## 6. Manifest Digests (Verification)

| Artifact | Digest |
| :--- | :--- |
| Manifest canonical payload (`canonical_payload_sha256`, repo convention) | `c9c8ae6b98a5ddb0b12e200c696e1a11286f8f32e65b3e07f5b629a7f1f4b6d7` |
| Manifest file `docs/phase14/manifests/HYP_009_R2_LIVE_PROVIDER_QUALIFICATION.json` | `c5d4321680db12eb08957258a0a83666d7386153ea84ad96ed5795b153ddc22a` |
