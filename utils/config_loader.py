# File: utils/config_loader.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Load YAML application configuration through the typed Config contract."""

from pathlib import Path

import yaml

from config.environment import configuration_path
from models.config import Config


def load_config(config_path: str | Path | None = None) -> Config:
    """Load application configuration.

    Args:
        config_path: Explicit configuration file path; None selects the documented
            environment/default path.

    Returns:
        Validated typed Config instance.

    Raises:
        pydantic.ValidationError: Required settings are absent or fail validation.
        TypeError: The YAML root is not a configuration mapping.
        OSError: The selected configuration file cannot be read.
        yaml.YAMLError: Configuration is not valid YAML.
    """

    path = configuration_path(config_path)

    with path.open("r", encoding="utf-8") as file:
        config_data = yaml.safe_load(file)

    return Config(**config_data)
