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
    assert "ExecStart=/home/mew/Acash/.venv/bin/python scripts/daily_market_collector.py" in lines
    assert "ProtectSystem=strict" in lines and "NoNewPrivileges=yes" in lines
    assert "ReadWritePaths=/home/mew/Acash/data/private" in lines
    assert not any("Enable=" in line for line in lines)
    text = SERVICE.read_text(encoding="utf-8").lower()
    for banned in ("/v2/orders", "paper-api", "transfer", "api.alpaca.markets"):
        assert banned not in text
    assert not re.search(r"(?m)^\[Install\]", SERVICE.read_text(encoding="utf-8"))


def test_templates_explicitly_refuse_to_claim_a_deployment() -> None:
    for path in (TIMER, SERVICE):
        head = path.read_text(encoding="utf-8")[:600].lower()
        assert "template only" in head
    plan = Path("docs/operations/market-data-collector-homelab.md").read_text(encoding="utf-8")
    assert "NOT DEPLOYED" in plan and "systemd-analyze calendar" in plan
