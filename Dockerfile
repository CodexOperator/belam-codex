# OpenClaw Workspace — ARM64 container
# Single-container V1: gateway + agents + scripts
#
# Build: docker compose build
# Run:   docker compose up -d
# Logs:  docker compose logs -f openclaw

# ── Base ──
FROM node:22-bookworm-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Match host UID/GID for bind mount permissions
ARG HOST_UID=1000
ARG HOST_GID=1000
RUN groupadd -g ${HOST_GID} oc 2>/dev/null || true && \
    useradd -m -u ${HOST_UID} -g ${HOST_GID} oc 2>/dev/null || true

# ── Python deps (base only — no torch, ~600MB not ~3GB) ──
COPY requirements-base.txt /tmp/
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements-base.txt

# ── OpenClaw (pinned version for reproducibility) ──
ARG OPENCLAW_VERSION=latest
RUN npm install -g openclaw@${OPENCLAW_VERSION}

# ── Runtime ──
USER oc
WORKDIR /home/oc

# Config and workspace are bind-mounted at runtime
VOLUME ["/home/oc/.openclaw"]

# Gateway port
EXPOSE 18789

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:18789/health || exit 1

# Gateway in fg mode (FLAG-1 fix: 'run' subcommand, not 'start')
ENTRYPOINT ["openclaw", "gateway", "run"]
CMD ["--port", "18789"]
