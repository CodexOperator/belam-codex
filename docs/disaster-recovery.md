# Disaster Recovery Runbook

**Last updated:** 2026-03-24  
**Estimated recovery time:** 15-30 minutes

---

## What's Preserved (in Git)

- All workspace code: `scripts/`, `extensions/`, configs
- All primitives: `tasks/`, `pipelines/`, `decisions/`, `lessons/`, `memory/`
- Docker files: `Dockerfile`, `docker-compose.yml`, `requirements-*.txt`
- Agent workspaces: `workspace-{architect,builder,critic,sage}/`
- Documentation: `docs/`

## What's NOT in Git (must be backed up separately)

> ⚠️ **FLAG-2 CRITICAL:** `openclaw.json` is at `~/.openclaw/openclaw.json`, OUTSIDE the workspace. It is NOT tracked in git.

- **`~/.openclaw/openclaw.json`** — Contains Telegram bot tokens, channel configs, agent definitions, gateway settings. **MUST be backed up separately.**
- **`data/temporal.db`** — Pipeline state SQLite database (can be rebuilt from git primitives, but loses transition history)
- Active agent sessions (ephemeral — recreated on restart)
- PID files and locks (auto-cleared on restart)
- Render engine RAM state (rebuilds from disk in <1s)
- `.codex_runtime/` (sockets, registers — recreated on first use)
- Experiment results not yet committed to git

### Config Backup

Run periodically (or before major changes):
```bash
# Backup config to a safe location (encrypted recommended)
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup
# Optional: add to git with encryption
# gpg -c ~/.openclaw/openclaw.json  # creates .gpg file
```

---

## Scenario 1: Complete VM Loss

### Recovery Steps

#### 1. Provision New VM (5 min)
```bash
# Oracle ARM64 instance, Ubuntu 24.04, 4+ cores, 24GB RAM
# Open port 18789 for gateway
```

#### 2. Clone Repository (2 min)
```bash
mkdir -p ~/.openclaw
cd ~/.openclaw
git clone <workspace-repo-url> workspace
# Agent workspaces are symlinked from main workspace
```

#### 3. Restore Config (2 min)
```bash
# Restore from backup (NOT in git — see FLAG-2 above)
# Option A: From encrypted backup
# gpg -d openclaw.json.gpg > ~/.openclaw/openclaw.json

# Option B: From secure storage / password manager
# Copy openclaw.json to ~/.openclaw/openclaw.json

# Option C: Recreate from scratch (if no backup exists)
openclaw wizard
# Then manually re-enter: Telegram tokens, channel configs, agent definitions
```

#### 4a. Recovery with Docker (5 min)
```bash
cd ~/.openclaw/workspace
bash scripts/docker-install.sh
newgrp docker
bash scripts/docker-build.sh
bash scripts/docker-run.sh
```

#### 4b. Recovery WITHOUT Docker — Fallback (5 min)
```bash
# Install Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Install OpenClaw
npm install -g openclaw

# Install Python deps
pip3 install --break-system-packages -r requirements-base.txt

# Start gateway via systemd
openclaw gateway start
```

#### 5. Validate (2 min)
```bash
# With Docker:
bash scripts/docker-validate.sh

# Without Docker:
openclaw status
curl -sf http://localhost:18789/health && echo "✅ Gateway healthy"
```

#### 6. Reconnect Channels (2 min)
- Telegram bot tokens are in config (restored in step 3)
- Gateway auto-reconnects on start
- Verify: send test message to bot

---

## Scenario 2: Container Corruption (Gateway Won't Start)

```bash
# Rebuild from scratch (no data loss — workspace is bind-mounted)
cd ~/.openclaw/workspace
docker compose down
docker compose build --no-cache
docker compose up -d

# Verify
bash scripts/docker-validate.sh
```

---

## Scenario 3: Workspace Data Corruption

```bash
# Restore from git
cd ~/.openclaw/workspace
git stash              # Save any uncommitted changes
git pull origin master

# If severe:
git reset --hard origin/master  # WARNING: discards local changes

# Restart
docker compose restart  # or: systemctl --user restart openclaw-gateway
```

---

## Scenario 4: Config Lost (openclaw.json)

If `~/.openclaw/openclaw.json` is lost and no backup exists:

```bash
# Recreate with wizard
openclaw wizard

# You will need:
# - Telegram bot tokens (from @BotFather)
# - Channel/group IDs
# - Agent definitions (check docs/ or git history for reference)
```

---

## Prevention: Regular Backups

Add to crontab or run manually:
```bash
# Commit workspace changes
cd ~/.openclaw/workspace && git add -A && git commit -m "auto-backup $(date -u +%Y-%m-%d)" && git push

# Backup config separately
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup.$(date -u +%Y%m%d)
```
