#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Prerequisite check
command -v docker >/dev/null 2>&1 || {
    echo "❌ Docker not installed. See docs/containerize-migration.md"
    exit 1
}

# Detect host UID/GID for bind mount permissions
export HOST_UID=$(id -u)
export HOST_GID=$(id -g)
export OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"

# Generate .env for docker compose
cat > "$PROJECT_DIR/.env" << EOF
HOST_UID=$HOST_UID
HOST_GID=$HOST_GID
OPENCLAW_HOME=$OPENCLAW_HOME
GATEWAY_PORT=18789
OPENCLAW_VERSION=latest
EOF
echo "📝 Generated .env (UID=$HOST_UID, GID=$HOST_GID)"

echo "🔨 Building OpenClaw container..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" build

echo "✅ Build complete."
echo "   Run with: bash scripts/docker-run.sh"
echo "   Or:       docker compose up -d"
