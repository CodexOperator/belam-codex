#!/usr/bin/env python3
"""
Pipeline Autorun — Event-driven pipeline lifecycle automation.

Replaces the LLM heartbeat's "notice and decide" pattern with deterministic code.
Call from heartbeat, cron, or post-completion hooks.

Two modes:
  1. --check-gates    Detect newly-opened gates and kick off eligible pipelines
  2. --check-stalled  Detect stalled pipelines (no activity > threshold) and re-kick
  3. (default)        Run both checks

Usage:
  python3 scripts/pipeline_autorun.py                  # Both checks
  python3 scripts/pipeline_autorun.py --check-gates    # Gate check only
  python3 scripts/pipeline_autorun.py --check-stalled  # Stall check only
  python3 scripts/pipeline_autorun.py --dry-run        # Report only, don't kick
  python3 scripts/pipeline_autorun.py --one <version>  # Kick one specific pipeline
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
PIPELINES_DIR = WORKSPACE / 'pipelines'
BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
SCRIPTS = WORKSPACE / 'scripts'
TASKS_DIR = WORKSPACE / 'tasks'

# Stall threshold: if pending_action has no progress for this many minutes, re-kick
STALL_THRESHOLD_MINUTES = 120  # 2 hours

# Delay between sequential kickoffs (seconds)
KICKOFF_DELAY_SECONDS = 10

# Only one pipeline may have active agent work at a time.
# A pipeline is "active" if its last_updated is within this window
# and it has a pending agent action (not human-gated).
ACTIVE_WINDOW_MINUTES = STALL_THRESHOLD_MINUTES  # Same as stall threshold

# Telegram group for notifications
PIPELINE_GROUP_CHAT_ID = '-5243763228'


def load_pipeline_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter fields from a pipeline markdown file."""
    content = path.read_text()
    if not content.startswith('---'):
        return {}
    end = content.index('---', 3)
    frontmatter = content[3:end]
    result = {}
    for line in frontmatter.strip().split('\n'):
        if ':' in line and not line.startswith(' '):
            key, _, val = line.partition(':')
            val = val.strip().strip('"').strip("'")
            # Handle arrays like [a, b, c]
            if val.startswith('[') and val.endswith(']'):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(',')]
            result[key.strip()] = val
    return result


def load_state_json(version: str) -> dict:
    """Load the pipeline state JSON."""
    state_file = BUILDS_DIR / f'{version}_state.json'
    if state_file.exists():
        return json.load(open(state_file))
    return {}


def get_active_pipelines() -> list[dict]:
    """Get all non-archived pipelines with their state."""
    pipelines = []
    for f in sorted(PIPELINES_DIR.glob('*.md')):
        fm = load_pipeline_frontmatter(f)
        if fm.get('status') == 'archived':
            continue
        version = f.stem
        state = load_state_json(version)
        pipelines.append({
            'version': version,
            'path': f,
            'frontmatter': fm,
            'state': state,
            'status': fm.get('status', 'unknown'),
            'pending_action': state.get('pending_action', 'none'),
            'last_updated': state.get('last_updated', ''),
        })
    return pipelines


def parse_timestamp(ts: str) -> datetime | None:
    """Parse various timestamp formats to datetime."""
    if not ts:
        return None
    for fmt in [
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
    ]:
        try:
            dt = datetime.strptime(ts, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def minutes_since(ts: str) -> float | None:
    """Minutes elapsed since timestamp."""
    dt = parse_timestamp(ts)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    return (now - dt).total_seconds() / 60


def kick_pipeline(version: str, dry_run: bool = False) -> bool:
    """Kick off a pipeline via the orchestrator."""
    print(f"  🚀 Kicking off {version}...")
    if dry_run:
        print(f"     [DRY RUN] Would call: belam kickoff {version}")
        return True

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / 'pipeline_orchestrate.py'),
             version, 'complete', 'pipeline_created',
             '--agent', 'belam-main',
             '--notes', f'Auto-kicked by pipeline_autorun (gate open or stall recovery)'],
            text=True,
            timeout=700,  # 10min agent timeout + buffer
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"     ⚠️  Kickoff timed out (orchestrator handles checkpoint-and-resume)")
        return True  # The orchestrator's checkpoint-and-resume takes over
    except Exception as e:
        print(f"     ❌ Kickoff failed: {e}")
        return False


def get_active_agent_pipeline() -> str | None:
    """
    Check if any pipeline currently has active agent work.
    
    Returns the version string of the active pipeline, or None if no pipeline
    is currently being worked on by an agent.
    
    A pipeline is "active" if:
    - It has a pending agent action (not human-gated)
    - Its last_updated is within ACTIVE_WINDOW_MINUTES
    
    This enforces ONE pipeline at a time — agents focus on a single pipeline
    until it either completes its current stage or stalls past the threshold.
    """
    agent_actions = {
        'architect_design', 'critic_design_review', 'builder_implementation',
        'critic_code_review', 'architect_design_revision', 'builder_apply_blocks',
        'phase2_architect_design', 'phase2_critic_design_review',
        'phase2_builder_implementation', 'phase2_critic_code_review',
        'phase2_architect_revision',
        'analysis_architect_design', 'analysis_critic_review',
        'analysis_builder_implementation', 'analysis_critic_code_review',
    }

    pipelines = get_active_pipelines()
    for p in pipelines:
        pending = p['pending_action']
        if pending not in agent_actions:
            continue

        elapsed = minutes_since(p['last_updated'])
        if elapsed is not None and elapsed < ACTIVE_WINDOW_MINUTES:
            return p['version']

    return None


def check_analysis_gate() -> bool:
    """Check if the v4-deep-analysis gate is open (phase2 complete)."""
    # Check both the pipeline file and state JSON
    pipeline_file = PIPELINES_DIR / 'v4-deep-analysis.md'
    if pipeline_file.exists():
        fm = load_pipeline_frontmatter(pipeline_file)
        status = fm.get('status', '')
        if 'phase2_complete' in status or status == 'archived':
            return True

    state = load_state_json('v4-deep-analysis')
    phase2_stage = state.get('phase2', {}).get('stage', '')
    if 'complete' in phase2_stage:
        return True

    return False


def check_gates(dry_run: bool = False) -> list[str]:
    """
    Check for newly-opened gates and kick off eligible pipelines.
    
    Gate rules:
    - New notebook versions require analysis_phase2_complete gate
    - Validation/ensemble tasks are gate-free
    - Only kick pipelines that are stuck at pipeline_created (never started)
    
    Returns list of versions kicked.
    """
    print("\n🔓 Checking gates...\n")
    kicked = []

    # Enforce one-at-a-time: check if any pipeline already has active agent work
    active = get_active_agent_pipeline()
    if active:
        print(f"  🔒 Pipeline '{active}' has active agent work — skipping new kickoffs")
        print(f"     (One pipeline at a time. Will kick next when this completes or stalls.)")
        return kicked

    analysis_gate_open = check_analysis_gate()
    print(f"  Analysis gate (v4-deep-analysis phase2): {'✅ OPEN' if analysis_gate_open else '🔒 CLOSED'}")

    pipelines = get_active_pipelines()
    
    # Sort by priority: critical first, then high, then normal
    priority_order = {'critical': 0, 'high': 1, 'normal': 2, 'low': 3}
    pipelines.sort(key=lambda p: priority_order.get(p['frontmatter'].get('priority', 'normal'), 2))

    for p in pipelines:
        version = p['version']
        status = p['status']
        pending = p['pending_action']

        # Skip pipelines that aren't waiting for kickoff
        if pending not in ('pipeline_created', 'architect_design'):
            continue

        # Check if this pipeline's state shows it was never actually worked on
        state = p['state']
        stages = state.get('stages', {})
        architect_stage = stages.get('architect_design', {})

        # If architect_design exists and has a completed_at, skip — it's done
        if architect_stage.get('status') == 'complete':
            continue

        # Determine if gate-blocked
        tags = p['frontmatter'].get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]

        # Notebook versions and architecture tasks need the analysis gate
        is_gate_blocked = (
            'architecture' in tags or
            version.startswith('v') and version[1:2].isdigit() or
            'notebook' in str(p['frontmatter'].get('description', '')).lower()
        )

        # Gate-free: validation, ensemble, stacking, infrastructure
        gate_free_tags = {'validation', 'ensemble', 'specialists', 'infrastructure'}
        if gate_free_tags & set(tags):
            is_gate_blocked = False

        if is_gate_blocked and not analysis_gate_open:
            print(f"  ⏳ {version}: gate-blocked (waiting for analysis phase2)")
            continue

        # Eligible — kick ONLY this one (highest priority first)
        print(f"  ✅ {version}: eligible (gate {'open' if is_gate_blocked else 'not required'}, priority: {p['frontmatter'].get('priority', 'normal')})")
        success = kick_pipeline(version, dry_run)
        if success:
            kicked.append(version)
        # ONE pipeline at a time — stop after the first kick
        break

    if not kicked:
        print("\n  No pipelines to kick off (or all gate-blocked).")

    return kicked


def check_stalled(dry_run: bool = False, skip_versions: set = None) -> list[str]:
    """
    Detect stalled pipelines and re-kick them.
    
    A pipeline is stalled if:
    - It has a pending_action (not 'none')
    - last_updated is older than STALL_THRESHOLD_MINUTES
    - The pending action is an agent task (not 'ready_for_colab_run' etc.)
    
    Returns list of versions re-kicked.
    """
    skip_versions = skip_versions or set()
    print(f"\n⏱️  Checking for stalled pipelines (>{STALL_THRESHOLD_MINUTES}min threshold)...\n")
    rekicked = []

    # If a pipeline was just kicked by gate check, it's now active — don't re-kick others
    if skip_versions:
        print(f"  ℹ️  Pipeline(s) just kicked: {', '.join(skip_versions)} — only recovering stalls for those\n")

    # Actions that indicate an agent should be working
    agent_actions = {
        'architect_design', 'critic_design_review', 'builder_implementation',
        'critic_code_review', 'architect_design_revision', 'builder_apply_blocks',
        'phase2_architect_design', 'phase2_critic_design_review',
        'phase2_builder_implementation', 'phase2_critic_code_review',
        'phase2_architect_revision',
        'analysis_architect_design', 'analysis_critic_review',
        'analysis_builder_implementation', 'analysis_critic_code_review',
    }

    # Actions that are human-gated (don't auto-recover)
    human_actions = {
        'ready_for_colab_run', 'phase1_complete', 'phase2_complete',
        'phase3_complete', 'pipeline_created',
    }

    pipelines = get_active_pipelines()

    for p in pipelines:
        version = p['version']
        pending = p['pending_action']
        last = p['last_updated']

        if pending in human_actions or pending == 'none':
            continue

        if version in skip_versions:
            print(f"  ⏭️  {version}: already kicked by gate check — skipping")
            continue

        if pending not in agent_actions:
            # Unknown action — skip but warn
            print(f"  ❓ {version}: unknown pending action '{pending}' — skipping")
            continue

        elapsed = minutes_since(last)
        if elapsed is None:
            print(f"  ❓ {version}: cannot parse last_updated '{last}' — skipping")
            continue

        if elapsed < STALL_THRESHOLD_MINUTES:
            print(f"  ✅ {version}: {pending} active ({elapsed:.0f}min ago)")
            continue

        # Stalled — check if there are recent handoff records that show checkpoint-and-resume is active
        handoffs_dir = PIPELINES_DIR / 'handoffs'
        if handoffs_dir.exists():
            recent_handoffs = [
                h for h in handoffs_dir.iterdir()
                if version in h.name and h.stat().st_mtime > (time.time() - STALL_THRESHOLD_MINUTES * 60)
            ]
            if recent_handoffs:
                print(f"  🔄 {version}: {pending} stalled but has recent handoff records — checkpoint-and-resume may be active")
                continue

        # Determine which agent should be working
        agent = 'architect' if 'architect' in pending else (
            'critic' if 'critic' in pending else (
                'builder' if 'builder' in pending else 'unknown'
            )
        )

        print(f"  🚨 {version}: STALLED — {pending} by {agent}, last activity {elapsed:.0f}min ago")

        if dry_run:
            print(f"     [DRY RUN] Would re-kick {version} → {agent}")
            rekicked.append(version)
            break  # ONE at a time, even in dry run

        # Re-kick: reset session first, then wake the agent
        print(f"     Resetting {agent} session for fresh context...")
        try:
            sys.path.insert(0, str(SCRIPTS))
            from pipeline_orchestrate import reset_agent_session
            reset_agent_session(agent)
        except Exception as e:
            print(f"     ⚠️  Session reset failed: {e} — continuing anyway")

        print(f"     Re-waking {agent} for {pending}...")
        try:
            # Build a recovery message
            msg = (
                f"🔄 RECOVERY — Pipeline {version} / Stage: {pending}\n\n"
                f"This stage was started but the agent session ended without completing.\n"
                f"Last activity: {last} ({elapsed:.0f} minutes ago).\n\n"
                f"Read your memory files first, then check pipeline_builds/ for any partial work.\n"
                f"Complete this stage and call the orchestrator when done:\n\n"
                f"python3 scripts/pipeline_orchestrate.py {version} complete {pending} "
                f"--agent {agent} --notes \"summary\" --learnings \"key insights\""
            )

            import uuid
            session_id = str(uuid.uuid4())

            result = subprocess.run(
                ['openclaw', 'agent',
                 '--agent', agent,
                 '--message', msg,
                 '--timeout', '600',
                 '--session-id', session_id,
                 '--json'],
                capture_output=True, text=True,
                timeout=615,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get('status') == 'ok':
                    print(f"     ✅ {agent} responded")
                    rekicked.append(version)
                else:
                    print(f"     ⚠️  {agent} status: {data.get('status')}")
            else:
                print(f"     ❌ Wake failed: exit {result.returncode}")

        except subprocess.TimeoutExpired:
            print(f"     ⏱️  Agent timed out — checkpoint-and-resume will handle on next cycle")
            # Write a checkpoint for the agent
            sys.path.insert(0, str(SCRIPTS))
            from pipeline_orchestrate import consolidate_agent_memory
            consolidate_agent_memory(
                agent, version, f'{pending}_stall_recovery',
                f'Stall recovery attempted, agent timed out after 10min. '
                f'Partial work may exist in pipeline_builds/.'
            )
            rekicked.append(version)

        except Exception as e:
            print(f"     ❌ Recovery failed: {e}")

        # ONE pipeline at a time — stop after the first re-kick
        if rekicked:
            break

    if not rekicked:
        print("\n  No stalled pipelines found.")

    return rekicked


def kick_one(version: str, dry_run: bool = False) -> bool:
    """Kick a specific pipeline regardless of gate/stall status."""
    print(f"\n🎯 Direct kick: {version}\n")
    return kick_pipeline(version, dry_run)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Pipeline Autorun — event-driven lifecycle automation')
    parser.add_argument('--check-gates', action='store_true', help='Check gates and kick eligible pipelines')
    parser.add_argument('--check-stalled', action='store_true', help='Check for stalled pipelines and re-kick')
    parser.add_argument('--dry-run', action='store_true', help='Report only, do not kick')
    parser.add_argument('--one', type=str, help='Kick one specific pipeline')
    args = parser.parse_args()

    print(f"{'═' * 60}")
    print(f"  🤖 PIPELINE AUTORUN — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'═' * 60}")

    if args.dry_run:
        print("  [DRY RUN MODE — no actions will be taken]\n")

    if args.one:
        kick_one(args.one, args.dry_run)
        return

    # Default: run both checks
    run_gates = args.check_gates or (not args.check_gates and not args.check_stalled)
    run_stalled = args.check_stalled or (not args.check_gates and not args.check_stalled)

    kicked = []
    if run_gates:
        kicked += check_gates(args.dry_run)
    if run_stalled:
        if kicked:
            # A pipeline was just kicked — don't start another one
            print(f"\n  ℹ️  Skipping stall check — pipeline '{kicked[0]}' was just kicked (one at a time)")
        else:
            # No gate kicks happened — check for stalls
            stalled = check_stalled(args.dry_run, skip_versions=set(kicked))
            kicked += stalled

    # Summary
    print(f"\n{'─' * 60}")
    if kicked:
        print(f"  📊 Kicked {len(kicked)} pipeline(s): {', '.join(kicked)}")
    else:
        print(f"  📊 No action needed — all pipelines healthy or gated.")
    print(f"{'─' * 60}\n")


if __name__ == '__main__':
    main()
