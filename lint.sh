#!/bin/bash
# Lint script for JobFunnel

set -e

echo "Running ruff check..."
uv run ruff check --fix jobfunnel/ tests/

echo "Running ruff format..."
uv run ruff format jobfunnel/ tests/

echo "Done!"
