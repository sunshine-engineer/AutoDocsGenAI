# File: utils/logger.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Initialize application logging and create configured file-handler directories."""

import logging
import logging.config
from pathlib import Path

import yaml


def setup_logger(
    config_path: str = "config/logging.yaml",
) -> logging.Logger:
    """Configure and return the application logger.

    Automatically creates the log directory if it doesn't exist.

    Args:
        config_path: Logging YAML path, defaulting to config/logging.yaml.

    Returns:
        Application logger named documentation_pipeline.

    Raises:
        OSError: The selected configuration file cannot be read.
        yaml.YAMLError: Configuration is not valid YAML.
    """

    config_file = Path(config_path)

    with config_file.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # Create log directory if using a FileHandler
    handlers = config.get("handlers", {})

    for handler in handlers.values():
        filename = handler.get("filename")

        if filename:
            log_file = Path(filename)
            log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(config)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return logging.getLogger("documentation_pipeline")
