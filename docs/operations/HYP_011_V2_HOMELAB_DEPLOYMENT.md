# HYP_011 V2 Homelab Deployment Runbook

**Status**: `PREPARATION_ONLY` — NOT DEPLOYED, NOT ACTIVATED
**Branch**: `research/hyp011-v2-activation-prep`
**Base**: `origin/main` @ `49b26f1ee4fc71a4726162bbbb0e318f38be2d8f`

---

## 1. Authority Model (Two Explicit Separate Authorities)

### Authority A: `AUTHORIZE_HYP_011_V2_CANONICAL_DEPLOYMENT`
**Allows**:
- Create `/var/lib/acash/hyp011/v2/` state directory (700, owned by mew:mew)
- Install systemd units: `acash-hyp011-v2.service`, `acash-hyp011-v2.timer`
- Install wrapper: `/home/mew/Acash/docs/operations/acash-hyp011-v2.sh` (755)
- Create secrets file: `/etc/acash/hyp011-v2.env` (600, owned by mew:mew)
- Run zero-network local preflight (`--local-preflight`)

**Does NOT allow**:
- Enable/arm timer
- Create ObservationIntent
- Choose activation session
- Issue `--execute-network` calls
- Paper/Live orders
- Real capital

### Authority B: `AUTHORIZE_HYP_011_V2_ACTIVATION_<SESSION>`
**Allows** (for a specific prospective session):
- Create RegisteredIntent for target session
- Create DispatchAuthority bound to intent + runtime + CA evidence
- Arm timer for that specific session
- Execute live observation with `--execute-network`

**Requires**: Authority A already completed

**Does NOT allow**:
- Backfill
- Automatic retry (failed dispatch = new Authority B required)
- Automatic skip to later session

---

## 2. Deployment Prerequisites

### Repository State
```bash
# On homelab
cd /home/mew/Acash
git fetch origin
git checkout 49b26f1ee4fc71a4726162bbbb0e318f38be2d8f  # exact canonical main
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

### Systemd Units
```bash
# Installed ONLY under Authority A
sudo cp /home/mew/Acash/docs/operations/acash-hyp011-v2.service /etc/systemd/system/
sudo cp /home/mew/Acash/docs/operations/acash-hyp011-v2.timer /etc/systemd/system/
sudo cp /home/mew/Acash/docs/operations/acash-hyp011-v2.sh /home/mew/Acash/docs/operations/
chmod +x /home/mew/Acash/docs/operations/acash-hyp011-v2.sh
sudo systemctl daemon-reload
# Timer remains DISABLED until Authority B
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
# 1. Verify canonical code
cd /home/mew/Acash
git rev-parse HEAD  # must equal 49b26f1ee4fc71a4726162bbbb0e318f38be2d8f

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

# 5. Install systemd units
sudo cp docs/operations/acash-hyp011-v2.service /etc/systemd/system/
sudo cp docs/operations/acash-hyp011-v2.timer /etc/systemd/system/
sudo cp docs/operations/acash-hyp011-v2.sh /home/mew/Acash/docs/operations/
chmod +x /home/mew/Acash/docs/operations/acash-hyp011-v2.sh
sudo systemctl daemon-reload

# 6. Verify timer is DISABLED
systemctl is-enabled acash-hyp011-v2.timer  # must be "disabled"

# 7. Run local preflight (zero network)
/home/mew/Acash/docs/operations/acash-hyp011-v2.sh --local-preflight
# Expected: LOCAL_PREFLIGHT = PASS, NETWORK_REQUESTS = 0

# 8. Verify V1 evidence untouched
sha256sum data/hyp_011/prospective/state.json
sha256sum data/hyp_011/prospective/observations/2026-09-30.json
```

---

## 5. Activation Procedure (Authority B)

```bash
# For target session YYYY-MM-DD
TARGET_SESSION="2026-10-05"  # example

# 1. Register intent (before session opens) via the existing authority API.
#    No new intent-registration CLI is introduced in this prep task; the
#    canonical entry point remains
#    `acash.research.hyp_011.shadow_authority.register_observation_intent`
#    (registry dir: /var/lib/acash/hyp011/v2/intent_registry, ordinal starts at 1).
#    Do NOT execute this step without AUTHORIZE_HYP_011_V2_ACTIVATION_<SESSION>.

# 2. Prepare CA evidence bundle (official scope/no-event)
#    Per F16/F19 intake contract

# 3. Create DispatchAuthority bound to:
#    - RegisteredIntent SHA
#    - Runtime commit SHA (49b26f1...)
#    - CA evidence bundle SHA
#    - Target session
#    - Ordinal = 1, Attempt = 1
#    - Locks: paper=false, live=false, capital=0, no_real_orders=true

# 4. Arm timer with session-specific drop-in
sudo systemctl edit --force acash-hyp011-v2.timer
# [Timer]
# OnCalendar=2026-10-05 20:15:00
# Timezone=America/New_York

# 5. Enable timer for THIS SESSION ONLY
sudo systemctl enable --now acash-hyp011-v2.timer

# 6. Verify armed
systemctl list-timers acash-hyp011-v2.timer
```

---

## 6. Verification Checklists

### Post-Deployment (Authority A Complete)
- [ ] `git rev-parse HEAD` = `49b26f1ee4fc71a4726162bbbb0e318f38be2d8f`
- [ ] `uv sync --locked` succeeds
- [ ] `/var/lib/acash/hyp011/v2/` exists, 700, mew:mew
- [ ] `/etc/acash/hyp011-v2.env` exists, 600, mew:mew
- [ ] Systemd units installed, `daemon-reload` done
- [ ] Timer `disabled`, service `inactive`
- [ ] Local preflight: `LOCAL_PREFLIGHT = PASS`, `NETWORK_REQUESTS = 0`
- [ ] V1 evidence hashes unchanged

### Post-Activation (Authority B Complete)
- [ ] RegisteredIntent created and bound
- [ ] DispatchAuthority created and bound
- [ ] Timer drop-in installed for exact session
- [ ] Timer `enabled` and armed
- [ ] Next elapse matches target session eligibility

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
- Fresh ordinal = 1, S1 = 0/20
- Zero network in `--local-preflight` / `--dry-run`
- Capital locks: paper=false, live=false, capital=0, no_real_orders=true

---

## 8. Rollback Procedure

If V2 deployment needs reversal before activation:

```bash
# 1. Disable timer (if somehow enabled)
sudo systemctl disable --now acash-hyp011-v2.timer

# 2. Remove systemd units
sudo rm /etc/systemd/system/acash-hyp011-v2.service
sudo rm /etc/systemd/system/acash-hyp011-v2.timer
sudo systemctl daemon-reload

# 3. Remove state root (V2 only — V1 preserved)
sudo rm -rf /var/lib/acash/hyp011/v2

# 4. Remove secrets
sudo rm /etc/acash/hyp011-v2.env
sudo rmdir /etc/acash 2>/dev/null || true

# 5. Remove wrapper
rm /home/mew/Acash/docs/operations/acash-hyp011-v2.sh
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