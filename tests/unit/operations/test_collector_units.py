"""Static checks on the collector unit templates (no systemd on the development host).

`systemd-analyze` must still be run on the target host before enabling anything; these tests only
guarantee that the templates do not contain the two mistakes that would silently break a deployment:
a `Timezone=` directive that is not portable, and an OnCalendar expression without its timezone.
"""

from __future__ import annotations

import re
from pathlib import Path

TIMER = Path("docs/operations/acash-market-collector.timer")
SERVICE = Path("docs/operations/acash-market-collector.service")


def _lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")]


def test_timer_carries_the_timezone_inside_the_calendar_expression() -> None:
    lines = _lines(TIMER)
    assert not any(line.startswith("Timezone=") for line in lines), "Timezone= is not a portable [Timer] key"
    calendars = [line.split("=", 1)[1] for line in lines if line.startswith("OnCalendar=")]
    assert calendars == ["Mon..Fri *-*-* 18:30:00 America/New_York"]
    assert calendars[0].endswith("America/New_York")
    assert "Persistent=true" in lines and "Unit=acash-market-collector.service" in lines
    assert "WantedBy=timers.target" in lines


def test_service_is_a_hardened_oneshot_that_cannot_place_an_order() -> None:
    lines = _lines(SERVICE)
    assert "Type=oneshot" in lines and "User=mew" in lines and "Restart=no" in lines
    assert "EnvironmentFile=/etc/acash/market-data.env" in lines
    assert ("ExecStart=/data/acash/venv/bin/python /data/acash/app/scripts/daily_market_collector.py"
            " --catch-up") in lines
    assert "Environment=ACASH_PRIVATE_DIR=/data/acash/state/private" in lines
    assert "EnvironmentFile=/etc/acash/market-data.env" in lines
    assert "ProtectSystem=strict" in lines and "NoNewPrivileges=yes" in lines
    assert "ReadWritePaths=/data/acash/state" in lines
    assert not any("Enable=" in line for line in lines)
    text = SERVICE.read_text(encoding="utf-8").lower()
    for banned in ("/v2/orders", "paper-api", "transfer", "api.alpaca.markets"):
        assert banned not in text
    assert not re.search(r"(?m)^\[Install\]", SERVICE.read_text(encoding="utf-8"))


def test_templates_explicitly_refuse_to_claim_a_deployment() -> None:
    for path in (TIMER, SERVICE):
        head = path.read_text(encoding="utf-8")[:600].lower()
        # The units are installed by the fail-closed installer; they must say so and must not claim a
        # running deployment.
        assert "installed by scripts/deploy/deploy_acash_collector.sh" in head
    assert "never enable before the acceptance pass" in TIMER.read_text(encoding="utf-8").lower()
    plan = Path("docs/operations/market-data-collector-homelab.md").read_text(encoding="utf-8")
    assert "NOT DEPLOYED" in plan and "systemd-analyze calendar" in plan


def test_installer_injects_credentials_through_systemd_and_guards_its_paths() -> None:
    installer = Path("scripts/deploy/deploy_acash_collector.sh").read_text(encoding="utf-8")
    # Acceptance runs the installed unit, whose EnvironmentFile supplies the provider key.
    assert "systemctl start acash-market-collector.service" in installer
    acceptance = installer.split("acceptance pass via")[1].split("enable only on request")[0]
    assert "runuser" not in acceptance  # the secret comes from systemd, never from this script
    assert "EnvironmentFile=/etc/acash/market-data.env" not in installer.split("acceptance")[1][:1200]
    assert "stat -c %Y" in installer  # health must be refreshed by the run
    # A root-owned recursive operation may only target the fixed app directory.
    assert "case \"$APP_ROOT\" in" in installer and "/data/acash/app) ;;" in installer
    # The runtime artifacts must travel with the bundle.
    assert "ODR_UPI_MARKET_DATA_004.json" in installer
    assert "nyse_xnys_calendar_2026_2028.json" in installer
    transfer = Path("scripts/deploy/Transfer-AcashCollectorBundle.ps1").read_text(encoding="utf-8")
    assert "docs\\governance" in transfer and "nyse_xnys_calendar_2026_2028.json" in transfer
