# File: .devcontainer/Dockerfile
# Purpose: Build the Python development runtime and pinned uv bootstrap.
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspaces

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Keep the environment bootstrap reproducible.
RUN pip install "uv==0.12.3"

# Default shell
CMD ["bash"]
