"""YAML configuration file loading with Pydantic validation."""

from pathlib import Path
from typing import Type, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from .models import EngineConfig, SuiteConfig, TestConfig

T = TypeVar("T", bound=BaseModel)


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""


def load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed YAML contents.

    Raises:
        ConfigError: If the file cannot be read or parsed.
    """
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
            if data is None:
                return {}
            return data
    except FileNotFoundError:
        raise ConfigError(f"Configuration file not found: {path}")
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}")


def load_config(path: Path, model_class: Type[T]) -> T:
    """Load and validate a YAML config file against a Pydantic model.

    Args:
        path: Path to the YAML configuration file.
        model_class: Pydantic model class to validate against.

    Returns:
        Validated configuration model instance.

    Raises:
        ConfigError: If validation fails.
    """
    data = load_yaml(path)
    try:
        return model_class(**data)
    except ValidationError as e:
        raise ConfigError(f"Configuration validation failed for {path}: {e}")


def load_test_config(path: Path) -> TestConfig:
    """Load a test configuration file."""
    return load_config(path, TestConfig)


def load_suite_config(path: Path) -> SuiteConfig:
    """Load a test suite configuration file."""
    return load_config(path, SuiteConfig)


def load_engine_config(path: Path) -> EngineConfig:
    """Load an engine configuration file."""
    return load_config(path, EngineConfig)
