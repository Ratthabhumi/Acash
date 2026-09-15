"""CLI option surface for the V2 follow-up (recovery + sizing + candidate add).

Verifies the argparse defaults stay legacy-safe for hand-built Namespaces
(getattr defaults), that the new operational flags parse, and that malformed
recovery/sizing inputs fail-closed at parse time.
"""

import argparse
from decimal import Decimal

import pytest

from acash.paper.runner import SignalSizingPolicy
from acash.paper.tournament_cli import (
    _parse_backoff_seconds,
    _parse_nav_sizing_pct,
    _resolve_sizing,
    parse_args,
)

_LEGACY_GIT = "a11995373bcb293135374e8c7dce6091963fea4a"


def _argv(*extra: str) -> list[str]:
    return ["--git-commit", _LEGACY_GIT, *extra]


def test_defaults_preserve_legacy_surface() -> None:
    ns = parse_args(_argv())
    assert ns.auto_mount_infra_candidates is True
    assert ns.infra_mount_count == 3
    assert ns.infra_sizing_policy == "auto"
    assert ns.nav_sizing_notional_pct == Decimal("10.0")
    assert ns.disable_feed_recovery is False
    assert ns.max_recovery_attempts == 5
    assert ns.recovery_backoff_seconds == (2.0, 5.0, 10.0, 20.0, 30.0)
    assert ns.recovery_poll_interval_seconds == 2.0
    assert ns.candidate_add_file is None
    assert ns.num_slots == 3


def test_explicit_sizing_policies_parse() -> None:
    assert parse_args(_argv("--infra-sizing-policy", "nav-relative")).infra_sizing_policy == "nav-relative"
    assert parse_args(_argv("--infra-sizing-policy", "legacy-fixed")).infra_sizing_policy == "legacy-fixed"
    assert parse_args(_argv("--infra-sizing-policy", "auto")).infra_sizing_policy == "auto"


def test_invalid_sizing_policy_rejected() -> None:
    with pytest.raises(SystemExit):
        parse_args(_argv("--infra-sizing-policy", "bogus"))


def test_nav_sizing_pct_parses() -> None:
    ns = parse_args(_argv("--nav-sizing-notional-pct", "12.5"))
    assert ns.nav_sizing_notional_pct == Decimal("12.5")


def test_nav_sizing_pct_zero_rejected() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_nav_sizing_pct("0")


def test_nav_sizing_pct_out_of_range_rejected() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_nav_sizing_pct("150")


def test_nav_sizing_pct_non_numeric_rejected() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_nav_sizing_pct("abc")
    with pytest.raises(SystemExit):
        parse_args(_argv("--nav-sizing-notional-pct", "abc"))


def test_recovery_flags_parse() -> None:
    ns = parse_args(
        _argv(
            "--max-recovery-attempts",
            "3",
            "--recovery-backoff-seconds",
            "1,2,3",
            "--recovery-poll-interval-seconds",
            "0.5",
        )
    )
    assert ns.max_recovery_attempts == 3
    assert ns.recovery_backoff_seconds == (1.0, 2.0, 3.0)
    assert ns.recovery_poll_interval_seconds == 0.5


def test_backoff_valid_multiline_parsing() -> None:
    assert _parse_backoff_seconds("1,2.5,3") == (1.0, 2.5, 3.0)
    assert _parse_backoff_seconds("5") == (5.0,)


def test_backoff_empty_rejected() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_backoff_seconds("")


def test_backoff_non_positive_rejected() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_backoff_seconds("1,0,5")
    with pytest.raises(SystemExit):
        parse_args(_argv("--recovery-backoff-seconds", "1,0,5"))


def test_backoff_non_numeric_rejected() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_backoff_seconds("1,x,5")
    with pytest.raises(SystemExit):
        parse_args(_argv("--recovery-backoff-seconds", "1,x,5"))


def test_candidate_add_file_flag() -> None:
    ns = parse_args(_argv("--candidate-add-file", "C:/tmp/adds.json"))
    assert ns.candidate_add_file is not None
    assert str(ns.candidate_add_file).endswith("adds.json")


def test_disable_feed_recovery_flag() -> None:
    ns = parse_args(_argv("--disable-feed-recovery"))
    assert ns.disable_feed_recovery is True


def test_infra_mount_count_flag() -> None:
    ns = parse_args(_argv("--infra-mount-count", "5"))
    assert ns.infra_mount_count == 5


def test_resolve_sizing_auto_legacy_when_not_auto_mounting() -> None:
    ns = argparse.Namespace(
        infra_sizing_policy="auto",
        auto_mount_infra_candidates=False,
        nav_sizing_notional_pct=Decimal("10.0"),
    )
    policy, pct = _resolve_sizing(ns)
    assert policy == SignalSizingPolicy.INFRA_FIXED_QUANTITY
    assert pct == Decimal("0")


def test_resolve_sizing_auto_nav_when_auto_mounting() -> None:
    ns = argparse.Namespace(
        infra_sizing_policy="auto",
        auto_mount_infra_candidates=True,
        nav_sizing_notional_pct=Decimal("7.5"),
    )
    policy, pct = _resolve_sizing(ns)
    assert policy == SignalSizingPolicy.NAV_RELATIVE_PERCENT
    assert pct == Decimal("7.5")


def test_resolve_sizing_getattr_safe_for_bare_namespace() -> None:
    ns = argparse.Namespace()  # legacy hand-built Namespace without new fields
    policy, pct = _resolve_sizing(ns)
    assert policy == SignalSizingPolicy.INFRA_FIXED_QUANTITY
    assert pct == Decimal("0")


def test_resolve_sizing_fixed_normalizes_pct_to_zero() -> None:
    ns = argparse.Namespace(
        infra_sizing_policy="legacy-fixed",
        auto_mount_infra_candidates=True,
        nav_sizing_notional_pct=Decimal("12.0"),
    )
    policy, pct = _resolve_sizing(ns)
    assert policy == SignalSizingPolicy.INFRA_FIXED_QUANTITY
    assert pct == Decimal("0")