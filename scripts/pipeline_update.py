#!/usr/bin/env python3
"""
Pipeline Stage Updater

Single command for agents to update pipeline state. Updates BOTH the pipeline
markdown primitive and the state JSON atomically.

Usage:
    # Complete a stage:
    python3 scripts/pipeline_update.py v4 complete architect_design "Design v2 with all blocks resolved"
    
    # Start a stage:
    python3 scripts/pipeline_update.py v4 start builder_implementation
    
    # Set overall pipeline status:
    python3 scripts/pipeline_update.py v4 status phase1_build
    
    # Add a Phase 3 iteration result:
    python3 scripts/pipeline_update.py v4 iteration 01 complete "54.2% accuracy, +0.3 Sharpe"
    
    # View current state:
    python3 scripts/pipeline_update.py v4 show
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
PIPELINES_DIR = WORKSPACE / 'pipelines'
BUILDS_DIR = WORKSPACE / 'SNN_research' / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'


def load_state(version):
    """Load pipeline state JSON."""
    state_file = BUILDS_DIR / f'{version}_state.json'
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {'version': version, 'stages': {}}


def save_state(version, state):
    """Save pipeline state JSON."""
    BUILDS_DIR.mkdir(parents=True, exist_ok=True)
    state_file = BUILDS_DIR / f'{version}_state.json'
    state_file.write_text(json.dumps(state, indent=2))


def load_pipeline_md(version):
    """Load pipeline markdown."""
    pf = PIPELINES_DIR / f'{version}.md'
    if not pf.exists():
        print(f"❌ No pipeline found: pipelines/{version}.md")
        sys.exit(1)
    return pf, pf.read_text()


def get_agent_id():
    """Try to determine the calling agent."""
    return os.environ.get('AGENT_ID', os.environ.get('USER', 'unknown'))


def now_str():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')


def now_date():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def cmd_show(version):
    """Show current pipeline state."""
    pf, content = load_pipeline_md(version)
    state = load_state(version)
    
    # Extract status from frontmatter
    status_match = re.search(r'^status:\s*(.+)$', content, re.MULTILINE)
    status = status_match.group(1).strip() if status_match else 'unknown'
    
    print(f"📋 Pipeline {version}")
    print(f"   Status: {status}")
    print(f"   File: {pf}")
    
    if 'stages' in state:
        print(f"   Completed stages: {len([s for s in state['stages'].values() if s.get('status') == 'complete'])}")
    
    # Show stage history from markdown
    in_history = False
    for line in content.split('\n'):
        if '| Stage |' in line:
            in_history = True
            print(f"\n   Stage History:")
        elif in_history and line.startswith('|') and '---' not in line:
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells and cells[0]:
                print(f"   {cells[0]:<30} {cells[1]:<12} {cells[2]:<25} {cells[3] if len(cells) > 3 else ''}")
        elif in_history and not line.startswith('|'):
            in_history = False


def cmd_complete(version, stage, notes='', agent=None):
    """Mark a stage as complete."""
    agent = agent or get_agent_id()
    pf, content = load_pipeline_md(version)
    state = load_state(version)
    
    # Update state JSON
    if 'stages' not in state:
        state['stages'] = {}
    state['stages'][stage] = {
        'status': 'complete',
        'completed_at': now_str(),
        'agent': agent,
        'notes': notes,
    }
    save_state(version, state)
    
    # Find the stage history table and append a new row
    lines = content.split('\n')
    output = []
    inserted = False
    i = 0
    while i < len(lines):
        line = lines[i]
        output.append(line)
        
        if not inserted and '| Stage |' in line:
            # Found the header — check for separator on next line
            next_i = i + 1
            if next_i < len(lines) and '---' in lines[next_i]:
                # Separator exists — include it
                output.append(lines[next_i])
                next_i += 1
            else:
                # Missing separator — auto-repair
                col_count = line.count('|') - 1
                separator = '|' + '|'.join(['---'] * col_count) + '|'
                output.append(separator)
                print(f"⚠️  Auto-repaired missing table separator in pipelines/{version}.md")
            
            # Copy existing data rows
            while next_i < len(lines) and lines[next_i].startswith('|'):
                output.append(lines[next_i])
                next_i += 1
            
            # Append new row at end of table
            output.append(f'| {stage} | {now_date()} | {agent} | {notes} |')
            inserted = True
            i = next_i  # skip past consumed lines
            continue
        
        i += 1
    
    if inserted:
        pf.write_text('\n'.join(output))
    else:
        # No table header found at all — warn loudly
        pf.write_text(content)
        print(f"⚠️  Could not find '| Stage |' header in pipelines/{version}.md")
        print(f"   State JSON updated, but markdown stage history was NOT updated.")
        print(f"   Fix: add a stage history table to the pipeline markdown:")
        print(f"   | Stage | Date | Agent | Notes |")
        print(f"   |-------|------|-------|-------|")
    
    print(f"✅ {version}: {stage} → complete ({agent})")
    if notes:
        print(f"   Notes: {notes}")
    print(f"")
    print(f"   ⚠️  NOW POST TO GROUP CHAT (Telegram group -5243763228):")
    print(f"   📊 Pipeline {version} — {stage} complete")
    print(f"   {notes if notes else '(add summary)'}")


def cmd_start(version, stage, agent=None):
    """Mark a stage as started."""
    agent = agent or get_agent_id()
    state = load_state(version)
    
    if 'stages' not in state:
        state['stages'] = {}
    state['stages'][stage] = {
        'status': 'in_progress',
        'started_at': now_str(),
        'agent': agent,
    }
    save_state(version, state)
    print(f"🔨 {version}: {stage} → in_progress ({agent})")


def cmd_status(version, new_status):
    """Update the overall pipeline status in frontmatter."""
    pf, content = load_pipeline_md(version)
    state = load_state(version)
    
    # Update frontmatter status
    content = re.sub(r'^status:\s*.+$', f'status: {new_status}', content, count=1, flags=re.MULTILINE)
    pf.write_text(content)
    
    # Update state JSON
    state['status'] = new_status
    state['status_updated'] = now_str()
    save_state(version, state)
    
    print(f"📊 {version}: status → {new_status}")


def cmd_iteration(version, iteration_id, status, result=''):
    """Update a Phase 3 iteration in the log."""
    pf, content = load_pipeline_md(version)
    
    # Find iteration log table and update or append
    if f'| {iteration_id} |' in content:
        # Update existing row — replace the status and result columns
        content = re.sub(
            rf'\| {re.escape(iteration_id)} \|.*\|',
            f'| {iteration_id} | — | — | {status} | {result} |',
            content
        )
    else:
        # Append new row after the iteration log header
        agent = get_agent_id()
        content = content.replace(
            '| _(none yet',
            f'| {iteration_id} | — | {agent} | {status} | {result} |\n| _(none yet'
        )
        # If no placeholder, append after header
        if f'| {iteration_id} |' not in content:
            content = content.replace(
                '| ID | Hypothesis | Proposed By | Status | Result |\n|----|',
                f'| ID | Hypothesis | Proposed By | Status | Result |\n|----|-----------|-------------|--------|--------|\n| {iteration_id} | — | {agent} | {status} | {result} |'
            )
    
    pf.write_text(content)
    print(f"🔬 {version} iteration {iteration_id}: {status}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    version = sys.argv[1]
    action = sys.argv[2]
    
    if action == 'show':
        cmd_show(version)
    elif action == 'complete':
        stage = sys.argv[3] if len(sys.argv) > 3 else None
        notes = sys.argv[4] if len(sys.argv) > 4 else ''
        agent = sys.argv[5] if len(sys.argv) > 5 else None
        if not stage:
            print("Usage: pipeline_update.py <version> complete <stage> [notes] [agent]")
            sys.exit(1)
        cmd_complete(version, stage, notes, agent)
    elif action == 'start':
        stage = sys.argv[3] if len(sys.argv) > 3 else None
        agent = sys.argv[4] if len(sys.argv) > 4 else None
        if not stage:
            print("Usage: pipeline_update.py <version> start <stage> [agent]")
            sys.exit(1)
        cmd_start(version, stage, agent)
    elif action == 'status':
        new_status = sys.argv[3] if len(sys.argv) > 3 else None
        if not new_status:
            print("Usage: pipeline_update.py <version> status <new_status>")
            sys.exit(1)
        cmd_status(version, new_status)
    elif action == 'iteration':
        iter_id = sys.argv[3] if len(sys.argv) > 3 else None
        status = sys.argv[4] if len(sys.argv) > 4 else None
        result = sys.argv[5] if len(sys.argv) > 5 else ''
        if not iter_id or not status:
            print("Usage: pipeline_update.py <version> iteration <id> <status> [result]")
            sys.exit(1)
        cmd_iteration(version, iter_id, status, result)
    else:
        print(f"Unknown action: {action}")
        print("Actions: show, complete, start, status, iteration")
        sys.exit(1)


if __name__ == '__main__':
    main()
