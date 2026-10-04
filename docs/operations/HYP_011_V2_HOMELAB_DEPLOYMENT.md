# HYP_011 V2 Homelab Deployment Runbook

**Status**: `PREPARATION_ONLY` — NOT DEPLOYED, NOT ACTIVATED
**Branch**: `fix/hyp011-v2-activation-safety-20261004`
**Base**: `origin/main` @ `5e1eb1877e2a9106bd0673bd7f8331bf54fab1a9`

> SHA rule: this document NEVER pins a deployment commit. The exact runtime
> commit is bound by the deployment authorization as `APPROVED_RUNTIME_SHA`
> AFTER the correction PR merges. Any `APPROVED_RUNTIME_SHA` below is a
> placeholder filled at authorization time, never a hardcoded SHA.

---

## 1. Authority Model (Two Explicit Separate Authorities)

### Authority A: `AUTHORIZE_HYP_011_V2_CANONICAL_DEPLOYMENT`
**Allows**:
- Create `/var/lib/acash/hyp011/v2/` state directory (700, owned by mew:mew)
- Install the wrapper as `/usr/local/sbin/acash-hyp011-v2` (0755, root:root)
- Install the SERVICE ONLY: `/etc/systemd/system/acash-hyp011-v2.service`
- Create secrets file: `/etc/acash/hyp011-v2.env` (600, owned by mew:mew)
- Run zero-network deployment preflight (`--deployment-preflight`)

**Does NOT allow**:
- Install/enable/arm any timer (no triggerless timer may enter systemd)
- chmod or otherwise mutate the tracked repository checkout
- Create ObservationIntent / SegmentActivationAuthority
- Choose activation session
- Issue `--execute-network` calls
- Paper/Live orders
- Real capital

### Authority B: `AUTHORIZE_HYP_011_V2_ACTIVATION_<SESSION>`
**Allows** (for a specific prospective session):
- Create SegmentActivationAuthority + RegisteredIntent for target session
- Create DispatchAuthority bound to intent + runtime + CA evidence
- Generate + install the timer for that exact session (template + validated trigger)
- Arm timer for that specific session (pre-arm dispatch preflight is NOT run — the session is still open)
- Rely on the elapse-time ExecStartPre gate for the full zero-network dispatch preflight (`--local-preflight` with authorities)
- Execute live observation with `--execute-network` (only if ExecStartPre passed at elapse)

**Requires**: Authority A already completed

**Does NOT allow**:
- Backfill
- Automatic retry (failed dispatch = new Authority B required)
- Automatic skip to later session

---

## 2. Deployment Prerequisites

### Repository State
```bash
# On homelab. APPROVED_RUNTIME_SHA comes from
# AUTHORIZE_HYP_011_V2_CANONICAL_DEPLOYMENT (bound after the correction PR
# merges) — never hardcode a commit from an older doc revision here.
cd /home/mew/Acash
git fetch origin main
test "$(git rev-parse origin/main)" = "$APPROVED_RUNTIME_SHA"
git merge --ff-only origin/main
test "$(git rev-parse HEAD)" = "$APPROVED_RUNTIME_SHA"
git status --short --branch  # clean
```

### Python Runtime Pin
- **Declared Range** (`pyproject.toml`): `requires-python = ">=3.12,<3.15"`
- **CI Matrix** (`.github/workflows/ci.yml`): 3.12, 3.13, 3.14 (all green required)
- **MyPy Target** (`pyproject.toml [tool.mypy]`): `python_version = "3.14"`
- **Locked Dependencies**: `uv sync --locked` from `pyproject.toml` + `uv.lock`
- **Chosen V2 Interpreter**: `<repo>/.venv/bin/python` created by `uv sync --locked`
  (observed 3.14.x on current environments; the contract pins the *venv binary path*,
  not a hardcoded `3.14` minor — the venv is always rebuilt from the lockfile)
- **Rationale**: No implicit `python3`/`uv run` interpreter drift between CI and
  homelab; the wrapper binds the venv binary explicitly. Homelab system python
  (observed 3.12.3) is never used for V2 execution.
- **No installation** in this task: no Homelab Python changes authorized.

### External State Root
```bash
# Created ONLY under Authority A
sudo mkdir -p /var/lib/acash/hyp011/v2
sudo chown mew:mew /var/lib/acash/hyp011/v2
sudo chmod 700 /var/lib/acash/hyp011/v2

# Subdirectories created by first runner invocation:
# /var/lib/acash/hyp011/v2/observations/
# /var/lib/acash/hyp011/v2/intent_registry/
# /var/lib/acash/hyp011/v2/attempt_ledger/
# /var/lib/acash/hyp011/v2/ca_evidence/
# /var/lib/acash/hyp011/v2/runtime_manifests/
```

### Secrets File
```bash
# Created ONLY under Authority A
sudo mkdir -p /etc/acash
sudo touch /etc/acash/hyp011-v2.env
sudo chown mew:mew /etc/acash/hyp011-v2.env
sudo chmod 600 /etc/acash/hyp011-v2.env

# Contents (never committed):
# ACASH_ALPACA_API_KEY_ID=...
# ACASH_ALPACA_API_SECRET=...
```

### Systemd Units (Authority A: SERVICE ONLY — never the timer)
```bash
# Installed ONLY under Authority A. The bare timer template is NEVER copied
# into systemd (a triggerless timer is refused at load); the timer is
# generated + installed later, only under Authority B.
sudo install -o root -g root -m 0755 \
  /home/mew/Acash/docs/operations/acash-hyp011-v2.sh \
  /usr/local/sbin/acash-hyp011-v2
sudo cp /home/mew/Acash/docs/operations/acash-hyp011-v2.service /etc/systemd/system/
sudo systemctl daemon-reload
# No timer installed. The tracked checkout stays clean (no chmod, no edits).
```

---

## 3. V2 Contract Summary

| Property | V1 | V2 |
|----------|-----|-----|
| Segment ID | (implicit) | `HYP_011_PROSPECTIVE_V2` |
| State Root | `data/hyp_011/prospective/` | `/var/lib/acash/hyp011/v2/` |
| State in Git | Yes (evidence) | **No** (external) |
| First Ordinal | 1 (session 2026-09-28) | 1 (fresh activation) |
| S1 Progress | 1/20 (platform validation) | 0/20 (fresh) |
| AUM | $100,000 | $100,000 |
| Capital | $0.00 | $0.00 |
| Paper/Live | false | false |
| No Real Orders | true | true |
| Python | Implicit uv | Explicit `.venv/bin/python` |
| Timer | V1 units (retired) | `acash-hyp011-v2.timer` (new) |

---

## 4. Deployment Procedure (Authority A)

```bash
# 1. Verify canonical code (APPROVED_RUNTIME_SHA from deployment authorization)
cd /home/mew/Acash
git fetch origin main
test "$(git rev-parse origin/main)" = "$APPROVED_RUNTIME_SHA"
git merge --ff-only origin/main
test "$(git rev-parse HEAD)" = "$APPROVED_RUNTIME_SHA"
git status --short --branch  # clean

# 2. Sync locked dependencies
uv sync --locked

# 3. Create state root
sudo mkdir -p /var/lib/acash/hyp011/v2
sudo chown mew:mew /var/lib/acash/hyp011/v2
sudo chmod 700 /var/lib/acash/hyp011/v2

# 4. Create secrets file (operator fills in credentials)
sudo mkdir -p /etc/acash
sudo touch /etc/acash/hyp011-v2.env
sudo chown mew:mew /etc/acash/hyp011-v2.env
sudo chmod 600 /etc/acash/hyp011-v2.env
# EDIT /etc/acash/hyp011-v2.env with credentials

# 5. Install wrapper (outside the repo) + SERVICE ONLY (never the timer)
sudo install -o root -g root -m 0755 \
  docs/operations/acash-hyp011-v2.sh \
  /usr/local/sbin/acash-hyp011-v2
sudo cp docs/operations/acash-hyp011-v2.service /etc/systemd/system/
sudo systemctl daemon-reload

# 6. Verify NO timer installed and service is INACTIVE
systemctl cat acash-hyp011-v2.timer  # must FAIL (unit absent)
systemctl is-active acash-hyp011-v2.service  # must be "inactive"

# 7. Run deployment preflight (zero network, no session authorities).
#    This checks host/runtime/state/secrets/install contracts ONLY — it never
#    invokes the runner and never needs a SegmentActivationAuthority.
#    The FULL dispatch preflight (--local-preflight with session authorities)
#    runs later under Authority B at timer ELAPSE via the service ExecStartPre
#    gate — never pre-arm (the session has not closed yet at arm time).
APPROVED_RUNTIME_SHA="$APPROVED_RUNTIME_SHA" /usr/local/sbin/acash-hyp011-v2 --deployment-preflight
# Expected: DEPLOYMENT_PREFLIGHT = PASS, NETWORK_REQUESTS = 0,
#           V2_STATE_CREATED = false, V2_TIMER_INSTALLED = false

# 8. Verify V1 evidence untouched
sha256sum data/hyp_011/prospective/state.json
sha256sum data/hyp_011/prospective/observations/2026-09-30.json
```

---

## 5. Activation Procedure (Authority B)

```bash
# AUTHORIZE_HYP_011_V2_ACTIVATION_<SESSION> binds, for ONE future session:
#   APPROVED_RUNTIME_SHA, V2 SegmentActivationAuthority file, TARGET_SESSION,
#   RegisteredIntent SHA, DispatchAuthority file, CA binding, dispatch time.
# Do NOT execute any step below without that authority.

# 1. Write the V2 SegmentActivationAuthority file, e.g.
#    /var/lib/acash/hyp011/v2/segment_activation_authority.json
#    (schema: segment_id HYP_011_PROSPECTIVE_V2, hypothesis HYP_011,
#    activation_session = TARGET_SESSION, runtime_commit_sha =
#    APPROVED_RUNTIME_SHA, starting_aum 100000.00, paper/live false,
#    capital 0.00, no_real_orders true, authorized_at_utc strictly before
#    the session open, human authority_identity).
#    The runner validates every field pre-network; the raw file digest is
#    recorded into V2 state identity.

# 2. Register intent (strictly before the session opens) via the existing
#    authority API `register_observation_intent`
#    (registry dir: /var/lib/acash/hyp011/v2/intent_registry, ordinal 1,
#    previous_observation_sha256 null). V2 session one REQUIRES a physically
#    preregistered intent — the V1 bare-token exception does not apply.

# 3. Create DispatchAuthority bound to:
#    - RegisteredIntent SHA (the physical registry artifact, F17)
#    - Runtime commit SHA (APPROVED_RUNTIME_SHA)
#    - Session-one CA binding digest
#      (CA_NOT_ECONOMICALLY_REQUIRED_NO_PRIOR_HOLDINGS — deterministic,
#      no invented event)
#    - Target session, ordinal = 1, attempt = 1, chain head = null
#    - Validity window covering the dispatch instant
#    - Locks: paper=false, live=false, capital=0, no_real_orders=true
#    V2 session one REQUIRES a DispatchAuthority — the V1 bare-token
#    exception does not apply.

# 4. Derive the exact dispatch time from canonical code (never hand-compute):
#      dispatch_at = candidate_schedule_time(TARGET_SESSION, NyseCa1Calendar())
#                = session.close_utc + 15-minute SIP delay + 5-minute margin
#    Render SYSTEMD_ONCALENDAR_EXPRESSION, e.g. "2026-10-06 20:20:00 UTC"
#    (exact value is calendar-derived per session; the example offset is NOT
#    a constant). Validate on the host:
#      systemd-analyze calendar "<expression>"
#    and confirm the normalized next elapse equals dispatch_at exactly.

# 5. Do NOT run the full dispatch preflight now. It validates session
#    completion + provider eligibility, so before the session closes it fails
#    SHADOW_INCOMPLETE_SESSION by design — that is correct behavior, not a
#    defect, and must never block arming. The full preflight instead runs
#    UNATTENDED at timer elapse via the service ExecStartPre gate:
#      elapse → ExecStartPre (--local-preflight, zero network, zero consume)
#        → on failure: service stops, ExecStart NEVER runs, no market-data
#          call, no attempt consumed, no retry (Restart=no); investigate,
#          then issue a fresh Authority B if governance allows
#        → on PASS: ExecStart runs the live observation immediately, and the
#          live runner independently revalidates every gate before transport.
#    PRE-OPEN ACTIVATION VALIDATION (this procedure: files, bindings, timer)
#    is therefore distinct from DISPATCH-TIME FULL LOCAL PREFLIGHT (elapse).

# 6. Generate + install the timer from the canonical template with the
#    validated trigger baked in (never install the bare triggerless
#    template). The drop-in form below clears first, then sets:
sudo tee /etc/systemd/system/acash-hyp011-v2.timer > /dev/null <<EOF
# Generated under AUTHORIZE_HYP_011_V2_ACTIVATION_<SESSION> from
# docs/operations/acash-hyp011-v2.timer + validated dispatch expression.
[Unit]
Description=ACASH HYP_011 V2 Prospective Shadow Observation Timer
Documentation=file:///home/mew/Acash/docs/operations/HYP_011_V2_HOMELAB_DEPLOYMENT.md

[Timer]
Unit=acash-hyp011-v2.service
OnCalendar=<validated SYSTEMD_ONCALENDAR_EXPRESSION, e.g. 2026-10-06 20:20:00 UTC>
Persistent=false
AccuracySec=1min
RandomizedDelaySec=0
RemainAfterElapse=false

[Install]
WantedBy=timers.target
EOF
# (No Timezone= directive: the expression is UTC-normalized.)
sudo systemd-analyze verify acash-hyp011-v2.timer
sudo systemctl daemon-reload
sudo systemctl cat acash-hyp011-v2.timer  # must show the real OnCalendar trigger
# Plus a service drop-in providing the per-session Environment=
# (AUTHORIZATION, ORDINAL, DISPATCH_ATTEMPT, DISPATCH_AUTHORITY,
# RUNTIME_SHA, SEGMENT_ACTIVATION_AUTHORITY, ...).

# 7. Enable timer for THIS SESSION ONLY
sudo systemctl enable --now acash-hyp011-v2.timer

# 8. Verify armed AND service NOT started by enabling
systemctl list-timers acash-hyp011-v2.timer
systemctl is-active acash-hyp011-v2.service  # must be "inactive" until elapse
```

---

## 6. Verification Checklists

### Post-Deployment (Authority A Complete)
- [ ] `origin/main == HEAD == APPROVED_RUNTIME_SHA` (from deployment authorization)
- [ ] `uv sync --locked` succeeds
- [ ] `/var/lib/acash/hyp011/v2/` exists, 700, mew:mew
- [ ] `/etc/acash/hyp011-v2.env` exists, 600, mew:mew
- [ ] Wrapper installed at `/usr/local/sbin/acash-hyp011-v2` (0755); repo checkout clean (no chmod, no edits)
- [ ] Service installed, `daemon-reload` done; NO timer installed (`systemctl cat` fails)
- [ ] Service `inactive`
- [ ] Deployment preflight: `DEPLOYMENT_PREFLIGHT = PASS`, `NETWORK_REQUESTS = 0`, `V2_TIMER_INSTALLED = false`
- [ ] V1 evidence hashes unchanged

### Post-Activation (Authority B Complete, BEFORE session close)
- [ ] SegmentActivationAuthority written, validated, digest bound into V2 state identity
- [ ] RegisteredIntent created strictly before session open, ordinal 1, chain head null
- [ ] DispatchAuthority created and bound (intent + runtime + session-one CA digest + window + locks)
- [ ] Service drop-in installed with per-session Environment (all bindings, incl. SEGMENT_ACTIVATION_AUTHORITY)
- [ ] Generated timer installed with validated UTC `OnCalendar` trigger (bare template never installed)
- [ ] `systemd-analyze calendar` next elapse equals canonical `candidate_schedule_time`
- [ ] Timer `enabled` and armed; service stays `inactive` until elapse
- [ ] NO pre-arm dispatch preflight attempted (it would fail SHADOW_INCOMPLETE_SESSION by design)

### Post-Elapse (unattended)
- [ ] Either: observation sealed, attempt ledger holds exactly one entry
- [ ] Or (preflight failed): NO observation file, NO ledger entry, NO network call, service failed with `Restart=no` — investigate, then a fresh Authority B if governance allows

---

## 7. Forensic Boundaries

### What V2 MUST NOT Touch
- `data/hyp_011/prospective/` — V1 evidence preserved immutable
- V1 observation artifacts, hashes, state
- V1 systemd units (retired, not deleted)
- Historical seal tests (CRLF-byte families)

### What V2 MUST Enforce
- Absolute `--state-dir` (rejects relative)
- Reject V1 evidence path
- Segment ID `HYP_011_PROSPECTIVE_V2` required with `--state-dir`
- `--segment-activation-authority` required; first target comes ONLY from it
- Fresh ordinal = 1, S1 = 0/20; V1 Stage-B/Stage-C never consulted
- V2 ordinal 1 REQUIRES RegisteredIntent + DispatchAuthority (no bare token)
- Session-one CA binding is the deterministic non-event digest (no invented event)
- `--local-preflight` validates the full live path with zero consumption and zero network; stale targets fail nonzero; it runs at timer ELAPSE via ExecStartPre, never pre-arm
- Capital locks: paper=false, live=false, capital=0, no_real_orders=true

---

## 8. Rollback Procedure

If V2 deployment needs reversal before activation:

```bash
# 1. Disable + remove timer (Authority B only ever creates it)
sudo systemctl disable --now acash-hyp011-v2.timer 2>/dev/null || true
sudo rm -f /etc/systemd/system/acash-hyp011-v2.timer

# 2. Remove service unit
sudo rm /etc/systemd/system/acash-hyp011-v2.service
sudo systemctl daemon-reload

# 3. Remove state root (V2 only — V1 preserved)
sudo rm -rf /var/lib/acash/hyp011/v2

# 4. Remove secrets
sudo rm /etc/acash/hyp011-v2.env
sudo rmdir /etc/acash 2>/dev/null || true

# 5. Remove the INSTALLED wrapper copy (never touch the tracked repo file)
sudo rm /usr/local/sbin/acash-hyp011-v2
```

---

## 9. Known Exceptions

**Homelab Full T1**: 9 historical CRLF-byte seal failures (HYP_009, HYP_006/007, MEC-0015 manifests, old R1 seals). These are **worktree representation anomalies** on the long-lived checkout, NOT runtime defects. GitHub canonical CI (Linux, fresh clone, `.gitattributes` enforced) passes clean. Do NOT mutate historical seals to satisfy these.

**V1 Evidence**: Preserved at `data/hyp_011/prospective/` — hash-verified immutable.

---

## 10. Next Steps After Deployment

1. Wait for authorized activation session
2. Execute Authority B procedure
3. Observe first V2 session (ordinal 1)
4. Begin S1 progression (0/20 → 1/20 → ...)
5. RI-01 Zero-Outcome Data Feasibility (separate authorization)
6. PPDS broker adapters (parallel lane)

---

**STOP**: This document prepares deployment ONLY. No timer armed, no intent registered, no market data accessed, no orders placed. Real capital remains $0.00.