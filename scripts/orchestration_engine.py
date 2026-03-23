#!/usr/bin/env python3
"""
orchestration_engine.py — Unified Orchestration Engine V2

Consolidates core logic from:
  - pipeline_autorun.py  (gate checking, stall detection, experiment monitoring)
  - pipeline_orchestrate.py  (handoffs, agent wake, checkpoint-and-resume)
  - launch_pipeline.py  (pipeline creation and kickoff)

Coordinate-aware: accepts version strings, numeric indices, or p-prefixed coordinates.
All output is plain text (no ANSI) — designed for LLM context consumption.
State changes use F-label format: F1 Δ p3.stage architect_design → critic_review
The orchestration engine owns F-labels (field-level diffs).
The codex-cockpit plugin owns R-labels (supermap landscape).

Importable AND runnable standalone:
  python3 scripts/orchestration_engine.py                    # full sweep
  python3 scripts/orchestration_engine.py status <ref>       # pipeline status
  python3 scripts/orchestration_engine.py gates [ref]        # gate check
  python3 scripts/orchestration_engine.py handoffs           # pending handoffs
  python3 scripts/orchestration_engine.py locks              # active locks
  python3 scripts/orchestration_engine.py stalls             # stall check
  python3 scripts/orchestration_engine.py dispatch <ref> <agent>  # dispatch agent
  python3 scripts/orchestration_engine.py dispatch-payload <ref> <agent>  # structured JSON dispatch
  python3 scripts/orchestration_engine.py complete <ref> <stage> --agent <a> --notes "..."  # stage done
  python3 scripts/orchestration_engine.py block <ref> <stage> --agent <a> --notes "..."    # stage blocked
  python3 scripts/orchestration_engine.py next <ref>         # next action
  python3 scripts/orchestration_engine.py verify-hooks       # hook verification
  python3 scripts/orchestration_engine.py launch <ver> --desc "..." [--start]  # create pipeline
  python3 scripts/orchestration_engine.py archive <ref>      # archive completed pipeline
  python3 scripts/orchestration_engine.py revert <ref> --at <ISO-ts> [--force]  # time-travel revert
  python3 scripts/orchestration_engine.py --dry-run          # dry run sweep
  python3 scripts/orchestration_engine.py --json <cmd>       # JSON output mode

  All commands accept --json for structured output (zero coordinator tokens).

FLAG fixes applied (orchestration-engine-v2 critic review):
  FLAG-1 (MED): STAGE_TRANSITIONS imported from pipeline_update.py (single source of truth)
  FLAG-2 (MED): Gate conditions support version strings for stored conditions; coordinate
                 syntax (p{N}) triggers a warning about archival fragility
  FLAG-3 (MED): pre/post_actions are metadata-only in DispatchPayload; engine executes
                 them before returning the payload. Coordinator only relays spawn{}.
  FLAG-4 (LOW): Lock staleness uses timeout as PRIMARY mechanism, PID as SECONDARY hint.
                 Handles OpenClaw's short-lived CLI process model correctly.

V2-temporal overlay integration (orchestration-engine-v2-temporal):
  Temporal hooks in _post_state_change() call log_transition(), advance_pipeline(),
  and create_handoff() on a SQLite-backed TemporalOverlay (graceful degradation).
  Addresses temporal Critic FLAGs:
    FLAG-1: Parameterized SQL queries (no injection)
    FLAG-2: Separated log_transition + advance_pipeline (not monolithic complete_stage)
    FLAG-3: SQLite DB IS on filesystem (agent_context inherently backed up)
    FLAG-5: Presence TTL applied at query time in get_dashboard()
"""

import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Callable

# ─── Paths ──────────────────────────────────────────────────────────────────────

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
SCRIPTS = WORKSPACE / 'scripts'
PIPELINES_DIR = WORKSPACE / 'pipelines'
BUILDS_DIR = WORKSPACE / 'pipeline_builds'
RESEARCH_BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
ML_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance'
RESULTS_BASE = ML_DIR / 'notebooks' / 'local_results'
HANDOFFS_DIR = PIPELINES_DIR / 'handoffs'

# Thresholds
STALL_THRESHOLD_MINUTES = 120
LOCK_STALE_MINUTES = 5

# Agent session directories
AGENT_SESSION_DIRS = {
    'architect': Path(os.path.expanduser('~/.openclaw/agents/architect/sessions')),
    'critic': Path(os.path.expanduser('~/.openclaw/agents/critic/sessions')),
    'builder': Path(os.path.expanduser('~/.openclaw/agents/builder/sessions')),
}

# Actions that indicate agent work is in progress
AGENT_ACTIONS = {
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
    'phase1_revision_architect', 'phase1_revision_critic_review',
    'phase1_revision_builder', 'phase1_revision_code_review',
    'phase1_revision_architect_fix', 'phase1_revision_builder_fix',
}

# Actions that are human-gated (don't auto-recover)
HUMAN_ACTIONS = {
    'ready_for_colab_run', 'phase1_complete', 'phase2_complete',
    'phase3_complete', 'pipeline_created', 'local_analysis_complete',
}

# Max resume attempts before alerting human
MAX_RESUMES = 3

# ─── Temporal Overlay (V2-temporal integration — lazy loaded) ──────────────────

_temporal_overlay = None  # Lazy-loaded TemporalOverlay instance


def _get_temporal():
    """Get the TemporalOverlay instance (lazy, graceful degradation).

    Returns TemporalOverlay if temporal DB (SQLite+WAL) is available,
    None otherwise. V2 engine continues normally when temporal is unavailable.
    """
    global _temporal_overlay
    if _temporal_overlay is None:
        try:
            from temporal_overlay import TemporalOverlay
            _temporal_overlay = TemporalOverlay(workspace=WORKSPACE)
            if not _temporal_overlay.available:
                _temporal_overlay = False  # Disabled — don't retry
        except ImportError:
            _temporal_overlay = False  # Module not installed
    return _temporal_overlay if _temporal_overlay else None


def _post_state_change(version: str, from_stage: str, to_stage: str,
                        agent: str, action: str, notes: str = '',
                        next_agent: str = '') -> bool:
    """Post-hook: record state change in temporal layer if available.

    Called after every state mutation in handle_complete/handle_block.
    Failure is silent — temporal is overlay, not critical path.

    V2-temporal integration (Critic FLAG-2 resolution):
      - log_transition(): append-only audit log (always safe)
      - advance_pipeline(): state mutation (updates current stage/agent)
      - create_handoff(): delivery tracking (when agent changes)
    These are separated per Critic FLAG-2 (split complete_stage into
    log_transition + advance_pipeline).
    """
    temporal = _get_temporal()
    if not temporal:
        return False
    try:
        # 1. Log the transition (immutable audit trail)
        temporal.log_transition(
            version=version, from_stage=from_stage, to_stage=to_stage,
            agent=agent, action=action, notes=notes,
        )
        # 2. Advance pipeline state
        if to_stage:
            temporal.advance_pipeline(
                version=version, stage=to_stage,
                agent=next_agent or agent,
            )
        # 3. Create handoff record if agent changes
        if action == 'complete' and next_agent and next_agent != agent:
            temporal.create_handoff(
                version=version, source_agent=agent,
                target_agent=next_agent, completed_stage=from_stage,
                next_stage=to_stage, notes=notes,
            )
        # 4. V3: Cascading dependency resolution on phase completion / archive
        if to_stage in HUMAN_ACTIONS or action == 'archive':
            try:
                from dependency_graph import resolve_downstream_deps
                resolved = resolve_downstream_deps(version, action=action)
                for r in resolved:
                    if r.get('all_deps_met'):
                        print(f'  🔗 Dep cascade: {r["target"]} now eligible '
                              f'(all deps met)')
            except ImportError:
                pass  # dependency_graph not available
            except Exception:
                pass  # Non-fatal

        # 5. Phase 2: Signal render engine for immediate pickup
        # Uses 'refresh' command (NOT anchor_reset which wipes the diff buffer
        # that .v5 R-label trail reads from — Critic FLAG-1).
        try:
            pipeline_md = PIPELINES_DIR / f'{version}.md'
            if pipeline_md.exists():
                from codex_render import _signal_render_engine
                _signal_render_engine('refresh', filepath=str(pipeline_md))
        except (ImportError, Exception):
            pass  # Non-fatal — inotify is the primary mechanism

        return True
    except Exception:
        return False  # Temporal failures are non-fatal


# ─── F-Label Counter ───────────────────────────────────────────────────────────

_f_counter = 0


def _next_f_label() -> str:
    """Generate next monotonic F-label for state transitions."""
    global _f_counter
    _f_counter += 1
    return f'F{_f_counter}'


def generate_f_label(operation: str, details: dict) -> str:
    """Generate an F-label for a pipeline state transition.

    Called during complete/block/dispatch operations.
    The orchestration engine owns F-labels (field-level diffs).
    The cockpit plugin owns R-labels (supermap landscape). No overlap.
    """
    label = _next_f_label()

    if operation == 'stage_change':
        old = details.get('old_stage', '?')
        new = details.get('new_stage', '?')
        coord = details.get('coord', '?')
        return f"{label} Δ {coord}.stage {old} → {new}"

    elif operation == 'lock_change':
        pipeline = details.get('pipeline', '?')
        action = details.get('action', '?')  # 'acquired' or 'released'
        return f"{label} Δ {pipeline}.lock {action}"

    elif operation == 'dispatch':
        agent = details.get('agent', '?')
        coord = details.get('coord', '?')
        stage = details.get('stage', '')
        return f"{label} Δ {coord}.dispatch → {agent}" + (f" ({stage})" if stage else "")

    elif operation == 'handoff':
        src = details.get('src', '?')
        dst = details.get('dst', '?')
        coord = details.get('coord', '?')
        return f"{label} Δ {coord}.handoff {src} → {dst}"

    return f"{label} Δ {operation}"


def generate_f_label_revert(details: dict) -> list[str]:
    """Generate F-labels for a revert operation (Phase 2 R1).

    Uses ⮌ (U+2B8C return arrow) instead of Δ to distinguish reverts
    from forward mutations. Any system processing F-labels can differentiate
    forward mutations from backward reverts without extra metadata.

    Returns a list of F-label strings (stage change + optional agent change).
    """
    labels = []
    coord = details.get('coord', '?')
    old_stage = details.get('old_stage', '?')
    new_stage = details.get('new_stage', '?')
    labels.append(f"{_next_f_label()} ⮌ {coord}.stage {old_stage} → {new_stage}")

    old_agent = details.get('old_agent')
    new_agent = details.get('new_agent')
    if old_agent and new_agent and old_agent != new_agent:
        labels.append(f"{_next_f_label()} ⮌ {coord}.agent {old_agent} → {new_agent}")

    return labels


def handle_revert(version: str, timestamp: str, force: bool = False) -> dict:
    """Handle time-travel revert via CLI (Phase 2 R1).

    Calls temporal overlay's time_travel_revert() to revert pipeline state
    to the specified timestamp. Generates F-labels with ⮌ format.

    Args:
        version: Pipeline version string (or coordinate like p1)
        timestamp: ISO-8601 timestamp to revert to
        force: If True, allow cross-phase reverts (with warning)

    Returns:
        Result dict with success, f_labels, r_label_hint, etc.
    """
    version = resolve_pipeline(version) or version
    temporal = _get_temporal()
    if not temporal:
        return {'status': 'error', 'error': 'Temporal DB unavailable'}

    # Phase boundary guard (Critic Q1): warn but allow with --force
    if not force:
        state = load_state_json(version)
        current_stage = state.get('pending_action', '')
        # Check if revert would cross phase boundary
        target_state = temporal.time_travel(version, timestamp)
        if target_state:
            target_stage = target_state.get('to_stage', '')
            current_phase = _get_phase(current_stage)
            target_phase = _get_phase(target_stage)
            if current_phase != target_phase and current_phase and target_phase:
                return {
                    'status': 'blocked',
                    'error': f'Cross-phase revert ({current_phase} → {target_phase}). '
                             f'Use --force to override.',
                    'current_phase': current_phase,
                    'target_phase': target_phase,
                }

    result = temporal.time_travel_revert(version, timestamp)
    if not result:
        return {'status': 'error', 'error': f'Revert failed for {version} at {timestamp}'}

    if result.get('noop'):
        return {'status': 'noop', 'message': 'Current state matches target — no revert needed.'}

    # Generate engine-level F-labels
    coord = _get_pipeline_coord(version)
    f_labels = generate_f_label_revert({
        'coord': coord,
        'old_stage': result['reverted_from'],
        'new_stage': result['reverted_to'],
    })

    result['engine_f_labels'] = f_labels
    result['status'] = 'reverted'
    return result


def _get_phase(stage: str) -> str:
    """Extract phase from a stage name. Returns 'phase1', 'phase2', etc."""
    if stage.startswith('phase2_'):
        return 'phase2'
    elif stage.startswith('analysis_') or stage.startswith('local_analysis_'):
        return 'analysis'
    elif stage in ('phase1_complete', 'phase2_complete'):
        return stage.replace('_complete', '')
    else:
        return 'phase1'


# ─── Dispatch Payload (Structured, Zero Coordinator Tokens) ────────────────────

@dataclass
class DispatchPayload:
    """Fully-formed dispatch instruction. Coordinator relays mechanically.

    The payload format is forward-compatible with numeric indexing:
    - pipeline_coord: 'p1' (future: index into field-level addressing)
    - agent_index: integer position in agent roster (future: 7i1 = field 7, index 1)
    - stage can be addressed by index (future: stage_index)
    """

    # Core spawn parameters
    agent: str                               # Target agent name
    task: str                                # Full prompt text (from template)
    model: Optional[str] = None              # Model override (None = agent default)
    timeout: int = 600                       # Seconds
    label: str = ''                          # Human-readable: "{version}/{stage}"
    session_id: str = ''                     # Fresh UUID4
    background: bool = True                  # Always True for pipeline work

    # Lifecycle actions — METADATA ONLY (FLAG-3 clarification)
    # The engine executes pre/post_actions BEFORE returning the payload.
    # They appear in the payload for audit/logging purposes only.
    # The coordinator NEVER executes these — it only relays spawn{}.
    # In headless mode: engine executes actions + dispatch in one shot.
    # In interactive mode: engine executes actions, then returns spawn{} for relay.
    pre_actions: list = field(default_factory=list)
    post_actions: list = field(default_factory=list)

    # Context metadata (informational, forward-compatible with numeric indexing)
    pipeline_version: str = ''
    pipeline_coord: str = ''                 # e.g., 'p1' (future: numeric index)
    current_stage: str = ''
    agent_index: int = 0                     # Position in agent roster (future: field 7 index)
    stage_index: int = 0                     # Position in stage sequence (future: coordinate)
    files_to_read: list = field(default_factory=list)
    completion_command: str = ''

    # Phase 2 R2: Persona-based view filter metadata.
    # Orchestration sets the view when dispatching — agents don't choose (D5).
    view_filter: Optional[dict] = None

    # Phase 2: Pre-rendered .v5 R-label trail for agent situational awareness.
    # The engine renders the trail and embeds it — agents don't need UDS access (D5).
    view_context: str = ''

    def to_dict(self) -> dict:
        """Serialize for JSON output / tool relay.

        The coordinator only uses the 'spawn' block — everything else is
        metadata for audit/logging. pre/post_actions are already executed
        by the engine before this payload is returned (FLAG-3).
        """
        return {
            '_dispatch': True,
            '_version': 'orchestration-engine-v2',
            'spawn': {
                'agent': self.agent,
                'task': self.task,
                'model': self.model,
                'timeout': self.timeout,
                'label': self.label,
                'session_id': self.session_id,
                'background': self.background,
            },
            # These are METADATA — already executed by the engine.
            # Included for audit trail and handoff records only.
            'pre_actions_executed': self.pre_actions,
            'post_actions_executed': self.post_actions,
            'context': {
                'pipeline_version': self.pipeline_version,
                'pipeline_coord': self.pipeline_coord,
                'current_stage': self.current_stage,
                'agent_index': self.agent_index,
                'stage_index': self.stage_index,
                'files_to_read': self.files_to_read,
                'completion_command': self.completion_command,
                'view_filter': self.view_filter,  # Phase 2 R2: persona view metadata
                'view_context': self.view_context,  # Phase 2: pre-rendered .v5 trail
            },
        }

    def to_spawn_args(self) -> list[str]:
        """Convert to openclaw agent CLI args for direct execution."""
        args = ['openclaw', 'agent', 'spawn', self.agent]
        if self.model:
            args.extend(['--model', self.model])
        args.extend(['--timeout', str(self.timeout)])
        if self.label:
            args.extend(['--label', self.label])
        if self.background:
            args.append('--background')
        args.extend(['--task', self.task])
        return args


# Agent roster with defaults (forward-compatible with numeric indexing)
AGENT_ROSTER = {
    'architect': {'index': 1, 'model': 'anthropic/claude-sonnet-4-20250514', 'timeout': 600},
    'critic':    {'index': 2, 'model': 'anthropic/claude-sonnet-4-20250514', 'timeout': 600},
    'builder':   {'index': 3, 'model': 'anthropic/claude-sonnet-4-20250514', 'timeout': 900},
}

# Stage sequence for numeric indexing (forward-compatible)
STAGE_SEQUENCE = [
    'pipeline_created',
    'architect_design',
    'critic_design_review',
    'builder_implementation',
    'critic_code_review',
    'phase1_complete',
    'phase2_architect_design',
    'phase2_critic_design_review',
    'phase2_builder_implementation',
    'phase2_critic_code_review',
    'phase2_complete',
]


def _get_pipeline_coord(version: str) -> str:
    """Get the p-coordinate for a pipeline version string."""
    versions = _get_active_versions()
    try:
        idx = versions.index(version)
        return f'p{idx + 1}'
    except ValueError:
        return 'p?'


def _build_completion_command(version: str, stage: str, agent: str) -> str:
    """Build the CLI completion command agents use when done."""
    return (f'python3 scripts/pipeline_orchestrate.py {version} complete {stage} '
            f'--agent {agent} --notes "your summary" '
            f'--learnings "key decisions, patterns discovered, insights worth keeping"')


def _build_block_command(version: str, stage: str, agent: str) -> str:
    """Build the CLI block command agents use to report issues."""
    return (f'python3 scripts/pipeline_orchestrate.py {version} block {stage} '
            f'--agent {agent} --notes "BLOCK reason" --artifact your_review_file.md '
            f'--learnings "what I found, why it\'s blocked, what the fix should look like"')


def _build_task_prompt(version: str, stage: str, agent: str,
                       notes: str = '', files: list = None,
                       is_resume: bool = False, resume_count: int = 0,
                       partial_files: list = None) -> str:
    """Build the full task prompt for an agent dispatch.

    Centralizes all prompt construction — coordinator never touches this.
    """
    files = files or []
    partial_files = partial_files or []
    comp_cmd = _build_completion_command(version, stage, agent)
    block_cmd = _build_block_command(version, stage, agent)
    files_list = '\n'.join(f'  - {f}' for f in files) if files else '  (no specific files)'

    if is_resume:
        partial_list = '\n'.join(f'  - {f}' for f in partial_files) if partial_files else '  (none detected)'
        return f"""🔄 RESUME — Pipeline {version} / Stage: {stage}
Attempt {resume_count + 1} of {MAX_RESUMES + 1} (previous session timed out)

⚠️ This is a FRESH session — you have NO context from the previous attempt.
Read your memory files first: they contain a checkpoint of what happened.

**Partial work detected:**
{partial_list}

**Critical:** Read your memory files FIRST. Continue from where the previous session left off.

**When you finish:**
```
{comp_cmd}
```

If you need to BLOCK:
```
{block_cmd}
```
"""

    # Determine reasoning flag for analysis stages
    is_local_analysis = 'local_analysis' in stage
    reasoning_block = ""
    if is_local_analysis:
        reasoning_block = """
⚠️ **REASONING REQUIRED** — Use extended thinking for this task. Think deeply about
the statistical patterns, architecture implications, and what additional analysis
would reveal. Quality of insight matters more than speed.
"""

    return f"""🔄 Pipeline Handoff — {version}

**Stage completed:** {_previous_stage(stage) or 'initial'}
**Your task:** {stage}
**Summary:** {notes or '(no notes from previous stage)'}
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
   - **Create primitives in the MAIN workspace** for significant work:

5. **Create primitives for SIGNIFICANT work only:**

   **Memory entries** (only for genuine insights, surprising findings, or architectural discoveries — NOT for routine stage completions. Pipeline stage tracking is automatic):
   ```bash
   # Only use this when you discovered something worth remembering across sessions
   python3 /home/ubuntu/.openclaw/workspace/scripts/log_memory.py \\
     --workspace /home/ubuntu/.openclaw/workspace \\
     --importance 3 \\
     --tags "instance:{agent},pipeline:{version}" \\
     "Description of the insight or finding (not just 'completed stage X')"
   ```

   **Lessons** (when you discover reusable patterns, mistakes to avoid, or surprising findings):
   ```bash
   python3 /home/ubuntu/.openclaw/workspace/scripts/create_primitive.py lesson <slug> \\
     --workspace /home/ubuntu/.openclaw/workspace \\
     --tags "instance:{agent},pipeline:{version}" \\
     --set "status=active" \\
     --set "importance=high"
   # Then edit the body with the lesson content using Edit tool
   ```

   **Decisions** (when you make architectural choices, technology selections, or scope boundaries):
   ```bash
   python3 /home/ubuntu/.openclaw/workspace/scripts/create_primitive.py decision <slug> \\
     --workspace /home/ubuntu/.openclaw/workspace \\
     --tags "instance:{agent},pipeline:{version}" \\
     --set "status=accepted"
   # Then edit the body with: context, options considered, rationale, consequences
   ```

   **Create at least 1 memory entry per stage. Create lessons and decisions whenever your work produces reusable knowledge or makes a choice that future agents should know about.**

**Read these files before starting:**
{files_list}

**Pipeline state:** `python3 scripts/pipeline_update.py {version} show`

**When you finish, call the orchestrator (it auto-saves your memory):**
```
{comp_cmd}
```

The `--learnings` flag is written directly to your memory files before the handoff — this is your continuity across sessions. Be specific about what you'd want to know next time you wake up fresh.

If you need to BLOCK, use:
```
{block_cmd}
```

Post your status update to the group chat (Telegram group -5243763228) when done."""


def _previous_stage(stage: str) -> str | None:
    """Get the stage that precedes this one in the sequence."""
    try:
        idx = STAGE_SEQUENCE.index(stage)
        return STAGE_SEQUENCE[idx - 1] if idx > 0 else None
    except ValueError:
        return None


def _files_for_stage(version: str, stage: str, agent: str) -> list[str]:
    """Determine which files an agent should read for a given stage.

    Includes agent-specific knowledge files and pipeline artifacts.
    """
    AGENT_KNOWLEDGE = {
        'architect': 'research/ARCHITECT_KNOWLEDGE.md',
        'critic': 'research/CRITIC_KNOWLEDGE.md',
        'builder': 'research/BUILDER_KNOWLEDGE.md',
    }

    base_files = ['research/AGENT_SOUL.md']

    # Agent knowledge file
    knowledge = AGENT_KNOWLEDGE.get(agent)
    if knowledge:
        knowledge_path = ML_DIR / knowledge.replace('research/', 'research/')
        if not knowledge_path.exists():
            knowledge_path = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / knowledge
        if knowledge_path.exists():
            base_files.append(knowledge)

    # Analysis pipelines get analysis roles
    is_analysis = 'analysis' in version or 'analysis' in stage
    if is_analysis:
        base_files.append('research/ANALYSIS_AGENT_ROLES.md')

    # Task file (if exists)
    task_candidates = list(WORKSPACE.glob(f'tasks/*{version}*'))
    for tc in task_candidates:
        base_files.append(str(tc.relative_to(WORKSPACE)))

    # Determine phase prefix for artifact lookup
    is_phase2 = 'phase2' in stage
    phase_prefix = 'phase2_' if is_phase2 else ''

    def _find_build_artifact(filename: str) -> Path | None:
        """Check workspace pipeline_builds/ first, then research pipeline_builds/."""
        for d in (BUILDS_DIR, RESEARCH_BUILDS_DIR):
            p = d / filename
            if p.exists():
                return p
        return None

    # Previous stage artifacts
    if 'critic' in stage and ('design' in stage or 'review' in stage):
        # Critics review the architect's design
        if is_analysis:
            design_file = _find_build_artifact(f'{version}_{phase_prefix}architect_analysis_design.md')
        else:
            design_file = _find_build_artifact(f'{version}_{phase_prefix}architect_design.md')
        if design_file:
            base_files.append(str(design_file.relative_to(WORKSPACE)))

    if 'builder' in stage or 'implementation' in stage:
        # Builders read design + critic review
        for suffix in [f'{phase_prefix}architect_design.md', f'{phase_prefix}critic_design_review.md']:
            f = _find_build_artifact(f'{version}_{suffix}')
            if f:
                base_files.append(str(f.relative_to(WORKSPACE)))

    if 'code_review' in stage:
        # Code reviewers read the notebook/implementation
        # Try to find the actual notebook
        notebooks_dir = ML_DIR / 'notebooks'
        notebook_patterns = [
            f'crypto_{version}_predictor.ipynb',
            f'crypto_{version.replace("-", "_")}_predictor.ipynb',
            f'crypto_{version}_analysis.ipynb',
        ]
        for pattern in notebook_patterns:
            nb_file = notebooks_dir / pattern
            if nb_file.exists():
                base_files.append(str(nb_file.relative_to(WORKSPACE)))
                break

    return base_files


def _detect_partial_work(version: str, window_minutes: int = 12) -> list[str]:
    """Scan pipeline_builds/ for recently-modified files matching this version."""
    partial = []
    if not BUILDS_DIR.exists():
        return partial
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    for f in BUILDS_DIR.glob(f'{version}*'):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime > cutoff:
                partial.append(str(f.relative_to(WORKSPACE)))
        except OSError:
            pass
    return partial


def build_dispatch_payload(version: str, stage: str, agent: str,
                            notes: str = '', is_resume: bool = False,
                            resume_count: int = 0) -> DispatchPayload:
    """Build a structured dispatch payload. Zero coordinator reasoning tokens.

    The coordinator receives this and relays spawn parameters mechanically.
    """
    version = resolve_pipeline(version) or version
    coord = _get_pipeline_coord(version)
    agent_info = AGENT_ROSTER.get(agent, {})
    session_id = str(uuid.uuid4())
    files = _files_for_stage(version, stage, agent)
    partial = _detect_partial_work(version) if is_resume else []

    task = _build_task_prompt(
        version, stage, agent, notes, files,
        is_resume=is_resume, resume_count=resume_count,
        partial_files=partial,
    )

    # V2-temporal: inject persistent agent context into task prompt
    temporal = _get_temporal()
    view_filter = None
    if temporal:
        lineage = temporal.get_design_lineage(version, agent)
        if lineage:
            task += f"\n\n## Your Persistent Context (Pipeline Memory)\n{lineage}\n"

        # Phase 2 R2: Inject persona-filtered dashboard into task prompt.
        # Orchestration sets the view filter when dispatching — agents don't choose (D5).
        persona = agent  # Agent name maps to persona
        filtered_dashboard = temporal.format_dashboard_for_prompt(persona=persona)
        if filtered_dashboard:
            task += f"\n\n## Autoclave Dashboard (filtered for {persona})\n{filtered_dashboard}\n"

        # Build view_filter metadata for dispatch payload
        try:
            from temporal_overlay import PERSONA_STAGE_FILTERS
            pf = PERSONA_STAGE_FILTERS.get(persona, {})
            view_filter = {
                'persona': persona,
                'persona_coord': f'i{agent_info.get("index", 0)}',
                'show_stages': pf.get('show_stages', []),
                'show_sections': pf.get('show_sections', []),
                'highlight_fields': pf.get('highlight_fields', []),
            }
        except ImportError:
            pass

    # Phase 2: Generate pre-rendered .v5 R-label trail for agent situational awareness.
    # Agents receive a rendered snapshot, not query capabilities (D5).
    trail_context = ''
    try:
        from monitoring_views import render_r_label_trail
        trail_context = render_r_label_trail(pipeline=version, window_minutes=10)
    except (ImportError, Exception):
        pass  # Non-fatal

    return DispatchPayload(
        agent=agent,
        task=task,
        model=agent_info.get('model'),
        timeout=agent_info.get('timeout', 600),
        label=f'{version}/{stage}',
        session_id=session_id,
        background=True,
        pre_actions=[
            {'action': 'session_reset', 'agent': agent},
            {'action': 'memory_consolidate', 'agent': agent, 'version': version, 'stage': stage},
        ],
        post_actions=[
            {'action': 'write_handoff', 'version': version, 'stage': stage, 'agent': agent},
            {'action': 'notify', 'channel': 'telegram', 'message': f'🏗️ {agent.title()} dispatched for {version}/{stage}'},
        ],
        pipeline_version=version,
        pipeline_coord=coord,
        current_stage=stage,
        agent_index=agent_info.get('index', 0),
        stage_index=STAGE_SEQUENCE.index(stage) if stage in STAGE_SEQUENCE else -1,
        files_to_read=files,
        completion_command=_build_completion_command(version, stage, agent),
        view_filter=view_filter,
        view_context=trail_context,
    )


# ─── Atomic Lock Acquire (TOCTOU fix — critic FLAG-1) ──────────────────────────

LOCKS_DIR = PIPELINES_DIR / 'locks'


def atomic_lock_acquire(pipeline: str, agent: str, pid: int = None,
                         timeout_minutes: int = 10) -> bool:
    """Acquire a pipeline lock atomically using O_CREAT|O_EXCL.

    Prevents TOCTOU race condition where two concurrent processes both
    see "no lock" and both write. The kernel guarantees only one O_EXCL
    open succeeds.

    Staleness detection (FLAG-4 fix):
    - PRIMARY: timeout_at — if past timeout, lock is stale regardless of PID
    - SECONDARY: PID liveness — if PID is dead, lock is stale even before timeout
    - Rationale: In OpenClaw's architecture, agent sessions run within the
      gateway's Node.js process. When orchestration_engine.py is called as a
      CLI script, the PID is the short-lived Python process that exits
      immediately. Timeout-based staleness is the only reliable mechanism
      for the agent dispatch → agent complete lifecycle.

    Returns True if lock acquired, False if already locked by live process.
    """
    if pid is None:
        pid = os.getpid()

    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = LOCKS_DIR / f'{pipeline}.lock.json'

    # Check if existing lock is stale
    if lock_file.exists():
        try:
            existing = json.loads(lock_file.read_text())
            stale = False
            stale_reason = ''

            # PRIMARY: timeout-based staleness (most reliable)
            timeout_at = existing.get('timeout_at')
            if timeout_at:
                try:
                    dt = datetime.fromisoformat(timeout_at)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) > dt:
                        stale = True
                        stale_reason = 'past_timeout'
                except ValueError:
                    pass

            # SECONDARY: PID liveness hint (catches early exits)
            if not stale:
                existing_pid = existing.get('pid')
                if existing_pid and not _pid_alive(existing_pid):
                    stale = True
                    stale_reason = 'pid_dead'
                elif existing_pid and _pid_alive(existing_pid):
                    # PID alive and not past timeout — genuinely locked
                    return False

            if stale:
                lock_file.unlink(missing_ok=True)
                fl = generate_f_label('lock_change', {
                    'pipeline': pipeline,
                    'action': f'stale_cleared ({stale_reason})'
                })
                print(f'  {fl}')
            else:
                return False  # Lock exists, not clearly stale
        except (json.JSONDecodeError, OSError):
            lock_file.unlink(missing_ok=True)

    # Atomic create: O_CREAT|O_EXCL guarantees only one process wins
    lock_data = {
        'pipeline': pipeline,
        'agent': agent,
        'pid': pid,
        'session_id': str(uuid.uuid4()),
        'acquired_at': datetime.now(timezone.utc).isoformat(),
        'timeout_at': (datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)).isoformat(),
        'resume_count': 0,
    }

    try:
        fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        try:
            os.write(fd, json.dumps(lock_data, indent=2).encode())
        finally:
            os.close(fd)
        fl = generate_f_label('lock_change', {'pipeline': pipeline, 'action': 'acquired'})
        print(f'  {fl}')
        return True
    except FileExistsError:
        # Another process won the race
        return False


def atomic_lock_release(pipeline: str) -> bool:
    """Release a pipeline lock. Returns True if lock existed."""
    lock_file = LOCKS_DIR / f'{pipeline}.lock.json'
    if lock_file.exists():
        lock_file.unlink(missing_ok=True)
        fl = generate_f_label('lock_change', {'pipeline': pipeline, 'action': 'released'})
        print(f'  {fl}')
        return True
    return False


def _pid_alive(pid: int) -> bool:
    """Check if a PID is alive."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, TypeError):
        return True


def list_central_locks() -> list[dict]:
    """List all centralized pipeline locks."""
    locks = []
    if not LOCKS_DIR.exists():
        return locks
    for f in LOCKS_DIR.glob('*.lock.json'):
        try:
            data = json.loads(f.read_text())
            pid = data.get('pid')
            data['pid_alive'] = _pid_alive(pid) if pid else False
            acquired = data.get('acquired_at', '')
            data['age_minutes'] = minutes_since(acquired)
            timeout_at = data.get('timeout_at', '')
            if timeout_at:
                try:
                    dt = datetime.fromisoformat(timeout_at)
                    data['past_timeout'] = datetime.now(timezone.utc) > dt
                except ValueError:
                    data['past_timeout'] = False
            # FLAG-4: timeout is PRIMARY staleness signal, PID is SECONDARY hint
            data['stale'] = data.get('past_timeout', False) or (not data['pid_alive'])
            data['stale_reason'] = (
                'past_timeout' if data.get('past_timeout') else
                'pid_dead' if not data['pid_alive'] else
                None
            )
            data['_path'] = str(f)
            locks.append(data)
        except (json.JSONDecodeError, OSError):
            locks.append({'_path': str(f), 'stale': True, 'error': 'unreadable'})
    return locks


# ─── Hook Verification (critic FLAG-2) ─────────────────────────────────────────

def verify_hooks() -> dict:
    """Verify that orchestration-relevant hooks are properly configured.

    Checks:
    1. before_prompt_build — pipeline-context plugin injects pipeline state
    2. Hook naming conventions (colons for internal, underscores for plugin)
    3. Plugin files exist and are valid
    4. agent_end hook availability

    Returns dict with verification results for each hook.
    """
    results = {
        'before_prompt_build': {'status': 'unknown', 'details': ''},
        'agent_end': {'status': 'unknown', 'details': ''},
        'plugins': [],
        'naming_conventions': {'status': 'ok', 'issues': []},
    }

    # Check pipeline-context plugin
    plugin_dirs = [
        WORKSPACE / 'plugins' / 'pipeline-context',
        WORKSPACE / '.openclaw' / 'extensions' / 'pipeline-context',
    ]
    for pd in plugin_dirs:
        index_file = pd / 'index.ts'
        if index_file.exists():
            content = index_file.read_text()
            if 'before_prompt_build' in content:
                results['before_prompt_build'] = {
                    'status': 'found',
                    'details': f'Plugin at {pd} registers before_prompt_build hook',
                }
            results['plugins'].append({
                'path': str(pd),
                'exists': True,
                'has_hook': 'before_prompt_build' in content,
            })

    if results['before_prompt_build']['status'] == 'unknown':
        results['before_prompt_build'] = {
            'status': 'not_found',
            'details': 'No pipeline-context plugin found. Pipeline state injection via hooks unavailable.',
        }

    # Check codex-cockpit plugin (R-label separation)
    cockpit_dir = WORKSPACE / 'plugins' / 'codex-cockpit'
    cockpit_index = cockpit_dir / 'index.ts'
    if cockpit_index.exists():
        content = cockpit_index.read_text()
        if 'F-label' in content or 'f-label' in content or 'F_label' in content:
            results['plugins'].append({
                'path': str(cockpit_dir),
                'exists': True,
                'f_label_boundary': True,
                'note': 'Cockpit owns R-labels, engine owns F-labels. Boundary documented.',
            })

    # Check agent_end hook availability
    agent_turn_logger = WORKSPACE / 'plugins' / 'agent-turn-logger'
    if agent_turn_logger.exists():
        results['agent_end'] = {
            'status': 'available',
            'details': 'agent-turn-logger plugin exists. agent_end hook can capture handoff metadata.',
        }
    else:
        results['agent_end'] = {
            'status': 'not_deployed',
            'details': 'agent-turn-logger not deployed. agent_end capture deferred (Phase 2).',
        }

    # Check naming conventions in all plugin files
    for plugin_dir in (WORKSPACE / 'plugins').iterdir() if (WORKSPACE / 'plugins').exists() else []:
        if not plugin_dir.is_dir():
            continue
        for ts_file in plugin_dir.glob('*.ts'):
            try:
                content = ts_file.read_text()
                # Internal hooks use colons: agent:bootstrap, before_prompt_build
                # Plugin hooks use underscores: before_prompt_build, after_tool_call
                # Flag any that mix conventions incorrectly
                if 'agent.bootstrap' in content:  # Wrong: should be agent:bootstrap
                    results['naming_conventions']['issues'].append(
                        f'{ts_file}: uses "agent.bootstrap" instead of "agent:bootstrap"'
                    )
                    results['naming_conventions']['status'] = 'warning'
            except OSError:
                pass

    return results


# ─── Import from existing scripts (reuse, don't rewrite) ───────────────────────

sys.path.insert(0, str(SCRIPTS))

try:
    from pipeline_autorun import (
        load_pipeline_frontmatter,
        load_state_json,
        get_active_pipelines,
        parse_timestamp,
        minutes_since,
    )
except ImportError as e:
    # Fallback inline implementations if import fails
    print(f"WARN: Could not import from pipeline_autorun: {e}")

    def load_pipeline_frontmatter(path: Path) -> dict:
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
                if val.startswith('[') and val.endswith(']'):
                    val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(',')]
                result[key.strip()] = val
        return result

    def load_state_json(version: str) -> dict:
        state_file = BUILDS_DIR / f'{version}_state.json'
        if state_file.exists():
            return json.load(open(state_file))
        return {}

    def get_active_pipelines() -> list:
        pipelines = []
        if not PIPELINES_DIR.exists():
            return pipelines
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

    def parse_timestamp(ts: str):
        if not ts:
            return None
        for fmt in ['%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%SZ',
                     '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
            try:
                dt = datetime.strptime(ts, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        return None

    def minutes_since(ts: str):
        dt = parse_timestamp(ts)
        if not dt:
            return None
        return (datetime.now(timezone.utc) - dt).total_seconds() / 60

try:
    from pipeline_orchestrate import (
        reset_agent_session,
        wake_agent,
        consolidate_agent_memory,
        checkpoint_and_resume,
        write_handoff,
        get_pending_handoffs,
        build_handoff_message,
        generate_session_id,
        orchestrate_complete,
        orchestrate_block,
        orchestrate_show,
        send_orchestrator_notification,
        AGENT_INFO,
    )
    _HAS_ORCHESTRATE = True
except ImportError as e:
    print(f"WARN: Could not import from pipeline_orchestrate: {e}")
    _HAS_ORCHESTRATE = False

try:
    from launch_pipeline import (
        create_pipeline as _create_pipeline,
        list_pipelines as _list_pipelines,
        check_archivable,
        archive_pipeline,
        auto_archive_downstream_tasks,
        link_tasks_to_pipeline,
    )
    _HAS_LAUNCH = True
except ImportError as e:
    print(f"WARN: Could not import from launch_pipeline: {e}")
    _HAS_LAUNCH = False


# ─── Coordinate Resolution ─────────────────────────────────────────────────────

def _get_active_versions() -> list[str]:
    """Get sorted list of active pipeline version strings."""
    pipelines = get_active_pipelines()
    return [p['version'] for p in pipelines]


def resolve_pipeline(ref: str) -> str | None:
    """Resolve a pipeline reference to a version string.

    Accepts:
      - version string: 'stack-specialists'
      - bare number: '3' (3rd active pipeline, 1-indexed)
      - coordinate: 'p3' (same as '3')
    Returns the version string, or None if unresolvable.
    """
    if not ref:
        return None

    ref = ref.strip()

    # Strip 'p' prefix for coordinate notation
    bare = ref
    if ref.startswith('p') and len(ref) > 1 and ref[1:].isdigit():
        bare = ref[1:]

    # Try numeric index (1-based)
    if bare.isdigit():
        idx = int(bare) - 1
        versions = _get_active_versions()
        if 0 <= idx < len(versions):
            return versions[idx]
        return None

    # Try exact version match
    pipeline_file = PIPELINES_DIR / f'{ref}.md'
    if pipeline_file.exists():
        return ref

    # Try partial match
    versions = _get_active_versions()
    matches = [v for v in versions if ref.lower() in v.lower()]
    if len(matches) == 1:
        return matches[0]

    return None


# ─── Pipeline Status ────────────────────────────────────────────────────────────

def pipeline_status(version: str) -> dict:
    """Return full pipeline state as a dict.

    Keys: version, status, stage, pending_action, agent, last_updated,
          locks, gates, next_action, stages, frontmatter
    """
    version = resolve_pipeline(version) or version
    state = load_state_json(version)
    pipeline_file = PIPELINES_DIR / f'{version}.md'

    if not state and not pipeline_file.exists():
        return {'version': version, 'error': 'not_found'}

    fm = {}
    if pipeline_file.exists():
        fm = load_pipeline_frontmatter(pipeline_file)

    pending = state.get('pending_action', 'none')
    last_updated = state.get('last_updated', '')

    # Determine current agent from pending action
    agent = _agent_from_action(pending)

    # Check locks
    locks = _get_locks_for(version)

    # Determine next action
    next_act = pipeline_next_action(version)

    # Gate status
    gates = _gate_status_for(version, fm, state)

    return {
        'version': version,
        'status': fm.get('status', state.get('status', 'unknown')),
        'pending_action': pending,
        'agent': agent,
        'last_updated': last_updated,
        'last_updated_ago': _format_age(minutes_since(last_updated)),
        'locks': locks,
        'gates': gates,
        'next_action': next_act,
        'stages': state.get('stages', {}),
        'priority': fm.get('priority', 'normal'),
        'frontmatter': fm,
    }


def pipeline_next_action(version: str) -> str | None:
    """What should happen next for this pipeline?

    Returns a human-readable action description, or None if nothing to do.
    """
    version = resolve_pipeline(version) or version
    state = load_state_json(version)
    pipeline_file = PIPELINES_DIR / f'{version}.md'
    fm = load_pipeline_frontmatter(pipeline_file) if pipeline_file.exists() else {}

    pending = state.get('pending_action', 'none')
    status = fm.get('status', state.get('status', ''))
    last_updated = state.get('last_updated', '')
    elapsed = minutes_since(last_updated)

    if pending == 'none' or not pending:
        return None

    # Human-gated stages
    if pending == 'pipeline_created':
        return f'Kick off pipeline: dispatch architect for design'
    if pending == 'phase1_complete':
        # Check for revision requests
        rev_file = BUILDS_DIR / f'{version}_revision_request.md'
        if rev_file.exists():
            return f'Process pending revision request'
        return f'Human gate: Phase 1 complete, awaiting experiment run or Phase 2 direction'
    if pending == 'local_analysis_complete':
        direction_file = BUILDS_DIR / f'{version}_phase2_shael_direction.md'
        if direction_file.exists():
            return f'Phase 2 direction file found -- kick off Phase 2'
        return f'Human gate: local analysis complete, awaiting Phase 2 direction'
    if pending in HUMAN_ACTIONS:
        return f'Human gate: {pending}'

    # Agent actions — check if stalled
    if pending in AGENT_ACTIONS:
        agent = _agent_from_action(pending)
        if elapsed is not None and elapsed > STALL_THRESHOLD_MINUTES:
            return f'STALLED: {agent} has not completed {pending} ({elapsed:.0f}min). Recovery needed.'
        elif elapsed is not None:
            return f'In progress: {agent} working on {pending} ({elapsed:.0f}min ago)'
        return f'In progress: {agent} working on {pending}'

    return f'Unknown pending action: {pending}'


def _agent_from_action(action: str) -> str:
    """Infer agent name from a pending action string."""
    if not action or action == 'none':
        return 'none'
    if 'architect' in action:
        return 'architect'
    if 'critic' in action:
        return 'critic'
    if 'builder' in action:
        return 'builder'
    if 'experiment' in action:
        return 'system'
    if 'report' in action:
        return 'system'
    if action in HUMAN_ACTIONS:
        return 'human-gate'
    return 'unknown'


def _format_age(minutes) -> str:
    """Format minutes into human-readable age string."""
    if minutes is None:
        return 'unknown'
    if minutes < 1:
        return 'just now'
    if minutes < 60:
        return f'{minutes:.0f}m ago'
    hours = minutes / 60
    if hours < 24:
        return f'{hours:.1f}h ago'
    days = hours / 24
    return f'{days:.1f}d ago'


def _get_locks_for(version: str) -> list[dict]:
    """Get active locks relevant to a pipeline version."""
    all_locks = list_locks()
    # All locks are agent-level, not pipeline-specific, but relevant
    return all_locks


def _gate_status_for(version: str, fm: dict, state: dict) -> dict:
    """Determine gate status for a pipeline.

    Supports two gate definition sources:
    1. Declarative gates in frontmatter (FLAG-2: preferred for stored conditions):
       gates:
         phase2_start: "self.status == phase1_complete"
         analysis_gate: "v4-deep-analysis.status == phase2_complete"
       Version strings (e.g., "v4-deep-analysis.status") are preferred over
       coordinate references (e.g., "p2.status") because coordinates shift
       when pipelines are archived.

    2. Heuristic gates (fallback when no gates: in frontmatter):
       Checks direction files, status strings, etc.
    """
    pending = state.get('pending_action', 'none')
    status = fm.get('status', '')
    gates = {}

    # Check for declarative gates in frontmatter (FLAG-2)
    declared_gates = fm.get('gates', {})
    if isinstance(declared_gates, dict) and declared_gates:
        for gate_name, condition in declared_gates.items():
            if isinstance(condition, str):
                is_open, detail = _resolve_gate_condition(condition, fm, version)
                gates[gate_name] = {
                    'status': 'open' if is_open else 'closed',
                    'condition': condition,
                    'resolved': detail,
                }
        return gates

    # Fallback: heuristic gates (backward compat with existing pipelines)
    # Phase 2 gate
    if 'phase1_complete' in pending or 'phase1_complete' in status:
        gates['phase2'] = 'open' if BUILDS_DIR.joinpath(
            f'{version}_phase2_shael_direction.md').exists() else 'closed'

    # Phase 3 gate
    phase2_status = state.get('phase2', {}).get('stage', '')
    gates['phase3'] = 'open' if 'complete' in phase2_status else 'locked'

    return gates


def _resolve_gate_condition(condition: str, self_fm: dict, self_version: str) -> tuple:
    """Resolve a gate condition string against current primitive state.

    Supports:
      "true"                                    — always open
      "self.status == phase1_complete"           — self-referential
      "v4-deep-analysis.status == phase2_complete"  — cross-pipeline by version (PREFERRED)
      "p2.status == phase2_complete"             — cross-pipeline by coordinate (FRAGILE)
      "tags contains infrastructure"             — tag-based

    Returns (is_open: bool, detail: str).

    FLAG-2 note: Coordinate references (p{N}) are fragile under archival —
    the index shifts when pipelines are archived. Use version strings for
    stored gate conditions. Coordinate syntax triggers a warning.
    """
    condition = condition.strip()

    # Always open
    if condition.lower() == 'true':
        return True, 'always open'

    # Self-referential: self.field == value
    if condition.startswith('self.'):
        field, _, expected = condition[5:].partition(' == ')
        actual = self_fm.get(field.strip(), '')
        return str(actual).strip() == expected.strip(), f'self.{field.strip()} = {actual}'

    # Cross-reference: <ref>.field == value
    match = re.match(r'([\w.-]+)\.(\w+)\s*==\s*(.+)', condition)
    if match:
        ref, field, expected = match.group(1), match.group(2), match.group(3).strip()

        # Check if ref is a coordinate (p{N}) — warn about fragility
        coord_match = re.match(r'^p(\d+)$', ref, re.IGNORECASE)
        if coord_match:
            print(f'  ⚠️  Gate uses coordinate "{ref}" which is fragile under archival. '
                  f'Consider using version string instead.', file=sys.stderr)
            resolved_version = resolve_pipeline(ref)
        else:
            # Treat ref as a version string (preferred, stable)
            resolved_version = ref
            # Verify the pipeline file exists
            pipeline_file = PIPELINES_DIR / f'{resolved_version}.md'
            if not pipeline_file.exists():
                return False, f'pipeline "{resolved_version}" not found'

        if resolved_version:
            ref_state = load_state_json(resolved_version)
            ref_fm = {}
            ref_pipeline = PIPELINES_DIR / f'{resolved_version}.md'
            if ref_pipeline.exists():
                ref_fm = load_pipeline_frontmatter(ref_pipeline)

            # Check the field in both frontmatter and state
            actual = ref_fm.get(field, ref_state.get(field, ''))
            return str(actual).strip() == expected, f'{resolved_version}.{field} = {actual}'
        else:
            return False, f'could not resolve "{ref}"'

    # Tag-based: tags contains <value>
    if 'tags contains' in condition.lower():
        parts = condition.lower().split('contains', 1)
        tag = parts[1].strip() if len(parts) > 1 else ''
        tags = self_fm.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]
        return tag in tags, f'tags = {tags}'

    return False, f'unparseable condition: {condition}'


# ─── Fire-and-Forget Dispatch (State Machine Core) ────────────────────────────

def fire_and_forget_dispatch(version: str, stage: str, agent: str,
                              message: str = '') -> dict:
    """Dispatch an agent non-blocking via subprocess.Popen.

    Architecture (new state-machine approach):
      1. Write pending_action / current_agent / last_dispatched to state JSON
      2. Launch `openclaw agent --message` via Popen (returns immediately)
      3. The pipeline-context plugin injects state into the agent's prompt
      4. The agent-end-telemetry plugin logs turn completion for check_completions()

    This replaces the blocking wake_agent() call. The orchestration script exits
    immediately; the agent runs independently in background.

    Returns: {'success': True/False, 'pid': int|None, 'error': str|None}
    """
    # --- Update state JSON first (state machine write) ---
    state_file = BUILDS_DIR / f'{version}_state.json'
    try:
        state = json.loads(state_file.read_text()) if state_file.exists() else {}
        # NOTE: Do NOT overwrite pending_action here — pipeline_update.py is the
        # single authority for that field via STAGE_TRANSITIONS. Overwriting it
        # here caused corruption (e.g. writing 'critic' instead of 'phase2_critic_code_review')
        # when callers passed agent role names instead of stage names.
        state['current_agent'] = stage  # stage name for dispatch tracking
        state['last_dispatched'] = datetime.now(timezone.utc).isoformat()
        state['dispatch_claimed'] = False
        state_file.write_text(json.dumps(state, indent=2))
    except Exception as e:
        return {'success': False, 'pid': None, 'error': f'State write failed: {e}'}

    # --- Build dispatch message ---
    if not message:
        message = (
            f'Pipeline dispatch: {version} / {stage}\n'
            f'Your task is stage `{stage}` for pipeline `{version}`.\n'
            f'The pipeline-context plugin has injected the full state above.\n'
            f'Read your task from `pending_action` in the state JSON, then complete it.'
        )

    # --- Fire and forget via Popen ---
    # NOTE: Do NOT pass --timeout here. Popen with start_new_session=True
    # already returns immediately. --timeout N sets the *agent's* runtime
    # limit (default 600s), so --timeout 1 was killing agents after 1 second.
    cmd = [
        'openclaw', 'agent',
        '--agent', agent,
        '--message', message,
    ]

    try:
        # Popen returns immediately — child process runs in background
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,   # Detach from our process group
        )
        return {'success': True, 'pid': proc.pid, 'error': None}
    except FileNotFoundError:
        return {'success': False, 'pid': None, 'error': 'openclaw CLI not found on PATH'}
    except Exception as e:
        return {'success': False, 'pid': None, 'error': str(e)}


# ─── Dispatch & Handoff ────────────────────────────────────────────────────────

def pipeline_dispatch(version: str, agent: str, stage: str = None,
                       structured: bool = False) -> bool | dict:
    """Dispatch an agent to work on a pipeline.

    If structured=True, returns a DispatchPayload dict instead of executing.
    This enables zero-coordinator-token relay — the coordinator just passes
    the JSON blob to sessions_spawn without reasoning about prompt construction.

    Returns True/dict if dispatch succeeded, False if failed.
    """
    version = resolve_pipeline(version) or version

    state = load_state_json(version)
    pending = state.get('pending_action', 'none')

    if stage is None:
        stage = pending

    if stage == 'none' or not stage:
        print(f'  No pending action for {version} -- nothing to dispatch')
        return False

    # Structured dispatch: build payload and return it
    if structured or '--json' in sys.argv:
        payload = build_dispatch_payload(version, stage, agent)
        fl = generate_f_label('dispatch', {
            'agent': agent, 'coord': _get_pipeline_coord(version), 'stage': stage
        })
        print(f'  {fl}', file=sys.stderr)
        return payload.to_dict()

    # Fire-and-forget dispatch (new state-machine approach — no blocking wake_agent)
    fl = generate_f_label('dispatch', {
        'agent': agent, 'coord': _get_pipeline_coord(version), 'stage': stage
    })
    print(f'  {fl}')

    result = fire_and_forget_dispatch(version, stage, agent)
    if result['success']:
        print(f'  Dispatched {agent} for {version}/{stage} (pid={result["pid"]})')
        return True
    else:
        print(f'  FAILED: {result.get("error", "")}')
        # Fallback to legacy orchestrate machinery if available
        if _HAS_ORCHESTRATE:
            print(f'  Falling back to legacy orchestrate dispatch...')
            if stage == 'pipeline_created' or stage == 'architect_design':
                return orchestrate_complete(version, 'pipeline_created', 'belam-main',
                                             f'Dispatched by orchestration_engine (fallback)')
            else:
                reset_agent_session(agent)
                session_id = generate_session_id(version, agent)
                handoff_msg = build_handoff_message(version, '', stage, agent,
                                                     f'Dispatched by orchestration engine for {stage}')
                # LEGACY: wake_agent is blocking — only used as fallback when Popen fails
                wake_result = wake_agent(agent, handoff_msg, timeout=600, session_id=session_id)
                if wake_result['success']:
                    write_handoff(version, '', stage, agent, wake_result, session_id)
                    return True
                return False
        return False


def pipeline_handoff(version: str, from_agent: str, to_agent: str, notes: str = '') -> bool:
    """Execute a handoff between agents.

    Captures output from from_agent, constructs context, spawns to_agent.
    Returns True on success.
    """
    version = resolve_pipeline(version) or version
    if not _HAS_ORCHESTRATE:
        print(f'ERROR: pipeline_orchestrate.py not available for handoff')
        return False

    state = load_state_json(version)
    pending = state.get('pending_action', 'none')

    # Consolidate outgoing agent's memory
    consolidate_agent_memory(from_agent, version, pending, notes)

    # Determine next stage from transition map
    try:
        from pipeline_update import STAGE_TRANSITIONS
        transition = STAGE_TRANSITIONS.get(pending)
        if transition:
            next_stage, expected_agent, _ = transition
            if to_agent != expected_agent:
                print(f'  WARN: expected {expected_agent} but dispatching to {to_agent}')
        else:
            next_stage = None
    except ImportError:
        next_stage = None

    if not next_stage:
        print(f'  No transition defined for {pending} -- manual handoff')
        next_stage = f'{to_agent}_task'

    # Use orchestrate_complete for the full handoff chain
    return orchestrate_complete(version, pending, from_agent, notes)


def pipeline_resume(version: str) -> bool:
    """Resume a stalled/timed-out pipeline from last checkpoint.

    Returns True if resume was dispatched.
    """
    version = resolve_pipeline(version) or version
    if not _HAS_ORCHESTRATE:
        print(f'ERROR: pipeline_orchestrate.py not available for resume')
        return False

    state = load_state_json(version)
    pending = state.get('pending_action', 'none')

    if pending in HUMAN_ACTIONS or pending == 'none':
        print(f'  {version}: at human gate or idle ({pending}) -- nothing to resume')
        return False

    agent = _agent_from_action(pending)
    if agent in ('unknown', 'none', 'system'):
        print(f'  {version}: cannot determine agent for {pending}')
        return False

    print(f'  F1 D {version}.resume {agent} for {pending}')
    reset_agent_session(agent)

    notes = f'Resume from stall. Pipeline {version} stage {pending}.'
    wake_result = checkpoint_and_resume(agent, version, pending, notes, resume_count=0)
    return wake_result.get('success', False)


# ─── Completion Detection (Event Loop) ────────────────────────────────────────

def check_completions(dry_run: bool = False) -> list[dict]:
    """Check agent_telemetry.jsonl for completed agent turns that signal handoffs.

    Called periodically by the heartbeat to replace the blocking wake_agent() wait.
    When a handoff is detected for an active pipeline, advances state and dispatches
    the next agent via fire_and_forget_dispatch().

    Flow:
      agent_end hook fires → telemetry logged → check_completions() picks it up
      → state advanced via pipeline_update.py → next agent dispatched

    Returns: list of processed events [{version, stage, agent, action, ...}]
    """
    logs_dir = WORKSPACE / 'logs'
    telemetry_file = logs_dir / 'agent_telemetry.jsonl'

    if not telemetry_file.exists():
        return []

    # Read all telemetry entries
    entries = []
    try:
        with open(telemetry_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f'  [check_completions] Failed to read telemetry: {e}')
        return []

    if not entries:
        return []

    # Get active pipelines
    active = {p['version']: p for p in get_active_pipelines()}
    if not active:
        return []

    # Track which telemetry entries we've already processed
    checkpoint_file = logs_dir / '.telemetry_checkpoint'
    last_processed_ts = ''
    if checkpoint_file.exists():
        try:
            last_processed_ts = checkpoint_file.read_text().strip()
        except Exception:
            pass

    # Filter to new entries with handoff_detected
    new_handoffs = [
        e for e in entries
        if e.get('handoff_detected')
        and e.get('timestamp', '') > last_processed_ts
    ]

    if not new_handoffs:
        return []

    processed = []
    newest_ts = last_processed_ts

    for entry in new_handoffs:
        ts = entry.get('timestamp', '')
        agent = entry.get('agent', 'unknown')
        pipeline = entry.get('pipeline')
        stage = entry.get('stage')
        handoff_target = entry.get('handoff_target')

        # Match against active pipelines
        matched_version = None
        if pipeline:
            # Try direct match
            if pipeline in active:
                matched_version = pipeline
            else:
                # Partial match (telemetry may have a slug, not full version)
                for ver in active:
                    if pipeline in ver or ver in pipeline:
                        matched_version = ver
                        break

        if not matched_version:
            # Try to match by agent + stage
            for ver, p in active.items():
                pending = p.get('pending_action', '')
                current_agent = p.get('state', {}).get('current_agent', '')
                if agent and current_agent and agent in current_agent:
                    matched_version = ver
                    break

        if not matched_version:
            if ts > newest_ts:
                newest_ts = ts
            continue

        version = matched_version
        pipeline_state = active[version]['state']
        pending = pipeline_state.get('pending_action', 'none')

        print(f'  [check_completions] Handoff detected: {version}/{pending} by {agent}'
              f' → {handoff_target or "next stage"}')

        if dry_run:
            processed.append({
                'version': version, 'stage': pending, 'agent': agent,
                'action': 'DRY_RUN: would advance and dispatch',
                'handoff_target': handoff_target,
            })
            if ts > newest_ts:
                newest_ts = ts
            continue

        # Advance state via pipeline_update.py
        try:
            update_result = subprocess.run(
                ['python3', str(SCRIPTS / 'pipeline_update.py'), version, 'complete', pending,
                 '--agent', agent, '--notes', f'Handoff detected by check_completions (telemetry)'],
                capture_output=True, text=True, timeout=30,
                cwd=str(WORKSPACE),
            )
            if update_result.returncode != 0:
                print(f'  [check_completions] pipeline_update.py failed: {update_result.stderr[:200]}')
        except Exception as e:
            print(f'  [check_completions] State advance failed: {e}')

        # Determine next stage and agent
        try:
            from pipeline_update import STAGE_TRANSITIONS
            transition = STAGE_TRANSITIONS.get(pending)
            if transition:
                next_stage, next_agent, _ = transition
            else:
                next_stage, next_agent = None, handoff_target
        except ImportError:
            next_stage = handoff_target
            next_agent = _agent_from_action(next_stage) if next_stage else None

        if next_stage and next_agent and next_stage not in HUMAN_ACTIONS:
            dispatch_result = fire_and_forget_dispatch(version, next_stage, next_agent)
            fl = generate_f_label('handoff', {
                'src': agent, 'dst': next_agent, 'coord': _get_pipeline_coord(version)
            })
            print(f'  {fl}  (pid={dispatch_result.get("pid")})')
            processed.append({
                'version': version, 'stage': pending, 'agent': agent,
                'next_stage': next_stage, 'next_agent': next_agent,
                'action': 'dispatched', 'pid': dispatch_result.get('pid'),
            })
        else:
            action = 'at_human_gate' if next_stage in HUMAN_ACTIONS else 'no_transition'
            processed.append({
                'version': version, 'stage': pending, 'agent': agent,
                'next_stage': next_stage, 'action': action,
            })

        if ts > newest_ts:
            newest_ts = ts

    # Update checkpoint
    if newest_ts and not dry_run:
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            checkpoint_file.write_text(newest_ts)
        except Exception:
            pass

    return processed


# ─── Gate Operations ────────────────────────────────────────────────────────────

def check_gates(version: str = None, dry_run: bool = False) -> list[dict]:
    """Check pipeline gates.

    If version given, check that pipeline only.
    Returns list of {pipeline, gate, status, blocked_by, action}.
    """
    results = []

    if version:
        version = resolve_pipeline(version) or version
        pipelines = [p for p in get_active_pipelines() if p['version'] == version]
    else:
        pipelines = get_active_pipelines()

    for p in pipelines:
        ver = p['version']
        state = p['state']
        fm = p['frontmatter']
        pending = p['pending_action']
        status = fm.get('status', '')

        # Pipeline-created gate: needs kickoff
        if pending == 'pipeline_created':
            results.append({
                'pipeline': ver,
                'gate': 'kickoff',
                'status': 'eligible',
                'blocked_by': None,
                'action': f'Dispatch architect for initial design',
            })
            continue

        # Phase 1 complete gate: experiment or revision
        if pending == 'phase1_complete':
            rev_file = BUILDS_DIR / f'{ver}_revision_request.md'
            if rev_file.exists():
                results.append({
                    'pipeline': ver,
                    'gate': 'phase1_revision',
                    'status': 'open',
                    'blocked_by': None,
                    'action': 'Process revision request',
                })
            else:
                results.append({
                    'pipeline': ver,
                    'gate': 'phase1_complete',
                    'status': 'waiting',
                    'blocked_by': 'human_review',
                    'action': 'Awaiting experiment run or human direction',
                })
            continue

        # Local analysis complete gate
        if pending == 'local_analysis_complete' or status == 'local_analysis_complete':
            direction_file = BUILDS_DIR / f'{ver}_phase2_shael_direction.md'
            if direction_file.exists():
                results.append({
                    'pipeline': ver,
                    'gate': 'phase2_direction',
                    'status': 'open',
                    'blocked_by': None,
                    'action': 'Phase 2 direction file found -- kick Phase 2',
                })
            else:
                results.append({
                    'pipeline': ver,
                    'gate': 'phase2_direction',
                    'status': 'waiting',
                    'blocked_by': 'human_direction',
                    'action': 'Awaiting Phase 2 direction file',
                })
            continue

        # Experiment complete gate -> analysis
        if pending == 'local_experiment_complete' or status == 'experiment_complete':
            results.append({
                'pipeline': ver,
                'gate': 'analysis',
                'status': 'open',
                'blocked_by': None,
                'action': 'Launch local analysis',
            })
            continue

        # Active agent work -- not a gate, but report it
        if pending in AGENT_ACTIONS:
            elapsed = minutes_since(p['last_updated'])
            if elapsed is not None and elapsed > STALL_THRESHOLD_MINUTES:
                results.append({
                    'pipeline': ver,
                    'gate': 'stalled',
                    'status': 'stalled',
                    'blocked_by': f'{_agent_from_action(pending)} unresponsive ({elapsed:.0f}min)',
                    'action': f'Recovery needed for {pending}',
                })
            # else: active work, no gate issue

    return results


# ─── Handoff Operations ────────────────────────────────────────────────────────

def check_handoffs() -> list[dict]:
    """Check for pending (unverified) handoffs.

    Returns list of pending handoff records with path and metadata.
    """
    if not _HAS_ORCHESTRATE:
        # Manual check
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

    return get_pending_handoffs()


# ─── Lock Operations ───────────────────────────────────────────────────────────

def list_locks() -> list[dict]:
    """Return all active pipeline locks with PID, age, agent info."""
    locks = []

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

                # Check if PID is alive
                pid_alive = True
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    pid_alive = False
                except PermissionError:
                    pid_alive = True

                age = minutes_since(created_at)

                locks.append({
                    'agent': agent,
                    'file': str(lock_file),
                    'pid': pid,
                    'pid_alive': pid_alive,
                    'created_at': created_at,
                    'age_minutes': age,
                    'stale': (not pid_alive) or (age is not None and age > LOCK_STALE_MINUTES),
                })
            except (json.JSONDecodeError, OSError) as e:
                locks.append({
                    'agent': agent,
                    'file': str(lock_file),
                    'pid': None,
                    'pid_alive': False,
                    'error': str(e),
                    'stale': True,
                })

    return locks


def release_lock(version: str) -> bool:
    """Force-release a pipeline lock.

    Since locks are agent-level (not pipeline-level), this releases
    all stale locks for the agent associated with the pipeline's current stage.
    """
    version = resolve_pipeline(version) or version
    state = load_state_json(version)
    pending = state.get('pending_action', 'none')
    agent = _agent_from_action(pending)

    if agent in ('unknown', 'none', 'system'):
        print(f'  Cannot determine agent for {version} (pending: {pending})')
        return False

    sessions_dir = AGENT_SESSION_DIRS.get(agent)
    if not sessions_dir or not sessions_dir.exists():
        print(f'  No session dir for {agent}')
        return False

    released = False
    for lock_file in sessions_dir.glob('*.lock'):
        try:
            lock_data = json.loads(lock_file.read_text())
            pid = lock_data.get('pid')

            # Kill the process if alive
            if pid:
                try:
                    os.kill(pid, 15)
                    time.sleep(1)
                    try:
                        os.kill(pid, 9)
                    except ProcessLookupError:
                        pass
                except ProcessLookupError:
                    pass

            lock_file.unlink()
            print(f'  F1 D {version}.lock.{agent} RELEASED (PID {pid})')
            released = True
        except Exception as e:
            print(f'  WARN: Failed to release {lock_file}: {e}')

    return released


# ─── Stall Detection ───────────────────────────────────────────────────────────

def check_stalls(threshold_minutes: int = STALL_THRESHOLD_MINUTES) -> list[dict]:
    """Find stalled pipelines.

    Returns list of {pipeline, pending_action, agent, stalled_since, last_activity, age_minutes}.
    """
    stalled = []
    pipelines = get_active_pipelines()

    for p in pipelines:
        version = p['version']
        pending = p['pending_action']
        last = p['last_updated']

        if pending in HUMAN_ACTIONS or pending == 'none' or not pending:
            continue

        if pending not in AGENT_ACTIONS:
            continue

        elapsed = minutes_since(last)
        if elapsed is None:
            continue

        if elapsed >= threshold_minutes:
            stalled.append({
                'pipeline': version,
                'pending_action': pending,
                'agent': _agent_from_action(pending),
                'stalled_since': last,
                'last_activity': last,
                'age_minutes': elapsed,
            })

    return stalled


def _check_unclaimed_dispatches(dry_run: bool = False,
                                 threshold_minutes: int = 5) -> list[dict]:
    """Find pipelines where a dispatch was sent but never claimed by an agent.

    Returns list of dicts with pipeline, agent, elapsed keys.
    """
    AGENT_STAGES = {
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
    }

    unclaimed = []
    pipelines = get_active_pipelines()

    for p in pipelines:
        version = p.get('version', '')
        state_file = BUILDS_DIR / f'{version}_state.json'
        if not state_file.exists():
            continue

        try:
            state = json.loads(state_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        pending = state.get('pending_action', '')
        dispatch_claimed = state.get('dispatch_claimed', True)
        last_dispatched = state.get('last_dispatched', '')
        current_agent = state.get('current_agent', pending)

        if dispatch_claimed or not last_dispatched:
            continue

        # pending_action can be either a stage name or an agent role
        AGENT_ROLES = {'architect', 'critic', 'builder'}
        if pending not in AGENT_STAGES and pending not in AGENT_ROLES:
            continue

        try:
            dispatched_dt = datetime.fromisoformat(last_dispatched)
            elapsed = (datetime.now(timezone.utc) - dispatched_dt).total_seconds() / 60
        except (ValueError, TypeError):
            continue

        if elapsed < threshold_minutes:
            continue

        # Resolve agent name from stage
        agent = 'unknown'
        for role in ('architect', 'critic', 'builder'):
            if role in current_agent:
                agent = role
                break

        unclaimed.append({
            'pipeline': version,
            'agent': agent,
            'stage': current_agent,
            'elapsed': elapsed,
        })

    return unclaimed


# ─── Full Sweep ─────────────────────────────────────────────────────────────────

def sweep(dry_run: bool = False) -> list[str]:
    """Run all checks: stale locks, gates, stalls, experiments, revisions.

    Returns list of action descriptions taken.
    """
    actions = []
    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    print(f'{"=" * 60}')
    print(f'  ORCHESTRATION SWEEP -- {now_str}')
    print(f'{"=" * 60}')

    if dry_run:
        print('  [DRY RUN -- no actions will be taken]\n')

    # 0a. Temporal sync: reconcile filesystem → SQLite temporal DB (if available)
    temporal = _get_temporal()
    if temporal:
        print(f'\n--- Temporal Sync (SQLite+WAL) ---\n')
        try:
            from temporal_sync import run_sync, export_agent_contexts
            summary = run_sync(dry_run=dry_run)
            created = summary.get('created', 0)
            updated = summary.get('updated', 0)
            unchanged = summary.get('unchanged', 0)
            errors = summary.get('errors', 0)
            print(f'  Pipeline state: {created} created, {updated} updated, '
                  f'{unchanged} unchanged')
            if errors:
                print(f'  ⚠ {errors} sync errors')
                actions.append(f'temporal-sync-errors: {errors}')
            # Export agent contexts for backup (FLAG-3)
            if not dry_run:
                exported = export_agent_contexts(temporal)
                if exported:
                    print(f'  Exported {len(exported)} agent context backup(s)')
        except ImportError:
            print(f'  temporal_sync.py not found — skipping')
        except Exception as e:
            print(f'  Temporal sync error (non-fatal): {e}')

    # 0. Check telemetry for completed agent turns (event loop)
    print(f'\n--- Completion Check (agent_end telemetry) ---\n')
    completions = check_completions(dry_run=dry_run)
    if completions:
        for c in completions:
            act = c.get('action', '?')
            print(f'  {c["version"]}/{c["stage"]}: {act}')
            actions.append(f'F1 D {c["version"]}.{c["stage"]} {act}')
    else:
        print('  No new completions in telemetry.')

    # 1. Check and clear stale locks
    print(f'\n--- Lock Check (>{LOCK_STALE_MINUTES}min threshold) ---\n')
    locks = list_locks()
    stale_locks = [l for l in locks if l.get('stale')]
    healthy_locks = [l for l in locks if not l.get('stale')]

    for l in healthy_locks:
        age_str = f'{l["age_minutes"]:.0f}m' if l.get('age_minutes') is not None else '?'
        print(f'  OK {l["agent"]}: PID {l["pid"]} alive, age {age_str}')

    for l in stale_locks:
        pid = l.get('pid', '?')
        reason = 'dead PID' if not l.get('pid_alive') else 'stale'
        print(f'  STALE {l["agent"]}: PID {pid} ({reason})')
        if not dry_run:
            try:
                lock_path = Path(l['file'])
                if l.get('pid') and l.get('pid_alive'):
                    try:
                        os.kill(l['pid'], 15)
                        time.sleep(1)
                        try:
                            os.kill(l['pid'], 9)
                        except ProcessLookupError:
                            pass
                    except ProcessLookupError:
                        pass
                lock_path.unlink(missing_ok=True)
                actions.append(f'F1 D lock.{l["agent"]} CLEARED (PID {pid})')
                print(f'    -> Lock cleared')
            except Exception as e:
                print(f'    -> Failed: {e}')
        else:
            actions.append(f'[DRY] Would clear lock for {l["agent"]}')

    if not locks:
        print('  No locks found.')

    # 2. Check running experiments
    print(f'\n--- Experiment Monitor ---\n')
    exp_pids = list(BUILDS_DIR.glob('*_experiment.pid')) if BUILDS_DIR.exists() else []
    for pid_file in exp_pids:
        try:
            pid_info = json.loads(pid_file.read_text())
            pid = pid_info.get('pid')
            ver = pid_info.get('version', pid_file.stem.replace('_experiment', ''))
            try:
                os.kill(pid, 0)
                started = pid_info.get('started', '')
                elapsed = minutes_since(started) if started else None
                age_str = f'{elapsed:.0f}min' if elapsed else '?'
                print(f'  RUNNING {ver}: PID {pid}, {age_str} elapsed')
            except (OSError, ProcessLookupError):
                print(f'  DEAD {ver}: PID {pid} -- process ended')
                if not dry_run:
                    pid_file.unlink(missing_ok=True)
                    actions.append(f'F1 D {ver}.experiment.pid CLEANED')
        except Exception:
            pass

    if not exp_pids:
        print('  No experiments running.')

    # 3. Check gates
    print(f'\n--- Gate Check ---\n')
    gates = check_gates(dry_run=dry_run)
    MAX_CONCURRENT = 2  # Max pipelines with active agent work
    kicked = 0
    for g in gates:
        status_label = g['status'].upper()
        blocked = f' (blocked by: {g["blocked_by"]})' if g.get('blocked_by') else ''
        print(f'  {g["pipeline"]}: {g["gate"]} = {status_label}{blocked}')
        if g.get('action'):
            print(f'    -> {g["action"]}')

        # Auto-kick eligible pipelines (up to MAX_CONCURRENT)
        if g['status'] in ('eligible', 'open') and kicked < MAX_CONCURRENT and not dry_run:
            if g['gate'] == 'kickoff' and _HAS_ORCHESTRATE:
                print(f'    -> Auto-kicking {g["pipeline"]}...')
                try:
                    result = orchestrate_complete(g['pipeline'], 'pipeline_created',
                                                  'belam-main', 'Auto-kicked by sweep')
                    if result:
                        actions.append(f'F1 D {g["pipeline"]}.kickoff -> architect_design')
                        kicked += 1
                except Exception as e:
                    print(f'    -> Kick failed: {e}')
            elif g['gate'] == 'analysis' and _HAS_ORCHESTRATE:
                print(f'    -> Auto-launching analysis for {g["pipeline"]}...')
                try:
                    from pipeline_orchestrate import orchestrate_local_analysis
                    result = orchestrate_local_analysis(g['pipeline'])
                    if result:
                        actions.append(f'F1 D {g["pipeline"]}.analysis LAUNCHED')
                        kicked += 1
                except Exception as e:
                    print(f'    -> Analysis launch failed: {e}')
            elif dry_run:
                actions.append(f'[DRY] Would process gate {g["gate"]} for {g["pipeline"]}')

    if not gates:
        print('  All gates clear or no gate-blocked pipelines.')

    # 4. Check pending revisions
    print(f'\n--- Revision Check ---\n')
    rev_files = list(BUILDS_DIR.glob('*_revision_request.md')) if BUILDS_DIR.exists() else []
    if rev_files:
        for rf in rev_files:
            fm = load_pipeline_frontmatter(rf)
            ver = fm.get('version', rf.stem.replace('_revision_request', ''))
            print(f'  PENDING: {ver} revision request at {rf.name}')
            if kicked < MAX_CONCURRENT and not dry_run and _HAS_ORCHESTRATE:
                try:
                    from pipeline_orchestrate import orchestrate_revise
                    context = rf.read_text()
                    result = orchestrate_revise(ver, context)
                    if result:
                        actions.append(f'F1 D {ver}.revision KICKED')
                        kicked += 1
                        rf.unlink()
                except Exception as e:
                    print(f'    -> Revision kick failed: {e}')
    else:
        print('  No pending revisions.')

    # 5. Check stalls
    print(f'\n--- Stall Check (>{STALL_THRESHOLD_MINUTES}min) ---\n')
    stalls = check_stalls()
    if stalls:
        for s in stalls:
            print(f'  STALLED: {s["pipeline"]}/{s["pending_action"]} by {s["agent"]} ({s["age_minutes"]:.0f}min)')
            if kicked < MAX_CONCURRENT and not dry_run and _HAS_ORCHESTRATE:
                print(f'    -> Auto-recovering...')
                try:
                    ok = pipeline_resume(s['pipeline'])
                    if ok:
                        actions.append(f'F1 D {s["pipeline"]}.stall_recovery {s["agent"]} RESUMED')
                        kicked += 1
                except Exception as e:
                    print(f'    -> Recovery failed: {e}')
            elif dry_run:
                actions.append(f'[DRY] Would resume {s["pipeline"]}/{s["pending_action"]}')
    else:
        print('  No stalled pipelines.')

    # 5b. Check unclaimed dispatches (agent never picked up the handoff)
    print(f'\n--- Unclaimed Dispatch Recovery ---\n')
    if kicked >= MAX_CONCURRENT:
        print(f'  Skipping — {kicked} pipeline(s) already kicked this sweep (limit={MAX_CONCURRENT}).')
    else:
        unclaimed = _check_unclaimed_dispatches(dry_run=dry_run)
        if unclaimed:
            for u in unclaimed:
                print(f'  ⚠️  {u["pipeline"]}: dispatch to {u["agent"]} unclaimed after {u["elapsed"]:.0f}min — re-kicking')
                if not dry_run and _HAS_ORCHESTRATE:
                    try:
                        ok = pipeline_resume(u['pipeline'])
                        if ok:
                            actions.append(f'F1 D {u["pipeline"]}.unclaimed_recovery {u["agent"]} RESUMED')
                            kicked += 1
                    except Exception as e:
                        print(f'    -> Recovery failed: {e}')
                elif dry_run:
                    actions.append(f'[DRY] Would re-kick {u["pipeline"]}/{u["agent"]}')
        else:
            print('  No unclaimed dispatches.')

    # 6. Check pending handoffs
    print(f'\n--- Handoff Check ---\n')
    handoffs = check_handoffs()
    if handoffs:
        for h in handoffs:
            ver = h.get('version', '?')
            agent = h.get('next_agent', '?')
            stage = h.get('next_stage', '?')
            ts = h.get('timestamp', '?')[:19]
            print(f'  PENDING: {ver} -> {agent} for {stage} (since {ts})')
    else:
        print('  No pending handoffs.')

    # Summary
    print(f'\n{"=" * 60}')
    pipelines = get_active_pipelines()
    print(f'  Active pipelines: {len(pipelines)}')
    for i, p in enumerate(pipelines, 1):
        pending = p['pending_action']
        agent = _agent_from_action(pending)
        age = minutes_since(p['last_updated'])
        age_str = _format_age(age)
        pri = p['frontmatter'].get('priority', '-')
        print(f'    p{i} {p["version"]:<35} {pending:<30} {agent:<10} {age_str:<12} [{pri}]')
    if actions:
        print(f'\n  Actions taken: {len(actions)}')
        for a in actions:
            print(f'    {a}')
    else:
        print(f'\n  No actions taken.')
    print(f'{"=" * 60}\n')

    return actions


# ─── Complete / Block Handlers ──────────────────────────────────────────────────

def handle_complete(version: str, stage: str, agent: str,
                     notes: str = '', learnings: str = '') -> dict:
    """Handle stage completion. Returns dispatch payload for next stage.

    This is what agents call when they finish their work:
      python3 scripts/orchestration_engine.py complete <version> <stage> --agent <agent> --notes "..."

    The engine:
    1. Records completion
    2. Determines next stage from transition map
    3. Builds dispatch payload for the next agent
    4. Returns payload (interactive) or executes (headless)
    """
    version = resolve_pipeline(version) or version
    coord = _get_pipeline_coord(version)

    # Generate F-label for state transition
    fl = generate_f_label('stage_change', {
        'old_stage': stage, 'new_stage': _next_stage_for(stage),
        'coord': coord,
    })
    print(f'  {fl}')

    # Use legacy orchestrate_complete if available (passes learnings for memory)
    if _HAS_ORCHESTRATE:
        try:
            result = orchestrate_complete(version, stage, agent, notes, learnings)
            # V2-temporal post-hook: record transition in SpacetimeDB
            next_stg = _next_stage_for(stage)
            next_ag = _agent_from_action(next_stg) if next_stg else ''
            _post_state_change(version, stage, next_stg or 'terminal',
                               agent, 'complete', notes, next_ag)
            return {'status': 'completed', 'dispatched': bool(result), 'f_label': fl}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'f_label': fl}

    # Fallback: just update state and build next payload
    next_stg = _next_stage_for(stage)
    if not next_stg:
        return {'status': 'terminal', 'message': f'No transition from {stage}', 'f_label': fl}

    next_agent = _agent_from_action(next_stg)
    payload = build_dispatch_payload(version, next_stg, next_agent, notes=notes)

    # V2-temporal post-hook: record transition in SpacetimeDB
    _post_state_change(version, stage, next_stg, agent, 'complete', notes, next_agent)

    return {
        'status': 'completed',
        'next_dispatch': payload.to_dict(),
        'f_label': fl,
    }


def handle_block(version: str, stage: str, agent: str,
                  notes: str = '', learnings: str = '') -> dict:
    """Handle stage block. Routes back to the fixing agent.

    Blocks reverse direction — critic sends work back to architect.
    """
    version = resolve_pipeline(version) or version
    coord = _get_pipeline_coord(version)

    # Determine block target
    block_target = _block_target_for(stage)
    fl = generate_f_label('stage_change', {
        'old_stage': stage, 'new_stage': block_target or 'blocked',
        'coord': coord,
    })
    print(f'  {fl}')

    if _HAS_ORCHESTRATE:
        try:
            result = orchestrate_block(version, stage, agent, notes, learnings=learnings)
            # V2-temporal post-hook
            _post_state_change(version, stage, block_target or 'blocked',
                               agent, 'block', notes,
                               _agent_from_action(block_target) if block_target else '')
            return {'status': 'blocked', 'dispatched': bool(result), 'f_label': fl}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'f_label': fl}

    if not block_target:
        return {'status': 'blocked', 'message': f'No block target for {stage}', 'f_label': fl}

    target_agent = _agent_from_action(block_target)
    payload = build_dispatch_payload(version, block_target, target_agent, notes=notes)

    # V2-temporal post-hook
    _post_state_change(version, stage, block_target, agent, 'block', notes, target_agent)

    return {
        'status': 'blocked',
        'next_dispatch': payload.to_dict(),
        'f_label': fl,
    }


def _next_stage_for(stage: str) -> str | None:
    """Get the next stage in the standard transition sequence."""
    # Try pipeline_update.py STAGE_TRANSITIONS first
    try:
        from pipeline_update import STAGE_TRANSITIONS
        transition = STAGE_TRANSITIONS.get(stage)
        if transition:
            return transition[0]  # (next_stage, expected_agent, desc)
    except ImportError:
        pass

    # Fallback to STAGE_SEQUENCE
    try:
        idx = STAGE_SEQUENCE.index(stage)
        if idx + 1 < len(STAGE_SEQUENCE):
            return STAGE_SEQUENCE[idx + 1]
    except ValueError:
        pass

    return None


def _block_target_for(stage: str) -> str | None:
    """Get the block-reversal target for a stage."""
    try:
        from pipeline_update import BLOCK_TRANSITIONS
        transition = BLOCK_TRANSITIONS.get(stage)
        if transition:
            return transition[0]
    except ImportError:
        pass

    # Common block patterns
    block_map = {
        'critic_design_review': 'architect_design_revision',
        'critic_code_review': 'builder_apply_blocks',
        'phase2_critic_design_review': 'phase2_architect_revision',
        'phase2_critic_code_review': 'phase2_builder_apply_blocks',
    }
    return block_map.get(stage)


# ─── CLI Rendering Helpers ──────────────────────────────────────────────────────

def _render_status(version: str):
    """Render pipeline status to stdout."""
    s = pipeline_status(version)

    if s.get('error') == 'not_found':
        print(f'Pipeline not found: {version}')
        return

    print(f'\n--- Pipeline Status: {s["version"]} ---\n')
    print(f'  Status:         {s["status"]}')
    print(f'  Pending action: {s["pending_action"]}')
    print(f'  Current agent:  {s["agent"]}')
    print(f'  Last updated:   {s["last_updated"]} ({s["last_updated_ago"]})')
    print(f'  Priority:       {s["priority"]}')

    if s.get('next_action'):
        print(f'  Next action:    {s["next_action"]}')

    if s.get('gates'):
        print(f'\n  Gates:')
        for gate, status in s['gates'].items():
            print(f'    {gate}: {status}')

    if s.get('locks'):
        print(f'\n  Locks ({len(s["locks"])} total):')
        for l in s['locks']:
            alive = 'alive' if l.get('pid_alive') else 'dead'
            stale = ' STALE' if l.get('stale') else ''
            age = f'{l["age_minutes"]:.0f}m' if l.get('age_minutes') is not None else '?'
            print(f'    {l["agent"]}: PID {l.get("pid", "?")} ({alive}, {age}){stale}')

    # Stage history
    stages = s.get('stages', {})
    if stages:
        print(f'\n  Stage History ({len(stages)} stages):')
        for stage_name, info in stages.items():
            status = info.get('status', '?')
            agent = info.get('agent', '?')
            completed = info.get('completed_at', '?')
            notes = (info.get('notes', '') or '')[:80]
            print(f'    {stage_name:<40} {status:<10} {agent:<10} {completed}')
            if notes:
                print(f'      {notes}')

    print()


def _render_gates(version: str = None):
    """Render gate check results to stdout."""
    gates = check_gates(version=version)

    if not gates:
        print('\nNo gate-blocked pipelines found.\n')
        return

    print(f'\n--- Gate Check ---\n')
    for g in gates:
        blocked = f' [{g["blocked_by"]}]' if g.get('blocked_by') else ''
        print(f'  {g["pipeline"]:<35} {g["gate"]:<20} {g["status"].upper()}{blocked}')
        if g.get('action'):
            print(f'    -> {g["action"]}')
    print()


def _render_locks():
    """Render lock status to stdout."""
    locks = list_locks()

    if not locks:
        print('\nNo active locks.\n')
        return

    print(f'\n--- Active Locks ---\n')
    for l in locks:
        alive = 'alive' if l.get('pid_alive') else 'DEAD'
        stale = ' STALE' if l.get('stale') else ''
        age = f'{l["age_minutes"]:.0f}m' if l.get('age_minutes') is not None else '?'
        print(f'  {l["agent"]:<12} PID {l.get("pid", "?"):<8} {alive} age={age}{stale}')
        if l.get('error'):
            print(f'    error: {l["error"]}')
    print()


def _render_stalls():
    """Render stall check results to stdout."""
    stalls = check_stalls()

    if not stalls:
        print('\nNo stalled pipelines.\n')
        return

    print(f'\n--- Stalled Pipelines ---\n')
    for s in stalls:
        print(f'  {s["pipeline"]:<35} {s["pending_action"]:<30} {s["agent"]:<10} {s["age_minutes"]:.0f}min')
    print()


def _render_handoffs():
    """Render pending handoffs to stdout."""
    handoffs = check_handoffs()

    if not handoffs:
        print('\nNo pending handoffs.\n')
        return

    print(f'\n--- Pending Handoffs ---\n')
    for h in handoffs:
        ver = h.get('version', '?')
        agent = h.get('next_agent', '?')
        stage = h.get('next_stage', '?')
        ts = h.get('timestamp', '?')[:19]
        wake_status = h.get('wake_result', {}).get('status', '?')
        print(f'  {ver:<35} -> {agent:<10} {stage:<30} {ts} [{wake_status}]')
    print()


def _render_next(version: str):
    """Render next action for a pipeline."""
    version = resolve_pipeline(version) or version
    action = pipeline_next_action(version)
    if action:
        print(f'\n{version}: {action}\n')
    else:
        print(f'\n{version}: No pending action.\n')


# ─── CLI Main ──────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    if dry_run:
        args.remove('--dry-run')
    json_mode = '--json' in args
    if json_mode:
        args.remove('--json')

    if not args:
        # Full sweep
        sweep(dry_run=dry_run)
        return

    cmd = args[0]

    if cmd == 'status':
        if len(args) < 2:
            print('Usage: orchestration_engine.py status <version>')
            sys.exit(1)
        if json_mode:
            print(json.dumps(pipeline_status(args[1]), indent=2, default=str))
        else:
            _render_status(args[1])

    elif cmd == 'gates':
        version = args[1] if len(args) > 1 else None
        if json_mode:
            print(json.dumps(check_gates(version=version), indent=2, default=str))
        else:
            _render_gates(version)

    elif cmd == 'handoffs':
        if json_mode:
            print(json.dumps(check_handoffs(), indent=2, default=str))
        else:
            _render_handoffs()

    elif cmd == 'locks':
        if json_mode:
            all_locks = list_locks() + list_central_locks()
            print(json.dumps(all_locks, indent=2, default=str))
        else:
            _render_locks()

    elif cmd == 'stalls':
        if json_mode:
            print(json.dumps(check_stalls(), indent=2, default=str))
        else:
            _render_stalls()

    elif cmd == 'next':
        if len(args) < 2:
            print('Usage: orchestration_engine.py next <version>')
            sys.exit(1)
        _render_next(args[1])

    elif cmd == 'dispatch':
        if len(args) < 3:
            print('Usage: orchestration_engine.py dispatch <version> <agent> [stage]')
            sys.exit(1)
        version = args[1]
        agent = args[2]
        stage = args[3] if len(args) > 3 else None
        result = pipeline_dispatch(version, agent, stage, structured=json_mode)
        if json_mode and isinstance(result, dict):
            print(json.dumps(result, indent=2, default=str))

    elif cmd == 'complete':
        if len(args) < 3:
            print('Usage: orchestration_engine.py complete <version> <stage> --agent <agent> --notes "..."')
            sys.exit(1)
        version = args[1]
        stage = args[2]
        agent = _extract_flag(args, '--agent') or _agent_from_action(stage)
        notes = _extract_flag(args, '--notes') or ''
        learnings = _extract_flag(args, '--learnings') or ''
        result = handle_complete(version, stage, agent, notes, learnings)
        if json_mode:
            print(json.dumps(result, indent=2, default=str))
        else:
            status = result.get('status', 'unknown')
            fl = result.get('f_label', '')
            print(f'\n  Complete: {version}/{stage} -> {status}')
            if fl:
                print(f'  {fl}')
            if result.get('next_dispatch'):
                next_label = result['next_dispatch'].get('spawn', {}).get('label', '')
                print(f'  Next: {next_label}')
            print()

    elif cmd == 'block':
        if len(args) < 3:
            print('Usage: orchestration_engine.py block <version> <stage> --agent <agent> --notes "..."')
            sys.exit(1)
        version = args[1]
        stage = args[2]
        agent = _extract_flag(args, '--agent') or _agent_from_action(stage)
        notes = _extract_flag(args, '--notes') or ''
        learnings = _extract_flag(args, '--learnings') or ''
        result = handle_block(version, stage, agent, notes, learnings)
        if json_mode:
            print(json.dumps(result, indent=2, default=str))
        else:
            status = result.get('status', 'unknown')
            fl = result.get('f_label', '')
            print(f'\n  Block: {version}/{stage} -> {status}')
            if fl:
                print(f'  {fl}')
            print()

    elif cmd == 'completions':
        # Check telemetry for agent turn completions, advance pipelines
        results = check_completions(dry_run=dry_run)
        if json_mode:
            print(json.dumps(results, indent=2, default=str))
        else:
            if results:
                for r in results:
                    print(f'  {r["version"]}/{r.get("stage","?")} -> {r.get("action","?")}')
            else:
                print('  No new completions found.')

    elif cmd == 'resume':
        if len(args) < 2:
            print('Usage: orchestration_engine.py resume <version>')
            sys.exit(1)
        pipeline_resume(args[1])

    elif cmd == 'release-lock':
        if len(args) < 2:
            print('Usage: orchestration_engine.py release-lock <version>')
            sys.exit(1)
        release_lock(args[1])
        # Also try central lock
        atomic_lock_release(args[1])

    elif cmd == 'list':
        pipelines = get_active_pipelines()
        if not pipelines:
            print('\nNo active pipelines.\n')
            return
        if json_mode:
            print(json.dumps([{
                'index': i, 'coord': f'p{i}',
                'version': p['version'], 'pending_action': p['pending_action'],
                'agent': _agent_from_action(p['pending_action']),
                'priority': p['frontmatter'].get('priority', '-'),
            } for i, p in enumerate(pipelines, 1)], indent=2))
        else:
            print(f'\n--- Active Pipelines ---\n')
            for i, p in enumerate(pipelines, 1):
                pending = p['pending_action']
                agent = _agent_from_action(pending)
                age = minutes_since(p['last_updated'])
                age_str = _format_age(age)
                pri = p['frontmatter'].get('priority', '-')
                print(f'  p{i} {p["version"]:<35} {pending:<30} {agent:<10} {age_str:<12} [{pri}]')
            print()

    elif cmd == 'resolve':
        if len(args) < 2:
            print('Usage: orchestration_engine.py resolve <ref>')
            sys.exit(1)
        result = resolve_pipeline(args[1])
        print(result or f'Could not resolve: {args[1]}')

    elif cmd == 'sweep':
        sweep(dry_run=dry_run)

    elif cmd == 'verify-hooks':
        results = verify_hooks()
        if json_mode:
            print(json.dumps(results, indent=2, default=str))
        else:
            _render_hook_verification(results)

    elif cmd == 'dispatch-payload':
        # Explicit structured dispatch payload (always JSON)
        if len(args) < 3:
            print('Usage: orchestration_engine.py dispatch-payload <version> <agent> [stage]')
            sys.exit(1)
        version = args[1]
        agent = args[2]
        stage = args[3] if len(args) > 3 else None
        version = resolve_pipeline(version) or version
        state = load_state_json(version)
        if stage is None:
            stage = state.get('pending_action', 'none')
        payload = build_dispatch_payload(version, stage, agent)
        print(json.dumps(payload.to_dict(), indent=2, default=str))

    elif cmd == 'launch':
        # Create a new pipeline (delegating to launch_pipeline.py)
        if len(args) < 2:
            print('Usage: orchestration_engine.py launch <version> --desc "description" [--priority high] [--tags a,b] [--start]')
            sys.exit(1)
        version = args[1]
        desc = _extract_flag(args, '--desc') or _extract_flag(args, '-d') or ''
        priority = _extract_flag(args, '--priority') or 'high'
        tags_str = _extract_flag(args, '--tags')
        tags = [t.strip() for t in tags_str.split(',')] if tags_str else None
        start = '--start' in args or '--kickoff' in args

        if not desc:
            print('ERROR: --desc required')
            sys.exit(1)

        if _HAS_LAUNCH:
            pf = _create_pipeline(version, desc, priority, tags)
            if start and _HAS_ORCHESTRATE:
                print(f'\n🚀 Kicking off via orchestrator...')
                orchestrate_complete(version, 'pipeline_created', 'belam-main',
                                     f'Pipeline created: {desc}')
        else:
            # Fallback: call launch_pipeline.py as subprocess
            import subprocess as _sp
            launch_args = [sys.executable, str(SCRIPTS / 'launch_pipeline.py'), version,
                          '--desc', desc, '--priority', priority]
            if tags_str:
                launch_args.extend(['--tags', tags_str])
            if start:
                launch_args.append('--kickoff')
            _sp.run(launch_args, cwd=str(WORKSPACE))

    elif cmd == 'archive':
        if len(args) < 2:
            print('Usage: orchestration_engine.py archive <version>')
            sys.exit(1)
        version = resolve_pipeline(args[1]) or args[1]
        if _HAS_LAUNCH:
            archive_pipeline(version)
        else:
            import subprocess as _sp
            _sp.run([sys.executable, str(SCRIPTS / 'launch_pipeline.py'), version, '--archive'],
                    cwd=str(WORKSPACE))

    elif cmd == 'archive-tasks':
        # Standalone: auto-archive tasks whose work has moved downstream
        if _HAS_LAUNCH:
            version = resolve_pipeline(args[1]) if len(args) > 1 else None
            archived = auto_archive_downstream_tasks(version)
            if archived:
                print(f"\n📋 Auto-archived {len(archived)} task(s):")
                for t in archived:
                    print(f"  • {t}")
            else:
                print("\n✅ No tasks eligible for auto-archive.")
        else:
            print("⚠ launch_pipeline not available")

    elif cmd == 'link-tasks':
        # Auto-set pipeline field on tasks matching a pipeline version
        if _HAS_LAUNCH:
            if len(args) < 2:
                # Link all: iterate active pipelines
                all_linked = []
                for pf in sorted(PIPELINES_DIR.glob('*.md')):
                    pc = pf.read_text()
                    from launch_pipeline import _extract_field as _ef
                    if _ef(pc, 'status') == 'archived':
                        continue
                    linked = link_tasks_to_pipeline(pf.stem)
                    all_linked.extend(linked)
                if all_linked:
                    print(f"\n📋 Linked {len(all_linked)} task(s):")
                    for slug, reason in all_linked:
                        print(f"  • {slug} ({reason})")
                else:
                    print("\n✅ All tasks already linked.")
            else:
                version = resolve_pipeline(args[1]) or args[1]
                linked = link_tasks_to_pipeline(version)
                if linked:
                    print(f"\n📋 Linked {len(linked)} task(s) to {version}:")
                    for slug, reason in linked:
                        print(f"  • {slug} ({reason})")
                else:
                    print(f"\n✅ No unlinked tasks for {version}.")
        else:
            print("⚠ launch_pipeline not available")

    # ─── V2-Temporal Commands (autoclave/timeline/timetravel/temporal-sync) ────

    elif cmd == 'autoclave':
        # Autoclave dashboard — shared view of all pipelines + agents
        temporal = _get_temporal()
        if not temporal:
            print('\n⚠ Temporal DB unavailable — autoclave requires temporal overlay.\n')
            print('  Setup: python3 scripts/temporal_schema.py && python3 scripts/temporal_sync.py')
            sys.exit(1)
        sub = args[1] if len(args) > 1 else None
        if sub == 'agents':
            dashboard = temporal.get_dashboard() or {}
            agents = dashboard.get('agents', [])
            print(f'\n--- Agent Presence ---\n')
            for a in agents:
                pipeline = a.get('current_pipeline', '-')
                print(f'  {a["agent"]:<12} {a["status"]:<20} pipeline={pipeline}')
            if not agents:
                print('  No agents registered.')
            print()
        elif sub and sub.startswith('@'):
            # Time-travel: autoclave @2h (all pipelines 2h ago)
            # For now, just show the dashboard at point-in-time
            print(f'\n  Time-travel queries require a pipeline version:')
            print(f'  orchestration_engine.py timetravel <version> --at <ISO-timestamp>\n')
        else:
            dashboard = temporal.get_dashboard()
            if dashboard:
                print(f'\n--- AUTOCLAVE Dashboard ({dashboard.get("generated_at", "")}) ---\n')
                print(f'  PIPELINES')
                for p in dashboard.get('pipelines', []):
                    locked = '🔒' if p.get('locked_by') else '  '
                    print(f'  {locked} {p.get("version","?"):<35} {p.get("current_stage","?"):<25} {p.get("current_agent","?")}')
                print(f'\n  AGENTS')
                for a in dashboard.get('agents', []):
                    print(f'  {a.get("agent","?"):<12} {a.get("status","?")}')
                handoffs = dashboard.get('recent_handoffs', [])
                if handoffs:
                    print(f'\n  RECENT HANDOFFS')
                    for h in handoffs[:5]:
                        print(f'  {h.get("source_agent","?")} → {h.get("target_agent","?")} ({h.get("version","?")}/{h.get("next_stage","?")})')
                print()
            else:
                print('  Dashboard unavailable.')

    elif cmd == 'timeline':
        if len(args) < 2:
            print('Usage: orchestration_engine.py timeline <version>')
            sys.exit(1)
        temporal = _get_temporal()
        if not temporal:
            print('\n⚠ Temporal DB unavailable.\n')
            sys.exit(1)
        version = resolve_pipeline(args[1]) or args[1]
        timeline = temporal.get_timeline(version)
        if timeline:
            print(f'\n--- Timeline: {version} ---\n')
            for entry in timeline:
                ts = entry.get('timestamp', '?')
                print(f'  {ts} | {entry.get("from_stage","?")} → {entry.get("to_stage","?")} | {entry.get("agent","?")} | {entry.get("action","?")}')
                if entry.get('notes'):
                    print(f'            {entry["notes"][:80]}')
            print()
        else:
            print(f'\n  No timeline data for {version}.\n')

    elif cmd == 'timetravel':
        if len(args) < 2:
            print('Usage: orchestration_engine.py timetravel <version> --at <ISO-timestamp>')
            sys.exit(1)
        temporal = _get_temporal()
        if not temporal:
            print('\n⚠ Temporal DB unavailable.\n')
            sys.exit(1)
        version = resolve_pipeline(args[1]) or args[1]
        at = _extract_flag(args, '--at') or ''
        if not at:
            print('  --at <ISO-timestamp> required')
            sys.exit(1)
        state = temporal.time_travel(version, at)
        if json_mode:
            print(json.dumps(state, indent=2, default=str))
        else:
            if state:
                print(f'\n  State at {at}: stage={state.get("to_stage","?")} agent={state.get("agent","?")} action={state.get("action","?")}\n')
            else:
                print(f'\n  No state found for {version} at {at}.\n')

    elif cmd == 'revert':
        # Phase 2 R1: Time-travel revert with F-label/R-label causal coupling
        if len(args) < 2:
            print('Usage: orchestration_engine.py revert <version> --at <ISO-timestamp> [--force]')
            sys.exit(1)
        version = args[1]
        at = _extract_flag(args, '--at') or ''
        if not at:
            print('  --at <ISO-timestamp> required')
            sys.exit(1)
        force = '--force' in args
        result = handle_revert(version, at, force=force)
        if json_mode:
            print(json.dumps(result, indent=2, default=str))
        else:
            status = result.get('status', 'unknown')
            if status == 'reverted':
                print(f'\n  ⮌ Reverted {version}: {result.get("reverted_from","?")} → {result.get("reverted_to","?")}')
                for fl in result.get('engine_f_labels', []):
                    print(f'  {fl}')
                hint = result.get('r_label_hint', {})
                if hint.get('affected_coords'):
                    print(f'  R-label hint: re-render {", ".join(hint["affected_coords"])}')
                print()
            elif status == 'noop':
                print(f'\n  {result.get("message", "No-op.")}\n')
            elif status == 'blocked':
                print(f'\n  ⚠ {result.get("error", "Blocked.")}\n')
            else:
                print(f'\n  ❌ {result.get("error", "Revert failed.")}\n')

    elif cmd == 'temporal-sync':
        # Delegate to temporal_sync.py for filesystem → temporal DB reconciliation
        try:
            from temporal_sync import run_sync
            dry_run = '--dry-run' in args or '-n' in args
            pipeline_flag = _extract_flag(args, '--pipeline') or _extract_flag(args, '-p')
            summary = run_sync(pipeline_filter=pipeline_flag, dry_run=dry_run,
                               json_output=json_mode)
            if json_mode:
                print(json.dumps(summary, indent=2))
            else:
                prefix = '[DRY RUN] ' if dry_run else ''
                print(f'{prefix}✅ Temporal sync: {summary.get("created", 0)} created, '
                      f'{summary.get("updated", 0)} updated, '
                      f'{summary.get("unchanged", 0)} unchanged')
        except ImportError:
            print('\n⚠ temporal_sync.py not found.\n')
            sys.exit(1)

    elif cmd == 'context':
        # Show persistent agent context for a pipeline
        if len(args) < 2:
            print('Usage: orchestration_engine.py context <version> [agent]')
            sys.exit(1)
        temporal = _get_temporal()
        if not temporal:
            print('\n⚠ Temporal DB unavailable.\n')
            sys.exit(1)
        version = resolve_pipeline(args[1]) or args[1]
        agent_filter = args[2] if len(args) > 2 else None
        agents_to_show = [agent_filter] if agent_filter else ['architect', 'critic', 'builder']
        for ag in agents_to_show:
            lineage = temporal.get_design_lineage(version, ag)
            if lineage:
                print(f'\n--- Persistent Context: {ag} on {version} ---')
                print(lineage)
            elif agent_filter:
                print(f'\n  No context for {ag} on {version}.')
        print()

    # ─── V3 Monitoring Commands (view, deps, watcher) ─────────────────────────

    elif cmd == 'view':
        # V3: .v namespace view resolution
        if len(args) < 2:
            # No args = list views
            try:
                from monitoring_views import list_views
                print(list_views())
            except ImportError:
                print('\n⚠ monitoring_views.py not found.\n')
            sys.exit(0)

        coord = args[1]
        persona = _extract_flag(args, '--persona')

        try:
            from monitoring_views import resolve_view
            result = resolve_view(coord, persona=persona)
            if json_mode:
                print(json.dumps({
                    'view_type': result.view_type,
                    'view_name': result.view_name,
                    'pipeline': result.pipeline,
                    'persona': result.persona,
                    'content': result.content,
                    'generated_at': result.generated_at,
                }, indent=2))
            else:
                print(result.content)
        except ImportError:
            print('\n⚠ monitoring_views.py not found.\n')
            sys.exit(1)

    elif cmd == 'deps':
        # V3: Dependency graph management
        sub = args[1] if len(args) > 1 else 'list'
        try:
            from dependency_graph import (render_dependency_graph,
                                          register_dependency, check_deps_satisfied,
                                          resolve_downstream_deps)
            if sub == 'list' or sub == 'graph':
                if json_mode:
                    from dependency_graph import get_all_deps
                    print(json.dumps(get_all_deps(), indent=2))
                else:
                    print(render_dependency_graph())
            elif sub == 'register':
                if len(args) < 4:
                    print('Usage: orchestration_engine.py deps register <source> <target> [type]')
                    sys.exit(1)
                dep_type = args[4] if len(args) > 4 else 'completion'
                ok = register_dependency(args[2], args[3], dep_type)
                print(f"{'✅' if ok else '❌'} {args[2]} → {args[3]} ({dep_type})")
            elif sub == 'check':
                if len(args) < 3:
                    print('Usage: orchestration_engine.py deps check <version>')
                    sys.exit(1)
                ver = resolve_pipeline(args[2]) or args[2]
                result = check_deps_satisfied(ver)
                if json_mode:
                    print(json.dumps(result, indent=2))
                else:
                    status = '✅ All deps met' if result['all_met'] else '⏳ Deps pending'
                    print(f"{status} for {ver}")
                    for d in result.get('deps', []):
                        icon = '✅' if d['status'] == 'satisfied' else '⏳'
                        print(f"  {icon} {d['source_version']} ({d['dep_type']})")
            elif sub == 'resolve':
                if len(args) < 3:
                    print('Usage: orchestration_engine.py deps resolve <version>')
                    sys.exit(1)
                ver = resolve_pipeline(args[2]) or args[2]
                results = resolve_downstream_deps(ver)
                if json_mode:
                    print(json.dumps(results, indent=2))
                else:
                    for r in results:
                        icon = '✅' if r['all_deps_met'] else '⏳'
                        print(f"  {icon} {r['target']}: all met={r['all_deps_met']}")
                    if not results:
                        print(f"  No downstream deps for {ver}")
            else:
                print(f'Unknown deps subcommand: {sub}')
                print('Subcommands: list, register, check, resolve')
                sys.exit(1)
        except ImportError:
            print('\n⚠ dependency_graph.py not found.\n')
            sys.exit(1)

    elif cmd == 'watcher':
        # V3: Start WAL watcher
        try:
            from wal_watcher import WALWatcher
            interval = float(_extract_flag(args, '--interval') or '2')
            no_canvas = '--no-canvas' in args
            once = '--once' in args
            watcher = WALWatcher(interval_seconds=interval, use_canvas=not no_canvas)
            if once:
                print(watcher.render_once())
            else:
                watcher.run()
        except ImportError:
            print('\n⚠ wal_watcher.py not found.\n')
            sys.exit(1)

    elif cmd == 'help' or cmd == '--help' or cmd == '-h':
        print(__doc__)

    else:
        # Maybe it's a version string? Try status
        resolved = resolve_pipeline(cmd)
        if resolved:
            _render_status(resolved)
        else:
            print(f'Unknown command: {cmd}')
            print('Commands: status, gates, handoffs, locks, stalls, next, dispatch, resume,')
            print('          complete, block, release-lock, list, resolve, sweep, launch, archive,')
            print('          dispatch-payload, completions, verify-hooks,')
            print('          autoclave, timeline, timetravel, revert, temporal-sync, context,')
            print('          view, deps, watcher, help')
            print('Or pass a pipeline version/coordinate for quick status.')
            sys.exit(1)


def _extract_flag(args: list, flag: str) -> str | None:
    """Extract a --flag value from args list."""
    try:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
    except ValueError:
        pass
    return None


def _render_hook_verification(results: dict):
    """Render hook verification results to stdout."""
    print(f'\n--- Hook Verification ---\n')

    bpb = results.get('before_prompt_build', {})
    print(f'  before_prompt_build: {bpb.get("status", "?")}')
    if bpb.get('details'):
        print(f'    {bpb["details"]}')

    ae = results.get('agent_end', {})
    print(f'  agent_end: {ae.get("status", "?")}')
    if ae.get('details'):
        print(f'    {ae["details"]}')

    plugins = results.get('plugins', [])
    if plugins:
        print(f'\n  Plugins ({len(plugins)}):')
        for p in plugins:
            exists = '✓' if p.get('exists') else '✗'
            print(f'    {exists} {p.get("path", "?")}')

    naming = results.get('naming_conventions', {})
    if naming.get('issues'):
        print(f'\n  Naming Issues:')
        for issue in naming['issues']:
            print(f'    ⚠ {issue}')
    else:
        print(f'\n  Naming conventions: OK')

    print()


if __name__ == '__main__':
    main()
