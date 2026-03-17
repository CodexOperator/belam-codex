#!/usr/bin/env python3
"""
Pipeline Orchestrator — Reliable stage transitions with verified handoffs.

Replaces the manual 3-step dance agents had to do:
  1. pipeline_update.py (state + telegram notification)
  2. sessions_send to next agent (often missed/pending)
  3. message to group chat (sometimes skipped)

Now agents call ONE command:
  python3 scripts/pipeline_orchestrate.py <version> complete <stage> --agent <role> --notes "summary"
  python3 scripts/pipeline_orchestrate.py <version> block <stage> --agent <role> --notes "BLOCK reason" --artifact file.md

The orchestrator:
  1. Runs pipeline_update.py for state management + telegram notification
  2. Wakes the next agent via `openclaw agent` CLI (reliable, synchronous)
  3. Verifies the agent started processing
  4. Retries if needed
  5. Posts a delivery receipt to the calling agent

Also supports:
  python3 scripts/pipeline_orchestrate.py <version> start <stage> --agent <role>
  python3 scripts/pipeline_orchestrate.py <version> status <new_status>
  python3 scripts/pipeline_orchestrate.py <version> show
  python3 scripts/pipeline_orchestrate.py <version> verify   # Check if pending handoff was picked up
  python3 scripts/pipeline_orchestrate.py --check-pending     # Check ALL pipelines for stuck handoffs

Usage examples:
  # Architect completes design revision:
  python3 scripts/pipeline_orchestrate.py v4-deep-analysis complete analysis_phase2_architect_revision \\
    --agent architect --notes "BLOCK-1 resolved: softmax gradient corrected"

  # Critic blocks a review:
  python3 scripts/pipeline_orchestrate.py v4-deep-analysis block analysis_phase2_critic_review \\
    --agent critic --notes "BLOCK-1: wrong gradient formula" --artifact v4-deep-analysis_phase2_critic_blocks.md

  # Check for stuck handoffs:
  python3 scripts/pipeline_orchestrate.py --check-pending
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
SCRIPTS = WORKSPACE / 'scripts'
PIPELINE_UPDATE = SCRIPTS / 'pipeline_update.py'
BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
PIPELINES_DIR = WORKSPACE / 'pipelines'
HANDOFFS_DIR = WORKSPACE / 'pipelines' / 'handoffs'
OPENCLAW_CONFIG = Path(os.path.expanduser('~/.openclaw/openclaw.json'))

# How long to wait for agent to respond (seconds)
AGENT_WAKE_TIMEOUT = 60
# Retry once if first attempt fails
AGENT_WAKE_RETRIES = 1
# Grace period before checking if agent picked up (seconds)
PICKUP_GRACE_SECONDS = 5

# Telegram group for notifications
PIPELINE_GROUP_CHAT_ID = '-5243763228'

# Agent display info
AGENT_INFO = {
    'architect': {
        'emoji': '🏗️',
        'name': 'Architect',
        'knowledge': 'research/ARCHITECT_KNOWLEDGE.md',
        'skills': ['quant-workflow'],
    },
    'critic': {
        'emoji': '🔍',
        'name': 'Critic',
        'knowledge': 'research/CRITIC_KNOWLEDGE.md',
        'skills': ['quant-workflow', 'quant-infrastructure'],
    },
    'builder': {
        'emoji': '🔨',
        'name': 'Builder',
        'knowledge': 'research/BUILDER_KNOWLEDGE.md',
        'skills': ['quant-infrastructure'],
    },
}

# ═══════════════════════════════════════════════════════════════════════
# Handoff message templates — rich context for the target agent
# These replace the bare-bones ping instructions from pipeline_update.py
# ═══════════════════════════════════════════════════════════════════════

def build_handoff_message(version: str, completed_stage: str, next_stage: str,
                          next_agent: str, notes: str, artifact: str = '') -> str:
    """Build a rich handoff message with full context for the target agent."""

    agent_info = AGENT_INFO.get(next_agent, {})
    knowledge_file = agent_info.get('knowledge', '')

    # Determine the design/review file to read based on pipeline type and phase
    is_analysis = 'analysis' in version or 'analysis' in completed_stage
    phase = 2 if 'phase2' in completed_stage else (3 if 'phase3' in completed_stage else 1)

    # Build file references
    files_to_read = [
        f'research/AGENT_SOUL.md',
    ]
    if knowledge_file:
        files_to_read.append(knowledge_file)
    if is_analysis:
        files_to_read.append('research/ANALYSIS_AGENT_ROLES.md')

    # Add the relevant design/review artifact
    if artifact:
        files_to_read.append(f'research/pipeline_builds/{artifact}')
    else:
        # Infer the artifact based on stage
        if 'design' in next_stage or 'review' in next_stage:
            prefix = f'{version}_phase{phase}_' if phase > 1 else f'{version}_'
            if is_analysis:
                files_to_read.append(f'research/pipeline_builds/{version}_{"phase2_" if phase == 2 else ""}architect_analysis_design.md')
            else:
                files_to_read.append(f'research/pipeline_builds/{version}_{"phase2_" if phase == 2 else ""}architect_design.md')
        if 'code_review' in next_stage or 'implementation' in next_stage:
            # Builder/code reviewer needs the notebook
            notebook_name = f'crypto_{version.replace("-", "_")}_{"deep_" if "deep" in version else ""}analysis.ipynb' if is_analysis else f'crypto_{version}_predictor.ipynb'
            files_to_read.append(f'notebooks/{notebook_name}')

    files_list = '\n'.join(f'  - {f}' for f in files_to_read)

    msg = f"""🔄 Pipeline Handoff — {version}

**Stage completed:** {completed_stage}
**Your task:** {next_stage}
**Summary:** {notes}

**Read these files before starting:**
{files_list}

**Pipeline state:** `python3 scripts/pipeline_update.py {version} show`

**When you finish, call the orchestrator:**
```
python3 scripts/pipeline_orchestrate.py {version} complete {next_stage} --agent {next_agent} --notes "your summary"
```

If you need to BLOCK, use:
```
python3 scripts/pipeline_orchestrate.py {version} block {next_stage} --agent {next_agent} --notes "BLOCK reason" --artifact your_review_file.md
```

Post your status update to the group chat (Telegram group {PIPELINE_GROUP_CHAT_ID}) when done."""

    return msg


# ═══════════════════════════════════════════════════════════════════════
# Agent wake via `openclaw agent` CLI
# ═══════════════════════════════════════════════════════════════════════

def wake_agent(agent: str, message: str, timeout: int = AGENT_WAKE_TIMEOUT) -> dict:
    """
    Wake a target agent by injecting a message via `openclaw agent` CLI.
    Returns {success, response, session_id, error}.
    """
    cmd = [
        'openclaw', 'agent',
        '--agent', agent,
        '--message', message,
        '--timeout', str(timeout),
        '--json',
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 15,  # extra buffer beyond openclaw's own timeout
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                status = data.get('status', 'unknown')
                session_id = data.get('result', {}).get('meta', {}).get('agentMeta', {}).get('sessionId', '')
                response_text = ''
                payloads = data.get('result', {}).get('payloads', [])
                if payloads:
                    response_text = payloads[0].get('text', '')

                return {
                    'success': status == 'ok',
                    'status': status,
                    'response': response_text,
                    'session_id': session_id,
                    'error': None,
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'status': 'parse_error',
                    'response': result.stdout[:200],
                    'session_id': '',
                    'error': f'Failed to parse JSON response',
                }
        else:
            return {
                'success': False,
                'status': 'exit_error',
                'response': '',
                'session_id': '',
                'error': f'Exit code {result.returncode}: {result.stderr[:200]}',
            }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'status': 'timeout',
            'response': '',
            'session_id': '',
            'error': f'Agent did not respond within {timeout}s',
        }
    except FileNotFoundError:
        return {
            'success': False,
            'status': 'not_found',
            'response': '',
            'session_id': '',
            'error': 'openclaw CLI not found on PATH',
        }
    except Exception as e:
        return {
            'success': False,
            'status': 'exception',
            'response': '',
            'session_id': '',
            'error': str(e),
        }


def check_sessions(agent: str = None) -> list:
    """Check active sessions via gateway call."""
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'call', 'sessions.list', '--json'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            sessions = data.get('sessions', [])
            if agent:
                return [s for s in sessions if f'agent:{agent}' in s.get('key', '')]
            return sessions
    except Exception:
        pass
    return []


# ═══════════════════════════════════════════════════════════════════════
# Handoff tracking — write/read handoff state for verification
# ═══════════════════════════════════════════════════════════════════════

def write_handoff(version: str, completed_stage: str, next_stage: str,
                  next_agent: str, wake_result: dict):
    """Write a handoff record for later verification."""
    HANDOFFS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    handoff = {
        'version': version,
        'completed_stage': completed_stage,
        'next_stage': next_stage,
        'next_agent': next_agent,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'wake_result': {
            'success': wake_result.get('success'),
            'status': wake_result.get('status'),
            'session_id': wake_result.get('session_id'),
            'response_preview': (wake_result.get('response', '') or '')[:100],
        },
        'verified': wake_result.get('success', False),
    }
    path = HANDOFFS_DIR / f'{ts}_{version}_{next_agent}.json'
    path.write_text(json.dumps(handoff, indent=2))
    return path


def get_pending_handoffs() -> list:
    """Get all unverified handoff records."""
    if not HANDOFFS_DIR.exists():
        return []
    pending = []
    for f in sorted(HANDOFFS_DIR.glob('*.json')):
        try:
            data = json.loads(f.read_text())
            if not data.get('verified', False):
                data['_path'] = str(f)
                pending.append(data)
        except Exception:
            pass
    return pending


def mark_handoff_verified(handoff_path: str):
    """Mark a handoff as verified."""
    path = Path(handoff_path)
    if path.exists():
        data = json.loads(path.read_text())
        data['verified'] = True
        data['verified_at'] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(data, indent=2))


# ═══════════════════════════════════════════════════════════════════════
# Telegram notification (supplementary — pipeline_update.py also sends)
# ═══════════════════════════════════════════════════════════════════════

def _get_bot_token(agent: str) -> str | None:
    """Read bot token for Telegram notifications."""
    try:
        if not OPENCLAW_CONFIG.exists():
            return None
        import urllib.request
        config = json.loads(OPENCLAW_CONFIG.read_text())
        accounts = config.get('channels', {}).get('telegram', {}).get('accounts', {})
        GROUP_MEMBER_ACCOUNTS = {'architect', 'critic', 'builder'}
        account_key = agent if agent in GROUP_MEMBER_ACCOUNTS else 'architect'
        account = accounts.get(account_key, {})
        return account.get('botToken')
    except Exception:
        return None


def send_orchestrator_notification(version: str, event: str, details: str):
    """Send an orchestrator-level notification to the group chat."""
    import urllib.request
    import urllib.error
    try:
        token = _get_bot_token('architect')
        if not token:
            return

        message = f"🔄 <b>Orchestrator</b> — <code>{version}</code>\n{event}\n{details}"

        url = f'https://api.telegram.org/bot{token}/sendMessage'
        payload = json.dumps({
            'chat_id': PIPELINE_GROUP_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
            'disable_notification': False,
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"   ⚠️  Orchestrator notification failed: {e}")


# ═══════════════════════════════════════════════════════════════════════
# Import stage transition maps from pipeline_update.py
# ═══════════════════════════════════════════════════════════════════════

# We import these dynamically to stay in sync
sys.path.insert(0, str(SCRIPTS))
try:
    from pipeline_update import STAGE_TRANSITIONS, BLOCK_TRANSITIONS
except ImportError:
    print("❌ Cannot import from pipeline_update.py — ensure it exists at scripts/pipeline_update.py")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════
# Core orchestration commands
# ═══════════════════════════════════════════════════════════════════════

def run_pipeline_update(args: list) -> tuple[bool, str]:
    """Run pipeline_update.py with given args. Returns (success, output)."""
    cmd = [sys.executable, str(PIPELINE_UPDATE)] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except Exception as e:
        return False, str(e)


def orchestrate_complete(version: str, stage: str, agent: str, notes: str):
    """Complete a stage and orchestrate the handoff to the next agent."""
    print(f"\n{'═' * 70}")
    print(f"  🔄 ORCHESTRATOR: {version} — completing {stage}")
    print(f"{'═' * 70}\n")

    # Step 1: Run pipeline_update.py (state + markdown + telegram notification)
    update_args = [version, 'complete', stage, '--agent', agent]
    if notes:
        update_args.extend(['--notes', notes])
    success, output = run_pipeline_update(update_args)
    print(output)
    if not success:
        print(f"\n❌ pipeline_update.py failed — aborting handoff")
        return False

    # Step 2: Determine next agent from transition map
    transition = STAGE_TRANSITIONS.get(stage)
    if not transition:
        print(f"\n   ℹ️  No auto-transition for '{stage}' — no handoff needed")
        return True

    next_stage, next_agent, _ = transition
    print(f"\n   📋 Transition: {stage} → {next_stage} ({next_agent})")

    # Step 3: Build rich handoff message
    handoff_msg = build_handoff_message(version, stage, next_stage, next_agent, notes)

    # Step 4: Wake the next agent
    print(f"\n   🔔 Waking {next_agent}...")
    wake_result = wake_agent(next_agent, handoff_msg, timeout=AGENT_WAKE_TIMEOUT)

    if wake_result['success']:
        print(f"   ✅ {next_agent} responded (session: {wake_result['session_id'][:8]}...)")
        response_preview = (wake_result.get('response', '') or '')[:100]
        if response_preview:
            print(f"   📝 Response: {response_preview}")
    else:
        print(f"   ⚠️  First wake attempt failed: {wake_result.get('error', 'unknown')}")

        # Retry once
        if AGENT_WAKE_RETRIES > 0:
            print(f"   🔄 Retrying wake ({AGENT_WAKE_RETRIES} retry)...")
            time.sleep(3)
            wake_result = wake_agent(next_agent, handoff_msg, timeout=AGENT_WAKE_TIMEOUT + 30)
            if wake_result['success']:
                print(f"   ✅ {next_agent} responded on retry (session: {wake_result['session_id'][:8]}...)")
            else:
                print(f"   ❌ {next_agent} failed to respond after retry: {wake_result.get('error', 'unknown')}")

    # Step 5: Write handoff record
    handoff_path = write_handoff(version, stage, next_stage, next_agent, wake_result)
    print(f"\n   📝 Handoff record: {handoff_path.relative_to(WORKSPACE)}")

    # Step 6: Send orchestrator notification if wake failed
    if not wake_result['success']:
        send_orchestrator_notification(
            version,
            f"⚠️ Handoff delivery issue",
            f"Stage <code>{stage}</code> completed by {agent}, "
            f"but <b>{next_agent}</b> did not confirm pickup for <code>{next_stage}</code>. "
            f"Error: {wake_result.get('error', 'unknown')}"
        )

    # Summary
    print(f"\n{'─' * 70}")
    print(f"  📊 Orchestration Summary:")
    print(f"     Pipeline:    {version}")
    print(f"     Completed:   {stage} ({agent})")
    print(f"     Next:        {next_stage} ({next_agent})")
    print(f"     Handoff:     {'✅ Delivered' if wake_result['success'] else '⚠️ Pending verification'}")
    print(f"     Telegram:    ✅ Group notified (via pipeline_update.py)")
    print(f"{'─' * 70}\n")

    return wake_result['success']


def orchestrate_block(version: str, stage: str, agent: str, notes: str, artifact: str = ''):
    """Block a stage and orchestrate the handoff back to the fixing agent."""
    print(f"\n{'═' * 70}")
    print(f"  🚫 ORCHESTRATOR: {version} — blocking {stage}")
    print(f"{'═' * 70}\n")

    # Step 1: Run pipeline_update.py
    update_args = [version, 'block', stage, '--agent', agent, '--notes', notes]
    if artifact:
        update_args.extend(['--artifact', artifact])
    success, output = run_pipeline_update(update_args)
    print(output)
    if not success:
        print(f"\n❌ pipeline_update.py failed — aborting handoff")
        return False

    # Step 2: Determine fix agent from block transition map
    transition = BLOCK_TRANSITIONS.get(stage)
    if not transition:
        print(f"\n   ℹ️  No auto-transition for blocking '{stage}' — no handoff needed")
        return True

    next_stage, next_agent, _ = transition
    print(f"\n   📋 Block transition: {stage} → {next_stage} ({next_agent})")

    # Step 3: Build handoff message
    handoff_msg = build_handoff_message(version, stage, next_stage, next_agent, notes, artifact)

    # Step 4: Wake the fix agent
    print(f"\n   🔔 Waking {next_agent} for block fix...")
    wake_result = wake_agent(next_agent, handoff_msg, timeout=AGENT_WAKE_TIMEOUT)

    if wake_result['success']:
        print(f"   ✅ {next_agent} responded")
    else:
        print(f"   ⚠️  Wake failed: {wake_result.get('error', 'unknown')}")
        if AGENT_WAKE_RETRIES > 0:
            print(f"   🔄 Retrying...")
            time.sleep(3)
            wake_result = wake_agent(next_agent, handoff_msg, timeout=AGENT_WAKE_TIMEOUT + 30)
            if not wake_result['success']:
                print(f"   ❌ {next_agent} failed to respond after retry")

    # Write handoff record
    write_handoff(version, stage, next_stage, next_agent, wake_result)

    if not wake_result['success']:
        send_orchestrator_notification(
            version,
            f"⚠️ Block handoff issue",
            f"Stage <code>{stage}</code> BLOCKED by {agent}, "
            f"but <b>{next_agent}</b> did not confirm pickup. "
            f"Error: {wake_result.get('error', 'unknown')}"
        )

    return wake_result['success']


def orchestrate_start(version: str, stage: str, agent: str, notes: str = ''):
    """Start a stage — just pass through to pipeline_update.py."""
    update_args = [version, 'start', stage, '--agent', agent]
    if notes:
        update_args.extend(['--notes', notes])
    success, output = run_pipeline_update(update_args)
    print(output)
    return success


def orchestrate_status(version: str, new_status: str):
    """Set pipeline status — pass through to pipeline_update.py."""
    success, output = run_pipeline_update([version, 'status', new_status])
    print(output)
    return success


def orchestrate_show(version: str):
    """Show pipeline state — pass through to pipeline_update.py."""
    success, output = run_pipeline_update([version, 'show'])
    print(output)
    return success


def check_pending():
    """Check all pipelines for stuck/unverified handoffs."""
    pending = get_pending_handoffs()

    if not pending:
        print("✅ No pending handoffs — all clear")
        return True

    print(f"\n⚠️  {len(pending)} pending handoff(s):\n")
    all_ok = True

    for h in pending:
        version = h.get('version', '?')
        next_agent = h.get('next_agent', '?')
        next_stage = h.get('next_stage', '?')
        ts = h.get('timestamp', '?')[:19]
        path = h.get('_path', '')

        print(f"   📦 {version}: {next_stage} → {next_agent}")
        print(f"      Timestamp: {ts}")
        print(f"      Wake status: {h.get('wake_result', {}).get('status', '?')}")

        # Check if the agent has been active since the handoff
        sessions = check_sessions(next_agent)
        if sessions:
            latest = max(sessions, key=lambda s: s.get('updatedAt', 0))
            updated_at = latest.get('updatedAt', 0) / 1000
            handoff_ts = datetime.fromisoformat(h['timestamp']).timestamp()
            if updated_at > handoff_ts:
                print(f"      ✅ Agent active since handoff — marking verified")
                mark_handoff_verified(path)
            else:
                print(f"      ❌ Agent NOT active since handoff — may need re-dispatch")
                all_ok = False

                # Offer to re-dispatch
                print(f"      💡 Re-dispatch with:")
                print(f"         python3 scripts/pipeline_orchestrate.py {version} verify")
        else:
            print(f"      ❓ Could not check agent sessions")
            all_ok = False

        print()

    return all_ok


def orchestrate_verify(version: str):
    """Verify and retry any pending handoffs for a specific pipeline."""
    pending = [h for h in get_pending_handoffs() if h.get('version') == version]

    if not pending:
        print(f"✅ No pending handoffs for {version}")
        return True

    print(f"\n🔍 Verifying {len(pending)} handoff(s) for {version}...\n")

    for h in pending:
        next_agent = h.get('next_agent', '')
        next_stage = h.get('next_stage', '')
        completed_stage = h.get('completed_stage', '')
        path = h.get('_path', '')

        # Check if agent has been active
        sessions = check_sessions(next_agent)
        if sessions:
            latest = max(sessions, key=lambda s: s.get('updatedAt', 0))
            updated_at = latest.get('updatedAt', 0) / 1000
            handoff_ts = datetime.fromisoformat(h['timestamp']).timestamp()
            if updated_at > handoff_ts:
                print(f"   ✅ {next_agent} active since handoff — marking verified")
                mark_handoff_verified(path)
                continue

        # Agent hasn't picked up — retry
        print(f"   🔄 Re-dispatching to {next_agent} for {next_stage}...")
        handoff_msg = build_handoff_message(
            version, completed_stage, next_stage, next_agent,
            f"[RETRY] Original handoff was not picked up. Please process {next_stage}."
        )
        wake_result = wake_agent(next_agent, handoff_msg)
        if wake_result['success']:
            print(f"   ✅ {next_agent} responded on retry")
            mark_handoff_verified(path)
        else:
            print(f"   ❌ {next_agent} still not responding: {wake_result.get('error')}")
            send_orchestrator_notification(
                version,
                f"❌ Handoff retry failed",
                f"<b>{next_agent}</b> not responding for <code>{next_stage}</code>. Manual intervention needed."
            )

    return True


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def parse_flags(argv):
    """Parse --flag value pairs from argv."""
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


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Global flag: --check-pending
    if sys.argv[1] == '--check-pending':
        check_pending()
        return

    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    version = sys.argv[1]
    action = sys.argv[2]
    flags, positional = parse_flags(sys.argv[3:])

    if action == 'show':
        orchestrate_show(version)

    elif action == 'complete':
        stage = positional[0] if positional else flags.get('stage')
        notes = flags.get('notes', positional[1] if len(positional) > 1 else '')
        agent = flags.get('agent', positional[2] if len(positional) > 2 else 'unknown')
        if not stage:
            print("Usage: pipeline_orchestrate.py <version> complete <stage> --agent <role> --notes <text>")
            sys.exit(1)
        orchestrate_complete(version, stage, agent, notes)

    elif action == 'block':
        stage = positional[0] if positional else flags.get('stage')
        notes = flags.get('notes', positional[1] if len(positional) > 1 else '')
        agent = flags.get('agent', positional[2] if len(positional) > 2 else 'unknown')
        artifact = flags.get('artifact', '')
        if not stage:
            print("Usage: pipeline_orchestrate.py <version> block <stage> --agent <role> --notes <text> [--artifact file.md]")
            sys.exit(1)
        orchestrate_block(version, stage, agent, notes, artifact)

    elif action == 'start':
        stage = positional[0] if positional else flags.get('stage')
        agent = flags.get('agent', positional[1] if len(positional) > 1 else 'unknown')
        notes = flags.get('notes', '')
        if not stage:
            print("Usage: pipeline_orchestrate.py <version> start <stage> --agent <role>")
            sys.exit(1)
        orchestrate_start(version, stage, agent, notes)

    elif action == 'status':
        new_status = positional[0] if positional else flags.get('status')
        if not new_status:
            print("Usage: pipeline_orchestrate.py <version> status <new_status>")
            sys.exit(1)
        orchestrate_status(version, new_status)

    elif action == 'verify':
        orchestrate_verify(version)

    else:
        print(f"Unknown action: {action}")
        print("Actions: show, complete, block, start, status, verify")
        print("Global: --check-pending")
        sys.exit(1)


if __name__ == '__main__':
    main()
