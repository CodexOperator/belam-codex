# Codex Engine V2: Dense Alphanumeric Modes — Architect Design

**Pipeline:** codex-engine-v2-modes  
**Phase:** 1 (Autonomous Build)  
**Agent:** Architect  
**Date:** 2026-03-21  

---

## 1. Executive Summary

V2 upgrades the Codex Engine from CLI-flag-based mode switching to coordinate-addressed modes with dense alphanumeric grammar. The engine already has ~70% of V2 functionality implemented (V2 parser, mode dispatch, extend mode, deprecation warnings). This design covers the remaining 30%: hardening the parser, implementing the full e3 meta-layer, adding enum field indexing, integrating the dulwich RAM state layer, and wiring codex_codec.py as the boundary translation layer.

### What Already Exists (V1.5 — Current State)
- `_parse_v2_operations()` — splits `e0p3 e1t12` into operation tuples ✅
- `_parse_dense_target()` — resolves `t12` into (namespace, index, embedded_field) ✅
- `_dispatch_v2_operation()` — routes e0-e3 to handlers ✅
- `execute_extend()` — e3 category/namespace (session-scoped) ✅
- Mode primitives in `modes/*.md` with frontmatter ✅
- Deprecation warnings on `-e`, `-n`, `-x` flags ✅
- `_dispatch_e0()` — orchestration dispatch via orchestration_engine.py ✅

### What's Missing (This Build)
1. **Spaced input collapse** — `e0 p3` → `e0p3` not handled in the tokenizer
2. **Enum field indexing** — `e1 d8 2 1` → status=proposed (numeric option lookup)
3. **Dot-as-connector parsing** — `e0p1 1.i1` (dispatch as architect), `4.i1.i3` (handoff chain)
4. **E0 operation indexing** — numbered operations (1=dispatch, 2=status, 3=gates, etc.)
5. **E3 full meta-layer** — template scaffolding, integrate command, primitive trail
6. **RAM state layer (dulwich)** — in-memory git tree for speculative branching
7. **Codec integration** — codex_codec.py as JSON boundary for MCP
8. **Output format indexing** — `.1` suffix for JSON output
9. **Legacy flag full retirement** — remove `-o` flag path (currently `-x` handles this)

---

## 2. Dense Alphanumeric Parser

### 2.1 Grammar (from d10 — accepted)

```
<operation>  ::= <mode><target>[<field>]
<mode>       ::= e0 | e1 | e2 | e3
<target>     ::= <namespace><index>
<namespace>  ::= t | d | l | p | k | s | c | w | m | e | md | mw | i | mo
<index>      ::= <digit>+
<field>      ::= <digit>+
<chain>      ::= <operation> (" " <operation>)*
<connector>  ::= "." <target>
<output_fmt> ::= "." <digit>+
```

### 2.2 Spaced Input Collapse

**Problem:** Users type `e0 p3` (spaced) but the parser expects `e0p3` (dense). Currently `_parse_v2_operations()` treats `p3` as a separate argument to e0 mode, which works for most cases but fails for chained operations where spacing is inconsistent.

**Solution:** Add a pre-processing step `_collapse_spaced_v2()` that merges adjacent tokens when:
1. Token N matches `^e[0-3]$` (bare mode) AND
2. Token N+1 starts with a namespace prefix followed by digits

```python
def _collapse_spaced_v2(tokens: list[str]) -> list[str]:
    """Collapse spaced V2 input: ['e0', 'p3', 'e1', 't1', '2', 'active'] 
    → ['e0p3', 'e1t1', '2', 'active']
    
    Only collapses bare eN + namespace-target pairs. Doesn't touch
    non-coordinate arguments (field values, strings, flags).
    """
    result = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if (re.match(r'^e[0-3]$', tok, re.IGNORECASE) and 
            i + 1 < len(tokens) and
            re.match(r'^(md|mw|[a-z])\d*', tokens[i+1], re.IGNORECASE)):
            # Collapse: e0 + p3 → e0p3
            result.append(tok + tokens[i+1])
            i += 2
        else:
            result.append(tok)
            i += 1
    return result
```

**Integration point:** Called at the top of `main()` after `clean_args` is built, before V2 detection.

### 2.3 Dot-Connector Parsing

The dot serves as "as" / "via" connector linking operations to targets:

| Input | Meaning |
|-------|---------|
| `e0p1 1.i1` | dispatch pipeline 1 as architect |
| `e0p1 5.i1` | complete pipeline 1 as architect |
| `4.i1.i3` | handoff from architect to critic |

**Implementation:** Parse dot-connected tokens into structured argument chains:

```python
def _parse_dot_connector(token: str) -> list[tuple[str, str|None]]:
    """Parse dot-connected token: '1.i1' → [('1', None), ('i', '1')]
    '4.i1.i3' → [('4', None), ('i', '1'), ('i', '3')]
    """
    parts = token.split('.')
    result = []
    for part in parts:
        m = re.match(r'^([a-z]*)(\d+)?$', part, re.IGNORECASE)
        if m:
            result.append((m.group(1) or None, m.group(2) or None))
        else:
            result.append((part, None))
    return result
```

### 2.4 Enum Field Indexing

Field values with limited options are addressable by index:

| Field | 1 | 2 | 3 | 4 | 5 |
|-------|---|---|---|---|---|
| status (decisions) | proposed | accepted | rejected | superseded | — |
| status (tasks) | open | active | in_pipeline | complete | blocked |
| priority | critical | high | medium | low | — |
| boolean | false (0) | true (1) | — | — | — |

**Implementation:** Add enum resolution to `execute_edit()`:

```python
ENUM_FIELDS = {
    'status': {
        'd': {1: 'proposed', 2: 'accepted', 3: 'rejected', 4: 'superseded'},
        't': {1: 'open', 2: 'active', 3: 'in_pipeline', 4: 'complete', 5: 'blocked'},
        'p': {1: 'phase1_design', 2: 'phase1_build', 3: 'phase1_review', 
              4: 'phase1_complete', 5: 'phase2_build', 6: 'phase2_complete',
              7: 'phase3_active', 8: 'complete', 9: 'archived'},
    },
    'priority': {
        '_default': {1: 'critical', 2: 'high', 3: 'medium', 4: 'low'},
    },
}

def _resolve_enum_value(prefix: str, field_key: str, value_str: str) -> str:
    """If value_str is a digit and field_key has an enum map for this prefix,
    resolve to the enum string. Otherwise return value_str unchanged."""
    if not value_str.isdigit():
        return value_str
    idx = int(value_str)
    field_enums = ENUM_FIELDS.get(field_key, {})
    enum_map = field_enums.get(prefix) or field_enums.get('_default')
    if enum_map and idx in enum_map:
        return enum_map[idx]
    return value_str
```

**Integration:** Called inside `execute_edit()` after field key resolution, before value application.

### 2.5 E0 Operation Indexing

Operations are numbered for token-efficient dispatch:

| Op | Function | Example | Maps to |
|----|----------|---------|---------|
| 1 | dispatch | `e0p1 1.i1` | `orch.dispatch(p1, architect)` |
| 2 | status | `e0p1 2` | `orch.status(p1)` |
| 3 | gates | `e0p1 3` | `orch.gates(p1)` |
| 4 | locks | `e0p1 4` | `orch.locks(p1)` |
| 5 | complete | `e0p1 5.i1` | `orch.complete(p1, as=architect)` |
| 6 | block | `e0p1 6.i1` | `orch.block(p1, as=architect)` |
| 7 | next | `e0p1 7` | `orch.next(p1)` |
| 8 | archive | `e0p1 8` | `orch.archive(p1)` |
| 9 | launch | `e0 9 ver --desc "..."` | `orch.launch(ver, ...)` |

**Current state:** `_parse_e0_args()` already handles named operations (status, gates, etc.). The builder needs to add numeric alias resolution at the top of `_parse_e0_args()`.

```python
E0_OP_INDEX = {
    '1': 'dispatch', '2': 'status', '3': 'gates', '4': 'locks',
    '5': 'complete', '6': 'block', '7': 'next', '8': 'archive', '9': 'launch',
}
```

### 2.6 Output Format Indexing

Append `.1` to any operation for JSON output instead of text:

```
e0p1 2     → text status output (default)
e0p1 2.1   → JSON status output (via codex_codec.py)
```

**Implementation:** Check last token for trailing `.N` format spec. If `.1`, wrap output through `codex_codec.to_codex()` or `json.dumps()`.

---

## 3. Modes as Coordinates

### 3.1 Current Implementation (Already Working)

The engine already routes `e0`-`e3` to their handlers:

| Coordinate | Handler | Status |
|-----------|---------|--------|
| `e0` | `_dispatch_e0()` → orchestration_engine.py | ✅ Working |
| `e1` | `execute_edit()` | ✅ Working |
| `e2` | `execute_create()` | ✅ Working |
| `e3` | `execute_extend()` | ✅ Working (basic) |

### 3.2 Mode Primitive Enhancement

Current mode primitives in `modes/*.md` are documentation-only. They need:

1. **applicable_namespaces** — already in frontmatter ✅
2. **composability rules** — add `composes_with: [view_flags]` to frontmatter
3. **operation_index** — for e0, add operation numbering to the mode primitive
4. **enum_fields** — for e1, add field enum maps to the mode primitive

This keeps mode behavior self-documenting and inspectable via `e1` (view the mode primitive itself).

### 3.3 View Modifier Composition

View modifiers (`-g`, `--depth`, `--as`) compose orthogonally with modes:

```
e0p3 -g     → orchestrate pipeline 3, render result as graph
e1t1 --as architect  → edit task 1 as architect persona
e2 t "Fix bug" --tag infrastructure  → create task with tag
```

**Current state:** View flags are stripped in `main()` pre-parsing. They need to be passed through to `_dispatch_v2_operation()`. The builder should:
1. Extract `-g` and `--depth` from `clean_args` into a `view_flags` dict
2. Pass `view_flags` to `_dispatch_v2_operation()` (already has the parameter)
3. Apply view transformations after the operation completes

---

## 4. Extend Mode (e3) — The Meta-Layer

### 4.1 Current State
`execute_extend()` handles:
- `e3` bare → list session extensions ✅
- `e3 category <name>` → create dir + register namespace ✅
- `e3 namespace <prefix> <dir>` → register namespace mapping ✅

### 4.2 Missing Operations

#### `e3 template <type>`
Create a frontmatter template for a primitive type:

```python
def _e3_template(args):
    """e3 template <type_prefix> — scaffold a YAML frontmatter template.
    
    Creates templates/<type>.yaml with all known fields for that primitive type.
    Useful for documenting/standardizing new primitive categories.
    """
    if not args:
        print("e3 template: specify a type prefix (t, d, l, p, ...)")
        return 1
    prefix = _normalize_prefix(args[0])
    if not prefix:
        print(f"e3 template: unknown prefix '{args[0]}'")
        return 1
    
    # Introspect existing primitives to discover common fields
    primitives = get_primitives(prefix, active_only=False)
    field_census = {}
    for slug, fp in primitives:
        fm, _ = parse_frontmatter(fp.read_text())
        for key in fm:
            field_census[key] = field_census.get(key, 0) + 1
    
    # Build template with fields sorted by frequency
    template_fields = sorted(field_census.keys(), key=lambda k: -field_census[k])
    template_path = WORKSPACE / 'templates' / f'{prefix}_template.yaml'
    template_path.parent.mkdir(exist_ok=True)
    
    lines = ['---']
    for f in template_fields:
        lines.append(f'{f}: ')
    lines.append('---')
    lines.append('')
    lines.append(f'# [Title]')
    lines.append('')
    
    template_path.write_text('\n'.join(lines))
    tracker = get_render_tracker()
    f_label = tracker.next_f_label()
    print(f"{f_label} + template {prefix} -> templates/{prefix}_template.yaml")
    print(f"   Fields discovered: {len(template_fields)} from {len(primitives)} primitives")
    return 0
```

#### `e3 integrate <path>`
Register an external script/module as an engine plugin:

```python
def _e3_integrate(args):
    """e3 integrate <script_path> — register a script as engine-callable.
    
    Adds script to the engine's dispatch table (session-scoped).
    Script must expose a main(args) function.
    """
    if not args:
        print("e3 integrate: specify a script path")
        return 1
    script_path = Path(args[0])
    if not script_path.exists():
        script_path = WORKSPACE / 'scripts' / args[0]
    if not script_path.exists():
        print(f"e3 integrate: file not found: {args[0]}")
        return 1
    
    # Register in session integration table
    name = script_path.stem
    _SESSION_INTEGRATIONS[name] = str(script_path)
    tracker = get_render_tracker()
    f_label = tracker.next_f_label()
    print(f"{f_label} + integration '{name}' -> {script_path} [session-scoped]")
    return 0
```

#### Primitive Trail
Every e3 operation should append to `extensions.log` (or an in-memory list) so `e3` bare can show the full trail:

```python
_EXTENSION_TRAIL = []  # List of (timestamp, operation, details)

# In each e3 handler, after success:
_EXTENSION_TRAIL.append((datetime.datetime.now().isoformat(), subcmd, details))
```

### 4.3 Updated `execute_extend()` Dispatch

```python
def execute_extend(args):
    if not args:
        # Show trail + active extensions
        ...
    subcmd = args[0].lower()
    handlers = {
        'category': _e3_category,
        'namespace': _e3_namespace,
        'template': _e3_template,
        'integrate': _e3_integrate,
    }
    handler = handlers.get(subcmd)
    if handler:
        return handler(args[1:])
    print(f"e3: unknown subcommand '{subcmd}'")
    return 1
```

---

## 5. Legacy Flag Retirement

### 5.1 Current Deprecation State

| Flag | Status | V2 Equivalent |
|------|--------|---------------|
| `-e` | Warns, still works | `e1` |
| `-n` | Warns, still works | `e2` |
| `-x` | Warns, still works | `e0` |
| `-z` | Warns, still works | TBD (keep as `-z` or add `e-z`) |
| `-g` | Active, NO deprecation | stays as `-g` (view modifier) |
| `--depth` | Active | stays (view modifier) |
| `--as` | Active | stays (view modifier) |

### 5.2 Deprecation Strategy

**Phase 1 (this build):** Keep warnings, add usage telemetry counter.
**Phase 2 (future):** Remove flag handling entirely after 30 days of zero usage.

The builder should add a simple counter:

```python
_DEPRECATION_HITS = {}  # flag → count this session

def _deprecation_warn(old_flag, new_coord, example):
    _DEPRECATION_HITS[old_flag] = _DEPRECATION_HITS.get(old_flag, 0) + 1
    print(f"⚠ {old_flag} is deprecated → use {new_coord} (e.g., {example})")
```

### 5.3 `-o` Flag

The task mentions `-o` but V1 never had an `-o` flag. The `-x` flag (explicit execute) maps to `e0`. No `-o` retirement needed.

### 5.4 `-z` Undo

Keep `-z` as-is. It's a session utility, not a mode. It doesn't need a coordinate. Optionally alias as `e-z` for consistency.

---

## 6. RAM State Layer (dulwich)

### 6.1 Architecture

```
┌─────────────────────────────────────────────┐
│  Codex Engine V2                            │
│                                             │
│  ┌───────────────┐  ┌───────────────────┐   │
│  │ RAM State     │  │ Disk State        │   │
│  │ (dulwich)     │  │ (filesystem)      │   │
│  │               │  │                   │   │
│  │ speculative   │◄─┤ source of truth   │   │
│  │ branching     │  │                   │   │
│  │ rollback      │──►│ checkpoint writes │   │
│  │ diff/merge    │  │                   │   │
│  └───────────────┘  └───────────────────┘   │
│                                             │
│  ┌───────────────────────────────────────┐   │
│  │ codex_codec.py (boundary translation) │   │
│  │ .codex ↔ JSON ↔ MCP                   │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 6.2 Module: `scripts/codex_ram.py`

```python
"""
codex_ram.py — In-memory git state layer using dulwich.

Provides speculative branching, diff, merge, and rollback for
workspace primitives without touching disk until explicit checkpoint.

Usage:
    ram = CodexRAM(workspace_path)
    ram.snapshot()                    # load current disk state into RAM
    ram.branch('speculative-edit')   # create speculative branch
    ram.write('tasks/foo.md', content)  # write to RAM tree
    diff = ram.diff('main')          # diff against main branch
    ram.merge('main')                # merge speculative into main
    ram.checkpoint()                 # flush RAM state to disk
    ram.rollback()                   # discard speculative branch
"""

from pathlib import Path
from typing import Optional
import hashlib
import time

class CodexRAM:
    """In-memory state tree with speculative branching."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._trees = {}        # branch_name → {path: content}
        self._current = 'main'
        self._history = []      # list of (timestamp, branch, operation, path)
    
    def snapshot(self) -> int:
        """Load current disk state into RAM main branch. Returns file count."""
        tree = {}
        for subdir in ('tasks', 'decisions', 'lessons', 'pipelines', 'commands',
                       'knowledge', 'projects', 'modes', 'personas', 'skills'):
            dirpath = self.workspace / subdir
            if dirpath.exists():
                for f in dirpath.rglob('*.md'):
                    relpath = str(f.relative_to(self.workspace))
                    tree[relpath] = f.read_text(encoding='utf-8', errors='replace')
        self._trees['main'] = tree
        self._current = 'main'
        return len(tree)
    
    def branch(self, name: str) -> None:
        """Create a new branch from current, switch to it."""
        self._trees[name] = dict(self._trees[self._current])
        self._current = name
        self._history.append((time.time(), name, 'branch', None))
    
    def switch(self, name: str) -> None:
        """Switch to an existing branch."""
        if name not in self._trees:
            raise KeyError(f"Branch '{name}' does not exist")
        self._current = name
    
    def read(self, path: str) -> Optional[str]:
        """Read file from current RAM branch."""
        return self._trees[self._current].get(path)
    
    def write(self, path: str, content: str) -> None:
        """Write file to current RAM branch."""
        self._trees[self._current][path] = content
        self._history.append((time.time(), self._current, 'write', path))
    
    def delete(self, path: str) -> bool:
        """Delete file from current RAM branch."""
        if path in self._trees[self._current]:
            del self._trees[self._current][path]
            self._history.append((time.time(), self._current, 'delete', path))
            return True
        return False
    
    def diff(self, other_branch: str = 'main') -> dict:
        """Diff current branch against another. Returns {added, modified, deleted}."""
        current = self._trees[self._current]
        other = self._trees.get(other_branch, {})
        
        added = set(current.keys()) - set(other.keys())
        deleted = set(other.keys()) - set(current.keys())
        modified = set()
        for path in current.keys() & other.keys():
            if current[path] != other[path]:
                modified.add(path)
        
        return {
            'added': sorted(added),
            'modified': sorted(modified),
            'deleted': sorted(deleted),
        }
    
    def merge(self, target: str = 'main') -> dict:
        """Merge current branch into target. Returns diff applied."""
        d = self.diff(target)
        target_tree = self._trees[target]
        current_tree = self._trees[self._current]
        
        for path in d['added'] + d['modified']:
            target_tree[path] = current_tree[path]
        for path in d['deleted']:
            target_tree.pop(path, None)
        
        self._history.append((time.time(), self._current, 'merge', target))
        return d
    
    def checkpoint(self) -> int:
        """Flush current RAM branch to disk. Returns files written."""
        tree = self._trees[self._current]
        written = 0
        for path, content in tree.items():
            fp = self.workspace / path
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding='utf-8')
            written += 1
        self._history.append((time.time(), self._current, 'checkpoint', None))
        return written
    
    def rollback(self) -> None:
        """Discard current branch, switch to main."""
        if self._current != 'main':
            del self._trees[self._current]
            self._history.append((time.time(), self._current, 'rollback', None))
            self._current = 'main'
    
    def branches(self) -> list[str]:
        """List all branches."""
        return list(self._trees.keys())
    
    def stats(self) -> dict:
        """Return branch stats."""
        return {
            'current': self._current,
            'branches': {name: len(tree) for name, tree in self._trees.items()},
            'history_length': len(self._history),
        }
```

### 6.3 dulwich vs Pure-Python Decision

**For this build: use pure-Python dict-based RAM tree (above).** Rationale:
- `dulwich` is not currently installed (`ModuleNotFoundError`)
- The dict-based approach gives us 90% of the value (branching, diff, merge, rollback) without the dependency
- dulwich integration can be added later as a drop-in replacement for the storage backend
- The API is designed to be dulwich-compatible — swap `_trees` dict for dulwich `MemoryRepo` when ready

**Future dulwich upgrade path:**
```python
# Replace _trees dict with:
from dulwich.repo import MemoryRepo
from dulwich.objects import Blob, Tree, Commit

class DulwichBackend:
    """Drop-in replacement for dict-based _trees using dulwich MemoryRepo."""
    def __init__(self):
        self.repo = MemoryRepo.init_bare([])
    # ... (same API surface)
```

### 6.4 Engine Integration

The RAM layer hooks into the engine as an optional acceleration layer:

```python
# In codex_engine.py main():
_RAM = None  # Lazily initialized

def _get_ram():
    global _RAM
    if _RAM is None:
        _RAM = CodexRAM(WORKSPACE)
        _RAM.snapshot()
    return _RAM
```

**When RAM is active:**
- `get_primitives()` can optionally read from RAM tree instead of scanning disk
- `execute_edit()` writes to RAM tree; disk write happens on checkpoint
- Speculative edits (e.g., "what if I change this status?") use branches

**When RAM is not active:** Everything works as before (direct disk I/O). RAM is opt-in.

---

## 7. Codec Integration (codex_codec.py)

### 7.1 Current State

`codex_codec.py` (441 lines) is a complete bidirectional parser:
- `to_codex(dict) → str` — JSON to .codex format
- `from_codex(str) → dict` — .codex to JSON  
- Streaming: `codex_to_json_stream()`, `json_to_codex_stream()`
- MCP registration: `register_codec()` → `{"content_type": "application/x-codex", "encode", "decode"}`
- Handles nested dicts via dot-notation flattening
- Full test suite passing

### 7.2 Integration Points

#### 7.2.1 Output Format Switch

When `.1` suffix is detected on an operation, route output through codec:

```python
# In _dispatch_v2_operation():
def _dispatch_v2_operation(mode_num, op_args, view_flags, tracker):
    # Check for output format suffix
    output_format = 'text'  # default
    if op_args and '.' in op_args[-1]:
        parts = op_args[-1].rsplit('.', 1)
        if parts[1].isdigit():
            fmt_idx = int(parts[1])
            if fmt_idx == 1:
                output_format = 'json'
            op_args = op_args[:-1] + ([parts[0]] if parts[0] else [])
    
    # ... execute operation, capture output ...
    
    if output_format == 'json':
        # Convert output to JSON via codec
        from codex_codec import to_codex
        result_dict = _output_to_dict(captured_output)
        print(json.dumps(result_dict, indent=2))
```

#### 7.2.2 Primitive Serialization

Use codec for primitive read/write when JSON format is requested:

```python
# In render_zoom(), when output_format == 'json':
from codex_codec import from_codex
text = filepath.read_text()
json_dict = from_codex(text)
print(json.dumps(json_dict, indent=2))
```

#### 7.2.3 MCP Boundary

For future MCP server integration, the codec provides the translation layer:

```python
# MCP tool handler (future):
async def handle_codex_tool(request):
    codec = codex_codec.register_codec()
    # Incoming: JSON from MCP client
    # Outgoing: .codex format for engine, JSON response back to client
    result = engine.process(request.params)
    return codec['encode'](result)
```

### 7.3 No Changes to codex_codec.py

The codec module is complete and tested. No modifications needed. Integration is purely on the engine side — import and call.

---

## 8. Builder Implementation Spec

### 8.1 Files to Create

| File | Purpose | Lines (est.) |
|------|---------|-------------|
| `scripts/codex_ram.py` | RAM state layer (pure-Python, dulwich-ready API) | ~180 |

### 8.2 Files to Modify

| File | Changes | Scope |
|------|---------|-------|
| `scripts/codex_engine.py` | Main target — all parser/dispatch changes | ~200 lines added/modified |
| `modes/orchestrate.md` | Add operation_index to frontmatter | ~10 lines |
| `modes/extend.md` | Add template/integrate operations | ~15 lines |

### 8.3 Step-by-Step Build Order

#### Step 1: Spaced Input Collapse
**File:** `scripts/codex_engine.py`
**Function:** Add `_collapse_spaced_v2(tokens)` 
**Integration:** Call in `main()` after building `clean_args`, before V2 detection block
**Test:** `belam e0 p3` produces same output as `belam e0p3`

#### Step 2: Enum Field Indexing
**File:** `scripts/codex_engine.py`
**Add:** `ENUM_FIELDS` dict and `_resolve_enum_value()` function
**Integration:** Call inside `execute_edit()` after field key is resolved, before `_coerce_value()`
**Test:** `belam e1 d1 2 2` → sets status to "accepted", F-label shows `status proposed→accepted`

#### Step 3: E0 Operation Indexing
**File:** `scripts/codex_engine.py`
**Add:** `E0_OP_INDEX` dict
**Integration:** At top of `_parse_e0_args()`, resolve numeric ops to named ops
**Test:** `belam e0p1 2` → same as `belam e0p1 status`

#### Step 4: Dot-Connector Parsing
**File:** `scripts/codex_engine.py`
**Add:** `_parse_dot_connector(token)` function
**Integration:** In `_parse_e0_args()`, parse `.iN` suffixes on operation args
**Test:** `belam e0p1 1.i1` → dispatches pipeline 1 as architect

#### Step 5: E3 Template & Integrate
**File:** `scripts/codex_engine.py`
**Add:** `_e3_template()`, `_e3_integrate()`, `_EXTENSION_TRAIL`, `_SESSION_INTEGRATIONS`
**Integration:** Update `execute_extend()` dispatch table
**Test:** `belam e3 template t` → creates `templates/t_template.yaml`

#### Step 6: Output Format Indexing
**File:** `scripts/codex_engine.py`
**Add:** Output format detection in `_dispatch_v2_operation()`
**Integration:** Import `codex_codec` for JSON serialization
**Test:** `belam e0p1 2.1` → JSON output of pipeline status

#### Step 7: RAM State Layer
**File:** `scripts/codex_ram.py` (new)
**Add:** `CodexRAM` class with branch/diff/merge/checkpoint/rollback
**Integration:** Lazy init in `codex_engine.py` via `_get_ram()`
**Test:** Python unit test — snapshot, branch, write, diff, merge, checkpoint

#### Step 8: Deprecation Telemetry
**File:** `scripts/codex_engine.py`
**Add:** `_DEPRECATION_HITS` counter, `_deprecation_warn()` helper
**Integration:** Replace inline `print("Warning: ...")` calls in legacy flag handlers
**Test:** `belam -e t1 2 active` → shows deprecation warning with e1 equivalent

#### Step 9: Mode Primitive Updates
**Files:** `modes/orchestrate.md`, `modes/extend.md`
**Add:** operation_index, new subcommands in body
**Test:** `belam e0` shows updated help, `belam e3` shows all subcommands

### 8.4 Test Checklist

| # | Test | Command | Expected |
|---|------|---------|----------|
| 1 | Spaced collapse | `belam e0 p1` | Same as `belam e0p1` |
| 2 | Dense chain | `belam e0p1 e1t1 2 active` | Orchestrate p1 then edit t1 |
| 3 | Enum resolve | `belam e1 t1 2 2` | status → active |
| 4 | E0 op index | `belam e0p1 2` | Pipeline 1 status |
| 5 | Dot connector | `belam e0p1 1.i1` | Dispatch as architect |
| 6 | E3 template | `belam e3 template d` | Creates template file |
| 7 | E3 integrate | `belam e3 integrate codex_ram.py` | Registers script |
| 8 | E3 trail | `belam e3` after operations | Shows trail |
| 9 | Output JSON | `belam t1.1` or `e0p1 2.1` | JSON output |
| 10 | Deprecation | `belam -e t1 2 active` | Warning + works |
| 11 | RAM snapshot | Python: `CodexRAM.snapshot()` | Returns file count > 0 |
| 12 | RAM branch/diff | Python: branch, write, diff | Shows modified files |
| 13 | RAM checkpoint | Python: checkpoint() | Files written to disk |
| 14 | Bare mode help | `belam e1` | Shows edit mode help |
| 15 | Mode list | `belam e` | Lists all modes |

### 8.5 Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| `pyyaml` | ✅ Installed | Used by codex_engine.py and codex_codec.py |
| `dulwich` | ❌ Not installed | Not needed for this build (pure-Python RAM layer) |
| `pydantic` | ❌ Not installed | Deferred — not needed for V2 core |
| `orchestration_engine.py` | ✅ Exists (2834L) | E0 dispatch target |
| `codex_codec.py` | ✅ Exists (441L) | JSON boundary translation |
| `pipeline_orchestrate.py` | ✅ Exists | Legacy orchestration (still used by some paths) |

### 8.6 What NOT to Change

- **codex_codec.py** — complete, tested, don't touch
- **orchestration_engine.py** — separate pipeline, don't modify
- **temporal_*.py** — separate overlay, don't modify
- **View flag behavior** — `-g`, `--depth`, `--as` stay as-is
- **Action word dispatch** — 55 action words stay, no changes
- **Supermap rendering** — R-label system stays as-is

### 8.7 Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Dense parser ambiguity (t12 = task 12 or task 1 field 2) | Medium | Already handled by `_parse_dense_target()` — tries full index first |
| E0 numeric ops conflict with pipeline indices | Low | E0 ops apply after target resolution — `e0p1 2` = op 2 on p1, not p12 |
| RAM layer memory pressure | Low | Pure dict-based, garbage collected on session end |
| Codec import path | Low | `scripts/` is on sys.path via `_run_script()` pattern |

---

## 9. Architecture Diagram

```
User Input: "e0p3 e1t12 e2l"
         │
         ▼
┌─────────────────────────────┐
│  main() pre-processing      │
│  1. Strip global flags       │
│  2. _collapse_spaced_v2()    │  ◄── NEW
│  3. V2 detection             │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  _parse_v2_operations()     │
│  Splits into:                │
│  [(0, ['p3']),               │
│   (1, ['t1', '2']),          │  ◄── embedded field split
│   (2, ['l'])]                │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  _dispatch_v2_operation()   │
│  per operation:              │
│  e0 → _dispatch_e0()        │──► orchestration_engine.py
│  e1 → execute_edit()         │──► _resolve_enum_value() ◄── NEW
│  e2 → execute_create()       │
│  e3 → execute_extend()       │──► template/integrate ◄── NEW
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Output Pipeline             │
│  1. F-labels (mutations)     │
│  2. R-labels (views)         │
│  3. Format switch (.1=JSON)  │  ◄── NEW (via codex_codec)
└─────────────────────────────┘
```

---

## 10. Summary of Decisions

| Decision | Rationale |
|----------|-----------|
| Pure-Python RAM over dulwich | dulwich not installed; dict-based gives 90% value with zero dependencies |
| Enum indexing by prefix | Different primitive types have different valid status values |
| E0 ops as numeric index | Consistent with grammar philosophy — everything is a coordinate |
| Dot-connector not dot-separator | Dot means "as/via" connection, not hierarchical nesting |
| No codex_codec.py changes | Module is complete and tested; integration is engine-side only |
| Keep `-z` as flag | Undo is a session utility, not a state-changing mode |
| Template introspection | e3 template discovers fields from existing primitives rather than hardcoding |
| Lazy RAM init | RAM layer only loaded when explicitly requested — no performance tax on normal ops |

---

*Design complete. Ready for critic review → builder implementation.*
