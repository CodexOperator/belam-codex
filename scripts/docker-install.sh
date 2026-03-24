#!/bin/bash
set -euo pipefail
# D1: Docker Installation Script — Ubuntu 24.04 ARM64
# Idempotent — safe to re-run (FLAG-5).

echo "=== Installing Docker Engine on Ubuntu ARM64 ==="

# Check if Docker is already installed and working
if command -v docker &>/dev/null && docker version &>/dev/null 2>&1; then
    echo "✅ Docker already installed: $(docker --version)"
    echo "✅ Docker Compose: $(docker compose version 2>/dev/null || echo 'not found')"
    exit 0
fi

# Add Docker's official GPG key and repo
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends ca-certificates curl

sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -qq
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

# Add current user to docker group (avoids sudo for docker commands)
if ! groups "$USER" | grep -qw docker; then
    sudo usermod -aG docker "$USER"
    echo "⚠️  Added $USER to docker group. Run: newgrp docker (or log out/in)"
fi

echo ""
echo "✅ Docker installed: $(docker --version)"
echo "✅ Docker Compose: $(docker compose version)"
echo ""
echo "If 'docker ps' fails with permission error, run: newgrp docker"
