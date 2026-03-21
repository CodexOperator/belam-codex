#!/usr/bin/env bash
# entrypoint.sh — Container startup for Belam / OpenClaw
#
# Responsibilities:
#   1. Verify workspace is mounted (fail fast if not)
#   2. Install/link belam CLI
#   3. Run incarnate.sh dependencies (Python packages check)
#   4. Start OpenClaw gateway in foreground

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${CYAN}[belam]${NC} $*"; }
ok()   { echo -e "${GREEN}[ok]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
fail() { echo -e "${RED}[fail]${NC} $*"; exit 1; }

# ── 1. Workspace check ───────────────────────────────────────
WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"

log "Checking workspace at $WORKSPACE..."
if [ ! -d "$WORKSPACE" ]; then
  fail "Workspace not found at $WORKSPACE. Did you mount the volume?
  Expected: -v /path/to/belam-codex:$WORKSPACE"
fi

if [ ! -f "$WORKSPACE/SOUL.md" ]; then
  warn "SOUL.md not found — workspace may be empty or misconfigured"
else
  ok "Workspace found ($(ls $WORKSPACE | wc -l) items)"
fi

# ── 2. Config check ──────────────────────────────────────────
CONFIG="$HOME/.openclaw/openclaw.json"
if [ ! -f "$CONFIG" ]; then
  warn "openclaw.json not found at $CONFIG"
  warn "Telegram/channel features will not work without it."
  warn "Mount it: -v ~/.openclaw/openclaw.json:$CONFIG"
fi

# ── 3. SSH keys check ────────────────────────────────────────
if [ -d "$HOME/.ssh" ] && [ "$(ls -A $HOME/.ssh 2>/dev/null)" ]; then
  # Fix permissions (common issue with bind mounts)
  chmod 700 "$HOME/.ssh"
  chmod 600 "$HOME/.ssh"/* 2>/dev/null || true
  ok "SSH keys present"
else
  warn "No SSH keys found — git push/clone over SSH won't work"
fi

# ── 4. belam CLI link ────────────────────────────────────────
BELAM_SCRIPT="$WORKSPACE/scripts/belam.sh"
BELAM_LINK="$HOME/.local/bin/belam"

if [ -f "$BELAM_SCRIPT" ]; then
  mkdir -p "$HOME/.local/bin"
  ln -sf "$BELAM_SCRIPT" "$BELAM_LINK"
  chmod +x "$BELAM_SCRIPT"
  ok "belam CLI linked"
else
  warn "belam.sh not found in workspace/scripts/"
fi

# ── 5. Git safe directory (for mounted repos) ────────────────
git config --global --add safe.directory "$WORKSPACE" 2>/dev/null || true
if [ -d "$HOME/machinelearning" ]; then
  git config --global --add safe.directory "$HOME/machinelearning" 2>/dev/null || true
fi

# ── 6. Start OpenClaw gateway ────────────────────────────────
log "Starting OpenClaw gateway on :18789..."
echo ""

# Trap SIGTERM/SIGINT for clean shutdown
trap 'echo ""; log "Shutting down..."; kill $PID 2>/dev/null; wait $PID 2>/dev/null; exit 0' TERM INT

exec openclaw gateway --port 18789
