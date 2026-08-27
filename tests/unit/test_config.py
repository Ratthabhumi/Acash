"""Unit tests for configuration loading and error boundary separation."""

from pathlib import Path
import pytest
from pydantic import ValidationError

from acash.core.config.loader import load_config
from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import ConfigParseError


def test_load_base_config() -> None:
    config = load_config(config_dir="configs")
    assert config.system.environment == "base"
    assert config.system.base_currency == "USD"
    assert config.data.default_timeframe == BarTimeframe.M1
    assert config.execution.mode == "mock"
    assert config.risk.max_drawdown_limit_pct == 0.15


def test_load_profile_overrides() -> None:
    research_cfg = load_config(config_dir="configs", profile="research")
    assert research_cfg.system.environment == "research"
    assert research_cfg.system.log_level == "DEBUG"
    assert research_cfg.data.max_lookback_bars == 50000
    assert research_cfg.risk.max_drawdown_limit_pct == 0.25

    dev_cfg = load_config(config_dir="configs", profile="development")
    assert dev_cfg.system.environment == "development"
    assert dev_cfg.system.json_logs is False


def test_yaml_syntax_error_raises_config_parse_error(tmp_path: Path) -> None:
    # Malformed YAML syntax (bad indentation / invalid syntax)
    bad_yaml = tmp_path / "base.yaml"
    bad_yaml.write_text("system:\n  env: [bad indentation\n", encoding="utf-8")

    with pytest.raises(ConfigParseError):
        load_config(config_dir=tmp_path)


def test_schema_error_raises_validation_error(tmp_path: Path) -> None:
    # Valid YAML syntax, but invalid schema value (e.g. max_drawdown_limit_pct = 5.0 > 1.0)
    invalid_schema_yaml = tmp_path / "base.yaml"
    invalid_schema_yaml.write_text("risk:\n  max_drawdown_limit_pct: 5.0\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(config_dir=tmp_path)
