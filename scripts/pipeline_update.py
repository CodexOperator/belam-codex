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

try:
    import yaml
except ImportError:
    yaml = None

from pipeline_paths import pipeline_builds_dir_from_meta, state_file_candidates

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
PIPELINES_DIR = WORKSPACE / 'pipelines'
BUILDS_DIR = WORKSPACE / 'pipeline_builds'
RESEARCH_BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
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
    'system':     ('🤖 System', 'default'),
    'coordinator':('🔮 Belam', 'default'),
    'belam-main': ('🔮 Belam', 'default'),
    'main':       ('🔮 Belam', 'default'),
    'unknown':    ('🔮 Belam', 'default'),
}

# ═══════════════════════════════════════════════════════════════════════
# Stage transitions are resolved from template YAML files exclusively.
# No hardcoded transition dicts — templates are the single source of truth.
# See templates/builder-first-pipeline.md and templates/research-pipeline.md.
#
# Legacy stage names (from existing pipeline files) are mapped to new
# phase-based names via LEGACY_STAGE_MAP in template_parser.py.
# ═══════════════════════════════════════════════════════════════════════

# Empty dicts kept for backward compatibility with imports from other modules
STAGE_TRANSITIONS = {}
BLOCK_TRANSITIONS = {}
STATUS_BUMPS = {}
START_STATUS_BUMPS = {}


def get_transitions_for_pipeline(version: str) -> tuple:
    """Resolve transitions for pipeline. Prefer local phase_map, else template."""
    from template_parser import parse_phase_map, parse_template

    fm = _parse_pipeline_md_frontmatter(version)
    phase_map = fm.get('phase_map')
    if isinstance(phase_map, dict):
        try:
            parsed = parse_phase_map(phase_map)
            if parsed:
                return (
                    parsed['transitions'],
                    parsed.get('block_transitions', {}),
                    parsed.get('status_bumps', {}),
                    parsed.get('start_status_bumps', {}),
                )
        except Exception as e:
            print(f"   ⚠️  phase_map parse error for '{version}': {e}")

    pipeline_type = fm.get('type')
    if not pipeline_type or pipeline_type in ('research', 'infrastructure'):
        template_name = 'research'
    else:
        template_name = pipeline_type

    try:
        parsed = parse_template(template_name)
        if parsed:
            return (
                parsed['transitions'],
                parsed.get('block_transitions', {}),
                parsed.get('status_bumps', {}),
                parsed.get('start_status_bumps', {}),
            )
    except Exception as e:
        print(f"   ⚠️  Template parse error for '{template_name}': {e}")

    return ({}, {}, {}, {})


# ═══════════════════════════════════════════════════════════════════════
# Phase detection: determine which phase a stage belongs to based on
# its name prefix. Used for routing history table entries.
# ═══════════════════════════════════════════════════════════════════════

def detect_phase(stage_name: str) -> int:
    """Determine which phase a stage belongs to.
    
    Supports both legacy names (phase2_*, phase3_*) and new names (p2_*, p3_*, p4_*).
    """
    # New phase-based names: p1_, p2_, p3_, p4_
    m = re.match(r'^p(\d+)_', stage_name)
    if m:
        return int(m.group(1))
    
    # Legacy patterns
    if re.search(r'(analysis_)?phase3_|^phase3_', stage_name):
        return 3
    if re.search(r'(analysis_)?phase2_|^phase2_', stage_name):
        return 2
    if re.search(r'local_experiment|local_analysis', stage_name):
        return 2  # Local experiment/analysis is Phase 2 in research pipelines
    return 1


# Phase section header patterns (match common variations)
PHASE_SECTION_PATTERNS = {
    1: re.compile(r'^## Phase 1[:\s\x97\x96-]', re.MULTILINE),
    2: re.compile(r'^## Phase 2[:\s\x97\x96-]', re.MULTILINE),
    3: re.compile(r'^## Phase 3[:\s\x97\x96-]', re.MULTILINE),
    4: re.compile(r'^## Phase 4[:\s\x97\x96-]', re.MULTILINE),
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

        # Prefer the acting agent's bot, but fall back through known group
        # member bots if the acting agent isn't one (e.g. system, belam-main,
        # coordinator, default bot)
        GROUP_MEMBER_ACCOUNTS = {'architect', 'critic', 'builder'}
        if account_key not in GROUP_MEMBER_ACCOUNTS:
            # Try each group member bot as fallback
            for fallback_key in ('architect', 'builder', 'critic'):
                token = accounts.get(fallback_key, {}).get('botToken')
                if token:
                    return token
            return None  # no tokens found at all

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
    """Suppressed — pipeline stage transitions no longer generate memory entries.
    
    Pipeline state is tracked in pipeline files themselves; memory entries for
    routine stage transitions were noise that bloated daily logs. Decisions,
    lessons, and significant events are captured by sage extraction instead.
    """
    pass


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


def _parse_pipeline_md_frontmatter(version):
    """Parse frontmatter from pipeline .md file for authoritative fields."""
    md_path = PIPELINES_DIR / f'{version}.md'
    if not md_path.exists():
        return {}
    text = md_path.read_text()
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return {}

    fm_text = m.group(1)
    if yaml is not None:
        try:
            data = yaml.safe_load(fm_text) or {}
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    fields = {}
    for line in fm_text.splitlines():
        kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if kv:
            val = kv.group(2).strip()
            if val.lower() in ('true', 'false'):
                val = val.lower() == 'true'
            fields[kv.group(1)] = val
    return fields


def _pipeline_builds_dir(version: str) -> Path:
    """Resolve pipeline builds dir from frontmatter, else legacy defaults."""
    meta = _parse_pipeline_md_frontmatter(version)
    return pipeline_builds_dir_from_meta(
        WORKSPACE,
        meta,
        BUILDS_DIR,
        RESEARCH_BUILDS_DIR,
    )


def _state_file_candidates(version: str) -> list[Path]:
    """Return candidate state file paths, preferring pipeline frontmatter."""
    paths = []
    seen = set()
    for base in (_pipeline_builds_dir(version), BUILDS_DIR, RESEARCH_BUILDS_DIR):
        for path in state_file_candidates(base, version):
            key = str(path)
            if key not in seen:
                paths.append(path)
                seen.add(key)
    return paths


def _builds_artifact_ref(version: str, artifact: str) -> str:
    """Return workspace-relative or absolute artifact ref for messages/state."""
    build_dir = _pipeline_builds_dir(version)
    try:
        base = build_dir.relative_to(WORKSPACE)
    except ValueError:
        base = build_dir
    return f'{base}/{artifact}'


def load_state(version):
    """Load pipeline state with .md frontmatter as authoritative source.

    Reads _state.json for detail (stages, handoffs), but .md frontmatter
    wins for shared fields: status, pending_action, dispatch_claimed,
    last_updated, current_phase.
    """
    # Load JSON state (detail store)
    state = {'version': version, 'stages': {}}
    for state_path in _state_file_candidates(version):
        if state_path.exists():
            state = json.loads(state_path.read_text())
            break

    # Merge .md frontmatter as authoritative for shared fields
    md_fields = _parse_pipeline_md_frontmatter(version)
    MD_AUTHORITATIVE = ('status', 'pending_action', 'dispatch_claimed', 'last_updated', 'current_phase')
    for key in MD_AUTHORITATIVE:
        md_val = md_fields.get(key)
        if md_val is not None and md_val != '':
            json_val = state.get(key)
            if json_val is not None and str(json_val) != str(md_val):
                import logging
                logging.getLogger(__name__).warning(
                    f"State drift [{version}] {key}: md={md_val} json={json_val} — using .md"
                )
            state[key] = md_val

    return state


def _update_pipeline_md_frontmatter(version, updates):
    """Write-through authoritative fields to pipeline .md frontmatter."""
    md_path = PIPELINES_DIR / f'{version}.md'
    if not md_path.exists():
        return
    text = md_path.read_text()
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, re.DOTALL)
    if not m:
        return
    fm_lines = m.group(1).splitlines()
    body = m.group(2)
    updated_keys = set()
    for i, line in enumerate(fm_lines):
        kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if kv and kv.group(1) in updates:
            key = kv.group(1)
            val = updates[key]
            if isinstance(val, bool):
                val = 'true' if val else 'false'
            fm_lines[i] = f'{key}: {val}'
            updated_keys.add(key)
    for key, val in updates.items():
        if key not in updated_keys:
            if isinstance(val, bool):
                val = 'true' if val else 'false'
            fm_lines.append(f'{key}: {val}')
    md_path.write_text(f'---\n' + '\n'.join(fm_lines) + f'\n---\n{body}')


def save_state(version, state):
    """Save pipeline state JSON + write-through to .md frontmatter."""
    build_dir = _pipeline_builds_dir(version)
    build_dir.mkdir(parents=True, exist_ok=True)
    content = json.dumps(state, indent=2)
    # Always write flat file in resolved builds dir
    state_file = build_dir / f'{version}_state.json'
    state_file.write_text(content)
    # Also write subdirectory file if it exists (sweep prefers this)
    sub_dir = build_dir / version
    if sub_dir.is_dir():
        (sub_dir / '_state.json').write_text(content)

    # Write-through authoritative fields to .md frontmatter
    _update_pipeline_md_frontmatter(version, {
        'status': state.get('status', ''),
        'pending_action': state.get('pending_action', ''),
        'current_phase': str(state.get('current_phase', '')),
        'dispatch_claimed': state.get('dispatch_claimed', False),
        'last_updated': state.get('last_updated', ''),
    })


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
    
    # Update pending_action based on stage transition map (template-aware)
    stage_trans, block_trans, status_bumps_map, start_bumps_map = get_transitions_for_pipeline(version)
    transition = stage_trans.get(stage)
    if transition:
        next_action, next_agent, ping_template = transition[0], transition[1], transition[2]
        state['pending_action'] = next_action
        state['last_updated'] = now_str()
        save_state(version, state)

        # Auto-bump the overall pipeline status
        new_status = status_bumps_map.get(next_action)
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

    # Auto-bump frontmatter status for phase transitions (template-aware)
    _, _, _, start_bumps_map = get_transitions_for_pipeline(version)
    new_status = start_bumps_map.get(stage)
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
        state[f'{stage}_blocks_artifact'] = _builds_artifact_ref(version, artifact)

    # Use template-aware transitions for block resolution
    stage_trans, block_trans, status_bumps_map, _ = get_transitions_for_pipeline(version)
    transition = block_trans.get(stage)
    if transition:
        # Block transitions are 3/4/5-tuples:
        # (fix_stage, fix_role, msg[, session_mode[, runtime]])
        next_action, next_agent = transition[0], transition[1]
        ping_template = transition[2] if len(transition) > 2 else ''
        block_session_mode = transition[3] if len(transition) > 3 else 'fresh'
        state['pending_action'] = next_action
        state['pending_session_mode'] = block_session_mode
    state['last_updated'] = now_str()
    save_state(version, state)

    # Auto-bump status
    if transition:
        new_status = status_bumps_map.get(next_action)
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
