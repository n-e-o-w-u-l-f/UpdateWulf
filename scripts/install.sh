#!/usr/bin/env bash
# Unix user installation. For machine services, follow docs/installation.md.
set -euo pipefail

UPDATEWULF_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
UPDATEWULF_INTERPRETER="${UPDATEWULF_PYTHON:-python3}"

if ! command -v "$UPDATEWULF_INTERPRETER" >/dev/null 2>&1; then
  printf '%s\n' 'Python 3.9+ is required. Set UPDATEWULF_PYTHON to its executable path.' >&2
  exit 127
fi
if [ ! -f "$UPDATEWULF_ROOT/install.py" ]; then
  printf '%s\n' 'Incomplete UpdateWulf source: install.py is missing.' >&2
  exit 2
fi

exec "$UPDATEWULF_INTERPRETER" "$UPDATEWULF_ROOT/install.py" "$@"
