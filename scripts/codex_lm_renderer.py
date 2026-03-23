#!/usr/bin/env python3
"""Codex Legendary Map (LM) Renderer.

Auto-generates the `lm` namespace from four sources:
  1. modes/*.md      — engine action modes (e0–e3)
  2. commands/*.md   — CLI commands (opt-in via lm_include: true)
  3. Render verbs    — hardcoded view/diff/sort verbs
  4. Tool patterns   — hardcoded session-universal tools

Renders as a dense tree section prepended to the supermap.
Budget: ≤1KB for ~16 entries.

Pipeline: codex-engine-v3-legendary-map
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Frontmatter parser (lightweight, avoids yaml dep) ───────────────────────

_FM_SEP = re.compile(r'^---\s*$', re.MULTILINE)


def _parse_frontmatter(text: str) -> Dict[str, str]:
    """Minimal YAML-like frontmatter parser. Returns flat key→value dict."""
    parts = _FM_SEP.split(text, maxsplit=2)
    if len(parts) < 3:
        return {}
    fm: Dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        line = line.strip()
        if ':' in line:
            k, _, v = line.partition(':')
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


# ── Data model ──────────────────────────────────────────────────────────────

@dataclass
class LMEntry:
    """Single legendary map entry."""
    coord: str = ''           # assigned during build_lm_tree
    verb: str = ''            # e.g. "navigate", "edit-field"
    syntax: str = ''          # e.g. "{coord}" or "e1{coord} {f} {v}"
    description: str = ''     # brief, ≤40 chars
    source: str = ''          # 'mode' | 'command' | 'render_verb' | 'tool'


@dataclass
class LMWorkflow:
    """Complex workflow with numbered steps, attached to a parent coordinate."""
    name: str = ''            # e.g. "full-launch"
    sub_coord: str = ''       # e.g. "l1"
    steps: List[str] = field(default_factory=list)


# ── Source scanners ─────────────────────────────────────────────────────────

# Hardcoded mode→entry mapping (stable, matches modes/*.md frontmatter)
_MODE_ENTRIES = [
    LMEntry(verb='navigate',    syntax='{coord}',               description='render primitive',       source='mode'),
    LMEntry(verb='edit-field',  syntax='e1{coord} {f} {v}',     description='set field',              source='mode'),
    LMEntry(verb='edit-body',   syntax='e1{coord} B+ {text}',   description='append to body',         source='mode'),
    LMEntry(verb='create',      syntax='e2 {ns} "title"',       description='new primitive',          source='mode'),
    LMEntry(verb='extend-ns',   syntax='e3 {ns}.{sub}',         description='register namespace',     source='mode'),
    LMEntry(verb='orchestrate', syntax='e0',                     description='pipeline sweep',         source='mode'),
]

# Render verbs — the view/diff/sort interaction layer
_RENDER_VERBS = [
    LMEntry(verb='diff',        syntax='.d',                     description='diff since anchor',      source='render_verb'),
    LMEntry(verb='anchor',      syntax='.a',                     description='reset diff anchor',      source='render_verb'),
    LMEntry(verb='filter-tag',  syntax='--tag {t}',              description='filter by tag',          source='render_verb'),
    LMEntry(verb='filter-since',syntax='--since {d}',            description='filter by date',         source='render_verb'),
    LMEntry(verb='persona-view',syntax='--as {role}',            description='persona filter',         source='render_verb'),
]

# Tool patterns — session-universal tools agents use constantly
_TOOL_PATTERNS = [
    LMEntry(verb='mem-search',  syntax='memory_search("{q}")',   description='search memory',          source='tool'),
    LMEntry(verb='spawn-agent', syntax='sessions_spawn(...)',     description='spawn sub-agent',        source='tool'),
    LMEntry(verb='shell',       syntax='exec {cmd}',             description='run command',            source='tool'),
]


def scan_modes(workspace: Path) -> List[LMEntry]:
    """Return mode-derived LM entries. Scans modes/*.md to verify active status."""
    modes_dir = workspace / 'modes'
    if not modes_dir.exists():
        return list(_MODE_ENTRIES)  # return defaults even without modes dir

    active_coords = set()
    for fp in modes_dir.glob('*.md'):
        fm = _parse_frontmatter(fp.read_text(encoding='utf-8', errors='replace'))
        if fm.get('status', 'active') not in ('archived', 'superseded'):
            coord = fm.get('coordinate', '')
            if coord:
                active_coords.add(coord)

    # Return all mode entries (they map to the engine grammar, not 1:1 to mode files)
    return list(_MODE_ENTRIES)


def scan_commands(workspace: Path) -> List[LMEntry]:
    """Return command-derived LM entries. Only commands with lm_include: true."""
    cmds_dir = workspace / 'commands'
    if not cmds_dir.exists():
        return []

    entries: List[LMEntry] = []
    for fp in sorted(cmds_dir.glob('*.md')):
        fm = _parse_frontmatter(fp.read_text(encoding='utf-8', errors='replace'))
        if fm.get('status') in ('archived', 'superseded'):
            continue
        if fm.get('lm_include', '').lower() != 'true':
            continue
        desc = fm.get('description', fp.stem)[:40]
        entries.append(LMEntry(
            verb=fp.stem,
            syntax=f'belam {fp.stem}',
            description=desc,
            source='command',
        ))
    return entries


def get_render_verbs() -> List[LMEntry]:
    """Return hardcoded render verb entries."""
    return list(_RENDER_VERBS)


def get_tool_patterns() -> List[LMEntry]:
    """Return hardcoded tool pattern entries."""
    return list(_TOOL_PATTERNS)


# ── Tree building ───────────────────────────────────────────────────────────

def build_lm_tree(workspace: Path) -> List[LMEntry]:
    """Build the full LM entry list with assigned coordinates.

    Order: modes → render_verbs → commands → tools.
    Coordinates: sequential lm1, lm2, ...
    """
    all_entries: List[LMEntry] = []
    all_entries.extend(scan_modes(workspace))
    all_entries.extend(get_render_verbs())
    all_entries.extend(scan_commands(workspace))
    all_entries.extend(get_tool_patterns())

    # Assign sequential coordinates
    for i, entry in enumerate(all_entries, 1):
        entry.coord = f'lm{i}'

    return all_entries


# ── Workflow scanning ───────────────────────────────────────────────────────

def scan_workflows(workspace: Path) -> Dict[str, List[LMWorkflow]]:
    """Scan modes/*.md for ## Workflows sections. Returns {parent_coord: [workflows]}."""
    modes_dir = workspace / 'modes'
    if not modes_dir.exists():
        return {}

    result: Dict[str, List[LMWorkflow]] = {}

    for fp in sorted(modes_dir.glob('*.md')):
        text = fp.read_text(encoding='utf-8', errors='replace')
        fm = _parse_frontmatter(text)
        if fm.get('status') in ('archived', 'superseded'):
            continue
        parent_coord = fm.get('coordinate', '')
        if not parent_coord:
            continue

        # Find ## Workflows section
        wf_match = re.search(r'^## Workflows\s*\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL)
        if not wf_match:
            continue

        wf_text = wf_match.group(1)
        workflows: List[LMWorkflow] = []

        # Parse ### .lN — name headings
        for sub_match in re.finditer(
            r'^### \.(l\d+)\s*[—–-]\s*(.+?)\s*\n(.*?)(?=^### |\Z)',
            wf_text, re.MULTILINE | re.DOTALL,
        ):
            sub_coord = sub_match.group(1)
            name = sub_match.group(2).strip()
            body = sub_match.group(3).strip()
            steps = [line.strip() for line in body.splitlines() if re.match(r'^\d+\.', line.strip())]
            workflows.append(LMWorkflow(name=name, sub_coord=sub_coord, steps=steps))

        if workflows:
            result[parent_coord] = workflows

    return result


# ── Rendering ───────────────────────────────────────────────────────────────

def render_lm_section(workspace: Path) -> List[str]:
    """Render the LM section as a list of formatted lines for supermap injection.

    No caching — scans fresh each call. <100ms for typical workspace.
    """
    entries = build_lm_tree(workspace)
    workflows = scan_workflows(workspace)

    lines: List[str] = []
    lines.append(f'╶─ lm  legendary map ({len(entries)} actions)')

    # Track which parent coords have had workflows rendered (avoid duplicates)
    rendered_wf_coords: set = set()

    for entry in entries:
        # Compact format: │  ╶─ {coord:<5} {verb:<12} {syntax}
        # Descriptions omitted in tree view — available via lm{N} zoom
        line = f'│  ╶─ {entry.coord:<5} {entry.verb:<12} {entry.syntax}'
        lines.append(line)

        # Show workflows only once per parent mode coordinate
        if entry.source == 'mode':
            syntax_prefix = entry.syntax.split('{')[0].split(' ')[0] if '{' in entry.syntax else entry.syntax
            if syntax_prefix in workflows and syntax_prefix not in rendered_wf_coords:
                rendered_wf_coords.add(syntax_prefix)
                for wf in workflows[syntax_prefix]:
                    step_count = len(wf.steps)
                    lines.append(f'│  │  ╶─ {syntax_prefix}.{wf.sub_coord}  {wf.name:<16} ({step_count} steps)')

    return lines


def render_lm_expanded(workspace: Path) -> str:
    """Render the full LM with expanded descriptions for bare `lm` navigation."""
    entries = build_lm_tree(workspace)
    workflows = scan_workflows(workspace)

    lines: List[str] = []
    lines.append('╶─ Legendary Map — Full Action Grammar\n')

    # Group by source
    groups = [
        ('Modes (e0–e3)', 'mode'),
        ('Render Verbs', 'render_verb'),
        ('Commands', 'command'),
        ('Tool Patterns', 'tool'),
    ]

    for group_name, source_key in groups:
        group_entries = [e for e in entries if e.source == source_key]
        if not group_entries:
            continue
        lines.append(f'## {group_name}')
        for entry in group_entries:
            lines.append(f'{entry.coord}  {entry.verb:<14} {entry.syntax}')
            lines.append(f'     {entry.description}')

            # Show workflows if this is a mode entry
            if entry.source == 'mode':
                syntax_prefix = entry.syntax.split('{')[0].split(' ')[0] if '{' in entry.syntax else entry.syntax
                if syntax_prefix in workflows:
                    for wf in workflows[syntax_prefix]:
                        lines.append(f'     .{wf.sub_coord} — {wf.name}')
                        for step in wf.steps:
                            lines.append(f'       {step}')
            lines.append('')

    return '\n'.join(lines)


def render_lm_entry(workspace: Path, index: int) -> Optional[str]:
    """Render a single LM entry expanded. Returns None if index out of range."""
    entries = build_lm_tree(workspace)
    if index < 1 or index > len(entries):
        return None
    entry = entries[index - 1]
    return f'{entry.coord}  {entry.verb}  {entry.syntax}\n  → {entry.description}'


# ── Workflow resolution ─────────────────────────────────────────────────────

def resolve_workflow(parent_coord: str, sub_coord: str, workspace: Path) -> Optional[str]:
    """Resolve a dot-syntax workflow sub-index like e0.l1.

    Returns formatted workflow text, or None if not found.
    """
    workflows = scan_workflows(workspace)
    parent_workflows = workflows.get(parent_coord, [])
    for wf in parent_workflows:
        if wf.sub_coord == sub_coord:
            lines = [f'{parent_coord}.{wf.sub_coord} — {wf.name}']
            for step in wf.steps:
                lines.append(f'  {step}')
            return '\n'.join(lines)
    return None


# ── CLI entry point (for testing) ───────────────────────────────────────────

if __name__ == '__main__':
    import sys
    workspace = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / '.openclaw' / 'workspace'
    section = render_lm_section(workspace)
    for line in section:
        print(line)
    print(f'\n--- Total bytes: {sum(len(l.encode()) for l in section)} ---')
