# Codex Engine V3: Architect Design

**Pipeline:** codex-engine-v3  
**Stage:** architect_design  
**Agent:** architect  
**Date:** 2026-03-22  

---

## Overview

V3 extends the Codex Engine's **external interface layer** — how external clients consume codex state, how agents experience grammar changes at runtime, how state materializes into files, and how multiple rendering formats display simultaneously. No orchestration changes. No notebook. Pure infrastructure.

### Architectural Principle

The V2 engine is the **core** — coordinate parsing, primitive loading, R/F-label tracking, rendering. V3 wraps it with four interface capabilities:

1. **MCP Server** — external consumption via Model Context Protocol
2. **Live Mode-Switch** — runtime grammar transformation
3. **Reactive Materialization** — .codex files as materialized views
4. **Multi-Pane Rendering** — simultaneous format visualization

Each is a distinct module that imports from `codex_engine.py` and `codex_codec.py` without modifying their core APIs.

---

## 1. MCP-Native Codex Server (`scripts/codex_mcp_server.py`)

### What It Does

Serves codex primitives over MCP (Model Context Protocol). External clients — Cursor, Claude Desktop, any MCP-aware tool — request `mcp://belam/codex/t1` and receive the primitive in codex-native format via `codex_codec.to_codex()`.

### Architecture

```
External Client (Cursor/Claude Desktop)
        │
        ▼
codex_mcp_server.py (JSON-RPC stdio transport)
        │
        ├─ resources/list  → enumerate all primitives as MCP resources
        ├─ resources/read  → resolve coordinate → load → codex_codec.to_codex()
        ├─ tools/list      → expose engine operations as MCP tools
        └─ tools/call      → dispatch V2 operations (e0/e1/e2/e3)
        │
        ▼
codex_engine.py (resolve_coords, load_primitive, render_*)
codex_codec.py (to_codex, from_codex, register_codec)
```

### MCP Resource URIs

```
codex://workspace/t1          → task at coordinate t1
codex://workspace/p3          → pipeline at coordinate p3
codex://workspace/supermap    → full supermap render
codex://workspace/m           → today's memory entries
codex://workspace/d5          → decision at coordinate d5
```

URI scheme: `codex://workspace/<coordinate>`. The workspace segment is fixed (single-workspace model). Coordinates follow the V2 grammar exactly.

### MCP Tools Exposed

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `codex_navigate` | Resolve and render any coordinate | `coord: str` |
| `codex_edit` | Edit primitive field (e1 equivalent) | `coord: str, field: int, value: str` |
| `codex_create` | Create new primitive (e2 equivalent) | `type: str, title: str` |
| `codex_graph` | Render dependency graph | `coord: str, depth: int` |
| `codex_supermap` | Render supermap | `persona?: str, tag?: str` |

### Response Format

MCP responses use `codex_codec.to_codex()` as the primary content type (`application/x-codex`). The codec's `register_codec()` function already returns the correct dict shape for integration:

```python
{
    "content_type": "application/x-codex",
    "encode": to_codex,
    "decode": from_codex,
}
```

For resources, the response includes:
- **contents[0].text** — codex-formatted primitive (frontmatter + body)
- **contents[0].mimeType** — `application/x-codex`
- **contents[0].uri** — the requested resource URI

For tools, the response includes:
- **content[0].text** — rendered output (same as CLI would produce)
- **content[0].type** — `text`
- R-label tracking applies: responses include the R-label in the text output

### R-Label Diffs in MCP

When a client re-reads a resource it previously read, the server can optionally include an R-label diff header showing what changed since the last read:

```
R38Δ (3 coords shifted)
  Δ t1 status active→complete
  Δ p2 stage architect_design→critic_review
  + m152 [01:10] New memory entry
```

This reuses the existing `RenderTracker` — the MCP server maintains its own tracker instance per session (one per connected client).

### Transport

**stdio** transport (standard for MCP). The server is launched as a subprocess:

```json
{
  "mcpServers": {
    "codex": {
      "command": "python3",
      "args": ["/home/ubuntu/.openclaw/workspace/scripts/codex_mcp_server.py"],
      "env": {
        "BELAM_WORKSPACE": "/home/ubuntu/.openclaw/workspace"
      }
    }
  }
}
```

### Key Functions

```python
# codex_mcp_server.py

class CodexMCPServer:
    """MCP server serving codex primitives and engine operations."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.tracker = RenderTracker()  # per-session R-label tracking
    
    async def handle_resources_list(self) -> list[dict]:
        """List all primitives as MCP resources."""
        # Iterate NAMESPACE prefixes, get_primitives() for each
        # Return list of {uri, name, description, mimeType}
    
    async def handle_resources_read(self, uri: str) -> dict:
        """Read a primitive by URI, return codex-formatted content."""
        # Parse URI → coordinate
        # resolve_coords() → load_primitive() → to_codex()
        # Track with RenderTracker for diff capability
    
    async def handle_tools_list(self) -> list[dict]:
        """List available codex tools."""
        # Return tool schemas for navigate/edit/create/graph/supermap
    
    async def handle_tools_call(self, name: str, arguments: dict) -> dict:
        """Execute a codex tool and return result."""
        # Route to _dispatch_v2_operation or render_* functions
        # Capture stdout, return as text content

def main():
    """stdio transport loop — read JSON-RPC from stdin, write to stdout."""
```

### Dependencies

- No new external dependencies (MCP stdio transport is just JSON-RPC over stdin/stdout)
- Imports: `codex_engine` (resolve_coords, load_primitive, render_supermap, render_zoom, render_graph, get_render_tracker)
- Imports: `codex_codec` (to_codex, from_codex, register_codec)

---

## 2. Live Mode-Switch (`e0x` command in `codex_engine.py`)

### What It Does

`e0x` swaps the coordinate grammar mid-session. The supermap re-renders with new coordinate assignments. This creates attention interference — the model's embeddings for coordinates shift, forcing re-encoding of the full state space.

### Architecture

Mode-switch is a **view transformation**, not a state change. The underlying primitives don't move. Only the coordinate-to-primitive mapping changes.

```
e0x              → cycle to next grammar variant
e0x shuffle      → randomized coordinate assignment
e0x alpha        → alphabetical by slug (current default)
e0x reverse      → reverse of current ordering
e0x priority     → sort by priority field (critical first)
e0x recent       → sort by last-modified date
e0x reset        → restore default (alpha) ordering
```

### Implementation

Mode-switch modifies the **sort key** used by `get_primitives()`. Currently, primitives are sorted alphabetically by filename. Mode-switch introduces a `SORT_MODE` registry:

```python
# In codex_engine.py — new module-level state

SORT_MODES = {
    'alpha':    lambda slug, fp, fm: slug,                    # default
    'reverse':  lambda slug, fp, fm: '~' + slug,             # reverse alpha (~ sorts high)
    'priority': lambda slug, fp, fm: _priority_sort_key(fm),  # critical=0, high=1, med=2, low=3
    'recent':   lambda slug, fp, fm: _mtime_sort_key(fp),    # newest first
    'shuffle':  None,                                         # special: random.shuffle post-sort
}

_current_sort_mode = 'alpha'  # session-scoped state

def set_sort_mode(mode: str) -> str:
    """Set sort mode, return confirmation string. Forces supermap re-render."""
    global _current_sort_mode
    if mode == 'shuffle':
        _current_sort_mode = 'shuffle'
    elif mode in SORT_MODES:
        _current_sort_mode = mode
    elif mode == 'reset':
        _current_sort_mode = 'alpha'
    else:
        return f"Unknown sort mode: {mode}. Valid: {', '.join(SORT_MODES.keys())}"
    # Invalidate any cached primitive lists
    _invalidate_primitive_cache()
    return f"Mode-switch: {_current_sort_mode}. Coordinates re-assigned."

def _apply_sort_mode(items: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    """Apply current sort mode to a primitive list. Called by get_primitives()."""
    global _current_sort_mode
    if _current_sort_mode == 'shuffle':
        import random
        result = list(items)
        random.shuffle(result)
        return result
    key_fn = SORT_MODES.get(_current_sort_mode)
    if key_fn is None:
        return items
    # Need frontmatter for priority/recent sorts — lazy load
    def _sort_key(item):
        slug, fp = item
        try:
            fm_raw, _ = parse_frontmatter(fp.read_text(encoding='utf-8', errors='replace'))
            fm = dict(fm_raw)
        except Exception:
            fm = {}
        return key_fn(slug, fp, fm)
    return sorted(items, key=_sort_key)
```

### Integration with get_primitives()

`get_primitives()` currently returns `sorted(items)`. The change: after the existing sort/filter, apply `_apply_sort_mode()`:

```python
# In get_primitives(), before return:
items = _apply_sort_mode(items)
return items
```

### e0x Dispatch

`e0x` is parsed in the V2 grammar as mode=0 with first op_arg starting with 'x'. Add to `_dispatch_e0`:

```python
# In _dispatch_e0():
if spec['op'] == 'mode_switch':
    mode_arg = spec['extra'][0] if spec['extra'] else 'cycle'
    if mode_arg == 'cycle':
        # Cycle through: alpha → priority → recent → reverse → alpha
        cycle = ['alpha', 'priority', 'recent', 'reverse']
        idx = cycle.index(_current_sort_mode) if _current_sort_mode in cycle else -1
        mode_arg = cycle[(idx + 1) % len(cycle)]
    result = set_sort_mode(mode_arg)
    print(f"{tracker.next_f_label()} {result}")
    # Auto-render supermap in new order
    content = render_supermap()
    _, output = tracker.track_render(content)
    print(output)
    return 0
```

### e0x Detection in _parse_e0_args()

The existing `_parse_e0_args()` function needs to recognize `x` or `mode-switch` as an operation:

```python
# When first token is 'x' or starts with 'x':
if first_arg.startswith('x'):
    spec['op'] = 'mode_switch'
    spec['extra'] = [first_arg[1:]] if len(first_arg) > 1 else remaining_args[:1]
```

### --shuffle Flag

`--shuffle` is a view modifier flag (same category as `--as`, `--depth`). It sets shuffle mode for a single render without persisting:

```python
# In main() flag parsing:
if a == '--shuffle':
    # One-shot shuffle — don't persist to _current_sort_mode
    _one_shot_shuffle = True
```

This triggers `random.shuffle` on the primitive list for that render only, then reverts.

### Render State Tracking

When mode-switch occurs, the `RenderTracker` records it as an F-label mutation:

```
F23 Δ engine.sort_mode alpha→shuffle
R39 ╶─ Codex Engine Supermap [2026-03-22 01:30 UTC]
  ...shuffled coordinates...
```

The R-label diff between R38 and R39 shows all coordinate reassignments.

---

## 3. Reactive .codex Materialization (`scripts/codex_materialize.py`)

### What It Does

Generates `.codex` files as materialized views of workspace state. These are **format-layer files** — derived from the canonical `.md` primitives, not sources of truth. The `before_prompt_build` hook (OpenClaw's `--boot` equivalent) triggers materialization so agents see fresh codex state each turn.

### Architecture

```
State Change (edit/create/orchestrate)
        │
        ▼
codex_engine.py (F-label mutation)
        │
        ├─ Writes .md primitive (source of truth)
        └─ Calls materialize_affected(coord) → updates .codex view
        
Agent Turn Start (before_prompt_build)
        │
        ▼
codex_materialize.py --boot
        │
        ├─ Reads all primitives via get_primitives()
        ├─ Generates CODEX.codex (full workspace materialized view)
        ├─ Generates state/*.codex (per-namespace views)
        └─ Computes temporal diff vs last materialization
        
Agent Context
        │
        ▼
CODEX.codex injected into AGENTS.md (existing --boot mechanism)
  + temporal diff section showing "what changed since last turn"
```

### .codex File Format

Uses `codex_codec.to_codex()` for individual primitives. The workspace-level `CODEX.codex` is a **multi-document codex stream** (documents separated by `---`):

```yaml
---
type: supermap
generated: 2026-03-22T01:30:00Z
sort_mode: alpha
hash: a3f2b1
---
╶─ Codex Engine Supermap [2026-03-22 01:30 UTC]
╶─ p   pipelines (6)
│  ╶─ p1    orchestration-engine-v2-temporal  phase2_complete/medium
...
---
type: diff
since: 2026-03-22T01:00:00Z
changes: 3
---
Δ p2  codex-engine-v3  phase1_design/medium
Δ m152  [01:10] Launched pipeline
+ t15  new-task  open/medium
```

### Materialization Trigger Points

1. **Boot-time** (`codex_materialize.py --boot`): Full materialization. Replaces current `codex_engine.py --boot` supermap injection. Generates `CODEX.codex` and injects into `AGENTS.md`.

2. **Post-mutation** (`materialize_affected(coord)`): Called after F-label mutations in `execute_edit()`, `execute_create()`, and orchestration operations. Only updates the affected `.codex` section.

3. **On-demand** (`codex_materialize.py --full`): Full re-materialization for debugging or manual refresh.

### Key Functions

```python
# codex_materialize.py

class CodexMaterializer:
    """Generates and maintains .codex materialized views."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.state_dir = workspace / 'state'
        self.last_hash_file = self.state_dir / 'materialize_hashes.json'
    
    def materialize_full(self) -> dict:
        """Full workspace materialization.
        
        Returns: {
            'codex_path': Path to CODEX.codex,
            'diff': temporal diff string (empty on first run),
            'hash': content hash of current state,
            'primitives_count': int,
        }
        """
        # 1. Render supermap via render_supermap()
        # 2. Compute hash of rendered content
        # 3. Compare with last_hash_file for diff
        # 4. Write CODEX.codex as multi-doc stream (supermap + diff)
        # 5. Update hash file
    
    def materialize_affected(self, coords: list[str]) -> None:
        """Incremental materialization after mutation.
        
        Only regenerates the .codex sections affected by the given coordinates.
        Appends diff entries to the current CODEX.codex diff section.
        """
        # 1. For each coord, re-render that primitive
        # 2. Update the corresponding section in CODEX.codex
        # 3. Append to diff section
    
    def compute_diff(self, since: str = None) -> str:
        """Compute temporal diff since last materialization or given timestamp.
        
        Returns codex-formatted diff string using R-label format:
          Δ coord  field  old→new
          + coord  (added)
          - coord  (removed)
        """
    
    def inject_into_agents_md(self, content: str) -> None:
        """Replace the SUPERMAP section in AGENTS.md.
        
        Reuses existing BEGIN:SUPERMAP/END:SUPERMAP markers.
        Adds diff section after supermap.
        """

    def boot(self) -> None:
        """Boot-time entry point. Full materialize + inject."""
        result = self.materialize_full()
        supermap_content = self._read_supermap_from_codex(result['codex_path'])
        self.inject_into_agents_md(supermap_content)
```

### Integration with codex_engine.py --boot

The existing `--boot` flag in `main()` calls `render_supermap()` and injects into `AGENTS.md`. V3 changes this to delegate to `CodexMaterializer.boot()`:

```python
# In main():
if '--boot' in args:
    from codex_materialize import CodexMaterializer
    materializer = CodexMaterializer(WORKSPACE)
    materializer.boot()
    return
```

### Hash-Based Change Detection

Each materialization stores a hash of the rendered content per-coordinate. On next materialization, only primitives whose content hash changed are included in the diff. This avoids full re-reads:

```python
# Hash file: state/materialize_hashes.json
{
    "t1": "a3f2b1c4",
    "p3": "7e8d9f0a",
    "last_materialize": "2026-03-22T01:30:00Z",
    "sort_mode": "alpha"
}
```

---

## 4. Multi-Pane Rendering (`scripts/codex_panes.py`)

### What It Does

Launches a tmux session with 3 panes showing the same codex state in different formats simultaneously:

```
┌─────────────────────┬────────────────────────┬─────────────────────┐
│  DENSE CODEX        │  JSON MCP              │  HUMAN-PRETTY       │
│                     │                        │                     │
│  ╶─ p  pipelines(6) │  {                     │  ## Pipelines       │
│  │ ╶─ p1 orch..     │    "pipelines": [      │                     │
│  │ ╶─ p2 codex..    │      {                 │  1. **orch-v2**     │
│  ╶─ t  tasks (14)   │        "coord": "p1",  │     Status: done    │
│  │ ╶─ t1 build..    │        "slug": "orch.."│     Phase: 2        │
│                     │      }                 │                     │
│  R38 2026-03-22     │    ]                   │  2. **codex-v3**    │
│                     │  }                     │     Status: design   │
└─────────────────────┴────────────────────────┴─────────────────────┘
```

### Architecture

```
codex_panes.py --start [coord]
        │
        ├─ Creates tmux session "codex-panes"
        ├─ Pane 0: watch -n2 codex_panes.py --render dense [coord]
        ├─ Pane 1: watch -n2 codex_panes.py --render json [coord]
        └─ Pane 2: watch -n2 codex_panes.py --render pretty [coord]

codex_panes.py --render <format> [coord]
        │
        ├─ dense:  render_supermap() or render_zoom() — existing engine output
        ├─ json:   resolve → load_primitive() → json.dumps() (or to_codex → from_codex → json)
        └─ pretty: resolve → load_primitive() → _render_pretty() — markdown-style human output
```

### Rendering Modes

**Dense (default engine output):**
```
╶─ Codex Engine Supermap [2026-03-22 01:30 UTC]
╶─ p   pipelines (6)
│  ╶─ p1    orchestration-engine-v2-temporal  phase2_complete/medium
```

**JSON MCP (what external MCP clients would see):**
```json
{
  "resources": [
    {
      "uri": "codex://workspace/p1",
      "name": "orchestration-engine-v2-temporal",
      "primitive": "pipeline",
      "status": "phase2_complete",
      "priority": "medium"
    }
  ]
}
```

**Human-Pretty (expanded readable format):**
```markdown
## Pipelines (6 active)

### p1 — Orchestration Engine V2 Temporal
- **Status:** Phase 2 Complete ✅
- **Priority:** Medium
- **Started:** 2026-03-21
- **Agents:** architect, critic, builder
```

### Key Functions

```python
# codex_panes.py

def render_dense(coord: str = None) -> str:
    """Render in dense codex format (existing engine output)."""
    if coord:
        return render_zoom([coord])
    return render_supermap()

def render_json(coord: str = None) -> str:
    """Render as JSON (MCP-compatible representation)."""
    if coord:
        resolved, _ = resolve_coords([coord])
        results = []
        for r in resolved:
            prim = load_primitive(r['filepath'], r['type'])
            if prim:
                # Convert to JSON-friendly dict
                entry = {
                    'uri': f"codex://workspace/{r['prefix']}{r['index']}",
                    'coord': f"{r['prefix']}{r['index']}",
                    'slug': r['slug'],
                }
                for idx, field_data in prim['fields'].items():
                    entry[field_data['key']] = field_data['value']
                if prim['body']:
                    entry['body'] = '\n'.join(prim['body'])
                results.append(entry)
        return json.dumps({'resources': results}, indent=2)
    else:
        # Full supermap as JSON
        return _supermap_to_json()

def render_pretty(coord: str = None) -> str:
    """Render in human-pretty markdown format."""
    if coord:
        resolved, _ = resolve_coords([coord])
        lines = []
        for r in resolved:
            prim = load_primitive(r['filepath'], r['type'])
            if prim:
                lines.append(_format_pretty_primitive(r, prim))
        return '\n\n'.join(lines)
    return _supermap_to_pretty()

def start_panes(coord: str = None) -> None:
    """Launch tmux multi-pane session."""
    session = 'codex-panes'
    script = Path(__file__).resolve()
    coord_arg = f' {coord}' if coord else ''
    
    subprocess.run(['tmux', 'kill-session', '-t', session], 
                   capture_output=True)  # clean start
    subprocess.run(['tmux', 'new-session', '-d', '-s', session,
                    f'watch -n2 python3 {script} --render dense{coord_arg}'])
    subprocess.run(['tmux', 'split-window', '-h', '-t', session,
                    f'watch -n2 python3 {script} --render json{coord_arg}'])
    subprocess.run(['tmux', 'split-window', '-h', '-t', session,
                    f'watch -n2 python3 {script} --render pretty{coord_arg}'])
    subprocess.run(['tmux', 'select-layout', '-t', session, 'even-horizontal'])
    print(f"Multi-pane started. Attach: tmux attach -t {session}")

def stop_panes() -> None:
    """Kill the multi-pane tmux session."""
    subprocess.run(['tmux', 'kill-session', '-t', 'codex-panes'],
                   capture_output=True)
```

### CLI Interface

```
python3 codex_panes.py --start [coord]     # launch tmux panes
python3 codex_panes.py --stop              # kill tmux session
python3 codex_panes.py --render dense [coord]   # single-format render (for watch)
python3 codex_panes.py --render json [coord]
python3 codex_panes.py --render pretty [coord]
```

### Integration with Monitoring Views

The `monitoring_views.py` v1-v4 views can also be rendered in the multi-pane format. When a `.v` coordinate is provided:

```
python3 codex_panes.py --start e0p3.v1    # pipeline dashboard in 3 formats
```

The pretty pane renders `render_turn_by_turn()` output, the JSON pane renders the structured data, and the dense pane renders the codex coordinate view.

---

## Builder Spec

### Files to Create

| File | Lines (est.) | Description |
|------|:------:|-------------|
| `scripts/codex_mcp_server.py` | 350-450 | MCP server (stdio JSON-RPC transport) |
| `scripts/codex_materialize.py` | 200-250 | Reactive .codex materialization |
| `scripts/codex_panes.py` | 200-250 | Multi-pane tmux rendering |

### Files to Modify

| File | Changes | Description |
|------|---------|-------------|
| `scripts/codex_engine.py` | ~80 lines | Add sort mode state, `_apply_sort_mode()`, `e0x` detection in `_parse_e0_args()`, `--shuffle` flag, `--boot` delegation to materializer |
| `scripts/codex_codec.py` | 0 lines | No changes needed — API already suitable |
| `scripts/codex_ram.py` | 0 lines | No changes needed |

### Function Signatures (New Files)

#### `codex_mcp_server.py`

```python
class CodexMCPServer:
    def __init__(self, workspace: Path): ...
    async def handle_initialize(self, params: dict) -> dict: ...
    async def handle_resources_list(self) -> list[dict]: ...
    async def handle_resources_read(self, uri: str) -> dict: ...
    async def handle_tools_list(self) -> list[dict]: ...
    async def handle_tools_call(self, name: str, arguments: dict) -> dict: ...
    def _parse_uri(self, uri: str) -> str: ...  # URI → coordinate
    def _coord_to_uri(self, prefix: str, index: int, slug: str) -> str: ...

def read_jsonrpc(stream) -> dict: ...
def write_jsonrpc(stream, response: dict) -> None: ...
def main() -> None: ...  # stdio event loop
```

#### `codex_materialize.py`

```python
class CodexMaterializer:
    def __init__(self, workspace: Path): ...
    def materialize_full(self) -> dict: ...
    def materialize_affected(self, coords: list[str]) -> None: ...
    def compute_diff(self, since: str = None) -> str: ...
    def inject_into_agents_md(self, content: str) -> None: ...
    def boot(self) -> None: ...
    def _load_hashes(self) -> dict: ...
    def _save_hashes(self, hashes: dict) -> None: ...
    def _hash_primitive(self, coord: str, content: str) -> str: ...

def main() -> None: ...  # CLI entry point (--boot, --full, --diff)
```

#### `codex_panes.py`

```python
def render_dense(coord: str = None) -> str: ...
def render_json(coord: str = None) -> str: ...
def render_pretty(coord: str = None) -> str: ...
def start_panes(coord: str = None) -> None: ...
def stop_panes() -> None: ...
def _supermap_to_json() -> str: ...
def _supermap_to_pretty() -> str: ...
def _format_pretty_primitive(resolved: dict, prim: dict) -> str: ...

def main() -> None: ...  # CLI entry point
```

#### `codex_engine.py` (additions)

```python
# Module-level state
SORT_MODES: dict                          # name → sort key function
_current_sort_mode: str = 'alpha'         # session-scoped

def set_sort_mode(mode: str) -> str: ...
def _apply_sort_mode(items: list) -> list: ...
def _priority_sort_key(fm: dict) -> tuple: ...
def _mtime_sort_key(fp: Path) -> float: ...
def _invalidate_primitive_cache() -> None: ...
```

### Build Order

1. **codex_engine.py modifications** — sort mode infrastructure + e0x dispatch (prerequisite for all others)
2. **codex_materialize.py** — materialization engine (depends on engine sort mode)
3. **codex_panes.py** — multi-pane rendering (depends on engine rendering functions)
4. **codex_mcp_server.py** — MCP server (depends on engine + codec, independent of 2 & 3)

### Test Checklist

#### MCP Server Tests
- [ ] `resources/list` returns all active primitives with correct URIs
- [ ] `resources/read` for valid coordinate returns codex-formatted content
- [ ] `resources/read` for invalid coordinate returns error
- [ ] `tools/call codex_navigate` returns rendered zoom view
- [ ] `tools/call codex_edit` mutates primitive and returns F-label
- [ ] `tools/call codex_supermap` returns full supermap
- [ ] JSON-RPC error handling (invalid method, missing params)
- [ ] Content-type is `application/x-codex` for resource reads
- [ ] R-label tracking works across multiple reads in same session

#### Live Mode-Switch Tests
- [ ] `e0x` cycles through sort modes
- [ ] `e0x shuffle` randomizes coordinate assignments
- [ ] `e0x alpha` restores default sort
- [ ] `e0x priority` sorts critical→high→medium→low
- [ ] `e0x recent` sorts by file mtime
- [ ] `e0x reverse` reverses current order
- [ ] `e0x reset` returns to alpha
- [ ] `e0x` triggers automatic supermap re-render
- [ ] `--shuffle` flag applies one-shot shuffle without persisting
- [ ] F-label tracks mode-switch: `F23 Δ engine.sort_mode alpha→shuffle`
- [ ] R-label diff shows coordinate reassignments after mode-switch
- [ ] Invalid mode name returns error message with valid options

#### Reactive Materialization Tests
- [ ] `codex_materialize.py --boot` generates CODEX.codex
- [ ] `codex_materialize.py --boot` injects into AGENTS.md via existing markers
- [ ] Hash-based change detection: unchanged primitives produce no diff
- [ ] Diff output shows Δ/+/- for changed/added/removed primitives
- [ ] `materialize_affected(['t1'])` only updates t1's section
- [ ] `--full` flag forces complete re-materialization
- [ ] State file `state/materialize_hashes.json` persists between runs
- [ ] Graceful handling when state/materialize_hashes.json doesn't exist (first run)

#### Multi-Pane Tests
- [ ] `--render dense` produces valid engine output
- [ ] `--render json` produces valid JSON
- [ ] `--render pretty` produces readable markdown
- [ ] `--start` creates tmux session with 3 panes
- [ ] `--stop` kills the tmux session
- [ ] `--start t1` renders specific coordinate in all 3 formats
- [ ] JSON output round-trips through `codex_codec.from_codex(codex_codec.to_codex(data))`
- [ ] Pretty output includes emoji status indicators
- [ ] Panes auto-refresh via `watch -n2`

#### Integration Tests
- [ ] MCP server + materialization: MCP read triggers materialization check
- [ ] Mode-switch + materialization: e0x triggers re-materialization
- [ ] Mode-switch + multi-pane: panes update on mode-switch (via watch refresh)
- [ ] MCP + multi-pane: JSON pane matches MCP resource output format

---

## Key Design Decisions

1. **Separate files, not engine bloat.** The V2 engine is already 4272 lines. V3 capabilities are separate modules that import from it. Only ~80 lines added to codex_engine.py (sort mode + e0x dispatch).

2. **stdio MCP transport.** No HTTP server, no websockets. MCP's standard transport is stdio JSON-RPC. Simple, no new dependencies, works with all MCP clients.

3. **Sort mode is session-scoped.** `_current_sort_mode` resets to 'alpha' on each CLI invocation. For persistent mode-switch across agent turns, the materializer records the active sort mode in its hash file.

4. **Materialization replaces --boot, doesn't extend it.** The current `--boot` mechanism is a subset of what the materializer does. V3 makes `--boot` delegate to `CodexMaterializer.boot()` which does supermap + diff + hash tracking.

5. **No daemon for materialization.** `codex_watch.py` already exists as a file-watching daemon. Materialization is triggered by explicit calls (boot, post-mutation), not by filesystem events. This is simpler and more predictable.

6. **Pretty renderer is new, dense and JSON reuse existing.** Dense = existing engine output. JSON = existing codec + load_primitive. Pretty = new human-optimized renderer. Only one new rendering function needed.

7. **codex:// URI scheme.** Not `mcp://` — the MCP spec uses the server name for routing, and resource URIs use custom schemes. `codex://workspace/<coord>` is clean and coordinate-native.

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| MCP spec changes | LOW | Use minimal MCP surface (resources + tools only). Spec is stable for these primitives. |
| Sort mode breaks coordinate-dependent scripts | MED | Sort mode is session-scoped, resets on CLI restart. Persistent mode only via materializer. Scripts that parse coordinates should resolve via slug, not positional index. |
| Materialization performance on large workspaces | LOW | Hash-based diffing means most primitives skip re-render. Current workspace is ~100 primitives — O(100) is trivial. |
| tmux not available | LOW | Multi-pane gracefully degrades: `--render` works standalone. Only `--start` needs tmux. |

---

## Non-Goals (Deferred)

- **Vector-direct encoding** (pre-tokenized representations → encoder) — v4+ territory per task spec
- **Mobile viewport rendering** — polish item, not V3 scope
- **MCP subscriptions** (server-sent events for live updates) — future extension once base MCP works
- **Multi-workspace MCP** — single workspace model for now; `codex://workspace/` prefix allows future extension
