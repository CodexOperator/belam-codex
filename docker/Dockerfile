# ============================================================
# Belam / OpenClaw — ARM64 Container
# Base: ubuntu:24.04 | Target: linux/arm64
# ============================================================
# Build:  docker build -t belam-core .
# Run:    docker compose up -d  (see docker-compose.yml)
# ============================================================

FROM ubuntu:24.04

LABEL org.opencontainers.image.title="Belam Core"
LABEL org.opencontainers.image.description="OpenClaw + Belam agent runtime (ARM64)"
LABEL org.opencontainers.image.source="https://github.com/CodexOperator/belam-codex"

# ── Prevent interactive prompts during apt ──────────────────
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# ── Build args (override to bust cache from a specific layer)
ARG NODE_VERSION=22
ARG OPENCLAW_VERSION=latest
ARG BUST_CACHE=1

# ── System packages ─────────────────────────────────────────
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    # Core tools
    curl wget git ca-certificates gnupg sudo unzip \
    # Python
    python3 python3-pip python3-venv python3-dev \
    # Audio/video
    ffmpeg \
    # Canvas / PDF rendering
    libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev \
    # Misc
    tmux jq build-essential \
    # GitHub CLI
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
       | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
       https://cli.github.com/packages stable main" \
       > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update -qq && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js 22 (NodeSource) ──────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version && npm --version

# ── Create non-root user ─────────────────────────────────────
RUN useradd -ms /bin/bash ubuntu \
    && echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# ── Python packages (core — no PyTorch) ─────────────────────
# Installed as root first so they're system-wide, then used by ubuntu user
COPY requirements-core.txt /tmp/requirements-core.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements-core.txt \
    && rm /tmp/requirements-core.txt

# ── Switch to ubuntu user ────────────────────────────────────
USER ubuntu
WORKDIR /home/ubuntu

# ── Node/npm global prefix for non-root install ─────────────
ENV NPM_CONFIG_PREFIX=/home/ubuntu/.npm-global
ENV PATH="/home/ubuntu/.npm-global/bin:/home/ubuntu/.local/bin:${PATH}"
RUN mkdir -p ~/.npm-global

# ── Install OpenClaw ─────────────────────────────────────────
# Use BUST_CACHE arg to force reinstall: --build-arg BUST_CACHE=$(date +%s)
ARG BUST_CACHE
RUN echo "OpenClaw install (cache key: ${BUST_CACHE})" \
    && npm install -g openclaw${OPENCLAW_VERSION:+@${OPENCLAW_VERSION}} \
    && openclaw --version

# ── Runtime directories ──────────────────────────────────────
RUN mkdir -p \
    ~/.openclaw \
    ~/.openclaw/workspace \
    ~/.local/bin \
    ~/.config/systemd/user \
    ~/.ssh

# ── Entrypoint script ────────────────────────────────────────
COPY --chown=ubuntu:ubuntu entrypoint.sh /home/ubuntu/entrypoint.sh
RUN chmod +x /home/ubuntu/entrypoint.sh

# ── Ports ────────────────────────────────────────────────────
# OpenClaw gateway (loopback inside container; exposed via compose)
EXPOSE 18789

# ── Health check ─────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -sf http://127.0.0.1:18789/ > /dev/null || exit 1

ENTRYPOINT ["/home/ubuntu/entrypoint.sh"]
