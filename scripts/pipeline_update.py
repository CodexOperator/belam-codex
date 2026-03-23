#!/usr/bin/env python3
"""
Pipeline Stage Updater

Single command for agents to update pipeline state. Updates BOTH the pipeline
markdown primitive and the state JSON atomically. Manages pending_action and
prints fire-and-forget ping instructions for the next agent.

Automatically:
  - Appends rows to the correct phase's Stage History table
  - Creates new Stage History tables when a phase section exists but has no table
  - Bumps frontmatter status on start/complete/block transitions
  - Updates state JSON phase tracking

Usage:
    # Complete a stage:
    python3 scripts/pipeline_update.py v4 complete architect_design --agent architect --notes "Design v2 with all blocks resolved"
    
    # Block a stage (Critic found issues):
    python3 scripts/pipeline_update.py v4 block critic_code_review --agent critic --notes "BLOCK-1: wrong loss fn" --artifact v4_critic_blocks.md
    
    # Start a stage:
    python3 scripts/pipeline_update.py v4 start builder_implementation --agent builder --notes "Starting implementation"
    
    # Set overall pipeline status:
    python3 scripts/pipeline_update.py v4 status phase1_build
    
    # Add a Phase 3 iteration result:
    python3 scripts/pipeline_update.py v4 iteration 01 complete "54.2% accuracy, +0.3 Sharpe"
    
    # View current state:
    python3 scripts/pipeline_update.py v4 show

Flag-style args (--agent, --notes, --artifact) work from any position.
Positional args still supported for backward compatibility:
    python3 scripts/pipeline_update.py v4 complete stage "notes" agent
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
PIPELINES_DIR = WORKSPACE / 'pipelines'
BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
SCRIPTS = WORKSPACE / 'scripts'
OPENCLAW_CONFIG = Path(os.path.expanduser('~/.openclaw/openclaw.json'))

# Telegram group chat for pipeline notifications
PIPELINE_GROUP_CHAT_ID = '-5243763228'

# Agent session keys for fire-and-forget pings
AGENT_SESSIONS = {
    'architect': 'agent:architect:telegram:group:-5243763228',
    'critic':    'agent:critic:telegram:group:-5243763228',
    'builder':   'agent:builder:telegram:group:-5243763228',
}

# Agent display names and emojis for notifications
AGENT_DISPLAY = {
    'architect':  ('🏗️ Architect', 'architect'),
    'critic':     ('🔍 Critic', 'critic'),
    'builder':    ('🔨 Builder', 'builder'),
    'belam-main': ('🔮 Belam', 'default'),
    'main':       ('🔮 Belam', 'default'),
    'unknown':    ('🔮 Belam', 'default'),
}

# ═══════════════════════════════════════════════════════════════════════
# Stage transition map: when stage X completes, what's next?
# Format: completed_stage → (next_pending_action, next_agent, ping_message_template)
# ═══════════════════════════════════════════════════════════════════════
STAGE_TRANSITIONS = {
    # Kickoff — initial pipeline creation triggers architect design
    'pipeline_created':           ('architect_design',           'architect', 'New pipeline created. Design the notebook architecture per pipelines/{v}.md'),

    # Phase 1
    'architect_design':           ('critic_design_review',       'critic',    'Design ready for review at pipeline_builds/{v}_architect_design.md'),
    'critic_design_review':       ('builder_implementation',     'builder',   'Design approved. Build spec at pipeline_builds/{v}_architect_design.md'),
    'architect_design_revision':  ('critic_design_review',       'critic',    'Design revised, re-review at pipeline_builds/{v}_architect_design.md'),
    'builder_implementation':     ('critic_code_review',         'critic',    'Implementation done. Review the notebook.'),
    'critic_code_review':         ('phase1_complete',            'architect', 'Phase 1 code review passed. Ready for Phase 2 design.'),
    # Phase 1 blocks
    'builder_apply_blocks':       ('critic_code_review',         'critic',    'Blocks fixed. Re-review the notebook.'),

    # Phase 1 revisions (coordinator-triggered, loops back to phase1_complete)
    'phase1_revision_architect':        ('phase1_revision_critic_review',  'critic',    'Revision design ready at pipeline_builds/{v}_phase1_revision_architect.md'),
    'phase1_revision_critic_review':    ('phase1_revision_builder',        'builder',   'Revision design approved. Build per pipeline_builds/{v}_phase1_revision_architect.md'),
    'phase1_revision_builder':          ('phase1_revision_code_review',    'critic',    'Revision implementation done. Review the notebook.'),
    'phase1_revision_code_review':      ('phase1_complete',                'architect', 'Phase 1 revision code review passed. Back to phase1_complete.'),
    # Phase 1 revision blocks
    'phase1_revision_architect_fix':    ('phase1_revision_critic_review',  'critic',    'Revision design revised, re-review at pipeline_builds/{v}_phase1_revision_architect.md'),
    'phase1_revision_builder_fix':      ('phase1_revision_code_review',    'critic',    'Revision blocks fixed. Re-review the notebook.'),

    # Local experiment execution (process stage, not agent)
    'local_experiment_running':   ('local_experiment_complete',  'system',    'Local experiment run completed. Results at notebooks/local_results/{v}/'),
    'local_experiment_complete':  ('local_analysis_architect',   'architect', 'Experiments complete. Analyze results at notebooks/local_results/{v}/. Read the analysis MD and write a comprehensive preliminary report with any additional analysis scripts needed.'),

    # Local analysis (architect→critic→builder loop with reasoning)
    'local_analysis_architect':           ('local_analysis_critic_review',       'critic',    'Preliminary analysis report ready at notebooks/local_results/{v}/{v}_analysis_report.md. Review the analysis and script recommendations.'),
    'local_analysis_critic_review':       ('local_analysis_builder',             'builder',   'Analysis design approved. Implement additional scripts, run them, incorporate results into the report at notebooks/local_results/{v}/'),
    'local_analysis_architect_revision':  ('local_analysis_critic_review',       'critic',    'Analysis revised. Re-review at notebooks/local_results/{v}/{v}_analysis_report.md'),
    'local_analysis_builder':             ('local_analysis_code_review',         'critic',    'Analysis scripts implemented and run. Review the updated report and code at notebooks/local_results/{v}/'),
    'local_analysis_builder_fix':         ('local_analysis_code_review',         'critic',    'Analysis blocks fixed. Re-review at notebooks/local_results/{v}/'),
    'local_analysis_code_review':         ('local_analysis_report_build',        'system',    'Analysis code review passed. Building LaTeX report.'),
    'local_analysis_report_build':        ('local_analysis_complete',            'system',    'LaTeX report built. PDF at notebooks/local_results/{v}/{v}_report.pdf'),
    # local_analysis_complete is a HUMAN GATE — no auto-transition to Phase 2.
    # Shael must explicitly approve via: R kickoff <ver> --phase2
    # 'local_analysis_complete':         ('phase2_architect_design',            'architect', 'Local analysis complete with PDF report. Design Phase 2 per ...'),

    # Phase 2
    'phase2_architect_design':    ('phase2_critic_design_review','critic',    'Phase 2 design ready at pipeline_builds/{v}_phase2_architect_design.md'),
    'phase2_critic_design_review':('phase2_builder_implementation','builder', 'Phase 2 design approved. Build spec at pipeline_builds/{v}_phase2_architect_design.md'),
    'phase2_architect_revision':  ('phase2_critic_design_review','critic',    'Phase 2 design revised, re-review at pipeline_builds/{v}_phase2_architect_design.md'),
    'phase2_builder_implementation':('phase2_critic_code_review','critic',    'Phase 2 implementation done. Review the notebook.'),
    'builder_phase2_implemented': ('phase2_critic_code_review',  'critic',    'Phase 2 implementation done. Review the notebook.'),
    'phase2_critic_code_review':  ('phase2_complete',            'architect', 'Phase 2 code review passed. Pipeline complete (or ready for Phase 3).'),
    # Phase 2 blocks
    'builder_apply_phase2_blocks':('phase2_critic_code_review',  'critic',    'Phase 2 analysis blocks fixed. Re-review the notebook.'),
    'critic_block_fixes':         ('phase2_critic_code_review',  'critic',    'Blocks fixed. Re-review the notebook.'),

    # Phase 3
    'phase3_architect_design':    ('phase3_critic_review',       'critic',    'Phase 3 iteration design ready for review.'),
    'phase3_critic_review':       ('phase3_builder_implementation','builder', 'Phase 3 design approved. Build it.'),
    'phase3_builder_implementation':('phase3_critic_code_review','critic',    'Phase 3 implementation done. Review the notebook.'),
    'phase3_critic_code_review':  ('phase3_complete',            'architect', 'Phase 3 iteration complete.'),

    # ── Analysis Pipeline — Phase 1 (autonomous statistical analysis) ──────
    'analysis_architect_design':          ('analysis_critic_review',            'critic',    'Analysis design ready at pipeline_builds/{v}_architect_analysis_design.md'),
    'analysis_critic_review':             ('analysis_builder_implementation',   'builder',   'Analysis design approved. Implement notebook per pipeline_builds/{v}_architect_analysis_design.md'),
    'analysis_architect_design_revision': ('analysis_critic_review',            'critic',    'Analysis design revised, re-review at pipeline_builds/{v}_architect_analysis_design.md'),
    'analysis_builder_implementation':    ('analysis_critic_code_review',       'critic',    'Analysis notebook complete. Review implementation at notebooks/crypto_{v}_analysis.ipynb'),
    'analysis_critic_code_review':        ('analysis_phase1_complete',          'architect', 'Phase 1 analysis code review passed. Notify Shael — phase 1 complete, ready for directed questions.'),
    # Analysis Phase 1 block fixes
    'analysis_builder_apply_blocks':      ('analysis_critic_code_review',       'critic',    'Analysis blocks fixed. Re-review the notebook.'),

    # ── Analysis Pipeline — Phase 2 (Shael-directed analysis) ─────────────
    'analysis_phase2_architect':                 ('analysis_phase2_critic_review',            'critic',    'Phase 2 analysis design ready at pipeline_builds/{v}_phase2_architect_design.md'),
    'analysis_phase2_architect_design':          ('analysis_phase2_critic_review',            'critic',    'Phase 2 analysis design ready at pipeline_builds/{v}_phase2_architect_analysis_design.md'),
    'analysis_phase2_critic_review':             ('analysis_phase2_builder_implementation',   'builder',   'Phase 2 analysis design approved. Extend notebook per pipeline_builds/{v}_phase2_architect_analysis_design.md'),
    'analysis_phase2_architect_revision':        ('analysis_phase2_critic_review',            'critic',    'Phase 2 analysis design revised, re-review.'),
    'analysis_phase2_builder_implementation':    ('analysis_phase2_critic_code_review',       'critic',    'Phase 2 analysis notebook extended. Review additions.'),
    'analysis_phase2_critic_code_review':        ('analysis_phase2_complete',                 'architect', 'Phase 2 analysis code review passed. Pipeline complete.'),
    # Analysis Phase 2 block fixes
    'analysis_phase2_builder_apply_blocks':      ('analysis_phase2_critic_code_review',       'critic',    'Phase 2 analysis blocks fixed. Re-review the notebook.'),
}

# ═══════════════════════════════════════════════════════════════════════
# Status bumps: when pending_action reaches one of these, bump overall
# pipeline frontmatter status. Keyed on next_action.
# ═══════════════════════════════════════════════════════════════════════
STATUS_BUMPS = {
    # ── Kickoff ──────────────────────────────────────────────────────
    'architect_design':                 'phase1_design',

    # ── Builder Pipeline — Phase 1 ───────────────────────────────────
    'critic_design_review':             'phase1_review',
    'builder_implementation':           'phase1_build',
    'critic_code_review':               'phase1_code_review',
    'phase1_complete':                  'phase1_complete',

    # Phase 1 revisions
    'phase1_revision_critic_review':    'phase1_revision',
    'phase1_revision_builder':          'phase1_revision',
    'phase1_revision_code_review':      'phase1_revision',

    # ── Local Experiment Execution ────────────────────────────────────
    'local_experiment_running':         'experiment_running',
    'local_experiment_complete':        'experiment_complete',

    # ── Local Analysis (post-experiment) ──────────────────────────────
    'local_analysis_critic_review':     'local_analysis_in_progress',
    'local_analysis_builder':           'local_analysis_in_progress',
    'local_analysis_code_review':       'local_analysis_in_progress',
    'local_analysis_report_build':      'local_analysis_report',
    'local_analysis_complete':          'local_analysis_complete',

    # ── Builder Pipeline — Phase 2 ───────────────────────────────────
    'phase2_critic_design_review':      'phase2_review',
    'phase2_builder_implementation':    'phase2_build',
    'phase2_critic_code_review':        'phase2_code_review',
    'phase2_complete':                  'phase2_complete',

    # ── Builder Pipeline — Phase 3 ───────────────────────────────────
    'phase3_critic_review':             'phase3_active',
    'phase3_builder_implementation':    'phase3_active',
    'phase3_critic_code_review':        'phase3_active',
    'phase3_complete':                  'phase3_complete',

    # ── Analysis Pipeline — Phase 1 ──────────────────────────────────
    'analysis_critic_review':                   'analysis_phase1_review',
    'analysis_builder_implementation':          'analysis_phase1_build',
    'analysis_critic_code_review':              'analysis_phase1_code_review',
    'analysis_phase1_complete':                 'phase1_complete',

    # ── Analysis Pipeline — Phase 2 ──────────────────────────────────
    'analysis_phase2_critic_review':            'phase2_in_progress',
    'analysis_phase2_builder_implementation':   'phase2_in_progress',
    'analysis_phase2_critic_code_review':       'phase2_in_progress',
    'analysis_phase2_complete':                 'phase2_complete',
}

# ═══════════════════════════════════════════════════════════════════════
# Start status bumps: when a stage is started, bump frontmatter status.
# This ensures the pipeline status reflects the current active phase
# even before the first complete call.
# ═══════════════════════════════════════════════════════════════════════
START_STATUS_BUMPS = {
    # Local analysis starts
    'local_analysis_architect':                 'local_analysis_in_progress',
    'local_analysis_critic_review':             'local_analysis_in_progress',
    'local_analysis_builder':                   'local_analysis_in_progress',
    'local_analysis_code_review':               'local_analysis_in_progress',
    'local_analysis_report_build':              'local_analysis_report',

    # Analysis Phase 2 starts
    'analysis_phase2_architect':                'phase2_in_progress',
    'analysis_phase2_architect_design':         'phase2_in_progress',
    'analysis_phase2_critic_review':            'phase2_in_progress',
    'analysis_phase2_builder_implementation':   'phase2_in_progress',
    'analysis_phase2_critic_code_review':       'phase2_in_progress',

    # Phase 1 revision starts
    'phase1_revision_architect':                'phase1_revision',
    'phase1_revision_critic_review':            'phase1_revision',
    'phase1_revision_builder':                  'phase1_revision',
    'phase1_revision_code_review':              'phase1_revision',

    # Local experiment starts
    'local_experiment_running':                 'experiment_running',

    # Builder Phase 2 starts
    'phase2_architect_design':                  'phase2_in_progress',
    'phase2_critic_design_review':              'phase2_in_progress',
    'phase2_builder_implementation':            'phase2_in_progress',
    'phase2_critic_code_review':                'phase2_in_progress',

    # Phase 3 starts
    'phase3_architect_design':                  'phase3_active',
    'phase3_critic_review':                     'phase3_active',
    'phase3_builder_implementation':            'phase3_active',
    'phase3_critic_code_review':                'phase3_active',
}

BLOCK_TRANSITIONS = {
    'critic_design_review':       ('architect_design_revision',  'architect', 'Design has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'critic_code_review':         ('builder_apply_blocks',       'builder',   'Code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'phase2_critic_design_review':('phase2_architect_revision',  'architect', 'Phase 2 design has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'phase2_critic_code_review':  ('builder_apply_phase2_blocks','builder',   'Phase 2 code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    # Phase 1 revision blocks
    'phase1_revision_critic_review':   ('phase1_revision_architect_fix',  'architect', 'Revision design has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'phase1_revision_code_review':     ('phase1_revision_builder_fix',    'builder',   'Revision code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),

    'phase3_critic_review':       ('phase3_architect_revision',  'architect', 'Phase 3 design has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'phase3_critic_code_review':  ('phase3_builder_fix',         'builder',   'Phase 3 code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),

    # ── Local Analysis block transitions ──────────────────────────────
    'local_analysis_critic_review':        ('local_analysis_architect_revision',        'architect', 'Analysis review has blocks. Revise report at notebooks/local_results/{v}/{v}_analysis_report.md'),
    'local_analysis_code_review':          ('local_analysis_builder_fix',               'builder',   'Analysis code review has blocks. Fix at notebooks/local_results/{v}/'),

    # ── Analysis Pipeline block transitions ────────────────────────────
    'analysis_critic_review':              ('analysis_architect_design_revision',       'architect', 'Analysis design has methodology blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'analysis_critic_code_review':         ('analysis_builder_apply_blocks',            'builder',   'Analysis code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'analysis_phase2_critic_review':       ('analysis_phase2_architect_revision',       'architect', 'Phase 2 analysis design has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
    'analysis_phase2_critic_code_review':  ('analysis_phase2_builder_apply_blocks',     'builder',   'Phase 2 analysis code review has blocks. Fix instructions at pipeline_builds/{v}_{artifact}'),
}

# ═══════════════════════════════════════════════════════════════════════
# Phase detection: determine which phase a stage belongs to based on
# its name prefix. Used for routing history table entries.
# ═══════════════════════════════════════════════════════════════════════
PHASE_PATTERNS = [
    # Order matters — more specific patterns first
    (re.compile(r'(analysis_)?phase3_|^phase3_'),    3),
    (re.compile(r'(analysis_)?phase2_|^phase2_'),    2),
    # Everything else is Phase 1
]

def detect_phase(stage_name: str) -> int:
    """Determine which phase a stage belongs to (1, 2, or 3)."""
    for pattern, phase in PHASE_PATTERNS:
        if pattern.search(stage_name):
            return phase
    return 1


# Phase section header patterns (match common variations)
PHASE_SECTION_PATTERNS = {
    1: re.compile(r'^## Phase 1[:\s—–-]', re.MULTILINE),
    2: re.compile(r'^## Phase 2[:\s—–-]', re.MULTILINE),
    3: re.compile(r'^## Phase 3[:\s—–-]', re.MULTILINE),
}


# ═══════════════════════════════════════════════════════════════════════
# Telegram group chat notifications
# ═══════════════════════════════════════════════════════════════════════

def _get_bot_token(agent: str) -> str | None:
    """
    Read bot token from OpenClaw config for sending group notifications.
    Uses the acting agent's bot if they're a group member (architect/critic/builder),
    otherwise falls back to architect bot (since the main/default bot may not be
    in the group chat).
    """
    try:
        if not OPENCLAW_CONFIG.exists():
            return None
        config = json.loads(OPENCLAW_CONFIG.read_text())
        accounts = config.get('channels', {}).get('telegram', {}).get('accounts', {})

        # Map agent name to Telegram account
        _, account_key = AGENT_DISPLAY.get(agent, ('', 'default'))

        # Prefer the acting agent's bot, but fall back to architect if the
        # acting agent isn't a group member (e.g. belam-main/default bot)
        GROUP_MEMBER_ACCOUNTS = {'architect', 'critic', 'builder'}
        if account_key not in GROUP_MEMBER_ACCOUNTS:
            account_key = 'architect'  # fallback — always a group member

        account = accounts.get(account_key, {})
        return account.get('botToken')
    except Exception:
        return None


def notify_group(agent: str, version: str, event_type: str, stage: str, notes: str = ''):
    """
    Best-effort: send a pipeline status notification to the Telegram group chat.
    Uses the acting agent's bot token so the message appears from the right bot.
    Silently fails on any error — never blocks pipeline operations.
    """
    try:
        token = _get_bot_token(agent)
        if not token:
            print(f"   ℹ️  No bot token found for '{agent}' — group notification skipped")
            return

        display_name, _ = AGENT_DISPLAY.get(agent, (agent, 'default'))

        # Format the notification message
        if event_type == 'start':
            emoji = '▶️'
            action_text = 'started'
        elif event_type == 'complete':
            emoji = '✅'
            action_text = 'completed'
        elif event_type == 'block':
            emoji = '🚫'
            action_text = 'BLOCKED'
        else:
            emoji = '📋'
            action_text = event_type

        # Build message with Telegram MarkdownV2 — keep it simple, use HTML instead
        lines = [
            f'{emoji} <b>{display_name}</b> {action_text}: <code>{stage}</code>',
            f'📦 Pipeline: <code>{version}</code>',
        ]
        if notes:
            # Truncate long notes for readability
            truncated = notes[:300] + ('…' if len(notes) > 300 else '')
            lines.append(f'📝 {truncated}')

        message = '\n'.join(lines)

        # Send via Telegram Bot API
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        payload = json.dumps({
            'chat_id': PIPELINE_GROUP_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
            'disable_notification': False,
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get('ok'):
                print(f"   📢 Group chat notified")
            else:
                print(f"   ⚠️  Telegram API error: {result.get('description', 'unknown')}")

    except Exception as e:
        # Best-effort — never block pipeline operations
        print(f"   ⚠️  Group notification failed: {e}")


def trigger_memory_update(agent: str, version: str, stage: str, notes: str):
    """Fire-and-forget: log a memory entry for the agent that just completed a stage."""
    agent_id = agent if agent in ("architect", "critic", "builder", "main") else "main"
    try:
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "agent_memory_update.py"),
                "--agent", agent_id,
                "--pipeline", version,
                "--stage", stage,
                "--summary", notes or f"Completed stage {stage}",
            ],
            timeout=15,
            check=False,
        )
    except Exception as e:
        print(f"   ⚠️  Memory update skipped: {e}")


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


def parse_flags(argv):
    """Parse --flag value pairs from argv, returning a dict and remaining positional args."""
    flags = {}
    positional = []
    i = 0
    while i < len(argv):
        if argv[i].startswith('--') and i + 1 < len(argv) and not argv[i + 1].startswith('--'):
            flags[argv[i][2:]] = argv[i + 1]
            i += 2
        elif argv[i].startswith('--') and '=' in argv[i]:
            key, val = argv[i][2:].split('=', 1)
            flags[key] = val
            i += 1
        else:
            positional.append(argv[i])
            i += 1
    return flags, positional


def find_phase_table_range(lines, phase_num):
    """
    Find the line range of the Stage History table for a given phase.
    Returns (header_line_idx, last_row_line_idx, table_exists).
    If the phase section exists but has no table, returns (insert_after_idx, None, False).
    If the phase section doesn't exist, returns (None, None, False).
    """
    phase_pattern = PHASE_SECTION_PATTERNS.get(phase_num)
    if not phase_pattern:
        return None, None, False

    # Find the phase section header
    phase_header_idx = None
    for i, line in enumerate(lines):
        if phase_pattern.match(line):
            phase_header_idx = i
            break

    if phase_header_idx is None:
        return None, None, False

    # Find the next ## header (end of this phase section)
    next_section_idx = len(lines)
    for i in range(phase_header_idx + 1, len(lines)):
        if lines[i].startswith('## ') and not lines[i].startswith('### '):
            next_section_idx = i
            break

    # Look for a Stage History table within this phase section
    table_header_idx = None
    for i in range(phase_header_idx, next_section_idx):
        if '| Stage |' in lines[i]:
            table_header_idx = i
            break

    if table_header_idx is None:
        # No table yet — return insertion point (after phase header + any description text)
        insert_idx = phase_header_idx + 1
        # Skip past any non-empty, non-header lines (description text)
        while insert_idx < next_section_idx and lines[insert_idx].strip() and not lines[insert_idx].startswith('#'):
            insert_idx += 1
        return insert_idx, None, False

    # Table exists — find the last row
    last_row_idx = table_header_idx
    for i in range(table_header_idx + 1, next_section_idx):
        if lines[i].startswith('|'):
            last_row_idx = i
        else:
            break

    return table_header_idx, last_row_idx, True


def append_to_phase_table(content, phase_num, stage, date, agent, notes):
    """
    Append a row to the correct phase's Stage History table.
    Creates the table if the phase section exists but has no table yet.
    Returns the updated content string.
    """
    lines = content.split('\n')
    header_idx, last_row_idx, table_exists = find_phase_table_range(lines, phase_num)

    new_row = f'| {stage} | {date} | {agent} | {notes} |'

    if table_exists:
        # Insert after the last row
        lines.insert(last_row_idx + 1, new_row)
    elif header_idx is not None:
        # Phase section exists but no table — create one
        table_lines = [
            '',
            '### Stage History',
            '| Stage | Date | Agent | Notes |',
            '|-------|------|-------|-------|',
            new_row,
        ]
        for j, tl in enumerate(table_lines):
            lines.insert(header_idx + j, tl)
    else:
        # Phase section doesn't exist at all — fall back to appending to any existing table
        # (backward compat: find the LAST table in the file)
        fallback_idx = None
        for i, line in enumerate(lines):
            if line.startswith('|') and '---' not in line and 'Stage' not in line:
                fallback_idx = i
        if fallback_idx is not None:
            lines.insert(fallback_idx + 1, new_row)
            print(f"   ⚠️  No Phase {phase_num} section found — appended to last table in file")
        else:
            # No table anywhere — append at end with a new section
            lines.extend([
                '',
                f'## Phase {phase_num}',
                '',
                '### Stage History',
                '| Stage | Date | Agent | Notes |',
                '|-------|------|-------|-------|',
                new_row,
            ])
            print(f"   📝 Created new Phase {phase_num} section with Stage History table")

    return '\n'.join(lines)


def update_phase_state_json(state, phase_num, stage, started=False):
    """Update the phase-level tracking in state JSON."""
    phase_key = f'phase{phase_num}'
    if phase_key not in state:
        state[phase_key] = {}
    state[phase_key]['stage'] = stage
    if started:
        state[phase_key]['started'] = now_date()


# ═══════════════════════════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════════════════════════

def cmd_show(version):
    """Show current pipeline state."""
    pf, content = load_pipeline_md(version)
    state = load_state(version)
    
    status_match = re.search(r'^status:\s*(.+)$', content, re.MULTILINE)
    status = status_match.group(1).strip() if status_match else 'unknown'
    
    print(f"📋 Pipeline {version}")
    print(f"   Status: {status}")
    print(f"   File: {pf}")
    
    if 'stages' in state:
        print(f"   Completed stages: {len([s for s in state['stages'].values() if s.get('status') == 'complete'])}")
    
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
    phase = detect_phase(stage)
    
    # Update state JSON
    if 'stages' not in state:
        state['stages'] = {}
    state['stages'][stage] = {
        'status': 'complete',
        'completed_at': now_str(),
        'agent': agent,
        'notes': notes,
    }
    update_phase_state_json(state, phase, stage)
    state['last_updated'] = now_str()
    save_state(version, state)
    
    # Append to the correct phase's history table
    content = append_to_phase_table(content, phase, stage, now_date(), agent, notes)
    pf.write_text(content)
    
    # Update pending_action based on stage transition map
    transition = STAGE_TRANSITIONS.get(stage)
    if transition:
        next_action, next_agent, ping_template = transition
        state['pending_action'] = next_action
        state['last_updated'] = now_str()
        save_state(version, state)

        # Auto-bump the overall pipeline status
        new_status = STATUS_BUMPS.get(next_action)
        if new_status:
            content = pf.read_text()
            old_match = re.search(r'^status:\s*(.+)$', content, re.MULTILINE)
            old_status = old_match.group(1).strip() if old_match else '?'
            if old_status != new_status:
                cmd_status(version, new_status)
                print(f"   📊 Auto-bumped status: {old_status} → {new_status}")
    
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

    # Notify group chat
    notify_group(agent, version, 'complete', stage, notes)

    trigger_memory_update(agent, version, stage, notes)


def cmd_start(version, stage, agent=None, notes=None):
    """Mark a stage as started. Updates state JSON, frontmatter status, and history table."""
    agent = agent or get_agent_id()
    pf, content = load_pipeline_md(version)
    state = load_state(version)
    phase = detect_phase(stage)
    
    # Update state JSON
    if 'stages' not in state:
        state['stages'] = {}
    state['stages'][stage] = {
        'status': 'in_progress',
        'started_at': now_str(),
        'agent': agent,
    }
    if notes:
        state['stages'][stage]['notes'] = notes

    update_phase_state_json(state, phase, stage, started=True)
    state['last_updated'] = now_str()
    save_state(version, state)
    
    # Append to the correct phase's history table
    display_notes = notes or 'In progress'
    content = append_to_phase_table(content, phase, stage, now_date(), agent, display_notes)
    pf.write_text(content)

    # Auto-bump frontmatter status for phase transitions
    new_status = START_STATUS_BUMPS.get(stage)
    if new_status:
        current_content = pf.read_text()
        old_match = re.search(r'^status:\s*(.+)$', current_content, re.MULTILINE)
        old_status = old_match.group(1).strip() if old_match else '?'
        if old_status != new_status:
            cmd_status(version, new_status)
            print(f"   📊 Auto-bumped status: {old_status} → {new_status}")
    
    print(f"🔨 {version}: {stage} → in_progress ({agent})")
    if notes:
        print(f"   Notes: {notes}")

    # Notify group chat
    notify_group(agent, version, 'start', stage, notes or '')


def cmd_block(version, stage, notes='', agent=None, artifact=None):
    """Mark a review stage as blocked — sets pending_action to the fix step."""
    agent = agent or get_agent_id()
    pf, content = load_pipeline_md(version)
    state = load_state(version)
    phase = detect_phase(stage)

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
        state[f'{stage}_blocks_artifact'] = f'machinelearning/snn_applied_finance/research/pipeline_builds/{artifact}'

    transition = BLOCK_TRANSITIONS.get(stage)
    if transition:
        next_action, next_agent, ping_template = transition
        state['pending_action'] = next_action
    state['last_updated'] = now_str()
    save_state(version, state)

    # Auto-bump status
    if transition:
        new_status = STATUS_BUMPS.get(next_action)
        if new_status:
            cmd_status(version, new_status)

    # Append to the correct phase's history table
    content = append_to_phase_table(content, phase, blocked_stage, now_date(), agent, f'BLOCKED: {notes}')
    pf.write_text(content)

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

    # Notify group chat
    notify_group(agent, version, 'block', stage, notes)

    trigger_memory_update(agent, version, f"{stage}_blocked", f"BLOCKED: {notes}")


def cmd_status(version, new_status):
    """Update the overall pipeline status in frontmatter."""
    pf, content = load_pipeline_md(version)
    state = load_state(version)
    
    content = re.sub(r'^status:\s*.+$', f'status: {new_status}', content, count=1, flags=re.MULTILINE)
    pf.write_text(content)
    
    state['status'] = new_status
    state['status_updated'] = now_str()
    save_state(version, state)
    
    print(f"📊 {version}: status → {new_status}")


def cmd_iteration(version, iteration_id, status, result=''):
    """Update a Phase 3 iteration in the log."""
    pf, content = load_pipeline_md(version)
    
    if f'| {iteration_id} |' in content:
        content = re.sub(
            rf'\| {re.escape(iteration_id)} \|.*\|',
            f'| {iteration_id} | — | — | {status} | {result} |',
            content
        )
    else:
        agent = get_agent_id()
        content = content.replace(
            '| _(none yet',
            f'| {iteration_id} | — | {agent} | {status} | {result} |\n| _(none yet'
        )
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
    
    # Parse flags from all remaining args
    flags, positional = parse_flags(sys.argv[3:])
    
    if action == 'show':
        cmd_show(version)

    elif action == 'complete':
        stage = positional[0] if positional else flags.get('stage')
        notes = flags.get('notes', positional[1] if len(positional) > 1 else '')
        agent = flags.get('agent', positional[2] if len(positional) > 2 else None)
        if not stage:
            print("Usage: pipeline_update.py <version> complete <stage> [--agent name] [--notes text]")
            sys.exit(1)
        cmd_complete(version, stage, notes, agent)

    elif action == 'start':
        stage = positional[0] if positional else flags.get('stage')
        agent = flags.get('agent', positional[1] if len(positional) > 1 else None)
        notes = flags.get('notes', positional[2] if len(positional) > 2 else None)
        if not stage:
            print("Usage: pipeline_update.py <version> start <stage> [--agent name] [--notes text]")
            sys.exit(1)
        cmd_start(version, stage, agent, notes)

    elif action == 'block':
        stage = positional[0] if positional else flags.get('stage')
        notes = flags.get('notes', positional[1] if len(positional) > 1 else '')
        agent = flags.get('agent', positional[2] if len(positional) > 2 else None)
        artifact = flags.get('artifact')
        if not stage:
            print("Usage: pipeline_update.py <version> block <stage> [--agent name] [--notes text] [--artifact file.md]")
            sys.exit(1)
        cmd_block(version, stage, notes, agent, artifact)

    elif action == 'status':
        new_status = positional[0] if positional else flags.get('status')
        if not new_status:
            print("Usage: pipeline_update.py <version> status <new_status>")
            sys.exit(1)
        cmd_status(version, new_status)

    elif action == 'iteration':
        iter_id = positional[0] if positional else flags.get('id')
        status = positional[1] if len(positional) > 1 else flags.get('status')
        result = positional[2] if len(positional) > 2 else flags.get('result', '')
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
