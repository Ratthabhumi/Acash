# HYP_011 Prospective Shadow — Pre-Observation Contract Correction

Base: `8ae1589` (atomic engine finalization). Zero price data accessed by this
correction (unit + mocked-client tests only). Observed count remains 0.

## Defects corrected (all fail-closed, no silent fallback)

### A. Authorization-string ambiguity
Runner accepted any `--authorization` string so long as the ordinal integer
matched. Now the authorization is derived and compared exactly:
`AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_{ordinal:04d}`.
Any deviation raises `SHADOW_AUTHORIZATION_STRING_MISMATCH` pre-network.
(`scripts/process_hyp_011_prospective_shadow.py`)

### B. First-state incompleteness + session-one CA claim
- `verify_chain` on an absent `state.json` returned a bare
  `{observed_sessions: [], ...}` dict with no identity, no balances, no
  benchmark, no locks. Now it returns `build_initial_state()`: schema v1,
  `HYP_011`, activation `2026-09-28`, AUM `100000.00`, all-cash strategy,
  un-entered benchmark, and `paper/live=False, capital 0.00, no_real_orders`.
- `verify_chain` re-validates identity fields (`schema_version`,
  `hypothesis_id`, `activation_session`, `starting_aum`, `locks`) on every
  present state, and requires complete economic state once sessions exist.
- `append_observation` stamps identity fields + locks on every seal (empty or
  existing state), so the chain can never degrade to a partial doc.
- Session one no longer records `{"has_event": False}` (an existence claim
  without an authority lookup). It records
  `{"status": "CA_NOT_ECONOMICALLY_REQUIRED_NO_PRIOR_HOLDINGS"}`.
- `validate_initial_state()` enforces the pristine pre-observation invariants
  (empty ledger, zero count, all-cash strategy, un-entered benchmark, locks).
  (`src/acash/research/hyp_011/shadow_ops.py`)

### C. CA schema duality + receivable provenance gap
- Canonical determination keys are `amount_per_share` / `source_sha256`
  (`CADetermination`). The legacy `amount` / `authority_sha` spellings are
  rejected at the schema boundary (`SHADOW_CA_FIELD_MISMATCH`), never
  silently coerced.
- `CADetermination.from_dict()` is the single parsing authority for runner
  CA files: symbol/session/sponsor binding, timezone-aware retrieval
  timestamp not in the future, 64-hex source SHA, boolean `has_event`,
  strictly-positive event amount.
- Entitlements and receivables now carry the full provenance tuple
  `(symbol, ex_date, payable_date, amount, authority_source, authority_sha)`;
  entitlement requires whole-share ownership and strict ex-date precedence
  over acquisition (`SHADOW_PRIOR_CLOSE_*`, `SHADOW_SPLIT_EX_PRECEDENCE`).
- Session-one `MockSponsorAuthorityAdapter` seeding removed: no fake
  authority lookup on a session with no prior holdings. Sponsor mapping
  (`BLACKROCK_ISHARES_OFFICIAL`, `STATE_STREET_SPDR_OFFICIAL`) and
  session N≥2 retrieval ordering (`CA_LOOKUP_AFTER_CLOSE_UTC`,
  `CA_RETRIEVAL_BEFORE_PROCESSING`) are unchanged.
  (`src/acash/research/hyp_011/shadow_ca.py`,
  `src/acash/research/hyp_011/shadow_ops.py`,
  `scripts/process_hyp_011_prospective_shadow.py`)

### D. Derived trigger made explicit
- `EXPECTED_SESSION_OPEN_US = 13:30 UTC` bound in
  `src/acash/research/hyp_011/shadow.py`; the zero-network pretest dry-run
  now validates local contracts and prints
  `expected_next=<session> expected_open_utc=<ts>`, flagging a pre-trigger
  invocation explicitly. No network is issued in dry-run mode.

## Verification
- `uv run pytest`: 3232 passed, 1 skipped (full suite, second run).
- `uv run mypy src/ tests/`: clean, 549 files.
- `git diff --check`: clean.
- Warnings: 3 pre-existing dependency-compat items
  (`Pandas4Warning` in `nautilus_bridge.py`, pydantic serializer notices);
  none originate from changed files — accepted debt, not introduced here.
- No observation artifacts created; no network issued; state count 0.
