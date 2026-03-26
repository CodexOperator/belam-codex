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
  python3 scripts/pipeline_orchestrate.py <version> complete-task --agent <role> --notes "reason"
  python3 scripts/pipeline_orchestrate.py <version> verify   # Check if pending handoff was picked up
  python3 scripts/pipeline_orchestrate.py --check-pending     # Check ALL pipelines for stuck handoffs

  complete-task: Architect declares task fully done. Archives pipeline + marks parent task done.
                 Use at any human gate (p1_complete, p2_complete, etc.) when no further work is needed.

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
BUILDS_DIR = WORKSPACE / 'pipeline_builds'
RESEARCH_BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
PIPELINES_DIR = WORKSPACE / 'pipelines'


def resolve_build_path(version: str, artifact: str, write: bool = False) -> Path:
    """Resolve a pipeline build artifact path.
    
    Checks subdirectory first (pipeline_builds/{version}/{artifact}),
    then legacy flat path (pipeline_builds/{version}_{artifact}).
    If write=True and neither exists, returns subdirectory path (new convention).
    """
    for d in (BUILDS_DIR, RESEARCH_BUILDS_DIR):
        subdir = d / version / artifact
        if subdir.exists():
            return subdir
        flat = d / f'{version}_{artifact}'
        if flat.exists():
            return flat
    # Not found — return new convention path for writes
    path = BUILDS_DIR / version / artifact
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path
HANDOFFS_DIR = WORKSPACE / 'pipelines' / 'handoffs'
OPENCLAW_CONFIG = Path(os.path.expanduser('~/.openclaw/openclaw.json'))

# How long to wait for agent to respond (seconds)
# Opus gets 10 minutes per session. If it times out, checkpoint-and-resume kicks in.
AGENT_WAKE_TIMEOUT = 600
# Max checkpoint-and-resume cycles before giving up and alerting
AGENT_MAX_RESUMES = 5
# Retry once if first attempt fails (non-timeout failures only)
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

    # Build git diff section (changes since this agent's last session)
    diff_section = ''
    try:
        from handoff_diff import build_handoff_diff
        diff_section = build_handoff_diff(version, next_agent)
    except Exception as e:
        print(f"   ⚠️  handoff_diff failed (non-fatal): {e}")

    agent_info = AGENT_INFO.get(next_agent, {})
    knowledge_file = agent_info.get('knowledge', '')

    # Determine the design/review file to read based on pipeline type and phase
    is_analysis = 'analysis' in version or 'analysis' in completed_stage
    # Detect phase from BOTH completed and next stage (phase1_complete → phase2_architect_design is Phase 2)
    phase2_signal = 'phase2' in completed_stage or 'phase2' in next_stage
    phase3_signal = 'phase3' in completed_stage or 'phase3' in next_stage
    phase = 2 if phase2_signal else (3 if phase3_signal else 1)

    # Build file references
    files_to_read = [
        f'research/AGENT_SOUL.md',
    ]
    if knowledge_file:
        files_to_read.append(knowledge_file)
    if is_analysis:
        files_to_read.append('research/ANALYSIS_AGENT_ROLES.md')

    # Add Phase 2 direction file if this is a Phase 2 transition
    if phase == 2:
        direction_found = False
        for dname in (f'{version}_phase2_direction.md', f'{version}_phase2_shael_direction.md'):
            # Check both workspace pipeline_builds/ and research pipeline_builds/
            for base_dir, prefix in ((BUILDS_DIR, 'pipeline_builds'),
                                      (RESEARCH_BUILDS_DIR, 'machinelearning/snn_applied_finance/research/pipeline_builds')):
                dpath = base_dir / dname
                if dpath.exists():
                    files_to_read.append(f'{prefix}/{dname}')
                    direction_found = True
                    break
            if direction_found:
                break
        # Also include the task file for context
        task_file = WORKSPACE / 'tasks' / f'{version}.md'
        if task_file.exists():
            files_to_read.append(f'tasks/{version}.md')

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

    # Add reasoning flag for local analysis stages
    is_local_analysis = 'local_analysis' in next_stage
    reasoning_block = ""
    if is_local_analysis:
        reasoning_block = """
⚠️ **REASONING REQUIRED** — Use extended thinking for this task. Think deeply about
the statistical patterns, architecture implications, and what additional analysis
would reveal. Quality of insight matters more than speed.
"""

    msg = f"""🔄 Pipeline Handoff — {version}

**Stage completed:** {completed_stage}
**Your task:** {next_stage}
**Summary:** {notes}
{reasoning_block}
⚠️ **IMPORTANT — Session Protocol:**
This is a FRESH session. You have no prior context except your memory files.
1. Read your memory files first: `memory/` directory in your workspace
2. Read the files listed below for pipeline context
3. Do your work for THIS pipeline only (one pipeline per session)
4. **Before calling the orchestrator to complete/block**, crystallize what you learned:
   - Write key decisions, patterns, and lessons to your `memory/$(date -u +%Y-%m-%d).md`
   - Include: what worked, what didn't, architectural insights, things to remember
   - This is your continuity — next session starts fresh, your memory files are all you keep
   - **Create primitives for SIGNIFICANT findings only** (not routine stage completions — pipeline tracking is automatic):
     ```bash
     # Only for genuine insights, surprising findings, or architectural discoveries:
     python3 /home/ubuntu/.openclaw/workspace/scripts/log_memory.py \
       --workspace /home/ubuntu/.openclaw/workspace \
       --importance 3 \
       --tags "instance:{next_agent},pipeline:{version}" \
       "Description of the insight (not just 'completed stage X')"

     # If you discovered a reusable lesson (slug = short-hyphenated-name):
     python3 /home/ubuntu/.openclaw/workspace/scripts/create_primitive.py lesson <slug> \
       --tags "instance:{next_agent},<relevant_tags>" \
       --set "status=active"
     ```

**Pipeline files:**
{files_list}
{diff_section}
Read the diff to see what specifically changed since your last session. Feel free to read the other files for the full picture.

**Pipeline state:** `python3 scripts/pipeline_update.py {version} show`

**When you finish, call the orchestrator (it auto-saves your memory):**
```
python3 scripts/pipeline_orchestrate.py {version} complete {next_stage} --agent {next_agent} --notes "your summary" --learnings "key decisions, patterns discovered, insights worth keeping"
```

The `--learnings` flag is written directly to your memory files before the handoff — this is your continuity across sessions. Be specific about what you'd want to know next time you wake up fresh.

If you need to BLOCK, use:
```
python3 scripts/pipeline_orchestrate.py {version} block {next_stage} --agent {next_agent} --notes "BLOCK reason" --artifact your_review_file.md --learnings "what I found, why it's blocked, what the fix should look like"
```

Stage transitions are posted to the group chat automatically by the orchestrator script. You can post additional updates if you have something worth sharing."""

    # Only architects can declare a task fully complete — critics decide block vs pass-to-architect
    if next_agent == 'architect':
        msg += f"""

If the task is **fully complete** and needs no further pipeline phases, use:
```
python3 scripts/pipeline_orchestrate.py {version} complete-task --agent architect --notes "Task complete — reason"
```
This archives the pipeline and marks the parent task as done. Use this when the implementation
fully satisfies the task requirements and no Phase 2/3 is needed."""

    return msg


def build_continue_message(version: str, completed_stage: str, next_stage: str,
                            next_agent: str, notes: str, artifact: str = '') -> str:
    """Build a lightweight handoff message for continue-session mode.

    Used for both block-fix dispatches (critic→builder/architect) and re-review
    pings (builder/architect→critic) within a block cycle. The agent already has
    full context from their previous session — they just need the update and a diff.
    """
    diff_section = ''
    try:
        from handoff_diff import build_handoff_diff
        diff_section = build_handoff_diff(version, next_agent)
    except Exception as e:
        print(f"   ⚠️  handoff_diff failed (non-fatal): {e}")

    artifact_line = ''
    if artifact:
        artifact_line = f'\n**Review artifact:** `research/pipeline_builds/{artifact}`\n'

    # Detect whether this is a block-fix or a re-review
    is_block_fix = 'fix_blocks' in next_stage
    if is_block_fix:
        header = '🚫 BLOCK — Critic sent your work back for fixes'
        action_verb = 'Address the blocks'
    else:
        header = '🔄 Re-review — Fixes submitted, please re-review'
        action_verb = 'Review the changes'

    msg = f"""{header}

**Pipeline:** {version}
**Completed stage:** {completed_stage}
**Your task:** {next_stage}
**Notes:** {notes}
{artifact_line}
You still have full context from your previous session. {action_verb} and complete:

```
python3 scripts/pipeline_orchestrate.py {version} complete {next_stage} --agent {next_agent} --notes "summary" --learnings "key observations"
```

If you need to BLOCK, use:
```
python3 scripts/pipeline_orchestrate.py {version} block {next_stage} --agent {next_agent} --notes "BLOCK reason" --artifact your_review_file.md --learnings "findings"
```
{diff_section}"""

    return msg


# ═══════════════════════════════════════════════════════════════════════
# Agent wake via `openclaw agent` CLI
# ═══════════════════════════════════════════════════════════════════════

def reset_agent_session(agent: str) -> str | None:
    """
    Reset an agent's session via gateway, giving it a fresh context.
    
    Resets BOTH the main session (used by `openclaw agent` CLI) and the
    group session (used by Telegram group messages). This ensures the agent
    starts completely fresh with no accumulated context from prior pipelines.
    
    Returns the new main session ID, or None on failure.
    """
    new_id = None
    
    # Reset both session types — main (CLI) and group (Telegram)
    session_keys = [
        f'agent:{agent}:main',                                    # CLI session
        f'agent:{agent}:telegram:group:{PIPELINE_GROUP_CHAT_ID}', # Group session
    ]
    
    for session_key in session_keys:
        try:
            result = subprocess.run(
                ['openclaw', 'gateway', 'call', 'sessions.reset',
                 '--json', '--params', json.dumps({'key': session_key})],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get('ok'):
                    sid = data.get('entry', {}).get('sessionId', '')
                    print(f"   🔄 Session reset [{session_key}]: {sid[:8]}...")
                    if 'main' in session_key:
                        new_id = sid
                else:
                    # Session might not exist yet — that's fine
                    err = data.get('error', '')
                    if 'not found' not in str(err).lower():
                        print(f"   ⚠️  Session reset [{session_key}]: {err}")
        except Exception as e:
            print(f"   ⚠️  Session reset failed [{session_key}]: {e}")
    
    return new_id


def generate_session_id(version: str, agent: str) -> str:
    """Generate a fresh unique session ID for each pipeline+agent interaction.
    
    Each handoff gets a brand new session — agents start fresh every time,
    relying on their persisted memory files for continuity rather than
    session context. This prevents stale context buildup and ensures
    each interaction begins clean.
    """
    import uuid
    return str(uuid.uuid4())



def wake_agent(agent: str, message: str, timeout: int = AGENT_WAKE_TIMEOUT,
               session_id: str = None) -> dict:
    """
    [LEGACY — blocking dispatch. Use fire_and_forget_dispatch() in orchestration_engine.py instead.]

    Wake a target agent by injecting a message via `openclaw agent` CLI.
    Blocks for up to `timeout` seconds waiting for the agent to respond.
    The new architecture uses subprocess.Popen (non-blocking) and detects
    completion via agent_end telemetry (check_completions() event loop).

    This function is kept for fallback compatibility only.
    Uses --session-id for isolated per-pipeline sessions when provided.
    Returns {success, response, session_id, error}.
    """
    cmd = [
        'openclaw', 'agent',
        '--agent', agent,
        '--message', message,
        '--timeout', str(timeout),
        '--json',
    ]
    if session_id:
        cmd.extend(['--session-id', session_id])

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


AGENT_WORKSPACES = {
    'architect': Path(os.path.expanduser('~/.openclaw/workspace-architect')),
    'critic': Path(os.path.expanduser('~/.openclaw/workspace-critic')),
    'builder': Path(os.path.expanduser('~/.openclaw/workspace-builder')),
    'belam-main': WORKSPACE,
}


def consolidate_agent_memory(agent: str, version: str, stage: str, notes: str,
                              learnings: str = '') -> bool:
    """No-op — daily log writing retired per decision/retire-daily-log-writers-extraction-only.

    Pipeline stage transitions are tracked in pipeline .md files and _state.json.
    Memory extraction (sage) handles lesson/decision creation from session transcripts.
    Kept as stub so callers don't break.
    """
    return True


def checkpoint_and_resume(agent: str, version: str, stage: str, notes: str,
                           resume_count: int = 0) -> dict:
    """
    Checkpoint-and-resume: when an agent times out mid-work.
    
    1. Scan the agent's workspace for any partial artifacts produced
    2. Write a checkpoint summary to the agent's memory
    3. Wake the agent again with a fresh session + resume context
    
    Returns the final wake_result from the last attempt.
    """
    print(f"\n   ⏱️  CHECKPOINT-AND-RESUME (attempt {resume_count + 1}/{AGENT_MAX_RESUMES})")

    workspace = AGENT_WORKSPACES.get(agent)
    builds_dir = BUILDS_DIR

    # Step 1: Detect partial work — check for files modified in the last 12 minutes
    partial_files = []
    cutoff = time.time() - 720  # 12 min window
    if builds_dir.exists():
        for f in builds_dir.iterdir():
            if version.replace('-', '_') in f.name.replace('-', '_') and f.stat().st_mtime > cutoff:
                partial_files.append(f.name)

    # Also check the agent's workspace memory for recent writes
    if workspace:
        memory_dir = workspace / 'memory'
        if memory_dir.exists():
            for f in memory_dir.iterdir():
                if f.is_file() and f.stat().st_mtime > cutoff:
                    partial_files.append(f'memory/{f.name}')

    # Step 2: Write checkpoint to agent's memory
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    now = datetime.now(timezone.utc).strftime('%H:%M UTC')

    checkpoint_notes = (
        f"Session timed out while working on {version}/{stage} "
        f"(attempt {resume_count + 1}). "
        f"Partial files detected: {', '.join(partial_files) if partial_files else 'none found'}. "
        f"A fresh session will continue this work."
    )
    consolidate_agent_memory(agent, version, f'{stage}_checkpoint_{resume_count + 1}',
                              checkpoint_notes)
    print(f"   💾 Checkpoint written to {agent}'s memory")

    # Step 3: Build resume message with context about what was already done
    partial_context = ""
    if partial_files:
        partial_context = f"""
**Partial work from previous session(s):**
The following files were created/modified — READ THEM FIRST to avoid redoing work:
{chr(10).join(f'  - {f}' for f in partial_files)}
"""

    resume_msg = f"""🔄 RESUME — Pipeline {version} / Stage: {stage}
Attempt {resume_count + 2} of {AGENT_MAX_RESUMES + 1} (previous session timed out)

⚠️ This is a FRESH session — you have NO context from the previous attempt.
Read your memory files first: they contain a checkpoint of what happened.

**Your task:** Complete {stage} for pipeline {version}
**Original context:** {notes}
{partial_context}
**Critical:** Read your memory/$(date -u +%Y-%m-%d).md FIRST — it has your checkpoint.
Then check what files already exist in research/pipeline_builds/ for this pipeline.
Continue from where the previous session left off. Don't redo completed work.

**When you finish (orchestrator auto-saves your memory):**
```
python3 scripts/pipeline_orchestrate.py {version} complete {stage} --agent {agent} --notes "your summary" --learnings "key insights"
```
"""

    # Step 4: Fire-and-forget dispatch with resume context
    print(f"   🔔 Dispatching {agent} with resume context (fire-and-forget)...")
    result = fire_and_forget_dispatch(version, stage, agent, message=resume_msg)
    if result.get('success'):
        print(f"   🔔 Dispatched {agent} (fire-and-forget)")
    else:
        print(f"   ⚠️ Dispatch failed: {result.get('error')}")
    return {'success': result.get('success', False), 'status': 'dispatched', 'session_id': ''}


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
                  next_agent: str, wake_result: dict,
                  pipeline_session_id: str = ''):
    """Write a handoff record for later verification."""
    HANDOFFS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    handoff = {
        'version': version,
        'completed_stage': completed_stage,
        'next_stage': next_stage,
        'next_agent': next_agent,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'pipeline_session_id': pipeline_session_id,
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
    """DISABLED — was sending via architect's bot token for orchestrator-level events.
    notify_group() in pipeline_update.py handles per-agent notifications instead.
    Kept as no-op so callers don't break."""
    pass


# ═══════════════════════════════════════════════════════════════════════
# Import stage transition maps from pipeline_update.py
# ═══════════════════════════════════════════════════════════════════════

# We import these dynamically to stay in sync
sys.path.insert(0, str(Path(__file__).parent))
try:
    from pipeline_update import STAGE_TRANSITIONS, BLOCK_TRANSITIONS
except ImportError:
    print("❌ Cannot import from pipeline_update.py — ensure it exists at scripts/pipeline_update.py")
    sys.exit(1)

def fire_and_forget_dispatch(version, stage, agent, message=''):
    """Lazy wrapper to avoid circular import with orchestration_engine."""
    from orchestration_engine import fire_and_forget_dispatch as _dispatch
    return _dispatch(version, stage, agent, message=message)


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


def orchestrate_complete(version: str, stage: str, agent: str, notes: str,
                          learnings: str = ''):
    """Complete a stage and orchestrate the handoff to the next agent."""
    print(f"\n{'═' * 70}")
    print(f"  🔄 ORCHESTRATOR: {version} — completing {stage}")
    print(f"{'═' * 70}\n")

    # Step 0: Consolidate calling agent's memory BEFORE anything else
    print(f"   💾 Consolidating {agent}'s memory...")
    consolidate_agent_memory(agent, version, stage, notes, learnings)

    # Step 0.5: Snapshot git commits for handoff diff context
    try:
        from handoff_diff import snapshot_handoff_commits
        snap = snapshot_handoff_commits(version, stage, agent)
        ws_hash = snap.get('commits', {}).get('workspace', '?')[:8]
        ml_hash = snap.get('commits', {}).get('machinelearning', '?')[:8]
        print(f"   📸 Git snapshot: ws={ws_hash} ml={ml_hash}")
    except Exception as e:
        print(f"   ⚠️  Git snapshot failed (non-fatal): {e}")
    print()

    # Step 1: Run pipeline_update.py (state + markdown + telegram notification)
    update_args = [version, 'complete', stage, '--agent', agent]
    if notes:
        update_args.extend(['--notes', notes])
    success, output = run_pipeline_update(update_args)
    print(output)
    if not success:
        print(f"\n❌ pipeline_update.py failed — aborting handoff")
        return False

    # Step 1.5 (D9): Check if verification stage needs retry instead of advancing
    verification_result = check_verification_result(version, stage, notes)
    if verification_result == 'retry':
        print(f"\n   🔄 Verification RED — re-dispatching builder (auto-retry)...")
        result = dispatch_verification(version)
        if result.get('success'):
            print(f"   🔔 Re-dispatched builder for retry #{result.get('retry_count', '?')}")
        else:
            print(f"   ⚠️ Re-dispatch failed: {result.get('error')}")
        print(f"\n{'─' * 70}")
        print(f"  📊 Orchestration Summary:")
        print(f"     Pipeline:    {version}")
        print(f"     Completed:   {stage} ({agent}) — RED")
        print(f"     Action:      🔄 Auto-retry dispatch")
        print(f"{'─' * 70}\n")
        return result.get('success', False)
    elif verification_result == 'exhausted':
        print(f"\n   🚨 Verification exhausted {VERIFICATION_MAX_RETRIES} retries — "
              f"escalating to coordinator")
        escalate_verification_failure(version, load_pipeline_state(version))
        return False

    # Step 2: Determine next agent from transition map (template-aware)
    from pipeline_update import get_transitions_for_pipeline
    stage_trans, block_trans, _, _ = get_transitions_for_pipeline(version)
    transition = stage_trans.get(stage)

    # Phase gate handling: human gates (p1_complete, p2_complete, etc.) have
    # transitions defined in templates but are gated. When kicked off via
    # orchestrate_complete, the transition fires normally.
    # Legacy gate names are resolved via template_parser.resolve_stage_name().
    if not transition and '_complete' in stage:
        # Try resolving via legacy stage name mapping
        try:
            from template_parser import resolve_stage_name
            resolved = resolve_stage_name(stage, stage_trans)
            if resolved != stage:
                transition = stage_trans.get(resolved)
                if transition:
                    print(f"   📋 Resolved legacy stage '{stage}' → '{resolved}'")
        except ImportError:
            pass

    if not transition and '_complete' in stage:
        # Check for direction files (any phase)
        direction_note = ''
        import re as _re
        phase_match = _re.search(r'p(\d+)_complete|phase(\d+)_complete', stage)
        phase_n = int(phase_match.group(1) or phase_match.group(2)) if phase_match else None
        next_phase = (phase_n or 1) + 1
        for fname in (f'{version}_phase{next_phase}_direction.md',
                      f'{version}_phase{next_phase}_shael_direction.md',
                      f'{version}_phase2_direction.md',
                      f'{version}_phase2_shael_direction.md'):
            for loc, prefix in ((BUILDS_DIR, 'pipeline_builds'),
                                (RESEARCH_BUILDS_DIR, 'machinelearning/snn_applied_finance/research/pipeline_builds')):
                if (loc / fname).exists():
                    direction_note = f' Read direction at {prefix}/{fname}.'
                    break
            if direction_note:
                break

        # Auto-complete on clean critic pass (0 BLOCKs, 0 FLAGs of any severity)
        # Only when the template opts in via auto_complete_on_clean_pass: true
        if phase_n and not direction_note:
            try:
                from template_parser import parse_template
                import re as _re_tpl
                # Resolve template name from pipeline type (same logic as pipeline_update)
                _pf = PIPELINES_DIR / f'{version}.md'
                _ptype = None
                if _pf.exists():
                    _m = _re_tpl.search(r'^type:\s*(.+)$', _pf.read_text(errors='replace'), _re_tpl.MULTILINE)
                    if _m:
                        _ptype = _m.group(1).strip()
                _tpl_map = {'research': 'research', 'infrastructure': 'research', 'builder-first': 'builder-first'}
                _tpl_name = _tpl_map.get(_ptype, 'research') if _ptype else 'research'
                tpl = parse_template(_tpl_name)
                auto_clean = tpl.get('auto_complete_on_clean_pass', False) if tpl else False
            except Exception:
                auto_clean = False

            if auto_clean:
                # Look for critic review and check for clean pass (0 blocks, 0 flags)
                import re as _re2
                clean_pass = False
                for loc in (BUILDS_DIR, RESEARCH_BUILDS_DIR):
                    for suffix in ('_critic_review.md', '_critic_code_review.md'):
                        candidate = loc / f'{version}{suffix}'
                        if candidate.exists():
                            review_text = candidate.read_text()
                            if 'APPROVED' not in review_text:
                                break
                            # Check all FLAG counts are 0
                            # Verdict format: "0 BLOCKs, 0 HIGH FLAGs, 0 MED FLAG, 0 LOW FLAGs"
                            # or simpler: "0 BLOCKs, 0 FLAGs"
                            flag_counts = _re2.findall(
                                r'(\d+)\s+(?:HIGH\s+|MED\s+|LOW\s+)?FLAG', review_text)
                            block_counts = _re2.findall(r'(\d+)\s+BLOCK', review_text)
                            if (block_counts and all(int(c) == 0 for c in block_counts)
                                    and flag_counts and all(int(c) == 0 for c in flag_counts)):
                                clean_pass = True
                            break
                    if clean_pass:
                        break

                if clean_pass:
                    print(f"\n   ✅ Phase {phase_n} critic: clean pass (0 blocks, 0 flags) "
                          f"→ auto-completing task (auto_complete_on_clean_pass)")
                    return orchestrate_complete_task(version, agent='system',
                        notes=f'Auto-completed: critic clean pass at {stage} '
                              f'(0 blocks, 0 flags). Template: auto_complete_on_clean_pass.')

        # Auto-complete logic: only at p3_complete (architect had 3 chances to call complete-task)
        # At p1_complete and p2_complete, architect reviews and decides — don't auto-complete
        if phase_n and phase_n >= 3 and not direction_note:
            # Three phases done. Check Phase 3 critic review — if approved, auto-complete.
            critic_approved = False
            for loc in (BUILDS_DIR, RESEARCH_BUILDS_DIR):
                for suffix in ('_critic_review.md', '_critic_code_review.md'):
                    candidate = loc / f'{version}{suffix}'
                    if candidate.exists():
                        review_text = candidate.read_text()
                        if 'APPROVED' in review_text and '0 BLOCK' in review_text:
                            critic_approved = True
                        break
                if critic_approved:
                    break

            if critic_approved:
                print(f"\n   ✅ Phase {phase_n} critic approved, architect did not call complete-task "
                      f"after {phase_n} phases → auto-completing task")
                return orchestrate_complete_task(version, agent='system',
                    notes=f'Auto-completed after {phase_n} phases: critic approved at {stage}, '
                          f'architect did not call complete-task')
            else:
                # Critic blocked at p3+ — check loop count (capped at 1 retry)
                p3_state = load_pipeline_state(version)
                p3_loop_count = p3_state.get('p3_loop_count', 0)
                if p3_loop_count >= 1:
                    # Already looped once — something is catastrophically wrong. Stop.
                    print(f"\n   🚨 Critic blocked at p3 after {p3_loop_count} loop(s) — "
                          f"capping here. Auto-completing with warning.")
                    return orchestrate_complete_task(version, agent='system',
                        notes=f'Auto-completed after p3 loop cap ({p3_loop_count} retries). '
                              f'Critic still blocking — needs manual review.')
                else:
                    # First loop — retry once
                    p3_state['p3_loop_count'] = p3_loop_count + 1
                    save_pipeline_state(version, p3_state)
                    print(f"\n   🔄 Critic blocked at phase {phase_n} — looping back to "
                          f"p3_architect_design (loop {p3_loop_count + 1}/1)")
                    transition = (f'p3_architect_design', 'architect',
                                  f'Phase {phase_n} critic had issues. Re-entering at p3 to address blocks. '
                                  f'Review the critic report and design fixes. '
                                  f'Call complete-task if the remaining issues are acceptable.')
        elif direction_note:
            # Direction file found → construct next-phase transition
            transition = (f'p{next_phase}_architect_design', 'architect',
                          f'Phase {next_phase} approved.{direction_note} Design Phase {next_phase} changes.')
        else:
            # p1_complete or p2_complete with no direction — let architect review
            # Construct generic next-phase transition (architect will call complete-task if done)
            transition = (f'p{next_phase}_architect_design', 'architect',
                          f'Phase {next_phase} — review critic report and either call complete-task '
                          f'or write phase {next_phase} direction.')

    if not transition:
        print(f"\n   ℹ️  No auto-transition for '{stage}' — no handoff needed")
        return True

    next_stage, next_agent = transition[0], transition[1]
    session_mode = transition[3] if len(transition) > 3 else 'fresh'
    print(f"\n   📋 Transition: {stage} → {next_stage} ({next_agent}) [session: {session_mode}]")

    # Special case: local_analysis_code_review → report build (process stage, not agent)
    if stage == 'local_analysis_code_review':
        print(f"\n   📄 Analysis approved — triggering LaTeX report build...")
        return orchestrate_report_build(version)

    # Special case: local_analysis_report_build → local_analysis_complete (HUMAN GATE)
    # local_analysis_complete is a terminal stage. Phase 2 requires explicit human approval.
    if stage == 'local_analysis_report_build':
        print(f"\n   ✅ Report build complete — local analysis done")
        # Update stage to local_analysis_complete
        run_pipeline_update([
            version, 'complete', 'local_analysis_complete',
            '--agent', 'system',
            '--notes', 'Local analysis complete. Awaiting human review for Phase 2.'
        ])
        # Notify coordinator that human approval is needed
        send_orchestrator_notification(version, '📊 Local analysis complete',
            f'<b>{version}</b> local analysis is complete with PDF report. '
            f'Awaiting Phase 2 approval to proceed.\n'
            f'Approve: <code>R kickoff {version} --phase2 [--direction file.md]</code>')
        return True

    # Step 3: Build handoff message — lightweight for continue, full for fresh
    if session_mode == 'continue':
        handoff_msg = build_continue_message(version, stage, next_stage, next_agent, notes)
    else:
        handoff_msg = build_handoff_message(version, stage, next_stage, next_agent, notes)

    # Step 3.5: Session mode — fresh resets the agent session, continue reuses it
    if session_mode == 'fresh':
        print(f"   🔄 Resetting {next_agent} session for fresh context...")
        reset_agent_session(next_agent)
        pipeline_session_id = generate_session_id(version, next_agent)
    else:
        # 'continue' — reuse existing session, skip reset
        pipeline_session_id = None
        print(f"   🔄 Session mode: continue — reusing existing agent session")

    # Write preliminary handoff record (updated after dispatch)
    pre_wake_result = {
        'success': True,
        'status': 'dispatching',
        'response': '',
        'session_id': '',
        'error': None,
    }
    handoff_path = write_handoff(version, stage, next_stage, next_agent, pre_wake_result,
                                  pipeline_session_id or '')
    print(f"\n   📝 Handoff record: {handoff_path.relative_to(WORKSPACE)}")

    # Step 4: Fire-and-forget dispatch to next agent
    # Use verification dispatch for verification stages (includes wiggum steer timer)
    VERIFICATION_STAGES = {'builder_verification', 'phase2_builder_verification',
                           'p1_builder_verify', 'p2_builder_verify', 'p3_builder_verify'}
    if next_stage in VERIFICATION_STAGES:
        print(f"\n   🔔 Dispatching {next_agent} for VERIFICATION (with wiggum steer)...")
        result = dispatch_verification(version)
    else:
        print(f"\n   🔔 Dispatching {next_agent} (fire-and-forget, session: {session_mode})...")
        result = fire_and_forget_dispatch(version, next_stage, next_agent, message=handoff_msg)
    if result.get('success'):
        print(f"   🔔 Dispatched {next_agent} (fire-and-forget)")
    else:
        print(f"   ⚠️ Dispatch failed: {result.get('error')}")

    # Summary
    print(f"\n{'─' * 70}")
    print(f"  📊 Orchestration Summary:")
    print(f"     Pipeline:    {version}")
    print(f"     Completed:   {stage} ({agent})")
    print(f"     Next:        {next_stage} ({next_agent})")
    print(f"     Session:     {session_mode}")
    print(f"     Handoff:     🔔 Fire-and-forget dispatch (PID: {result.get('pid')})")
    print(f"     Telegram:    ✅ Group notified (via pipeline_update.py)")
    print(f"{'─' * 70}\n")

    return result.get('success', False)


def orchestrate_block(version: str, stage: str, agent: str, notes: str,
                       artifact: str = '', learnings: str = ''):
    """Block a stage and orchestrate the handoff back to the fixing agent."""
    print(f"\n{'═' * 70}")
    print(f"  🚫 ORCHESTRATOR: {version} — blocking {stage}")
    print(f"{'═' * 70}\n")

    # Step 0: Consolidate calling agent's memory BEFORE anything else
    print(f"   💾 Consolidating {agent}'s memory...")
    consolidate_agent_memory(agent, version, stage, notes, learnings)

    # Step 0.5: Snapshot git commits for handoff diff context
    try:
        from handoff_diff import snapshot_handoff_commits
        snap = snapshot_handoff_commits(version, stage, agent)
        ws_hash = snap.get('commits', {}).get('workspace', '?')[:8]
        ml_hash = snap.get('commits', {}).get('machinelearning', '?')[:8]
        print(f"   📸 Git snapshot: ws={ws_hash} ml={ml_hash}")
    except Exception as e:
        print(f"   ⚠️  Git snapshot failed (non-fatal): {e}")
    print()

    # Step 1: Run pipeline_update.py
    update_args = [version, 'block', stage, '--agent', agent, '--notes', notes]
    if artifact:
        update_args.extend(['--artifact', artifact])
    success, output = run_pipeline_update(update_args)
    print(output)
    if not success:
        print(f"\n❌ pipeline_update.py failed — aborting handoff")
        return False

    # Step 2: Determine fix agent from block transition map (template-aware)
    from pipeline_update import get_transitions_for_pipeline
    _, block_trans, _, _ = get_transitions_for_pipeline(version)
    transition = block_trans.get(stage)
    if not transition:
        print(f"\n   ℹ️  No auto-transition for blocking '{stage}' — no handoff needed")
        return True

    next_stage, next_agent = transition[0], transition[1]
    block_session_mode = transition[3] if len(transition) > 3 else 'fresh'
    print(f"\n   📋 Block transition: {stage} → {next_stage} ({next_agent}) [session: {block_session_mode}]")

    # Step 3: Session mode — fresh resets the agent session, continue reuses it
    if block_session_mode == 'fresh':
        print(f"\n   🔄 Resetting {next_agent} session for fresh context...")
        reset_agent_session(next_agent)
        pipeline_session_id = generate_session_id(version, next_agent)
    else:
        # 'continue' — reuse existing session, skip reset
        pipeline_session_id = None
        print(f"\n   🔄 Session mode: continue — reusing {next_agent}'s existing session")

    # Step 4: Build handoff message — lightweight for continue, full for fresh
    if block_session_mode == 'continue':
        handoff_msg = build_continue_message(version, stage, next_stage, next_agent, notes, artifact)
    else:
        handoff_msg = build_handoff_message(version, stage, next_stage, next_agent, notes, artifact)

    print(f"\n   🔔 Dispatching {next_agent} for block fix (fire-and-forget, session: {block_session_mode})...")
    result = fire_and_forget_dispatch(version, next_stage, next_agent, message=handoff_msg)
    if result.get('success'):
        print(f"   🔔 Dispatched {next_agent} (fire-and-forget)")
    else:
        print(f"   ⚠️ Dispatch failed: {result.get('error')}")

    # Write handoff record
    wake_result = {'success': result.get('success', False), 'status': 'dispatched', 'session_id': pipeline_session_id or ''}
    write_handoff(version, stage, next_stage, next_agent, wake_result, pipeline_session_id or '')

    return True


def orchestrate_revise(version: str, context: str, revision_num: int = None):
    """Trigger a Phase 1 revision cycle (coordinator-initiated).

    Moves a pipeline from phase1_complete back through architect→critic→builder
    with coordinator-provided revision context. Loops back to phase1_complete.

    Usage:
        python3 pipeline_orchestrate.py <version> revise --context "findings..."
        R revise <version> --context "findings..."
    """
    print(f"\n{'═' * 70}")
    print(f"  🔄 ORCHESTRATOR: {version} — triggering Phase 1 revision")
    print(f"{'═' * 70}\n")

    # Step 1: Verify pipeline is at phase1_complete
    state_file = BUILDS_DIR / f'{version}_state.json'
    if state_file.exists():
        import json
        with open(state_file) as f:
            state = json.load(f)
        pending = state.get('pending_action', '')
        if pending not in ('phase1_complete', ''):
            # Also allow revision from a previous revision_complete
            status = state.get('status', '')
            if status != 'phase1_complete' and not pending.startswith('phase1_revision'):
                print(f"   ⚠️  Pipeline {version} is at '{pending}' (status: {status})")
                print(f"   ⚠️  Revisions can only be triggered from phase1_complete")
                print(f"   ⚠️  Use 'orchestrate complete' to advance the pipeline first")
                return False

    # Step 2: Determine revision number
    if revision_num is None:
        builds_dir = BUILDS_DIR
        existing = list(builds_dir.glob(f'{version}_phase1_revision_*_architect.md'))
        revision_num = len(existing) + 1
    print(f"   📝 Revision #{revision_num}")

    # Step 3: Write revision direction file for the architect
    direction_file = BUILDS_DIR / f'{version}_phase1_revision_{revision_num:02d}_direction.md'
    direction_content = f"""# Phase 1 Revision #{revision_num} — {version}

## Coordinator Direction

{context}

## Instructions

1. Read this direction file and the existing Phase 1 design/notebook
2. Revise the architecture to address the points above
3. Write your revised design to `pipeline_builds/{version}_phase1_revision_architect.md`
4. Complete via: `python3 scripts/pipeline_orchestrate.py {version} complete phase1_revision_architect --agent architect --notes "..."`
"""
    direction_file.write_text(direction_content)
    print(f"   📄 Direction file: {direction_file.name}")

    # Step 4: Update pipeline state to revision
    success, output = run_pipeline_update([version, 'start', 'phase1_revision_architect', '--agent', 'coordinator'])
    print(output)
    if not success:
        print(f"\n❌ Failed to start revision stage")
        return False

    # Step 5: Reset architect session and dispatch
    print(f"\n   🔄 Resetting architect session for fresh context...")
    reset_agent_session('architect')

    pipeline_session_id = generate_session_id(version, 'architect')
    print(f"   🆔 Pipeline session: {pipeline_session_id[:8]}...")

    # Step 6: Build handoff message for architect
    handoff_msg = f"""🔄 PHASE 1 REVISION #{revision_num} — {version}

The coordinator has requested a revision to the Phase 1 design/implementation.

**Read first:**
1. Direction file: `machinelearning/snn_applied_finance/research/pipeline_builds/{version}_phase1_revision_{revision_num:02d}_direction.md`
2. Current Phase 1 design: `pipeline_builds/{version}_architect_design.md`
3. Current notebook (if exists)

**Your task:** Revise the architecture per the direction file. Write your updated design to:
`pipeline_builds/{version}_phase1_revision_architect.md`

**When done:**
```bash
python3 scripts/pipeline_orchestrate.py {version} complete phase1_revision_architect --agent architect --notes "revision summary"
```
"""

    # Step 7: Fire-and-forget dispatch to architect
    print(f"\n   📨 Dispatching to architect (fire-and-forget)...")
    result = fire_and_forget_dispatch(version, 'phase1_revision_architect', 'architect', message=handoff_msg)
    if result.get('success'):
        print(f"   🔔 Dispatched architect (fire-and-forget)")
    else:
        print(f"   ⚠️ Dispatch failed: {result.get('error')}")

    # Step 8: Write handoff file
    wake_result = {'success': True, 'status': 'dispatched', 'session_id': pipeline_session_id}
    write_handoff(version, 'phase1_complete', 'phase1_revision_architect', 'architect', wake_result, pipeline_session_id)

    print(f"\n   ✅ Revision #{revision_num} dispatched to architect")

    # Step 9: Notify
    send_orchestrator_notification(version, 'phase1_revision_started',
        f'Revision #{revision_num} triggered by coordinator. Architect designing.')

    return True


def orchestrate_local_run(version: str, dry_run: bool = False, max_retries: int = 2,
                           no_recovery: bool = False):
    """Launch local experiment runner for a pipeline in the background.

    This is a PROCESS stage, not an agent stage. The experiment runner
    (run_experiment.py) self-reports completion via pipeline_update.py.
    """
    print(f"\n{'═' * 70}")
    print(f"  🧪 ORCHESTRATOR: {version} — launching local experiments")
    print(f"{'═' * 70}\n")

    # Verify pipeline state
    state_file = BUILDS_DIR / f'{version}_state.json'
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
        pending = state.get('pending_action', '')
        if pending not in ('phase1_complete', 'local_experiment_running', 'local_experiment_complete', 'none', ''):
            print(f"   ⚠️  Pipeline pending_action is '{pending}', expected 'phase1_complete'")
            print(f"   Proceeding anyway (manual override)")

    # Check for already-running experiment
    pid_file = BUILDS_DIR / f'{version}_experiment.pid'
    if pid_file.exists():
        import json as _json
        pid_info = _json.loads(pid_file.read_text())
        pid = pid_info.get('pid')
        # Check if PID is still alive
        try:
            os.kill(pid, 0)
            print(f"   ⚠️  Experiment already running (PID: {pid}, started: {pid_info.get('started', '?')})")
            print(f"   Use 'kill {pid}' to stop it, or wait for completion")
            return False
        except ProcessError:
            print(f"   ℹ️  Stale PID file found (PID {pid} dead) — cleaning up")
            pid_file.unlink()
        except OSError:
            print(f"   ℹ️  Stale PID file found (PID {pid} dead) — cleaning up")
            pid_file.unlink()

    # Build command
    cmd = [
        sys.executable, str(WORKSPACE / 'scripts' / 'run_experiment.py'),
        version,
    ]
    if dry_run:
        cmd.append('--dry-run')
    if max_retries != 2:
        cmd.extend(['--max-retries', str(max_retries)])
    if no_recovery:
        cmd.append('--direct')  # Direct mode skips builder supervision

    # Launch in background
    log_dir = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'notebooks' / 'local_results' / version
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'orchestrator_launch.log'

    print(f"   📋 Command: {' '.join(cmd)}")
    print(f"   📂 Log: {log_file.relative_to(WORKSPACE)}")

    with open(log_file, 'w') as lf:
        proc = subprocess.Popen(
            cmd,
            stdout=lf, stderr=subprocess.STDOUT,
            cwd=str(WORKSPACE),
            start_new_session=True,  # Detach from parent process group
        )

    print(f"   🚀 Launched experiment runner (PID: {proc.pid})")
    print(f"   📊 Pipeline will auto-transition when experiments complete")
    print(f"   📝 Monitor: tail -f {log_file.relative_to(WORKSPACE)}")

    # Notify
    send_orchestrator_notification(version, '🧪 Experiments started',
        f'Local experiment runner launched for <b>{version}</b> (PID: {proc.pid}). '
        f'Auto-transitions to Phase 2 on completion.')

    return True


def orchestrate_local_analysis(version: str, dry_run: bool = False):
    """Orchestrate the local analysis loop for a pipeline's experiment results.

    Flow:
      1. Run analyze_local_results.py (data prep — generates MD + plots)
      2. Kick architect (with reasoning) to write preliminary analysis report
      3. Existing orchestration loop handles: architect→critic→builder→critic
         with reasoning enabled for all agents
      4. After code_review passes, spawn subagent to build LaTeX→PDF report
      5. Complete local_analysis_complete

    Returns True if analysis loop was kicked successfully.
    """
    print(f"\n{'═' * 70}")
    print(f"  📊 ORCHESTRATOR: {version} — launching local analysis")
    print(f"{'═' * 70}\n")

    results_dir = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'notebooks' / 'local_results' / version

    if not results_dir.exists():
        # Check base dir (older runs without version subdir)
        results_dir = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'notebooks' / 'local_results'

    # Step 1: Run analyze_local_results.py for data prep
    print(f"   📊 Running data analysis preparation...")
    analyze_cmd = [
        sys.executable,
        str(WORKSPACE / 'scripts' / 'analyze_local_results.py'),
        version,
        '--extra-plots',
    ]
    result = subprocess.run(analyze_cmd, capture_output=True, text=True, cwd=str(WORKSPACE), timeout=300)
    print(result.stdout)
    if result.returncode != 0:
        print(f"   ⚠️  analyze_local_results.py returned non-zero: {result.stderr[:500]}")
        print(f"   Proceeding anyway — architect can work with raw data")

    # Step 2: Update pipeline stage → local_analysis_architect
    print(f"\n   📊 Updating pipeline stage → local_analysis_architect")
    success, output = run_pipeline_update([
        version, 'start', 'local_analysis_architect',
        '--agent', 'system',
        '--notes', f'Local analysis started. Results at {results_dir.relative_to(WORKSPACE)}/'
    ])
    print(output)

    if dry_run:
        print(f"   [DRY RUN] Would wake architect with reasoning for analysis")
        return True

    # Step 3: Build the analysis handoff message (with reasoning instructions)
    analysis_md = results_dir / f'{version}_analysis.md'
    analysis_md_rel = analysis_md.relative_to(WORKSPACE) if analysis_md.exists() else 'N/A'

    # List available plots for context
    plots = sorted(results_dir.glob('*.png'))
    plots_list = '\n'.join(f'  - {p.name}' for p in plots)

    handoff_msg = f"""🔬 Local Analysis — {version}

**Your task:** local_analysis_architect
**Results directory:** {results_dir.relative_to(WORKSPACE)}/
**Pre-generated analysis:** {analysis_md_rel}

⚠️ **REASONING REQUIRED** — Use extended thinking for this task. Think deeply about:
- What the results mean for the SNN architecture
- Which patterns are statistically meaningful vs noise
- What additional analysis scripts would reveal deeper insights
- How to structure findings for maximum clarity

## Context
Experiments have completed for pipeline `{version}`. A preliminary analysis document
with statistical tables and plots has been auto-generated. Your job is to:

1. **Read the auto-generated analysis:** `{analysis_md_rel}`
2. **Read the raw results** in `{results_dir.relative_to(WORKSPACE)}/`
3. **Write a comprehensive preliminary analysis report** at:
   `{results_dir.relative_to(WORKSPACE)}/{version}_analysis_report.md`

   The report should include:
   - Executive summary with key findings and their implications
   - Detailed interpretation of each experiment category (primary, ablation, baselines)
   - Statistical significance assessment
   - Scale-performance analysis
   - Sharpe vs accuracy discrepancy analysis
   - Architecture-level insights (what the SNN is/isn't learning)
   - Specific recommendations for additional analysis scripts

4. **Specify any additional analysis scripts** needed. Write specs in your report under
   "## Additional Analysis Scripts Needed". For each script, specify:
   - What it computes
   - Input data (which pkl files, what format)
   - Expected output (plots, tables, metrics)
   - Why it matters for the analysis

5. **Save your report** and complete via orchestrator.

## Available Data
- Results pickle: `{results_dir.relative_to(WORKSPACE)}/*_results.pkl`
- Histories pickle: `{results_dir.relative_to(WORKSPACE)}/*_histories.pkl`
- Run log: `{results_dir.relative_to(WORKSPACE)}/run.log`
- Auto-generated plots:
{plots_list}
- Auto-generated analysis: `{analysis_md_rel}`

## Important
- Use **extended thinking/reasoning** for deep analysis
- All output files go in `{results_dir.relative_to(WORKSPACE)}/`
- When done: `python3 scripts/pipeline_orchestrate.py {version} complete local_analysis_architect --agent architect --notes "your summary" --learnings "insights"`

⚠️ **Session Protocol:** Fresh session. Read memory files first. Write learnings before completing."""

    # Step 4: Fire-and-forget dispatch to architect
    print(f"\n   🔔 Dispatching architect (fire-and-forget)...")
    result = fire_and_forget_dispatch(version, 'local_analysis_architect', 'architect', message=handoff_msg)
    if result.get('success'):
        print(f"   🔔 Dispatched architect (fire-and-forget)")
    else:
        print(f"   ⚠️ Dispatch failed: {result.get('error')}")

    pipeline_session_id = generate_session_id(version, 'architect')
    wake_result = {'success': result.get('success', False), 'status': 'dispatched', 'session_id': pipeline_session_id}

    # Write handoff record
    write_handoff(version, 'local_experiment_complete', 'local_analysis_architect',
                  'architect', wake_result, pipeline_session_id)

    # Notify
    send_orchestrator_notification(version, '📊 Local analysis started',
        f'Architect analyzing experiment results for <b>{version}</b>. '
        f'Reasoning enabled for deep analysis.')

    return wake_result.get('success', False)


def orchestrate_report_build(version: str):
    """Build the final LaTeX report and PDF from the approved analysis.

    Called after local_analysis_code_review passes. Spawns a subagent
    to convert the analysis report → LaTeX → PDF.

    Returns True if report was built successfully.
    """
    print(f"\n{'═' * 70}")
    print(f"  📄 ORCHESTRATOR: {version} — building LaTeX report")
    print(f"{'═' * 70}\n")

    results_dir = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'notebooks' / 'local_results' / version
    if not results_dir.exists():
        results_dir = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'notebooks' / 'local_results'

    # Find the analysis report
    report_md = results_dir / f'{version}_analysis_report.md'
    if not report_md.exists():
        report_md = results_dir / f'{version}_analysis.md'
    if not report_md.exists():
        print(f"   ❌ No analysis report found in {results_dir}")
        return False

    # List all images
    images = sorted(results_dir.glob('*.png'))
    image_list = '\n'.join(f'  - {img.name}' for img in images)

    # Update stage
    print(f"   📊 Starting local_analysis_report_build stage")
    run_pipeline_update([
        version, 'start', 'local_analysis_report_build',
        '--agent', 'system',
        '--notes', f'Building LaTeX report from {report_md.name}'
    ])

    # Try auto-build first via pandoc
    print(f"\n   📋 Attempting pandoc auto-build...")
    build_cmd = [
        sys.executable,
        str(WORKSPACE / 'scripts' / 'build_report.py'),
        version,
    ]
    result = subprocess.run(build_cmd, capture_output=True, text=True,
                           cwd=str(WORKSPACE), timeout=120)
    print(result.stdout)

    pdf_path = results_dir / f'{version}_report.pdf'
    if pdf_path.exists():
        size_kb = pdf_path.stat().st_size / 1024
        print(f"   ✅ PDF generated: {pdf_path.relative_to(WORKSPACE)} ({size_kb:.1f} KB)")

        # Complete the stage
        run_pipeline_update([
            version, 'complete', 'local_analysis_report_build',
            '--agent', 'system',
            '--notes', f'LaTeX report built. PDF: {pdf_path.relative_to(WORKSPACE)} ({size_kb:.1f} KB)'
        ])

        send_orchestrator_notification(version, '📄 Report built',
            f'PDF report generated for <b>{version}</b>: '
            f'<code>{pdf_path.relative_to(WORKSPACE)}</code> ({size_kb:.1f} KB)')

        return True

    # Pandoc failed — fall back to builder agent with reasoning
    print(f"\n   ⚠️  Auto-build failed. Spawning builder agent for LaTeX report...")

    report_task = f"""📄 Build LaTeX Report — {version}

⚠️ **REASONING REQUIRED** — Use extended thinking for professional report formatting.

The analysis for pipeline `{version}` has been approved. Your job is to turn the
approved analysis report into a professional LaTeX document and compile it to PDF.

## Source Material
- **Analysis report:** `{report_md.relative_to(WORKSPACE)}`
- **Results directory:** `{results_dir.relative_to(WORKSPACE)}/`
- **Available images:**
{image_list}

## Instructions

1. **Read the analysis report** thoroughly
2. **Write a professional LaTeX document** at `{results_dir.relative_to(WORKSPACE)}/{version}_report.tex`:
   - Title page with pipeline metadata (name, date, experiment count, duration)
   - Table of contents
   - Executive summary
   - All sections from the analysis report, properly formatted
   - All plots as figures with captions (use \\includegraphics with relative paths)
   - Properly formatted tables using booktabs
   - Conclusions section
   - References to plot files use relative paths (just the filename, e.g. accuracy_summary.png)

3. **Compile to PDF:**
   ```bash
   cd {results_dir}
   pdflatex -interaction=nonstopmode {version}_report.tex
   pdflatex -interaction=nonstopmode {version}_report.tex
   ```

4. **Verify** the PDF exists and has reasonable size (>50KB with images)

5. **Complete via orchestrator:**
   ```
   python3 scripts/pipeline_orchestrate.py {version} complete local_analysis_report_build --agent builder --notes "LaTeX report compiled" --learnings "..."
   ```

## Style
- 11pt article, a4paper, 2.5cm margins
- booktabs tables, float [H] figures
- hyperref with dark blue links
- fancyhdr headers/footers
- Section numbering
- lmodern fonts"""

    # Fire-and-forget dispatch to builder (LaTeX report)
    session_id = generate_session_id(version, 'builder')
    print(f"\n   🔔 Dispatching builder for LaTeX report (fire-and-forget)...")
    result = fire_and_forget_dispatch(version, 'local_analysis_report_build', 'builder', message=report_task)
    if result.get('success'):
        print(f"   🔔 Dispatched builder (fire-and-forget)")
    else:
        print(f"   ⚠️ Dispatch failed: {result.get('error')}")

    wake_result = {'success': result.get('success', False), 'status': 'dispatched', 'session_id': session_id}
    write_handoff(version, 'local_analysis_code_review', 'local_analysis_report_build',
                  'builder', wake_result, session_id)

    return True


def orchestrate_complete_task(version: str, agent: str = 'architect', notes: str = ''):
    """Architect declares a task fully done — archives pipeline, marks task done.

    Called when the architect (or coordinator) determines a task needs no further
    pipeline phases. This is the "task is done" path from phase1_complete or
    phase2_complete review gates.

    Steps:
      1. Load pipeline markdown and extract the task slug from frontmatter
      2. Set pipeline status to 'archived' with archive reason
      3. Find the parent task and set its status to 'done'
      4. Notify Telegram group about task completion
    """
    print(f"\n{'═' * 70}")
    print(f"  ✅ ORCHESTRATOR: {version} — completing task (archiving pipeline)")
    print(f"{'═' * 70}\n")

    # Step 1: Load pipeline and extract task slug
    pipeline_path = PIPELINES_DIR / f'{version}.md'
    if not pipeline_path.exists():
        print(f"❌ Pipeline not found: pipelines/{version}.md")
        return False

    pipeline_content = pipeline_path.read_text()

    # Extract task slug from frontmatter
    task_slug = None
    # Try 'task:' field first (builder-first pipelines)
    task_match = re.search(r'^task:\s*(.+)$', pipeline_content, re.MULTILINE)
    if task_match:
        task_slug = task_match.group(1).strip()
    else:
        # Fall back to version as task slug (common convention)
        task_slug = version

    # Extract current status for logging
    status_match = re.search(r'^status:\s*(.+)$', pipeline_content, re.MULTILINE)
    old_status = status_match.group(1).strip() if status_match else 'unknown'

    print(f"   📦 Pipeline: {version} (status: {old_status})")
    print(f"   📋 Task: {task_slug}")
    print(f"   👤 Agent: {agent}")
    if notes:
        print(f"   📝 Notes: {notes}")

    # Step 2: Archive the pipeline
    archive_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    archive_reason = notes or f'Task completed by {agent}'

    # Update status to archived
    pipeline_content = re.sub(
        r'^status:\s*.+$',
        'status: archived',
        pipeline_content,
        count=1,
        flags=re.MULTILINE,
    )

    # Add/update archived date
    if re.search(r'^archived:', pipeline_content, re.MULTILINE):
        pipeline_content = re.sub(
            r'^archived:\s*.+$',
            f'archived: {archive_date}',
            pipeline_content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        # Insert after 'started:' line if it exists, otherwise after 'status:'
        if re.search(r'^started:', pipeline_content, re.MULTILINE):
            pipeline_content = re.sub(
                r'^(started:\s*.+)$',
                f'\\1\narchived: {archive_date}',
                pipeline_content,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            pipeline_content = re.sub(
                r'^(status:\s*archived)$',
                f'\\1\narchived: {archive_date}',
                pipeline_content,
                count=1,
                flags=re.MULTILINE,
            )

    # Add archive_reason if not present
    if not re.search(r'^archive_reason:', pipeline_content, re.MULTILINE):
        pipeline_content = re.sub(
            r'^(archived:\s*.+)$',
            f'\\1\narchive_reason: {archive_reason}',
            pipeline_content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        pipeline_content = re.sub(
            r'^archive_reason:\s*.+$',
            f'archive_reason: {archive_reason}',
            pipeline_content,
            count=1,
            flags=re.MULTILINE,
        )

    pipeline_path.write_text(pipeline_content)
    print(f"   ✅ Pipeline archived (status: archived, archived: {archive_date})")

    # Update state JSON too
    state = load_pipeline_state(version)
    state['status'] = 'archived'
    state['archived'] = archive_date
    state['archive_reason'] = archive_reason
    state['last_updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    save_pipeline_state(version, state)

    # Step 3: Mark the parent task as done
    task_path = WORKSPACE / 'tasks' / f'{task_slug}.md'
    if task_path.exists():
        task_content = task_path.read_text()
        old_task_status = 'unknown'
        task_status_match = re.search(r'^status:\s*(.+)$', task_content, re.MULTILINE)
        if task_status_match:
            old_task_status = task_status_match.group(1).strip()

        task_content = re.sub(
            r'^status:\s*.+$',
            'status: done',
            task_content,
            count=1,
            flags=re.MULTILINE,
        )
        task_path.write_text(task_content)
        print(f"   ✅ Task '{task_slug}' marked done (was: {old_task_status})")
    else:
        print(f"   ⚠️  Task file not found: tasks/{task_slug}.md — skipping task status update")

    # Step 4: Consolidate agent memory
    consolidate_agent_memory(agent, version, 'task_complete', notes or archive_reason)

    # Step 5: Notify Telegram group
    from pipeline_update import notify_group
    notify_group(agent, version, 'complete', 'task_complete',
                 f'Task fully done. Pipeline archived. Reason: {archive_reason}')

    print(f"\n{'─' * 70}")
    print(f"  📊 Task Completion Summary:")
    print(f"     Pipeline:  {version} → archived")
    print(f"     Task:      {task_slug} → done")
    print(f"     Agent:     {agent}")
    print(f"     Reason:    {archive_reason}")
    print(f"{'─' * 70}\n")

    return True


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

        # Agent hasn't picked up — retry via fire_and_forget_dispatch
        print(f"   🔄 Re-dispatching to {next_agent} for {next_stage} (fire-and-forget)...")
        handoff_msg = build_handoff_message(
            version, completed_stage, next_stage, next_agent,
            f"[RETRY] Original handoff was not picked up. Please process {next_stage}."
        )
        result = fire_and_forget_dispatch(version, next_stage, next_agent, message=handoff_msg)
        if result.get('success'):
            print(f"   🔔 Dispatched {next_agent} (fire-and-forget)")
        else:
            print(f"   ⚠️ Dispatch failed: {result.get('error')}")
        mark_handoff_verified(path)

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


# ═══════════════════════════════════════════════════════════════════════
# P3: Agent-to-Agent Conversational Exchange Loop
# ═══════════════════════════════════════════════════════════════════════

MAX_EXCHANGES = 3
DISPATCH_TIMEOUT = 300  # FLAG-1 MED: per-dispatch timeout in seconds


def load_pipeline_state(version: str) -> dict:
    """Load pipeline state JSON."""
    state_file = BUILDS_DIR / f'{version}_state.json'
    if not state_file.exists():
        state_file = RESEARCH_BUILDS_DIR / f'{version}_state.json'
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def save_pipeline_state(version: str, state: dict):
    """Save pipeline state JSON."""
    state_file = BUILDS_DIR / f'{version}_state.json'
    if not state_file.exists():
        state_file = RESEARCH_BUILDS_DIR / f'{version}_state.json'
    try:
        state_file.write_text(json.dumps(state, indent=2, default=str), encoding='utf-8')
    except Exception as e:
        print(f"   ⚠️  Failed to save state: {e}")


def dispatch_agent(agent: str, message: str, session_id: str = None,
                   timeout: int = DISPATCH_TIMEOUT) -> dict:
    """Dispatch an agent with optional session-ID tracking.

    Uses wake_agent() with timeout. Returns {completed, session_id, response, has_blocks}.
    """
    result = wake_agent(agent, message, timeout=timeout, session_id=session_id)
    response = result.get('response', '')

    # Detect blocks/flags in critic responses
    has_blocks = bool(re.search(r'\bBLOCK', response, re.IGNORECASE)) if response else False

    return {
        'completed': result.get('success', False),
        'session_id': result.get('session_id', ''),
        'response': response,
        'has_blocks': has_blocks,
    }


def get_render_diff() -> str:
    """Get render engine diff for review context."""
    try:
        import socket as _socket
        sock_path = WORKSPACE / '.codex_runtime' / 'render.sock'
        if sock_path.exists():
            s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect(str(sock_path))
            s.sendall(b'diff\n')
            data = s.recv(65536).decode('utf-8', errors='replace')
            s.close()
            return data.strip()
    except Exception:
        pass
    # Fallback: run codex_engine --supermap-diff
    try:
        out = subprocess.run(
            [sys.executable, str(WORKSPACE / 'scripts' / 'codex_engine.py'), '--supermap-diff'],
            capture_output=True, text=True, cwd=str(WORKSPACE), timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return ''


def build_review_message(version: str, stage: str, builder_result: dict) -> str:
    """D6: Build a review message with embedded diffs for critic."""
    diff = get_render_diff()
    notes = builder_result.get('response', '')[:500]

    msg = f"🔄 Review request — {version}\n"
    msg += f"Stage: {stage}\n"
    if notes:
        msg += f"Builder notes: {notes}\n"
    if diff:
        msg += f"\n## Changes Since Last Anchor\n```\n{diff[:2000]}\n```\n"
    msg += "\nReview the implementation and provide feedback. If issues found, list BLOCKs."
    return msg


def post_exchange_to_group(from_agent: str, to_agent: str, exchange: int,
                           version: str, summary: str):
    """D7: Post agent exchange summary to group chat.

    FLAG-2 LOW: For 1-exchange cases, post only once (the approval).
    For 2+ exchanges, post first (review started) + last (concluded).
    """
    preview = summary[:200] + ('...' if len(summary) > 200 else '')
    group_msg = f"💬 {from_agent} → {to_agent} [exchange {exchange + 1}] ({version})\n{preview}"
    try:
        send_orchestrator_notification(version, f'💬 Exchange {exchange + 1}', group_msg)
    except Exception:
        pass  # non-critical


def run_exchange_loop(version: str, stage: str) -> dict:
    """D5: Run builder→critic exchange loop with session-ID tracking.

    Returns {status, exchanges, final_result}.
    """
    state = load_pipeline_state(version)
    active = state.get('active_sessions', {})
    critic_session_id = active.get('critic', {}).get('session_id')

    for exchange in range(MAX_EXCHANGES):
        # 1. Spawn builder (always fresh — stateless implementors)
        builder_context = f"Exchange {exchange + 1}/{MAX_EXCHANGES} for {version} stage {stage}"
        if exchange > 0:
            # Include previous critic feedback
            prev_feedback = active.get('critic', {}).get('last_feedback', '')
            if prev_feedback:
                builder_context += f"\n\nCritic feedback from previous exchange:\n{prev_feedback}"

        builder_result = dispatch_agent('builder', builder_context, timeout=DISPATCH_TIMEOUT)
        if not builder_result.get('completed'):
            return {'status': 'builder_timeout', 'exchanges': exchange}

        # 2. Build review message with diffs
        review_msg = build_review_message(version, stage, builder_result)

        # 3. Spawn/resume critic (Option B: session-ID tracking, Option C: fallback)
        critic_result = dispatch_agent(
            'critic', review_msg,
            session_id=critic_session_id,
            timeout=DISPATCH_TIMEOUT,
        )

        # Track critic session for next exchange
        new_session_id = critic_result.get('session_id', '')
        if new_session_id:
            critic_session_id = new_session_id

        # Update state
        active.setdefault('critic', {})
        active['critic']['session_id'] = critic_session_id
        active['critic']['exchange_count'] = exchange + 1
        active['critic']['last_feedback'] = critic_result.get('response', '')[:1000]
        state['active_sessions'] = active
        save_pipeline_state(version, state)

        # 4. Group chat visibility (FLAG-2: first + last only, dedup for 1-exchange)
        should_post = (exchange == 0) or (not critic_result.get('has_blocks'))
        if should_post:
            summary = critic_result.get('response', 'No response')[:200]
            post_exchange_to_group('builder', 'critic', exchange, version, summary)

        # 5. Check if critic approved (no blocks)
        if not critic_result.get('has_blocks'):
            return {
                'status': 'approved',
                'exchanges': exchange + 1,
                'final_result': critic_result,
            }

    # Hit exchange limit
    return {
        'status': 'exchange_limit',
        'exchanges': MAX_EXCHANGES,
        'final_result': critic_result if 'critic_result' in dir() else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2 V4: Stage Session Support
# ═══════════════════════════════════════════════════════════════════════════════

# D3: Stage flow table — defines session behavior per transition
# session_type: 'shared' = reviewer joins existing session, 'fresh' = new session
STAGE_FLOW = {
    # Legacy names
    'architect_design':       ('critic_design_review', 'critic', 'shared'),
    'critic_design_review':   ('builder_implementation', 'builder', 'fresh'),
    'builder_implementation': ('builder_verification', 'builder', 'fresh'),
    'builder_verification':   ('critic_code_review', 'critic', 'shared'),
    'critic_code_review':     ('phase1_complete', 'architect', 'fresh'),
    'phase2_architect_design':       ('phase2_critic_design_review', 'critic', 'shared'),
    'phase2_critic_design_review':   ('phase2_builder_implementation', 'builder', 'fresh'),
    'phase2_builder_implementation': ('phase2_builder_verification', 'builder', 'fresh'),
    'phase2_builder_verification':   ('phase2_critic_code_review', 'critic', 'shared'),
    'phase2_critic_code_review':     ('phase2_complete', 'architect', 'fresh'),
    # Phase-based names (dynamically populated from templates if needed)
}


def generate_stage_session_id(version: str, stage: str) -> str:
    """Generate a deterministic session ID for a pipeline stage."""
    return f"pipeline:{version}:{stage}"


# ─── Verification Dispatch (D5 + D9 auto-retry) ────────────────────────────

VERIFICATION_TIMEOUT = 600       # 10 min total
VERIFICATION_STEER_AT = 420     # 7 min steer warning
VERIFICATION_MAX_RETRIES = 3    # D9: max retries before escalation


def build_verification_message(version: str, retry_count: int = 0) -> str:
    """Build the dispatch message for builder verification stage."""
    if retry_count > 0:
        # Include previous failure context for retry
        results_path = RESEARCH_BUILDS_DIR / f'{version}_test_results.md'
        if not results_path.exists():
            results_path = BUILDS_DIR / f'{version}_test_results.md'
        failure_report = ''
        if results_path.exists():
            failure_report = results_path.read_text(encoding='utf-8')[:2000]
        return (
            f"⚠️ Verification RETRY {retry_count}/{VERIFICATION_MAX_RETRIES} "
            f"for {version}.\n\n"
            f"Previous test failures:\n```\n{failure_report}\n```\n\n"
            f"Fix the failing tests and re-run: "
            f"python3 scripts/pipeline_verify.py {version}\n\n"
            f"If all GREEN → complete the stage. If still failing, fix and re-run. "
            f"If unfixable, block the stage with details."
        )
    return f"""Run the verification loop for pipeline {version}:

1. Run: python3 scripts/pipeline_verify.py {version}
2. If all GREEN → complete the stage with the test results summary
3. If FAIL → read the test results, fix the failing code, commit, re-run
4. Max 5 iterations. If still failing after 5, block with the test results.

The test spec is at: pipeline_builds/{version}_test_spec.md
Test results will be written to: pipeline_builds/{version}_test_results.md"""


def _start_steer_timer(session_id: str) -> None:
    """Start wiggum steer timer in background."""
    steer_script = WORKSPACE / 'skills' / 'ralph-wiggum' / 'scripts' / 'steer_timer.sh'
    if steer_script.exists():
        try:
            subprocess.Popen(
                ['bash', str(steer_script), session_id,
                 str(VERIFICATION_STEER_AT), str(VERIFICATION_TIMEOUT)],
                cwd=str(WORKSPACE),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"   ⏰ Wiggum steer timer started: {VERIFICATION_STEER_AT}s steer, "
                  f"{VERIFICATION_TIMEOUT}s hard timeout")
        except Exception as e:
            print(f"   ⚠️ Failed to start steer timer: {e}")
    else:
        print(f"   ⚠️ Steer timer script not found: {steer_script}")


def dispatch_verification(version: str) -> dict:
    """Dispatch builder for verification with wiggum steer timer and auto-retry.

    Uses generate_stage_session_id() for deterministic session routing.
    Reads verification_retries from pipeline state for retry context.
    """
    stage = 'builder_verification'
    session_id = generate_stage_session_id(version, stage)

    # D9: Read retry count from state
    state = load_pipeline_state(version)
    retry_count = state.get('verification_retries', 0)

    if retry_count >= VERIFICATION_MAX_RETRIES:
        escalate_verification_failure(version, state)
        return {'success': False, 'error': 'max_retries_exhausted',
                'session_id': session_id}

    message = build_verification_message(version, retry_count=retry_count)

    # Increment retry counter BEFORE dispatch
    state['verification_retries'] = retry_count + 1
    save_pipeline_state(version, state)

    # Dispatch builder
    result = fire_and_forget_dispatch(version, stage, 'builder', message=message)

    # Start steer timer — uses session_id not result.session_key
    _start_steer_timer(session_id)

    result['session_id'] = session_id
    result['retry_count'] = retry_count
    return result


def escalate_verification_failure(version: str, state: dict) -> None:
    """Alert coordinator after max retries exhausted. D9 escalation."""
    results_path = RESEARCH_BUILDS_DIR / f'{version}_test_results.md'
    if not results_path.exists():
        results_path = BUILDS_DIR / f'{version}_test_results.md'
    failure_summary = ''
    if results_path.exists():
        failure_summary = results_path.read_text(encoding='utf-8')[:500]

    msg = (f"⚠️ {version} verification FAILED after "
           f"{VERIFICATION_MAX_RETRIES} retries.\n"
           f"{failure_summary}\n"
           f"Escalating to coordinator.")

    # Post to group chat
    try:
        from pipeline_update import send_telegram
        send_telegram(msg)
        print(f"   📢 Escalation posted to group chat")
    except Exception as e:
        print(f"   ⚠️ Failed to post escalation: {e}")

    print(f"   🚨 ESCALATION: {version} verification exhausted "
          f"{VERIFICATION_MAX_RETRIES} retries")


def check_verification_result(version: str, stage: str, notes: str) -> str:
    """D9: Check if verification passed or needs retry.

    Returns:
        'pass' — continue to next stage
        'retry' — re-dispatch verification
        'exhausted' — max retries reached, block
    """
    VERIFICATION_STAGES = {'builder_verification', 'phase2_builder_verification',
                           'p1_builder_verify', 'p2_builder_verify', 'p3_builder_verify'}
    if stage not in VERIFICATION_STAGES:
        return 'pass'

    # Check if GREEN
    notes_lower = notes.lower()
    if 'green' in notes_lower or 'all pass' in notes_lower or '8/8' in notes_lower:
        # Reset retry counter on success
        state = load_pipeline_state(version)
        state['verification_retries'] = 0
        save_pipeline_state(version, state)
        return 'pass'

    # RED — check retry budget
    state = load_pipeline_state(version)
    retry_count = state.get('verification_retries', 0)
    if retry_count >= VERIFICATION_MAX_RETRIES:
        return 'exhausted'
    return 'retry'


def orchestrate_signal(version: str, stage: str, agent: str, signal: str, notes: str = ''):
    """D2: Agent signals a stage event (ready_for_review, approved, flag, block).
    
    Writes signal to pipeline state JSON. Consumers watch via inotify or polling.
    """
    state = load_pipeline_state(version)
    stages = state.setdefault('stage_signals', {}).setdefault(stage, {})
    stages['signal'] = signal
    stages['signal_at'] = datetime.now(timezone.utc).isoformat()
    stages['signal_agent'] = agent
    stages['signal_notes'] = notes
    save_pipeline_state(version, state)

    # Notify render engine for push to attached agents
    try:
        import socket as _socket
        sock_path = WORKSPACE / '.codex_runtime' / 'render.sock'
        if sock_path.exists():
            s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect(str(sock_path))
            s.sendall(json.dumps({'cmd': 'refresh', 'prefix': 'p'}).encode() + b'\n')
            s.recv(4096)
            s.close()
    except Exception:
        pass

    print(f"   📡 Signal '{signal}' from {agent} for {version}:{stage}")
    if notes:
        print(f"   📝 Notes: {notes[:200]}")


def wait_for_signal(version: str, stage: str, signals: list[str],
                    timeout: int = 1800, poll_interval: int = 30) -> str | None:
    """D2: Wait for a signal in pipeline state.
    
    Uses inotify when available, falls back to polling.
    Returns the signal string or None on timeout.
    """
    state_path = None
    for candidate in [BUILDS_DIR / f'{version}_state.json',
                      RESEARCH_BUILDS_DIR / f'{version}_state.json']:
        if candidate.exists():
            state_path = candidate
            break
    if not state_path:
        return None

    deadline = time.time() + timeout
    use_inotify = False

    # Try inotify
    try:
        import inotify.adapters
        i = inotify.adapters.Inotify()
        i.add_watch(str(state_path.parent), mask=0x00000002)  # IN_MODIFY
        use_inotify = True
    except ImportError:
        pass

    while time.time() < deadline:
        state = load_pipeline_state(version)
        current = state.get('stage_signals', {}).get(stage, {}).get('signal')
        if current and current in signals:
            return current

        if use_inotify:
            remaining = deadline - time.time()
            wait_time = min(poll_interval, max(remaining, 0))
            try:
                events = list(i.event_gen(yield_nones=False, timeout_s=wait_time))
                # Check state again after any file change
            except Exception:
                time.sleep(min(poll_interval, max(deadline - time.time(), 0)))
        else:
            time.sleep(min(poll_interval, max(deadline - time.time(), 0)))

    return None


def terminate_stage_session(version: str, stage: str):
    """D7: Archive session conversation and clean up.
    
    Archives conversation history to pipeline_builds/ for memory extraction.
    """
    state = load_pipeline_state(version)
    active = state.get('active_sessions', {})
    session_info = active.get(stage, {})
    session_id = session_info.get('session_id')

    if session_id:
        # Archive conversation (best-effort — sessions may already be gone)
        try:
            archive_path = BUILDS_DIR / f'{version}_{stage}_session_archive.md'
            # Attempt to fetch history via openclaw CLI
            result = subprocess.run(
                ['openclaw', 'sessions', 'history', '--session-id', session_id,
                 '--limit', '100', '--format', 'markdown'],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                archive_content = f"# Session Archive: {version} / {stage}\n\n"
                archive_content += f"Session ID: {session_id}\n"
                archive_content += f"Archived: {datetime.now(timezone.utc).isoformat()}\n\n"
                archive_content += result.stdout
                archive_path.write_text(archive_content, encoding='utf-8')
                print(f"   📦 Session archived: {archive_path.name}")
        except Exception as e:
            print(f"   ⚠️  Session archive failed: {e}")

    # Clean up session tracking
    active.pop(stage, None)
    # Clear signal
    state.get('stage_signals', {}).pop(stage, None)
    state['active_sessions'] = active
    save_pipeline_state(version, state)


def run_stage_session(version: str, stage: str, primary_agent: str,
                      reviewer: str = 'critic', max_exchanges: int = 3) -> dict:
    """D2+D3: Run a pipeline stage as a shared session with ping-pong review.
    
    Uses openclaw agent --session-id to create/reuse persistent sessions.
    Session type from STAGE_FLOW determines if reviewer joins existing session
    or gets a fresh one.
    """
    session_id = generate_stage_session_id(version, stage)

    # Build context
    context = build_handoff_message(version, '', stage, primary_agent, '')
    
    # Track in pipeline state
    state = load_pipeline_state(version)
    active = state.setdefault('active_sessions', {})
    active[stage] = {
        'session_id': session_id,
        'primary': primary_agent,
        'reviewer': reviewer,
        'started_at': datetime.now(timezone.utc).isoformat(),
        'exchange_count': 0,
    }
    save_pipeline_state(version, state)

    # Dispatch primary agent
    result = dispatch_agent(primary_agent, context, session_id=session_id,
                           timeout=DISPATCH_TIMEOUT)

    if not result.get('completed'):
        return {'status': 'primary_timeout', 'exchanges': 0}

    # Check stage flow for session type
    flow = STAGE_FLOW.get(stage)
    if not flow:
        return {'status': 'no_flow', 'exchanges': 1}

    next_stage, next_agent, session_type = flow

    if session_type == 'shared':
        # Reviewer joins same session
        review_msg = build_review_message(version, stage, result)
        reviewer_result = dispatch_agent(
            reviewer, review_msg, session_id=session_id,
            timeout=DISPATCH_TIMEOUT
        )

        # Update exchange count
        active[stage]['exchange_count'] = 1
        save_pipeline_state(version, state)

        if not reviewer_result.get('has_blocks'):
            terminate_stage_session(version, stage)
            return {'status': 'approved', 'exchanges': 1}

        # FLAG — iterate
        for exchange in range(1, max_exchanges):
            fix_msg = f"Exchange {exchange + 1}/{max_exchanges}: Fix blocks from reviewer.\n"
            fix_msg += reviewer_result.get('response', '')[:2000]

            result = dispatch_agent(primary_agent, fix_msg, session_id=session_id,
                                   timeout=DISPATCH_TIMEOUT)
            if not result.get('completed'):
                break

            review_msg = build_review_message(version, stage, result)
            reviewer_result = dispatch_agent(reviewer, review_msg,
                                             session_id=session_id,
                                             timeout=DISPATCH_TIMEOUT)
            active[stage]['exchange_count'] = exchange + 1
            save_pipeline_state(version, state)

            if not reviewer_result.get('has_blocks'):
                terminate_stage_session(version, stage)
                return {'status': 'approved', 'exchanges': exchange + 1}

        terminate_stage_session(version, stage)
        return {'status': 'exchange_limit', 'exchanges': max_exchanges}
    else:
        # Fresh session for next agent — terminate current, start new
        terminate_stage_session(version, stage)
        return {'status': 'completed', 'exchanges': 1}


def check_stalled_sessions(max_idle_seconds: int = 7200):
    """D3: Check for sessions with no activity for >2h. Called by cron."""
    for state_file in BUILDS_DIR.glob('*_state.json'):
        try:
            state = json.loads(state_file.read_text())
        except Exception:
            continue
        version = state_file.stem.replace('_state', '')
        for stage, session in state.get('active_sessions', {}).items():
            started = session.get('started_at', '')
            if not started:
                continue
            try:
                started_dt = datetime.fromisoformat(started)
                idle = (datetime.now(timezone.utc) - started_dt).total_seconds()
                if idle > max_idle_seconds:
                    exchanges = session.get('exchange_count', 0)
                    print(f"⚠️ STALLED: {version}/{stage} — idle {idle/3600:.1f}h, "
                          f"exchanges={exchanges}")
                    send_orchestrator_notification(
                        version, '⚠️ Stalled Session',
                        f'<b>{version}/{stage}</b> idle for {idle/3600:.1f}h '
                        f'({exchanges} exchanges). Manual intervention needed.'
                    )
            except Exception:
                pass


# ─── D8: Lesson Injection Diagnostic ────────────────────────────────────────

def show_lessons(version: str) -> None:
    """Show which lessons would be injected for a given pipeline stage."""
    try:
        from orchestration_engine import _files_for_stage
    except ImportError:
        print("  ⚠️ orchestration_engine._files_for_stage not available")
        return

    for stage, agent in [('architect_design', 'architect'),
                         ('builder_implementation', 'builder'),
                         ('critic_code_review', 'critic')]:
        try:
            files = _files_for_stage(version, stage, agent)
            lesson_files = [f for f in files if 'lesson' in f.lower()]
            print(f"\n  {stage} ({agent}): {len(lesson_files)} lessons")
            for lf in lesson_files:
                print(f"    - {lf}")
        except Exception as e:
            print(f"\n  {stage} ({agent}): error — {e}")


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

    elif action == 'show-lessons':
        show_lessons(version)

    elif action == 'complete':
        stage = positional[0] if positional else flags.get('stage')
        notes = flags.get('notes', positional[1] if len(positional) > 1 else '')
        agent = flags.get('agent', positional[2] if len(positional) > 2 else 'unknown')
        learnings = flags.get('learnings', '')
        if not stage:
            print("Usage: pipeline_orchestrate.py <version> complete <stage> --agent <role> --notes <text> [--learnings <text>]")
            sys.exit(1)
        orchestrate_complete(version, stage, agent, notes, learnings)

    elif action == 'block':
        stage = positional[0] if positional else flags.get('stage')
        notes = flags.get('notes', positional[1] if len(positional) > 1 else '')
        agent = flags.get('agent', positional[2] if len(positional) > 2 else 'unknown')
        artifact = flags.get('artifact', '')
        learnings = flags.get('learnings', '')
        if not stage:
            print("Usage: pipeline_orchestrate.py <version> block <stage> --agent <role> --notes <text> [--artifact file.md] [--learnings <text>]")
            sys.exit(1)
        orchestrate_block(version, stage, agent, notes, artifact, learnings)

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

    elif action == 'revise':
        context = flags.get('context', positional[0] if positional else '')
        revision_num = int(flags['revision']) if 'revision' in flags else None
        if not context:
            print("Usage: pipeline_orchestrate.py <version> revise --context \"revision directions...\"")
            print("  Optional: --revision <num>  (auto-increments if omitted)")
            sys.exit(1)
        orchestrate_revise(version, context, revision_num)

    elif action == 'verify':
        orchestrate_verify(version)

    elif action == 'signal':
        stage = positional[0] if positional else flags.get('stage')
        signal_name = positional[1] if len(positional) > 1 else flags.get('signal')
        agent = flags.get('agent', 'unknown')
        notes = flags.get('notes', '')
        if not stage or not signal_name:
            print("Usage: pipeline_orchestrate.py <version> signal <stage> <signal> --agent <role>")
            sys.exit(1)
        orchestrate_signal(version, stage, agent, signal_name, notes)

    elif action == 'complete-task':
        agent = flags.get('agent', 'architect')
        notes = flags.get('notes', positional[0] if positional else '')
        orchestrate_complete_task(version, agent, notes)

    elif action == 'check-stalled':
        max_idle = int(flags.get('max-idle', flags.get('max_idle', '7200')))
        check_stalled_sessions(max_idle)

    elif action in ('run-experiment', 'run', 'experiment'):
        dry_run = 'dry-run' in flags or 'dry_run' in flags
        max_retries = int(flags.get('max-retries', flags.get('max_retries', '2')))
        no_recovery = 'no-recovery' in flags or 'no_recovery' in flags
        analyze_local = 'analyze-local' in flags or 'analyze_local' in flags or 'analyze' in flags
        orchestrate_local_run(version, dry_run=dry_run, max_retries=max_retries,
                               no_recovery=no_recovery)
        # Chain into local analysis if requested and experiments succeeded
        if analyze_local:
            print(f"\n{'─' * 70}")
            print(f"  🔗 Chaining into local analysis...")
            print(f"{'─' * 70}\n")
            orchestrate_local_analysis(version, dry_run=dry_run)

    elif action in ('local-analysis', 'analyze-local', 'analysis'):
        dry_run = 'dry-run' in flags or 'dry_run' in flags
        orchestrate_local_analysis(version, dry_run=dry_run)

    elif action in ('report-build', 'report', 'build-report'):
        orchestrate_report_build(version)

    elif action == 'kickoff':
        # Generic phase kickoff: --phase N (or --phase2 for backward compat)
        md_path = WORKSPACE / 'pipelines' / f'{version}.md'
        current_status = ''
        pending_action = ''
        if md_path.exists():
            text = md_path.read_text()
            for line in text.split('\n'):
                if line.startswith('status:'):
                    current_status = line.split(':', 1)[1].strip()
                if line.startswith('pending_action:'):
                    pending_action = line.split(':', 1)[1].strip()

        # Parse --phase N or --phase2 (backward compat)
        phase_num = None
        if '--phase2' in sys.argv:
            phase_num = 2
        elif 'phase' in flags:
            phase_num = int(flags['phase'])
        direction = flags.get('direction', '')

        if phase_num:
            # Phase N kickoff — find the human gate to complete
            notes = f'Phase {phase_num} kickoff'

            # Human gate stages end with _complete (both legacy and new format)
            # Find which complete stage to advance from
            # New format: p{N-1}_complete or p{N}_complete
            # Legacy: phase1_complete, local_analysis_complete, phase2_complete, etc.
            gate_candidates = [
                f'p{phase_num - 1}_complete',  # New format
                current_status,                  # Current status might be the gate
                pending_action,                  # Or pending_action
            ]
            # Legacy gate names
            legacy_gates = {
                2: ['phase1_complete', 'local_analysis_complete', 'p1_complete'],
                3: ['phase2_complete', 'local_analysis_complete', 'p2_complete'],
                4: ['phase3_complete', 'p3_complete'],
            }
            gate_candidates.extend(legacy_gates.get(phase_num, []))

            # Find a valid gate stage
            complete_from = None
            for candidate in gate_candidates:
                if candidate and ('complete' in candidate or candidate == current_status):
                    complete_from = candidate
                    break

            if not complete_from:
                complete_from = f'p{phase_num - 1}_complete'

            # Handle direction file
            ws_builds = WORKSPACE / 'pipeline_builds'
            search_dirs = [ws_builds, BUILDS_DIR]

            if direction:
                direction_path = None
                for loc in [Path(direction), BUILDS_DIR / direction, ws_builds / direction, WORKSPACE / direction]:
                    if loc.exists():
                        direction_path = loc
                        break
                if direction_path:
                    import shutil
                    target = ws_builds / f'{version}_phase{phase_num}_shael_direction.md'
                    shutil.copy2(direction_path, target)
                    notes = f'Phase {phase_num} kickoff. Direction at {target.name}'
                    print(f"   📄 Direction file: {target.name}")
                else:
                    print(f"   ❌ Direction file not found: {direction}")
                    sys.exit(1)
            else:
                # Auto-detect direction file
                for loc in search_dirs:
                    for dname in (f'{version}_phase{phase_num}_direction.md',
                                  f'{version}_phase{phase_num}_shael_direction.md',
                                  # Legacy names for phase 2
                                  f'{version}_phase2_direction.md',
                                  f'{version}_phase2_shael_direction.md'):
                        if (loc / dname).exists():
                            notes = f'Phase {phase_num} kickoff. Direction at {dname}'
                            print(f"   📄 Direction file found: {loc / dname}")
                            break
                    else:
                        continue
                    break

            print(f"   🔄 Phase {phase_num} kickoff (from {complete_from})")
            orchestrate_complete(version, complete_from, 'belam-main', notes)

        elif current_status in ('', 'pipeline_created', 'created'):
            # Standard Phase 1 kickoff
            orchestrate_complete(version, 'pipeline_created', 'belam-main', 'Pipeline kickoff')
        else:
            print(f"   ⚠️  Pipeline status is '{current_status}' — not at a kickoff-ready stage")
            print(f"   Expected: pipeline_created (Phase 1) or use --phase N for later phases")
            print(f"   Use 'complete <stage>' for manual stage transitions")
            sys.exit(1)

    else:
        print(f"Unknown action: {action}")
        print("Actions: show, complete, block, start, status, complete-task, verify, revise, kickoff, run-experiment, local-analysis, report-build")
        print("Global: --check-pending")
        sys.exit(1)


if __name__ == '__main__':
    main()
