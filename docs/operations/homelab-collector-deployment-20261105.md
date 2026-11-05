# Homelab Collector Deployment — 2026-11-05 (PARTIAL, waiting on one sudo step)

Status (updated 2026-11-05): **INSTALLED AND ACTIVE on the Acer host.** The timer is active, the
service completed with `Result=success`, one Massive Grouped Daily request collected the
2026-11-04 session for all 26 symbols (`failed=0`, `storage_rights=PERMITTED`), and the next run is
2026-11-06 13:00 ICT (01:00 ET). No order authority, `NO_REAL_ORDERS=true`,
capital authority USD 0.00.

## Host facts (verified read-only over SSH, 2026-11-05)

| Item | Result |
| --- | --- |
| SSH / user | reachable at `mew@homelab`, non-root `mew` |
| `/data` | `/dev/sda1`, 916 G, **870 G free**, separate mount |
| `/data/acash` | exists, `root:root 0700`, empty — **not writable by `mew` yet** |
| Python | 3.12.3, `rsync` present, `systemd 255 (255.4-1ubuntu8.18)` |
| `systemd-analyze` | present |
| governance/calendar in bundle | `ODR_UPI_MARKET_DATA_004.json`, ODR-001, NYSE fixture — present |
| `python3.12-venv` | **missing** (`ensurepip` unavailable) — the installer now installs it as root |
| Time sync | `NTPSynchronized=yes` |
| Existing ACASH units | none (HYP_011 state preserved) |
| sudo | password required, so installation is the Owner's step |

## What was transferred

Bundle `~/acash-bundle` on the host, archive SHA-256 `4bbbd547e914e6b3176d4456b6027f9d139d595b0084e35848fc19dba6a980b0`,
hash re-verified after transfer (the V104 bundle also carries `docs/governance/*` and the NYSE calendar fixture):

- `app/` — `src/` + `scripts/` + this operations doc (no Git history, no credentials);
- `deploy/` — the two unit templates and the installer;
- `warehouse/` — **26 Parquet partitions + manifest + session index + FX artifacts**, all 26 SHA-256
  values re-checked on the host (0 failures);
- `snapshot.json` — needed for the symbol universe (owner-private, transferred over SSH only).

Nothing was re-downloaded: the Windows warehouse is the authoritative copy and the transfer preserved it.

## Owner actions (two commands, on the host)

```bash
# 1. Credentials: create locally, never copied from Windows Credential Manager
sudo install -d -m 0700 /etc/acash
sudo install -m 0600 /dev/null /etc/acash/market-data.env
sudoedit /etc/acash/market-data.env
#   ACASH_MARKET_DATA_MASSIVE_BASIC=<key>
#   ACASH_MARKET_DATA_BOT_EXCHANGE_RATES=<key>   (optional)

# 2. Install + acceptance pass (installs python3.12-venv, venv, app, state, units, one bounded run)
sudo ~/acash-bundle/deploy/deploy_acash_collector.sh

# 3. Only after reviewing /data/acash/state/private/market_warehouse/health.json
sudo ~/acash-bundle/deploy/deploy_acash_collector.sh --enable
```

The acceptance run is started through the installed `acash-market-collector.service`, so the provider key is loaded by systemd from `/etc/acash/market-data.env` and never enters the installer process, a command line or a log. The installer is fail-closed: it refuses when `/data` is not a separate mount, when the credential file is
missing or not `0600`, when a transferred partition fails its hash, when the calendar expression is
rejected by the installed systemd, or when the acceptance pass does not write a health record with
`storage_rights: PERMITTED`. It never touches HYP_011 units and does not enable the timer without
`--enable`.

## Layout once installed

```
/data/acash/app     code, root-owned, read-only to the service user
/data/acash/venv    python 3.12 + pyarrow
/data/acash/state   ACASH_PRIVATE_DIR (mew 0700): market_warehouse/, health.json, fx/
/etc/acash/market-data.env   credentials, root 0600, read by systemd before privilege drop
```

Service: oneshot, `User=mew`, `MemoryMax=512M`, `CPUQuota=50%`, `ProtectSystem=strict`,
`ReadWritePaths=/data/acash/state`, `ExecStart=… daily_market_collector.py --catch-up`.
Timer: `OnCalendar=Tue..Sat *-*-* 01:00:00 America/New_York`, `Persistent=true` (validated with
`systemd-analyze calendar` inside the installer before install).

## What is still unproven

- The collector has **not run on the host** (needs the sudo step above).
- The timer has **not been enabled**; `systemctl list-timers` is not evidence until the service ran.
- Reboot survival, missed-session recovery on the host and 24/7 continuity across the single hotspot
  uplink are untested.
- Off-device backup remains blocked (no second device); `/data/backups` is same-HDD, per the Pi contract.

## Catch-up behaviour (implemented, tested locally)

- A durable pass resumes from the stored partitions, not from a "we saw this range" checkpoint.
- `--catch-up` detects middle gaps (dates missing between a symbol and the union calendar) and refetches
  up to `--max-gap-symbols` (default 5) over the bounded window, inside the same 5 req/min budget.
- A missed timer fire runs once at the next boot (`Persistent=true`), then the gap repair fills the
  sessions the host missed while offline.


## V106 — production sync back to git and to Windows

The running host was hotfixed after the bundle was built, so the verified changes were ported back into
Git (not re-implemented): a separate 12 MB cap for the full-market Grouped Daily response, attempts
counted including failed HTTP calls, sanitized `grouped_error_codes`, no per-ticker catch-up while
grouped collection runs, `FAILED` versus `NO_WORK` reporting with non-zero exit, a `Path` for the
governance record in the installer, and `grep -Fxq` for the timer expression.

An installer re-run is now upgrade-safe: if `/data/acash/state/private/market_warehouse/manifest.json`
already exists, the bundle's older warehouse is **not** copied over it, the existing snapshot is kept,
and only the app directory is replaced (ownership reset to root, world-readable). Credentials and the
running timer are untouched.

Windows sync (no provider calls):

```powershell
powershell -NoProfile -File scripts/deploy/Sync-WarehouseFromHomelab.ps1
```

It stages the host warehouse, verifies every partition against the host manifest's SHA-256, replaces
only `data/private/market_warehouse`, writes `sync_state.json` (`provider_calls: 0`) and rebuilds the
research panel offline. The Dashboard shows the sync time and partition count.

Coverage is now inception-aware: a date before an instrument's first stored session is reported as
`not_applicable_pre_inception` (status `PARTIAL_LIMITED_HISTORY`), not as missing data. After the
2026-11-04 sync: 23 COVERED, 2 PARTIAL_LIMITED_HISTORY (CRWV, NASA), 1 PARTIAL (SPCX has a real gap after
inception) and 0 missing.
