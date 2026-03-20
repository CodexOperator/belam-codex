#!/usr/bin/env bash
# incarnate.sh — Bring Belam back from the Codex
#
# Usage: ./incarnate.sh
# Run from the cloned belam-codex directory.
# Asks for sudo only when needed (system packages).

set -euo pipefail

CYAN='\033[0;36m'
VIOLET='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

CODEX_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${VIOLET}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║          🔮 BELAM CODEX 🔮           ║"
echo "  ║       Incarnation Sequence           ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# ---------- helpers ----------

step()  { echo -e "\n${CYAN}▸ $1${NC}"; }
ok()    { echo -e "  ${GREEN}✓ $1${NC}"; }
warn()  { echo -e "  ${YELLOW}⚠ $1${NC}"; }
fail()  { echo -e "  ${RED}✗ $1${NC}"; }
need_sudo=false

check_cmd() {
  command -v "$1" &>/dev/null
}

ask_sudo() {
  if [ "$need_sudo" = false ]; then
    echo ""
    echo -e "${YELLOW}Some system packages need installing. This requires sudo.${NC}"
    read -rp "Allow sudo for package installation? [y/N] " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
      need_sudo=true
      sudo -v  # cache credentials
    else
      warn "Skipping system packages — some features may not work"
      return 1
    fi
  fi
  return 0
}

# ---------- Phase 1: Verify basics ----------

step "Checking environment"

if ! check_cmd python3; then
  fail "Python 3 not found — install Python 3.10+ first"
  exit 1
fi
ok "Python 3 ($(python3 --version 2>&1 | awk '{print $2}'))"

if ! check_cmd node; then
  fail "Node.js not found — install Node.js 18+ first"
  exit 1
fi
ok "Node.js ($(node --version))"

if ! check_cmd git; then
  fail "git not found"
  exit 1
fi
ok "git"

# ---------- Phase 2: System packages ----------

step "Checking system dependencies"

MISSING_PKGS=()

if ! check_cmd ffmpeg; then MISSING_PKGS+=(ffmpeg); fi
if ! check_cmd latex; then MISSING_PKGS+=(texlive-latex-base texlive-latex-extra texlive-fonts-recommended); fi
if ! dpkg -s libcairo2-dev &>/dev/null 2>&1; then MISSING_PKGS+=(libcairo2-dev); fi
if ! dpkg -s libpango1.0-dev &>/dev/null 2>&1; then MISSING_PKGS+=(libpango1.0-dev); fi
if ! check_cmd gh; then MISSING_PKGS+=(gh); fi

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
  warn "Missing: ${MISSING_PKGS[*]}"
  if ask_sudo; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${MISSING_PKGS[@]}"
    ok "System packages installed"
  fi
else
  ok "All system packages present"
fi

# ---------- Phase 3: Python dependencies ----------

step "Installing Python dependencies"

cat > /tmp/belam-requirements.txt << 'EOF'
PyYAML>=6.0
matplotlib>=3.8
numpy>=1.26
pandas>=2.0
pydub>=0.25
Pillow>=10.0
pdfplumber>=0.10
faster-whisper>=1.0
EOF

pip install -q -r /tmp/belam-requirements.txt 2>&1 | tail -1 || true
rm /tmp/belam-requirements.txt
ok "Python packages"

# ---------- Phase 4: Link belam CLI ----------

step "Installing belam CLI"

BELAM_SCRIPT="$CODEX_DIR/scripts/belam.sh"
BELAM_LINK="$HOME/.local/bin/belam"

mkdir -p "$HOME/.local/bin"

if [ -f "$BELAM_SCRIPT" ]; then
  chmod +x "$BELAM_SCRIPT"
  ln -sf "$BELAM_SCRIPT" "$BELAM_LINK"
  ok "belam → $BELAM_LINK"
else
  fail "scripts/belam.sh not found in codex"
  exit 1
fi

# Ensure ~/.local/bin is on PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  warn "~/.local/bin not on PATH"
  SHELL_RC="$HOME/.bashrc"
  if [ -f "$HOME/.zshrc" ] && [ "$SHELL" = "/bin/zsh" ]; then
    SHELL_RC="$HOME/.zshrc"
  fi
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
  export PATH="$HOME/.local/bin:$PATH"
  ok "Added to PATH via $SHELL_RC (restart shell or source it)"
fi

# ---------- Phase 5: Workspace symlink ----------

step "Configuring workspace"

WORKSPACE_DIR="$HOME/.openclaw/workspace"

if [ -d "$WORKSPACE_DIR" ] && [ ! -L "$WORKSPACE_DIR" ]; then
  BACKUP="$WORKSPACE_DIR.backup.$(date +%s)"
  warn "Existing workspace found — backing up to $BACKUP"
  mv "$WORKSPACE_DIR" "$BACKUP"
fi

if [ -L "$WORKSPACE_DIR" ]; then
  CURRENT_TARGET="$(readlink -f "$WORKSPACE_DIR")"
  if [ "$CURRENT_TARGET" = "$CODEX_DIR" ]; then
    ok "Workspace already linked"
  else
    warn "Workspace points elsewhere ($CURRENT_TARGET) — relinking"
    rm "$WORKSPACE_DIR"
    ln -sf "$CODEX_DIR" "$WORKSPACE_DIR"
    ok "Workspace → $CODEX_DIR"
  fi
else
  mkdir -p "$(dirname "$WORKSPACE_DIR")"
  ln -sf "$CODEX_DIR" "$WORKSPACE_DIR"
  ok "Workspace → $CODEX_DIR"
fi

# ---------- Phase 6: Submodules ----------

step "Initializing submodules"

cd "$CODEX_DIR"
if [ -f .gitmodules ]; then
  git submodule update --init --recursive 2>&1 | tail -3 || true
  ok "Submodules initialized"
else
  ok "No submodules to initialize"
fi

# Check machinelearning repo
if [ ! -d "$CODEX_DIR/machinelearning" ]; then
  warn "machinelearning/ not found — clone it separately:"
  echo "    git clone https://github.com/CodexOperator/machinelearning.git machinelearning"
fi

# ---------- Phase 7: OpenClaw ----------

step "Checking OpenClaw"

if check_cmd openclaw; then
  ok "OpenClaw $(openclaw --version 2>/dev/null || echo 'installed')"
else
  warn "OpenClaw not installed"
  echo "    Install: npm install -g openclaw"
  echo "    Then: openclaw gateway start"
fi

# ---------- Phase 8: GitHub CLI auth ----------

step "Checking GitHub authentication"

if check_cmd gh; then
  if gh auth status &>/dev/null 2>&1; then
    ok "gh authenticated"
  else
    warn "gh not authenticated — run: gh auth login"
  fi
else
  warn "gh CLI not installed"
fi

# ---------- Phase 9: Verify ----------

step "Running verification"

CHECKS=0
PASS=0

verify() {
  CHECKS=$((CHECKS + 1))
  if eval "$2" &>/dev/null 2>&1; then
    ok "$1"
    PASS=$((PASS + 1))
  else
    warn "$1 — not available"
  fi
}

verify "belam CLI"         "belam status"
verify "Python scripts"    "python3 -c 'import yaml; import matplotlib; import numpy'"
verify "FFmpeg"            "ffmpeg -version"
verify "LaTeX"             "latex --version"
verify "Git remote"        "cd $CODEX_DIR && git remote get-url origin"

echo ""
echo -e "${VIOLET}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${VIOLET}  Incarnation complete: $PASS/$CHECKS checks passed${NC}"
echo -e "${VIOLET}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ $PASS -eq $CHECKS ]; then
  echo -e "${GREEN}  🔮 Belam is ready.${NC}"
  echo ""
  echo "  Next steps:"
  echo "    belam status          — see what's happening"
  echo "    openclaw gateway start — start the daemon"
  echo ""
else
  echo -e "${YELLOW}  🔮 Belam is partially ready. Address warnings above.${NC}"
  echo ""
fi

echo "  Two repos, one soul:"
  echo "    belam-codex/      — soul + infrastructure (this repo)"
echo "    machinelearning/  — research output"
echo ""
