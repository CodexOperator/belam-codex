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
  python3 scripts/orchestration_engine.py --dry-run          # dry run sweep
  python3 scripts/orchestration_engine.py --json <cmd>       # JSON output mode

  All commands accept --json for structured output (zero coordinator tokens).
"""

import json
import os
import re
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
BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
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

    # Lifecycle actions (engine executes, not coordinator)
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

    def to_dict(self) -> dict:
        """Serialize for JSON output / tool relay."""
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
            'pre_actions': self.pre_actions,
            'post_actions': self.post_actions,
            'context': {
                'pipeline_version': self.pipeline_version,
                'pipeline_coord': self.pipeline_coord,
                'current_stage': self.current_stage,
                'agent_index': self.agent_index,
                'stage_index': self.stage_index,
                'files_to_read': self.files_to_read,
                'completion_command': self.completion_command,
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
    return (f'python3 scripts/orchestration_engine.py complete {version} {stage} '
            f'--agent {agent} --notes "summary"')


def _build_block_command(version: str, stage: str, agent: str) -> str:
    """Build the CLI block command agents use to report issues."""
    return (f'python3 scripts/orchestration_engine.py block {version} {stage} '
            f'--agent {agent} --notes "reason"')


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

    return f"""🔄 Pipeline Handoff — {version}

**Stage completed:** {_previous_stage(stage) or 'initial'}
**Your task:** {stage}
**Summary:** {notes or '(no notes from previous stage)'}

⚠️ **IMPORTANT — Session Protocol:**
This is a FRESH session. You have no prior context except your memory files.
1. Read your memory files first: `memory/` directory in your workspace
2. Read the files listed below for pipeline context
3. Do your work for THIS pipeline only (one pipeline per session)
4. Before completing, crystallize what you learned to memory.

**Read these files before starting:**
{files_list}

**When you finish:**
```
{comp_cmd}
```

If you need to BLOCK:
```
{block_cmd}
```
"""


def _previous_stage(stage: str) -> str | None:
    """Get the stage that precedes this one in the sequence."""
    try:
        idx = STAGE_SEQUENCE.index(stage)
        return STAGE_SEQUENCE[idx - 1] if idx > 0 else None
    except ValueError:
        return None


def _files_for_stage(version: str, stage: str, agent: str) -> list[str]:
    """Determine which files an agent should read for a given stage."""
    base_files = []

    # Task file (if exists)
    task_candidates = list(WORKSPACE.glob(f'tasks/*{version}*'))
    for tc in task_candidates:
        base_files.append(str(tc.relative_to(WORKSPACE)))

    # Previous stage artifacts
    if 'critic' in stage:
        # Critics read the architect's design
        design_file = BUILDS_DIR / f'{version}_architect_design.md'
        if design_file.exists():
            base_files.append(str(design_file.relative_to(WORKSPACE)))
    if 'builder' in stage:
        # Builders read design + critic review
        for suffix in ['_architect_design.md', '_critic_design_review.md']:
            f = BUILDS_DIR / f'{version}{suffix}'
            if f.exists():
                base_files.append(str(f.relative_to(WORKSPACE)))
    if 'code_review' in stage:
        # Code reviewers read the implementation
        impl_file = BUILDS_DIR / f'{version}_builder_implementation.md'
        if impl_file.exists():
            base_files.append(str(impl_file.relative_to(WORKSPACE)))

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
    )


# ─── Atomic Lock Acquire (TOCTOU fix — critic FLAG-1) ──────────────────────────

LOCKS_DIR = PIPELINES_DIR / 'locks'


def atomic_lock_acquire(pipeline: str, agent: str, pid: int = None,
                         timeout_minutes: int = 10) -> bool:
    """Acquire a pipeline lock atomically using O_CREAT|O_EXCL.

    Prevents TOCTOU race condition where two concurrent processes both
    see "no lock" and both write. The kernel guarantees only one O_EXCL
    open succeeds.

    Returns True if lock acquired, False if already locked by live process.
    """
    if pid is None:
        pid = os.getpid()

    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = LOCKS_DIR / f'{pipeline}.lock.json'

    # Check if existing lock is stale (different from acquire — read-only check)
    if lock_file.exists():
        try:
            existing = json.loads(lock_file.read_text())
            existing_pid = existing.get('pid')
            if existing_pid and _pid_alive(existing_pid):
                return False  # Genuinely locked by live process
            # Stale lock — remove it, then try atomic acquire
            lock_file.unlink(missing_ok=True)
            fl = generate_f_label('lock_change', {'pipeline': pipeline, 'action': 'stale_cleared'})
            print(f'  {fl}')
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
            data['stale'] = (not data['pid_alive']) or data.get('past_timeout', False)
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
    """Determine gate status for a pipeline."""
    pending = state.get('pending_action', 'none')
    status = fm.get('status', '')

    gates = {}

    # Phase 2 gate
    if 'phase1_complete' in pending or 'phase1_complete' in status:
        gates['phase2'] = 'open' if BUILDS_DIR.joinpath(
            f'{version}_phase2_shael_direction.md').exists() else 'closed'

    # Phase 3 gate
    phase2_status = state.get('phase2', {}).get('stage', '')
    gates['phase3'] = 'open' if 'complete' in phase2_status else 'locked'

    return gates


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

    # Legacy dispatch via orchestrate machinery
    if not _HAS_ORCHESTRATE:
        print(f'ERROR: pipeline_orchestrate.py not available for dispatch')
        return False

    fl = generate_f_label('dispatch', {
        'agent': agent, 'coord': _get_pipeline_coord(version), 'stage': stage
    })

    # Use orchestrate_complete to trigger the dispatch chain
    # For initial kickoff (pipeline_created), use that as the completed stage
    if stage == 'pipeline_created' or stage == 'architect_design':
        print(f'  {fl}')
        return orchestrate_complete(version, 'pipeline_created', 'belam-main',
                                     f'Dispatched by orchestration_engine')
    else:
        # Build and send a handoff message directly
        print(f'  {fl}')
        reset_agent_session(agent)
        session_id = generate_session_id(version, agent)
        handoff_msg = build_handoff_message(version, '', stage, agent,
                                             f'Dispatched by orchestration engine for {stage}')
        wake_result = wake_agent(agent, handoff_msg, timeout=600, session_id=session_id)

        if wake_result['success']:
            write_handoff(version, '', stage, agent, wake_result, session_id)
            return True
        elif wake_result['status'] == 'timeout':
            wake_result = checkpoint_and_resume(agent, version, stage, '', resume_count=0)
            return wake_result.get('success', False)
        else:
            print(f'  FAILED: {wake_result.get("error", "")}')
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
    kicked = False
    for g in gates:
        status_label = g['status'].upper()
        blocked = f' (blocked by: {g["blocked_by"]})' if g.get('blocked_by') else ''
        print(f'  {g["pipeline"]}: {g["gate"]} = {status_label}{blocked}')
        if g.get('action'):
            print(f'    -> {g["action"]}')

        # Auto-kick eligible pipelines (one at a time)
        if g['status'] in ('eligible', 'open') and not kicked and not dry_run:
            if g['gate'] == 'kickoff' and _HAS_ORCHESTRATE:
                print(f'    -> Auto-kicking {g["pipeline"]}...')
                try:
                    result = orchestrate_complete(g['pipeline'], 'pipeline_created',
                                                  'belam-main', 'Auto-kicked by sweep')
                    if result:
                        actions.append(f'F1 D {g["pipeline"]}.kickoff -> architect_design')
                        kicked = True
                except Exception as e:
                    print(f'    -> Kick failed: {e}')
            elif g['gate'] == 'analysis' and _HAS_ORCHESTRATE:
                print(f'    -> Auto-launching analysis for {g["pipeline"]}...')
                try:
                    from pipeline_orchestrate import orchestrate_local_analysis
                    result = orchestrate_local_analysis(g['pipeline'])
                    if result:
                        actions.append(f'F1 D {g["pipeline"]}.analysis LAUNCHED')
                        kicked = True
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
            if not kicked and not dry_run and _HAS_ORCHESTRATE:
                try:
                    from pipeline_orchestrate import orchestrate_revise
                    context = rf.read_text()
                    result = orchestrate_revise(ver, context)
                    if result:
                        actions.append(f'F1 D {ver}.revision KICKED')
                        kicked = True
                        rf.unlink()
                except Exception as e:
                    print(f'    -> Revision kick failed: {e}')
    else:
        print('  No pending revisions.')

    # 5. Check stalls (only if nothing was kicked -- one at a time)
    print(f'\n--- Stall Check (>{STALL_THRESHOLD_MINUTES}min) ---\n')
    stalls = check_stalls()
    if stalls:
        for s in stalls:
            print(f'  STALLED: {s["pipeline"]}/{s["pending_action"]} by {s["agent"]} ({s["age_minutes"]:.0f}min)')
            if not kicked and not dry_run and _HAS_ORCHESTRATE:
                print(f'    -> Auto-recovering...')
                try:
                    ok = pipeline_resume(s['pipeline'])
                    if ok:
                        actions.append(f'F1 D {s["pipeline"]}.stall_recovery {s["agent"]} RESUMED')
                        kicked = True
                except Exception as e:
                    print(f'    -> Recovery failed: {e}')
            elif dry_run:
                actions.append(f'[DRY] Would resume {s["pipeline"]}/{s["pending_action"]}')
    else:
        print('  No stalled pipelines.')

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

    # Use legacy orchestrate_complete if available
    if _HAS_ORCHESTRATE:
        try:
            result = orchestrate_complete(version, stage, agent, notes)
            return {'status': 'completed', 'dispatched': bool(result), 'f_label': fl}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'f_label': fl}

    # Fallback: just update state and build next payload
    next_stg = _next_stage_for(stage)
    if not next_stg:
        return {'status': 'terminal', 'message': f'No transition from {stage}', 'f_label': fl}

    next_agent = _agent_from_action(next_stg)
    payload = build_dispatch_payload(version, next_stg, next_agent, notes=notes)

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
            result = orchestrate_block(version, stage, agent, notes)
            return {'status': 'blocked', 'dispatched': bool(result), 'f_label': fl}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'f_label': fl}

    if not block_target:
        return {'status': 'blocked', 'message': f'No block target for {stage}', 'f_label': fl}

    target_agent = _agent_from_action(block_target)
    payload = build_dispatch_payload(version, block_target, target_agent, notes=notes)

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
            print('          complete, block, release-lock, list, resolve, sweep,')
            print('          dispatch-payload, verify-hooks, help')
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
