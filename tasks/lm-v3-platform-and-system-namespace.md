---
title: LM v3 — Platform & System Namespace + Scaffolded Writes
status: open
priority: high
tags: [lm, infrastructure, codex-engine, platform]
depends_on: []
project: codex-engine
---

## Scope

Extend the Legendary Map with three new sub-namespaces and a scaffolded write system:

### 1. `oc.*` — OpenClaw Platform Commands
Lift the openclaw CLI command surface into coordinate-addressable LM entries.

**High-value commands to map:**
- `oc.status` — `openclaw status` (overall health)
- `oc.gw` — `openclaw gateway status|start|stop|restart|health`
- `oc.cron` — `openclaw cron list|add|rm|run|status`
- `oc.agent` — `openclaw agent --to {target} --message {msg}`
- `oc.sessions` — `openclaw sessions` (list active)
- `oc.logs` — `openclaw logs --follow`
- `oc.doctor` — `openclaw doctor` (health checks + fixes)
- `oc.memory` — `openclaw memory search|reindex`
- `oc.hooks` — `openclaw hooks list|enable|disable`
- `oc.cost` — `openclaw gateway usage-cost` (spend tracking)

### 2. `sys.*` — System Tools
Common host operations agents reach for frequently.

**Process & Service:**
- `sys.ps` — process listing/search (`ps aux | grep`, `pgrep`)
- `sys.kill` — process termination (`kill`, `pkill`)
- `sys.svc` — systemd service management (`systemctl --user start|stop|restart|status`)
- `sys.cron` — system crontab (`crontab -l`, edit patterns)

**Files & Search:**
- `sys.grep` — pattern search across workspace
- `sys.find` — file discovery
- `sys.tail` — log tailing
- `sys.disk` — disk usage (`df -h`, `du -sh`)

**Network & Diagnostics:**
- `sys.curl` — HTTP requests (health checks, webhooks)
- `sys.net` — port/connection checks (`ss`, `netstat`)
- `sys.top` — resource monitoring

**Git:**
- `sys.git` — git operations (status, commit, push, log, diff)

### 3. Scaffolded Writes (`e2.*` extensions)
Template-driven creation that lays out document skeleton + wires hooks automatically.

**Core scaffolds:**
- `e2.script` — Create a new script with standard header, argparse, logging, and auto-wire into appropriate hook points
- `e2.cron` — Create cron job: script + crontab entry + watchdog pattern
- `e2.hook` — Create an OpenClaw hook: handler file + registration + config entry
- `e2.skill` — Create a skill directory: SKILL.md + references/ + scripts/ (existing skill-creator, but coordinate-native)
- `e2.pipeline` — Create pipeline with all supporting files (direction, state JSON, frontmatter)

**Convention:** Each scaffold:
1. Creates the file with skeleton frontmatter + section headers
2. Wires into relevant systems (crontab, hooks config, plugin registration)
3. Returns the coord of the new entry so you can immediately `e1{coord}` to fill content

### 4. Customized Read Commands (`r.*` extensions)  
Formatted, filtered reads that compress common multi-step lookups.

- `r.health` — Combined gateway + render engine + experiment status
- `r.cost` — Token usage + cost summary across sessions
- `r.experiments` — All running/completed experiments with results
- `r.recent` — Last N changes across all namespaces (like `git log` for primitives)

## Design Principles

- Each LM entry IS the invocation, not docs about it
- Entries auto-generate from discovered command surfaces where possible
- Scaffolds create real files with real wiring, not just templates
- System tools map to the most common invocation pattern, not the full man page
- Everything degrades gracefully if the target isn't available

## Implementation

Single new file: `scripts/codex_lm_platform.py` (~300-400L)
- Auto-discovers openclaw CLI subcommands via `openclaw help` parsing
- Maps system tools to curated invocation patterns
- Scaffold templates as Python dicts/strings
- Plugs into existing `codex_lm_renderer.py` registration system

### 5. Subagent Context Views (`ctx.*`)
Auto-generated coordinate maps for subagent spawns, rendered by the existing render engine.

**Architecture:**
- Render engine already has full filesystem tree in RAM (F-labels from inotify)
- New `render_subagent_context(task_type)` method assembles a filesystem-oriented view
- Auto-coordinate assignment: `a1`–`z9`, `aa1`... over discovered files
- Coordinates are navigable — subagent can zoom into any file by coord
- UDS interface: `{"cmd": "context", "mode": "subagent", "task_type": "code_fix"}`
- No disk footprint — rendered on demand from RAM state

**Task-type tailoring:**
- `code_fix` → relevant source files + scripts + recent diffs
- `analysis` → data files + notebooks + results
- `infrastructure` → configs + services + logs

**Current state:** Legend primer only (via ralph-wiggum skill). Full subagent views deferred.

## Design Decisions (Resolved)

1. **Auto-exec, not render.** `oc.gw` executes `openclaw gateway status` via codex_engine.py and returns output directly. No intermediate render step. Saves tokens.
2. **Full autowire.** Scaffolds create files AND wire into hooks/crontab/config. Documentation baked into the scaffold's output view so the agent knows what was wired and how to proceed.
3. **Curated, extensible via e3.** Start with high-value tools. Agents extend via `e3 sys.{newtool}` as needed — the tools you collect become a memory of what you do.
