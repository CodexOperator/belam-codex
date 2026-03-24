#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

command -v docker >/dev/null 2>&1 || {
    echo "❌ Docker not installed. See docs/containerize-migration.md"
    exit 1
}

# Ensure .env exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "📝 No .env found — generating from host..."
    bash "$SCRIPT_DIR/docker-build.sh"
fi

echo "🚀 Starting OpenClaw container..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d

echo "⏳ Waiting for health check..."
sleep 5
docker compose -f "$PROJECT_DIR/docker-compose.yml" ps

echo ""
echo "✅ Gateway: http://localhost:${GATEWAY_PORT:-18789}"
echo "   Logs:    docker compose logs -f openclaw"
echo "   Stop:    bash scripts/docker-stop.sh"
