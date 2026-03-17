#!/usr/bin/env python3
"""
Pipeline Dashboard — Live CLI monitor for SNN research pipelines.

Usage:
    python3 scripts/pipeline_dashboard.py              # One-shot overview
    python3 scripts/pipeline_dashboard.py --watch       # Auto-refresh every 10s
    python3 scripts/pipeline_dashboard.py --watch 5     # Auto-refresh every 5s
    python3 scripts/pipeline_dashboard.py v4-deep-analysis  # Detail view for one pipeline
    python3 scripts/pipeline_dashboard.py --stages      # Show all stage history
    python3 scripts/pipeline_dashboard.py --json        # Machine-readable output
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
PIPELINES_DIR = WORKSPACE / 'pipelines'
BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'

# ── ANSI helpers ──────────────────────────────────────────────────────────────

BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'

STATUS_STYLE = {
    'phase1_design':       (CYAN,    '📐', 'Phase 1 — Design'),
    'phase1_review':       (CYAN,    '🔍', 'Phase 1 — Review'),
    'phase1_build':        (CYAN,    '🔨', 'Phase 1 — Build'),
    'phase1_code_review':  (CYAN,    '🔬', 'Phase 1 — Code Review'),
    'phase1_complete':     (GREEN,   '✅', 'Phase 1 — Complete'),
    'phase2_waiting':      (YELLOW,  '⏳', 'Phase 2 — Waiting for Input'),
    'phase2_design':       (MAGENTA, '📐', 'Phase 2 — Design'),
    'phase2_build':        (MAGENTA, '🔨', 'Phase 2 — Build'),
    'phase2_complete':     (GREEN,   '✅', 'Phase 2 — Complete'),
    'phase3_active':       (BLUE,    '🔬', 'Phase 3 — Active'),
    'phase3_complete':     (GREEN,   '✅', 'Phase 3 — Complete'),
    'archived':            (DIM,     '📦', 'Archived'),
}

PRIORITY_STYLE = {
    'critical': (RED + BOLD, '🔴'),
    'high':     (YELLOW,     '🟡'),
    'medium':   (BLUE,       '🔵'),
    'low':      (DIM,        '⚪'),
}


def extract_field(content, field):
    match = re.search(rf'^{field}:\s*(.+)$', content, re.MULTILINE)
    return match.group(1).strip() if match else None


def extract_list_field(content, field):
    match = re.search(rf'^{field}:\s*\[(.+?)\]', content, re.MULTILINE)
    if match:
        return [t.strip() for t in match.group(1).split(',')]
    return []


def parse_stage_history(content):
    """Extract stage history rows from the markdown table."""
    stages = []
    in_table = False
    for line in content.splitlines():
        if '| Stage ' in line or '| stage ' in line:
            in_table = True
            continue
        if in_table and line.strip().startswith('|---'):
            continue
        if in_table and line.strip().startswith('|'):
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) >= 4:
                stages.append({
                    'stage': parts[0],
                    'date': parts[1],
                    'agent': parts[2],
                    'notes': parts[3] if len(parts) > 3 else '',
                })
        elif in_table and not line.strip().startswith('|'):
            in_table = False
    return stages


def load_pipeline(path):
    """Load a pipeline file and extract all metadata."""
    content = path.read_text()
    version = path.stem
    status = extract_field(content, 'status') or 'unknown'
    priority = extract_field(content, 'priority') or 'medium'
    started = extract_field(content, 'started') or '—'
    tags = extract_list_field(content, 'tags')
    agents = extract_list_field(content, 'agents')
    desc_match = re.search(r'^## Description\n(.+?)(?=\n##|\Z)', content, re.MULTILINE | re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ''
    stages = parse_stage_history(content)

    # Count phase 3 iterations from iteration log table
    iter_rows = re.findall(r'\| \w+-\d+ \|', content)

    # Load state JSON if available
    state_file = BUILDS_DIR / f'{version}_state.json'
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except json.JSONDecodeError:
            pass

    return {
        'version': version,
        'status': status,
        'priority': priority,
        'started': started,
        'tags': tags,
        'agents': agents,
        'description': description,
        'stages': stages,
        'iterations': len(iter_rows),
        'state': state,
        'path': str(path),
    }


def load_all_pipelines():
    if not PIPELINES_DIR.exists():
        return []
    pipelines = []
    for pf in sorted(PIPELINES_DIR.glob('*.md')):
        pipelines.append(load_pipeline(pf))
    return pipelines


# ── Renderers ─────────────────────────────────────────────────────────────────

def render_status(status):
    color, icon, label = STATUS_STYLE.get(status, (WHITE, '❓', status))
    return f"{icon} {color}{label}{RESET}"


def render_priority(priority):
    color, icon = PRIORITY_STYLE.get(priority, (DIM, '⚪'))
    return f"{icon} {color}{priority}{RESET}"


def render_overview(pipelines):
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = []
    lines.append(f"\n{BOLD}{'═' * 72}{RESET}")
    lines.append(f"{BOLD}  🔬 PIPELINE DASHBOARD{RESET}                          {DIM}{now}{RESET}")
    lines.append(f"{BOLD}{'═' * 72}{RESET}")

    if not pipelines:
        lines.append(f"\n  {DIM}No active pipelines.{RESET}\n")
        return '\n'.join(lines)

    # Sort: active first (non-archived), then by priority
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    active = [p for p in pipelines if p['status'] != 'archived']
    archived = [p for p in pipelines if p['status'] == 'archived']
    active.sort(key=lambda p: priority_order.get(p['priority'], 9))

    for p in active:
        lines.append('')
        lines.append(f"  {BOLD}{p['version'].upper()}{RESET}  {render_priority(p['priority'])}  {DIM}started {p['started']}{RESET}")
        lines.append(f"  {render_status(p['status'])}")
        if p['description']:
            desc_short = p['description'][:90] + ('…' if len(p['description']) > 90 else '')
            lines.append(f"  {DIM}{desc_short}{RESET}")

        # Latest stage
        if p['stages']:
            last = p['stages'][-1]
            notes_short = last['notes'][:70] + ('…' if len(last['notes']) > 70 else '')
            lines.append(f"  {DIM}Latest:{RESET} {last['stage']} {DIM}by{RESET} {last['agent']} {DIM}— {notes_short}{RESET}")

        # Phase 3 iterations
        if p['iterations']:
            lines.append(f"  {DIM}Phase 3 iterations:{RESET} {p['iterations']}")

        if p['tags']:
            lines.append(f"  {DIM}Tags: {', '.join(p['tags'])}{RESET}")

        lines.append(f"  {DIM}{'─' * 68}{RESET}")

    if archived:
        lines.append(f"\n  {DIM}📦 Archived: {', '.join(p['version'] for p in archived)}{RESET}")

    lines.append('')
    return '\n'.join(lines)


def render_detail(pipeline, show_stages=True):
    p = pipeline
    lines = []
    lines.append(f"\n{BOLD}{'═' * 72}{RESET}")
    lines.append(f"{BOLD}  🔬 {p['version'].upper()}{RESET}  {render_priority(p['priority'])}")
    lines.append(f"{BOLD}{'═' * 72}{RESET}")
    lines.append(f"\n  {render_status(p['status'])}")
    lines.append(f"  {DIM}Started:{RESET} {p['started']}")
    if p['description']:
        lines.append(f"\n  {p['description']}")
    if p['tags']:
        lines.append(f"\n  {DIM}Tags:{RESET} {', '.join(p['tags'])}")
    if p['agents']:
        lines.append(f"  {DIM}Agents:{RESET} {', '.join(p['agents'])}")

    if show_stages and p['stages']:
        lines.append(f"\n  {BOLD}Stage History{RESET}")
        lines.append(f"  {'─' * 68}")
        for s in p['stages']:
            # Color-code agent
            agent_colors = {'architect': CYAN, 'critic': YELLOW, 'builder': GREEN, 'belam-main': MAGENTA}
            ac = agent_colors.get(s['agent'], WHITE)
            notes_short = s['notes'][:60] + ('…' if len(s['notes']) > 60 else '')
            lines.append(f"  {DIM}{s['date']}{RESET}  {ac}{s['agent']:<12}{RESET}  {s['stage']}")
            if notes_short:
                lines.append(f"  {DIM}{'':>12}  {notes_short}{RESET}")

    # State JSON summary
    if p['state']:
        st = p['state']
        lines.append(f"\n  {BOLD}State JSON{RESET}")
        lines.append(f"  {'─' * 68}")
        if 'phase1' in st:
            lines.append(f"  Phase 1: {json.dumps(st['phase1'], default=str)}")
        if 'phase2' in st:
            lines.append(f"  Phase 2: {json.dumps(st['phase2'], default=str)}")
        if 'phase3' in st:
            lines.append(f"  Phase 3: gate={st['phase3'].get('gate', '?')}, iters={len(st['phase3'].get('iterations', []))}")

    lines.append(f"\n  {DIM}File: {p['path']}{RESET}")
    lines.append('')
    return '\n'.join(lines)


def render_json(pipelines):
    return json.dumps(pipelines, indent=2, default=str)


# ── Watch mode ────────────────────────────────────────────────────────────────

def clear_screen():
    sys.stdout.write('\033[2J\033[H')
    sys.stdout.flush()


def watch(interval, version=None):
    try:
        while True:
            clear_screen()
            if version:
                pipelines = load_all_pipelines()
                match = [p for p in pipelines if p['version'] == version]
                if match:
                    print(render_detail(match[0]))
                else:
                    print(f"  ❌ Pipeline '{version}' not found")
            else:
                pipelines = load_all_pipelines()
                print(render_overview(pipelines))
            print(f"  {DIM}Refreshing every {interval}s — Ctrl+C to exit{RESET}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n  {DIM}Dashboard stopped.{RESET}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pipeline Dashboard — Live CLI monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pipeline_dashboard.py                    Overview of all pipelines
  pipeline_dashboard.py v4-deep-analysis   Detail view for v4-deep-analysis
  pipeline_dashboard.py --watch            Auto-refresh every 10s
  pipeline_dashboard.py --watch 5          Auto-refresh every 5s
  pipeline_dashboard.py v4 --watch 3       Watch one pipeline, refresh 3s
  pipeline_dashboard.py --stages           Show full stage history
  pipeline_dashboard.py --json             JSON output (for scripting)
        """
    )
    parser.add_argument('version', nargs='?', help='Show detail for a specific pipeline')
    parser.add_argument('--watch', '-w', nargs='?', const=10, type=int, metavar='SEC',
                        help='Auto-refresh mode (default: 10s)')
    parser.add_argument('--stages', '-s', action='store_true', help='Show full stage history in overview')
    parser.add_argument('--json', '-j', action='store_true', help='JSON output')

    args = parser.parse_args()

    if args.watch is not None:
        watch(args.watch, args.version)
        return

    pipelines = load_all_pipelines()

    if args.json:
        print(render_json(pipelines))
        return

    if args.version:
        match = [p for p in pipelines if p['version'] == args.version]
        if match:
            print(render_detail(match[0], show_stages=True))
        else:
            print(f"  ❌ Pipeline '{args.version}' not found")
            print(f"  Available: {', '.join(p['version'] for p in pipelines)}")
    else:
        # Overview — optionally with stages
        if args.stages:
            for p in pipelines:
                print(render_detail(p, show_stages=True))
        else:
            print(render_overview(pipelines))


if __name__ == '__main__':
    main()
