#!/usr/bin/env python3
"""
codex_panes.py — Multi-pane tmux rendering for the Codex Engine (V3).

Launches a tmux session with 3 panes showing codex state in different formats:
  - Dense: compact codex tree (existing engine output)
  - JSON: MCP-compatible structured representation
  - Pretty: human-readable expanded markdown

Usage:
  python3 codex_panes.py --start [coord]       # launch tmux 3-pane session
  python3 codex_panes.py --stop                 # kill tmux session
  python3 codex_panes.py --render dense [coord] # single-format render
  python3 codex_panes.py --render json [coord]
  python3 codex_panes.py --render pretty [coord]
"""

import json
import re
import subprocess
import sys
from pathlib import Path

# ── Lazy imports from codex_engine ──────────────────────────────────────────────

_engine = None


def _get_engine():
    """Lazy import codex_engine."""
    global _engine
    if _engine is None:
        sys.path.insert(0, str(Path(__file__).parent))
        import codex_engine
        _engine = codex_engine
    return _engine


# ── Status emoji helper ────────────────────────────────────────────────────────

_STATUS_EMOJI = {
    'complete': '✅', 'active': '🔵', 'open': '⚪',
    'blocked': '🔴', 'accepted': '✅', 'proposed': '💡',
    'superseded': '🔁', 'archived': '📦', 'draft': '📝',
    'phase1_build': '🔨', 'phase1_complete': '✅',
    'phase2_build': '🔨', 'phase2_complete': '✅',
}


def _status_emoji(status):
    """Return emoji for a status string."""
    s = str(status).lower()
    if s in _STATUS_EMOJI:
        return _STATUS_EMOJI[s]
    if 'complete' in s:
        return '✅'
    if 'build' in s or 'progress' in s:
        return '🔨'
    return '⚪'


# ── Render functions ────────────────────────────────────────────────────────────

def render_dense(coord=None):
    """Render in dense codex format (existing engine output)."""
    engine = _get_engine()
    if coord:
        return engine.render_zoom([coord])
    return engine.render_supermap()


def render_json(coord=None):
    """Render as JSON (MCP-compatible representation)."""
    engine = _get_engine()

    if coord:
        resolved, _ = engine.resolve_coords([coord])
        results = []
        for r in resolved:
            prim = engine.load_primitive(r['filepath'], r['type'])
            if prim:
                entry = {
                    'uri': f"codex://workspace/{r['prefix']}{r['index']}",
                    'coord': f"{r['prefix']}{r['index']}",
                    'slug': r['slug'],
                }
                for idx, field_data in prim['fields'].items():
                    entry[field_data['key']] = field_data['value']
                if prim.get('body'):
                    entry['body'] = '\n'.join(prim['body'])
                results.append(entry)
        return json.dumps({'resources': results}, indent=2, default=str)
    else:
        return _supermap_to_json()


def render_pretty(coord=None):
    """Render in human-pretty markdown format."""
    engine = _get_engine()

    if coord:
        resolved, _ = engine.resolve_coords([coord])
        sections = []
        for r in resolved:
            prim = engine.load_primitive(r['filepath'], r['type'])
            if prim:
                sections.append(_format_pretty_primitive(r, prim))
        return '\n\n'.join(sections)
    return _supermap_to_pretty()


def _supermap_to_json():
    """Convert full supermap to JSON structure."""
    engine = _get_engine()
    result = {'namespaces': {}}

    for prefix in engine.SHOW_ORDER:
        if prefix not in engine.NAMESPACE:
            continue
        type_label = engine.NAMESPACE[prefix][0]
        try:
            prims = engine.get_primitives(prefix, active_only=True)
        except Exception:
            continue

        entries = []
        for i, (slug, fp) in enumerate(prims, 1):
            coord = f"{prefix}{i}"
            entry = {
                'uri': f"codex://workspace/{coord}",
                'coord': coord,
                'slug': slug,
            }
            try:
                prim = engine.load_primitive(fp, type_label)
                if prim:
                    for idx, field_data in prim['fields'].items():
                        entry[field_data['key']] = field_data['value']
            except Exception:
                pass
            entries.append(entry)

        result['namespaces'][prefix] = {
            'type': type_label,
            'count': len(entries),
            'resources': entries[:20],  # cap at 20 for readability
        }

    return json.dumps(result, indent=2, default=str)


def _supermap_to_pretty():
    """Convert full supermap to human-pretty markdown."""
    engine = _get_engine()
    lines = ['# Codex Workspace Overview', '']

    for prefix in engine.SHOW_ORDER:
        if prefix not in engine.NAMESPACE:
            continue
        type_label = engine.NAMESPACE[prefix][0]
        try:
            prims = engine.get_primitives(prefix, active_only=True)
        except Exception:
            continue

        count = len(prims)
        if count == 0:
            continue

        lines.append(f'## {type_label.title()} ({count})')
        lines.append('')

        for i, (slug, fp) in enumerate(prims[:10], 1):
            coord = f"{prefix}{i}"
            try:
                prim = engine.load_primitive(fp, type_label)
                if prim:
                    lines.append(_format_pretty_primitive(
                        {'prefix': prefix, 'index': i, 'slug': slug, 'filepath': fp, 'type': type_label},
                        prim
                    ))
                    lines.append('')
                else:
                    lines.append(f'### {coord} — {slug}')
                    lines.append('')
            except Exception:
                lines.append(f'### {coord} — {slug}')
                lines.append('')

        if count > 10:
            lines.append(f'*... and {count - 10} more*')
            lines.append('')

    return '\n'.join(lines)


def _format_pretty_primitive(resolved, prim):
    """Format a single primitive in human-readable markdown."""
    coord = f"{resolved['prefix']}{resolved['index']}"
    slug = resolved['slug']

    lines = [f"### {coord} — {slug}"]

    # Extract key fields
    status = None
    priority = None
    for idx, fi in prim['fields'].items():
        key = fi['key']
        val = fi['value']
        if key == 'status':
            status = str(val)
        elif key == 'priority':
            priority = str(val)

    # Status line with emoji
    if status:
        emoji = _status_emoji(status)
        status_line = f"- **Status:** {emoji} {status.replace('_', ' ').title()}"
        if priority:
            status_line += f"  |  **Priority:** {priority.title()}"
        lines.append(status_line)
    elif priority:
        lines.append(f"- **Priority:** {priority.title()}")

    # Other fields (skip primitive, status, priority — already shown)
    skip_keys = {'primitive', 'status', 'priority', 'coordinate'}
    for idx in sorted(prim['fields'].keys()):
        fi = prim['fields'][idx]
        key = fi['key']
        val = fi['value']
        if key in skip_keys:
            continue
        if isinstance(val, list):
            val_str = ', '.join(str(v) for v in val)
        else:
            val_str = str(val)
        if val_str and val_str not in ('None', 'null', '[]', ''):
            # Truncate long values
            if len(val_str) > 100:
                val_str = val_str[:97] + '...'
            lines.append(f"- **{key.replace('_', ' ').title()}:** {val_str}")

    return '\n'.join(lines)


# ── tmux session management ────────────────────────────────────────────────────

TMUX_SESSION = 'codex-panes'


def start_panes(coord=None):
    """Launch tmux multi-pane session with 3 panes (dense/json/pretty)."""
    script = str(Path(__file__).resolve())
    coord_arg = f' {coord}' if coord else ''

    # Kill existing session if any
    subprocess.run(['tmux', 'kill-session', '-t', TMUX_SESSION],
                   capture_output=True)

    # Create new session with dense pane
    subprocess.run([
        'tmux', 'new-session', '-d', '-s', TMUX_SESSION,
        f'watch -n2 python3 {script} --render dense{coord_arg}'
    ])

    # Split for JSON pane
    subprocess.run([
        'tmux', 'split-window', '-h', '-t', TMUX_SESSION,
        f'watch -n2 python3 {script} --render json{coord_arg}'
    ])

    # Split for Pretty pane
    subprocess.run([
        'tmux', 'split-window', '-h', '-t', TMUX_SESSION,
        f'watch -n2 python3 {script} --render pretty{coord_arg}'
    ])

    # Even out the layout
    subprocess.run(['tmux', 'select-layout', '-t', TMUX_SESSION, 'even-horizontal'])

    print(f"Multi-pane started. Attach: tmux attach -t {TMUX_SESSION}")


def stop_panes():
    """Kill the multi-pane tmux session."""
    result = subprocess.run(['tmux', 'kill-session', '-t', TMUX_SESSION],
                            capture_output=True)
    if result.returncode == 0:
        print(f"Stopped tmux session '{TMUX_SESSION}'")
    else:
        print(f"No active session '{TMUX_SESSION}' found")


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Multi-pane codex rendering')
    parser.add_argument('--start', nargs='?', const='', default=None,
                        metavar='COORD', help='Start tmux multi-pane session')
    parser.add_argument('--stop', action='store_true', help='Stop tmux session')
    parser.add_argument('--render', type=str, choices=['dense', 'json', 'pretty'],
                        help='Render in specified format')
    parser.add_argument('coord', nargs='?', default=None,
                        help='Optional coordinate to focus on')

    args = parser.parse_args()

    if args.stop:
        stop_panes()
        return

    if args.start is not None:
        coord = args.start if args.start else args.coord
        start_panes(coord or None)
        return

    if args.render:
        coord = args.coord
        if args.render == 'dense':
            print(render_dense(coord))
        elif args.render == 'json':
            print(render_json(coord))
        elif args.render == 'pretty':
            print(render_pretty(coord))
        return

    parser.print_help()


if __name__ == '__main__':
    main()
