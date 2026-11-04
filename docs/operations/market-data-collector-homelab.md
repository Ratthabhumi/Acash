# Daily Market-Data Collector — Homelab Deployment Plan

Status: **NOT DEPLOYED, NOT VERIFIED.** The Homelab is **pending an Ubuntu reinstall** (the Owner
reported the existing installation is no longer workable), so no remote inspection was attempted in
this cycle. The unit files in this directory are templates: no timer is enabled, and no scheduled
collection has ever run on that host. Nothing here authorises trading; `NO_REAL_ORDERS=true` and real
capital authority stays USD 0.00.

## What the collector is (and is not)

- An **incremental, idempotent** daily pass over the held US universe. A durable pass resumes from the
  stored Parquet partitions, not from a "we already saw this range" checkpoint, so purged or missing
  data is fetched again instead of being assumed complete.
- **Calendar-aware**: the US venue fixture decides whether today is a session. On a weekend or a
  holiday the pass prints `NO_SESSION` and makes **no provider request** (`--force` overrides).
- **Not** the HYP_011 governed observation probe. Those units and their historical evidence are
  untouched and must not be reused or overwritten.
- A timer firing is not ingestion. Health is read from `data/private/market_warehouse/health.json`.

## Timer correction (V99)

`Timezone=` is **not** a portable `[Timer]` key, so the timezone now lives inside the calendar
expression:

```ini
OnCalendar=Mon..Fri *-*-* 18:30:00 America/New_York
Persistent=true
AccuracySec=1min
RandomizedDelaySec=120
```

Validate on the **target host** before enabling, and record the output:

```bash
systemd-analyze calendar 'Mon..Fri *-*-* 18:30:00 America/New_York'
systemd-analyze verify /etc/systemd/system/acash-market-collector.timer
systemctl --version
```

18:30 ET is after the 16:00 close and after a 13:00 early close; the collector's
`eod_eligible_after` value (close + 30 minutes) is the earliest defensible moment. DST is handled by the
timezone in the expression, never by a hard-coded ICT offset.

## Preconditions (Owner, after the reinstall)

1. Confirm the host and record the actual checkout:

   ```bash
   cd ~/Acash && git status --short --branch && git log -1 --oneline
   ```

   Do **not** `git reset`, `git stash` or force-pull. If the remote is ahead, inspect the divergence.

2. Runtime: `uv sync --locked` (or an existing `.venv`) must provide `pyarrow` for the partitions.

3. Disk: check `df -h ~`. Partitions are small (about 20 KB per symbol-year); `data/raw` is untouched.

4. Credentials — create the file **on the Homelab**, never by copying a Windows secret:

   ```bash
   sudo install -d -m 0700 /etc/acash
   sudo install -m 0600 /dev/null /etc/acash/market-data.env
   sudoedit /etc/acash/market-data.env      # ACASH_MARKET_DATA_MASSIVE_BASIC=<key>
                                            # ACASH_MARKET_DATA_BOT_EXCHANGE_RATES=<key>
   ```

   `market_authority.default_credential_store()` reads `ACASH_MARKET_DATA_<PROVIDER_ID>` on POSIX.

5. Rights: ODR-004 amendment 004 records the Owner's private-storage decision for `MASSIVE_BASIC` and
   the reference-FX rights for `BOT_REFERENCE_FX`. It is conditional: private warehouse only, no
   redistribution, no public derived benchmark, no model training, and purge within 30 days of the
   terms or plan ending. If the vendor terms change, stop collecting and run
   `uv run python scripts/purge_market_data.py --confirm DELETE_PRIVATE_MARKET_DATA`.

## Install (only after the preconditions pass)

```bash
sudo install -m 0644 docs/operations/acash-market-collector.service /etc/systemd/system/
sudo install -m 0644 docs/operations/acash-market-collector.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start acash-market-collector.service      # one manual pass first
journalctl -u acash-market-collector.service -n 50 --no-pager
cat ~/Acash/data/private/market_warehouse/health.json
```

Enable the timer only if that manual pass produced a real result (coverage, or an explicit and
understood stop reason):

```bash
sudo systemctl enable --now acash-market-collector.timer
systemctl list-timers acash-market-collector.timer
systemctl is-active acash-market-collector.timer
```

Verification is the stored evidence, not the unit state:

```bash
python - <<'PY'
import json, pathlib
doc = json.loads(pathlib.Path.home().joinpath("Acash/data/private/market_warehouse/health.json").read_text())
print(doc["coverage"]["covered"], doc["coverage"]["missing"], doc["last_job"], doc["storage_rights"])
PY
```

## Rollback

```bash
sudo systemctl disable --now acash-market-collector.timer
sudo systemctl stop acash-market-collector.service
sudo rm -f /etc/systemd/system/acash-market-collector.{service,timer}
sudo systemctl daemon-reload
```

Removing the units does not delete `data/private/market_warehouse/`. Delete it only through the purge
command, and never delete HYP_003/HYP_004/HYP_007/HYP_009/HYP_011 evidence.

## What is still missing

- The Homelab host does not exist in a deployable state until the Ubuntu reinstall is finished.
- Remote HEAD, disk, services and credentials remain **NOT_VERIFIED**.
- The timer has never been parsed by `systemd-analyze` on a real host.
