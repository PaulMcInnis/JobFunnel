#!/bin/bash
# Lint script for JobFunnel

set -e

echo "Running ruff format..."
uv run ruff format jobfunnel/

echo "Running ruff check..."
uv run ruff check --fix jobfunnel/

echo "Running pyright type check..."
uv run pyright jobfunnel/

echo "Done!"
