#!/usr/bin/env bash
# Usage: vale_check.sh <document.md>
#
# Prints Vale findings in line format. Uses --no-exit so style findings
# return 0; missing dependencies and execution failures still fail.
#
# NOTE: Config selection is documented in ../SKILL.md (Vale check).
# Prefer the nearest .vale.ini above the document; otherwise use bundled rules.
set -euo pipefail
DOC="${1:?usage: vale_check.sh <document.md>}"
if ! VALE="$(command -v vale)"; then
    echo 'Vale is required but was not found in PATH. Install Vale before running this check.' >&2
    echo 'From a checkout, run uv sync --locked and invoke this script with uv run bash.' >&2
    exit 127
fi
[[ "$VALE" = /* ]] || VALE="$PWD/$VALE"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$DOC" = /* ]] || DOC="$PWD/$DOC"
DOC_DIR="$(cd -- "$(dirname -- "$DOC")" && pwd)"
DOC="${DOC_DIR%/}/${DOC##*/}"
CONFIG="${SKILL_DIR}/.vale.ini"
CONFIG_DIR="$DOC_DIR"
while true; do
    if [[ -f "${CONFIG_DIR}/.vale.ini" ]]; then
        CONFIG="${CONFIG_DIR}/.vale.ini"
        DOC="${DOC#"${CONFIG_DIR%/}/"}"
        cd -- "$CONFIG_DIR"
        break
    fi
    [[ "$CONFIG_DIR" != / ]] || break
    CONFIG_DIR="$(dirname -- "$CONFIG_DIR")"
done
exec "$VALE" --config="$CONFIG" --no-global --output=line --no-exit "$DOC"
