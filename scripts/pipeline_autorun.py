#!/usr/bin/env python3
"""
Pipeline Autorun — Event-driven pipeline lifecycle automation.

Replaces the LLM heartbeat's "notice and decide" pattern with deterministic code.
Call from heartbeat, cron, or post-completion hooks.

Three checks:
  1. --check-locks    Detect stale session locks (dead/hung agent PIDs) and clear them (5min)
  2. --check-gates    Detect newly-opened gates and kick off eligible pipelines
  3. --check-stalled  Detect stalled pipelines (no activity > 2h threshold) and re-kick
  4. (default)        Run all three checks

Usage:
  python3 scripts/pipeline_autorun.py                  # All checks
  python3 scripts/pipeline_autorun.py --check-locks    # Lock check only
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
ML_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance'
RESULTS_BASE = ML_DIR / 'notebooks' / 'local_results'
SCRIPTS = WORKSPACE / 'scripts'
TASKS_DIR = WORKSPACE / 'tasks'

# Stall threshold: if pending_action has no progress for this many minutes, re-kick
STALL_THRESHOLD_MINUTES = 120  # 2 hours

# Lock staleness threshold: if a session lock file is older than this, the agent is hung
LOCK_STALE_MINUTES = 5

# Delay between sequential kickoffs (seconds)
KICKOFF_DELAY_SECONDS = 10

# Only one pipeline may have active agent work at a time.
# A pipeline is "active" if its last_updated is within this window
# and it has a pending agent action (not human-gated).
ACTIVE_WINDOW_MINUTES = STALL_THRESHOLD_MINUTES  # Same as stall threshold

# Telegram group for notifications
PIPELINE_GROUP_CHAT_ID = '-5243763228'

# Agent session directories
AGENT_SESSION_DIRS = {
    'architect': Path(os.path.expanduser('~/.openclaw/agents/architect/sessions')),
    'critic': Path(os.path.expanduser('~/.openclaw/agents/critic/sessions')),
    'builder': Path(os.path.expanduser('~/.openclaw/agents/builder/sessions')),
}


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


def _is_pipeline_already_dispatched(version: str) -> bool:
    """Check if a pipeline already has an active orchestration dispatch.

    Returns True if the state JSON shows:
    - A pending_action in an agent stage, AND
    - last_dispatched is within the ACTIVE_WINDOW (not stale)

    This prevents duplicate orchestration flows for the same pipeline
    (e.g. two heartbeats firing close together, or manual e0 while
    an agent is already working).
    """
    state_file = BUILDS_DIR / f'{version}_state.json'
    if not state_file.exists():
        return False

    try:
        state = json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError):
        return False

    pending = state.get('pending_action', '')
    last_dispatched = state.get('last_dispatched', '')

    if not pending or not last_dispatched:
        return False

    # Agent stages that indicate an agent has been dispatched
    agent_stages = {
        'architect_design', 'critic_design_review', 'builder_implementation',
        'critic_code_review', 'architect_design_revision', 'builder_apply_blocks',
        'phase2_architect_design', 'phase2_critic_design_review',
        'phase2_builder_implementation', 'phase2_critic_code_review',
        'phase2_architect_revision',
        'analysis_architect_design', 'analysis_critic_review',
        'analysis_builder_implementation', 'analysis_critic_code_review',
        'local_analysis_architect', 'local_analysis_critic_review',
        'local_analysis_builder', 'local_analysis_code_review',
        'local_analysis_report_build',
        'local_experiment_running', 'report_building',
    }

    if pending not in agent_stages:
        return False

    # Check if the dispatch is recent (not stale)
    try:
        dispatched_dt = datetime.fromisoformat(last_dispatched)
        elapsed = (datetime.now(timezone.utc) - dispatched_dt).total_seconds() / 60

        # Unclaimed dispatch older than 5 min = failed dispatch, not active
        UNCLAIMED_THRESHOLD_MINUTES = 5
        dispatch_claimed = state.get('dispatch_claimed', True)  # default True for backwards compat
        if not dispatch_claimed and elapsed >= UNCLAIMED_THRESHOLD_MINUTES:
            print(f"  ⚠️  {version}: dispatch unclaimed after {elapsed:.0f}min — treating as failed")
            return False

        if elapsed < ACTIVE_WINDOW_MINUTES:
            return True
    except (ValueError, TypeError):
        pass

    return False


def kick_pipeline(version: str, dry_run: bool = False) -> bool:
    """Kick off a pipeline via the orchestrator."""
    # Guard: don't spawn a duplicate orchestration flow
    if _is_pipeline_already_dispatched(version):
        print(f"  ⏭️  Skipping {version} — already has an active dispatch (use --check-stalled for stale recovery)")
        return False

    print(f"  🚀 Kicking off {version}...")
    if dry_run:
        print(f"     [DRY RUN] Would call: R kickoff {version}")
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
        'local_analysis_architect', 'local_analysis_critic_review',
        'local_analysis_builder', 'local_analysis_code_review',
        'local_analysis_report_build',
        'local_experiment_running', 'report_building',
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


def check_stale_locks(dry_run: bool = False) -> list[str]:
    """
    Detect and clear stale session lock files that prevent agent dispatch.
    
    A lock is stale if:
    - The PID in the lock file is no longer running, OR
    - The lock is older than LOCK_STALE_MINUTES and the process is hung
    
    Returns list of agents whose locks were cleared.
    """
    print(f"\n🔒 Checking for stale session locks (>{LOCK_STALE_MINUTES}min threshold)...\n")
    cleared = []

    for agent, sessions_dir in AGENT_SESSION_DIRS.items():
        if not sessions_dir.exists():
            continue

        for lock_file in sessions_dir.glob('*.lock'):
            try:
                lock_data = json.loads(lock_file.read_text())
                pid = lock_data.get('pid')
                created_at = lock_data.get('createdAt', '')

                if not pid:
                    continue

                # Check if the PID is still alive
                pid_alive = True
                try:
                    os.kill(pid, 0)  # Signal 0 = check existence
                except ProcessLookupError:
                    pid_alive = False
                except PermissionError:
                    pid_alive = True  # Process exists but we can't signal it

                if not pid_alive:
                    # PID is dead — lock is definitely stale
                    print(f"  💀 {agent}: lock file {lock_file.name} — PID {pid} is dead")
                    if not dry_run:
                        lock_file.unlink()
                        print(f"     ✅ Lock cleared")
                    else:
                        print(f"     [DRY RUN] Would clear lock")
                    cleared.append(agent)
                    continue

                # PID is alive — check how old the lock is
                lock_age = minutes_since(created_at)
                if lock_age is not None and lock_age > LOCK_STALE_MINUTES:
                    print(f"  🧟 {agent}: lock file {lock_file.name} — PID {pid} alive but locked for {lock_age:.0f}min (>{LOCK_STALE_MINUTES}min)")
                    if not dry_run:
                        # Kill the hung process
                        try:
                            os.kill(pid, 15)  # SIGTERM
                            print(f"     🔪 Sent SIGTERM to PID {pid}")
                            # Brief wait for process to die
                            import time as _time
                            _time.sleep(2)
                            # Check if it died
                            try:
                                os.kill(pid, 0)
                                # Still alive — SIGKILL
                                os.kill(pid, 9)
                                print(f"     🔪 Sent SIGKILL to PID {pid}")
                                _time.sleep(1)
                            except ProcessLookupError:
                                pass  # Good, it died
                        except ProcessLookupError:
                            pass  # Already dead
                        except Exception as e:
                            print(f"     ⚠️  Kill failed: {e}")

                        # Clear the lock file
                        if lock_file.exists():
                            lock_file.unlink()
                            print(f"     ✅ Lock cleared")
                    else:
                        print(f"     [DRY RUN] Would kill PID {pid} and clear lock")
                    cleared.append(agent)
                else:
                    age_str = f"{lock_age:.0f}min" if lock_age else "unknown"
                    print(f"  ✅ {agent}: lock file {lock_file.name} — PID {pid} alive, age {age_str} (OK)")

            except (json.JSONDecodeError, OSError) as e:
                print(f"  ⚠️  {agent}: corrupt lock file {lock_file.name} — {e}")
                if not dry_run:
                    lock_file.unlink()
                    print(f"     ✅ Corrupt lock cleared")
                cleared.append(agent)

    if not cleared:
        print("  No stale locks found.")

    # If we cleared locks, reset affected agent sessions for clean dispatch
    if cleared and not dry_run:
        print()
        for agent in set(cleared):
            print(f"  🔄 Resetting {agent} sessions after lock cleanup...")
            try:
                sys.path.insert(0, str(SCRIPTS))
                from pipeline_orchestrate import reset_agent_session
                reset_agent_session(agent)
            except Exception as e:
                print(f"     ⚠️  Session reset failed: {e}")

    return cleared


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
        'local_analysis_architect', 'local_analysis_critic_review',
        'local_analysis_builder', 'local_analysis_code_review',
        'local_analysis_report_build',
        'local_experiment_running', 'report_building',
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


def check_unclaimed_dispatches(dry_run: bool = False, skip_versions: set = None) -> list[str]:
    """
    Recover pipelines where a dispatch was sent but never claimed by the agent.

    A dispatch is considered unclaimed if:
    - dispatch_claimed is False
    - last_dispatched is older than UNCLAIMED_THRESHOLD_MINUTES (5 min)
    - pending_action is an agent stage

    This catches the gap between _is_pipeline_already_dispatched (which now
    treats unclaimed dispatches as failed) and check_stalled (which uses the
    120-min threshold on last_updated).
    """
    UNCLAIMED_THRESHOLD_MINUTES = 5
    skip_versions = skip_versions or set()

    agent_stages = {
        'architect_design', 'critic_design_review', 'builder_implementation',
        'critic_code_review', 'architect_design_revision', 'builder_apply_blocks',
        'phase2_architect_design', 'phase2_critic_design_review',
        'phase2_builder_implementation', 'phase2_critic_code_review',
        'phase2_architect_revision',
        'analysis_architect_design', 'analysis_critic_review',
        'analysis_builder_implementation', 'analysis_critic_code_review',
        'local_analysis_architect', 'local_analysis_critic_review',
        'local_analysis_builder', 'local_analysis_code_review',
        'local_analysis_report_build',
        'local_experiment_running', 'report_building',
    }

    pipelines = get_active_pipelines()
    rekicked = []

    for p in pipelines:
        version = p['version']
        if version in skip_versions:
            continue

        state_file = BUILDS_DIR / f'{version}_state.json'
        if not state_file.exists():
            continue

        try:
            state = json.loads(state_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        pending = state.get('pending_action', '')
        dispatch_claimed = state.get('dispatch_claimed', True)  # default True for backwards compat
        last_dispatched = state.get('last_dispatched', '')

        if dispatch_claimed or not last_dispatched:
            continue
        if pending not in agent_stages:
            continue

        try:
            dispatched_dt = datetime.fromisoformat(last_dispatched)
            elapsed = (datetime.now(timezone.utc) - dispatched_dt).total_seconds() / 60
        except (ValueError, TypeError):
            continue

        if elapsed < UNCLAIMED_THRESHOLD_MINUTES:
            continue

        print(f"  ⚠️  {version}: dispatch unclaimed after {elapsed:.0f}min — re-kicking")

        if dry_run:
            print(f"     [DRY RUN] Would re-kick {version}")
            rekicked.append(version)
            break

        success = kick_pipeline(version, dry_run=False)
        if success:
            rekicked.append(version)
        break  # ONE at a time

    return rekicked


def check_pending_revisions(dry_run: bool = False) -> list[str]:
    """
    Check for pending revision requests and kick off eligible revisions.
    
    Revision request files live at:
        pipeline_builds/{version}_revision_request.md
    
    Format (YAML frontmatter):
        ---
        version: build-equilibrium-snn
        context_file: research/v4_deep_analysis_findings.md
        section: "## For BUILD-EQUILIBRIUM-SNN"
        priority: critical
        created: 2026-03-19T03:15:00Z
        ---
        Optional extra context here.
    
    The request is consumed (deleted) after the revision is kicked.
    Only one revision at a time (respects active-pipeline lock).
    
    Returns list of versions where revisions were kicked.
    """
    print(f"\n🔄 Checking for pending revision requests...\n")
    kicked = []

    # Enforce one-at-a-time
    active = get_active_agent_pipeline()
    if active:
        print(f"  🔒 Pipeline '{active}' has active agent work — skipping revisions")
        return kicked

    # Scan for revision request files
    request_files = sorted(BUILDS_DIR.glob('*_revision_request.md'))
    if not request_files:
        print("  No pending revision requests.")
        return kicked

    # Parse and sort by priority
    requests = []
    priority_order = {'critical': 0, 'high': 1, 'normal': 2, 'low': 3}
    for rf in request_files:
        fm = load_pipeline_frontmatter(rf)
        version = fm.get('version', rf.stem.replace('_revision_request', ''))
        requests.append({
            'file': rf,
            'version': version,
            'frontmatter': fm,
            'priority': fm.get('priority', 'normal'),
        })
    requests.sort(key=lambda r: priority_order.get(r['priority'], 2))

    print(f"  Found {len(requests)} revision request(s): {', '.join(r['version'] for r in requests)}")

    for req in requests:
        version = req['version']
        fm = req['frontmatter']

        # Verify pipeline is at phase1_complete
        state = load_state_json(version)
        pending = state.get('pending_action', '')
        if pending != 'phase1_complete' and not pending.startswith('phase1_revision'):
            print(f"  ⏭️  {version}: not at phase1_complete (pending={pending}) — skipping")
            continue

        # Build revision context
        context_parts = []

        # Load context from referenced file + section if specified
        context_file = fm.get('context_file', '')
        section_header = fm.get('section', '')
        if context_file:
            context_path = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / context_file
            if not context_path.exists():
                # Try relative to workspace
                context_path = WORKSPACE / context_file
            if context_path.exists():
                full_text = context_path.read_text()
                if section_header:
                    # Extract the specific section
                    section_text = _extract_section(full_text, section_header)
                    if section_text:
                        context_parts.append(section_text)
                    else:
                        # Section not found — use full file
                        context_parts.append(full_text)
                else:
                    context_parts.append(full_text)
            else:
                print(f"  ⚠️  Context file not found: {context_file}")

        # Also include body text from the request file itself
        body = _extract_body(req['file'])
        if body.strip():
            context_parts.append(body)

        if not context_parts:
            print(f"  ⚠️  {version}: no context could be loaded — skipping")
            continue

        context = '\n\n'.join(context_parts)

        print(f"  ✅ {version}: eligible for revision (priority: {req['priority']})")

        if dry_run:
            print(f"     [DRY RUN] Would trigger revision for {version}")
            kicked.append(version)
            break

        # Trigger the revision via orchestrator
        try:
            sys.path.insert(0, str(SCRIPTS))
            from pipeline_orchestrate import orchestrate_revise
            result = orchestrate_revise(version, context)
            if result is not False:
                print(f"  ✅ Revision kicked for {version}")
                # Consume the request file
                req['file'].unlink()
                print(f"  🗑️  Consumed request: {req['file'].name}")
                kicked.append(version)
            else:
                print(f"  ❌ Revision failed for {version}")
        except Exception as e:
            print(f"  ❌ Revision error for {version}: {e}")

        # ONE at a time
        break

    return kicked


def _extract_section(text: str, header: str) -> str:
    """Extract a markdown section by header prefix (e.g. '## For BUILD-EQUILIBRIUM-SNN')."""
    header_clean = header.lstrip('#').strip()
    lines = text.split('\n')
    capture = False
    captured = []
    header_level = None

    for line in lines:
        if not capture:
            # Match if the line contains the header text
            stripped = line.lstrip('#').strip()
            if header_clean.lower() in stripped.lower():
                capture = True
                header_level = len(line) - len(line.lstrip('#'))
                captured.append(line)
        else:
            # Stop at next section of same or higher level
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                if level <= header_level:
                    break
            captured.append(line)

    return '\n'.join(captured) if captured else ''


def _extract_body(path: Path) -> str:
    """Extract body text (after YAML frontmatter) from a markdown file."""
    text = path.read_text()
    if text.startswith('---'):
        try:
            end = text.index('---', 3)
            return text[end + 3:].strip()
        except ValueError:
            return text
    return text


def check_phase2_eligible(dry_run: bool = False) -> list[str]:
    """
    Check for Phase 2 direction files and kick off Phase 2 when found.

    Phase 2 is gated on a human-authored direction file:
        pipeline_builds/{version}_phase2_shael_direction.md

    When a pipeline is at local_analysis_complete AND the direction file exists,
    auto-kick Phase 2 (wake architect with the direction content).
    The direction file is NOT consumed — it stays for the architect to read.

    Returns list of versions where Phase 2 was kicked.
    """
    print(f"\n🎯 Checking for Phase 2 direction files...\n")
    kicked = []

    # Enforce one-at-a-time
    active = get_active_agent_pipeline()
    if active:
        print(f"  🔒 Pipeline '{active}' has active agent work — skipping Phase 2 kicks")
        return kicked

    # Find pipelines at local_analysis_complete
    pipelines = get_active_pipelines()
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'normal': 2, 'low': 3}
    eligible = []

    for p in pipelines:
        version = p['version']
        status = p['frontmatter'].get('status', '')
        if status != 'local_analysis_complete':
            continue

        # Check for direction file
        direction_file = BUILDS_DIR / f'{version}_phase2_shael_direction.md'
        if not direction_file.exists():
            print(f"  ⏳ {version}: at local_analysis_complete — no direction file yet")
            continue

        eligible.append(p)

    if not eligible:
        print("  No Phase 2-eligible pipelines.")
        return kicked

    # Sort by priority
    eligible.sort(key=lambda p: priority_order.get(p['frontmatter'].get('priority', 'medium'), 2))

    for p in eligible:
        version = p['version']
        direction_file = BUILDS_DIR / f'{version}_phase2_shael_direction.md'
        print(f"  ✅ {version}: direction file found — kicking Phase 2")

        if dry_run:
            print(f"     [DRY RUN] Would kick Phase 2 for {version}")
            kicked.append(version)
            break

        try:
            sys.path.insert(0, str(SCRIPTS))
            from pipeline_orchestrate import orchestrate_complete
            result = orchestrate_complete(version, 'local_analysis_complete', 'system',
                                          f'Phase 2 approved. Direction at {direction_file.name}')
            if result is not False:
                print(f"  ✅ Phase 2 kicked for {version}")
                kicked.append(version)
            else:
                print(f"  ❌ Phase 2 kick failed for {version}")
        except Exception as e:
            print(f"  ❌ Phase 2 error for {version}: {e}")

        # ONE at a time
        break

    return kicked


def check_analysis_eligible(dry_run: bool = False) -> list[str]:
    """
    Check for pipelines at experiment_complete that are ready for local analysis.

    A pipeline is eligible if:
    - status is experiment_complete
    - Not already in local_analysis stages
    - No active agent work on other pipelines (one at a time)

    Auto-launches the analysis orchestration loop.
    Returns list of versions launched.
    """
    print(f"\n📊 Checking for analysis-eligible pipelines...\n")
    launched = []

    # Check for active agent work
    active = get_active_agent_pipeline()
    if active:
        print(f"  🔒 Pipeline '{active}' has active agent work — skipping analysis")
        return launched

    pipelines = get_active_pipelines()
    eligible = []

    for p in pipelines:
        version = p['version']
        status = p['status']
        pending = p['pending_action']
        pipeline_type = p['frontmatter'].get('type', 'research')

        # Skip infrastructure pipelines — they don't have experiment/analysis phases
        if pipeline_type == 'infrastructure':
            continue

        # Must be at experiment_complete
        if status != 'experiment_complete' and pending != 'local_experiment_complete':
            continue

        # Skip if already in analysis
        if 'local_analysis' in status or 'local_analysis' in pending:
            continue

        eligible.append(p)

    if not eligible:
        print("  No analysis-eligible pipelines.")
        return launched

    # Priority order
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    eligible.sort(key=lambda p: priority_order.get(p['frontmatter'].get('priority', 'medium'), 2))

    for p in eligible:
        version = p['version']
        print(f"  ✅ {version}: eligible for local analysis (priority: {p['frontmatter'].get('priority', '?')})")

        if dry_run:
            print(f"     [DRY RUN] Would launch analysis for {version}")
            launched.append(version)
            break

        try:
            sys.path.insert(0, str(SCRIPTS))
            from pipeline_orchestrate import orchestrate_local_analysis
            result = orchestrate_local_analysis(version)
            if result:
                print(f"  🚀 Analysis loop launched for {version}")
                launched.append(version)
            else:
                print(f"  ❌ Failed to launch analysis for {version}")
        except Exception as e:
            print(f"  ❌ Analysis launch error for {version}: {e}")
            import traceback
            traceback.print_exc()

        # ONE at a time
        break

    return launched


def check_experiment_eligible(dry_run: bool = False) -> list[str]:
    """
    Check for pipelines at phase1_complete that are ready for experiment runs.

    A pipeline is eligible if:
    - status is phase1_complete or pending_action is phase1_complete
    - No pending revision requests exist for it
    - No experiment is currently running (PID file check)
    - No other experiment is currently running (one at a time)

    Auto-launches run_experiment.py via orchestrator.
    Returns list of versions launched.
    """
    print(f"\n🧪 Checking for experiment-eligible pipelines...\n")
    launched = []

    # Check if any experiment is already running
    for pid_file in BUILDS_DIR.glob('*_experiment.pid'):
        try:
            import json as _json
            pid_info = _json.loads(pid_file.read_text())
            pid = pid_info.get('pid')
            os.kill(pid, 0)  # Check if alive
            version_running = pid_info.get('version', pid_file.stem.replace('_experiment', ''))
            print(f"  🔒 Experiment already running: {version_running} (PID: {pid})")
            return launched
        except (OSError, ProcessLookupError):
            # PID dead — clean up stale file
            print(f"  🗑️  Cleaning stale experiment PID: {pid_file.name}")
            pid_file.unlink()

    # Check for active agent work (don't start experiments while agents are working)
    active = get_active_agent_pipeline()
    if active:
        print(f"  🔒 Pipeline '{active}' has active agent work — skipping experiments")
        return launched

    # Find pipelines at phase1_complete with no pending revisions
    revision_versions = set()
    for rf in BUILDS_DIR.glob('*_revision_request.md'):
        fm = load_pipeline_frontmatter(rf)
        version = fm.get('version', rf.stem.replace('_revision_request', ''))
        revision_versions.add(version)

    pipelines = get_active_pipelines()
    eligible = []

    for p in pipelines:
        version = p['version']
        pending = p['pending_action']
        status = p['status']
        pipeline_type = p['frontmatter'].get('type', 'research')

        # Skip infrastructure pipelines — they don't have experiments
        if pipeline_type == 'infrastructure':
            continue

        # Must be at phase1_complete
        if pending != 'phase1_complete' and status != 'phase1_complete':
            continue

        # Skip if pending revision
        if version in revision_versions:
            print(f"  ⏭️  {version}: has pending revision request — skipping experiments")
            continue

        # Skip if already has experiment results and completed
        if status == 'experiment_complete':
            continue

        # Skip if experiment is actively running (not failed)
        if status == 'experiment_running' or pending == 'local_experiment_running':
            # Check if it's a failed run (last stage note says FAILED)
            state_file = BUILDS_DIR / f'{version}_state.json'
            is_failed = False
            if state_file.exists():
                try:
                    state = json.loads(state_file.read_text())
                    last_notes = state.get('last_notes', '')
                    if 'EXPERIMENT FAILED' in last_notes:
                        is_failed = True
                except Exception:
                    pass
            if not is_failed:
                continue
            print(f"  🔄 {version}: previous experiment FAILED — eligible for retry")

        eligible.append(p)

    if not eligible:
        print("  No experiment-eligible pipelines.")
        return launched

    # Priority order
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    eligible.sort(key=lambda p: priority_order.get(p['frontmatter'].get('priority', 'medium'), 2))

    for p in eligible:
        version = p['version']
        print(f"  ✅ {version}: eligible for experiment run (priority: {p['frontmatter'].get('priority', '?')})")

        if dry_run:
            print(f"     [DRY RUN] Would launch experiments for {version}")
            launched.append(version)
            break

        # Launch via orchestrator
        try:
            sys.path.insert(0, str(SCRIPTS))
            from pipeline_orchestrate import orchestrate_local_run
            result = orchestrate_local_run(version)
            if result:
                print(f"  🚀 Experiment runner launched for {version}")
                launched.append(version)
            else:
                print(f"  ❌ Failed to launch experiments for {version}")
        except Exception as e:
            print(f"  ❌ Launch error for {version}: {e}")
            import traceback
            traceback.print_exc()

        # ONE at a time
        break

    return launched


def check_running_experiments(dry_run: bool = False) -> list[str]:
    """
    Monitor running experiments and report status.

    Checks PID files for running experiments, reports progress,
    detects stuck/dead experiments.

    Returns list of versions with completed experiments detected.
    """
    print(f"\n📊 Checking running experiments...\n")
    completed = []

    for pid_file in sorted(BUILDS_DIR.glob('*_experiment.pid')):
        try:
            import json as _json
            pid_info = _json.loads(pid_file.read_text())
        except Exception:
            continue

        pid = pid_info.get('pid')
        version = pid_info.get('version', pid_file.stem.replace('_experiment', ''))
        started = pid_info.get('started', '')

        # Check if process is alive
        try:
            os.kill(pid, 0)
            # Process alive — check how long it's been running
            if started:
                from datetime import datetime as dt
                start_dt = dt.fromisoformat(started)
                elapsed = (dt.now(timezone.utc) - start_dt).total_seconds() / 60
                print(f"  🔬 {version}: running (PID: {pid}, {elapsed:.0f}min elapsed)")

                # Check log for progress
                log_file = RESULTS_BASE / version / 'run.log'
                if log_file.exists():
                    lines = log_file.read_text().strip().split('\n')
                    # Find last progress line
                    for line in reversed(lines[-10:]):
                        if line.startswith('[') and '/' in line:
                            print(f"     Last progress: {line.strip()}")
                            break

            else:
                print(f"  🔬 {version}: running (PID: {pid})")

        except (OSError, ProcessLookupError):
            # Process dead
            print(f"  💀 {version}: experiment process dead (PID: {pid})")

            # Check if it completed successfully
            results_dir = RESULTS_BASE / version
            results_summary = BUILDS_DIR / f'{version}_experiment_results.md'

            if results_summary.exists():
                print(f"     ✅ Results summary exists — likely completed before PID cleanup")
                completed.append(version)
            else:
                print(f"     ⚠️  No results summary — experiment may have crashed")
                # Check if pipeline stage was updated
                state = load_state_json(version)
                if state.get('pending_action') == 'local_experiment_complete':
                    print(f"     ✅ Pipeline shows experiment_complete — cleaning up")
                    completed.append(version)
                else:
                    print(f"     ❌ Pipeline stuck at experiment_running with dead process")
                    if not dry_run:
                        # Reset pipeline to phase1_complete so it can be retried
                        print(f"     🔄 Resetting to phase1_complete for retry")
                        run_cmd = [sys.executable, str(SCRIPTS / 'pipeline_update.py'),
                                  version, 'status', 'phase1_complete']
                        subprocess.run(run_cmd, capture_output=True)

            # Clean up PID file
            if not dry_run:
                pid_file.unlink()
                print(f"     🗑️  Cleaned PID file")

    if not list(BUILDS_DIR.glob('*_experiment.pid')):
        print("  No experiments currently running.")

    return completed


def kick_one(version: str, dry_run: bool = False) -> bool:
    """Kick a specific pipeline regardless of gate/stall status."""
    print(f"\n🎯 Direct kick: {version}\n")
    return kick_pipeline(version, dry_run)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Pipeline Autorun — event-driven lifecycle automation')
    parser.add_argument('--check-gates', action='store_true', help='Check gates and kick eligible pipelines')
    parser.add_argument('--check-stalled', action='store_true', help='Check for stalled pipelines and re-kick')
    parser.add_argument('--check-locks', action='store_true', help='Check for stale session locks only')
    parser.add_argument('--check-revisions', action='store_true', help='Check for pending revision requests')
    parser.add_argument('--check-experiments', action='store_true', help='Check for experiment-eligible pipelines')
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

    if args.check_locks:
        check_stale_locks(args.dry_run)
        return

    # Determine which checks to run
    explicit = args.check_gates or args.check_stalled or args.check_revisions or args.check_experiments
    run_gates = args.check_gates or not explicit
    run_stalled = args.check_stalled or not explicit
    run_revisions = args.check_revisions or not explicit
    run_experiments = args.check_experiments or not explicit

    # Always check stale locks first — they block everything else
    stale_agents = check_stale_locks(args.dry_run)

    # Always check running experiments (monitoring, not launching)
    experiment_completed = check_running_experiments(args.dry_run)

    kicked = []
    if run_gates:
        kicked += check_gates(args.dry_run)
    if run_revisions and not kicked:
        kicked += check_pending_revisions(args.dry_run)
    # Auto-launch analysis for experiment_complete pipelines (before new experiments)
    if not kicked:
        analysis_launched = check_analysis_eligible(args.dry_run)
        kicked += analysis_launched
    if run_experiments and not kicked:
        # Auto-launch experiments for phase1_complete pipelines
        launched = check_experiment_eligible(args.dry_run)
        kicked += launched
    if run_stalled:
        if kicked:
            # A pipeline was just kicked — don't start another one
            print(f"\n  ℹ️  Skipping stall check — pipeline '{kicked[0]}' was just kicked (one at a time)")
        else:
            # No gate kicks happened — check for stalls
            stalled = check_stalled(args.dry_run, skip_versions=set(kicked))
            kicked += stalled

    # Unclaimed dispatch recovery — catches dispatches that were sent but never picked up
    if not kicked:
        unclaimed = check_unclaimed_dispatches(args.dry_run, skip_versions=set(kicked))
        kicked += unclaimed

    # Summary
    print(f"\n{'─' * 60}")
    if stale_agents:
        print(f"  🔒 Cleared stale locks for: {', '.join(set(stale_agents))}")
    if experiment_completed:
        print(f"  🧪 Experiments completed: {', '.join(experiment_completed)}")
    if kicked:
        print(f"  📊 Kicked {len(kicked)} pipeline(s): {', '.join(kicked)}")
    if not kicked and not stale_agents and not experiment_completed:
        print(f"  📊 No action needed — all pipelines healthy or gated.")
    print(f"{'─' * 60}\n")


if __name__ == '__main__':
    main()
