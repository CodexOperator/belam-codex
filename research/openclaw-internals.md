# OpenClaw Internals: Orchestration Integration Points

**Date:** 2026-03-21  
**Purpose:** Map extension points for custom orchestration into OpenClaw  
**Source:** Static analysis of `/usr/lib/node_modules/openclaw/dist/` + config

---

## 1. Session System

### Session Key Format
```
agent:<agentId>:<rest>
```

Key variants:
| Pattern | Description |
|---|---|
| `agent:main:main` | Main session (canonical) |
| `agent:<id>:subagent:<uuid>` | Spawned subagent |
| `agent:<id>:cron:<name>:run:<uuid>` | Cron run |
| `agent:<id>:acp:<uuid>` | ACP bridge session |
| `agent:<id>:<channel>:...` | Channel-scoped sessions |

Thread sessions use `:thread:` or `:topic:` markers within the key.  
Depth is counted by the number of `:subagent:` splits.

### sessions_spawn Tool (Agent-internal)
Spawns a subagent from within an agent session. Key parameters:
- `task` (required) — full task description
- `label` — human-readable label; used by `sessions_send` to target by name
- `agentId` — target agent (defaults to same agent); must be in `subagents.allowAgents`
- `model` — model override (provider/model format)
- `thinking` — thinking level override
- `thread` (bool) — bind to a channel thread (requires channel plugin support)
- `mode` — `"run"` (ephemeral, default) or `"session"` (persistent, requires `thread=true`)
- `sandbox` — `"inherit"` (default) or `"require"`
- `runtime` — `"subagent"` (default) or `"acp"` (for IDE/ACP harness sessions)
- `cleanup` — `"keep"` or `"delete"` (for run mode)
- `runTimeoutSeconds` — timeout override
- `streamTo` — `"parent"` (relay streaming output to parent session)

**Depth limit:** Configurable via `agents.defaults.subagents.maxSpawnDepth` (default: 1)  
**Concurrency:** `agents.defaults.subagents.maxConcurrent` (config: 8) and `maxChildrenPerAgent` (default: 5)

### sessions_send Tool (Agent-internal)
Send a message into another session:
- Target by `sessionKey` (full key) or `label` (resolved via `sessions.resolve` RPC)
- Optionally scope with `agentId` for cross-agent sends
- Cross-agent sends require `tools.agentToAgent.enabled=true` and both agents in `tools.agentToAgent.allow`

### sessions_yield Tool (Agent-internal)
Ends the current turn (used after spawning subagents to wait for push-based completion events).

**Auto-announce:** Completion events are push-based — arrive as user messages to the spawner. Do NOT poll after spawn.

---

## 2. Gateway RPC API (Programmatic Access)

### Connection
- WebSocket at `ws://localhost:18789` (default port, loopback bind)
- Auth via `gateway.auth` token in config
- CLI: `openclaw gateway call <method> --params '{"key": "value"}'`

### Key RPC Methods
```
chat.send          — Send a message to a session (triggers agent run)
chat.inject        — Inject an assistant message into transcript (no LLM run)
chat.abort         — Abort an active run
chat.history       — Fetch session history

sessions.list      — List sessions
sessions.get       — Get session details
sessions.resolve   — Resolve session by label/key
sessions.patch     — Patch session metadata
sessions.delete    — Delete a session
sessions.reset     — Reset session (clears history)
sessions.preview   — Preview session
sessions.compact   — Compact session transcript
sessions.usage     — Usage stats

agents.list        — List configured agents
agents.create      — Dynamically create an agent
agents.update      — Update agent config
agents.delete      — Delete an agent

cron.add/remove/update/list/run/status  — Cron job management

config.get/set/patch/apply  — Runtime config manipulation
```

**`chat.send` params (key fields):**
- `sessionKey` — target session key
- `message` — text message
- `attachments` — optional array of attachments
- `timeoutMs` — optional timeout

**`chat.inject` params:**  
Writes an assistant message directly into the transcript and broadcasts it — useful for injecting results/context without triggering an LLM run.

**`agents.create`:** Dynamically adds an agent to the running gateway (no restart needed).

**Feasibility: ⭐⭐⭐⭐⭐ HIGH** — Full programmatic control over agent sessions from external scripts via WebSocket RPC. The `gateway call` CLI wrapper makes this scriptable without writing a WebSocket client.

---

## 3. Hooks System

### Hook Locations (Priority Order, later wins)
1. `hooks.internal.load.extraDirs` (config-specified dirs)
2. `~/.openclaw/dist/bundled/` (bundled)
3. `~/.openclaw/hooks/` (managed — `openclaw hooks install`)
4. `<workspace>/hooks/` (workspace — **highest priority**)

**Current state:** `~/.openclaw/hooks/` dir does not exist (not yet used).  
**Workspace hooks** at `~/.openclaw/workspace/hooks/` would be picked up automatically.

### Hook Format
Each hook is a directory containing:
- `HOOK.md` — frontmatter with metadata + description
- `handler.js` or `handler.ts` — the implementation

`HOOK.md` frontmatter (YAML via `metadata.openclaw` block):
```yaml
---
name: my-hook
description: "What this does"
metadata:
  {
    "openclaw": {
      "emoji": "🔧",
      "events": ["gateway:startup"],
      "hookKey": "my-hook",          # key for openclaw.json enable/disable
      "requires": { "config": ["workspace.dir"] }
    }
  }
---
```

### Available Event Types
| Event | Trigger |
|---|---|
| `gateway:startup` | Gateway starts |
| `agent:bootstrap` | Agent initializes (loads workspace context) |
| `command` | Any `/command` issued |
| `command:new` | `/new` command |
| `command:reset` | `/reset` command |

**Feasibility: ⭐⭐⭐⭐ HIGH** — Workspace hooks at `<workspace>/hooks/` are auto-loaded. Can hook into key lifecycle events. Events are limited but cover critical points.

### Bundled Hooks (Available/Configurable)
| Hook | Event | Purpose |
|---|---|---|
| `boot-md` | `gateway:startup` | Run `BOOT.md` at startup |
| `bootstrap-extra-files` | `agent:bootstrap` | Inject extra context files |
| `session-memory` | `command:new/reset` | Save session to memory file |
| `command-logger` | `command` | Audit log all commands |

Enable/disable via `hooks.internal.entries.<hookKey>.enabled`.

---

## 4. Agent Routing

### Config-Driven Agent System
Agents are defined in `openclaw.json` under `agents.list`:
```json
{
  "id": "architect",
  "name": "Belam Architect",
  "workspace": "~/.openclaw/workspace-architect",
  "model": "anthropic/claude-opus-4-6",
  "identity": { "name": "Belam Architect", "emoji": "🏗️" },
  "groupChat": { "mentionPatterns": ["@architect"] }
}
```

**Current agents:** main (Belam), sage, architect, critic, builder

### Routing Mechanisms
1. **Channel bindings** (`bindings` array): Match `channel` + `accountId` → route to `agentId`
2. **Group chat mentions**: `mentionPatterns` in agent config; messages mentioning `@architect` route to that agent
3. **`--agent <id>` CLI flag**: Force routing to specific agent on session start
4. **`agentId` in sessions_spawn**: Target specific agent for subagents

### Agent-to-Agent (A2A) Messaging
- Enabled: `tools.agentToAgent.enabled = true`
- Allow list: `tools.agentToAgent.allow = ["architect", "critic", "builder", "main", "sage"]`
- Use `sessions_send` with `agentId` param for cross-agent sends
- Session keys format: `agent:<targetAgentId>:<rest>`

### Dynamic Agent Creation
Via `agents.create` RPC — can add agents without restart. Useful for spawning pipeline-specific agents.

**Feasibility: ⭐⭐⭐⭐⭐ HIGH** — Full A2A is configured and active. External orchestration can route work by targeting specific session keys or using `chat.send` to any agent session.

---

## 5. MCP Support

**Status: No native MCP server in OpenClaw core.**  
MCP references found only in:
- ACP bridge docs: "Per-session MCP servers unsupported in bridge mode — configure MCP on the OpenClaw gateway instead" (but no gateway-level MCP config found)
- Security threat model: MCP listed as an external tool provider surface
- `mcporter` CLI mentioned in docs as "tool server runtime for managing external skill backends"

**ACP bridge** (`openclaw acp`) implements Agent Client Protocol (ACP) over stdio — the nearest thing to MCP. Supports: `initialize`, `newSession`, `prompt`, `cancel`, `listSessions`, `loadSession`. IDEs (e.g., Cursor, VS Code) that speak ACP can connect via this bridge.

**Feasibility: ⭐⭐ LOW** — No first-class MCP server. Would need external MCP-to-gateway bridge or use ACP protocol instead.

---

## 6. Config Structure (openclaw.json)

Key sections relevant to orchestration:

```json
{
  "agents": {
    "defaults": {
      "model": { "primary": "anthropic/claude-opus-4-6" },
      "maxConcurrent": 4,
      "subagents": { "maxConcurrent": 8 }
    },
    "list": [ /* agent definitions */ ]
  },
  "tools": {
    "sessions": { "visibility": "all" },
    "agentToAgent": {
      "enabled": true,
      "allow": ["architect", "critic", "builder", "main", "sage"]
    }
  },
  "hooks": {
    "internal": {
      "enabled": true,
      "entries": {
        "supermap-boot": { "enabled": true },
        "memory-extract": { "enabled": true },
        "session-memory": { "enabled": false }
      }
    }
  },
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback",
    "auth": "<token>"
  }
}
```

**Runtime config mutation:** `config.patch` RPC allows live config changes without restart.

---

## 7. Integration Patterns for Custom Orchestration

### Pattern A: External Script → Gateway RPC
```bash
# Trigger an agent from external script
openclaw gateway call chat.send \
  --params '{"sessionKey":"agent:main:main","message":"Run pipeline step 2"}' \
  --expect-final
```
**Best for:** Kicking off agent work from cron jobs, webhooks, or pipeline scripts.

### Pattern B: Workspace Hook
Create `~/.openclaw/workspace/hooks/pipeline-trigger/` with:
- `HOOK.md` — listen to `gateway:startup` or `agent:bootstrap`
- `handler.js` — check pipeline state, send messages via gateway RPC
**Best for:** Auto-triggering pipelines on boot or session start.

### Pattern C: Agent-to-Agent via sessions_send
From within an agent:
```
sessions_send(sessionKey="agent:architect:main", message="Analyze task X")
```
**Best for:** In-session coordination between specialized agents.

### Pattern D: sessions_spawn with Label
Spawn a subagent with a label, then communicate back via announce:
```
sessions_spawn(task="...", label="pipeline-step-3", agentId="builder")
# Result auto-announces back when complete
```
**Best for:** Parallel pipeline execution with result aggregation.

### Pattern E: chat.inject for Context Injection
```bash
openclaw gateway call chat.inject \
  --params '{"sessionKey":"agent:main:main","message":"Pipeline completed: result=..."}'
```
**Best for:** Injecting pipeline results into an agent's context without triggering an LLM run.

---

## 8. Current Configuration Notes

- **5 agents active:** main, sage, architect, critic, builder
- **A2A enabled:** All 5 agents can message each other
- **Subagent depth:** Configured at default (1) — subagents cannot spawn further subagents
- **Gateway:** Local-only, port 18789, loopback bind (scripts must run on same host)
- **session-memory hook:** Disabled (could enable for automatic session context preservation)
- **No workspace hooks directory yet** — `~/.openclaw/workspace/hooks/` doesn't exist

### Suggested Config Tuning for Orchestration
```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "maxSpawnDepth": 2,
        "maxConcurrent": 12
      }
    }
  }
}
```
This would allow subagents to spawn their own subagents (depth 2), enabling multi-tier pipeline orchestration.

---

## Summary: Feasibility Matrix

| Extension Point | Feasibility | Notes |
|---|---|---|
| Gateway RPC (`chat.send`) | ⭐⭐⭐⭐⭐ | Full external control; scriptable via `openclaw gateway call` |
| `sessions_spawn` (agent tool) | ⭐⭐⭐⭐⭐ | Primary mechanism for pipeline delegation |
| `sessions_send` (agent tool) | ⭐⭐⭐⭐⭐ | A2A messaging fully configured |
| Workspace hooks (`<workspace>/hooks/`) | ⭐⭐⭐⭐ | Auto-loaded; limited events but covers lifecycle |
| Agent-to-agent routing | ⭐⭐⭐⭐⭐ | 5 agents, all allowed, groupchat patterns set |
| Dynamic agent creation (RPC) | ⭐⭐⭐⭐ | `agents.create` RPC exists; untested |
| `chat.inject` (result injection) | ⭐⭐⭐⭐ | Useful for injecting pipeline output without LLM run |
| MCP native server | ⭐⭐ | Not natively supported; ACP bridge is the nearest equivalent |
| ACP bridge integration | ⭐⭐⭐ | Available but IDE-focused; overhead for orchestration use |
| Custom hook events (user-defined) | ⭐⭐ | Only predefined events; no custom event firing from outside |
