#!/bin/bash
# Lint script for JobFunnel

set -e

echo "Running isort..."
uv run isort jobfunnel/ tests/

echo "Running black..."
uv run black jobfunnel/ tests/

echo "Running flake8..."
uv run flake8 jobfunnel/ tests/ || true

echo "Done!"
