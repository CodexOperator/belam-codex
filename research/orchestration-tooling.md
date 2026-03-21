# Orchestration Tooling Research
**Date:** 2026-03-21  
**Scope:** Off-the-shelf tools and frameworks for multi-agent LLM orchestration  
**Context:** Evaluate against our custom orchestration engine — constraints: no daemon, on-demand, file-native state, ARM64 Oracle Cloud (Ubuntu 22.04 / Python 3.12)

---

## Executive Summary

Our custom engine (`pipeline_orchestrate.py` + `pipeline_autorun.py`) is architecturally sound and better fit for our constraints than any off-the-shelf framework. The main opportunity is **selectively adopting patterns** from the ecosystem rather than replacing anything wholesale. The clearest wins: **MCP as a tool-exposure layer** (adapt) and **SQLite WAL as a lightweight signal bus** (adapt) for future inter-agent coordination.

---

## 1. MCP (Model Context Protocol)

### What It Is
Open standard (Anthropic, now broadly adopted) for connecting AI clients to external context sources. JSON-RPC 2.0 over STDIO or HTTP. Three primitive types:
- **Resources** — readable data (files, DB rows, API responses)
- **Tools** — callable functions (the LLM decides when to invoke)
- **Prompts** — reusable instruction templates

Architecture: Host (Claude/VSCode) → MCP Client → MCP Server(s). One client per server. STDIO transport = local process, no network overhead.

### Building a Custom MCP Server (Python)
Uses `FastMCP` from `mcp[cli]` package (Python 3.10+):
```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("my-server")

@mcp.tool()
def get_pipeline_status(version: str) -> dict:
    """Get current pipeline state for a version."""
    # read from pipelines/{version}.md
    ...

mcp.run()  # STDIO transport, launched on-demand by host
```
Tools are auto-discovered from type hints + docstrings. No persistent daemon — process spawned per connection.

### Can MCP Handle Inter-Agent State Sync?
**No** — not its design goal. MCP is fundamentally client→server read/tool, not peer-to-peer. There's no pub/sub, no agent-to-agent push. It could *expose* our pipeline state as readable resources, but coordination is still the orchestrator's job.

### Feasibility for Our Use Case
| Aspect | Rating |
|--------|--------|
| Tool exposure layer | **High** — STDIO transport, no daemon, Python-native |
| Inter-agent coordination | **Low** — wrong abstraction layer |
| Custom server complexity | **Low** — FastMCP makes it trivial |

**Recommendation: Adapt**  
Build a `pipeline-state` MCP server that exposes pipeline JSON/markdown as Resources and orchestrator operations as Tools. This would let Claude Code and any future MCP-capable agent access pipeline state natively without custom skill files. Low cost, high leverage.

---

## 2. Agent Frameworks

### 2a. LangGraph
**What:** Graph-based state machine for agent workflows. Nodes = agent steps, edges = transitions. Stateful checkpointing via SQLite or Postgres. Used heavily in production LLM pipelines.  
**Inter-agent comms:** Shared state dict passed through graph. No diff protocol — full state replacement per step.  
**Pros:** Mature, well-documented, first-class checkpointing, conditional edges  
**Cons:** Heavy dependency tree (langgraph, langchain-core, etc), requires persistent graph runtime, Python API is verbose, doesn't map cleanly to our stage/agent model  
**ARM64 compatibility:** Should work, no native extensions  

**Feasibility: Medium** — powerful but heavyweight for our on-demand model  
**Recommendation: Ignore** — our pipeline state machine is architecturally equivalent and lighter. LangGraph's checkpointing pattern is worth studying for inspiration but we already have three-tier recovery.

---

### 2b. CrewAI
**What:** Two-layer architecture — **Flows** (event-driven state machine) + **Crews** (autonomous agent teams). Flows manage state and trigger Crews. Python-native. 100k+ certified developers.  
**Inter-agent comms:** Flows pass state between steps. Crews communicate via task delegation and shared context. No diff protocol.  
**Pros:** Clean separation of workflow control (Flow) vs. agent intelligence (Crew), good production story, event-driven execution built-in  
**Cons:** Opinionated role model doesn't match our architect/critic/builder pattern, requires CrewAI server for Flows, dependencies are heavy  

**Feasibility: Low** — structurally similar to what we have but more opaque  
**Recommendation: Ignore** — CrewAI Flows is conceptually equivalent to our `pipeline_orchestrate.py` + JSON state files. Their "Crew" = our "agent session." We'd be trading our lean custom engine for a heavier opinionated framework.

---

### 2c. AutoGen (Microsoft, v0.4+)
**What:** Event-driven multi-agent framework with AgentChat (high-level) and Core (low-level). Patterns: group chat (shared context + selector), swarm (tool-based routing), GraphFlow (directed graph), reflection (critic loop).  
**Inter-agent comms:** Message-passing via shared context. GraphFlow supports DAG-based agent sequencing.  
**Pros:** GraphFlow maps well to our pipeline stages, event-driven core, good for complex topologies  
**Cons:** Heavy framework, requires asyncio event loop infrastructure, shared context model means all agents see everything (not our isolated session model), still evolving API  

**Feasibility: Medium** — GraphFlow pattern is relevant  
**Recommendation: Adapt (pattern only)** — the GraphFlow directed-graph model is worth borrowing as a concept. Our hardcoded transition map in `pipeline_orchestrate.py` could evolve into a proper DAG config (YAML/JSON graph definition), inspired by AutoGen's approach. Don't adopt the library.

---

### 2d. OpenAI Swarm → OpenAI Agents SDK
**What:** Swarm (now archived) was a minimal handoff framework — agents could return another agent as the "next agent." Evolved into **OpenAI Agents SDK** (production). Key features: handoffs, MCP tool integration, tracing, human-in-the-loop, sessions (optional Redis).  
**Inter-agent comms:** Handoffs via function returns. Stateless between calls (like our model). Sessions optional.  
**Pros:** Very lightweight primitives (Agent + Runner), MCP-native, provider-agnostic via LiteLLM, tracing built-in  
**Cons:** Handoffs are synchronous (sequential), no persistent async coordination, sessions require Redis for cross-process state  

**Feasibility: Medium**  
**Recommendation: Adapt (patterns)** — the handoff-as-function-return pattern is elegant and maps well to our model. Their tracing approach (built-in run recording) is worth borrowing — we should emit structured trace events per handoff rather than just Telegram messages.

---

### 2e. PydanticAI
**What:** Pydantic's agent framework. Five levels: single agent, delegation (tool), programmatic handoff, graph-based, deep agents. Clean Python, strongly typed via Pydantic.  
**Inter-agent comms:** Agent delegation via tool calls. Programmatic handoff = run agent A, then call agent B in code. Graph = graph-based state machine.  
**Pros:** Minimal, strongly typed, Pythonic, no framework lock-in, composable  
**Cons:** Younger ecosystem, graph support is new  

**Feasibility: Medium**  
**Recommendation: Adapt (patterns)** — PydanticAI's "programmatic handoff" pattern is exactly what our orchestrator does. Worth studying for the strongly-typed state model. If we ever formalize our pipeline state schema, Pydantic models would be the right tool.

---

### 2f. Agno (formerly Phidata)
**What:** Full-stack agentic runtime. Framework (agents/teams/workflows) + Runtime (FastAPI) + Control Plane (AgentOS UI). SQLite-native session storage. MCP tool integration.  
**Inter-agent comms:** Team coordination, tool delegation.  
**Pros:** SQLite by default (no daemon), MCP-native, own-infrastructure deployment  
**Cons:** Production API server model (FastAPI daemon), more infrastructure than we want  

**Feasibility: Low** — too much infrastructure for on-demand model  
**Recommendation: Ignore** — though the SQLite session storage design is worth noting (aligns with our constraints).

---

## 3. Event-Driven Patterns

### 3a. Redis Pub/Sub
**What:** Classic pub/sub broker. Agents publish events to channels, subscribers receive them.  
**Pros:** Fast, mature, battle-tested  
**Cons:** **Requires Redis daemon** — violates our no-daemon constraint  
**Feasibility: Low**  
**Recommendation: Ignore** for now. Could revisit if we move to containerized deployment.

---

### 3b. File-Based Events (Current Approach)
**What:** Our handoff JSON files (`pipelines/handoffs/*.json`) and pipeline markdown files serve as the event log. Autorun polls every heartbeat cycle.  
**Pros:** Zero dependencies, fully inspectable, recoverable, ARM64-native, `git`-friendly  
**Cons:** Polling latency (heartbeat interval), no push notification to agents  
**Feasibility: High** — it's what we have  
**Recommendation: Adopt (evolve)** — consider adding a lightweight `events/` directory with timestamped event files as a more explicit event log. Autorun reads and archives them.

---

### 3c. SQLite WAL (Write-Ahead Log)
**What:** SQLite's WAL mode allows concurrent readers + one writer. Combined with `NOTIFY`-style polling or the `watchdog` library (filesystem events), it's a zero-daemon event bus.  
**Pros:** No daemon, Python `sqlite3` built-in (v3.45.1 on this machine), single file, ACID, concurrent safe, queryable  
**Cons:** Polling or watchdog required for push semantics; slightly more complex than flat files  

**Pattern:**
```python
import sqlite3

# Writer (orchestrator)
conn = sqlite3.connect("events.db")
conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, type TEXT, payload TEXT, ts REAL)")
conn.execute("INSERT INTO events VALUES (NULL, 'handoff_complete', ?, ?)", (json.dumps(payload), time.time()))
conn.commit()

# Reader (any agent, polled or via watchdog)
last_id = 0
rows = conn.execute("SELECT id, type, payload FROM events WHERE id > ?", (last_id,)).fetchall()
```

**Feasibility: High** — zero dependencies beyond stdlib  
**Recommendation: Adapt** — strong candidate for V2 event bus. Gives us queryable history, schema-enforced events, and concurrent-safe writes without any daemon. Watchdog lib (no daemon itself) can trigger immediate reads on WAL changes.

---

### 3d. Python Watchdog
**What:** Cross-platform filesystem event library. Detects file creates/modifies/deletes via inotify (Linux), kqueue (macOS), ReadDirectoryChangesW (Windows).  
**Pros:** No daemon, pure Python, `inotify`-backed on Linux (very low overhead), detects new handoff files immediately  
**Cons:** Requires background thread within process (not cross-process push)  
**Feasibility: Medium** — useful for within-process event detection  
**Recommendation: Adapt** — if autorun ever runs as a long-lived process, watchdog can replace heartbeat polling. For now, cron + polling is simpler.

---

## 4. State Management

### How Others Handle It

| Framework | State Model | Diff/Patch |
|-----------|-------------|------------|
| LangGraph | Typed state dict, checkpointed per node | No — full snapshot |
| CrewAI | Flow state dict, passed between steps | No |
| AutoGen | Shared message history | No |
| OpenAI Agents | Stateless + optional session store | No |
| Temporal | Event sourced — event log IS the state | Yes (effectively) |
| Our system | JSON files + Markdown with frontmatter | Partial — git can diff |

**Key insight:** No mainstream framework uses diff/patch protocols for inter-agent context sync. The closest is **Temporal**'s event-sourcing model (the event log is the canonical state; current state is derived by replaying events). This is conceptually elegant but requires Temporal's infrastructure.

### Diff-Friendly State (Our Opportunity)
Our markdown+YAML frontmatter format is inherently diff-friendly (text-based). The gap is that agents don't currently *use* diffs to sync — they re-read full files each session. A lightweight improvement:

```python
# In pipeline_orchestrate.py, after updating pipeline state:
# Write a compact "delta" alongside the full state
delta = {
    "ts": now(),
    "stage": old_stage,
    "new_stage": new_stage,
    "agent": agent,
    "changed_keys": ["status", "current_stage", "updated_at"],
}
(PIPELINES_DIR / f"{version}_deltas.jsonl").open("a").write(json.dumps(delta) + "\n")
```

This gives agents a cheap "what changed since I last looked" query without full file reads.

**Recommendation: Evolve our own** — add a `_deltas.jsonl` sidecar per pipeline as a lightweight diff log.

---

## 5. Temporal Coordination

### How Others Handle Async Waiting

| Tool | Pattern |
|------|---------|
| Temporal | Durable sleep (`workflow.sleep()`), signal-based wakeup |
| LangGraph | Human-in-the-loop via interrupt nodes |
| CrewAI | Flow `@listen(event)` decorators |
| AutoGen | Human-in-the-loop via `UserProxyAgent` |
| OpenAI Agents SDK | `interrupt()` + `approve()` API for HITL |
| Our system | Checkpoint-and-resume + stall detection (polling) |

### Temporal (Full Evaluation)
**What:** Durable execution platform. Workflows survive crashes, restarts, and months of inactivity. Sleep is free. Signal-based wakeup. Polyglot.  
**Pros:** True durable execution, signals as first-class primitives, battle-tested at scale  
**Cons:** **Requires Temporal server daemon** (Go service). Heavy. Misaligned with on-demand model. Total overengineering for our scale.  
**Feasibility: Low**  
**Recommendation: Ignore** — Temporal solves a much harder problem than we have.

### Signal-Based Coordination (Our Gap)
Our current coordination is polling-based (heartbeat). The missing primitive is **agent wakeup signals** — a way for one agent to *immediately* trigger another without waiting for the next heartbeat cycle.

We partially solve this with `openclaw agent` CLI calls in `pipeline_orchestrate.py`. The gap is *passive waiting* — when an agent needs to wait for an external condition (e.g., human approval, upstream pipeline completing), it currently relies on stall detection (2h timeout) rather than explicit signals.

**Pattern to borrow from OpenAI Agents SDK:**
```python
# Explicit interrupt-and-resume pattern
def complete_stage_with_gate(version, stage):
    if requires_human_approval(version, stage):
        write_gate_file(version, stage)  # Drop a file, don't block
        notify_human(version, stage)
        return "gated"   # Agent exits cleanly
    # ... continue normal handoff
```

We already do something like this with gate files — the autorun script checks them. Worth formalizing as an explicit primitive.

---

## 6. Constraint Matrix

| Tool/Pattern | No Daemon | Python Native | File-Native | ARM64 | On-Demand |
|---|:---:|:---:|:---:|:---:|:---:|
| MCP (STDIO) | ✅ | ✅ | ✅ | ✅ | ✅ |
| LangGraph | ✅ | ✅ | ❌ | ✅ | ⚠️ |
| CrewAI | ⚠️ | ✅ | ❌ | ✅ | ❌ |
| AutoGen | ✅ | ✅ | ❌ | ✅ | ⚠️ |
| OpenAI Agents SDK | ✅ | ✅ | ❌ | ✅ | ✅ |
| PydanticAI | ✅ | ✅ | ❌ | ✅ | ✅ |
| Agno | ❌ | ✅ | ✅ | ✅ | ❌ |
| Redis pub/sub | ❌ | ✅ | ❌ | ✅ | ❌ |
| SQLite WAL | ✅ | ✅ | ✅ | ✅ | ✅ |
| File-based events | ✅ | ✅ | ✅ | ✅ | ✅ |
| Temporal | ❌ | ✅ | ❌ | ✅ | ❌ |
| **Our system** | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 7. Consolidated Recommendations

### Adopt
**Nothing wholesale.** No framework aligns with our constraints well enough to replace what we have. Our file-native, on-demand, no-daemon model is a genuine differentiator — it's portable, inspectable, and zero-infrastructure. Most frameworks implicitly assume a persistent process.

### Adapt (High Value)

1. **MCP Tool Server for Pipeline State** *(high value, low effort)*  
   Build a `pipeline-state` MCP server using `FastMCP` that exposes:
   - Resources: `pipeline/{version}/state`, `pipeline/{version}/history`
   - Tools: `orchestrate_complete`, `orchestrate_block`, `check_pending`
   
   This makes our orchestration layer MCP-native, accessible from Claude Code and any future MCP client. STDIO transport = spawned on-demand, no daemon.

2. **SQLite WAL Event Bus** *(medium value, medium effort)*  
   Replace per-handoff JSON files with a single `pipelines/events.db` SQLite database in WAL mode. Benefits: queryable history, atomic writes, concurrent reads, JSONL-equivalent but indexed.

3. **Typed Pipeline State (Pydantic)** *(medium value, low effort)*  
   Add Pydantic models to `pipeline_orchestrate.py` for pipeline state validation. Catches corrupt state early. Zero new dependencies (Pydantic is already available in the ecosystem).

4. **Delta/Diff Sidecar Log** *(low value, low effort)*  
   Add `{version}_deltas.jsonl` alongside each pipeline file. Records what changed per handoff. Lets agents and the orchestrator quickly check "what changed since I last processed this" without reading full state.

5. **DAG-Configured Transitions** *(medium value, medium effort)*  
   Move the hardcoded transition map in `pipeline_orchestrate.py` to a YAML/JSON config per pipeline type. Inspired by LangGraph/AutoGen GraphFlow. Makes new pipeline topologies addable without code changes.

### Ignore
- LangGraph, CrewAI, AutoGen, Agno — heavy frameworks, wrong fit
- Redis, Temporal — daemon requirement disqualifies them
- Swarm (archived) — replaced by Agents SDK, but we don't need it
- OpenAI Agents SDK as primary framework — good patterns, but we're already doing what it does, more portably

---

## 8. V1 Architecture Recommendation

**Stay the course, sharpen the edges.**

Our current architecture — `pipeline_orchestrate.py` as handoff engine, `pipeline_autorun.py` as heartbeat-driven automation, file-based state, three-tier recovery — is production-appropriate and constraint-aligned. No framework surveyed would improve it without adding infrastructure complexity.

**V1 improvements worth making (in priority order):**

1. **MCP server for pipeline state** — makes orchestration accessible as a standard tool interface, future-proofs for any MCP-compatible host
2. **Pydantic state models** — catch state corruption at the boundary, cheaply
3. **DAG transition config** — decouple pipeline topology from orchestrator code
4. **Delta log sidecars** — give agents a fast "changed since last check" primitive
5. **SQLite event bus** — revisit for V2 if we need cross-pipeline event coordination

**The mental model that holds:**  
> Files as first-class state. Scripts as on-demand workers. Sessions as isolated compute. Heartbeat as the coordination clock. Telegram as the human interface.

This maps cleanly to our ARM64 Oracle Cloud environment: no services to manage, no daemons to monitor, instant recovery from reboot (cron restores everything), and every piece of state is grep-able.

---

*Research by: subagent `research-orchestration` | Date: 2026-03-21*
