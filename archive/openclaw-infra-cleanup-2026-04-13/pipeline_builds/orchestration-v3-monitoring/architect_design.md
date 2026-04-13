# Orchestration V3: Real-Time Monitoring Suite — Architect Design

**Pipeline:** orchestration-v3-monitoring
**Stage:** architect_design
**Date:** 2026-03-21
**Architecture:** Option C (hybrid) — confirmed by Shael

---

## 1. Executive Summary

V3 adds a **real-time monitoring layer** on top of the V2-temporal SQLite overlay. Two delivery paths:

1. **Per-turn injection** — codex engine embeds `.v` view data into dispatch payloads (agent-facing)
2. **Lightweight watcher** — SQLite WAL polling process renders live dashboard via OpenClaw canvas (human-facing)

Both paths read from the same `temporal.db` — zero duplication. The `.v` (view) namespace extends the coordinate system with composable view types bound to pipeline coordinates.

---

## 2. Architecture: Option C Hybrid

```
┌─────────────────────────────────────────────────────────────────┐
│                     SQLite temporal.db (WAL)                    │
│  pipeline_state │ state_transition │ handoff │ agent_context    │
│  agent_presence │ view_config (NEW) │ dep_graph (NEW)          │
└──────────┬──────────────────────────┬──────────────────────────┘
           │                          │
    ┌──────▼──────┐           ┌───────▼──────┐
    │  Per-Turn   │           │  WAL Watcher │
    │  Injection  │           │  (daemon)    │
    │             │           │              │
    │ e0p1.v1-v4  │           │ Canvas render│
    │ in dispatch │           │ for Shael    │
    │ payloads    │           │              │
    └─────────────┘           └──────────────┘
     Agent-facing              Human-facing
```

### Why Hybrid

- **Per-turn injection** costs zero extra processes. The codex engine already builds dispatch payloads — we add `.v` view rendering as a payload extension. Agents see pipeline state in their context window.
- **WAL watcher** provides live streaming for Shael without agents needing to be active. Lightweight: single-threaded Python polling SQLite WAL changes at configurable intervals.
- **No duplication** — both paths query the same `temporal.db`. WAL mode guarantees concurrent read safety.

---

## 3. `.v` (View) Namespace Design

### 3.1 Coordinate Grammar

```
e0p{N}.v{M}          # Scoped view: pipeline N, view type M
e0.v{M}  / e0v{M}    # Global view: all pipelines, view type M
e0.v     / e0v        # List available view types
```

The dot (`.`) binds the view type to the pipeline coordinate. This is a **suffix modifier**, not a separate namespace — the view is always *of* something.

### 3.2 View Types

| Coord | Name | Description | Data Source |
|-------|------|-------------|-------------|
| `.v1` | Turn-by-turn | Snapshot dashboard injected per agent turn | `get_dashboard(persona=)` |
| `.v2` | Live diff | Continuous diffs between agent turns | `state_transition` table, diffed |
| `.v3` | Timeline | Stage progression, durations, bottlenecks | `get_timeline()` + `get_stage_durations()` |
| `.v4` | Agent context | Decisions, flags, learnings for pipeline agents | `get_agent_context()` + `get_design_lineage()` |

### 3.3 Resolution Logic

View coordinates resolve in `orchestration_engine.py`'s dispatch path:

```python
def resolve_view(coord: str) -> ViewResult:
    """
    Parse: e0p3.v2 → pipeline='p3', view_type=2
    Parse: e0v1    → pipeline=None (global), view_type=1
    Parse: e0.v    → pipeline=None, view_type=None (list views)
    """
```

Resolution flow:
1. Strip mode prefix (`e0`) — already handled by mode dispatch
2. Parse pipeline ref (`p{N}`) — resolve to version string via existing `_resolve_pipeline_ref()`
3. Parse view suffix (`.v{M}`) — select renderer
4. If no view suffix and coordinate has a pipeline, fall through to existing orchestration behavior (backward-compatible)

### 3.4 View Registry

Views are extensible. A `VIEW_REGISTRY` dict maps view type numbers to renderer functions:

```python
VIEW_REGISTRY: dict[int, ViewRenderer] = {
    1: render_turn_by_turn,
    2: render_live_diff,
    3: render_timeline,
    4: render_agent_context,
}
```

New views register by adding to this dict. `e0.v` lists all registered views.

---

## 4. Feature Design

### 4.1 Pipeline Timeline Visualization (`.v3`)

**Renderer:** `render_timeline(version: str, persona: str = None) -> str`

Data flow:
1. Query `state_transition` for pipeline, ordered by timestamp
2. Compute durations from consecutive transition timestamps
3. Identify bottlenecks (stages exceeding 2× median duration)
4. Format as text timeline with duration bars

Output format (plain text, LLM-compatible):
```
Timeline: orchestration-engine-v2-temporal (p1)
──────────────────────────────────────────────
  pipeline_created    │████               │   3m   2026-03-21 10:00
  architect_design    │████████████████   │  45m   2026-03-21 10:03
  critic_design_rev   │██████             │  12m   2026-03-21 10:48
  builder_impl        │████████████████████│  62m   2026-03-21 11:00  ⚠ BOTTLENECK
  critic_code_review  │█████              │   8m   2026-03-21 12:02
  phase1_complete     │██                 │   2m   2026-03-21 12:10
                                            ───
                                           132m total
```

**Time-travel scrubber:** `render_timeline(version, at='2026-03-21T14:00:00Z')` adds a cursor marker (`▼ YOU ARE HERE`) at the specified timestamp. Uses existing `time_travel()` to determine the state at that point.

### 4.2 Agent Activity Monitor (`.v4` global, heartbeat subsystem)

**Heartbeat enhancement:**

Current `heartbeat()` in temporal_overlay.py records presence. V3 extends this with:

```python
def heartbeat_extended(self, agent: str, pipeline: str = None,
                       stage: str = None, session_id: str = None,
                       context_snapshot: dict = None) -> bool:
    """Extended heartbeat with context accumulation.
    
    context_snapshot: {
        'decisions_this_turn': int,
        'flags_resolved': int,
        'tokens_used': int,
        'current_focus': str,  # Brief description
    }
    """
```

**Liveness detection (existing, no change needed):**
- `HEARTBEAT_TTL_SECONDS = 300` (5 min) — already implemented
- `_apply_presence_ttl()` marks stale agents — already implemented
- V3 surfaces this in `.v4` view with visual indicators

**Agent context view:** `render_agent_context(version: str, agent: str = None) -> str`

When `agent=None`, shows all agents for the pipeline. Pulls from `get_design_lineage()` and formats as a summary of accumulated decisions, flags, and learnings.

### 4.3 F-label ↔ R-label Causal Graph

**Core concept:** When an F-label (field-level state change) fires, which R-labels (supermap re-renders) are affected?

**Implementation: `compute_f_r_causal_chain()`**

```python
def compute_f_r_causal_chain(f_labels: list[str]) -> dict:
    """Given F-labels from a revert, compute which R-labels would change.
    
    Returns:
        {
            'f_labels': ['⮌ p3.stage critic_review → architect_design'],
            'r_labels': [
                'R1 Δ p3 stage=architect_design',  # Pipeline row update
                'R2 Δ supermap.p section refresh',   # Supermap p-section
            ],
            'cascading': [
                'handoff p3 cancelled (critic no longer dispatched)',
            ]
        }
    """
```

**Visual diff for undo preview:** `preview_revert(version: str, target_ts: str) -> str`

Before executing a revert, show what would change:
```
Preview revert: orchestration-engine-v2 → 2026-03-21T10:00Z
────────────────────────────────────────────────────────────
  F-labels (state changes):
    ⮌ p2.stage builder_implementation → architect_design
    ⮌ p2.agent builder → architect
  
  R-labels (view impacts):
    R Δ supermap.p2 stage/agent fields
    R Δ dashboard.pipelines row p2
    R Δ handoff.latest cancelled
  
  Downstream:
    ⚠ Builder's current session would become orphaned
    ⚠ Handoff #47 (architect→critic) would be invalidated
```

This integrates with the existing `time_travel_revert()` in temporal_overlay.py. The preview is a dry-run wrapper that computes the diff without executing.

### 4.4 Scoped Views via Persona Primitives

**Already partially implemented** in Phase 2 R2 (`PERSONA_STAGE_FILTERS`, `_apply_persona_filter()`).

V3 extension: The `.v` views inherit persona filtering from the dispatch context.

```python
def render_view(view_type: int, pipeline: str = None, 
                persona: str = None) -> str:
    """Master renderer — delegates to VIEW_REGISTRY with persona context."""
    renderer = VIEW_REGISTRY.get(view_type)
    if not renderer:
        return f"Unknown view type .v{view_type}. Available: {list(VIEW_REGISTRY.keys())}"
    return renderer(pipeline=pipeline, persona=persona)
```

Persona scoping rules (unchanged from Phase 2 R2):
- `i1` (architect): sees design/review stages, all dashboard sections
- `i2` (critic): sees review stages + builder output for context
- `i3` (builder): sees implementation stages, stats only
- Global coordinates NEVER remapped — filtering only hides irrelevant rows

### 4.5 Cross-Pipeline State (`.v1` global mode)

**Multi-pipeline dashboard:** `render_turn_by_turn(pipeline=None)` (global mode) shows all active pipelines in a single view.

**Dependency graph:** New table + query.

```sql
CREATE TABLE IF NOT EXISTS pipeline_dependency (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_version  TEXT NOT NULL,     -- upstream pipeline
    target_version  TEXT NOT NULL,     -- downstream pipeline  
    dep_type        TEXT NOT NULL DEFAULT 'completion',  -- completion | archive | gate
    status          TEXT NOT NULL DEFAULT 'pending',     -- pending | satisfied | blocked
    satisfied_at    TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_dep_source ON pipeline_dependency(source_version);
CREATE INDEX IF NOT EXISTS idx_dep_target ON pipeline_dependency(target_version);
```

**Gate visualization:** `render_dependency_graph() -> str`

```
Pipeline Dependencies
─────────────────────
  orch-engine-v1 ──────✅──→ orch-engine-v2
  orch-engine-v2 ──────✅──→ orch-v2-temporal  
  orch-v2-temporal ────✅──→ orch-v3-monitoring (THIS)
  codex-v2-modes ──────✅──→ codex-v3-mcp (t4)
  orch-v3-monitoring ──⏳──→ codex-v3-mcp (t4)
  
  Legend: ✅ satisfied  ⏳ pending  🚫 blocked
```

### 4.6 Cascading Dependency Resolution

**Trigger:** When `handle_complete()` or `handle_archive()` fires in orchestration_engine.py.

**New function:** `resolve_downstream_deps(version: str, action: str) -> list[dict]`

```python
def resolve_downstream_deps(version: str, action: str = 'complete') -> list[dict]:
    """Resolve downstream dependencies when a pipeline completes/archives.
    
    1. Query pipeline_dependency for rows where source_version = version
    2. Mark matching deps as 'satisfied'
    3. For each target_version, check if ALL deps are now satisfied
    4. If all satisfied, emit a gate-open event (live diff .v2)
    5. Return list of resolution actions taken
    
    Returns: [
        {'target': 'codex-v3-mcp', 'dep_satisfied': 'orch-v3-monitoring', 
         'all_deps_met': True, 'eligible': True},
    ]
    """
```

**Integration point:** Hook into `_post_state_change()` — when `to_stage` is a phase-complete or archive stage, call `resolve_downstream_deps()`. This is the same pattern as the existing temporal hooks (graceful degradation).

**Live diff emission:** Resolution events are logged to `state_transition` with `action='dep_resolved'`, making them visible in `.v2` (live diff) automatically.

---

## 5. WAL Watcher Design (Human-Facing Live View)

### 5.1 Architecture

```python
class WALWatcher:
    """Lightweight SQLite WAL change detector for live dashboard.
    
    Polls SQLite WAL for changes at configurable intervals.
    When changes detected, re-renders dashboard and pushes to canvas.
    
    NOT a daemon — designed to run in a background exec session
    managed by OpenClaw, killable on demand.
    """
    
    def __init__(self, db_path: Path, interval_seconds: float = 2.0,
                 canvas_target: str = 'sandbox'):
        self.db_path = db_path
        self.interval = interval_seconds
        self.canvas_target = canvas_target
        self._last_wal_size = 0
        self._last_mtime = 0.0
```

### 5.2 Change Detection Strategy

**Primary:** Monitor `temporal.db-wal` file size and mtime. When either changes, a write has occurred.

**Fallback:** If WAL file doesn't exist (DB in rollback mode), poll `temporal.db` mtime directly.

**Why not inotify?** Adds a dependency (pyinotify/watchdog) and is Linux-specific. Polling the WAL file at 2-second intervals is negligible overhead for our scale (~5 pipelines, ~10 transitions/hour).

### 5.3 Canvas Rendering

The watcher renders HTML dashboard and pushes to OpenClaw canvas:

```python
def render_to_canvas(self, dashboard: dict) -> None:
    """Render dashboard as HTML and push to canvas."""
    html = self._render_html(dashboard)
    # Canvas push via subprocess:
    # openclaw canvas present --url "data:text/html,{encoded_html}"
```

Dashboard HTML is a single-page app with:
- Pipeline cards showing current stage, agent, lock status
- Timeline bars with stage durations
- Agent presence indicators (green/yellow/red)
- Dependency graph (simple directed graph via CSS)
- Auto-refresh meta tag as backup (watcher pushes updates, but page can self-poll too)

### 5.4 Research Note: SQLite WAL Reliability

The task spec flags this as needing research. Assessment:

- **WAL file monitoring is reliable for our use case.** WAL mode is SQLite's default for concurrent readers. The `-wal` file grows with uncommitted changes and checkpoints periodically. Monitoring file size + mtime catches all committed writes.
- **Edge case:** WAL checkpoint can reset the file size to 0. Solution: also monitor `temporal.db` mtime (the main DB updates on checkpoint).
- **Conclusion:** WAL polling is sufficient. No need for exotic change notification. The 2-second polling interval means <2s latency for human-facing view, which is acceptable.

---

## 6. Schema Changes

### 6.1 New Table: `pipeline_dependency`

```sql
CREATE TABLE IF NOT EXISTS pipeline_dependency (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_version  TEXT NOT NULL,
    target_version  TEXT NOT NULL,
    dep_type        TEXT NOT NULL DEFAULT 'completion',
    status          TEXT NOT NULL DEFAULT 'pending',
    satisfied_at    TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_dep_source ON pipeline_dependency(source_version);
CREATE INDEX IF NOT EXISTS idx_dep_target ON pipeline_dependency(target_version);
```

### 6.2 New Table: `view_config`

```sql
CREATE TABLE IF NOT EXISTS view_config (
    view_type       INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    renderer        TEXT NOT NULL,        -- Python function path
    enabled         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
```

Pre-populated with v1–v4 on migration. Used by `e0.v` (list views) command.

### 6.3 Schema Migration

`SCHEMA_VERSION = 2`. Migration adds the two new tables and seeds `view_config` with v1–v4 defaults. Existing tables unchanged — purely additive.

---

## 7. File Plan

### 7.1 New Files

| File | Purpose | Lines (est) |
|------|---------|-------------|
| `scripts/monitoring_views.py` | View renderers (v1–v4), VIEW_REGISTRY, resolve_view() | ~400 |
| `scripts/wal_watcher.py` | WAL change detector + canvas renderer | ~300 |
| `scripts/dependency_graph.py` | pipeline_dependency CRUD, cascading resolution, graph rendering | ~250 |

### 7.2 Modified Files

| File | Changes |
|------|---------|
| `scripts/temporal_schema.py` | Add `pipeline_dependency` + `view_config` tables, bump SCHEMA_VERSION to 2, add migration logic |
| `scripts/temporal_overlay.py` | Add `heartbeat_extended()`, import and delegate to `monitoring_views.py` for `.v` rendering |
| `scripts/orchestration_engine.py` | Add `.v` coordinate parsing in dispatch path, hook `resolve_downstream_deps()` into `_post_state_change()`, add `view` CLI subcommand |

### 7.3 NOT Modified

- `scripts/pipeline_orchestrate.py` — legacy wrapper, no changes needed
- `scripts/codex_engine.py` — V2 engine, no changes (V3 MCP integration is t4's scope)
- Pipeline markdown files — read-only data sources

---

## 8. Function Signatures

### 8.1 `scripts/monitoring_views.py`

```python
# ─── Types ───────────────────────────────────────────────────────
@dataclass
class ViewResult:
    """Result of resolving and rendering a .v coordinate."""
    view_type: int                    # 1-4
    view_name: str                    # "turn-by-turn", "live-diff", etc.
    pipeline: Optional[str]           # Version string or None (global)
    persona: Optional[str]            # Persona filter or None
    content: str                      # Rendered text output
    generated_at: str                 # ISO timestamp

# ─── Coordinate Resolution ───────────────────────────────────────
def parse_view_coord(coord: str) -> tuple[Optional[str], Optional[int]]:
    """Parse .v coordinate suffix.
    
    'e0p3.v2' → ('p3', 2)
    'e0v1'    → (None, 1)  
    'e0.v'    → (None, None)
    
    Returns (pipeline_ref, view_type).
    """

def resolve_view(coord: str, persona: str = None, 
                 overlay: 'TemporalOverlay' = None) -> ViewResult:
    """Resolve a .v coordinate to rendered content.
    
    1. Parse coordinate → (pipeline_ref, view_type)
    2. Resolve pipeline_ref → version string (or None for global)
    3. Look up renderer in VIEW_REGISTRY
    4. Call renderer with (pipeline, persona, overlay)
    5. Return ViewResult
    """

def list_views() -> str:
    """List all registered view types. Called by e0.v / e0v."""

# ─── View Renderers ──────────────────────────────────────────────
def render_turn_by_turn(pipeline: str = None, persona: str = None,
                        overlay: 'TemporalOverlay' = None) -> str:
    """v1: Snapshot dashboard for agent context injection.
    
    When pipeline=None: all active pipelines summary.
    When pipeline set: detailed single-pipeline view.
    Persona filtering applied via overlay.get_dashboard(persona=).
    """

def render_live_diff(pipeline: str = None, persona: str = None,
                     overlay: 'TemporalOverlay' = None,
                     since: str = None) -> str:
    """v2: Diffs since last agent turn (or since timestamp).
    
    Queries state_transition for changes since `since`.
    Groups by pipeline, shows F-labels for each transition.
    Includes dep resolution events (action='dep_resolved').
    """

def render_timeline(pipeline: str = None, persona: str = None,
                    overlay: 'TemporalOverlay' = None,
                    at: str = None) -> str:
    """v3: Timeline with stage progression, durations, bottlenecks.
    
    Uses get_timeline() + get_stage_durations().
    Bottleneck: stage duration > 2× median of all stages.
    Time-travel scrubber: if `at` is set, adds cursor marker.
    """

def render_agent_context(pipeline: str = None, persona: str = None,
                         overlay: 'TemporalOverlay' = None,
                         agent: str = None) -> str:
    """v4: Agent context — decisions, flags, learnings.
    
    When agent=None: all agents for the pipeline.
    Uses get_design_lineage() for narrative format.
    """
```

### 8.2 `scripts/dependency_graph.py`

```python
def register_dependency(source_version: str, target_version: str,
                        dep_type: str = 'completion',
                        overlay: 'TemporalOverlay' = None) -> bool:
    """Register a pipeline dependency."""

def resolve_downstream_deps(version: str, action: str = 'complete',
                            overlay: 'TemporalOverlay' = None) -> list[dict]:
    """Resolve downstream deps when pipeline completes/archives.
    
    Returns list of resolution dicts with target, status, eligibility.
    """

def check_deps_satisfied(version: str,
                         overlay: 'TemporalOverlay' = None) -> dict:
    """Check if all upstream deps for a pipeline are satisfied.
    
    Returns: {'all_met': bool, 'deps': [...], 'blocking': [...]}
    """

def render_dependency_graph(overlay: 'TemporalOverlay' = None) -> str:
    """Render cross-pipeline dependency graph as text."""

def seed_dependencies_from_tasks(workspace: Path) -> int:
    """Parse task frontmatter depends_on fields and seed pipeline_dependency table.
    
    Called once on schema migration, then incrementally on pipeline creation.
    Returns number of deps seeded.
    """
```

### 8.3 `scripts/wal_watcher.py`

```python
class WALWatcher:
    def __init__(self, db_path: Path, interval_seconds: float = 2.0):
        ...
    
    def detect_changes(self) -> bool:
        """Check if WAL file has changed since last check."""
    
    def run(self, callback: Callable[[dict], None] = None) -> None:
        """Main loop: poll WAL, re-render on change.
        
        Default callback: push HTML to OpenClaw canvas.
        Ctrl+C / SIGTERM to stop.
        """
    
    def render_html_dashboard(self, dashboard: dict) -> str:
        """Render dashboard as self-contained HTML."""
    
    def push_to_canvas(self, html: str) -> None:
        """Push HTML to OpenClaw canvas via CLI."""

# CLI entry point
if __name__ == '__main__':
    # python3 scripts/wal_watcher.py [--interval 2] [--db path]
```

### 8.4 Changes to `scripts/orchestration_engine.py`

```python
# New CLI subcommand:
# python3 scripts/orchestration_engine.py view <coord> [--persona <p>]
# e.g.: python3 scripts/orchestration_engine.py view e0p3.v2

def handle_view(coord: str, persona: str = None) -> str:
    """Handle .v coordinate resolution in engine CLI."""

# In _post_state_change(), add:
def _post_state_change(version, from_stage, to_stage, agent, action, notes='', next_agent=''):
    # ... existing temporal hooks ...
    # NEW: cascading dependency resolution on phase completion / archive
    if to_stage in PHASE_COMPLETE_STAGES or action == 'archive':
        from dependency_graph import resolve_downstream_deps
        resolve_downstream_deps(version, action=action, overlay=_get_temporal())
```

### 8.5 Changes to `scripts/temporal_schema.py`

```python
SCHEMA_VERSION = 2

MIGRATION_V2_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_dependency (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_version  TEXT NOT NULL,
    target_version  TEXT NOT NULL,
    dep_type        TEXT NOT NULL DEFAULT 'completion',
    status          TEXT NOT NULL DEFAULT 'pending',
    satisfied_at    TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_dep_source ON pipeline_dependency(source_version);
CREATE INDEX IF NOT EXISTS idx_dep_target ON pipeline_dependency(target_version);

CREATE TABLE IF NOT EXISTS view_config (
    view_type       INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    renderer        TEXT NOT NULL,
    enabled         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Seed default views
INSERT OR IGNORE INTO view_config (view_type, name, description, renderer) VALUES
  (1, 'turn-by-turn', 'Snapshot dashboard injected per agent turn', 'monitoring_views.render_turn_by_turn'),
  (2, 'live-diff', 'Continuous diffs as they land between agents', 'monitoring_views.render_live_diff'),
  (3, 'timeline', 'Stage progression with durations and bottlenecks', 'monitoring_views.render_timeline'),
  (4, 'agent-context', 'Decisions, flags, learnings for pipeline agents', 'monitoring_views.render_agent_context');
"""

def migrate_v2(conn: sqlite3.Connection) -> None:
    """Apply V2 migration: dependency graph + view config tables."""
    conn.executescript(MIGRATION_V2_SQL)
    conn.execute(
        "INSERT OR IGNORE INTO schema_version (version, description) VALUES (?, ?)",
        (2, "V3 monitoring: pipeline_dependency + view_config tables")
    )
    conn.commit()
```

---

## 9. Integration Points

### 9.1 Dispatch Payload Extension

When the engine builds a `DispatchPayload`, if view injection is enabled:

```python
# In dispatch_payload construction:
if view_injection_enabled:
    from monitoring_views import resolve_view
    v1_content = resolve_view(f'e0{pipeline_coord}.v1', persona=agent)
    payload.view_context = v1_content.content  # Injected into agent task prompt
```

This adds a `### Pipeline State` section to the agent's task prompt — zero new tools, zero extra calls. Agents see state passively.

### 9.2 Codex Cockpit Plugin

The existing `before_prompt_build` hook in the cockpit plugin already injects the supermap. V3 adds:

```python
# In cockpit plugin's before_prompt_build:
if has_active_pipelines():
    from monitoring_views import render_turn_by_turn
    dashboard_summary = render_turn_by_turn(persona=current_persona)
    inject_into_prompt("## Active Pipeline State", dashboard_summary)
```

This is a future integration (cockpit plugin is separate infrastructure), documented here for the builder's awareness.

### 9.3 With Codex Engine V3 / MCP (t4)

V3 monitoring views can be served as MCP resources:
- `mcp://belam/codex/e0.v` → list views
- `mcp://belam/codex/e0p1.v3` → timeline for pipeline 1

This is t4's scope. V3 provides the Python functions; t4 wraps them in MCP.

---

## 10. Design Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Separate `monitoring_views.py` from `temporal_overlay.py` | Overlay is data access, views are presentation. Single responsibility. Overlay stays stable while views iterate. |
| D2 | Separate `dependency_graph.py` from `orchestration_engine.py` | Dependency logic is complex enough to warrant its own module. Engine imports it; graceful degradation if missing. |
| D3 | WAL polling over inotify | Zero deps, cross-platform, sufficient for our scale. 2s latency is acceptable for human-facing view. |
| D4 | View coordinates as suffix modifiers, not separate namespace | `.v` binds TO the thing being viewed. It's not a standalone primitive — it's a lens on existing coordinates. |
| D5 | HTML canvas for human-facing dashboard (not TUI) | Canvas works across Telegram/web. TUI requires terminal attachment. HTML is more portable. |
| D6 | `view_config` table for extensibility | New views can be registered without code changes to the schema. `e0.v` queries this table. |
| D7 | Dependency resolution in `_post_state_change()` hook | Same pattern as temporal hooks — non-fatal, graceful degradation. Minimal coupling. |

---

## 11. Open Questions Resolved

| Question (from task spec) | Resolution |
|---------------------------|------------|
| Standalone daemon vs engine vs hybrid? | **Option C hybrid** (confirmed by Shael) |
| Canvas rendering worth the complexity? | **Yes** — HTML dashboard via canvas is the human-facing path. Low complexity: it's just HTML generation + a subprocess call. |
| Time-travel undo as first-class engine op? | **Not in V3.** Existing `revert` CLI command is sufficient. V3 adds preview (dry-run) but doesn't change the undo mechanism. |
| Multiple concurrent human viewers? | **Not in V3 scope.** Single canvas target. Multi-viewer is a V4 concern if needed. |
| WAL polling vs inotify? | **WAL polling.** See D3. |

---

## 12. Test Checklist

### 12.1 `monitoring_views.py` Tests

- [ ] `parse_view_coord('e0p3.v2')` → `('p3', 2)`
- [ ] `parse_view_coord('e0v1')` → `(None, 1)`
- [ ] `parse_view_coord('e0.v')` → `(None, None)`
- [ ] `parse_view_coord('e0p3')` → `('p3', None)` (no view suffix — backward compat)
- [ ] `list_views()` returns all 4 registered views
- [ ] `render_turn_by_turn()` global mode shows all pipelines
- [ ] `render_turn_by_turn(pipeline='orch-v2-temporal')` shows single pipeline
- [ ] `render_turn_by_turn(persona='builder')` applies persona filter
- [ ] `render_live_diff(since='2026-03-21T10:00:00Z')` shows transitions after timestamp
- [ ] `render_timeline()` shows duration bars with bottleneck markers
- [ ] `render_timeline(at='2026-03-21T14:00:00Z')` adds time-travel cursor
- [ ] `render_agent_context(pipeline='orch-v2-temporal', agent='architect')` shows design lineage
- [ ] `resolve_view('e0p3.v2')` returns ViewResult with correct content

### 12.2 `dependency_graph.py` Tests

- [ ] `register_dependency('orch-v1', 'orch-v2')` creates row in `pipeline_dependency`
- [ ] `resolve_downstream_deps('orch-v1')` marks dep as satisfied
- [ ] Cascading: if orch-v2 has 2 deps and only 1 is satisfied, `all_deps_met=False`
- [ ] Cascading: when last dep satisfied, `all_deps_met=True, eligible=True`
- [ ] `render_dependency_graph()` produces readable text graph
- [ ] `seed_dependencies_from_tasks()` parses frontmatter `depends_on` correctly
- [ ] Resolution events logged to `state_transition` with `action='dep_resolved'`

### 12.3 `wal_watcher.py` Tests

- [ ] `detect_changes()` returns True after a DB write
- [ ] `detect_changes()` returns False when no writes
- [ ] `render_html_dashboard()` produces valid HTML with all sections
- [ ] Watcher handles missing WAL file gracefully (DB in rollback mode)
- [ ] Watcher handles WAL checkpoint (size reset to 0) without false negative

### 12.4 Integration Tests

- [ ] `orchestration_engine.py view e0p1.v1` produces dashboard output
- [ ] `orchestration_engine.py view e0.v` lists available views
- [ ] Stage completion triggers `resolve_downstream_deps()` via `_post_state_change()`
- [ ] Archive triggers dependency resolution
- [ ] Schema migration from v1→v2 is idempotent and preserves existing data
- [ ] Temporal overlay continues to work with new schema (backward compat)
- [ ] All existing orchestration engine tests still pass (no regressions)

### 12.5 F-label ↔ R-label Tests

- [ ] `compute_f_r_causal_chain()` maps stage revert to correct R-labels
- [ ] `preview_revert()` shows dry-run diff without executing
- [ ] Revert F-labels use `⮌` (not `Δ`)

---

## 13. Builder Spec Summary

**Build order:** (dependencies flow left → right)

```
temporal_schema.py (v2 migration)
    → dependency_graph.py (needs new tables)
    → monitoring_views.py (needs dependency_graph for .v cross-pipeline views)
        → orchestration_engine.py (integrate view CLI + dep resolution hook)
        → temporal_overlay.py (heartbeat_extended, delegate to monitoring_views)
    → wal_watcher.py (standalone, needs monitoring_views for rendering)
```

**Estimated effort:** ~950 lines new code, ~80 lines modified in existing files.

**Critical path:** Schema migration → dependency_graph → monitoring_views → engine integration.

**WAL watcher is independent** and can be built in parallel with the view renderers.

---

## 14. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Schema migration breaks existing temporal DB | HIGH | Migration is purely additive (CREATE IF NOT EXISTS). Existing tables untouched. Verify with `--verify` after migration. |
| View rendering slows down dispatch | LOW | Views are text rendering, not DB-intensive. The `get_dashboard()` query is already fast (small DB). Add timing guard: skip view injection if render > 500ms. |
| WAL watcher consumes too much CPU | LOW | 2s polling interval. Each poll is one `os.stat()` call. Negligible. |
| Circular dependencies in dep graph | MED | `resolve_downstream_deps()` tracks visited set to prevent cycles. Log warning on cycle detection. |
| Canvas unavailable (no browser) | LOW | WAL watcher degrades to console output. `--no-canvas` flag for terminal-only mode. |
