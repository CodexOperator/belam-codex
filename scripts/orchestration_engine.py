#!/usr/bin/env python3
"""
orchestration_engine.py — Orchestration Engine V1

On-demand CLI engine with persistent .codex state buffer.
Manages inter-agent communication, diff-based context sync, and pipeline flow.

Commands:
  status                        Show engine state (agents, pending diffs, flow)
  sync --generate               Compute diffs for changed primitives
  sync --deliver <agent>        Format pending diffs as R/F-labels for target agent
  sync --ready <agent>          Mark agent sync_ready=true (work unit complete)
  dispatch <persona> <coord>    Register dispatch intent in state
  flow --check                  Evaluate pipeline gates and report

State files:
  state/orchestration.codex     Main engine state (agents, diffs, flow)
  state/primitive_hashes.codex  Coord → content hash map for diff detection

Usage examples:
  python3 scripts/orchestration_engine.py status
  python3 scripts/orchestration_engine.py sync --generate
  python3 scripts/orchestration_engine.py sync --deliver architect
  python3 scripts/orchestration_engine.py sync --ready architect
  python3 scripts/orchestration_engine.py dispatch architect t1
  python3 scripts/orchestration_engine.py flow --check
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── Configuration ─────────────────────────────────────────────────────────────

WORKSPACE = Path(os.environ.get('BELAM_WORKSPACE', Path.home() / '.openclaw/workspace'))
STATE_DIR = WORKSPACE / 'state'
ORCH_STATE_FILE = STATE_DIR / 'orchestration.codex'
HASH_STATE_FILE = STATE_DIR / 'primitive_hashes.codex'
PIPELINES_DIR = WORKSPACE / 'pipelines'

# Namespace: prefix → subdirectory (relative to WORKSPACE)
NAMESPACE = {
    'p':  'pipelines',
    'w':  'projects',
    't':  'tasks',
    'd':  'decisions',
    'l':  'lessons',
    'c':  'commands',
    'k':  'knowledge',
}
# Note: memory/skills/daily handled separately; keep V1 scope to core primitives

TREE_ITEM = '╶─'
TREE_INDENT = '   '

# ─── Timestamp helpers ─────────────────────────────────────────────────────────

def now_utc() -> str:
    """Return UTC time as HH:MM string."""
    return datetime.now(timezone.utc).strftime('%H:%M')

def now_iso() -> str:
    """Return full ISO timestamp."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# ─── .codex format: parse ──────────────────────────────────────────────────────

def parse_codex(text: str) -> dict:
    """
    Parse a .codex file into a dict of sections.

    Format:
      # top-level comment (ignored or stored as 'title')
      ## section_name
      ╶─ key  val1  val2  ...
      ╶─ key  val1  val2  ...

    Returns:
      {
        '_title': str,
        'section_name': [
          {'_raw': str, '_key': str, '_rest': str, ...parsed fields...},
          ...
        ],
        ...
      }

    The parser is intentionally simple — each ╶─ line is stored as raw + key + rest.
    Higher-level functions interpret the fields per-section.
    """
    result = {'_title': '', '_sections_order': []}
    current_section = None
    multiline_key = None
    multiline_buf = []

    for line in text.splitlines():
        # Title comment
        stripped = line.strip()
        if stripped.startswith('# ') and current_section is None:
            result['_title'] = stripped[2:].strip()
            continue

        # Section header
        if stripped.startswith('## '):
            # Flush any pending multiline
            if multiline_key and current_section is not None:
                _flush_multiline(result[current_section], multiline_key, multiline_buf)
                multiline_key = None
                multiline_buf = []

            current_section = stripped[3:].strip()
            if current_section not in result:
                result[current_section] = []
                result['_sections_order'].append(current_section)
            continue

        # Item line
        if stripped.startswith(TREE_ITEM) and current_section is not None:
            # Flush previous multiline if any
            if multiline_key:
                _flush_multiline(result[current_section], multiline_key, multiline_buf)
                multiline_key = None
                multiline_buf = []

            rest = stripped[len(TREE_ITEM):].strip()
            parts = rest.split(None, 1)
            key = parts[0] if parts else ''
            rest_str = parts[1] if len(parts) > 1 else ''
            entry = {'_raw': line, '_key': key, '_rest': rest_str}
            result[current_section].append(entry)
            continue

        # Indented continuation lines (multiline body under a ╶─ key)
        if line.startswith('  ') and current_section is not None and result[current_section]:
            last = result[current_section][-1]
            last.setdefault('_body', []).append(stripped)
            continue

    return result


def _flush_multiline(section_list, key, buf):
    """Attach collected multiline body to the last entry."""
    if section_list and buf:
        section_list[-1].setdefault('_body', []).extend(buf)


# ─── .codex format: serialize ─────────────────────────────────────────────────

def serialize_codex(data: dict, title: str = '') -> str:
    """
    Serialize engine state dict back to .codex text.

    data format: same as parse_codex output — sections with lists of entries.
    """
    lines = []
    if title:
        lines.append(f'# {title}')
        lines.append('')

    sections_order = data.get('_sections_order', [k for k in data if not k.startswith('_')])

    for section in sections_order:
        if section.startswith('_'):
            continue
        lines.append(f'## {section}')
        items = data.get(section, [])
        if not items:
            lines.append('')
        for entry in items:
            if isinstance(entry, str):
                # Raw string entry
                lines.append(f'{TREE_ITEM} {entry}')
            elif isinstance(entry, dict):
                if '_raw_line' in entry:
                    lines.append(entry['_raw_line'])
                else:
                    key = entry.get('_key', '')
                    rest = entry.get('_rest', '')
                    line = f'{TREE_ITEM} {key}'
                    if rest:
                        line += f'  {rest}'
                    lines.append(line)
                    for body_line in entry.get('_body', []):
                        lines.append(f'  {body_line}')
        lines.append('')

    return '\n'.join(lines)


# ─── State: agents ─────────────────────────────────────────────────────────────

class AgentEntry:
    """Represents one agent in the agents section."""

    def __init__(self, agent_id: str, persona: str, status: str = 'idle',
                 ctx_hash: str = 'none', synced: str = '00:00',
                 sync_ready: bool = True, task_coord: str = ''):
        self.agent_id = agent_id
        self.persona = persona
        self.status = status
        self.ctx_hash = ctx_hash
        self.synced = synced
        self.sync_ready = sync_ready
        self.task_coord = task_coord

    def to_codex_line(self) -> str:
        """Format as a ╶─ line."""
        ready_flag = 'ready' if self.sync_ready else 'pending'
        task_part = f'  task:{self.task_coord}' if self.task_coord else ''
        return (
            f'{self.agent_id}  {self.persona}  {self.status}  '
            f'ctx:{self.ctx_hash}  synced:{self.synced}  sync:{ready_flag}{task_part}'
        )

    @classmethod
    def from_rest(cls, agent_id: str, rest: str) -> 'AgentEntry':
        """Parse the rest of a ╶─ line."""
        parts = rest.split()
        persona = parts[0] if len(parts) > 0 else 'unknown'
        status = parts[1] if len(parts) > 1 else 'idle'

        ctx_hash = 'none'
        synced = '00:00'
        sync_ready = True
        task_coord = ''

        for tok in parts[2:]:
            if tok.startswith('ctx:'):
                ctx_hash = tok[4:]
            elif tok.startswith('synced:'):
                synced = tok[7:]
            elif tok.startswith('sync:'):
                sync_ready = (tok[5:] == 'ready')
            elif tok.startswith('task:'):
                task_coord = tok[5:]

        return cls(agent_id, persona, status, ctx_hash, synced, sync_ready, task_coord)


# ─── State: diffs ──────────────────────────────────────────────────────────────

class DiffEntry:
    """Represents a pending diff in the pending_diffs section."""

    def __init__(self, diff_id: str, target_coord: str, route: str,
                 labels: list = None, body_lines: list = None):
        self.diff_id = diff_id
        self.target_coord = target_coord
        self.route = route          # e.g. 'a2→*' or 'a1→a2'
        self.labels = labels or []  # e.g. ['[R:status active→complete]', '[F1:+features]']
        self.body_lines = body_lines or []  # Full diff body for delivery

    def to_codex_line(self) -> str:
        label_str = '  '.join(self.labels)
        parts = [self.diff_id, self.target_coord, self.route]
        if label_str:
            parts.append(label_str)
        return '  '.join(parts)

    def to_delivery_block(self) -> str:
        """Format for delivery to an agent."""
        lines = [f'[SYNC {self.target_coord} {self.diff_id}]']
        lines.extend(self.body_lines)
        return '\n'.join(lines)

    @classmethod
    def from_entry(cls, entry: dict) -> 'DiffEntry':
        key = entry['_key']
        rest = entry.get('_rest', '')
        parts = rest.split(None, 2)
        target_coord = parts[0] if len(parts) > 0 else ''
        route = parts[1] if len(parts) > 1 else 'unknown→*'
        labels_raw = parts[2] if len(parts) > 2 else ''

        # Extract bracket labels [R:...] [F...:...]
        labels = re.findall(r'\[(?:R|F\d*)[^\]]*\]', labels_raw)

        body = entry.get('_body', [])
        return cls(key, target_coord, route, labels, body)


# ─── State: flow ───────────────────────────────────────────────────────────────

class FlowEntry:
    """Represents a pipeline in the flow section."""

    def __init__(self, flow_id: str, version: str, stage: str, gate: str = 'open'):
        self.flow_id = flow_id
        self.version = version
        self.stage = stage
        self.gate = gate

    def to_codex_line(self) -> str:
        return f'{self.flow_id}  {self.version}  {self.stage}  gate:{self.gate}'

    @classmethod
    def from_entry(cls, entry: dict) -> 'FlowEntry':
        key = entry['_key']
        rest = entry.get('_rest', '')
        parts = rest.split()
        version = parts[0] if len(parts) > 0 else 'unknown'
        stage = parts[1] if len(parts) > 1 else 'unknown'
        gate = 'open'
        for tok in parts[2:]:
            if tok.startswith('gate:'):
                gate = tok[5:]
        return cls(key, version, stage, gate)


# ─── Engine state: load/save ───────────────────────────────────────────────────

class EngineState:
    """Full engine state: agents + pending_diffs + flow."""

    def __init__(self):
        self.agents: list[AgentEntry] = []
        self.pending_diffs: list[DiffEntry] = []
        self.flow: list[FlowEntry] = []
        self._next_agent_num = 1
        self._next_diff_num = 1
        self._next_flow_num = 1

    # ── Persistence ──────────────────────────────────────────────────────────

    @classmethod
    def load(cls) -> 'EngineState':
        """Load from state/orchestration.codex, or return empty state."""
        state = cls()
        if not ORCH_STATE_FILE.exists():
            return state

        text = ORCH_STATE_FILE.read_text(encoding='utf-8')
        parsed = parse_codex(text)

        # Parse agents
        max_agent_num = 0
        for entry in parsed.get('agents', []):
            key = entry['_key']
            rest = entry.get('_rest', '')
            if key and rest:
                agent = AgentEntry.from_rest(key, rest)
                state.agents.append(agent)
                m = re.match(r'a(\d+)', key)
                if m:
                    max_agent_num = max(max_agent_num, int(m.group(1)))
        state._next_agent_num = max_agent_num + 1

        # Parse pending_diffs
        max_diff_num = 0
        for entry in parsed.get('pending_diffs', []):
            key = entry['_key']
            if key:
                diff = DiffEntry.from_entry(entry)
                state.pending_diffs.append(diff)
                # Parse number from Δ1, Δ2, etc.
                m = re.search(r'(\d+)', key)
                if m:
                    max_diff_num = max(max_diff_num, int(m.group(1)))
        state._next_diff_num = max_diff_num + 1

        # Parse flow
        max_flow_num = 0
        for entry in parsed.get('flow', []):
            key = entry['_key']
            rest = entry.get('_rest', '')
            if key and rest:
                flow = FlowEntry.from_entry(entry)
                state.flow.append(flow)
                m = re.match(r'p(\d+)', key)
                if m:
                    max_flow_num = max(max_flow_num, int(m.group(1)))
        state._next_flow_num = max_flow_num + 1

        return state

    def save(self):
        """Write state to state/orchestration.codex."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        data = {
            '_sections_order': ['agents', 'pending_diffs', 'flow'],
            'agents': [],
            'pending_diffs': [],
            'flow': [],
        }

        for agent in self.agents:
            data['agents'].append({
                '_key': agent.agent_id,
                '_rest': agent.to_codex_line().split(None, 1)[1] if '  ' in agent.to_codex_line() else '',
                '_raw_line': f'{TREE_ITEM} {agent.to_codex_line()}',
            })

        for diff in self.pending_diffs:
            entry = {
                '_key': diff.diff_id,
                '_rest': diff.to_codex_line().split(None, 1)[1] if '  ' in diff.to_codex_line() else '',
                '_raw_line': f'{TREE_ITEM} {diff.to_codex_line()}',
            }
            if diff.body_lines:
                entry['_body'] = diff.body_lines
            data['pending_diffs'].append(entry)

        for flow_entry in self.flow:
            data['flow'].append({
                '_key': flow_entry.flow_id,
                '_rest': flow_entry.to_codex_line().split(None, 1)[1] if '  ' in flow_entry.to_codex_line() else '',
                '_raw_line': f'{TREE_ITEM} {flow_entry.to_codex_line()}',
            })

        text = serialize_codex(data, title='orchestration.codex — Engine State')
        ORCH_STATE_FILE.write_text(text, encoding='utf-8')

    # ── Agent helpers ─────────────────────────────────────────────────────────

    def find_agent(self, identifier: str) -> AgentEntry | None:
        """Find agent by id (a1) or persona (architect)."""
        for agent in self.agents:
            if agent.agent_id == identifier or agent.persona == identifier:
                return agent
        return None

    def next_agent_id(self) -> str:
        aid = f'a{self._next_agent_num}'
        self._next_agent_num += 1
        return aid

    def next_diff_id(self) -> str:
        did = f'Δ{self._next_diff_num}'
        self._next_diff_num += 1
        return did

    def next_flow_id(self) -> str:
        fid = f'p{self._next_flow_num}'
        self._next_flow_num += 1
        return fid

    def diffs_for_agent(self, identifier: str) -> list[DiffEntry]:
        """Return diffs targeted at a specific agent (by id/persona) or '*'."""
        agent = self.find_agent(identifier)
        if not agent:
            # Still match by persona string in route
            target_id = identifier
        else:
            target_id = agent.agent_id

        results = []
        for diff in self.pending_diffs:
            # Route like 'a2→*' or 'a1→a2' or 'a1→architect'
            parts = diff.route.split('→')
            dest = parts[-1] if len(parts) > 1 else '*'
            if dest == '*' or dest == target_id or dest == identifier:
                results.append(diff)
            # Also check by persona
            elif agent and dest == agent.persona:
                results.append(diff)
        return results


# ─── Primitive hash state ──────────────────────────────────────────────────────

def load_hash_state() -> dict:
    """Load coord → hash map from state/primitive_hashes.codex."""
    if not HASH_STATE_FILE.exists():
        return {}
    text = HASH_STATE_FILE.read_text(encoding='utf-8')
    result = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(TREE_ITEM):
            rest = stripped[len(TREE_ITEM):].strip()
            parts = rest.split(None, 1)
            if len(parts) == 2:
                result[parts[0]] = parts[1]
    return result


def save_hash_state(hashes: dict):
    """Write coord → hash map to state/primitive_hashes.codex."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lines = ['# primitive_hashes.codex — Primitive Content Hash Map', '']
    lines.append('## hashes')
    for coord, h in sorted(hashes.items()):
        lines.append(f'{TREE_ITEM} {coord}  {h}')
    lines.append('')
    HASH_STATE_FILE.write_text('\n'.join(lines), encoding='utf-8')


# ─── Primitive scanning ────────────────────────────────────────────────────────

def file_hash(filepath: Path) -> str:
    """SHA256 of file content, first 8 chars."""
    try:
        content = filepath.read_bytes()
        return hashlib.sha256(content).hexdigest()[:8]
    except Exception:
        return 'err'


def scan_primitives() -> dict:
    """
    Scan all core primitive files and return coord → (hash, filepath) dict.
    Coord format: t1, t2, d1, p1, etc. — assigned by sorted file order.
    """
    result = {}
    for prefix, subdir in NAMESPACE.items():
        base = WORKSPACE / subdir
        if not base.exists():
            continue
        files = sorted(base.glob('*.md'))
        for i, f in enumerate(files, 1):
            coord = f'{prefix}{i}'
            h = file_hash(f)
            result[coord] = (h, f)
    return result


# ─── Diff computation ──────────────────────────────────────────────────────────

def extract_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter fields as a simple dict (no yaml dep needed for V1)."""
    fm = {}
    if not text.startswith('---'):
        return fm
    end = text.find('\n---', 3)
    if end < 0:
        return fm
    fm_text = text[3:end]
    for line in fm_text.splitlines():
        m = re.match(r'^(\w[\w-]*):\s*(.*)$', line.strip())
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"\'')
    return fm


def compute_diff(coord: str, filepath: Path, old_hash: str, new_hash: str) -> DiffEntry | None:
    """
    Compute a DiffEntry for a changed primitive.
    Uses simple heuristics to classify R (structural) vs F (body) changes.
    """
    try:
        text = filepath.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None

    fm = extract_frontmatter(text)

    # Build labels and body lines
    labels = []
    body_lines = []

    # Structural fields → R labels
    r_fields = ['status', 'priority', 'depends', 'edges', 'title', 'gate']
    r_changes = []
    for field in r_fields:
        if field in fm:
            r_changes.append(f'{field}:{fm[field]}')

    if r_changes:
        label = '[R:' + ' '.join(r_changes) + ']'
        labels.append(label)
        for change in r_changes:
            body_lines.append(f'  {change}  [R]')

    # Body content → F label
    # Count non-frontmatter lines as body
    body_start = text.find('\n---', 3)
    if body_start >= 0:
        body_text = text[body_start + 4:].strip()
        body_line_count = len([l for l in body_text.splitlines() if l.strip()])
    else:
        body_line_count = len([l for l in text.splitlines() if l.strip()])

    if body_line_count > 0:
        labels.append(f'[F1:~body ({body_line_count} lines)]')
        body_lines.append(f'  body: ~{body_line_count} lines  [F]')

    # Hash transition label
    hash_label = f'Δ{old_hash[:4]}→{new_hash[:4]}'

    diff_id_placeholder = f'Δ?'  # Caller assigns actual ID
    return DiffEntry(
        diff_id=diff_id_placeholder,
        target_coord=coord,
        route=f'engine→*',
        labels=labels,
        body_lines=[f'[SYNC {coord} {hash_label}]'] + body_lines,
    )


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_status(args: list):
    """Display current engine state."""
    state = EngineState.load()

    print('# Orchestration Engine — Status')
    print(f'# {now_iso()}')
    print()

    # Agents
    print('## agents')
    if not state.agents:
        print('  (none registered)')
    else:
        for agent in state.agents:
            ready_mark = '✓' if agent.sync_ready else '⏳'
            task_part = f'  task:{agent.task_coord}' if agent.task_coord else ''
            print(f'  {TREE_ITEM} {agent.agent_id}  {agent.persona}  [{agent.status}]  '
                  f'ctx:{agent.ctx_hash}  synced:{agent.synced}  {ready_mark}{task_part}')
    print()

    # Pending diffs
    print('## pending_diffs')
    if not state.pending_diffs:
        print('  (none pending)')
    else:
        for diff in state.pending_diffs:
            label_str = '  '.join(diff.labels)
            print(f'  {TREE_ITEM} {diff.diff_id}  {diff.target_coord}  {diff.route}  {label_str}')
    print()

    # Flow
    print('## flow')
    if not state.flow:
        print('  (no active pipelines tracked)')
    else:
        for f in state.flow:
            gate_mark = '🔒' if f.gate == 'waiting' else '🔓'
            print(f'  {TREE_ITEM} {f.flow_id}  {f.version}  {f.stage}  {gate_mark} gate:{f.gate}')
    print()

    # Summary
    n_agents = len(state.agents)
    n_diffs = len(state.pending_diffs)
    n_flows = len(state.flow)
    n_pending = sum(1 for a in state.agents if not a.sync_ready)
    print(f'# {n_agents} agents  {n_diffs} pending diffs  {n_flows} flow entries  {n_pending} agents pending sync')


def cmd_sync_generate(args: list):
    """Scan primitives, compute hashes, generate diffs for changed ones."""
    print('# sync --generate')
    print(f'# {now_iso()}')
    print()

    old_hashes = load_hash_state()
    current_primitives = scan_primitives()

    state = EngineState.load()

    new_hashes = {}
    new_diffs = 0
    changed_coords = []

    for coord, (new_hash, filepath) in sorted(current_primitives.items()):
        new_hashes[coord] = new_hash
        old_hash = old_hashes.get(coord)

        if old_hash is None:
            # New primitive — record hash, no diff (first-time scan)
            print(f'  + {coord}  {filepath.name}  (new, hash:{new_hash})')
        elif old_hash != new_hash:
            # Changed — generate diff
            diff = compute_diff(coord, filepath, old_hash, new_hash)
            if diff:
                diff.diff_id = state.next_diff_id()
                state.pending_diffs.append(diff)
                changed_coords.append(coord)
                new_diffs += 1
                print(f'  Δ {coord}  {filepath.name}  {old_hash[:4]}→{new_hash[:4]}  → {diff.diff_id}')
            else:
                print(f'  Δ {coord}  {filepath.name}  (change detected, diff failed)')
        else:
            pass  # Unchanged — silent

    # Check for removed primitives
    removed = set(old_hashes) - set(new_hashes)
    for coord in sorted(removed):
        print(f'  - {coord}  (removed)')

    # Mark agents with pending diffs as sync_ready=false
    if new_diffs > 0:
        for agent in state.agents:
            # Check if any new diff routes to this agent
            agent_diffs = state.diffs_for_agent(agent.agent_id)
            if agent_diffs:
                agent.sync_ready = False
                print(f'  ⏳ {agent.agent_id} ({agent.persona}) marked pending sync')

    save_hash_state(new_hashes)
    state.save()

    print()
    total = len(current_primitives)
    unchanged = total - len(changed_coords) - len([c for c in new_hashes if c not in old_hashes])
    print(f'# scanned {total} primitives  {new_diffs} diffs generated  {len(removed)} removed')
    if not old_hashes:
        print('# (first run — baseline established, no diffs generated)')


def cmd_sync_deliver(args: list):
    """Format and display pending diffs for a target agent."""
    if not args:
        print('ERROR: sync --deliver requires <agent> (id or persona)', file=sys.stderr)
        sys.exit(1)

    target = args[0]
    state = EngineState.load()

    agent = state.find_agent(target)
    if not agent:
        print(f'ERROR: agent not found: {target}', file=sys.stderr)
        print('Registered agents:', [a.agent_id + '/' + a.persona for a in state.agents], file=sys.stderr)
        sys.exit(1)

    diffs = state.diffs_for_agent(target)

    print(f'# SYNC DELIVERY → {agent.agent_id} ({agent.persona})')
    print(f'# {now_iso()}')
    print()

    if not diffs:
        print('# No pending diffs for this agent.')
        print(f'# sync_ready: {agent.sync_ready}')
        return

    for diff in diffs:
        print(diff.to_delivery_block())
        print()

    print(f'# {len(diffs)} diff(s) delivered')
    print(f'# Call: sync --ready {target}  when processing complete')

    # Update agent sync timestamp
    agent.synced = now_utc()
    state.save()


def cmd_sync_ready(args: list):
    """Mark an agent as sync_ready=true (work unit complete)."""
    if not args:
        print('ERROR: sync --ready requires <agent> (id or persona)', file=sys.stderr)
        sys.exit(1)

    target = args[0]
    state = EngineState.load()

    agent = state.find_agent(target)
    if not agent:
        print(f'ERROR: agent not found: {target}', file=sys.stderr)
        sys.exit(1)

    agent.sync_ready = True
    agent.synced = now_utc()
    state.save()

    print(f'# {agent.agent_id} ({agent.persona}) — sync_ready = true')
    print(f'# Downstream agents may now consume diffs from this agent.')


def cmd_dispatch(args: list):
    """Register a dispatch intent: associate a persona with a task coord."""
    if len(args) < 2:
        print('ERROR: dispatch requires <persona> <task_coord>', file=sys.stderr)
        sys.exit(1)

    persona = args[0]
    task_coord = args[1]
    state = EngineState.load()

    # Check if agent with this persona already exists
    existing = state.find_agent(persona)
    if existing:
        # Update task coord and status
        existing.task_coord = task_coord
        existing.status = 'dispatched'
        existing.synced = now_utc()
        state.save()
        print(f'# dispatch updated: {existing.agent_id} ({persona}) → {task_coord}')
        print(f'# Note: Agent spawning is V2. Register intent only.')
        return

    # Create new agent entry
    agent_id = state.next_agent_id()
    ctx_hash = hashlib.sha256(f'{persona}:{task_coord}:{now_iso()}'.encode()).hexdigest()[:4]
    agent = AgentEntry(
        agent_id=agent_id,
        persona=persona,
        status='dispatched',
        ctx_hash=ctx_hash,
        synced=now_utc(),
        sync_ready=True,
        task_coord=task_coord,
    )
    state.agents.append(agent)
    state.save()

    print(f'# dispatch registered: {agent_id} ({persona}) → {task_coord}')
    print(f'# Note: Agent spawning is V2. Dispatch intent recorded only.')
    print()
    print(f'  {TREE_ITEM} {agent.to_codex_line()}')


def cmd_flow_check(args: list):
    """
    Evaluate pipeline gates by reading pipeline files.
    Reports gate states and eligible transitions.
    """
    print('# flow --check')
    print(f'# {now_iso()}')
    print()

    state = EngineState.load()

    # Scan pipeline files for current gate states
    pipelines_found = []
    if PIPELINES_DIR.exists():
        for pf in sorted(PIPELINES_DIR.glob('*.md')):
            try:
                text = pf.read_text(encoding='utf-8', errors='replace')
                fm = extract_frontmatter(text)
                version = fm.get('version', pf.stem)
                status = fm.get('status', 'unknown')
                stage = fm.get('current_stage', fm.get('stage', 'unknown'))
                gate = fm.get('gate', 'open')
                pending_action = fm.get('pending_action', '')
                pipelines_found.append({
                    'file': pf.name,
                    'version': version,
                    'status': status,
                    'stage': stage,
                    'gate': gate,
                    'pending_action': pending_action,
                })
            except Exception as e:
                print(f'  ! {pf.name}: parse error ({e})')

    if not pipelines_found:
        print('  No pipeline files found.')
        print(f'  Looked in: {PIPELINES_DIR}')
    else:
        waiting_gates = []
        open_gates = []

        for p in pipelines_found:
            if p['status'] in ('archived', 'superseded', 'complete'):
                continue
            gate_status = p['gate']
            if gate_status == 'waiting':
                waiting_gates.append(p)
            else:
                open_gates.append(p)

        print(f'## active pipelines ({len(open_gates)} open, {len(waiting_gates)} waiting)')
        for p in open_gates:
            pending = f'  pending:{p["pending_action"]}' if p['pending_action'] else ''
            print(f'  {TREE_ITEM} {p["version"]}  [{p["status"]}]  stage:{p["stage"]}  🔓 gate:open{pending}')
        for p in waiting_gates:
            pending = f'  pending:{p["pending_action"]}' if p['pending_action'] else ''
            print(f'  {TREE_ITEM} {p["version"]}  [{p["status"]}]  stage:{p["stage"]}  🔒 gate:waiting{pending}')

    print()

    # Cross-reference with tracked flow entries
    if state.flow:
        print('## tracked flow entries')
        for f in state.flow:
            gate_mark = '🔒' if f.gate == 'waiting' else '🔓'
            print(f'  {TREE_ITEM} {f.flow_id}  {f.version}  {f.stage}  {gate_mark} gate:{f.gate}')
        print()

    # Sync pipeline state into engine state
    updated = False
    for p in pipelines_found:
        if p['status'] in ('archived', 'superseded', 'complete'):
            continue
        # Find or create flow entry
        existing_flow = None
        for fe in state.flow:
            if fe.version == p['version']:
                existing_flow = fe
                break
        if existing_flow is None:
            flow_id = state.next_flow_id()
            new_flow = FlowEntry(flow_id, p['version'], p['stage'], p['gate'])
            state.flow.append(new_flow)
            updated = True
        else:
            if existing_flow.stage != p['stage'] or existing_flow.gate != p['gate']:
                existing_flow.stage = p['stage']
                existing_flow.gate = p['gate']
                updated = True

    if updated:
        state.save()
        print('# flow state synced from pipeline files')

    # Summary
    n_waiting = len([p for p in pipelines_found
                     if p['status'] not in ('archived', 'superseded', 'complete')
                     and p['gate'] == 'waiting'])
    n_open = len([p for p in pipelines_found
                  if p['status'] not in ('archived', 'superseded', 'complete')
                  and p['gate'] != 'waiting'])
    print(f'# {n_open} open gates  {n_waiting} waiting gates')
    if n_open > 0:
        print(f'# Eligible for dispatch: {n_open} pipeline(s) ready for agent work')


# ─── Main dispatcher ───────────────────────────────────────────────────────────

USAGE = """
orchestration_engine.py — Orchestration Engine V1

Commands:
  status                        Show engine state
  sync --generate               Compute diffs for changed primitives
  sync --deliver <agent>        Deliver pending diffs to target agent
  sync --ready <agent>          Mark agent sync_ready (work unit complete)
  dispatch <persona> <coord>    Register dispatch intent
  flow --check                  Evaluate pipeline gates

Examples:
  python3 scripts/orchestration_engine.py status
  python3 scripts/orchestration_engine.py sync --generate
  python3 scripts/orchestration_engine.py sync --deliver architect
  python3 scripts/orchestration_engine.py sync --ready architect
  python3 scripts/orchestration_engine.py dispatch architect t1
  python3 scripts/orchestration_engine.py flow --check
""".strip()


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(USAGE)
        return

    cmd = args[0]
    rest = args[1:]

    if cmd == 'status':
        cmd_status(rest)

    elif cmd == 'sync':
        if not rest:
            print('ERROR: sync requires --generate, --deliver <agent>, or --ready <agent>', file=sys.stderr)
            sys.exit(1)
        subcmd = rest[0]
        subargs = rest[1:]
        if subcmd == '--generate':
            cmd_sync_generate(subargs)
        elif subcmd == '--deliver':
            cmd_sync_deliver(subargs)
        elif subcmd == '--ready':
            cmd_sync_ready(subargs)
        else:
            print(f'ERROR: unknown sync subcommand: {subcmd}', file=sys.stderr)
            sys.exit(1)

    elif cmd == 'dispatch':
        cmd_dispatch(rest)

    elif cmd == 'flow':
        if rest and rest[0] == '--check':
            cmd_flow_check(rest[1:])
        else:
            print('ERROR: flow requires --check', file=sys.stderr)
            sys.exit(1)

    else:
        print(f'ERROR: unknown command: {cmd}', file=sys.stderr)
        print()
        print(USAGE)
        sys.exit(1)


if __name__ == '__main__':
    main()
