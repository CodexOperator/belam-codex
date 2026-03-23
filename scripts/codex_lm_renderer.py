"""Codex LM (Legendary Map) Renderer — auto-generates action grammar namespace.

Scans modes/, commands/, plus hardcoded render verbs and tool patterns to produce
a navigable `lm` namespace rendered first in the supermap. No caching — scans fresh
on every render call (<100ms at current workspace size).

Pipeline: codex-engine-v3-legendary-map
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Tuple


@dataclass
class LMEntry:
    """Single legendary map entry."""
    coord: str           # e.g. "lm1" — assigned during build
    verb: str            # e.g. "navigate", "edit-field"
    syntax: str          # e.g. "{coord}" or "e1{coord} {f} {v}"
    description: str     # brief, ≤40 chars
    source: str          # 'mode' | 'command' | 'render_verb' | 'tool'


@dataclass
class LMWorkflow:
    """Complex workflow with numbered sub-steps for dot-syntax sub-indices."""
    parent_coord: str    # e.g. "e0"
    slug: str            # e.g. "full-launch"
    steps: List[str] = field(default_factory=list)


# ── Render verbs (static) ─────────────────────────────────────────────────────

LM_RENDER_VERBS: List[LMEntry] = [
    LMEntry('', 'diff',         '.d',                      'show diff since anchor',      'render_verb'),
    LMEntry('', 'anchor',       '.a',                      'reset diff anchor',           'render_verb'),
    LMEntry('', 'view',         '.v1–.v5',                 'switch view preset',          'render_verb'),
    LMEntry('', 'sort-mode',    'x (cycle)',               'cycle sort mode',             'render_verb'),
    LMEntry('', 'filter-tag',   '--tag {t}',               'filter by tag',               'render_verb'),
    LMEntry('', 'filter-since', '--since {d}',             'filter by date',              'render_verb'),
]


# ── Tool patterns (static, session-universal only) ────────────────────────────

LM_TOOL_PATTERNS: List[LMEntry] = [
    LMEntry('', 'mem-search',   'memory_search("{q}")',    'search memory',               'tool'),
    LMEntry('', 'spawn-agent',  'sessions_spawn(...)',     'spawn sub-agent',             'tool'),
    LMEntry('', 'shell',        'exec {cmd}',             'run command',                 'tool'),
]


# ── Frontmatter parser (lightweight, avoids circular import) ──────────────────

def _parse_fm(text: str) -> Dict[str, object]:
    """Quick frontmatter parse — returns dict. Handles YAML or fallback."""
    if not text.startswith('---'):
        return {}
    end = text.find('\n---', 3)
    if end < 0:
        return {}
    fm_text = text[3:end].strip()

    try:
        import yaml
        raw = yaml.safe_load(fm_text)
        if isinstance(raw, dict):
            return raw
    except Exception:
        pass

    # Fallback: simple key: value parser
    result: Dict[str, object] = {}
    for line in fm_text.split('\n'):
        line = line.strip()
        if ':' not in line or line.startswith('#'):
            continue
        k, _, v = line.partition(':')
        k = k.strip()
        v = v.strip().strip('"\'')
        # Inline list
        if v.startswith('[') and v.endswith(']'):
            result[k] = [x.strip().strip('"\'') for x in v[1:-1].split(',') if x.strip()]
        elif v.lower() == 'true':
            result[k] = True
        elif v.lower() == 'false':
            result[k] = False
        else:
            result[k] = v
    return result


def _extract_usage_line(text: str) -> Optional[str]:
    """Extract first non-blank line after '## Usage' or '### Usage' heading."""
    lines = text.split('\n')
    in_usage = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^#{2,3}\s+Usage', stripped, re.IGNORECASE):
            in_usage = True
            continue
        if in_usage:
            # Skip blank lines and code fences
            if not stripped or stripped == '```' or stripped == '```bash':
                continue
            # Stop at next heading
            if stripped.startswith('#'):
                break
            return stripped
    return None


# ── Scanners ──────────────────────────────────────────────────────────────────

def scan_modes(workspace: Path) -> List[LMEntry]:
    """Scan modes/*.md for action entries."""
    modes_dir = workspace / 'modes'
    entries: List[LMEntry] = []
    if not modes_dir.exists():
        return entries

    for fp in sorted(modes_dir.glob('*.md')):
        try:
            text = fp.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        fm = _parse_fm(text)
        status = str(fm.get('status', ''))
        if status in ('archived', 'superseded'):
            continue

        coord_prefix = str(fm.get('coordinate', ''))
        func = str(fm.get('function', fp.stem))
        desc = str(fm.get('description', ''))[:40]

        # Build syntax from coordinate + first usage line
        usage = _extract_usage_line(text)
        if usage:
            # Clean: take the first variant (before —)
            syntax = usage.split('—')[0].strip()
            # Truncate to 25 chars
            if len(syntax) > 25:
                syntax = syntax[:22] + '...'
        else:
            syntax = coord_prefix or func

        entries.append(LMEntry(
            coord='',  # assigned later
            verb=func,
            syntax=syntax,
            description=desc,
            source='mode',
        ))

    return entries


def scan_commands(workspace: Path) -> List[LMEntry]:
    """Scan commands/*.md for CLI workflow entries. Only those with lm_include: true."""
    cmds_dir = workspace / 'commands'
    entries: List[LMEntry] = []
    if not cmds_dir.exists():
        return entries

    for fp in sorted(cmds_dir.glob('*.md')):
        try:
            text = fp.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        fm = _parse_fm(text)
        status = str(fm.get('status', ''))
        if status in ('archived', 'superseded'):
            continue
        # Only include commands with lm_include: true (LOW-2 resolution)
        if not fm.get('lm_include'):
            continue

        cmd = str(fm.get('command', f'belam {fp.stem}'))
        desc = str(fm.get('description', ''))[:40]
        syntax = cmd
        if len(syntax) > 25:
            syntax = syntax[:22] + '...'

        entries.append(LMEntry(
            coord='',
            verb=fp.stem,
            syntax=syntax,
            description=desc,
            source='command',
        ))

    return entries


def scan_workflows(workspace: Path) -> List[Tuple[str, LMWorkflow]]:
    """Scan modes/*.md for ## Workflows sections — returns (parent_coord, LMWorkflow) pairs."""
    modes_dir = workspace / 'modes'
    workflows: List[Tuple[str, LMWorkflow]] = []
    if not modes_dir.exists():
        return workflows

    for fp in sorted(modes_dir.glob('*.md')):
        try:
            text = fp.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        fm = _parse_fm(text)
        parent_coord = str(fm.get('coordinate', ''))
        if not parent_coord:
            continue

        # Parse ## Workflows section
        lines = text.split('\n')
        in_workflows = False
        current_wf: Optional[LMWorkflow] = None

        for line in lines:
            stripped = line.strip()
            # Enter workflows section
            if re.match(r'^#{2}\s+Workflows', stripped, re.IGNORECASE):
                in_workflows = True
                continue
            # Exit on next ## heading that isn't a workflow sub-heading
            if in_workflows and re.match(r'^#{2}\s+', stripped) and not re.match(r'^#{3}\s+', stripped):
                break

            if not in_workflows:
                continue

            # ### .l{N} — title
            wf_match = re.match(r'^#{3}\s+\.l(\d+)\s*[—–-]\s*(.+)', stripped)
            if wf_match:
                if current_wf is not None:
                    workflows.append((parent_coord, current_wf))
                slug = wf_match.group(2).strip().lower().replace(' ', '-')
                current_wf = LMWorkflow(parent_coord=parent_coord, slug=slug)
                continue

            # Numbered step within a workflow
            if current_wf is not None and re.match(r'^\d+\.', stripped):
                current_wf.steps.append(stripped)

        if current_wf is not None:
            workflows.append((parent_coord, current_wf))

    return workflows


# ── Tree builder ──────────────────────────────────────────────────────────────

def build_lm_tree(workspace: Path) -> List[LMEntry]:
    """Build the full LM entry list with assigned coordinates.

    Source priority: modes → render_verbs → commands → tools.
    Entries are numbered lm1, lm2, ... sequentially.
    """
    all_entries: List[LMEntry] = []

    # 1. Modes
    all_entries.extend(scan_modes(workspace))

    # 2. Render verbs
    all_entries.extend(LMEntry(
        coord='', verb=e.verb, syntax=e.syntax,
        description=e.description, source=e.source
    ) for e in LM_RENDER_VERBS)

    # 3. Commands (lm_include opt-in)
    all_entries.extend(scan_commands(workspace))

    # 4. Tool patterns
    all_entries.extend(LMEntry(
        coord='', verb=e.verb, syntax=e.syntax,
        description=e.description, source=e.source
    ) for e in LM_TOOL_PATTERNS)

    # Assign sequential lm{N} coordinates
    for i, entry in enumerate(all_entries, 1):
        entry.coord = f'lm{i}'

    return all_entries


# ── Renderers ─────────────────────────────────────────────────────────────────

def render_lm_section(workspace: Path) -> List[str]:
    """Render the LM section for supermap output.

    Returns list of formatted lines. Budget target: ≤1KB total.
    """
    entries = build_lm_tree(workspace)
    if not entries:
        return []

    lines: List[str] = []
    lines.append(f'╶─ lm  legendary map ({len(entries)} actions)')

    for entry in entries:
        # Format: │  ╶─ {coord:<5} {verb:<14} {syntax:<25} → {description}
        line = f'│  ╶─ {entry.coord:<5} {entry.verb:<14} {entry.syntax:<25} → {entry.description}'
        lines.append(line)

    # Append workflow sub-indices (collapsed)
    workflows = scan_workflows(workspace)
    for parent_coord, wf in workflows:
        step_count = len(wf.steps)
        sub_idx = f'{parent_coord}.l{workflows.index((parent_coord, wf)) + 1}'
        lines.append(f'│  │  ╶─ {sub_idx:<8} {wf.slug:<16} ({step_count} steps)')

    # Budget check — trim tool entries if over 1024 bytes
    total = sum(len(l.encode('utf-8')) + 1 for l in lines)  # +1 for newline
    if total > 1024:
        # Drop tool entries from the end
        while total > 1024 and lines:
            removed = lines.pop()
            total -= len(removed.encode('utf-8')) + 1
        lines.append(f'│  ... (trimmed to 1KB budget)')

    return lines


def render_lm_expanded(workspace: Path) -> str:
    """Render full LM with expanded descriptions (for `lm` bare navigation)."""
    entries = build_lm_tree(workspace)
    if not entries:
        return 'Legendary Map — No actions found.'

    lines = ['╶─ Legendary Map — Full Action Grammar', '']

    # Group by source
    groups = OrderedDict()
    for entry in entries:
        label = {
            'mode': 'Modes (e0–e3)',
            'render_verb': 'Render Verbs',
            'command': 'Commands (belam CLI)',
            'tool': 'Tool Patterns',
        }.get(entry.source, 'Other')
        groups.setdefault(label, []).append(entry)

    for group_name, group_entries in groups.items():
        lines.append(f'## {group_name}')
        for entry in group_entries:
            lines.append(f'{entry.coord}  {entry.verb:<14} {entry.syntax}')
            lines.append(f'     {entry.description}')
            lines.append('')

    return '\n'.join(lines)


def render_lm_entry(workspace: Path, index: int) -> Optional[str]:
    """Render a single LM entry expanded (for `lm{N}` navigation)."""
    entries = build_lm_tree(workspace)
    if 1 <= index <= len(entries):
        entry = entries[index - 1]
        return (
            f'{entry.coord}  {entry.verb}\n'
            f'  Syntax:  {entry.syntax}\n'
            f'  Source:  {entry.source}\n'
            f'  {entry.description}'
        )
    return None


def resolve_workflow(parent_coord: str, sub_suffix: str, workspace: Path) -> Optional[str]:
    """Resolve a dot-syntax workflow sub-index like e0.l1.

    Returns the expanded workflow steps as a formatted string, or None.
    """
    m = re.match(r'^l(\d+)$', sub_suffix)
    if not m:
        return None
    target_idx = int(m.group(1))

    workflows = scan_workflows(workspace)
    count = 0
    for p_coord, wf in workflows:
        if p_coord == parent_coord:
            count += 1
            if count == target_idx:
                lines = [f'{parent_coord}.l{target_idx} — {wf.slug}', '']
                for step in wf.steps:
                    lines.append(f'  {step}')
                return '\n'.join(lines)

    return None


# ── CLI entry point (for testing) ─────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    workspace = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    lines = render_lm_section(workspace)
    print('\n'.join(lines))
    total_bytes = sum(len(l.encode('utf-8')) + 1 for l in lines)
    print(f'\n--- Budget: {total_bytes} bytes ({total_bytes / 1024:.1f} KB) ---')
