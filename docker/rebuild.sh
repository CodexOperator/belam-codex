#!/usr/bin/env bash
# rebuild.sh — Rebuild and restart the Belam Docker stack
#
# Usage:
#   ./rebuild.sh              # Rebuild core only (cached layers)
#   ./rebuild.sh --fresh      # Force full rebuild (no cache)
#   ./rebuild.sh --ml         # Also rebuild ML layer
#   ./rebuild.sh --openclaw   # Bust OpenClaw layer only (new npm version)

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "\n${CYAN}▸ $*${NC}"; }
ok()   { echo -e "  ${GREEN}✓ $*${NC}"; }
warn() { echo -e "  ${YELLOW}⚠ $*${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

FRESH=false
BUILD_ML=false
BUST_OPENCLAW=false

# Parse args
for arg in "$@"; do
  case "$arg" in
    --fresh)    FRESH=true ;;
    --ml)       BUILD_ML=true ;;
    --openclaw) BUST_OPENCLAW=true ;;
    --help|-h)
      echo "Usage: $0 [--fresh] [--ml] [--openclaw]"
      echo "  --fresh      Full rebuild, no Docker cache"
      echo "  --ml         Also rebuild belam-ml image"
      echo "  --openclaw   Bust OpenClaw npm install layer only"
      exit 0
      ;;
  esac
done

# ── Pre-flight checks ────────────────────────────────────────
log "Pre-flight checks"

if ! command -v docker &>/dev/null; then
  echo "Docker not installed. Install: https://docs.docker.com/engine/install/"
  exit 1
fi
ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"

if ! docker compose version &>/dev/null 2>&1; then
  echo "Docker Compose v2 not available. Update Docker."
  exit 1
fi
ok "Docker Compose $(docker compose version --short)"

# Check config
if [ ! -f ~/.openclaw/openclaw.json ]; then
  warn "~/.openclaw/openclaw.json not found — Telegram won't work"
fi

# ── Build args ───────────────────────────────────────────────
BUILD_ARGS=""
if [ "$BUST_OPENCLAW" = true ]; then
  BUST_VAL="$(date +%s)"
  BUILD_ARGS="--build-arg BUST_CACHE=$BUST_VAL"
  log "Busting OpenClaw cache (key: $BUST_VAL)"
fi

CACHE_FLAG=""
if [ "$FRESH" = true ]; then
  CACHE_FLAG="--no-cache"
  log "Full rebuild (no cache)"
fi

# ── Stop running containers ──────────────────────────────────
log "Stopping running containers..."
docker compose down 2>/dev/null || true
ok "Stopped"

# ── Build core image ─────────────────────────────────────────
log "Building belam-core..."
START=$(date +%s)
docker compose build $CACHE_FLAG $BUILD_ARGS belam-core
END=$(date +%s)
ok "Built in $((END - START))s"

# ── Build ML image (optional) ────────────────────────────────
if [ "$BUILD_ML" = true ]; then
  log "Building belam-ml (this takes a while — PyTorch is ~3GB)..."
  START=$(date +%s)
  docker compose --profile ml build $CACHE_FLAG belam-ml
  END=$(date +%s)
  ok "ML image built in $((END - START))s"
fi

# ── Start core service ───────────────────────────────────────
log "Starting belam-core..."
docker compose up -d belam-core
ok "Started"

# ── Wait for health ──────────────────────────────────────────
log "Waiting for gateway health check..."
MAX_WAIT=60
WAITED=0
while ! docker compose ps belam-core | grep -q "healthy"; do
  sleep 2
  WAITED=$((WAITED + 2))
  if [ $WAITED -ge $MAX_WAIT ]; then
    warn "Health check timed out after ${MAX_WAIT}s — check logs:"
    echo "    docker compose logs belam-core"
    exit 1
  fi
  echo -n "."
done
echo ""
ok "Gateway healthy (took ${WAITED}s)"

# ── Summary ──────────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  🔮 Belam is running${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Gateway:  http://127.0.0.1:18789"
echo "  Logs:     docker compose logs -f"
echo "  Shell:    docker compose exec belam-core bash"
echo "  Stop:     docker compose down"
echo ""

if [ "$BUILD_ML" = false ]; then
  echo "  ML layer: docker compose --profile ml run --rm belam-ml python3 ..."
  echo ""
fi
