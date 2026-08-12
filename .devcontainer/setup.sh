#!/usr/bin/env bash

set -euo pipefail

echo "================================="
echo "Initializing Development Environment"
echo "================================="

# Move to repository root
cd "$(dirname "$0")/.."

echo "Working directory:"
pwd

echo
echo "Checking project files..."

if [ ! -f "pyproject.toml" ]; then
    echo "ERROR: pyproject.toml not found."
    echo "Current directory: $(pwd)"
    exit 1
fi

# Create environment file if missing
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Created .env from .env.example"
    else
        echo "WARNING: .env.example not found."
    fi
else
    echo ".env already exists. Keeping existing configuration."
fi

# Install Python dependencies
echo
echo "Installing dependencies..."
uv sync

# Create required directories
echo
echo "Creating project directories..."

mkdir -p logs
mkdir -p data
mkdir -p tmp
mkdir -p notebooks

# Validate environment
echo
echo "Python:"
python --version

echo
echo "uv:"
uv --version

echo
echo "Project:"
pwd

echo
echo "================================="
echo "Development Environment Ready"
echo "================================="