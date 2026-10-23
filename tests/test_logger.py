# File: tests/test_logger.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for logger."""

from utils.logger import setup_logger


def test_setup_logger_returns_application_logger():
    """Verify setup logger returns application logger."""
    logger = setup_logger()

    assert logger.name == "documentation_pipeline"
