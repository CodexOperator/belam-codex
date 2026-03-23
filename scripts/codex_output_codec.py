"""Codex Output Codec — transforms command outputs into coordinate-addressed results.

Phase A of the Codex Layer. Provides:
  - Output recognition pipeline (JSON → table → KV → raw)
  - Known script parsers for top workspace scripts
  - Result register with transient coordinates (_, _1, _2, ...)
  - Dot notation field access (_.status, _.p1)

Register state persists per-workspace at {workspace}/.codex_result_register.json
(FLAG-1: scoped per-workspace, not HOME, to avoid cross-agent clobber).

Pipeline: build-codex-layer-v1
"""

from __future__ import annotations

import json
import re
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, List, Any


# ── Data model ──────────────────────────────────────────────────────────────

@dataclass
class CodexResult:
    """A coordinate-addressed result from any command execution."""
    coord: str = '_'          # transient coord: "_" (latest), "_1", "_2"
    source: str = ''          # what generated it: "e0", "!git status", "t5"
    content_type: str = 'text'  # 'table' | 'json' | 'kv' | 'text' | 'codex'
    fields: Dict[str, Any] = field(default_factory=dict)
    raw: str = ''             # original output
    rendered: str = ''        # codex-formatted output
    timestamp: float = 0.0    # epoch seconds (for TTL — S2)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'CodexResult':
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Result Register ─────────────────────────────────────────────────────────

REGISTER_TTL_SECONDS = 300  # 5 minutes — auto-expire stale entries (S2)

class ResultRegister:
    """Transient coordinate stack for command outputs.

    Persists to {workspace}/.codex_result_register.json for cross-process access.
    """

    def __init__(self, workspace: Path, max_history: int = 5):
        self.workspace = workspace
        self._stack: deque[CodexResult] = deque(maxlen=max_history)
        self._state_file = workspace / '.codex_result_register.json'
        self._load()

    def push(self, result: CodexResult) -> str:
        """Push result, return its transient coordinate."""
        result.timestamp = time.time()
        self._stack.appendleft(result)
        self._reassign_coords()
        self._persist()
        return '_'

    def resolve(self, coord: str) -> Optional[CodexResult]:
        """Resolve _ or _N. Returns None if expired or missing."""
        self._expire_stale()
        if coord == '_':
            return self._stack[0] if self._stack else None
        m = re.match(r'^_(\d+)$', coord)
        if m:
            idx = int(m.group(1))
            return self._stack[idx] if idx < len(self._stack) else None
        return None

    def resolve_field(self, coord: str) -> Optional[str]:
        """Resolve _.field or _N.field."""
        parts = coord.split('.', 1)
        result = self.resolve(parts[0])
        if result and len(parts) > 1:
            val = result.fields.get(parts[1])
            return str(val) if val is not None else None
        return None

    def show(self) -> str:
        """Render register state for context injection."""
        self._expire_stale()
        if not self._stack:
            return ''
        lines = []
        for r in self._stack:
            age = int(time.time() - r.timestamp) if r.timestamp else 0
            fields_str = ', '.join(f'{k}={v}' for k, v in list(r.fields.items())[:5])
            lines.append(f'{r.coord}  [{r.content_type}]  src={r.source}  age={age}s  {fields_str}')
        return '\n'.join(lines)

    def clear(self):
        """Clear all register entries (S1: --register-clear)."""
        self._stack.clear()
        self._persist()

    def _reassign_coords(self):
        for i, r in enumerate(self._stack):
            r.coord = '_' if i == 0 else f'_{i}'

    def _expire_stale(self):
        now = time.time()
        while self._stack and (now - self._stack[-1].timestamp > REGISTER_TTL_SECONDS):
            self._stack.pop()
        self._reassign_coords()

    def _persist(self):
        try:
            data = [r.to_dict() for r in self._stack]
            self._state_file.write_text(json.dumps(data, default=str), encoding='utf-8')
        except Exception:
            pass  # non-critical — register is transient

    def _load(self):
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text(encoding='utf-8'))
                for d in data:
                    self._stack.append(CodexResult.from_dict(d))
                self._expire_stale()
        except Exception:
            pass  # corrupted or missing — start fresh


# ── Output Recognition ──────────────────────────────────────────────────────

def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return (stripped.startswith('{') and stripped.endswith('}')) or \
           (stripped.startswith('[') and stripped.endswith(']'))


def _looks_like_table(text: str) -> bool:
    """Detect aligned columns (2+ spaces between fields) or TSV."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return False
    # Check if most lines have consistent column-like spacing
    multi_space = sum(1 for l in lines if re.search(r'  \S', l))
    return multi_space > len(lines) * 0.5


def _looks_like_kv(text: str) -> bool:
    """Detect key: value or key=value patterns."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return False
    kv_count = sum(1 for l in lines if re.match(r'^\s*\S+\s*[:=]\s*\S', l))
    return kv_count > len(lines) * 0.5


# ── Known Script Parsers ────────────────────────────────────────────────────

_KNOWN_SCRIPTS = [
    (re.compile(r'codex_engine\.py\s+--supermap'), '_parse_supermap'),
    (re.compile(r'pipeline_update\.py\s+(\S+)\s+show'), '_parse_pipeline_show'),
    (re.compile(r'pipeline_orchestrate\.py'), '_parse_orchestrate'),
    (re.compile(r'log_memory\.py'), '_parse_log_memory'),
    (re.compile(r'codex_engine\.py\s+([a-z]\S*)'), '_parse_coord_nav'),
]


def _parse_supermap(command: str, stdout: str) -> CodexResult:
    """Parse supermap output into addressable fields."""
    fields: Dict[str, Any] = {}
    # Extract namespace counts: ╶─ p   pipelines (3)
    for m in re.finditer(r'╶─\s+(\w+)\s+\S+\s+\((\d+)\)', stdout):
        fields[f'{m.group(1)}_count'] = int(m.group(2))
    # Extract individual entries: │  ╶─ p1    slug  summary
    for m in re.finditer(r'╶─\s+([a-z]+\d+)\s+(\S+)', stdout):
        fields[m.group(1)] = m.group(2)
    return CodexResult(
        source='e0 --supermap', content_type='codex',
        fields=fields, raw=stdout, rendered=stdout[:500],
    )


def _parse_pipeline_show(command: str, stdout: str) -> CodexResult:
    fields: Dict[str, Any] = {}
    # Status line
    sm = re.search(r'Status:\s*(\S+)', stdout)
    if sm:
        fields['status'] = sm.group(1)
    # Pending action
    pm = re.search(r'pending_action\s*→\s*(\S+)', stdout)
    if pm:
        fields['pending'] = pm.group(1)
    return CodexResult(
        source=command, content_type='codex',
        fields=fields, raw=stdout, rendered=stdout[:500],
    )


def _parse_orchestrate(command: str, stdout: str) -> CodexResult:
    fields: Dict[str, Any] = {}
    rm = re.search(r'Completed:\s*(\S+)', stdout)
    if rm:
        fields['result'] = rm.group(1)
    nm = re.search(r'Next:\s*(\S+)', stdout)
    if nm:
        fields['next_agent'] = nm.group(1)
    return CodexResult(
        source=command, content_type='codex',
        fields=fields, raw=stdout, rendered=stdout[:500],
    )


def _parse_log_memory(command: str, stdout: str) -> CodexResult:
    fields: Dict[str, Any] = {}
    em = re.search(r'Entry:\s*(\S+)', stdout)
    if em:
        fields['entry'] = em.group(1)
    dm = re.search(r'Daily:\s*(\S+)', stdout)
    if dm:
        fields['daily'] = dm.group(1)
    return CodexResult(
        source=command, content_type='codex',
        fields=fields, raw=stdout, rendered=stdout[:300],
    )


def _parse_coord_nav(command: str, stdout: str) -> CodexResult:
    """Parse coordinate navigation output."""
    fields: Dict[str, Any] = {}
    # Extract frontmatter key-value pairs
    for m in re.finditer(r'^(\w+):\s+(.+)$', stdout, re.MULTILINE):
        fields[m.group(1)] = m.group(2).strip()
    return CodexResult(
        source=command, content_type='codex',
        fields=fields, raw=stdout, rendered=stdout[:500],
    )


_PARSER_MAP = {
    '_parse_supermap': _parse_supermap,
    '_parse_pipeline_show': _parse_pipeline_show,
    '_parse_orchestrate': _parse_orchestrate,
    '_parse_log_memory': _parse_log_memory,
    '_parse_coord_nav': _parse_coord_nav,
}


def _is_known_script(command: str):
    """Check if command matches a known script pattern. Returns parser name or None."""
    for pattern, parser_name in _KNOWN_SCRIPTS:
        if pattern.search(command):
            return parser_name
    return None


# ── JSON/Table/KV parsers ──────────────────────────────────────────────────

def _parse_json_output(stdout: str) -> CodexResult:
    try:
        data = json.loads(stdout.strip())
        fields = data if isinstance(data, dict) else {'items': data}
        rendered = json.dumps(data, indent=2)[:500]
    except json.JSONDecodeError:
        fields = {}
        rendered = stdout[:500]
    return CodexResult(
        source='json', content_type='json',
        fields=fields, raw=stdout, rendered=rendered,
    )


def _parse_table_output(stdout: str) -> CodexResult:
    lines = [l for l in stdout.strip().splitlines() if l.strip()]
    fields: Dict[str, Any] = {'row_count': len(lines)}
    if lines:
        fields['header'] = lines[0].strip()
    return CodexResult(
        source='table', content_type='table',
        fields=fields, raw=stdout, rendered=stdout[:500],
    )


def _parse_kv_output(stdout: str) -> CodexResult:
    fields: Dict[str, Any] = {}
    for line in stdout.strip().splitlines():
        line = line.strip()
        for sep in [':', '=']:
            if sep in line:
                k, _, v = line.partition(sep)
                k = k.strip().lower().replace(' ', '_')
                if k:
                    fields[k] = v.strip()
                break
    return CodexResult(
        source='kv', content_type='kv',
        fields=fields, raw=stdout, rendered=stdout[:500],
    )


# ── Main entry point ───────────────────────────────────────────────────────

def output_to_codex(command: str, stdout: str, stderr: str = '', rc: int = 0) -> CodexResult:
    """Recognize output patterns and produce coordinate-addressed result."""
    # 1. Known script parsers (highest priority)
    parser_name = _is_known_script(command)
    if parser_name and parser_name in _PARSER_MAP:
        result = _PARSER_MAP[parser_name](command, stdout)
        result.source = command
        return result

    # 2. JSON detection
    if _looks_like_json(stdout):
        result = _parse_json_output(stdout)
        result.source = command
        return result

    # 3. Tabular detection
    if _looks_like_table(stdout):
        result = _parse_table_output(stdout)
        result.source = command
        return result

    # 4. Key-value detection
    if _looks_like_kv(stdout):
        result = _parse_kv_output(stdout)
        result.source = command
        return result

    # 5. Passthrough with coord wrapper
    return CodexResult(
        source=command, content_type='text',
        fields={}, raw=stdout, rendered=stdout[:500],
    )


# ── CLI test entry point ───────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    # Quick test: pipe stdout through the codec
    test_input = sys.stdin.read() if not sys.stdin.isatty() else '{"test": "value"}'
    result = output_to_codex('test', test_input)
    print(f'content_type: {result.content_type}')
    print(f'fields: {result.fields}')
    print(f'rendered: {result.rendered[:200]}')
