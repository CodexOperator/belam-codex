#!/usr/bin/env python3
"""
run_pipeline_stage.py — Pipeline Stage Session Orchestrator.

Orchestrates a single pipeline stage as a fresh agent session pair. This script
is a COORDINATOR — it sends tasks to agents, monitors completion, handles memory
consolidation and transcript archival. It does NOT do the work itself.

Usage:
    python3 scripts/run_pipeline_stage.py v4-analysis architect_design
    python3 scripts/run_pipeline_stage.py v4-analysis critic_review
    python3 scripts/run_pipeline_stage.py v4-analysis builder_implementation
    python3 scripts/run_pipeline_stage.py v4-analysis --auto
    python3 scripts/run_pipeline_stage.py v4-analysis architect_design --dry-run
    python3 scripts/run_pipeline_stage.py v4-analysis architect_design --timeout 60

Stage Architecture (each stage = primary agent + review agent pair):
    architect_design        → architect (quant-workflow)  reviewed by critic (quant-workflow)
    builder_implementation  → builder (quant-infrastructure) reviewed by architect (quant-workflow)
    critic_code_review      → critic (quant-infrastructure) reviewed by builder (quant-infrastructure)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
BUILDS_DIR = WORKSPACE / 'pipeline_builds'
CONVERSATIONS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'conversations'

# Agent session keys for sessions_send
AGENT_SESSIONS = {
    'architect': 'agent:architect:telegram:group:-5243763228',
    'critic':    'agent:critic:telegram:group:-5243763228',
    'builder':   'agent:builder:telegram:group:-5243763228',
}

# Stage definitions: stage_name → (primary_agent, review_agent, primary_skill, review_skill)
STAGE_CONFIG = {
    # Generic builder pipeline stages
    'architect_design':        ('architect', 'critic',    'quant-workflow',       'quant-workflow'),
    'critic_design_review':    ('critic',    'architect', 'quant-workflow',       'quant-workflow'),
    'builder_implementation':  ('builder',   'architect', 'quant-infrastructure', 'quant-workflow'),
    'critic_code_review':      ('critic',    'builder',   'quant-infrastructure', 'quant-infrastructure'),
    # Analysis pipeline stages
    'analysis_architect_design':       ('architect', 'critic',    'quant-workflow',       'quant-workflow'),
    'analysis_critic_review':          ('critic',    'architect', 'quant-workflow',       'quant-workflow'),
    'analysis_builder_implementation': ('builder',   'architect', 'quant-infrastructure', 'quant-workflow'),
    'analysis_critic_code_review':     ('critic',    'builder',   'quant-infrastructure', 'quant-infrastructure'),
}

# Stage orderings for --auto mode
# Analysis pipeline
ANALYSIS_PIPELINE_STAGES = [
    'analysis_architect_design',
    'analysis_critic_review',
    'analysis_builder_implementation',
    'analysis_critic_code_review',
    'analysis_phase1_complete',  # terminal marker — no agent task
]

# Builder pipeline
BUILDER_PIPELINE_STAGES = [
    'architect_design',
    'critic_design_review',
    'builder_implementation',
    'critic_code_review',
    'phase1_complete',  # terminal marker
]

# Poll interval and default timeout
POLL_INTERVAL_SECONDS = 30
DEFAULT_TIMEOUT_MINUTES = 45


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
    print(f"[{ts}] {msg}", flush=True)


def load_state(version: str) -> dict:
    """Load pipeline state JSON. Returns empty dict if not found."""
    state_path = BUILDS_DIR / f'{version}_state.json'
    if state_path.exists():
        try:
            return json.loads(state_path.read_text())
        except Exception as e:
            log(f"WARNING: Could not parse state JSON: {e}")
    return {}


def get_pending_stage(version: str) -> str:
    """Get the current pending_action from state JSON."""
    state = load_state(version)
    return state.get('pending_action', '')


def stage_is_complete(version: str, stage: str) -> bool:
    """Check if a stage is marked complete in state JSON."""
    state = load_state(version)
    stages = state.get('stages', {})
    stage_data = stages.get(stage, {})
    return stage_data.get('status') == 'complete'


def run_script(script_name: str, *args, dry_run: bool = False) -> tuple[int, str]:
    """Run a workspace script. Returns (returncode, stdout+stderr)."""
    cmd = [sys.executable, str(WORKSPACE / 'scripts' / script_name)] + list(args)
    if dry_run:
        log(f"[DRY-RUN] Would run: {' '.join(cmd)}")
        return 0, ''
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE))
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output
    except Exception as e:
        return 1, str(e)


def generate_context(version: str, role: str) -> str:
    """Generate session context for an agent."""
    cmd = [
        sys.executable,
        str(WORKSPACE / 'scripts' / 'generate_session_context.py'),
        '--pipeline', version,
        '--role', role,
        '--brief',
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE))
        return result.stdout.strip()
    except Exception as e:
        return f"(context generation failed: {e})"


def detect_pipeline_type(version: str) -> str:
    """Detect whether this is an analysis or builder pipeline."""
    state = load_state(version)
    pt = state.get('pipeline_type', '')
    if pt:
        return pt
    if 'analysis' in version.lower():
        return 'analysis'
    return 'builder'


def get_stage_order(pipeline_type: str) -> list:
    if pipeline_type == 'analysis':
        return ANALYSIS_PIPELINE_STAGES
    return BUILDER_PIPELINE_STAGES


# ---------------------------------------------------------------------------
# Task Message Builder
# ---------------------------------------------------------------------------

def build_task_message(version: str, stage: str, primary_agent: str, review_agent: str,
                       primary_skill: str, review_skill: str, context: str) -> str:
    """Build the task message to send to the primary agent."""
    state = load_state(version)
    pending = state.get('pending_action', stage)
    review_session = AGENT_SESSIONS.get(review_agent, f'agent:{review_agent}:...')

    # Find relevant artifact paths
    builds_rel = 'pipeline_builds'
    design_brief = f'{builds_rel}/{version}_design_brief.md'
    prev_artifact_hint = ''

    # Look for most recent artifact for this pipeline
    if BUILDS_DIR.exists():
        artifacts = sorted(
            [f for f in BUILDS_DIR.glob(f'{version}_*.md')],
            key=lambda p: p.stat().st_mtime, reverse=True
        )
        if artifacts:
            prev_artifact_hint = f'\n- Most recent artifact: `{builds_rel}/{artifacts[0].name}`'

    message = f"""## Pipeline Stage Task: `{stage}`
**Pipeline:** `{version}`
**Your role:** `{primary_agent}`
**Stage:** `{stage}`

---

### Session Context
{context}

---

### Your Task

You are the **{primary_agent}** agent. Complete the `{stage}` stage for pipeline `{version}`.

**Skill to use:** Load and follow `skills/{primary_skill}/SKILL.md`

**Files to read first:**
- `pipelines/{version}.md` — pipeline definition and current status
- `{builds_rel}/{version}_state.json` — current stage state{prev_artifact_hint}
- `{design_brief}` — design brief (if exists)

**What to produce:**
- Write your output to: `{builds_rel}/{version}_{primary_agent}_{stage}.md`
- Follow the pipeline's agent coordination protocol (filesystem-first)
- Update pipeline state when done: `python3 scripts/pipeline_update.py {version} complete {stage} "your notes here" {primary_agent}`

**Hand-off on completion:**
After completing your work and updating pipeline state, notify the review agent:
```
sessions_send(
    sessionKey="{review_session}",
    message="{stage} complete for {version}. Please review: {builds_rel}/{version}_{primary_agent}_{stage}.md",
    timeoutSeconds=0
)
```

The review agent ({review_agent}) will use skill `{review_skill}` to review your output.

**Do not use sessions_send with timeoutSeconds > 0. Write files first, ping second.**
"""
    return message.strip()


# ---------------------------------------------------------------------------
# Core: Run a Single Stage
# ---------------------------------------------------------------------------

def run_stage(version: str, stage: str, dry_run: bool = False,
              timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES,
              no_reset: bool = False) -> bool:
    """
    Run a single pipeline stage:
    1. Look up stage config
    2. Generate context
    3. Send task to primary agent
    4. Poll for completion
    5. Run memory consolidation + transcript export

    Returns True if stage completed successfully, False on timeout/error.
    """
    if stage not in STAGE_CONFIG:
        log(f"ERROR: Unknown stage '{stage}'. Valid stages: {list(STAGE_CONFIG.keys())}")
        return False

    primary_agent, review_agent, primary_skill, review_skill = STAGE_CONFIG[stage]
    session_key = AGENT_SESSIONS[primary_agent]

    log(f"Stage: {stage}")
    log(f"Primary: {primary_agent} (skill: {primary_skill})")
    log(f"Review:  {review_agent} (skill: {review_skill})")
    log(f"Session: {session_key}")

    # Generate context
    log("Generating session context...")
    context = generate_context(version, primary_agent)

    # Build task message
    message = build_task_message(
        version, stage, primary_agent, review_agent,
        primary_skill, review_skill, context
    )

    if dry_run:
        log("[DRY-RUN] Would send the following to primary agent:")
        print("\n" + "=" * 60)
        print(f"TO: {session_key}")
        print("=" * 60)
        print(message)
        print("=" * 60 + "\n")
        log("[DRY-RUN] Would then poll for completion and run memory consolidation.")
        return True

    # Reset sessions for agents NEW to this stage — preserve context for agents
    # carrying over from the previous stage. This way:
    #   architect_design (A+C fresh) → critic_review (C fresh, A carries design context)
    #   → builder_impl (B fresh, A carries review context) → critic_code_review (C fresh, B carries build context)
    if no_reset:
        log("Skipping session reset (--no-reset)")

    # Load previous stage's agents from state to determine who carries over
    carry_over_agents = set()
    if not no_reset:
        state = load_state(version)
        prev_agents = state.get('_last_stage_agents', [])
        current_agents = [primary_agent, review_agent]
        carry_over_agents = set(prev_agents) & set(current_agents)
        if carry_over_agents:
            log(f"Context carry-over: {', '.join(carry_over_agents)} (from previous stage)")

    for agent_name in ([] if no_reset else [primary_agent, review_agent]):
        if agent_name in carry_over_agents:
            log(f"  ↪ {agent_name}: keeping context (bridging from previous stage)")
            continue
        agent_session = AGENT_SESSIONS[agent_name]
        log(f"Resetting session for {agent_name}: {agent_session}")
        try:
            reset_result = subprocess.run(
                ['openclaw', 'gateway', 'call', 'sessions.reset',
                 '--params', json.dumps({'key': agent_session}),
                 '--json'],
                capture_output=True, text=True
            )
            if reset_result.returncode == 0:
                reset_data = json.loads(reset_result.stdout)
                new_sid = reset_data.get('entry', {}).get('sessionId', 'unknown')
                log(f"  ✅ {agent_name} reset → new session {new_sid[:8]}...")
            else:
                log(f"  ⚠️  Reset failed for {agent_name}: {reset_result.stderr.strip()[:100]}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            log(f"  ⚠️  Could not reset {agent_name}: {e}")

    # Send task to primary agent via sessions_send CLI
    log(f"Sending task to {primary_agent}...")
    send_cmd = [
        'openclaw', 'sessions', 'send',
        '--session-key', session_key,
        '--message', message,
    ]
    try:
        result = subprocess.run(send_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log(f"WARNING: sessions_send returned {result.returncode}: {result.stderr.strip()}")
            # Try alternative: write to a task file the agent can pick up
            task_file = BUILDS_DIR / f'{version}_{stage}_task.md'
            task_file.parent.mkdir(parents=True, exist_ok=True)
            task_file.write_text(message)
            log(f"Fallback: task written to {task_file}")
        else:
            log(f"Task sent to {primary_agent} successfully.")
    except FileNotFoundError:
        # openclaw CLI not available — write task file as fallback
        log("WARNING: openclaw CLI not found. Writing task file as fallback.")
        task_file = BUILDS_DIR / f'{version}_{stage}_task.md'
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(message)
        log(f"Task written to: {task_file}")

    # Poll for completion
    log(f"Polling for stage completion (every {POLL_INTERVAL_SECONDS}s, timeout {timeout_minutes}m)...")
    deadline = time.monotonic() + timeout_minutes * 60
    poll_count = 0

    while time.monotonic() < deadline:
        if stage_is_complete(version, stage):
            log(f"✅ Stage '{stage}' completed successfully!")
            # Save which agents were involved — next stage uses this for carry-over
            state = load_state(version)
            state['_last_stage_agents'] = [primary_agent, review_agent]
            state_file = BUILDS_DIR / f'{version}_state.json'
            state_file.write_text(json.dumps(state, indent=2))
            log(f"Saved agent pair [{primary_agent}, {review_agent}] for carry-over tracking")
            break
        poll_count += 1
        remaining = int((deadline - time.monotonic()) / 60)
        log(f"Waiting... ({poll_count} polls, ~{remaining}m remaining)")
        time.sleep(POLL_INTERVAL_SECONDS)
    else:
        log(f"⏰ TIMEOUT: Stage '{stage}' did not complete within {timeout_minutes} minutes.")
        return False

    # Memory consolidation
    log("Running memory consolidation...")
    rc, out = run_script(
        'log_memory.py',
        '--category', 'event',
        '--importance', '3',
        '--tags', f'pipeline,{version},{stage}',
        f'{stage} completed for {version}',
    )
    if rc != 0:
        log(f"WARNING: log_memory.py returned {rc}: {out}")
    else:
        log("Memory logged.")

    # Export session transcript
    log("Exporting session transcripts...")
    rc, out = run_script(
        'export_agent_conversations.py',
        '--since', '1',  # last 1 hour
        '--output-dir', str(CONVERSATIONS_DIR),
    )
    if rc != 0:
        log(f"WARNING: export_agent_conversations.py returned {rc}: {out}")
    else:
        log("Transcripts exported.")

    # Archive this stage's transcript
    log("Archiving stage transcript...")
    rc, out = run_script(
        'archive_session_transcript.py',
        '--session-key', AGENT_SESSIONS[primary_agent],
        '--pipeline', version,
        '--stage', stage,
        '--output-dir', str(CONVERSATIONS_DIR),
    )
    if rc != 0:
        log(f"WARNING: archive_session_transcript.py returned {rc}: {out}")
    else:
        log("Stage transcript archived.")

    return True


# ---------------------------------------------------------------------------
# Auto Mode
# ---------------------------------------------------------------------------

def run_auto(version: str, dry_run: bool = False, timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES,
             no_reset: bool = False):
    """Chain all stages in order for the detected pipeline type."""
    pipeline_type = detect_pipeline_type(version)
    stage_order = get_stage_order(pipeline_type)
    log(f"AUTO mode: pipeline_type={pipeline_type}, stages={stage_order}")

    # Find current position (skip completed stages)
    start_idx = 0
    state = load_state(version)
    stages_done = {s for s, d in state.get('stages', {}).items() if d.get('status') == 'complete'}

    for i, stage in enumerate(stage_order):
        if stage in stages_done or stage.endswith('_complete'):
            log(f"Skipping already-complete stage: {stage}")
            start_idx = i + 1

    remaining_stages = stage_order[start_idx:]
    if not remaining_stages:
        log("All stages already complete. Nothing to do.")
        return

    log(f"Starting from stage index {start_idx}: {remaining_stages}")

    for stage in remaining_stages:
        # Terminal markers — no agent task needed
        if stage.endswith('_complete'):
            log(f"✅ Reached terminal stage: {stage}")
            rc, out = run_script(
                'log_memory.py',
                '--category', 'event',
                '--importance', '4',
                '--tags', f'pipeline,{version},phase_complete',
                f'Pipeline {version} Phase 1 complete',
                dry_run=dry_run,
            )
            break

        success = run_stage(version, stage, dry_run=dry_run, timeout_minutes=timeout_minutes,
                           no_reset=no_reset)
        if not success:
            log(f"ERROR: Stage '{stage}' failed or timed out. Stopping auto chain.")
            sys.exit(1)

        log(f"Stage '{stage}' done. Advancing to next stage...")
        time.sleep(2)

    log("AUTO pipeline complete!")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description='Pipeline Stage Session Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('version', help='Pipeline version (e.g. v4-analysis)')
    parser.add_argument('stage', nargs='?', help='Stage name (e.g. architect_design). Omit for --auto.')
    parser.add_argument('--auto', action='store_true', help='Run all stages automatically')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen without doing it')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT_MINUTES,
                        help=f'Timeout per stage in minutes (default: {DEFAULT_TIMEOUT_MINUTES})')
    parser.add_argument('--no-reset', action='store_true',
                        help='Skip session reset (preserve existing context)')
    return parser.parse_args()


def main():
    args = parse_args()

    if args.auto and args.stage:
        print("ERROR: Cannot specify both a stage and --auto", file=sys.stderr)
        sys.exit(1)

    if not args.auto and not args.stage:
        print("ERROR: Specify a stage name or use --auto", file=sys.stderr)
        sys.exit(1)

    log(f"Pipeline Stage Orchestrator — version={args.version}, dry_run={args.dry_run}")

    if args.auto:
        run_auto(args.version, dry_run=args.dry_run, timeout_minutes=args.timeout,
                 no_reset=args.no_reset)
    else:
        success = run_stage(
            args.version, args.stage,
            dry_run=args.dry_run,
            timeout_minutes=args.timeout,
            no_reset=args.no_reset,
        )
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
