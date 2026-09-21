#!/usr/bin/env bash
# Run ON the Mac after life-companion-v0.1.tgz is copied next to AIProject/
set -euo pipefail
TGZ="${1:-}"
DEST="${2:-/Users/chunchenglu/Downloads/AIProject/life-companion}"
PARENT="$(dirname "$DEST")"
if [[ -z "$TGZ" ]]; then
  echo "Usage: $0 /path/to/life-companion-v0.1.tgz [dest_dir]" >&2
  exit 2
fi
mkdir -p "$PARENT"
# Extract into parent so life-companion/ appears
tar -xzf "$TGZ" -C "$PARENT"
cd "$DEST"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
pytest -q
python -m life_companion.cli demo --dry-run
echo "OK: life-companion ready at $DEST"
