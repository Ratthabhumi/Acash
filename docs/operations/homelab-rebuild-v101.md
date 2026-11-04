# Homelab Rebuild — V101 Preparation Checklist (NOT EXECUTED)

Status: **HOMELAB_DEFERRED_OS_REBUILD.** The previous Ubuntu root disk (`/dev/sdb`) failed with I/O
errors and has been removed; the Owner is installing a replacement. Nothing in this document was run
against any host, no SSH attempt was made, and no data was migrated.

Target: Ubuntu Server 24.04 LTS · ~500 GB SSD for OS/runtime (after a hardware-health check) · WD 1 TB
mounted at `/data` for the historical warehouse and backups.

## 1. Bootstrap checklist (GitOps, no secrets in Git)

```bash
# identity and network first
hostnamectl; ip -brief addr; timedatectl
# storage inventory by serial, never by assumed /dev/sdX
lsblk -o NAME,SIZE,SERIAL,MODEL,TRAN,MOUNTPOINTS
sudo smartctl -a /dev/<device>        # SMART health before any format
```

- [ ] `smartctl` reports PASSED for both disks; no reallocated-sector growth.
- [ ] `/data` is mounted **by UUID** in `/etc/fstab` with `nofail` and a dedicated 1 TB disk.
- [ ] Time sync active (`timedatectl` shows synchronised); the collector's ET/ICT conversion depends on it.
- [ ] `git clone https://github.com/Ratthabhumi/Acash.git ~/Acash` and record `git log -1 --oneline`.
- [ ] `uv sync --locked` (or a venv) provides `pyarrow`; `python -V` matches `pyproject.toml` (3.14 target, 3.12 runtime tested).
- [ ] `/etc/acash/market-data.env` created locally (mode 0600, owner root) with
      `ACASH_MARKET_DATA_MASSIVE_BASIC=…` and `ACASH_MARKET_DATA_BOT_EXCHANGE_RATES=…`.
      **Never copy a Windows Credential Manager secret over an unauthenticated channel.**
- [ ] `systemd-analyze calendar 'Mon..Fri *-*-* 18:30:00 America/New_York'` and
      `systemd-analyze verify acash-market-collector.timer` both succeed on the *actual* systemd version.

## 2. Infrastructure repository review (before running anything)

The previous infrastructure repository is <https://github.com/Ratthabhumi/Pi_Personal-Infrastructure>.
Do **not** run its playbooks wholesale. Read them first for:

- [ ] destructive tasks (`mkfs`, `parted`, `rm -rf`, `docker system prune`, volume removals);
- [ ] hardcoded `/dev/sdX` or old `/ssd-data` paths;
- [ ] Docker ownership/UID assumptions that no longer match the reinstalled host;
- [ ] services that would bind public ports.

Run playbooks in `--check` mode first and review the diff.

## 3. Private warehouse transfer (after the host is healthy)

The authoritative dataset currently lives on the Windows workstation:

- 26 Massive Parquet partitions (~0.6 MB) + `manifest.json` (SHA-256, source, adjustment basis,
  retention policy, terms revision `2026-11-03`);
- `session_index.json`, `health.json`, `fx/usd_thb_series.json`, `fx/decomposition.json`.

Transfer over an authenticated channel (`rsync -av --checksum` over SSH, or a USB disk), then verify:

```bash
cd ~/Acash/data/private/market_warehouse
python - <<'PY'
import hashlib, json, pathlib
root = pathlib.Path(".")
manifest = json.loads((root / "manifest.json").read_text())
bad = [s for s, e in manifest["partitions"].items()
       if not (root / "bars" / f"{s}.parquet").is_file()
       or hashlib.sha256((root / "bars" / f"{s}.parquet").read_bytes()).hexdigest() != e["sha256"]]
print(len(manifest["partitions"]), "partitions, failures:", bad)
PY
```

- [ ] 26/26 partitions verified, zero hash failures.
- [ ] The transferred `manifest.json` still carries the provider licence metadata; do not strip it.
- [ ] Do **not** re-download the 26 symbols if the transfer verifies — it wastes quota and adds nothing.

## 4. Collector acceptance (only after 1–3 pass)

```bash
python scripts/daily_market_collector.py --end 2026-11-03      # expect NO_WORK, 0 requests
python scripts/daily_market_collector.py --end 2026-11-04      # one real incremental pass
cat data/private/market_warehouse/health.json
```

- [ ] The first pass reports `NO_WORK` with **0 provider calls** (idempotence).
- [ ] The second pass either collects the new session or reports an understood stop reason.
- [ ] `health.json` shows `storage_rights: PERMITTED`, the retention policy and the coverage matrix.
- [ ] Only then: `systemctl enable --now acash-market-collector.timer`, and record
      `systemctl list-timers acash-market-collector.timer` plus the next elapse time.

## 5. Deferred items and boundaries

- Timer activation, service start and any remote mutation stay **out of scope** until the OS and storage
  pass their health checks.
- `data/raw` (HYP_003/004/007/009/011 evidence) is not migrated in this step; it needs a separate
  preservation plan.
- No private data or secret may enter Git, CI artifacts or the infrastructure repository.
