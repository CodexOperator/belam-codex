#!/usr/bin/env python3
"""
Pipeline Automation — Event-driven pipeline lifecycle management.

Runs as a cron job or from heartbeat. No LLM decision-making needed.

Two modes:
  1. Gate check: When analysis pipelines complete, auto-kick downstream pipelines
  2. Stall recovery: Detect pipelines with no activity beyond threshold, auto-re-kick

Usage:
  python3 scripts/pipeline_automate.py                  # Run all checks
  python3 scripts/pipeline_automate.py --gates-only     # Only check gates
  python3 scripts/pipeline_automate.py --stalls-only    # Only recover stalls
  python3 scripts/pipeline_automate.py --dry-run        # Report but don't act
  python3 scripts/pipeline_automate.py --stall-hours 4  # Custom stall threshold (default: 2)

Exit codes:
  0 = nothing to do (or dry-run)
  1 = actions taken
  2 = error
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
PIPELINES_DIR = WORKSPACE / 'pipelines'
BUILDS_DIR = WORKSPACE / 'pipeline_builds'
RESEARCH_BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
SCRIPTS = WORKSPACE / 'scripts'
HANDOFFS_DIR = PIPELINES_DIR / 'handoffs'

# Default stall threshold in hours
DEFAULT_STALL_HOURS = 2

# Telegram group for notifications
PIPELINE_GROUP_CHAT_ID = '-5243763228'


def parse_frontmatter(content: str) -> dict:
    """Extract YAML-like frontmatter from markdown file."""
    fm = {}
    if content.startswith('---'):
        end = content.find('---', 3)
        if end > 0:
            for line in content[3:end].strip().split('\n'):
                if ':' in line and not line.strip().startswith('-'):
                    key, val = line.split(':', 1)
                    fm[key.strip()] = val.strip()
    return fm


def get_pipeline_state(version: str) -> dict | None:
    """Read the state JSON for a pipeline."""
    state_file = BUILDS_DIR / f'{version}_state.json'
    if state_file.exists():
        try:
            return json.load(open(state_file))
        except Exception:
            return None
    return None


def get_pipeline_frontmatter(version: str) -> dict:
    """Read frontmatter from pipeline markdown file."""
    md_file = PIPELINES_DIR / f'{version}.md'
    if md_file.exists():
        return parse_frontmatter(md_file.read_text())
    return {}


def get_all_pipelines() -> list[dict]:
    """Get all pipeline versions with their status and state."""
    pipelines = []
    for md_file in sorted(PIPELINES_DIR.glob('*.md')):
        version = md_file.stem
        fm = parse_frontmatter(md_file.read_text())
        state = get_pipeline_state(version)
        pipelines.append({
            'version': version,
            'status': fm.get('status', 'unknown'),
            'priority': fm.get('priority', 'normal'),
            'started': fm.get('started', ''),
            'state': state,
            'frontmatter': fm,
        })
    return pipelines


def get_last_activity_time(state: dict) -> datetime | None:
    """Get the most recent activity timestamp from a pipeline state."""
    last_updated = state.get('last_updated', '')
    if not last_updated:
        return None
    try:
        # Try ISO format
        if 'T' in last_updated:
            return datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        # Try simple date-time format
        return datetime.strptime(last_updated, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
    except Exception:
        return None


def get_last_handoff_time(version: str) -> datetime | None:
    """Get the most recent handoff timestamp for a pipeline."""
    if not HANDOFFS_DIR.exists():
        return None
    latest = None
    for hf in HANDOFFS_DIR.glob(f'*_{version}_*.json'):
        try:
            data = json.load(open(hf))
            ts = datetime.fromisoformat(data['timestamp'])
            if latest is None or ts > latest:
                latest = ts
        except Exception:
            continue
    return latest


def kickoff_pipeline(version: str, reason: str, dry_run: bool = False) -> bool:
    """Kick off a pipeline via the orchestrator."""
    print(f"   🚀 Kicking off {version}: {reason}")
    if dry_run:
        print(f"   [DRY RUN] Would kick off {version}")
        return True

    cmd = [
        sys.executable, str(SCRIPTS / 'pipeline_orchestrate.py'),
        version, 'complete', 'pipeline_created',
        '--agent', 'belam-main',
        '--notes', f'Auto-kick: {reason}',
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=660)
        if result.returncode == 0:
            print(f"   ✅ {version} kicked off successfully")
            return True
        else:
            print(f"   ❌ Kickoff failed: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        # The orchestrator may be running checkpoint-and-resume — that's OK
        print(f"   ⏱️  Kickoff timed out (agent may be working via checkpoint-and-resume)")
        return True
    except Exception as e:
        print(f"   ❌ Kickoff error: {e}")
        return False


def check_analysis_gates(pipelines: list[dict], dry_run: bool = False) -> int:
    """
    Check if analysis pipeline completions unlock downstream pipelines.
    
    Gate rule: New notebook version pipelines require their analysis pipeline's
    Phase 2 to be complete before they can proceed.
    
    Returns number of actions taken.
    """
    actions = 0

    # Find completed analysis pipelines
    analysis_complete = set()
    for p in pipelines:
        ver = p['version']
        status = p['status']
        if 'analysis' in ver and status in ('phase2_complete', 'phase3_complete', 'archived'):
            # Extract the source version (e.g., v4-deep-analysis → v4)
            source_ver = ver.replace('-deep-analysis', '').replace('-analysis', '')
            analysis_complete.add(source_ver)

    if not analysis_complete:
        return 0

    # Find pipelines that might be gated on analysis completion
    for p in pipelines:
        ver = p['version']
        status = p['status']
        state = p['state']

        if status == 'archived' or not state:
            continue

        pending = state.get('pending_action', '')

        # A pipeline is eligible for auto-kick if:
        # 1. It's stuck at pipeline_created (never properly kicked off)
        # 2. OR it's in phase1_design but the agent never produced output
        if pending == 'architect_design':
            # Check if the architect actually produced a design file
            design_file = BUILDS_DIR / f'{ver}_architect_design.md'
            if not design_file.exists():
                # No design produced — this is a stalled kickoff, not a gate issue
                # (handled by stall recovery)
                continue

        # Check if this pipeline was blocked on an analysis gate
        # For now, any pipeline that's at pipeline_created status gets kicked
        if pending == 'pipeline_created' or status == 'pipeline_created':
            print(f"\n   📋 {ver}: at pipeline_created, checking gates...")
            # This pipeline hasn't been kicked off yet
            actions += 1
            kickoff_pipeline(ver, f'Analysis gate open (post-analysis)', dry_run)

    return actions


def check_stalled_pipelines(pipelines: list[dict], stall_hours: float,
                             dry_run: bool = False) -> int:
    """
    Detect and recover stalled pipelines.
    
    A pipeline is stalled if:
    1. It has a pending_action (agent should be working)
    2. No activity for > stall_hours
    3. No design/implementation artifacts were produced
    
    Recovery: re-kick via orchestrator (which uses checkpoint-and-resume).
    
    Returns number of actions taken.
    """
    actions = 0
    now = datetime.now(timezone.utc)
    stall_threshold = timedelta(hours=stall_hours)

    for p in pipelines:
        ver = p['version']
        status = p['status']
        state = p['state']

        if status in ('archived', 'phase2_complete', 'phase3_complete'):
            continue
        if not state:
            continue

        pending = state.get('pending_action', '')
        if not pending or pending == 'ready_for_colab_run':
            # No pending action or waiting for human (Colab run)
            continue

        # Get last activity time
        last_activity = get_last_activity_time(state)
        last_handoff = get_last_handoff_time(ver)

        # Use the most recent of state update and handoff
        most_recent = last_activity
        if last_handoff and (most_recent is None or last_handoff > most_recent):
            most_recent = last_handoff

        if most_recent is None:
            continue

        age = now - most_recent
        if age < stall_threshold:
            continue

        # Pipeline is stalled — check if work was actually produced
        hours_stalled = age.total_seconds() / 3600

        # Check for artifacts
        has_artifacts = False
        for f in BUILDS_DIR.glob(f'{ver}_*'):
            if f.suffix in ('.md', '.ipynb', '.yaml') and f.name != f'{ver}_state.json':
                # Check if this artifact was modified after the last kickoff
                if f.stat().st_mtime > most_recent.timestamp():
                    has_artifacts = True
                    break

        if has_artifacts:
            # Agent produced work but didn't call orchestrator to complete
            # This might be a session that timed out mid-work
            print(f"\n   ⚠️  {ver}: stalled {hours_stalled:.1f}h but has partial artifacts")
            print(f"      Pending: {pending}")
            print(f"      → Re-kicking with checkpoint-and-resume context")
        else:
            print(f"\n   🔴 {ver}: stalled {hours_stalled:.1f}h with NO artifacts")
            print(f"      Pending: {pending}")
            print(f"      → Re-kicking from scratch")

        actions += 1

        # Determine what to re-kick
        # If pending is architect_design and pipeline never progressed, re-kick from pipeline_created
        phase1_stage = state.get('phase1', {}).get('stage', '')
        if pending == 'architect_design' and phase1_stage in ('architect_design', 'pipeline_created'):
            success = kickoff_pipeline(ver, f'Stall recovery ({hours_stalled:.1f}h, no output)', dry_run)
            if success and not dry_run:
                # Wait before kicking off the next one — one pipeline at a time
                # The orchestrator + checkpoint-and-resume may take up to 10+ min
                # Give the agent time to complete before the next pipeline lands
                print(f"      ⏳ Waiting 10s before next pipeline...")
                time.sleep(10)
        else:
            # For other stages, we need to re-wake the appropriate agent
            # Use the orchestrator's verify mechanism
            if not dry_run:
                print(f"      Running orchestrator verify for {ver}...")
                try:
                    result = subprocess.run(
                        [sys.executable, str(SCRIPTS / 'pipeline_orchestrate.py'),
                         ver, 'verify'],
                        capture_output=True, text=True, timeout=660,
                    )
                    print(f"      {result.stdout[:200]}")
                except Exception as e:
                    print(f"      ❌ Verify failed: {e}")
            else:
                print(f"      [DRY RUN] Would run orchestrator verify for {ver}")

    return actions


def notify_actions(actions: int, details: str):
    """Send a Telegram notification about automated actions."""
    if actions == 0:
        return
    try:
        subprocess.run(
            [sys.executable, str(SCRIPTS / 'pipeline_update.py'),
             '--notify-only', f'🤖 Pipeline Automation: {actions} action(s) taken\n{details}'],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        pass  # Best effort


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Pipeline automation — gate checks + stall recovery')
    parser.add_argument('--gates-only', action='store_true', help='Only check analysis gates')
    parser.add_argument('--stalls-only', action='store_true', help='Only recover stalled pipelines')
    parser.add_argument('--dry-run', action='store_true', help='Report but don\'t act')
    parser.add_argument('--stall-hours', type=float, default=DEFAULT_STALL_HOURS,
                        help=f'Stall threshold in hours (default: {DEFAULT_STALL_HOURS})')
    args = parser.parse_args()

    check_gates = not args.stalls_only
    check_stalls = not args.gates_only

    pipelines = get_all_pipelines()
    total_actions = 0

    if check_gates:
        print("🔓 Checking analysis gates...")
        gate_actions = check_analysis_gates(pipelines, args.dry_run)
        total_actions += gate_actions
        if gate_actions == 0:
            print("   ✅ No gate-blocked pipelines to unlock")

    if check_stalls:
        print(f"\n⏱️  Checking for stalled pipelines (threshold: {args.stall_hours}h)...")
        stall_actions = check_stalled_pipelines(pipelines, args.stall_hours, args.dry_run)
        total_actions += stall_actions
        if stall_actions == 0:
            print("   ✅ No stalled pipelines detected")

    if total_actions > 0 and not args.dry_run:
        print(f"\n{'═' * 60}")
        print(f"  📊 Total actions: {total_actions}")
        print(f"{'═' * 60}")

    sys.exit(1 if total_actions > 0 else 0)


if __name__ == '__main__':
    main()
