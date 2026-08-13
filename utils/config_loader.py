from pathlib import Path

import yaml

from models.config import Config


def load_config(config_path: str | Path = "config/config.yaml") -> Config:
    """
    Load application configuration.
    """

    path = Path(config_path)

    with path.open("r", encoding="utf-8") as file:
        config_data = yaml.safe_load(file)

    return Config(**config_data)
