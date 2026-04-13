# Architect Design: Codex Engine V3 — Legendary Map (LM)

**Pipeline:** codex-engine-v3-legendary-map  
**Stage:** architect_design  
**Agent:** architect  
**Date:** 2026-03-23

---

## 1. Problem Statement

The supermap shows *what exists* (state). There is no equivalent structure for *what you can do* (actions). Action knowledge currently lives in the system prompt, external doc injections, or the agent's weights — all fragile, session-volatile, or invisible to the attention mechanism.

The Legendary Map (LM) closes this gap: a self-generating `lm` namespace on the supermap that encodes the engine's full action grammar as navigable coordinates, processed in the same single attention pass as state.

---

## 2. Architecture Overview

### 2.1 Sources → LM Entries → Supermap

```
modes/*.md          ──┐
commands/*.md       ──┤  LegendaryMapRenderer._generate_entries()
RENDER_VERBS (const)──┤  → list[LMEntry]
TOOL_PATTERNS (const)─┘

LMEntry {n, verb, syntax, desc, source, source_file, workflows[]}
         ↓
render_legendary_map()  →  "╶─ lm  legendary map (N)\n│  ╶─ lm1  ..."

render_supermap()  →  [LM block first] + [p, t, d, ...]
```

### 2.2 Module Location

All LM code lives in `scripts/codex_engine.py` (no new file needed). New additions:

- `LM_RENDER_VERBS` — module-level constant list
- `LM_TOOL_PATTERNS` — module-level constant list  
- `class LegendaryMapRenderer` — mtime-cached entry generator
- `render_legendary_map()` — supermap block renderer
- `render_lm_zoom(n)` — expanded single-entry view (syntax + params + example)
- `render_lm_workflow(base_coord, l_index)` — sub-index workflow renderer
- Hook in `render_supermap()` — inject LM block first
- Hook in `e3` handler — invalidate LM cache
- Hook in `e2` handler — invalidate LM cache when target is modes/ or commands/

---

## 3. Data Model

### 3.1 LMEntry

```python
@dataclass
class LMEntry:
    n: int                    # sequential 1-based index → lm{n}
    verb: str                 # action name, kebab-case (e.g. "edit-body")
    syntax: str               # invocation pattern IS the command template
    desc: str                 # ≤35 chars — context annotation for supermap
    source: str               # 'mode' | 'render_verb' | 'tool' | 'command'
    source_file: Path | None  # for auto-invalidation
    params: list[str]         # param descriptions for zoom view
    example: str              # runnable example for zoom view
    workflows: list[dict]     # [{n, name, body}] — sub-index workflows
```

### 3.2 Source Attribution

| Source | When included | Update trigger |
|--------|--------------|----------------|
| `mode` | `status` not in EXCLUDED_STATUSES | e2/e3 in modes/ |
| `render_verb` | always (hardcoded constant) | engine release |
| `tool` | always (hardcoded constant) | engine release |
| `command` | `lm_include: true` in frontmatter | e2 in commands/ |

**Commands are opt-in via `lm_include: true` frontmatter flag.** The `e2 c` scaffolding template will set `lm_include: false` by default. Architects promote commands by setting `lm_include: true`. This enforces the ≤1KB budget invariant.

---

## 4. Entry Set (Initial)

20 entries target. At ~45 chars/line avg: `20 × 45 + 33 (header) ≈ 933 bytes` — well within 1KB.

### 4.1 Modes (4 entries — sourced from modes/*.md)

Syntax extracted from first "### Usage" line in mode body. Falls back to mode `description` field.

| n | verb | syntax | source |
|---|------|--------|--------|
| 1 | orchestrate | `e0` | modes/orchestrate.md |
| 2 | pipeline-op | `e0p{n} {op}` | modes/orchestrate.md `operation_index` |
| 3 | edit-field | `e1{coord} {F} {val}` | modes/edit.md |
| 4 | edit-body | `e1{coord} B+ {text}` | modes/edit.md |
| 5 | create | `e2 {ns} "{title}"` | modes/create.md |
| 6 | extend-ns | `e3 category {name}` | modes/extend.md |

> Modes generate **multiple** entries when `operation_index` is present (one per logical operation group). The renderer maps operation clusters to verb names. e0 generates entries 1–2 from its `operation_index` frontmatter.

### 4.2 Render Verbs (6 entries — constant `LM_RENDER_VERBS`)

```python
LM_RENDER_VERBS = [
    LMEntry(verb='navigate',     syntax='{coord}',               desc='render primitive'),
    LMEntry(verb='graph',        syntax='{coord} -g',            desc='show relationships'),
    LMEntry(verb='diff',         syntax='.d',                    desc='diff vs anchor'),
    LMEntry(verb='anchor',       syntax='.a',                    desc='set diff anchor'),
    LMEntry(verb='filter-tag',   syntax='{coord} --tag {t}',     desc='filter by tag'),
    LMEntry(verb='persona-view', syntax='{coord} --as {role}',   desc='persona filter'),
]
```

### 4.3 Tool Patterns (5 entries — constant `LM_TOOL_PATTERNS`)

```python
LM_TOOL_PATTERNS = [
    LMEntry(verb='memory-search', syntax='memory_search("{q}")',         desc='search memory'),
    LMEntry(verb='spawn-agent',   syntax='sessions_spawn(label,task)',   desc='fork subagent'),
    LMEntry(verb='exec-shell',    syntax='exec(cmd)',                    desc='run shell'),
    LMEntry(verb='send-message',  syntax='message(action,target,msg)',   desc='send message'),
    LMEntry(verb='web-fetch',     syntax='web_fetch(url)',               desc='fetch URL'),
]
```

### 4.4 CLI Commands (5 entries — `lm_include: true` in frontmatter)

Initial candidates to tag `lm_include: true`:

| command file | verb | syntax |
|---|---|---|
| status.md | status | `belam status` |
| log.md | log-memory | `belam log "{msg}"` |
| spawn.md | spawn-belam | `belam -x spawn {agent} "{task}"` |
| kickoff.md | pipeline-kick | `belam kickoff {ver}` |
| orchestrate.md | orchestrate-cli | `belam orchestrate {op} {ver} {stage}` |

**Total: 6 (mode) + 6 (render) + 5 (tool) + 5 (cli) = 22 entries**

At 22 × 45 chars avg + header = ~1023 bytes. Right at limit. 

**Budget rule:** LM renderer enforces a hard cap. If generated entries exceed 1KB rendered, it trims from the `command` tier first (lowest priority), then warns via stderr. Target is ≤20 entries for comfortable margin.

---

## 5. Supermap Rendering

### 5.1 Format

```
╶─ lm  legendary map (20)
│  ╶─ lm1   orchestrate     e0
│  ╶─ lm2   pipeline-op     e0p{n} {op}
│  ╶─ lm3   edit-field      e1{coord} {F} {val}
│  ╶─ lm4   edit-body       e1{coord} B+ {text}
│  ╶─ lm5   create          e2 {ns} "{title}"
│  ╶─ lm6   extend-ns       e3 category {name}
│  ╶─ lm7   navigate        {coord}
│  ╶─ lm8   graph           {coord} -g
│  ╶─ lm9   diff            .d
│  ╶─ lm10  anchor          .a
│  ╶─ lm11  filter-tag      {coord} --tag {t}
│  ╶─ lm12  persona-view    {coord} --as {role}
│  ╶─ lm13  memory-search   memory_search("{q}")
│  ╶─ lm14  spawn-agent     sessions_spawn(label,task)
│  ╶─ lm15  exec-shell      exec(cmd)
│  ╶─ lm16  send-message    message(action,target,msg)
│  ╶─ lm17  web-fetch       web_fetch(url)
│  ╶─ lm18  status          belam status
│  ╶─ lm19  log-memory      belam log "{msg}"
│  ╶─ lm20  pipeline-kick   belam kickoff {ver}
```

**Column alignment:** verb padded to 16 chars, syntax not padded (variable length, no right-side annotation to save space).

**The syntax column IS the invocation template** — no separate description column. The verb name provides semantic context. This keeps each line ≤55 chars.

### 5.2 Insertion Point in `render_supermap()`

```python
def render_supermap(persona=None, tag_filter=None, since_days=None, only_prefixes=None):
    ...
    lines.append(header)
    
    # ── Legendary Map (first namespace — top-of-tree priming) ──────────────
    if only_prefixes is None or 'lm' in only_prefixes:
        lm_block = render_legendary_map()
        lines.extend(lm_block.splitlines())
    
    # ── Standard namespaces ─────────────────────────────────────────────────
    for prefix in SHOW_ORDER:   # ['p', 't', 'd', 'l', 'w', 'c', 'k', 's', 'e', 'i']
        ...
```

`lm` is NOT added to `SHOW_ORDER` (which drives the standard loop). It has its own dedicated block before the loop. This avoids coupling to the existing namespace machinery.

### 5.3 LM always fully expanded

Unlike standard namespaces that truncate at 5 when count > 10, LM always renders all entries. Rationale: the action grammar is the point — truncating it defeats the purpose.

---

## 6. Navigation: `lm{n}` Zoom

When the agent types `lm3`, the router resolves it to `render_lm_zoom(3)`, which renders the full entry:

```
lm3  edit-field
  syntax:   e1{coord} {F} {val}
  source:   modes/edit.md  (e1)
  params:
    {coord}  target primitive coordinate (e.g. t1, p3, d2)
    {F}      field number (from zoom view of primitive, e.g. 2)
    {val}    new value (string, no quotes needed unless spaces)
  example:
    e1t1 2 active        → set task 1 field 2 to "active"
    e1p3 B+ "appended"  → append to pipeline 3 body
  see also: lm4 (edit-body), e1 (full mode spec)
```

**Implementation:** `render_lm_zoom(n)` looks up entry by index, renders formatted block. This is called by the main router when `lm` prefix + digit is detected.

**Router integration:**
```python
# In main() arg parsing, before COORD_RE matching:
lm_match = re.match(r'^lm(\d+)$', arg)
if lm_match:
    render_lm_zoom(int(lm_match.group(1)))
    return
```

---

## 7. Hierarchical Workflow Sub-indices

### 7.1 Dot-syntax: `{coord}.l{n}`

| Expression | Meaning |
|---|---|
| `e0.l1` | first complex orchestration workflow |
| `e1.l3` | third edit workflow |
| `e2.l1` | first create workflow |
| `.v.l2` | second view-group workflow |
| `l` (bare) | lessons namespace (UNCHANGED) |
| `lm3` | zoom to LM entry 3 (UNCHANGED) |

**Disambiguation:** `.l` as sub-index only when preceded by a coord + dot. `l` bare = lessons always.

### 7.2 Workflow Storage in Mode Files

Workflows live as `## Workflow N: {name}` sections in each mode's `.md` body:

```markdown
## Workflow 1: Full pipeline sweep with status report

e0                  # run full sweep
e0p{n} status       # check specific pipeline

Triggers: gate evaluation, stall detection, lock release.
Use when: starting a session, after task completion.
```

The LM renderer parses these sections when generating entries. Workflows are stored in `LMEntry.workflows` as:
```python
[{'n': 1, 'name': 'Full pipeline sweep', 'body': '...markdown...'}]
```

### 7.3 Router for Sub-indices

```python
# Dot-syntax pattern: coord.l{n}
DOT_L_RE = re.compile(r'^(e\d+|\.v|\.r)\.(l\d+)$')

def handle_dot_l(match, args):
    base_coord, l_coord = match.group(1), match.group(2)
    l_n = int(l_coord[1:])
    render_lm_workflow(base_coord, l_n)
```

`render_lm_workflow(base_coord, n)` finds the mode file for `base_coord` (or the view-group constant for `.v`), extracts workflow `n`, and renders it.

### 7.4 View Group (`.v`)

`.v.l{n}` references view-group workflows — complex multi-step rendering patterns. These are hardcoded in `LM_VIEW_WORKFLOWS` constant since view verbs are engine-internal:

```python
LM_VIEW_WORKFLOWS = [
    {'n': 1, 'name': 'Scoped investigation flow',
     'body': '{coord}\n{coord} -g\n{coord} --tag {t}\n\nPattern: land → graph → filter'},
    {'n': 2, 'name': 'Temporal diff workflow', 
     'body': '.a\n# ... do work ...\n.d\n\nPattern: anchor → work → diff to see changes'},
]
```

---

## 8. Auto-Update Hooks

### 8.1 Cache Invalidation

```python
_LM_CACHE = {'entries': None, 'source_mtime': 0.0}

def _invalidate_lm_cache():
    """Force LM re-generation on next render."""
    _LM_CACHE['entries'] = None
    _LM_CACHE['source_mtime'] = 0.0

def _lm_source_mtime() -> float:
    """Max mtime across modes/ and commands/ directories."""
    dirs = [WORKSPACE / 'modes', WORKSPACE / 'commands']
    mtimes = []
    for d in dirs:
        for f in d.glob('*.md'):
            try: mtimes.append(f.stat().st_mtime)
            except: pass
    return max(mtimes, default=0.0)

def _get_lm_entries() -> list:
    mtime = _lm_source_mtime()
    if _LM_CACHE['entries'] is None or mtime > _LM_CACHE['source_mtime']:
        _LM_CACHE['entries'] = _generate_lm_entries()
        _LM_CACHE['source_mtime'] = mtime
    return _LM_CACHE['entries']
```

### 8.2 e3 Hook

In `execute_e3()` (or wherever e3 runs), after successful namespace registration:

```python
_invalidate_lm_cache()
```

### 8.3 e2 Hook

In `execute_create()`, after file is written, if target namespace is `e` (modes) or `c` (commands):

```python
if namespace in ('e', 'c'):
    _invalidate_lm_cache()
```

### 8.4 Mtime-based Lazy Re-render

The mtime check in `_get_lm_entries()` handles external edits (e.g. direct file edits). The cache is invalidated when any modes/*.md or commands/*.md file is newer than the cached generation time. This covers:
- `e3 category` creating new mode files
- `e2 e` creating new mode primitives  
- `e2 c` creating new command primitives
- Direct file edits (agent writes to mode file)
- Archiving a command (mtime changes, re-gen excludes it)

---

## 9. Payload Budget Enforcement

```python
LM_MAX_BYTES = 1024

def render_legendary_map() -> str:
    entries = _get_lm_entries()
    
    lines = [f"╶─ lm  legendary map ({len(entries)})"]
    for e in entries:
        lines.append(f"│  ╶─ lm{e.n:<3} {e.verb:<16} {e.syntax}")
    
    rendered = '\n'.join(lines)
    
    if len(rendered.encode('utf-8')) > LM_MAX_BYTES:
        # Trim from lowest-priority tier (commands) first
        trimmed_entries = [e for e in entries if e.source != 'command']
        lines = [f"╶─ lm  legendary map ({len(trimmed_entries)}, commands trimmed)"]
        for e in trimmed_entries:
            lines.append(f"│  ╶─ lm{e.n:<3} {e.verb:<16} {e.syntax}")
        rendered = '\n'.join(lines)
        
        if len(rendered.encode('utf-8')) > LM_MAX_BYTES:
            # Emergency: hard truncate + note
            rendered = rendered[:LM_MAX_BYTES - 30] + '\n│  ... [lm truncated]'
    
    return rendered
```

---

## 10. `lm` as Navigable Coordinate

### 10.1 Router Integration

The main router needs to handle `lm` as a pseudo-prefix:

```python
# Add 'lm' to parse path before standard NAMESPACE lookup
if arg.startswith('lm') and arg[2:].isdigit():
    n = int(arg[2:])
    print(render_lm_zoom(n))
    return

# Bare 'lm' → show full LM namespace view
if arg == 'lm':
    print(render_legendary_map())
    return
```

`lm` is NOT added to `NAMESPACE` dict (it's virtual, no backing directory). It's handled as a special case before the standard namespace loop.

### 10.2 `--supermap` inclusion

`lm` entries are included in `--supermap` output since they're rendered by `render_supermap()`. No separate flag needed.

---

## 11. Implementation Plan for Builder

### Phase 1: Core Renderer (est. 150 lines)

1. Define `LM_RENDER_VERBS` and `LM_TOOL_PATTERNS` constants (30 lines)
2. Implement `_generate_lm_entries()` — parse modes/*.md, apply constants, filter commands (60 lines)
3. Implement `render_legendary_map()` with budget enforcement (30 lines)
4. Implement `render_lm_zoom(n)` (30 lines)

### Phase 2: Supermap Integration (est. 20 lines)

5. Hook `render_legendary_map()` into `render_supermap()` as first block
6. Add `lm` + `lm{n}` routing to main router
7. Add `.d`/`.a` dot-syntax routing (may already exist — verify)

### Phase 3: Auto-update Hooks (est. 20 lines)

8. Add `_invalidate_lm_cache()` + `_lm_source_mtime()` + `_LM_CACHE` 
9. Hook into `execute_e3()` post-registration
10. Hook into `execute_create()` post-file-write for `e`/`c` namespaces

### Phase 4: Sub-index Routing (est. 40 lines)

11. Implement `DOT_L_RE` matching in router
12. Implement `render_lm_workflow(base_coord, n)` — parse mode file workflows
13. Define `LM_VIEW_WORKFLOWS` constant for `.v.l{n}`

### Phase 5: Frontmatter Tags (est. 10 lines)

14. Add `lm_include: true` to 5 priority command files
15. Update `e2 c` scaffolding template to include `lm_include: false`

### Total: ~240 lines new code + ~30 lines hooks/routing changes

---

## 12. File Changes Summary

| File | Change |
|------|--------|
| `scripts/codex_engine.py` | Add ~270 lines: LMEntry dataclass, constants, renderer, zoom, workflow renderer, cache, hooks, router cases |
| `commands/status.md` | Add `lm_include: true` |
| `commands/log.md` | Add `lm_include: true` |
| `commands/spawn.md` | Add `lm_include: true` |
| `commands/kickoff.md` | Add `lm_include: true` |
| `commands/orchestrate.md` | Add `lm_include: true` |
| `modes/orchestrate.md` | Add `## Workflow 1:` section |
| `modes/edit.md` | Add `## Workflow 1:` and `## Workflow 2:` sections |
| `scripts/create_primitive.py` | Add `lm_include: false` to command template |

---

## 13. Acceptance Criteria Mapping

| Criterion | Implementation |
|-----------|---------------|
| `lm` namespace in supermap | §5.2 — injected before SHOW_ORDER loop |
| All e0–e3 have lm entries | §4.1 — modes/*.md sourced |
| Active commands have lm entries | §4.4 — `lm_include: true` opt-in |
| Render verbs have lm entries | §4.2 — `LM_RENDER_VERBS` constant |
| e3 auto-updates LM | §8.2 — post-registration hook |
| Archive removes entry | §8.3 — mtime invalidation + `EXCLUDED_STATUSES` filter |
| LM fully expanded (no truncation) | §5.3 — no MAX_SHOW cap on lm |
| Total payload ≤ 1KB | §9 — budget enforcement with tiered trim |
| `lm{n}` navigates to action | §10.1 — router special-case |
| Tool patterns included | §4.3 — `LM_TOOL_PATTERNS` constant |
| First namespace in supermap | §5.2 — before SHOW_ORDER loop |
| Hierarchical sub-indices | §7 — `{coord}.l{n}` dot-syntax routing |

---

## 14. Design Decisions & Rationale

**Why not a `lm` directory?** The LM is generated, not authored. A directory implies manual maintenance. Auto-generation from sources is the whole point — the lathe sees itself.

**Why `lm_include: true` opt-in for commands?** 27 active commands would immediately blow the 1KB budget. Opt-in keeps the architect in control of what's hot-path vs available via `c{n}` zoom.

**Why not render verbs in a file?** Render verbs are engine internals — they don't have backing primitives. A constant is the right representation. If we ever want them editable, they can become `modes/` primitives.

**Why mtime-based cache?** inotify would require OS resources and wouldn't work cross-platform. Mtime check on render is cheap (<1ms for ~30 files) and always correct.

**Why sub-indices in mode files?** Colocates complex workflow docs with their mode definition. When the mode evolves (via e1 edit), the workflow evolves with it. No separate maintenance burden.

**Why `.v` for view group?** View verbs (navigate, graph, diff, anchor) don't have a mode file — they're engine-internal. `.v` is the dot-prefixed group name, consistent with the dot-syntax convention for non-primitive addresses.
