#!/usr/bin/env bash
# ACASH market-data collector — host-side installer for Acer Ubuntu (run ONCE with sudo).
#
# It is idempotent and fail-closed: it refuses to touch a host whose storage, permissions or credentials
# do not match the contract, never overwrites HYP_011 units, and only enables the timer after a real
# collection pass writes a health record.
#
#   sudo /home/mew/acash-bundle/deploy/deploy_acash_collector.sh --enable
#
# What it installs:
#   /data/acash/app        repository subset (src + scripts), root-owned read-only
#   /data/acash/venv       minimal runtime (python3 -m venv + pyarrow only)
#   /data/acash/state      ACASH_PRIVATE_DIR (mew-owned 0700): warehouse, health, FX artifacts
#   /etc/systemd/system/acash-market-collector.{service,timer}
#   /etc/acash/market-data.env must already exist (Owner-created, 0600) — never created here.
set -euo pipefail

APP_ROOT=/data/acash/app
STATE_ROOT=/data/acash/state
VENV=/data/acash/venv
BUNDLE="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE=/etc/acash/market-data.env
ENABLE=0
[[ "${1:-}" == "--enable" ]] && ENABLE=1

fail() { echo "STOP: $*" >&2; exit 2; }
say() { echo "[acash] $*"; }

[[ $EUID -eq 0 ]] || fail "run with sudo (storage and unit installation need root)"
[[ -d /data ]] || fail "/data is not mounted"
findmnt -rn /data >/dev/null || fail "/data is not a separate mount; refusing to write a warehouse"
[[ -n "$(ls -A /data 2>/dev/null || true)" || true ]] # /data may be empty

# ---- credentials -------------------------------------------------------------------------------
if [[ ! -f "$ENV_FILE" ]]; then
  cat >&2 <<'EOF'
STOP: /etc/acash/market-data.env does not exist.
Create it first (the key must never be copied from Windows Credential Manager automatically):

  sudo install -d -m 0700 /etc/acash
  sudo install -m 0600 /dev/null /etc/acash/market-data.env
  sudoedit /etc/acash/market-data.env      # add:
  # ACASH_MARKET_DATA_MASSIVE_BASIC=<Massive API key>
  # ACASH_MARKET_DATA_BOT_EXCHANGE_RATES=<BOT key>   (optional, anomaly cross-check)

Then re-run this installer.
EOF
  exit 3
fi
grep -q '^ACASH_MARKET_DATA_MASSIVE_BASIC=.*[^=[:space:]]' "$ENV_FILE" \
  || fail "ACASH_MARKET_DATA_MASSIVE_BASIC is missing from $ENV_FILE"
perm=$(stat -c '%a' "$ENV_FILE")
[[ "$perm" == "600" || "$perm" == "400" ]] || fail "$ENV_FILE must be 0600, found $perm"

# ---- app + state ---------------------------------------------------------------------------------
id mew >/dev/null 2>&1 || fail "user mew does not exist"
install -d -o root -g root -m 0755 /data/acash
rm -rf "$APP_ROOT.new"
install -d -o root -g root -m 0755 "$APP_ROOT.new"
cp -a "$BUNDLE/app/." "$APP_ROOT.new/"
install -d -o root -g root -m 0755 "$APP_ROOT"
rsync -a --delete "$APP_ROOT.new/" "$APP_ROOT/"
rm -rf "$APP_ROOT.new"

install -d -o mew -g mew -m 0700 "$STATE_ROOT"
install -d -o mew -g mew -m 0700 "$STATE_ROOT/private"
if [[ -d "$BUNDLE/warehouse" ]]; then
  install -d -o mew -g mew -m 0700 "$STATE_ROOT/private/market_warehouse"
  rsync -a "$BUNDLE/warehouse/." "$STATE_ROOT/private/market_warehouse/"
fi
[[ -f "$BUNDLE/snapshot.json" ]] && install -o mew -g mew -m 0600 "$BUNDLE/snapshot.json" "$STATE_ROOT/private/snapshot.json"

# ---- runtime -------------------------------------------------------------------------------------
if [[ ! -x "$VENV/bin/python" ]]; then
  if ! python3 -m ensurepip --version >/dev/null 2>&1; then
    say "python3-venv is missing; installing it (root)"
    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3.12-venv \
      || fail "could not install python3.12-venv; run: sudo apt install -y python3.12-venv"
  fi
  say "creating $VENV"
  python3 -m venv "$VENV" || fail "python3 -m venv failed even after installing python3.12-venv"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet 'pyarrow>=14.0.0' || fail "pyarrow install failed (check network/uplink)"
  chown -R mew:mew "$VENV"
fi
PYTHONPATH="$APP_ROOT/src" "$VENV/bin/python" - <<'PY'
import pyarrow, acash.market_data.collector, acash.market_data.warehouse, acash.invest.market_calendar
print("[acash] runtime ok: pyarrow", pyarrow.__version__)
PY

# ---- hash verification of transferred partitions --------------------------------------------------
PYTHONPATH="$APP_ROOT/src" ACASH_PRIVATE_DIR="$STATE_ROOT/private" "$VENV/bin/python" - <<'PY'
import hashlib, json, pathlib
root = pathlib.Path("/data/acash/state/private/market_warehouse")
manifest = root / "manifest.json"
if not manifest.is_file():
    print("[acash] no manifest transferred; a fresh warehouse will be created by the acceptance pass")
else:
    doc = json.loads(manifest.read_text())
    bad = []
    for symbol, entry in doc.get("partitions", {}).items():
        path = root / "bars" / f"{symbol}.parquet"
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry.get("sha256"):
            bad.append(symbol)
    if bad:
        raise SystemExit(f"PARTITION_HASH_MISMATCH: {bad[:5]}")
    print(f"[acash] {len(doc.get('partitions', {}))} partitions verified by SHA-256")
PY

# ---- systemd --------------------------------------------------------------------------------------
CAL='Mon..Fri *-*-* 18:30:00 America/New_York'
systemd-analyze calendar "$CAL" >/dev/null || fail "OnCalendar expression rejected by this systemd"
grep -q '^OnCalendar='"$CAL"'$' "$BUNDLE/deploy/acash-market-collector.timer" \
  || fail "timer template does not carry the validated OnCalendar expression"
install -m 0644 "$BUNDLE/deploy/acash-market-collector.service" /etc/systemd/system/acash-market-collector.service
install -m 0644 "$BUNDLE/deploy/acash-market-collector.timer" /etc/systemd/system/acash-market-collector.timer
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/acash-market-collector.timer

# ---- acceptance: one bounded, authorized collection pass -------------------------------------------
say "acceptance pass (bounded; respects 5 requests/minute)"
runuser -u mew -- env PYTHONPATH="$APP_ROOT/src" ACASH_PRIVATE_DIR="$STATE_ROOT/private" \
  "$VENV/bin/python" "$APP_ROOT/scripts/daily_market_collector.py" --catch-up --max-requests 40 \
  || fail "acceptance pass failed"
HEALTH="$STATE_ROOT/private/market_warehouse/health.json"
[[ -f "$HEALTH" ]] || fail "acceptance wrote no health record"
python3 - "$HEALTH" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
print("[acash] health:", doc.get("coverage", {}).get("covered"), "covered /",
      doc.get("coverage", {}).get("missing"), "missing; next run:", (doc.get("next_run") or {}).get("next_run_ict"))
if doc.get("storage_rights") != "PERMITTED":
    raise SystemExit("STORAGE_RIGHTS_NOT_PERMITTED: refuse to enable unattended collection")
PY

# ---- enable only on request and only after acceptance ----------------------------------------------
if [[ $ENABLE -eq 1 ]]; then
  systemctl enable --now acash-market-collector.timer
  systemctl --no-pager is-active acash-market-collector.timer
  systemctl list-timers --no-pager acash-market-collector.timer | head -3
else
  say "installed but NOT enabled; re-run with --enable after reviewing the health record"
fi
say "done"
