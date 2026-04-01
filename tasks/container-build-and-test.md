---
primitive: task
status: complete
priority: low
created: 2026-03-24
owner: belam
project: multi-agent-infrastructure
depends_on: []
upstream: [containerize-openclaw-workspace]
downstream: []
tags: [infrastructure, docker, containerization]
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# Container Build and Test — Full Self-Contained Image

## Description

Build a fully self-contained Docker image that can be pulled and run anywhere with one command. NOT a bind-mount dev setup — a portable, production-ready container.

## Critical Safety Rule

**All build work happens in `/tmp/container-build/` — NEVER in the live workspace.**
See: `lessons/containerization-must-use-isolated-build-directory.md`

Docker must be pre-installed by Shael. Pipeline halts if Docker is not available.

## Architecture

### What Goes Inside the Image
- Workspace (belam-codex repo) baked in via COPY or git clone at build time
- openclaw config (sans secrets) baked in
- All services managed by supervisord/s6-overlay:
  - Gateway (openclaw)
  - codex_render.py
  - Cron jobs (converted from system cron to in-container scheduler)

### What Stays Outside (Runtime)
- **Secrets:** SSH keys, API tokens, credentials — via Docker secrets, env vars, or mounted .env
- **openclaw.json credentials** — same treatment (env var override or secret mount)
- **Persistent state volumes:**
  - delivery-queue
  - agents
  - memory
  - logs
  - workspace (if mutable mode desired)

### Base Image
```dockerfile
FROM node:22-bookworm-slim
# Install: python3, pip, supervisord/s6
# COPY workspace into image
# npm install -g openclaw@<pinned-version>
# pip install -r requirements-base.txt
# Supervisord config starts: gateway, codex_render, cron
# HEALTHCHECK on :18789/health
```

### Re-Image Script
```bash
#!/bin/bash
# rebuild.sh — one-command re-image
set -e
cd /tmp/container-build/docker
git pull origin main
docker compose build --no-cache
docker compose up -d --force-recreate
docker image prune -f
echo "Done. New image running."
```

## Build Process

1. `mkdir /tmp/container-build/`
2. Clone/copy workspace + docker configs into build dir
3. Build Dockerfile, compose.yml, supervisord.conf in build dir
4. `docker build` + `docker run` from there
5. Verify: healthcheck on :18789, gateway probe, agent session test
6. Confirm working → tag image
7. `rm -rf /tmp/container-build/`

## Deliverables

1. **Dockerfile** — single multi-service image (node:22-bookworm-slim base)
2. **docker-compose.yml** — with named volumes, secret mounts, healthcheck
3. **supervisord.conf** — gateway + codex_render + cron
4. **rebuild.sh** — one-command re-image script
5. **Validation test script** — build → start → health → mounts → deps → CLI checks
6. **Disaster recovery runbook** — 15-30 min recovery from complete VM loss

## Gap Analysis

| Need | Current Status |
|------|---------------|
| Self-contained image | Bind-mounts everything from host |
| Multi-process (gateway + render + cron) | Only runs gateway |
| Secrets via env/runtime | Expects host files |
| Persistent volumes for state | Partially defined |
| One-command rebuild script | Doesn't exist |
| Pinned, reproducible deps | Partially (requirements files exist) |

## Success Criteria

- [ ] `docker compose up -d` starts all services from cold
- [ ] Gateway responds on healthcheck endpoint
- [ ] Agent sessions work (spawn + complete)
- [ ] Secrets never baked into image
- [ ] Named volumes survive re-image
- [ ] rebuild.sh does rolling restart with zero manual steps
- [ ] Build dir cleaned up after confirmed working
