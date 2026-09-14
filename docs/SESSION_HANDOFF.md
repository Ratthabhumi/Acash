# ACASH SESSION HANDOFF
## Shadow Alpha Tournament — Final Cross-Repo Merge / Deployment Readiness Gate

> **Document:** `docs/SESSION_HANDOFF.md`
> **This handoff is working context only.**
> Repository state is the source of truth.
> At the beginning of the next session:
> 1. `git fetch origin`
> 2. inspect actual remote branches
> 3. verify exact full 40-char SHAs
> 4. verify clean working trees
> 5. compare branches against current main
> 6. inspect canonical governance before consequential actions
>
> **Do not assume this handoff is newer than the repositories.**

---

## 1. Project Objective

ACASH is being extended with an isolated **Shadow Alpha Tournament**.

**Purpose:**
- consume REAL finalized market data
- run strategy logic, evaluate risk
- create SIMULATED order intents and fills
- maintain independent virtual portfolios
- collect journals / manifests / metrics
- show results through the existing custom ACASH Dashboard
- allow private mobile viewing over Tailscale
- allow normal ACASH research/development to continue without changing the running Homelab experiment

**This is NOT:**
- Paper Trading authorization
- Live Trading
- real capital
- backtest authorization
- HYP_003
- R1
- automatic alpha qualification

---

## 2. Immutable Governance

Unless the Human Operator explicitly changes governance:

| Boundary | State |
|---|---|
| G7 / S11 | PASS / CLOSED |
| Paper Trading | NOT AUTHORIZED |
| Live Trading | LOCKED |
| Backtesting | LOCKED |
| HYP_003 | NOT CREATED |
| R1 | NOT STARTED |
| Canonical Capital | $0.00 |
| NO_REAL_ORDERS | true |
| Shadow Tournament | SIMULATED / RESEARCH-INFRA ONLY |
| Dashboard | READ ONLY |
| Public Internet | DISABLED |
| Automatic Code Sync | DISABLED |
| Automatic Feed Reconnect | DISABLED |
| Operator Resume | REQUIRED |

**Do not reinterpret Shadow Tournament as Paper GO.**

---

## 3. ACASH Repository — Current Expected State

```
Repository:  Ratthabhumi/Acash
Branch:      feature/shadow-alpha-tournament
HEAD:        e17b3893e19ba3ce25530daf764ca7964cb0c755
Main base:   638388e38f721b49cab2621532b04757d6d85586
```

**Expected lineage:**
```
638388e  (main base)
   ↓
c621824
   ↓
9e4aa9f
   ↓
5a7bbac
   ↓
e17b389  <- current HEAD
```

- ahead of main = 4 | behind = 0 | FF-able
- working tree clean | remote branch synchronized

**VERIFY, do not assume.**

---

## 4. ACASH Work Completed

### `c621824` -- Initial Shadow Tournament
- Tournament supervisor, independent strategy slots A/B/C
- $1,000 virtual NAV concept
- Custom Shadow Tournament dashboard page
- Mock/live dashboard repository abstraction, contracts, container artifacts

### `9e4aa9f` -- First Integration Gaps
- `PaperStrategyProtocol`, strategy dependency injection
- Read-only Shadow API, tournament CLI / runtime entrypoint
- Production mock fail-closed behavior
- Unique session IDs, halt lifecycle, manifest sealing
- API + metrics wiring, path-prefix-ready dashboard build

### `5a7bbac` -- Major Runtime / Deployment Correctness
- `feed.connect()` / `feed.disconnect()` lifecycle
- Real-feed provenance: `data_source`, `market_domain`, max market data age
- Feed freshness monitoring
- Strategy evidence classification seam + dynamic manifest classification
- `/acash/` dashboard API resolution
- Eliminated stale hard-coded git SHA behavior

### `e17b389` -- Final Stale-Returned-Bar Blocker

Previous bug:
```
poll_next_bar() -> returned stale FeedBar -> process_bar()
-> global tournament could remain RUNNING
```

Fixed behavior:
```
poll_next_bar()
      |
freshness gate  (FeedBar.data_age_ms() > max_data_age_ms)
      |
if stale -> HALT -> seal manifests -> export status -> exit code 4
            DO NOT call process_bar()
      |
only fresh bars reach process_bar()
```

Added adversarial integration test:
`tests/integration/test_shadow_tournament_runtime.py::test_runtime_returned_stale_bar_halts_before_processing`
Patches `process_bar()` to raise `AssertionError` if called for a stale returned bar.

---

## 5. Latest Reported ACASH Verification

Reported by prior session against exact `e17b389`, clean working tree:

| Check | Result |
|---|---|
| Shadow runtime integration tests | 4 / 4 PASS |
| Full Python suite | 2262 passed, 1 skipped, 0 failures |
| MyPy new errors in changed files | 0 |
| MyPy pre-existing unused-ignore (unrelated files) | 6 (compatibility debt) |
| ACASH working tree | clean |
| ACASH local HEAD | `e17b389` |
| ACASH remote HEAD | `e17b389` |

> Do not silently convert these into new verified results.
> Re-run relevant final-gate checks as required.

---

## 6. Pi Personal Infrastructure -- Current Expected State

```
Repository:  Ratthabhumi/Pi_Personal-Infrastructure
Branch:      feature/acash-shadow-tournament-deploy
Last known HEAD (before e17b389 ACASH commit):
             4f06b3836224c208454c3494b406e4740856ce3d
Main base:   68142aecdccf636912902bbfc4061895c877d195
```

> **CRITICAL:** Pi branch still references ACASH commit `5a7bbacf5d5ee401a531247e723fc3fa12a59030`.
> It **MUST** be updated to `e17b3893e19ba3ce25530daf764ca7964cb0c755`
> before final merge/deploy review.
> **This is the first remaining technical task.**

---

## 7. Immediate Next Task -- Update Pi Provenance

On branch `feature/acash-shadow-tournament-deploy`:

1. Inspect actual `docker/compose.yaml`
2. Update all Shadow Tournament ACASH provenance references:

```
Old SHA: 5a7bbacf5d5ee401a531247e723fc3fa12a59030
New SHA: e17b3893e19ba3ce25530daf764ca7964cb0c755
```

Fields to update (at minimum):
- `acash-dashboard` image tag
- `acash-shadow` image tag
- `ACASH_GIT_COMMIT` environment variable
- `--git-commit` CLI argument

Use **actual current file contents**. Do NOT invent image digests before an actual Docker build.

Commit rules: normal follow-up commit / no amend / no rebase / no force push / push the branch / return full new Pi commit SHA.

---

## 8. Pi Architecture That Should Already Exist

**Verify rather than recreate.**

### Dashboard (`acash-dashboard`)
- read-only filesystem; writable nginx tmpfs only where required
- no Watchtower / no public application port / attached to proxy

| Access | URL |
|---|---|
| LAN | `https://acash.mew.lab` |
| Tailscale | `https://homelab.tail35e4b4.ts.net/acash/` |

Redirect: `/acash` -> `/acash/`

Traefik rule:
```
Host(`homelab.tail35e4b4.ts.net`) && PathPrefix(`/acash`)
-> strip /acash before forwarding to nginx
```

API routing:
```
Browser   /acash/api/shadow/status
Traefik   strip /acash
Nginx     /api/shadow/status
Proxy     http://acash-shadow:9103/api/shadow/status
LAN       /api/shadow/status  (root-host mode)
```

---

## 9. Shadow Runtime Service (`acash-shadow`)

```yaml
user: "10001:10001"
read_only: true
security_opt:
  - no-new-privileges:true
environment:
  NO_REAL_ORDERS: "true"
  CANONICAL_CAPITAL_USD: "0"
restart: "no"
```

- No broker credentials / no host-published trading ports / Watchtower disabled
- Networks: `proxy`, `acash_staging` (internal)
- Persistent evidence: `/data/docker/acash/tournament`
- Internal ports: `9102` metrics, `9103` read-only Shadow API

---

## 10. H01 Start Interlock -- Critical

`acash-shadow` **must** remain behind:

```yaml
profiles:
  - "acash-shadow"
```

Normal `docker compose up -d` **MUST NOT start Shadow runtime.**

Shadow runtime requires explicit Human H01:
```bash
docker compose --profile acash-shadow up -d acash-shadow
```

**Do not execute without explicit Human authorization.**

---

## 11. VictoriaMetrics

Verify existing scrape job:

```yaml
- job_name: 'acash-shadow'
  static_configs:
    - targets: ['acash-shadow:9102']
      labels:
        tier: 'execution-infrastructure'
        mode: 'shadow-tournament'
```

Do not remove existing `acash-staging:9102` -- both must coexist.
Verify VictoriaMetrics shares a network with `acash-shadow`.

---

## 12. Final Cross-Repo Review

After updating Pi provenance, perform ONE final merge-gate review.

### ACASH -- verify:
- [ ] branch ahead = 4, behind = 0
- [ ] merge base = current main
- [ ] exact changed files, no unexpected governance files
- [ ] feed connects before slots start
- [ ] no automatic reconnect
- [ ] returned stale bar halts **before** strategy evaluation
- [ ] None-poll stale condition also halts
- [ ] real-feed provenance correct
- [ ] strategy injection remains isolated
- [ ] infra strategy labeled `INFRASTRUCTURE_TEST_STRATEGY_ONLY`
- [ ] future approved alpha representable without false infra classification
- [ ] API is read-only
- [ ] production dashboard cannot silently use mock
- [ ] unique evidence/session paths
- [ ] halt seals manifests

### Pi -- verify:
- [ ] exact ACASH SHA = `e17b3893e19ba3ce25530daf764ca7964cb0c755`
- [ ] H01 profile exists on `acash-shadow`
- [ ] normal Compose launch excludes Shadow runtime
- [ ] Tailscale route is private (no Funnel / public exposure)
- [ ] dashboard routes API correctly
- [ ] Watchtower disabled for ACASH components
- [ ] persistent evidence mount present
- [ ] no trading credentials
- [ ] VictoriaMetrics scrape exists
- [ ] Compose parses cleanly

---

## 13. Final Verification Commands

### ACASH
```bash
uv run pytest tests/unit/paper -q
uv run pytest tests/integration/test_phase14_e35_real_feed_integration.py -q
uv run pytest tests/integration/test_shadow_tournament_runtime.py -q
uv run mypy src/ tests/
git diff --check
```

If the complete suite was freshly executed against exact `e17b389` with no subsequent working-tree changes, preserve that evidence and state exactly what was re-run now versus reused.

### Dashboard
```bash
cd dashboard
npm ci
npm run typecheck
npm test
npm run build
```

### Pi
```bash
docker compose -f docker/compose.yaml config --quiet
docker compose -f docker/compose.yaml config --services
docker compose -f docker/compose.yaml --profile acash-shadow config --services
```

Expected:
- default service set **excludes** `acash-shadow`
- profile service set **includes** `acash-shadow`

---

## 14. Docker / Homelab Caveat

Previous Windows workstation did NOT have Docker daemon running. Therefore:
- Compose syntax was validated
- Python runtime was integration-tested with mocked feed
- **Actual Linux container build/start has NOT yet been proven**

Do not claim actual container runtime verification until performed on `mew@homelab`.
This is acceptable as a PRE-DEPLOY verification gate.

---

## 15. If Final Review Passes

Return **`SAFE TO MERGE`** -- but do **NOT** merge unless explicit Human authorization is present.

**Recommended next Human-controlled sequence:**
1. FF merge ACASH branch
2. FF merge Pi branch
3. On `mew@homelab`: build exact commit-derived images, verify image IDs/digests, run container smoke validation
4. Deploy dashboard + monitoring only
5. Verify: LAN UI, Tailscale mobile UI, Shadow API route, VictoriaMetrics topology
6. **STOP -- await H01 before starting `acash-shadow`**

---

## 16. Important -- Alpha Slots

Current real approved Alpha candidates = **0**

- Do not invent strategies to fill A/B/C
- `InfrastructureTestStrategy` for infrastructure verification only -- must remain labeled `INFRASTRUCTURE_TEST_STRATEGY_ONLY`
- It is NOT HYP_003, qualified alpha, or admissible research evidence
- B/C may remain `UNASSIGNED` until Human strategy selection

---

## 17. Research Track Remains Separate

Research critical path still involves D17 / data-authority decisions.

Do **NOT** let Shadow deployment silently:
- unlock backtesting
- create HYP_003
- start R1
- qualify strategy
- authorize Paper or Live

Research/dev can continue independently after Shadow runtime is deployed. No automatic runtime code synchronization from main.

---

## 18. Final Report Format

```
Repository State
  ACASH:
    main:
    branch:
    HEAD:
    ahead:
    behind:
    merge base:
    working tree:
  Pi:
    main:
    branch:
    HEAD:
    ahead:
    behind:
    merge base:
    working tree:

Verification
  Python unit:
  Real-feed integration:
  Shadow integration:
  MyPy:
  Dashboard typecheck:
  Dashboard tests:
  Dashboard build:
  Compose:
  Default profile interlock:
  Shadow profile:

Findings
  Classify only: BLOCKER | MAJOR | MINOR | NONE

Merge Verdict
  SAFE TO MERGE
  or
  HOLD -- DO NOT MERGE

Human Actions Remaining
  H05   -- Merge authorization
  BUILD -- Homelab Docker build/digest verification
  DEPLOY -- Dashboard/monitoring deployment authorization
  H01   -- Shadow runtime START authorization
  H02   -- Strategy candidate selection
  BACKTEST -- Future research authorization
  (only actions actually requiring Human authority)
```

---

## 19. Stop Rule

Even if final merge gate passes -- **DO NOT:**
- start `acash-shadow`
- authorize Paper or Live
- unlock backtest
- create HYP_003
- start R1
- modify capital
- add auto reconnect
- connect a real broker

without **explicit Human authorization**.

**Final desired state before Human returns:**

| Item | State |
|---|---|
| IMPLEMENTATION | READY |
| PI PROVENANCE | UPDATED |
| FINAL REVIEW | COMPLETE |
| MERGE | AWAITING HUMAN |
| DEPLOY | AWAITING HUMAN |
| SHADOW START | AWAITING H01 |
| REAL CAPITAL | $0.00 |
| REAL ORDERS | 0 |
