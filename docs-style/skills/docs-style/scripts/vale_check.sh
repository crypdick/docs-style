#!/usr/bin/env bash
# Usage: vale_check.sh <document.md>
#
# Prints vale errors in line format. Always exits 0 (errors are signal,
# not failure — the caller is expected to read stdout and act on findings).
#
# Vale config is co-located at <skill_dir>/.vale.ini and references
# <skill_dir>/vale_styles/Google as its rule bundle.
set -euo pipefail
DOC="${1:?usage: vale_check.sh <document.md>}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec vale --config="${SKILL_DIR}/.vale.ini" --output=line "$DOC" || true
