# File: config/settings.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Re-export crawl and chunking settings for existing pipeline imports."""

from models.config import ChunkingConfig, CrawlConfig

__all__ = ["ChunkingConfig", "CrawlConfig"]
