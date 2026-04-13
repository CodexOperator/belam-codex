# Orchestration V3 Monitoring — Phase 2 Architect Design

**Pipeline:** orchestration-v3-monitoring
**Phase:** 2 (Human-in-the-Loop)
**Date:** 2026-03-22
**Architect:** architect

---

## Core Directive

**Script-led, not agent-led orchestration.** The orchestration script is the PILOT — it holds the execution graph, makes dispatch decisions, manages handoffs, detects stalls, and drives recovery. Agents are engines/thrusters — they receive scoped work packages, execute, and report back.

Phase 2 strengthens this pattern by:
1. Connecting the monitoring views to the render engine's live data stream
2. Making the script's R-label trail the real-time narrative of what the system is doing
3. Turning the .v namespace into the communication channel between script-pilot and agent-observer

---

## Architecture Overview

```
                       ┌─────────────────────────┐
                       │   codex_render.py        │
                       │   (RAM tree + inotify)   │
                       │   UDS: ~/.belam_render   │
                       │   .sock                  │
                       └──────┬──────────────┬────┘
                              │              │
                    diff stream          tree queries
                    (push via UDS)       (pull via UDS)
                              │              │
              ┌───────────────┴──────────────┴────────────┐
              │          monitoring_views.py v2            │
              │  .v1 turn-by-turn  (render engine + DB)   │
              │  .v2 live-diff     (render engine diffs)  │
              │  .v3 timeline      (DB temporal data)     │
              │  .v4 agent-context (DB lineage data)      │
              │  .v5 R-label trail (NEW — render diffs)   │
              └───────────────┬───────────────────────────┘
                              │
                              │ rendered views
                              │
              ┌───────────────┴───────────────────────────┐
              │        orchestration_engine.py             │
              │  F-label generation ──→ disk write ──→     │
              │  inotify ──→ render engine ──→ R-label     │
              │  DispatchPayload now includes view_context │
              │  Smarter stall detection via render diffs  │
              └───────────────┬───────────────────────────┘
                              │
                              │ dispatch payloads with
                              │ embedded view context
                              ▼
                         Agent Sessions
```

**Data flow for an F→R label round-trip:**
1. Orchestration engine writes a state change → generates F-label → updates pipeline .md on disk
2. Render engine's inotify detects file change → updates RAM tree → generates DiffEntry
3. DiffEntry flows to connected UDS clients as `{"event": "change", "diff": {...}}`
4. Monitoring views read from render engine (tree + diff buffer) instead of polling files
5. The R-label (render-side delta) is the render engine's DiffEntry rendered in Δ/+/− format
6. Agent or human sees the R-label trail in .v5 and knows what the script just decided

---

## Module Changes

### 1. monitoring_views.py — Render Engine Integration

**Goal:** Views read from the render engine's RAM tree via UDS, not from files or raw DB queries.

#### 1a. RenderClient helper class (NEW)

```python
class RenderClient:
    """Thin UDS client for monitoring views to query the render engine."""
    
    SOCKET = Path.home() / '.belam_render.sock'
    
    def __init__(self, timeout: float = 2.0):
        self._timeout = timeout
    
    def query(self, cmd: str, **kwargs) -> dict | None:
        """Single-shot UDS query. Returns response dict or None."""
        # Connect → send JSON-line → read JSON-line → close
        # Graceful: returns None if engine not running
    
    def get_tree_node(self, coord: str) -> dict | None:
        """Get a single primitive node from RAM tree."""
        return self.query('tree', coord=coord)
    
    def get_namespace(self, prefix: str) -> list[dict]:
        """Get all nodes in a namespace from RAM tree."""
        resp = self.query('tree', prefix=prefix)
        return resp.get('nodes', []) if resp else []
    
    def get_diff_since(self, timestamp: float) -> str:
        """Get render diffs since timestamp."""
        resp = self.query('diff_since', timestamp=timestamp)
        return resp.get('delta', '') if resp else ''
    
    def get_supermap(self) -> str:
        """Get current supermap from RAM."""
        resp = self.query('supermap')
        return resp.get('content', '') if resp else ''
    
    def is_available(self) -> bool:
        """Check if render engine is running."""
        return self.SOCKET.exists()
```

**Fallback:** When render engine isn't running, views fall back to current behavior (DB queries, file reads). The `RenderClient.query()` returning `None` triggers fallback paths in each renderer.

#### 1b. View renderers — dual-source reads

Each renderer gains a `render_client` parameter (default `None`). When available, it reads from the render engine first. When not, falls back to existing TemporalOverlay queries.

- **v1 (turn-by-turn):** Pipeline status from render engine tree (`prefix='p'` → pipeline nodes with frontmatter.status). Agent presence from DB (render engine doesn't track ephemeral agent state). Merged view.
- **v2 (live-diff):** Primary source becomes `render_client.get_diff_since()` instead of raw `overlay._get_conn()` query. **This fixes FLAG-2** (no more private `_get_conn` access). DB transitions used as secondary detail enrichment only.
- **v3 (timeline):** Stays DB-primary — timeline is historical data, render engine is live state. No change needed.
- **v4 (agent-context):** Stays DB-primary — design lineage is historical narrative. No change needed.

#### 1c. New view: v5 R-label trail (NEW)

```python
def render_r_label_trail(pipeline: str = None, persona: str = None,
                         overlay=None, render_client: RenderClient = None,
                         window_minutes: int = 30) -> str:
    """v5: R-label trail — real-time narrative of script-pilot decisions.
    
    Shows the render engine's diff stream as a temporal narrative:
    - Each DiffEntry becomes an R-label line
    - Grouped by time window (default 30 min)
    - Pipeline-filterable
    - Shows what changed, when, and (via F-label correlation) why
    """
```

This is the **key new view** — it's the communication channel where the agent-observer can see what the script-pilot is doing in real time. The R-labels from the render engine's diff buffer are the script's decision trail made visible.

#### 1d. VIEW_REGISTRY update

```python
VIEW_REGISTRY[5] = ViewEntry(
    number=5,
    name='r-label-trail',
    description='Real-time R-label narrative of script-pilot decisions',
    renderer=render_r_label_trail,
)
```

### 2. wal_watcher.py — Render Engine as Primary Data Source

**Goal:** The WAL watcher becomes a thin render-engine consumer, not an independent DB poller.

#### 2a. Dual-mode operation

```python
class WALWatcher:
    def __init__(self, ..., render_client: RenderClient = None):
        self._render_client = render_client or RenderClient()
        self._use_render_engine = self._render_client.is_available()
```

**When render engine is running:**
- Subscribe to UDS change notifications instead of polling WAL file
- Dashboard data assembled from render engine tree + DB (for historical data)
- Change detection is push-based (UDS events) rather than poll-based (WAL stat)

**When render engine is not running:**
- Falls back to current WAL polling behavior (unchanged)

#### 2b. HTML dashboard — stats escaping (FLAG-3 fix)

All values interpolated into HTML go through `html_escape()`, including stats dict values. Currently stats are integers so no real risk, but consistency matters.

```python
# Before (FLAG-3):
{stats.get('total_pipelines', 0)} pipelines

# After:
{html_escape(str(stats.get('total_pipelines', 0)))} pipelines
```

### 3. orchestration_engine.py — Script-Pilot Enhancements

**Goal:** The engine becomes smarter about dispatch, sequencing, and recovery. Its decisions flow through as F-labels that become R-labels in the render engine.

#### 3a. F-label → Render Engine notification

After `_post_state_change()` generates F-labels and writes pipeline state to disk, it also signals the render engine directly via UDS if available. This ensures the render engine picks up changes immediately (not waiting for inotify latency).

```python
def _post_state_change(version, from_stage, to_stage, agent, action, notes='', next_agent=''):
    # ... existing temporal logging ...
    
    # Signal render engine for immediate pickup
    try:
        from codex_render import _signal_render_engine
        # The render engine's inotify will also detect the disk write,
        # but this explicit signal ensures sub-100ms R-label latency
        _signal_render_engine('anchor_reset')  # or a new 'refresh' command
    except (ImportError, Exception):
        pass  # Non-fatal
```

**Note:** This is a hint, not the primary mechanism. The inotify path is the primary — this just reduces latency from ~100ms (inotify coalesce window) to near-zero for critical state changes.

#### 3b. heartbeat_extended session_id fix (FLAG-1)

**Problem:** `heartbeat_extended()` in temporal_overlay.py overwrites `session_id` column with a JSON blob when `context_snapshot` is provided.

**Fix:** Add a `context_json TEXT` column to `agent_presence` via a v2.1 micro-migration. Move the context snapshot there. `session_id` remains a plain string.

```sql
-- Migration v2.1
ALTER TABLE agent_presence ADD COLUMN context_json TEXT DEFAULT NULL;
```

```python
def heartbeat_extended(self, agent, session_id, status='working',
                       current_pipeline=None, context_snapshot=None, **kwargs):
    # session_id stays as plain string
    # context_snapshot goes to context_json column
    self._conn.execute(
        "INSERT OR REPLACE INTO agent_presence "
        "(agent, session_id, status, current_pipeline, context_json, ...) "
        "VALUES (?, ?, ?, ?, ?, ...)",
        (agent, session_id, status, current_pipeline,
         json.dumps(context_snapshot) if context_snapshot else None, ...)
    )
```

#### 3c. compute_f_r_causal_chain — full implementation (FLAG-4)

**Problem:** Current implementation is a stub doing string matching on F-labels.

**Design:** The function becomes a proper causal chain analyzer that:
1. Parses F-labels into structured `(coord, field, old_value, new_value)` tuples
2. Queries the render engine's diff buffer for corresponding R-labels
3. Walks the dependency graph to find cascading effects
4. Returns structured output: `{f_labels, r_labels, cascading_deps, orphaned_handoffs}`

```python
def compute_f_r_causal_chain(f_labels: list[str], db_path=DEFAULT_DB_PATH) -> dict:
    """Given F-labels from a revert, compute full causal chain.
    
    1. Parse F-labels → structured field changes
    2. Query render engine for R-labels corresponding to same coords
    3. Walk dependency graph: if reverted stage < completion,
       any downstream deps satisfied by this version become suspect
    4. Check handoff table: active handoffs from this pipeline
       become orphaned if the stage they reference no longer exists
    
    Returns:
        f_labels: original F-labels
        r_labels: corresponding render-side changes
        cascading_deps: [{target, was_satisfied_by, now_suspect}]
        orphaned_handoffs: [{handoff_id, target_agent, completed_stage}]
        impact_summary: human-readable one-liner
    """
```

#### 3d. DispatchPayload view_context enrichment

When dispatching an agent, the engine includes a snapshot of the relevant .v5 trail in the payload. This gives the agent immediate situational awareness — it can see what the script-pilot did leading up to this dispatch.

```python
@dataclass
class DispatchPayload:
    # ... existing fields ...
    
    # Phase 2: Embedded view context for agent situational awareness
    view_context: str = ''  # Pre-rendered .v5 trail for this pipeline
```

The engine calls `render_r_label_trail(pipeline=version, window_minutes=10)` and embeds the result. The agent sees the last 10 minutes of R-label activity without needing to query anything.

### 4. temporal_overlay.py — Public API for Transitions

**Goal:** Expose a public method for querying transitions, eliminating the private `_get_conn()` access from monitoring_views.py.

```python
class TemporalOverlay:
    def get_transitions_since(self, since: str, version: str = None,
                              limit: int = 100) -> list[dict]:
        """Public API: get state transitions since ISO timestamp.
        
        Args:
            since: ISO timestamp string
            version: optional pipeline filter
            limit: max rows (default 100)
        
        Returns list of transition dicts.
        """
        conn = self._get_conn()
        if version:
            rows = conn.execute(
                "SELECT * FROM state_transition "
                "WHERE version = ? AND timestamp > ? "
                "ORDER BY timestamp ASC LIMIT ?",
                (version, since, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM state_transition "
                "WHERE timestamp > ? ORDER BY timestamp ASC LIMIT ?",
                (since, limit)
            ).fetchall()
        return [dict(row) for row in rows]
```

### 5. temporal_schema.py — v2.1 Micro-Migration

```python
MIGRATION_V2_1_SQL = """
-- Add context_json column to agent_presence (FLAG-1 fix)
ALTER TABLE agent_presence ADD COLUMN context_json TEXT DEFAULT NULL;
"""

def migrate_v2_to_v2_1(conn):
    """Micro-migration: add context_json column."""
    try:
        conn.execute("SELECT context_json FROM agent_presence LIMIT 1")
    except Exception:
        conn.execute(MIGRATION_V2_1_SQL)
        conn.commit()
```

### 6. codex_render.py — New UDS Commands

Two new UDS commands to support monitoring integration:

```python
# In SessionManager._dispatch():

elif cmd == 'refresh':
    """Hint: re-scan a specific file or namespace."""
    filepath = msg.get('filepath')
    prefix = msg.get('prefix')
    if filepath:
        diff = self.tree.apply_disk_change(Path(filepath))
        if diff:
            self.diff_engine.record(diff)
            self.notify_all({'event': 'change', 'diff': asdict(diff)})
        return {'ok': True}
    elif prefix:
        diffs = self.tree.reindex_namespace(prefix)
        return {'ok': True, 'reindexed': len(diffs)}
    return {'ok': False, 'error': 'specify filepath or prefix'}

elif cmd == 'subscribe':
    """Subscribe this connection to push notifications."""
    # Already happens implicitly via attach, but this makes it explicit
    # and allows filtering by prefix/coord pattern
    patterns = msg.get('patterns', [])  # e.g., ['p*', 'm*']
    with self._lock:
        session = self._sessions.get(session_id)
        if session:
            session.subscribe_patterns = patterns
    return {'ok': True}
```

---

## Phase 1 FLAG Resolution Summary

| FLAG | Severity | Fix | Module |
|------|----------|-----|--------|
| FLAG-1: heartbeat_extended session_id | MED | Add `context_json` column, micro-migration v2.1 | temporal_overlay.py, temporal_schema.py |
| FLAG-2: render_live_diff private _get_conn | LOW | Add `get_transitions_since()` public method + RenderClient as primary source | temporal_overlay.py, monitoring_views.py |
| FLAG-3: HTML stats unescaped | LOW | `html_escape()` all interpolated values | wal_watcher.py |
| FLAG-4: compute_f_r_causal_chain placeholder | LOW | Full implementation with render engine + dep graph integration | dependency_graph.py |

---

## File Change Summary

| File | Action | Lines (est.) |
|------|--------|-------------|
| monitoring_views.py | MODIFY | +120 (RenderClient, v5 renderer, dual-source reads) |
| wal_watcher.py | MODIFY | +40 (render engine mode, HTML escaping) |
| orchestration_engine.py | MODIFY | +30 (render signal in _post_state_change, view_context in dispatch) |
| temporal_overlay.py | MODIFY | +25 (get_transitions_since, heartbeat_extended fix) |
| temporal_schema.py | MODIFY | +15 (v2.1 migration) |
| dependency_graph.py | MODIFY | +60 (full compute_f_r_causal_chain) |
| codex_render.py | MODIFY | +25 (refresh + subscribe commands) |

**Total:** ~315 lines changed/added across 7 files. No new files — all changes are enhancements to existing modules.

---

## Design Decisions

### D1: Render engine as optional accelerator, not hard dependency

Every view renderer has a fallback path when the render engine isn't running. The render engine improves latency and eliminates file polling, but the system works without it. This preserves the graceful degradation pattern established in Phase 1.

### D2: R-label trail as dedicated view (.v5), not merged into .v2

The R-label trail is conceptually different from the DB-backed live diff (.v2). The R-label trail is the render engine's perspective — what changed in the RAM tree. The live diff is the temporal DB's perspective — what state transitions occurred. They often correlate but have different sources and granularity. Keeping them separate preserves clarity.

### D3: Push notifications via existing UDS, not a new event system

The render engine's `notify_all()` already pushes change events to connected clients. Rather than building a separate event bus, monitoring views connect as UDS clients when they need streaming data. Simple, no new infrastructure.

### D4: F-label → R-label correlation is temporal, not structural

F-labels and R-labels are correlated by timestamp proximity, not by explicit linking. When the engine writes an F-label (disk change), the render engine produces an R-label (diff entry) within ~100ms. The .v5 trail interleaves them by timestamp. This avoids coupling the orchestration engine to the render engine's internal DiffEntry format.

### D5: DispatchPayload carries pre-rendered view, not view coordinates

Agents receive a rendered text snapshot of the R-label trail, not coordinates they need to resolve. This keeps agents as pure executors — they don't need UDS client code or view resolution logic. The script-pilot decides what context the agent sees.

---

## Integration Contract with codex_render.py

The design depends on these existing render engine capabilities:
- **UDS server** at `~/.belam_render.sock` (JSON-line protocol) ✓
- **`diff_since` command** returning delta since timestamp ✓
- **`tree` command** returning nodes by coord or prefix ✓
- **`notify_all()`** pushing change events to connected clients ✓
- **`supermap` command** returning rendered supermap ✓

New capabilities needed (minimal):
- **`refresh` command** — explicit file/namespace re-scan (latency hint)
- **`subscribe` command** — filtered push notifications (optional optimization)

Both are small additions to the existing `_dispatch()` method in SessionManager.

---

## Sequencing

1. **temporal_schema.py** — v2.1 migration (FLAG-1 prerequisite)
2. **temporal_overlay.py** — `get_transitions_since()` + heartbeat fix (FLAG-1, FLAG-2)
3. **codex_render.py** — refresh + subscribe commands
4. **monitoring_views.py** — RenderClient + v5 renderer + dual-source reads (FLAG-2)
5. **dependency_graph.py** — full compute_f_r_causal_chain (FLAG-4)
6. **wal_watcher.py** — render engine mode + HTML escaping (FLAG-3)
7. **orchestration_engine.py** — render signal + view_context dispatch

Items 1-3 are independent prerequisites. Items 4-7 depend on 1-3 but are independent of each other.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Render engine not running during builds | Medium | Low | All views have DB fallback paths |
| UDS connection overhead per view render | Low | Low | Single-shot queries (~1ms), no persistent connections needed |
| v2.1 migration on existing DBs | Low | Low | ALTER TABLE ADD COLUMN is safe on SQLite, idempotent check |
| R-label trail volume in long sessions | Low | Medium | Window parameter (default 30min) + configurable limit |

---

## Success Criteria

1. `.v2` no longer uses `overlay._get_conn()` — uses public API or render client
2. `.v5` shows real-time R-label narrative when render engine is running
3. `heartbeat_extended()` stores context in dedicated column, not session_id
4. `compute_f_r_causal_chain()` returns structured dep + handoff impact data
5. All HTML output properly escaped
6. DispatchPayload includes view_context with recent R-label trail
7. All views degrade gracefully when render engine is offline
