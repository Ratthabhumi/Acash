"""Hierarchical YAML configuration loader for ACASH."""

from pathlib import Path
from typing import Any, Optional, Union
import yaml  # type: ignore[import-untyped]

from acash.core.config.schema import AppConfig
from acash.core.domain.exceptions import ConfigParseError


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override dictionary into base dictionary."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _parse_yaml_file(file_path: Path) -> dict[str, Any]:
    """Parse a single YAML file and raise ConfigParseError on syntax errors."""
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
            if content is None:
                return {}
            if not isinstance(content, dict):
                raise ConfigParseError(f"YAML root in {file_path} must be a mapping, got: {type(content).__name__}")
            return content
    except yaml.YAMLError as e:
        raise ConfigParseError(f"Malformed YAML syntax in {file_path}: {e}") from e


def load_config(
    config_dir: Union[str, Path] = "configs",
    profile: Optional[str] = None
) -> AppConfig:
    """Load hierarchical configuration starting from base.yaml with optional profile override.
    
    Raises:
        ConfigParseError: If YAML syntax parsing fails.
        pydantic.ValidationError: If parsed schema or types are invalid.
        FileNotFoundError: If base.yaml or profile YAML does not exist.
    """
    dir_path = Path(config_dir)
    base_file = dir_path / "base.yaml"

    config_data = _parse_yaml_file(base_file)

    if profile:
        profile_file = dir_path / f"{profile}.yaml"
        profile_data = _parse_yaml_file(profile_file)
        config_data = _deep_merge(config_data, profile_data)

    return AppConfig(**config_data)
