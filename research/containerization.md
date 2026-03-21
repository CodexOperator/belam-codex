# Containerization Research — Belam / OpenClaw Workspace

> **Authored:** 2026-03-21  
> **Context:** Oracle Cloud ARM64 (aarch64), Ubuntu 24.04, 4 threads / 24GB RAM  
> **Goal:** Make the OpenClaw + Belam stack fully portable and rebuildable from scratch in <5 min

---

## Current State Snapshot

| Component | Location | Size |
|-----------|----------|------|
| OpenClaw (npm) | `/usr/lib/node_modules/openclaw/` | ~706 MB |
| Workspace (belam-codex) | `~/.openclaw/workspace/` | ~656 MB |
| OpenClaw state/config | `~/.openclaw/` (excl. workspace) | ~67 MB |
| SSH keys | `~/.ssh/` | ~12 KB |
| Python ML deps (torch, scipy, snntorch) | system pip | ~3+ GB |

**Runtime:** OpenClaw gateway runs as a `systemd --user` service, connecting to Telegram via outbound WebSocket/HTTP. The gateway binds to `127.0.0.1:18789`.

**`incarnate.sh` already covers:**
- ✅ Python dep check (PyYAML, matplotlib, numpy, pandas, pydub, Pillow, pdfplumber, faster-whisper)
- ✅ System package install (ffmpeg, latex, libcairo2-dev, libpango1.0-dev, gh)
- ✅ belam CLI symlink to `~/.local/bin/belam`
- ✅ `~/.openclaw/workspace` symlink → repo dir
- ✅ git submodule init
- ✅ PATH update in `.bashrc`

**`incarnate.sh` gaps:**
- ❌ Does NOT install Node.js itself
- ❌ Does NOT install OpenClaw via npm
- ❌ Does NOT set up systemd service
- ❌ Does NOT handle `~/.openclaw/openclaw.json` (Telegram tokens, channel config)
- ❌ Does NOT clone the repo — assumes you're already inside it
- ❌ Does NOT handle SSH key setup
- ❌ Does NOT install PyTorch / ML deps (those are heavy and separate)
- ❌ Does NOT clone or reference `machinelearning/` repo

---

## Approach Assessment

### 1. Docker (Single Container)

**What:** One Dockerfile bundling Node 22 + Python 3.12 + OpenClaw + belam scripts. Container clones `belam-codex` on first run, mounts SSH keys and config from host.

**Pros:**
- Standard, portable — works anywhere Docker runs (ARM64 well-supported)
- Reproducible environment, pinned versions
- Isolates system deps from host
- Easy to ship to a new Oracle Cloud instance: `docker pull` or `docker build`

**Cons:**
- 706 MB OpenClaw + system deps = ~1.2GB image (acceptable, no PyTorch inside)
- systemd not available inside Docker → must run `openclaw gateway` as foreground process
- Need to handle signals/restart cleanly (use `--init` or tini)
- SSH keys need bind-mounting with correct permissions

**Rebuild time:** ~3-4 min cold (downloading packages), ~30s with layer cache  
**Telegram connectivity:** ✅ Outbound connections work transparently in any Docker network mode

---

### 2. Docker Compose (Multi-Service) ⭐ RECOMMENDED

**What:** Two services — `belam-core` (OpenClaw gateway + agent runtime) and optionally `belam-ml` (Python ML workloads). Workspace and config are bind-mounted or named volumes.

**Pros:**
- Clean separation: agent core vs ML research layer
- Core container stays lean (~1.2GB, no PyTorch)
- ML container can be started on-demand (saves RAM when idle)
- Volumes make SSH keys, config, and git repos easy to preserve across rebuilds
- `docker compose up -d` is the entire startup command
- Easy to add future services (database, monitoring)

**Cons:**
- Slightly more config than single container
- Still needs Docker installed on host
- ML container with PyTorch = ~6GB+ image (PyTorch ARM64 wheel is ~2GB compressed)

**Rebuild time:** ~3-4 min cold; ~1 min with cache  
**Telegram connectivity:** ✅ Default bridge networking works fine for outbound bots

---

### 3. Portable Binary (PyInstaller / Nuitka)

**What:** Bundle Python scripts (codex_engine.py, pipeline_orchestrate.py, etc.) into standalone executables.

**Assessment:**
- ✅ Could work for the Python engine layer — eliminates pip install step
- ❌ **Cannot bundle OpenClaw itself** (it's a Node.js app, not Python)
- ❌ PyInstaller ARM64 support is functional but can be finicky with native extensions (numpy, torch)
- ❌ Doesn't solve the Node + OpenClaw portability problem
- ❌ Binaries are large (~200-400MB each) and harder to debug
- ❌ Doesn't speed up "rebuild from scratch" since OpenClaw still needs npm install

**Verdict:** Partial solution at best. Only useful as a complement (e.g., ship a standalone `codex_engine` binary). Not recommended as primary strategy.

---

### 4. Nix / Guix

**What:** Declarative package management that produces reproducible, hermetic builds without containers.

**Pros:**
- Minimal runtime overhead (no container abstraction)
- Truly reproducible — exact same deps on any machine
- Works great on ARM64 (NixOS has excellent aarch64 support)
- Can pin OpenClaw, Node, Python all in one `flake.nix`
- Shell environments via `nix develop` — activate per-project without installing globally

**Cons:**
- **Steep learning curve** — Nix language is unusual; flakes especially so
- OpenClaw isn't in nixpkgs — would need a custom derivation for a ~706MB npm package
- PyTorch in Nix is complex (CUDA/ROCm variants, different overlays)
- systemd integration is different on NixOS vs regular Ubuntu
- Debugging failed builds is harder
- Nix store (`/nix/store`) can grow very large (multiple generations)

**Verdict:** Architecturally elegant but operationally expensive to set up. Not worth it here unless migrating the whole host to NixOS. Skip for now.

---

### 5. Enhanced incarnate.sh (Bare-metal, No Container)

**What:** Extend the existing `incarnate.sh` to cover the full bootstrap gap: install Node, npm-install OpenClaw, set up systemd service, handle SSH keys, clone repos.

**Pros:**
- Zero overhead — runs directly on host
- Already partially done, familiar to the system
- Fits the current Oracle Cloud workflow perfectly
- Fastest startup after fresh `git clone`

**Cons:**
- Not isolated — system deps can drift over time
- Harder to reproduce exactly on a different distro
- Still manual SSH key provisioning

**Verdict:** Best complement to Docker, not a replacement. Ideal for quick bare-metal setups; Docker for strict reproducibility.

---

## Recommendation

**Use Docker Compose** as the primary deployment model, with an **enhanced `incarnate.sh`** as a bare-metal fallback.

### Rationale

1. **Portability:** `git clone belam-codex && docker compose up -d` is the entire rebuild flow on any ARM64 machine.
2. **Telegram:** Outbound bot connections are transparent in Docker — no special network config needed.
3. **SSH + Git:** Bind-mount `~/.ssh` read-only; git repos live in named volumes or bind-mounts.
4. **Lean core:** Keep PyTorch out of the core container → 1.2GB vs 5GB+ image.
5. **Secrets:** `openclaw.json` (Telegram tokens) lives outside the image, mounted at runtime.
6. **Rebuild speed:** With `--build-arg BUST_CACHE` only when needed, typical restarts are sub-second.

### Architecture

```
docker-compose.yml
├── belam-core          ← OpenClaw gateway + agent runtime (always up)
│   ├── Image: ~1.2GB (ubuntu:24.04 + Node22 + Python3 + OpenClaw)
│   ├── Mounts: ~/.ssh (ro), ~/.openclaw/openclaw.json, workspace volume
│   └── Runs: openclaw gateway (foreground, port 18789)
│
└── belam-ml (optional) ← Python ML workloads, on-demand
    ├── Image: belam-core + PyTorch + scipy + snntorch (~5GB)
    └── Mounts: workspace volume, machinelearning volume
```

---

## Implementation

See `docker/Dockerfile` and `docker/docker-compose.yml` in this repo.

### Quick Start (new machine)

```bash
# 1. Clone workspace
git clone git@github.com:CodexOperator/belam-codex.git ~/belam-codex
cd ~/belam-codex

# 2. Drop your secrets (from backup or 1Password)
mkdir -p ~/.openclaw
cp /path/to/your/openclaw.json ~/.openclaw/openclaw.json

# 3. Build and start
cd docker/
docker compose up -d --build

# 4. Watch logs
docker compose logs -f belam-core
```

### Rebuild from scratch

```bash
cd ~/belam-codex/docker
./rebuild.sh          # pulls base, rebuilds image, restarts service
```

---

## incarnate.sh Gap Analysis & Patch

The following additions would make `incarnate.sh` a complete bare-metal bootstrap:

```bash
# Gap 1: Node.js install (if missing)
if ! check_cmd node; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

# Gap 2: OpenClaw install (if missing)  
if ! check_cmd openclaw; then
  sudo npm install -g openclaw
fi

# Gap 3: systemd service setup
if ! systemctl --user is-enabled openclaw-gateway &>/dev/null; then
  openclaw gateway install
  systemctl --user enable --now openclaw-gateway
fi

# Gap 4: machinelearning repo clone
ML_DIR="$CODEX_DIR/machinelearning"
if [ ! -d "$ML_DIR" ]; then
  git clone git@github.com:CodexOperator/machinelearning.git "$ML_DIR"
fi

# Gap 5: Config check
if [ ! -f "$HOME/.openclaw/openclaw.json" ]; then
  warn "~/.openclaw/openclaw.json not found — copy from backup before starting gateway"
fi
```

---

## Size Budget

| Layer | Size | Notes |
|-------|------|-------|
| ubuntu:24.04 base | ~80 MB | ARM64 minimal |
| Node.js 22 | ~180 MB | NodeSource deb |
| Python packages (core) | ~400 MB | numpy, matplotlib, pandas, etc. |
| OpenClaw npm | ~706 MB | Includes node_modules |
| System tools | ~200 MB | ffmpeg, gh, cairo, pango |
| **Total core image** | **~1.6 GB** | No PyTorch |
| PyTorch (ML layer) | +~3.5 GB | Separate optional service |

24GB RAM budget: core container uses ~200-400MB RAM at idle. Well within budget.

---

## Security Notes

- Never bake `openclaw.json` (Telegram tokens, API keys) into the Docker image
- Mount SSH keys read-only (`ro` flag)
- Run container as non-root user (`USER ubuntu` in Dockerfile)
- The openclaw gateway binds to `127.0.0.1` by default — in Docker, expose only to `127.0.0.1:18789` on host if needed
- Use `.dockerignore` to exclude `*.json`, `*.key`, `memory/`, etc.
