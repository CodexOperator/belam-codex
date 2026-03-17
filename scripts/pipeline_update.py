#!/usr/bin/env python3
"""
Pipeline Stage Updater

Single command for agents to update pipeline state. Updates BOTH the pipeline
markdown primitive and the state JSON atomically. Manages pending_action and
prints fire-and-forget ping instructions for the next agent.

Usage:
    # Complete a stage (auto-advances pending_action + prints ping instruction):
    python3 scripts/pipeline_update.py v4 complete architect_design "Design v2 with all blocks resolved" architect
    
    # Block a stage (Critic found issues — sets pending_action to fix step):
    python3 scripts/pipeline_update.py v4 block critic_code_review "BLOCK-1: wrong loss fn" critic --artifact v4_critic_blocks.md
    
    # Start a stage:
    python3 scripts/pipeline_update.py v4 start builder_implementation builder
    
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

# Agent session keys for fire-and-forget pings
AGENT_SESSIONS = {
    'architect': 'agent:architect:telegram:group:-5243763228',
    'critic':    'agent:critic:telegram:group:-5243763228',
    'builder':   'agent:builder:telegram:group:-5243763228',
}

# Stage transition map: when stage X completes, what's next?
# Format: completed_stage → (next_pending_action, next_agent, ping_message_template)
STAGE_TRANSITIONS = {
    # Phase 1
    'architect_design':           ('critic_design_review',       'critic',    'Design ready for review at pipeline_builds/{v}_architect_design.md'),
    'critic_design_review':       ('builder_implementation',     'builder',   'Design approved. Build spec at pipeline_builds/{v}_architect_design.md'),
    'architect_design_revision':  ('critic_design_review',       'critic',    'Design revised, re-review at pipeline_builds/{v}_architect_design.md'),
    'builder_implementation':     ('critic_code_review',         'critic',    'Implementation done. Review the notebook.'),
    'critic_code_review':         ('phase1_complete',            'architect', 'Phase 1 code review passed. Ready for Phase 2 design.'),
    # Phase 1 blocks
    'builder_apply_blocks':       ('critic_code_review',         'critic',    'Blocks fixed. Re-review the notebook.'),

    # Phase 2
    'phase2_architect_design':    ('phase2_critic_design_review','critic',    'Phase 2 design ready at pipeline_builds/{v}_phase2_architect_design.md'),
    'phase2_critic_design_review':('phase2_builder_implementation','builder', 'Phase 2 design approved. Build spec at pipeline_builds/{v}_phase2_architect_design.md'),
    'phase2_architect_revision':  ('phase2_critic_design_review','critic',    'Phase 2 design revised, re-review at pipeline_builds/{v}_phase2_architect_design.md'),
    'phase2_builder_implementation':('phase2_critic_code_review','critic',    'Phase 2 implementation done. Review the notebook.'),
    'builder_phase2_implemented': ('phase2_critic_code_review',  'critic',    'Phase 2 implementation done. Review the notebook.'),
    'phase2_critic_code_review':  ('phase2_complete',            'architect', 'Phase 2 code review passed. Pipeline complete (or ready for Phase 3).'),
    # Phase 2 blocks
    'builder_apply_phase2_blocks':('phase2_critic_code_review',  'critic',    'Phase 2 blocks fixed. Re-review the notebook.'),
    'critic_block_fixes':         ('phase2_critic_code_review',  'critic',    'Blocks fixed. Re-review the notebook.'),

    # Phase 3
    'phase3_architect_design':    ('phase3_critic_review',       'critic',    'Phase 3 iteration design ready for review.'),
    'phase3_critic_review':       ('phase3_builder_implementation','builder', 'Phase 3 design approved. Build it.'),
    'phase3_builder_implementation':('phase3_critic_code_review','critic',    'Phase 3 implementation done. Review the notebook.'),
    'phase3_critic_code_review':  ('phase3_complete',            'architect', 'Phase 3 iteration complete.'),

    # ── Analysis Pipeline — Phase 1 (autonomous statistical analysis) ──────────
    'analysis_architect_design':          ('analysis_critic_review',            'critic',    'Analysis design ready at pipeline_builds/{v}_architect_analysis_design.md'),
    'analysis_critic_review':             ('analysis_builder_implementation',   'builder',   'Analysis design approved. Implement notebook per pipeline_builds/{v}_architect_analysis_design.md'),
    'analysis_architect_design_revision': ('analysis_critic_review',            'critic',    'Analysis design revised, re-review at pipeline_builds/{v}_architect_analysis_design.md'),
    'analysis_builder_implementation':    ('analysis_critic_code_review',       'critic',    'Analysis notebook complete. Review implementation at notebooks/crypto_{v}_analysis.ipynb'),
    'analysis_critic_code_review':        ('analysis_phase1_complete',          'architect', 'Phase 1 analysis code review passed. Notify Shael — phase 1 complete, ready for directed questions.'),
    # Analysis Phase 1 block fixes
    'analysis_builder_apply_blocks':      ('analysis_critic_code_review',       'critic',    'Analysis blocks fixed. Re-review the notebook.'),

    # ── Analysis Pipeline — Phase 2 (Shael-directed analysis) ─────────────────
    'analysis_phase2_architect_design':          ('analysis_phase2_critic_review',            'critic',    'Phase 2 analysis design ready at pipeline_builds/{v}_phase2_architect_analysis_design.md'),
    'analysis_phase2_critic_review':             ('analysis_phase2_builder_implementation',   'builder',   'Phase 2 analysis design approved. Extend notebook per pipeline_builds/{v}_phase2_architect_analysis_design.md'),
    'analysis_phase2_architect_revision':        ('analysis_phase2_critic_review',            'critic',    'Phase 2 analysis design revised, re-review.'),
    'analysis_phase2_builder_implementation':    ('analysis_phase2_critic_code_review',       'critic',    'Phase 2 analysis notebook extended. Review additions.'),
    'analysis_phase2_critic_code_review':        ('analysis_phase2_complete',                 'architect', 'Phase 2 analysis code review passed. Pipeline complete.'),
    # Analysis Phase 2 block fixes
    'analysis_phase2_builder_apply_blocks':      ('analysis_phase2_critic_code_review',       'critic',    'Phase 2 analysis blocks fixed. Re-review the notebook.'),
}

# Block transitions: when a review stage is blocked, what's the fix action?
BLOCK_TRANSITIONS = {
    'critic_design_review':       ('architect_design_revision',  'architect', 'Design has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'critic_code_review':         ('builder_apply_blocks',       'builder',   'Code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'phase2_critic_design_review':('phase2_architect_revision',  'architect', 'Phase 2 design has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'phase2_critic_code_review':  ('builder_apply_phase2_blocks','builder',   'Phase 2 code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'phase3_critic_review':       ('phase3_architect_revision',  'architect', 'Phase 3 design has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'phase3_critic_code_review':  ('phase3_builder_fix',         'builder',   'Phase 3 code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),

    # ── Analysis Pipeline block transitions ────────────────────────────────────
    'analysis_critic_review':              ('analysis_architect_design_revision',       'architect', 'Analysis design has methodology blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'analysis_critic_code_review':         ('analysis_builder_apply_blocks',            'builder',   'Analysis code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'analysis_phase2_critic_review':       ('analysis_phase2_architect_revision',       'architect', 'Phase 2 analysis design has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'analysis_phase2_critic_code_review':  ('analysis_phase2_builder_apply_blocks',     'builder',   'Phase 2 analysis code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
}


def print_ping_instruction(version, next_agent, ping_msg, artifact=None):
    """Print the fire-and-forget ping instruction for the agent to copy-paste."""
    session_key = AGENT_SESSIONS.get(next_agent)
    if not session_key:
        print(f"   ⚠️  Unknown agent '{next_agent}' — ping manually")
        return

    msg = ping_msg.format(v=version, artifact=artifact or '')
    print(f"")
    print(f"   🔔 PING {next_agent.upper()} (fire-and-forget, timeoutSeconds: 0):")
    print(f"   Session: {session_key}")
    print(f"   Message: {msg}")
    print(f"")
    print(f"   Also post status update to group chat (Telegram group -5243763228)")


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
    
    # Update pending_action based on stage transition map
    transition = STAGE_TRANSITIONS.get(stage)
    if transition:
        next_action, next_agent, ping_template = transition
        state['pending_action'] = next_action
        state['last_updated'] = now_str()
        save_state(version, state)
    
    print(f"✅ {version}: {stage} → complete ({agent})")
    if notes:
        print(f"   Notes: {notes}")

    if transition:
        print(f"   pending_action → {next_action}")
        print_ping_instruction(version, next_agent, ping_template)
    else:
        print(f"")
        print(f"   ⚠️  No auto-transition for '{stage}' — set pending_action manually if needed")
        print(f"   Also post status update to group chat (Telegram group -5243763228)")


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


def cmd_block(version, stage, notes='', agent=None, artifact=None):
    """Mark a review stage as blocked — sets pending_action to the fix step."""
    agent = agent or get_agent_id()
    pf, content = load_pipeline_md(version)
    state = load_state(version)

    blocked_stage = f'{stage}_blocked'

    # Update state JSON
    if 'stages' not in state:
        state['stages'] = {}
    state['stages'][blocked_stage] = {
        'status': 'blocked',
        'blocked_at': now_str(),
        'agent': agent,
        'notes': notes,
    }
    if artifact:
        state[f'{stage}_blocks_artifact'] = f'SNN_research/machinelearning/snn_applied_finance/research/pipeline_builds/{artifact}'

    # Look up the block transition
    transition = BLOCK_TRANSITIONS.get(stage)
    if transition:
        next_action, next_agent, ping_template = transition
        state['pending_action'] = next_action
    state['last_updated'] = now_str()
    save_state(version, state)

    # Append blocked entry to stage history table
    lines = content.split('\n')
    output = []
    inserted = False
    i = 0
    while i < len(lines):
        line = lines[i]
        output.append(line)

        if not inserted and '| Stage |' in line:
            next_i = i + 1
            if next_i < len(lines) and '---' in lines[next_i]:
                output.append(lines[next_i])
                next_i += 1
            else:
                col_count = line.count('|') - 1
                separator = '|' + '|'.join(['---'] * col_count) + '|'
                output.append(separator)

            while next_i < len(lines) and lines[next_i].startswith('|'):
                output.append(lines[next_i])
                next_i += 1

            output.append(f'| {blocked_stage} | {now_date()} | {agent} | BLOCKED: {notes} |')
            inserted = True
            i = next_i
            continue

        i += 1

    if inserted:
        pf.write_text('\n'.join(output))

    print(f"🚫 {version}: {stage} → BLOCKED ({agent})")
    if notes:
        print(f"   Notes: {notes}")
    if artifact:
        print(f"   Blocks artifact: pipeline_builds/{artifact}")

    if transition:
        print(f"   pending_action → {next_action}")
        print_ping_instruction(version, next_agent, ping_template, artifact)
    else:
        print(f"")
        print(f"   ⚠️  No auto-transition for blocking '{stage}' — set pending_action manually")
        print(f"   Also post status update to group chat (Telegram group -5243763228)")


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
    elif action == 'block':
        stage = sys.argv[3] if len(sys.argv) > 3 else None
        notes = sys.argv[4] if len(sys.argv) > 4 else ''
        agent = sys.argv[5] if len(sys.argv) > 5 else None
        # Parse --artifact flag
        artifact = None
        for i, arg in enumerate(sys.argv):
            if arg == '--artifact' and i + 1 < len(sys.argv):
                artifact = sys.argv[i + 1]
        if not stage:
            print("Usage: pipeline_update.py <version> block <stage> [notes] [agent] [--artifact filename.md]")
            sys.exit(1)
        cmd_block(version, stage, notes, agent, artifact)
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
        print("Actions: show, complete, block, start, status, iteration")
        sys.exit(1)


if __name__ == '__main__':
    main()
