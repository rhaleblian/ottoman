#!/usr/bin/env bash
set -euo pipefail

echo "[daemon] starting ottoman..."
exec python -m daemon.daemon

