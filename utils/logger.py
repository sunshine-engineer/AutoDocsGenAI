import logging
import logging.config
from pathlib import Path

import yaml


def setup_logger(
    config_path: str = "config/logging.yaml",
) -> logging.Logger:
    """
    Configure and return the application logger.

    Automatically creates the log directory if it doesn't exist.
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
