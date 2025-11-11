#!/usr/bin/env bash
set -euo pipefail

# Load .env if present (ignore comments/blank lines)
if [ -f .env ]; then
  export $(grep -v '^[[:space:]]*#' .env | grep -v '^[[:space:]]*$' | xargs)
fi

exec "$@"
