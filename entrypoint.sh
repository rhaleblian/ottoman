#!/usr/bin/env bash
set -euo pipefail

echo "[daemon] starting ottoman..."
echo "[daemon] volumes:"
echo "  models:    ${COMFY_MODELS_DIR:-not set} -> /app/models"
echo "  inputs:    ${COMFY_INPUT_DIR:-not set} -> /app/input"
echo "  workflows: ${COMFY_WORKFLOWS_DIR:-not set} -> /app/workflows"
exec python -m daemon.daemon

