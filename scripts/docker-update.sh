#!/bin/bash
set -euo pipefail
# D4: Container Update Workflow
# Pull latest code, rebuild container, restart, validate.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$WORKSPACE_DIR"

export HOST_UID=$(id -u)
export HOST_GID=$(id -g)
export OPENCLAW_HOME="$HOME/.openclaw"

echo "=== Container Update ==="

echo "1. Pulling latest code..."
git pull || echo "⚠️  Git pull failed (may be on detached HEAD)"

echo ""
echo "2. Rebuilding container..."
sg docker -c "docker compose build"

echo ""
echo "3. Restarting container..."
sg docker -c "docker compose up -d"

echo ""
echo "4. Waiting for gateway..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:18789/health >/dev/null 2>&1; then
        echo "   ✅ Gateway healthy after ${i}s"
        break
    fi
    sleep 1
    if [ "$i" -eq 30 ]; then
        echo "   ❌ Gateway did not respond within 30s"
        exit 1
    fi
done

echo ""
echo "✅ Update complete"
echo "   Run 'bash scripts/docker-validate.sh' for full validation"
