#!/usr/bin/env bash
# Install skills into supported AI agent skill directories.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/install_skills.py" "$@"
