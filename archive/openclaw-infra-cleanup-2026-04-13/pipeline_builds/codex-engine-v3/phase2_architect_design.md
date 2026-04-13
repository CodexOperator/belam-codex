# Codex Render Engine: Phase 2 Architect Design

**Pipeline:** codex-engine-v3  
**Stage:** phase2_architect_design  
**Agent:** architect  
**Date:** 2026-03-22  

---

## Overview

The Codex Render Engine (`codex_render.py`) is a **persistent foreground process** — a read-side daemon that holds the full primitive tree in RAM, detects disk changes, produces continuous diffs, and serves as the codec/context layer for all agents. Think `vim` for the codex: it loads everything on startup, tracks every mutation, and dies when the session dies.

### Core Mental Model

```
                    ┌─────────────────────────────────────┐
                    │     codex_render.py (foreground)     │
                    │                                     │
  inotify ─────────▶  RAM Tree (full primitive state)     │
  (disk changes)   │  ┌─────────────────────────────┐    │
                    │  │ PrimitiveNode per coordinate │    │
                    │  │ - slug, type, frontmatter   │    │
                    │  │ - body, content_hash        │    │
                    │  │ - mtime, edges              │    │
                    │  └─────────────────────────────┘    │
                    │                                     │
                    │  Diff Engine (anchor-based Δ view)   │
                    │  Codec Layer (compression levels)    │
                    │  Context Assembler (SOUL/AGENTS/etc) │
                    │                                     │
  UDS socket ◀─────▶  Session Manager (multi-agent)       │
  (agents attach)  │                                     │
                    │  [test mode] dulwich MemoryRepo      │
                    └─────────────────────────────────────┘
                              │              │
                              ▼              ▼
                         canvas/tmux    before-context
                         dashboard      hook injection
```

### What It Is NOT

- **Not a state engine.** R0/e commands still write to disk via `codex_engine.py`. This is read-side only (except in test mode).
- **Not a daemon.** It runs in the foreground, tied to the session lifecycle. No PID files, no service management.
- **Not a replacement for codex_engine.py.** The engine remains the write path. The render engine is the read/view path.

---

## 1. Module Structure

### Files

| File | Lines (est.) | Description |
|------|:------:|-------------|
| `scripts/codex_render.py` | 800–1000 | Main render engine — RAM tree, inotify, diff, codec, sessions, context assembly, CLI |

Single file. The render engine is conceptually one process with multiple concerns, and splitting into multiple files would create import tangles without meaningful separation. Internal organization via classes keeps it manageable.

### Dependencies

| Dependency | Source | Purpose |
|-----------|--------|---------|
| `ctypes` | stdlib | Raw Linux inotify syscalls (zero external deps) |
| `socket` | stdlib | Unix domain socket for agent sessions |
| `threading` | stdlib | inotify watcher thread, session acceptor thread |
| `json` | stdlib | Session protocol messages |
| `hashlib` | stdlib | Content hashing for diff detection |
| `dulwich` | installed | In-memory git branch for test mode |
| `codex_engine` | workspace | `get_primitives()`, `load_primitive()`, `parse_frontmatter()`, `resolve_coords()`, `render_supermap()`, `NAMESPACE`, `SHOW_ORDER` |
| `codex_codec` | workspace | `to_codex()`, `from_codex()` for codec compression |

No new pip installs needed. `dulwich` is already present. inotify via `ctypes` avoids the `inotify_simple`/`watchdog` dependency.

---

## 2. RAM Tree Data Structure

### PrimitiveNode

```python
@dataclass
class PrimitiveNode:
    """Single primitive loaded into RAM."""
    coord: str              # e.g., "t1", "p3", "md2"
    prefix: str             # e.g., "t", "p", "md"
    index: int              # 1-based coordinate index
    slug: str               # filename stem
    filepath: Path          # canonical disk path
    ptype: str              # type label: "tasks", "pipelines", etc.
    frontmatter: dict       # parsed frontmatter as flat dict
    body: list[str]         # body lines
    content_hash: str       # SHA-256 truncated to 16 chars
    mtime: float            # file modification time (epoch)
    edges_out: list[str]    # outgoing refs (→d25, →l8)
    edges_in: list[str]     # incoming refs (←d25, ←t9)
    raw_text: str           # full file content (for codec operations)
```

### CodexTree

```python
class CodexTree:
    """Full primitive tree held in RAM. Coordinate-addressable."""
    
    def __init__(self):
        self.nodes: dict[str, PrimitiveNode] = {}       # coord → node
        self.by_slug: dict[str, PrimitiveNode] = {}      # slug → node
        self.by_prefix: dict[str, list[PrimitiveNode]] = {}  # prefix → sorted nodes
        self.namespace_counts: dict[str, int] = {}       # prefix → count
        self.load_time: float = 0.0                      # time to load tree
        self.supermap_cache: str | None = None           # cached supermap render
        self._lock: threading.RLock = threading.RLock()  # thread-safe access
    
    def load_full(self, workspace: Path) -> None:
        """Load entire primitive tree from disk into RAM.
        
        Iterates all NAMESPACE prefixes via get_primitives(),
        loads each primitive via load_primitive(), builds index.
        """
    
    def get(self, coord: str) -> PrimitiveNode | None:
        """O(1) coordinate lookup."""
    
    def get_by_slug(self, slug: str) -> PrimitiveNode | None:
        """O(1) slug lookup."""
    
    def get_namespace(self, prefix: str) -> list[PrimitiveNode]:
        """Get all nodes in a namespace, in coordinate order."""
    
    def apply_disk_change(self, filepath: Path) -> DiffEntry | None:
        """Update a single node from disk. Returns diff entry or None if unchanged.
        
        1. Find which node owns this filepath (or create new if unknown file)
        2. Re-read file from disk
        3. Compare content_hash — if identical, return None
        4. Update node fields (frontmatter, body, hash, mtime, edges)
        5. Invalidate supermap_cache
        6. Return DiffEntry describing what changed
        """
    
    def apply_deletion(self, filepath: Path) -> DiffEntry | None:
        """Handle file deletion — remove node, reindex namespace."""
    
    def reindex_namespace(self, prefix: str) -> list[DiffEntry]:
        """Re-read a namespace from disk and reindex.
        
        Needed when files are added/removed (coordinate assignments shift).
        Returns list of diffs for all reassignments.
        """
    
    def render_supermap(self) -> str:
        """Render supermap from RAM tree (no disk I/O).
        
        Uses same visual format as codex_engine.render_supermap() but
        reads from self.nodes instead of disk. Caches result until
        next mutation invalidates it.
        """
    
    def to_codec_view(self, level: str = 'dense') -> str:
        """Compress tree into context-injectable format.
        
        Levels:
          'dense'   — supermap (coordinates + status/priority, ~50 tokens)
          'summary' — supermap + field summaries (~200 tokens)
          'full'    — supermap + all frontmatter (~500 tokens)
          'deep'    — full + body content (~2000+ tokens)
        """
```

### DiffEntry

```python
@dataclass
class DiffEntry:
    """Single change detected between disk and RAM."""
    kind: str          # 'modified', 'added', 'removed', 'reassigned'
    coord: str         # affected coordinate
    slug: str          # primitive slug
    field_diffs: list[tuple[str, str, str]]  # [(field, old_val, new_val), ...]
    timestamp: float   # when detected
```

### Memory Layout

The tree holds ~100–200 primitives (current workspace). Each `PrimitiveNode` is ~2–5KB (frontmatter + body text). Total RAM: **<1MB**. Negligible. No need for memory-mapped files, lazy loading, or eviction — just load everything.

---

## 3. inotify Integration

### Why inotify (not polling)

- **Latency:** inotify fires within milliseconds of disk write. Polling at 500ms introduces unnecessary lag.
- **CPU:** inotify is event-driven — zero CPU when idle. Polling reads directory listings every cycle.
- **Linux-native:** This runs on Linux (aarch64 Oracle VM). No portability concern.

### Implementation via ctypes

No external packages. Direct syscalls via `ctypes`:

```python
class InotifyWatcher:
    """Watch workspace directories for file changes using Linux inotify.
    
    Uses raw ctypes calls to avoid inotify_simple/watchdog dependency.
    Falls back to stat-based polling if inotify initialization fails.
    """
    
    def __init__(self, workspace: Path, callback: Callable[[Path, str], None]):
        self.workspace = workspace
        self.callback = callback  # (filepath, event_type) → None
        self._fd: int = -1
        self._watches: dict[int, Path] = {}  # watch descriptor → directory path
        self._running = False
        self._thread: threading.Thread | None = None
    
    def start(self) -> None:
        """Initialize inotify fd, add watches for all namespace directories, start thread."""
        # inotify_init1(IN_NONBLOCK | IN_CLOEXEC)
        # For each NAMESPACE directory: inotify_add_watch(fd, path, IN_MODIFY | IN_CREATE | IN_DELETE | IN_MOVED_FROM | IN_MOVED_TO)
        # Start self._watch_loop in daemon thread
    
    def stop(self) -> None:
        """Stop watching, close fd."""
        self._running = False
        # close(self._fd)
    
    def _watch_loop(self) -> None:
        """Read events from inotify fd in a loop.
        
        Uses select() with 1s timeout for clean shutdown.
        Batches events within 100ms window to coalesce rapid writes
        (editors often write temp files then rename).
        """
        # while self._running:
        #   readable, _, _ = select.select([self._fd], [], [], 1.0)
        #   if readable:
        #       buf = os.read(self._fd, 8192)
        #       events = self._parse_events(buf)
        #       # Coalesce: collect for 100ms, then deduplicate by filepath
        #       for filepath, event_type in deduplicated:
        #           self.callback(filepath, event_type)
    
    def _parse_events(self, buf: bytes) -> list[tuple[Path, str]]:
        """Parse raw inotify_event structs from buffer.
        
        struct inotify_event {
            int wd;        // watch descriptor
            uint32_t mask;  // event mask
            uint32_t cookie;
            uint32_t len;   // name length
            char name[];    // filename (variable length)
        };
        """
```

### Polling Fallback

If `inotify_init1` fails (e.g., running in a container with restricted syscalls), fall back to stat-based polling:

```python
class StatPoller:
    """Fallback: poll file mtimes every 500ms."""
    
    def __init__(self, workspace: Path, callback: Callable[[Path, str], None]):
        self.workspace = workspace
        self.callback = callback
        self._mtimes: dict[Path, float] = {}
        self._running = False
    
    def start(self) -> None:
        """Start polling thread."""
    
    def _poll_loop(self) -> None:
        """Every 500ms, scan all namespace dirs, compare mtimes."""
```

### Event Flow

```
disk write (codex_engine.py e1 t12)
    → inotify IN_MODIFY on tasks/build-incremental-relationship-mapper.md
    → InotifyWatcher._watch_loop reads event
    → 100ms coalesce window
    → callback(filepath, 'modified')
    → CodexTree.apply_disk_change(filepath)
    → DiffEntry generated
    → DiffEngine.record(diff_entry)
    → supermap_cache invalidated
    → all attached sessions notified
```

---

## 4. Diff Engine

### Anchor-Based Diffing

The diff engine maintains an **anchor point** — a snapshot of tree state at a given moment. All diffs are computed relative to this anchor.

```python
class DiffEngine:
    """Tracks changes relative to an anchor point."""
    
    def __init__(self, tree: CodexTree):
        self.tree = tree
        self._anchor_hashes: dict[str, str] = {}  # coord → content_hash at anchor
        self._anchor_time: float = 0.0
        self._diffs: list[DiffEntry] = []          # accumulated since anchor
        self._lock: threading.Lock = threading.Lock()
    
    def set_anchor(self) -> None:
        """Snapshot current tree state as the anchor.
        
        Copies all content_hashes. Future diffs are relative to this.
        Bare `e` calls this to reset mid-session.
        """
        with self._lock:
            self._anchor_hashes = {
                coord: node.content_hash 
                for coord, node in self.tree.nodes.items()
            }
            self._anchor_time = time.time()
            self._diffs.clear()
    
    def record(self, entry: DiffEntry) -> None:
        """Record a diff entry from a detected change."""
        with self._lock:
            self._diffs.append(entry)
    
    def get_delta(self) -> str:
        """Render accumulated diffs in Δ/+/− format.
        
        Returns:
            R{n}Δ (3 coords shifted)
              Δ t1  status active→complete
              + m156 [03:15] New memory
              − t14  deprecated-task (removed)
        """
    
    def get_delta_since(self, timestamp: float) -> str:
        """Get diffs since a specific timestamp (for agent handoffs)."""
    
    def has_changes(self) -> bool:
        """Quick check: any diffs since anchor?"""
```

### Bare `e` Integration

When the user types bare `e` (already parsed in `codex_engine.py` as the orchestrate/status view), the render engine resets the diff anchor:

```
e  →  codex_engine.py renders current state
   →  render engine receives 'anchor_reset' command via UDS
   →  DiffEngine.set_anchor()
   →  subsequent diffs start fresh
```

This happens automatically when codex_engine.py detects `e` with no arguments. A one-line integration point:

```python
# In codex_engine.py, after e0 (orchestrate) renders:
# Signal render engine to reset anchor (non-blocking, fire-and-forget)
_signal_render_engine('anchor_reset')
```

---

## 5. Shared Agent Sessions (Unix Domain Socket)

### Protocol

The render engine exposes a **Unix domain socket** at `~/.belam_render.sock`. Agents connect, send JSON-line commands, receive JSON-line responses.

```python
class SessionManager:
    """Manages multiple agent connections to the render engine."""
    
    SOCKET_PATH = Path.home() / '.belam_render.sock'
    
    def __init__(self, tree: CodexTree, diff_engine: DiffEngine):
        self.tree = tree
        self.diff_engine = diff_engine
        self._sessions: dict[str, AgentSession] = {}  # session_id → session
        self._server_sock: socket.socket | None = None
        self._running = False
    
    def start(self) -> None:
        """Bind UDS, start accept thread."""
        # Cleanup stale socket file
        # socket.AF_UNIX, socket.SOCK_STREAM
        # bind, listen(5)
        # daemon thread: accept loop
    
    def stop(self) -> None:
        """Close all sessions, unbind socket."""
    
    def _accept_loop(self) -> None:
        """Accept new connections, spawn handler threads."""
    
    def _handle_client(self, conn: socket.socket, addr) -> None:
        """Handle one agent's session.
        
        Read JSON-line commands, dispatch, write JSON-line responses.
        """


@dataclass
class AgentSession:
    """One agent's connection to the render engine."""
    session_id: str
    agent_name: str
    connected_at: float
    last_active: float
    anchor_time: float          # per-session diff anchor
    conn: socket.socket
```

### Session Protocol (JSON-line)

Commands from agent → render engine:

```json
{"cmd": "attach", "agent": "architect"}
{"cmd": "tree", "coord": "t1"}
{"cmd": "tree", "prefix": "p"}
{"cmd": "supermap"}
{"cmd": "diff"}
{"cmd": "diff_since", "timestamp": 1711065600.0}
{"cmd": "anchor_reset"}
{"cmd": "codec", "level": "dense"}
{"cmd": "codec", "level": "summary", "prefix": "t"}
{"cmd": "context"}
{"cmd": "status"}
{"cmd": "detach"}
```

Responses from render engine → agent:

```json
{"ok": true, "session_id": "abc123", "tree_size": 142}
{"ok": true, "node": {"coord": "t1", "slug": "build-incremental...", ...}}
{"ok": true, "delta": "Δ t1 status active→complete\n+ m156 ..."}
{"ok": true, "context": "... assembled context string ..."}
{"ok": true, "status": {"sessions": 2, "tree_size": 142, "uptime_s": 3600}}
```

### Zero-Cost Handoffs

When Agent A finishes and Agent B starts:

1. Agent A's `codex_engine.py` writes were detected via inotify → tree is current
2. Agent B connects to render engine via UDS
3. Agent B sends `{"cmd": "diff_since", "timestamp": <A's_start_time>}` 
4. Gets exactly what A changed — no re-parsing, no boot materialization
5. Agent B sends `{"cmd": "context"}` to get full assembled context
6. Ready to work in <10ms

### Client Helper

A thin client function for `codex_engine.py` to call:

```python
def _signal_render_engine(cmd: str, **kwargs) -> dict | None:
    """Send a command to the render engine if it's running. Non-blocking.
    
    Returns response dict or None if engine isn't running.
    Used for anchor_reset, status checks, etc.
    """
    sock_path = Path.home() / '.belam_render.sock'
    if not sock_path.exists():
        return None
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(str(sock_path))
        msg = json.dumps({"cmd": cmd, **kwargs}) + '\n'
        s.sendall(msg.encode())
        resp = s.recv(65536)
        s.close()
        return json.loads(resp)
    except Exception:
        return None
```

---

## 6. dulwich Test Mode

### Concept

`codex_render.py --test` creates an **in-memory git branch** via dulwich. All `codex_engine.py` writes go through the render engine's virtual filesystem instead of touching disk. The session becomes a branch that can be committed (merge to disk) or discarded (rollback).

### Implementation

```python
class TestMode:
    """In-memory git branch for risk-free experimentation.
    
    Uses dulwich's MemoryRepo to hold an in-memory object store.
    Changes are tracked as dulwich Blob/Tree objects.
    Commit merges objects to the on-disk repo.
    """
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.disk_repo: Repo | None = None        # dulwich Repo (on-disk)
        self.mem_store: MemoryObjectStore = None   # in-memory objects
        self.branch_name: str = ''                 # e.g., 'test/session-abc123'
        self.base_commit: bytes = b''              # commit SHA we branched from
        self._overlay: dict[str, str] = {}         # filepath → content (RAM overlay)
        self._deleted: set[str] = set()            # filepaths deleted in RAM
    
    def start(self) -> str:
        """Initialize test mode.
        
        1. Open on-disk git repo (dulwich.repo.Repo)
        2. Create MemoryObjectStore
        3. Record HEAD as base_commit
        4. Return branch name
        """
        from dulwich.repo import Repo
        from dulwich.object_store import MemoryObjectStore
        
        self.disk_repo = Repo(str(self.workspace))
        self.mem_store = MemoryObjectStore()
        self.base_commit = self.disk_repo.head()
        self.branch_name = f'test/session-{uuid.uuid4().hex[:8]}'
        return self.branch_name
    
    def write(self, filepath: str, content: str) -> None:
        """Intercept a write — store in RAM overlay, don't touch disk."""
        self._overlay[filepath] = content
        self._deleted.discard(filepath)
    
    def read(self, filepath: str) -> str | None:
        """Read from overlay first, then disk."""
        if filepath in self._deleted:
            return None
        if filepath in self._overlay:
            return self._overlay[filepath]
        # Fall through to disk
        disk_path = self.workspace / filepath
        if disk_path.exists():
            return disk_path.read_text(encoding='utf-8')
        return None
    
    def delete(self, filepath: str) -> None:
        """Mark file as deleted in RAM."""
        self._deleted.add(filepath)
        self._overlay.pop(filepath, None)
    
    def commit(self, message: str = 'test mode commit') -> str:
        """Merge RAM overlay to disk.
        
        1. Write all overlay files to disk
        2. Apply all deletions on disk
        3. Git add + commit via dulwich
        4. Return commit SHA
        """
        from dulwich.objects import Blob, Tree, Commit
        
        # Write overlay to disk
        for relpath, content in self._overlay.items():
            target = self.workspace / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
        
        # Apply deletions
        for relpath in self._deleted:
            target = self.workspace / relpath
            if target.exists():
                target.unlink()
        
        # Stage and commit via dulwich
        self.disk_repo.stage(list(self._overlay.keys()) + list(self._deleted))
        commit_sha = self.disk_repo.do_commit(
            message.encode('utf-8'),
            committer=b'codex-render <render@belam>',
        )
        return commit_sha.decode('ascii')
    
    def discard(self) -> None:
        """Discard all changes. Just clear the overlay."""
        self._overlay.clear()
        self._deleted.clear()
    
    def status(self) -> dict:
        """Return test mode status."""
        return {
            'branch': self.branch_name,
            'modified': len(self._overlay),
            'deleted': len(self._deleted),
            'base_commit': self.base_commit.decode('ascii') if self.base_commit else None,
            'files': list(self._overlay.keys()),
        }
```

### Test Mode inotify Integration

In test mode, the render engine's tree reads from the overlay **first**, then disk. The inotify watcher still runs (for changes from other processes), but the tree's `apply_disk_change` checks the overlay before reading disk:

```python
# In CodexTree, when test_mode is active:
def _read_file(self, filepath: Path) -> str | None:
    if self.test_mode:
        relpath = str(filepath.relative_to(self.workspace))
        overlay_content = self.test_mode.read(relpath)
        if overlay_content is not None:
            return overlay_content
    return filepath.read_text(encoding='utf-8', errors='replace')
```

### Intercepting Engine Writes in Test Mode

When test mode is active, `codex_engine.py`'s write operations need to be redirected. The render engine client helper provides a `should_intercept_write()` check:

```python
def _check_test_mode() -> bool:
    """Check if render engine is in test mode. Cache result per-invocation."""
    resp = _signal_render_engine('status')
    return resp and resp.get('test_mode', False)

def _intercept_write(filepath: str, content: str) -> bool:
    """Send write to render engine's test mode overlay. Returns True if intercepted."""
    resp = _signal_render_engine('test_write', filepath=filepath, content=content)
    return resp and resp.get('ok', False)
```

This requires ~3 lines added to `_write_frontmatter_file()` and `_write_body_only()` in `codex_engine.py`:

```python
# At top of _write_frontmatter_file / _write_body_only:
if _check_test_mode():
    if _intercept_write(str(filepath.relative_to(WORKSPACE)), content):
        return
```

---

## 7. Context Assembly API

### What It Replaces

Currently, OpenClaw's before-context hook manually loads:
- `SOUL.md` — personality
- `IDENTITY.md` — role identity
- `AGENTS.md` — workspace guide + supermap
- `USER.md` — user info
- `TOOLS.md` — tool configuration
- `memory/YYYY-MM-DD.md` — daily memory
- `MEMORY.md` — long-term memory index

Each loaded separately, each consuming context tokens. The render engine **owns context assembly** — it knows the full tree and can compress optimally.

### ContextAssembler

```python
class ContextAssembler:
    """Assembles agent context from the RAM tree.
    
    Replaces manual SOUL.md/AGENTS.md/etc. loading.
    Knows how to compress each section based on available token budget.
    """
    
    # Context files in injection order
    CONTEXT_FILES = [
        ('SOUL.md',     'soul',     True),   # (path, key, required)
        ('IDENTITY.md', 'identity', True),
        ('USER.md',     'user',     True),
        ('TOOLS.md',    'tools',    False),
    ]
    
    def __init__(self, workspace: Path, tree: CodexTree):
        self.workspace = workspace
        self.tree = tree
        self._context_cache: dict[str, str] = {}
        self._context_hashes: dict[str, str] = {}
    
    def assemble(self, agent: str = 'main', 
                 include_memory: bool = True,
                 budget_tokens: int | None = None) -> str:
        """Assemble full context for an agent.
        
        Returns a single string containing:
        1. SOUL.md content
        2. IDENTITY.md content  
        3. USER.md content
        4. TOOLS.md content (if exists)
        5. Supermap (from RAM tree, not disk)
        6. Today's memory (from RAM tree)
        7. Delta since last context assembly
        
        If budget_tokens is set, compress sections to fit.
        """
        sections = []
        
        # 1. Load context files (cached, invalidated on inotify)
        for filename, key, required in self.CONTEXT_FILES:
            content = self._load_context_file(filename)
            if content:
                sections.append(content)
            elif required:
                sections.append(f"<!-- {filename} not found -->")
        
        # 2. Supermap from RAM tree
        supermap = self.tree.render_supermap()
        sections.append(f"## Codex Engine Supermap\n\n```\n{supermap}\n```")
        
        # 3. Memory (today + yesterday)
        if include_memory:
            memory_section = self._assemble_memory()
            if memory_section:
                sections.append(memory_section)
        
        # 4. Delta since last assembly for this agent
        delta = self.tree.diff_engine.get_delta()
        if delta:
            sections.append(f"## Changes Since Last Context\n\n```\n{delta}\n```")
        
        full = '\n\n---\n\n'.join(sections)
        
        # 5. Compress if budget set
        if budget_tokens and self._estimate_tokens(full) > budget_tokens:
            full = self._compress_to_budget(sections, budget_tokens)
        
        return full
    
    def _load_context_file(self, filename: str) -> str | None:
        """Load a context file with caching and change detection."""
        path = self.workspace / filename
        if not path.exists():
            return None
        current_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        if self._context_hashes.get(filename) == current_hash:
            return self._context_cache.get(filename)
        content = path.read_text(encoding='utf-8')
        self._context_cache[filename] = content
        self._context_hashes[filename] = current_hash
        return content
    
    def _assemble_memory(self) -> str | None:
        """Assemble memory section from RAM tree's memory namespace."""
        today = datetime.date.today().strftime('%Y-%m-%d')
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        sections = []
        for date_str in [today, yesterday]:
            node = self.tree.get_by_slug(date_str)
            if node and node.raw_text:
                sections.append(f"### Memory: {date_str}\n\n{node.raw_text}")
        
        return '\n\n'.join(sections) if sections else None
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate: chars / 3.5."""
        return int(len(text) / 3.5)
    
    def _compress_to_budget(self, sections: list[str], budget: int) -> str:
        """Progressively compress sections to fit token budget.
        
        Strategy:
        1. Drop TOOLS.md (least critical)
        2. Truncate memory to today only
        3. Compress supermap to dense codec view
        4. Truncate remaining sections
        """
        # Implementation: try progressively more aggressive compression
        # until _estimate_tokens(result) <= budget
```

### Before-Context Hook Integration

The `--boot` flag in `codex_engine.py` currently delegates to `CodexMaterializer.boot()`. With the render engine running, it changes to:

```python
# In codex_engine.py main(), --boot handling:
if '--boot' in args:
    # Try render engine first (if running, context is instant)
    resp = _signal_render_engine('context')
    if resp and resp.get('ok'):
        # Inject assembled context into AGENTS.md
        _inject_context(resp['context'])
        return
    # Fallback: materializer (if render engine not running)
    try:
        from codex_materialize import CodexMaterializer
        CodexMaterializer(WORKSPACE).boot()
    except ImportError:
        # Double fallback: inline boot
        _inline_boot()
```

This is a **graceful degradation** chain: render engine → materializer → inline. The system works at every level; the render engine just makes it faster and richer.

---

## 8. Remote Dashboard

### Canvas/tmux Exposure

The render engine exposes its buffer for remote viewing:

```python
class DashboardServer:
    """Exposes render buffer for canvas/tmux consumption."""
    
    def __init__(self, tree: CodexTree, diff_engine: DiffEngine):
        self.tree = tree
        self.diff_engine = diff_engine
    
    def get_buffer(self, format: str = 'dense') -> str:
        """Return current render buffer in requested format.
        
        Formats:
          'dense'  — supermap tree view
          'json'   — JSON MCP-compatible
          'pretty' — human-readable markdown
          'diff'   — current delta only
          'status' — session/tree status
        """
        if format == 'dense':
            return self.tree.render_supermap()
        elif format == 'json':
            return self._json_view()
        elif format == 'pretty':
            return self._pretty_view()
        elif format == 'diff':
            return self.diff_engine.get_delta()
        elif format == 'status':
            return self._status_view()
    
    def start_tmux_pane(self, format: str = 'dense') -> None:
        """Launch a tmux pane that polls the render buffer.
        
        Uses the UDS client to read the buffer every 2s.
        Replaces codex_panes.py's disk-based watch approach.
        """
```

### Integration with Existing Panes

`codex_panes.py` currently spawns `watch -n2 python3 codex_panes.py --render <format>`, which re-reads from disk each time. With the render engine:

```python
# codex_panes.py can optionally read from render engine:
def render_dense(coord=None):
    # Try render engine first
    resp = _signal_render_engine('buffer', format='dense', coord=coord)
    if resp and resp.get('ok'):
        return resp['content']
    # Fallback to disk
    engine = _get_engine()
    return engine.render_supermap() if not coord else engine.render_zoom([coord])
```

This eliminates the per-render disk I/O in the pane refresh loop.

---

## 9. Main Process Structure

### CodexRenderEngine (Top-Level)

```python
class CodexRenderEngine:
    """Main render engine process. Foreground, session-scoped."""
    
    def __init__(self, workspace: Path, test_mode: bool = False):
        self.workspace = workspace
        self.tree = CodexTree()
        self.diff_engine = DiffEngine(self.tree)
        self.watcher: InotifyWatcher | StatPoller = None
        self.sessions = SessionManager(self.tree, self.diff_engine)
        self.context = ContextAssembler(workspace, self.tree)
        self.dashboard = DashboardServer(self.tree, self.diff_engine)
        self.test: TestMode | None = None
        self._running = False
        
        if test_mode:
            self.test = TestMode(workspace)
    
    def start(self) -> None:
        """Boot sequence:
        
        1. Load full tree into RAM (all primitives)
        2. Set initial diff anchor
        3. Start inotify watcher (or poll fallback)
        4. Start UDS session server
        5. If test mode: initialize dulwich in-memory branch
        6. Print boot status
        7. Enter main loop (block until signal)
        """
        t0 = time.time()
        
        # 1. Load tree
        self.tree.load_full(self.workspace)
        load_time = time.time() - t0
        
        # 2. Anchor
        self.diff_engine.set_anchor()
        
        # 3. File watcher
        try:
            self.watcher = InotifyWatcher(self.workspace, self._on_file_change)
            self.watcher.start()
            watcher_type = 'inotify'
        except Exception:
            self.watcher = StatPoller(self.workspace, self._on_file_change)
            self.watcher.start()
            watcher_type = 'poll'
        
        # 4. Session server
        self.sessions.start()
        
        # 5. Test mode
        if self.test:
            branch = self.test.start()
            print(f"Test mode: branch {branch}")
        
        # 6. Boot status
        print(f"Codex Render Engine started")
        print(f"  Tree: {len(self.tree.nodes)} primitives loaded in {load_time:.2f}s")
        print(f"  Watcher: {watcher_type}")
        print(f"  Socket: {self.sessions.SOCKET_PATH}")
        if self.test:
            print(f"  Test mode: {self.test.branch_name}")
        
        self._running = True
        
        # 7. Main loop
        self._main_loop()
    
    def _main_loop(self) -> None:
        """Block until SIGINT/SIGTERM.
        
        Handles:
        - Graceful shutdown on Ctrl+C
        - SIGUSR1 for status dump
        - SIGUSR2 for anchor reset
        """
        import signal
        
        def _shutdown(signum, frame):
            print("\nShutting down...")
            self._running = False
        
        def _status(signum, frame):
            self._print_status()
        
        def _anchor_reset(signum, frame):
            self.diff_engine.set_anchor()
            print("Diff anchor reset.")
        
        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGUSR1, _status)
        signal.signal(signal.SIGUSR2, _anchor_reset)
        
        while self._running:
            time.sleep(0.5)
        
        self._cleanup()
    
    def _cleanup(self) -> None:
        """Clean shutdown:
        
        1. If test mode with uncommitted changes: prompt to commit
        2. Close all agent sessions
        3. Stop file watcher
        4. Remove socket file
        """
        if self.test and self.test._overlay:
            # In foreground mode, prompt
            print(f"Test mode has {len(self.test._overlay)} uncommitted changes.")
            # Auto-discard in non-interactive, or prompt
        
        self.sessions.stop()
        self.watcher.stop()
        
        # Clean up socket
        if self.sessions.SOCKET_PATH.exists():
            self.sessions.SOCKET_PATH.unlink()
    
    def _on_file_change(self, filepath: Path, event_type: str) -> None:
        """Callback from inotify/poller when a file changes.
        
        1. Check if filepath is a primitive (.md in a namespace dir)
        2. If yes: apply change to tree, record diff
        3. If it's a context file (SOUL.md etc): invalidate context cache
        4. Notify all attached sessions
        """
        # Filter: only care about .md files in namespace dirs, or context files
        if filepath.suffix != '.md' and filepath.name not in ('CODEX.codex',):
            return
        
        if event_type in ('modified', 'created'):
            diff = self.tree.apply_disk_change(filepath)
            if diff:
                self.diff_engine.record(diff)
                self.sessions.notify_all({'event': 'change', 'diff': asdict(diff)})
        elif event_type == 'deleted':
            diff = self.tree.apply_deletion(filepath)
            if diff:
                self.diff_engine.record(diff)
                self.sessions.notify_all({'event': 'change', 'diff': asdict(diff)})
    
    def _print_status(self) -> None:
        """Print current status to stdout."""
        print(f"\n=== Codex Render Engine Status ===")
        print(f"  Uptime: {time.time() - self.diff_engine._anchor_time:.0f}s")
        print(f"  Tree: {len(self.tree.nodes)} nodes")
        print(f"  Sessions: {len(self.sessions._sessions)}")
        print(f"  Diffs since anchor: {len(self.diff_engine._diffs)}")
        if self.test:
            status = self.test.status()
            print(f"  Test mode: {status['modified']} modified, {status['deleted']} deleted")
```

---

## 10. CLI Interface

```
Usage:
  codex_render.py                    # Start render engine (foreground)
  codex_render.py --test             # Start in test mode (in-memory branch)
  codex_render.py --status           # Query running engine status
  codex_render.py --diff             # Get current delta from running engine
  codex_render.py --context          # Get assembled context from running engine
  codex_render.py --anchor-reset     # Reset diff anchor on running engine
  codex_render.py --commit [msg]     # Commit test mode changes
  codex_render.py --discard          # Discard test mode changes
  codex_render.py --buffer [format]  # Get render buffer (dense/json/pretty)
  codex_render.py --stop             # Send shutdown signal
```

Server mode (no flags or `--test`) starts the foreground process. All other flags are **client commands** that connect to a running engine via UDS and return immediately.

```python
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Codex Render Engine')
    parser.add_argument('--test', action='store_true', help='Start in test mode')
    parser.add_argument('--status', action='store_true', help='Query running engine')
    parser.add_argument('--diff', action='store_true', help='Get current delta')
    parser.add_argument('--context', action='store_true', help='Get assembled context')
    parser.add_argument('--anchor-reset', action='store_true', help='Reset diff anchor')
    parser.add_argument('--commit', nargs='?', const='test commit', help='Commit test changes')
    parser.add_argument('--discard', action='store_true', help='Discard test changes')
    parser.add_argument('--buffer', nargs='?', const='dense', help='Get render buffer')
    parser.add_argument('--stop', action='store_true', help='Shutdown running engine')
    parser.add_argument('--workspace', type=str, default=None)
    
    args = parser.parse_args()
    
    # Client commands (connect to running engine)
    if args.status:
        resp = _signal_render_engine('status')
        print(json.dumps(resp, indent=2) if resp else "Render engine not running")
        return
    # ... similar for --diff, --context, --anchor-reset, --commit, --discard, --buffer, --stop
    
    # Server mode
    workspace = Path(args.workspace) if args.workspace else WORKSPACE
    engine = CodexRenderEngine(workspace, test_mode=args.test)
    engine.start()
```

---

## 11. Integration Points with Existing Code

### codex_engine.py Changes (~15 lines)

```python
# 1. Import client helper (top of file, lazy):
# _signal_render_engine() function — copy from render module or inline

# 2. In --boot handler, try render engine first:
# resp = _signal_render_engine('context')
# if resp: inject and return

# 3. After bare `e` render, signal anchor reset:
# _signal_render_engine('anchor_reset')

# 4. In _write_frontmatter_file / _write_body_only, test mode intercept:
# if _check_test_mode(): _intercept_write(...)
```

### codex_materialize.py Changes (0 lines)

No changes. Materializer continues to work as fallback when render engine isn't running. The render engine subsumes its functionality but doesn't replace it.

### codex_panes.py Changes (~5 lines)

```python
# In render_dense/render_json/render_pretty: 
# Try render engine buffer first, fall back to disk reads
```

### codex_codec.py Changes (0 lines)

No changes. Codec is consumed as-is by the render engine for format conversions.

### FLAG Resolution

| FLAG | Source | Resolution |
|------|--------|------------|
| FLAG-1 (MED) | Phase 1 critic | **Subsumed.** Render engine holds tree in RAM — no CODEX.codex parsing needed. The fragile `_read_supermap_from_codex()` separator parsing becomes irrelevant when context comes from the render engine's `ContextAssembler`. |
| FLAG-2 (LOW) | Phase 1 critic | **Resolved.** `CodexTree` exposes full namespace via `get_namespace(prefix)` with no cap. Dashboard/panes read from tree — the 20-entry cap in `_supermap_to_json()` becomes a display choice, not a data limitation. |
| FLAG-3 (LOW) | Phase 1 critic | **Resolved.** The redundant `global _current_sort_mode` in the nested `_restore_shuffle()` function is cleaned up during the engine integration. Use `nonlocal` or refactor to avoid nested globals. |

---

## 12. Lifecycle

### Boot

```
Session starts (OpenClaw)
  → before_context hook
  → codex_engine.py --boot
  → Checks for render engine (UDS socket exists?)
  
  If render engine NOT running:
    → Start codex_render.py as foreground subprocess (or background via &)
    → Wait for UDS socket to appear (max 3s)
    → Read context from render engine
    → Inject into AGENTS.md
  
  If render engine already running:
    → Read context from render engine (instant)
    → Inject into AGENTS.md
```

### Runtime

```
Agent sends e1 t12
  → codex_engine.py writes tasks/xxx.md
  → inotify fires on tasks/ directory
  → Render engine detects change, updates RAM tree
  → DiffEntry recorded: Δ t12 status open→active
  → All attached sessions notified

Agent sends bare `e`
  → codex_engine.py renders orchestrate view
  → codex_engine.py signals render engine: anchor_reset
  → DiffEngine clears accumulated diffs
  → Next delta starts fresh
```

### Shutdown

```
Session ends (OpenClaw)
  → Process receives SIGTERM (or SIGINT from Ctrl+C)
  → If test mode: auto-discard (or prompt to commit)
  → Close all agent sessions
  → Stop inotify watcher
  → Remove UDS socket file
  → Exit
```

---

## 13. Key Design Decisions

1. **Single file, not multi-module.** The render engine is one process with multiple concerns. Internal classes provide separation. External imports from `codex_engine.py` and `codex_codec.py` provide the parsing/rendering substrate. Splitting into 4-5 files would create import complexity without proportional benefit.

2. **UDS over TCP.** Unix domain sockets are faster (no TCP overhead), naturally secured (filesystem permissions), and auto-cleanup on process death. No port conflicts. No firewall concerns.

3. **inotify with ctypes, not watchdog/inotify_simple.** Zero dependency. This runs on a specific Linux host. The 30 lines of ctypes wrapping are simpler than managing a pip dependency that might break.

4. **Overlay-based test mode, not full MemoryRepo.** dulwich's `MemoryRepo` is designed for creating repos from scratch, not overlaying on existing ones. A simple `dict[filepath, content]` overlay with read-through to disk is simpler, faster, and correctly handles the "branch from current state" semantic. dulwich is still used for the final commit operation.

5. **Context assembly as a render engine concern.** The render engine knows the full tree state. It knows what changed. It can compress optimally. Having it own context assembly eliminates the multi-file loading dance in the boot hook.

6. **Graceful degradation chain.** Render engine → materializer → inline boot. The system works at every level. No single point of failure. Agents can function without the render engine; they just get slower context assembly and no live diffs.

7. **No async.** The render engine uses threads (inotify thread, session acceptor thread, main thread). Python's `asyncio` adds complexity without benefit here — the workload is I/O-bound with low concurrency (2-5 agents max). Threads with locks are simpler and sufficient.

8. **Process-scoped, not service-scoped.** The render engine is tied to a session, not to the machine. It starts when an agent session starts and dies when it ends. No systemd unit, no restart logic, no PID file management. If it crashes, the next boot hook restarts it.

---

## 14. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| inotify fd exhaustion | LOW | Each namespace dir = 1 watch descriptor. ~15 dirs = 15 fds. Well under Linux default limits (8192). |
| Race: engine write + inotify read | LOW | inotify events are post-write. 100ms coalesce window handles rapid multi-write sequences. Tree lock prevents concurrent reads during update. |
| Test mode write intercept adds latency | LOW | UDS round-trip is <1ms local. Only active in test mode. |
| Socket file not cleaned on crash | MED | Stale socket detection: `connect()` fails → unlink → recreate. Standard pattern. |
| Thread safety in tree access | MED | `threading.RLock` on CodexTree. All mutations acquire lock. Reads are lock-free for snapshot consistency (dict reads are atomic in CPython). |
| dulwich version compat | LOW | Using only basic objects API (Blob, Tree, Commit, Repo, stage, do_commit). Stable across versions. |

---

## 15. Test Checklist

### Core Tree
- [ ] `load_full()` loads all namespace primitives into RAM
- [ ] `get()` returns correct node by coordinate
- [ ] `get_by_slug()` returns correct node by slug
- [ ] `apply_disk_change()` detects content changes via hash
- [ ] `apply_disk_change()` returns None for unchanged files
- [ ] `reindex_namespace()` handles added/removed files

### inotify
- [ ] Watcher starts and watches all namespace directories
- [ ] File modification triggers callback within 500ms
- [ ] File creation triggers callback
- [ ] File deletion triggers callback
- [ ] 100ms coalesce window deduplicates rapid events
- [ ] Falls back to StatPoller when inotify unavailable

### Diff Engine
- [ ] `set_anchor()` snapshots current tree state
- [ ] `record()` accumulates diff entries
- [ ] `get_delta()` returns Δ/+/− formatted output
- [ ] Bare `e` resets anchor (via UDS or signal)

### Sessions
- [ ] UDS socket created on start, removed on stop
- [ ] Multiple clients can connect simultaneously
- [ ] `attach` command returns session info
- [ ] `tree` command returns node data
- [ ] `diff` command returns current delta
- [ ] `context` command returns assembled context
- [ ] `status` command returns engine status
- [ ] Stale socket detection and cleanup

### Test Mode
- [ ] `--test` creates in-memory overlay
- [ ] Writes go to overlay, not disk
- [ ] Reads check overlay first, then disk
- [ ] `--commit` writes overlay to disk + git commit
- [ ] `--discard` clears overlay
- [ ] Tree reflects overlay state

### Context Assembly
- [ ] Assembles SOUL.md + IDENTITY.md + USER.md + TOOLS.md + supermap + memory
- [ ] Caches context files, invalidates on change
- [ ] Supermap comes from RAM tree (no disk read)
- [ ] Delta section shows changes since last assembly
- [ ] Token budget compression works progressively

### Integration
- [ ] `--boot` tries render engine before materializer
- [ ] `_signal_render_engine()` returns None when engine not running
- [ ] Panes can read from render engine buffer
- [ ] Process exits cleanly on SIGINT/SIGTERM
- [ ] Socket file cleaned up on exit

---

## 16. Build Order

1. **PrimitiveNode + CodexTree** — data structures and tree loading
2. **DiffEngine** — anchor/diff tracking
3. **InotifyWatcher + StatPoller** — file change detection
4. **SessionManager** — UDS server + protocol
5. **ContextAssembler** — context assembly API
6. **DashboardServer** — buffer exposure
7. **TestMode** — dulwich integration
8. **CodexRenderEngine** — main process orchestration
9. **CLI** — argument parsing + client commands
10. **Engine integration** — ~15 lines in codex_engine.py
