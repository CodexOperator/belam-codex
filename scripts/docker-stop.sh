#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🛑 Stopping OpenClaw container..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" down
echo "✅ Stopped."
