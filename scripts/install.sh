#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env in $ROOT/.env — edit that file (not ~/.env) with your Apple ID and password."
fi
echo "Install complete. Next: edit .env, then run scripts/sync-once.sh --album YourAlbum --list"
