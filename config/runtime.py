# File: config/runtime.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Load typed application settings for compatibility with existing runtime imports."""

# from config.runtime import settings

from utils.config_loader import load_config

settings = load_config()
