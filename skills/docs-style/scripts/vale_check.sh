#!/usr/bin/env bash
# Usage: vale_check.sh <document.md>
#
# Prints Vale findings in line format. Uses --no-exit so style findings
# return 0; missing dependencies and execution failures still fail.
#
# Vale config is co-located at <skill_dir>/.vale.ini and references
# <skill_dir>/vale_styles/Google as its rule bundle.
set -euo pipefail
DOC="${1:?usage: vale_check.sh <document.md>}"
if ! command -v vale >/dev/null 2>&1; then
    echo 'Vale is required but was not found in PATH. Install Vale before running this check.' >&2
    echo 'From a checkout, run uv sync --locked and invoke this script with uv run bash.' >&2
    exit 127
fi
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec vale --config="${SKILL_DIR}/.vale.ini" --output=line --no-exit "$DOC"
