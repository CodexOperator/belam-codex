# Migrating to Containerized OpenClaw

## Prerequisites

- **Docker Engine 24+** (or Docker Desktop)
  ```bash
  # Ubuntu/Debian ARM64:
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  # Log out and back in for group membership
  ```
- **docker compose v2** (included with Docker Engine 24+)
- **Existing OpenClaw installation** at `~/.openclaw`

## Quick Start

```bash
cd ~/.openclaw/workspace

# 1. Build container (one-time, ~5 min)
bash scripts/docker-build.sh

# 2. Stop existing systemd service
systemctl --user stop openclaw-gateway

# 3. Start container
bash scripts/docker-run.sh

# 4. Verify
curl http://localhost:18789/health
```

## What Changes

| Before (systemd) | After (Docker) |
|-------------------|----------------|
| Gateway runs as systemd user service | Gateway runs inside container |
| Python deps installed on host pip | Python deps inside container (base only) |
| Node.js from host nvm/n | Node.js 22 from container image |
| Updates via `npm update -g openclaw` | Rebuild container: `docker compose build` |

## What Doesn't Change

- **Config location:** `~/.openclaw/openclaw.json` (bind-mounted)
- **Workspace structure:** Same paths inside container via bind mount
- **Agent behavior:** Transparent — agents don't know they're containerized
- **Telegram/channel connections:** Gateway handles via outbound polling
- **Extensions:** Loaded from `~/.openclaw/extensions/` (bind-mounted)
- **Render engine:** UDS socket via bind-mounted workspace

## Architecture

```
Container (openclaw-workspace:local)
├── Node.js 22 (bookworm-slim)
├── Python 3 + base deps (PyYAML, scipy, numpy, etc.)
├── openclaw@latest (npm global)
└── Bind mount: ~/.openclaw → /home/oc/.openclaw
    ├── openclaw.json (config)
    ├── workspace/ (scripts, pipelines, etc.)
    ├── workspace-{architect,builder,critic,sage}/ (agent workspaces)
    └── extensions/ (cockpit plugins)
```

**Note:** ML deps (torch, snntorch) are NOT in the container — they're ~2.4GB
and only needed for Colab/GPU hosts. Use `requirements-ml.txt` if needed locally.

## Updating OpenClaw

```bash
# Rebuild with latest version
docker compose build --no-cache
docker compose up -d

# Or pin a specific version
OPENCLAW_VERSION=2026.3.23-1 docker compose build
```

## Logs

```bash
# Follow logs
docker compose logs -f openclaw

# Last 100 lines
docker compose logs --tail 100 openclaw
```

## Rollback to systemd

```bash
# 1. Stop container
bash scripts/docker-stop.sh

# 2. Restart systemd service
systemctl --user start openclaw-gateway

# 3. Verify
openclaw gateway status
```

## Troubleshooting

### Permission denied on bind mount
The container user (`oc`) is created with your host UID/GID. If permissions
are wrong, rebuild with correct UID:
```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose build
```

### Gateway fails to start
Check the config file is valid:
```bash
docker compose run --rm openclaw cat /home/oc/.openclaw/openclaw.json | python3 -m json.tool
```

### Python script fails
The container has base deps only. If a script needs torch/snntorch:
```bash
# Run on host Python instead
python3 scripts/your_script.py
```
