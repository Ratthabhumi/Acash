# Daily Market-Data Collector — Homelab Deployment Plan

Status: **NOT DEPLOYED, NOT VERIFIED.** The unit files in this directory are templates. No timer is
enabled on `mew@homelab`, and no claim is made that any scheduled collection has run. Nothing in this
document authorises trading; `NO_REAL_ORDERS=true` and real capital authority stays USD 0.00.

## What the collector is (and is not)

- It is an **incremental, idempotent** daily pass over the held US universe: symbols come from the
  private snapshot, the range is the Massive Basic window, and each symbol resumes from the last
  session already indexed.
- It is **not** the HYP_011 governed observation probe. Those units
  (`acash-hyp011-v2.service` / `.timer`) and their historical evidence are untouched and must not be
  reused or overwritten.
- A timer firing is not ingestion. Health is read from `data/private/market_warehouse/health.json`,
  which reports coverage, missing sessions, request counts and the last stop reason.

## Preconditions (Owner, on the Homelab)

1. Confirm the host is the intended one and record the actual checkout:

   ```bash
   cd ~/Acash
   git status --short --branch
   git log -1 --oneline
   git fetch --dry-run
   ```

   Do **not** `git reset`, `git stash` or force-pull. If the remote is ahead, inspect the divergence
   first; the Homelab checkout may contain uncommitted local work.

2. Runtime: `~/.venv` (or `uv sync`) must satisfy `pyproject.toml`. `pyarrow` is required for the
   Parquet partitions.

3. Disk: the collector writes only derived metadata until retention rights are established (see
   below), so the footprint is small. Check `df -h ~` and do not place partitions under `data/raw`.

4. Credentials — create the file **on the Homelab**, never by copying a Windows secret:

   ```bash
   sudo install -d -m 0700 /etc/acash
   sudo install -m 0600 /dev/null /etc/acash/market-data.env
   sudoedit /etc/acash/market-data.env      # add: ACASH_MARKET_DATA_MASSIVE_BASIC=<key>
   ```

   `market_authority.default_credential_store()` reads `ACASH_MARKET_DATA_<PROVIDER_ID>` on POSIX.
   A vendor alias (`BOT_REFERENCE_FX` → `BOT_EXCHANGE_RATES`) reuses the secret only; it never grants
   entitlement, display or derived-use rights.

5. Provider rights: the Massive ODR-004 scope entry permits display, calculation and derived-value use
   but still records `cache_permitted: null` / `retention_policy_verified: null`. Until the Owner
   records a retention decision, the collector **will not** persist raw bars; it indexes session dates
   and derives research output only, and reports `storage_rights: UNESTABLISHED`.

## Install (only after the preconditions pass)

```bash
sudo install -m 0644 docs/operations/acash-market-collector.service /etc/systemd/system/
sudo install -m 0644 docs/operations/acash-market-collector.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start acash-market-collector.service      # one manual pass first
journalctl -u acash-market-collector.service -n 50 --no-pager
cat ~/Acash/data/private/market_warehouse/health.json
```

Only if that manual pass reports a real result (coverage or an explicit, understood stop reason):

```bash
sudo systemctl enable --now acash-market-collector.timer
systemctl list-timers acash-market-collector.timer
```

Verification is the stored evidence, not the unit state:

```bash
systemctl is-active acash-market-collector.timer
ls -l ~/Acash/data/private/market_warehouse/
python - <<'PY'
import json, pathlib
doc = json.loads(pathlib.Path.home().joinpath("Acash/data/private/market_warehouse/health.json").read_text())
print(doc["coverage"]["covered"], doc["coverage"]["missing"], doc["last_job"])
PY
```

## Rollback

```bash
sudo systemctl disable --now acash-market-collector.timer
sudo systemctl stop acash-market-collector.service
sudo rm -f /etc/systemd/system/acash-market-collector.{service,timer}
sudo systemctl daemon-reload
```

Removing the units does not delete `data/private/market_warehouse/`; delete it only after reviewing the
manifest, and never delete HYP_003/HYP_004/HYP_007/HYP_009/HYP_011 evidence.

## What is still missing

- Remote HEAD, disk and service state on `mew@homelab` are **NOT_VERIFIED** in this cycle.
- No Linux secret has been created; the Owner must do step 4 on the host.
- No retention decision exists for Massive raw bars, so the durable warehouse stays gated.
