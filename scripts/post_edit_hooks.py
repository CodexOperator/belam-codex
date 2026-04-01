#!/usr/bin/env python3
"""
Post-edit hook registry for reactive orchestration.

When execute_edit() in codex_engine.py modifies a primitive's frontmatter,
fire_hooks() is called with the list of operations. Registered hooks inspect
the changes and trigger side-effects (pipeline launch, rewind, queue, etc.).

Hooks are registered at module load and fire synchronously after the edit
is written to disk but before the F-label output is returned to the user.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

WORKSPACE = Path(__file__).resolve().parent.parent


@dataclass
class EditContext:
    """Context passed to each hook's condition and handler functions."""
    coord: str             # "t5", "p3"
    prefix: str            # "t", "p"
    slug: str              # task/pipeline slug
    filepath: Path         # absolute path to the .md file
    field_key: str         # frontmatter field that changed
    old_value: Any         # value before edit
    new_value: Any         # value after edit
    all_fields: dict       # full frontmatter dict after edit
    dry_run: bool = False  # if True, hooks describe but don't execute


@dataclass
class HookResult:
    """Result returned by a hook handler."""
    action: str            # human-readable description of what happened
    f_label_suffix: str    # appended to F-label output line
    cascades: list = field(default_factory=list)  # additional mutations triggered


@dataclass
class PostEditHook:
    """A registered post-edit hook."""
    name: str
    prefix: str            # 't', 'p', or '*' for any
    field_key: str         # specific field or '*' for any
    condition: Callable[[EditContext], bool]
    handler: Callable[[EditContext], HookResult | None]


# Global hook registry
_HOOKS: list[PostEditHook] = []


def register(name: str, prefix: str, field_key: str,
             condition: Callable[[EditContext], bool],
             handler: Callable[[EditContext], HookResult | None]):
    """Register a post-edit hook.

    Args:
        name: Human-readable hook name
        prefix: Primitive prefix to match ('t', 'p', '*')
        field_key: Frontmatter field to match, or '*' for any
        condition: Function(ctx) -> bool, whether to fire
        handler: Function(ctx) -> HookResult, the side-effect
    """
    _HOOKS.append(PostEditHook(
        name=name, prefix=prefix, field_key=field_key,
        condition=condition, handler=handler,
    ))


def fire_hooks(operations: list[dict], all_fields_map: dict = None,
               dry_run: bool = False) -> list[HookResult]:
    """Fire all matching hooks for a batch of edit operations.

    Args:
        operations: List of dicts from execute_edit(), each with:
            coord, prefix (derived), filepath, field_key, old_value, new_value, slug
        all_fields_map: Optional dict mapping coord -> full frontmatter dict
        dry_run: If True, hooks report what they would do without acting

    Returns:
        List of HookResult from all hooks that fired.
    """
    results = []

    for op in operations:
        prefix = op.get('prefix', '')
        if not prefix and 'coord' in op:
            # Derive prefix from coord (e.g., 't5' -> 't', 'pt1' -> 'pt')
            coord = op['coord']
            prefix = ''.join(c for c in coord if c.isalpha())

        ctx = EditContext(
            coord=op.get('coord', ''),
            prefix=prefix,
            slug=op.get('slug', ''),
            filepath=Path(op.get('filepath', '')),
            field_key=op.get('field_key', ''),
            old_value=op.get('old_value'),
            new_value=op.get('new_value'),
            all_fields=all_fields_map.get(op.get('coord', ''), {}) if all_fields_map else {},
            dry_run=dry_run,
        )

        for hook in _HOOKS:
            # Match prefix
            if hook.prefix != '*' and hook.prefix != ctx.prefix:
                continue
            # Match field
            if hook.field_key != '*' and hook.field_key != ctx.field_key:
                continue
            # Check condition
            try:
                if not hook.condition(ctx):
                    continue
            except Exception:
                continue

            # Fire handler
            try:
                result = hook.handler(ctx)
                if result:
                    results.append(result)
            except Exception as e:
                results.append(HookResult(
                    action=f"HOOK ERROR ({hook.name}): {e}",
                    f_label_suffix=f"err:{hook.name}",
                ))

    return results


# ═══════════════════════════════════════════════════════════════════════
# Concrete hooks — registered at module load
# ═══════════════════════════════════════════════════════════════════════

def _task_status_to_open_condition(ctx: EditContext) -> bool:
    """Task status changed to 'open' and has a pipeline_template set."""
    return (ctx.new_value == 'open'
            and ctx.all_fields.get('pipeline_template', ''))


def _task_status_to_open_handler(ctx: EditContext) -> HookResult | None:
    """Queue task for pipeline launch."""
    template = ctx.all_fields.get('pipeline_template', '')
    if ctx.dry_run:
        return HookResult(
            action=f"[dry-run] Would queue {ctx.coord} for pipeline launch (template: {template})",
            f_label_suffix=f"queue:{ctx.coord}",
        )

    # Update task fields to mark as queued
    _update_frontmatter(ctx.filepath, {
        'pipeline_status': 'queued',
        'launch_mode': ctx.all_fields.get('launch_mode', 'queued'),
    })

    return HookResult(
        action=f"Queued {ctx.coord} for pipeline launch (template: {template})",
        f_label_suffix=f"queue:{ctx.coord}",
        cascades=[{'coord': ctx.coord, 'field': 'pipeline_status', 'value': 'queued'}],
    )


def _task_status_to_active_condition(ctx: EditContext) -> bool:
    """Task status changed to 'active' and has a pipeline_template set."""
    return (ctx.new_value == 'active'
            and ctx.all_fields.get('pipeline_template', ''))


def _task_status_to_active_handler(ctx: EditContext) -> HookResult | None:
    """Immediately launch pipeline, bypassing concurrency limits."""
    import subprocess

    template = ctx.all_fields.get('pipeline_template', '')
    slug = ctx.slug

    if ctx.dry_run:
        return HookResult(
            action=f"[dry-run] Would launch pipeline for {ctx.coord} (template: {template}, bypass concurrency)",
            f_label_suffix=f"launch:{ctx.coord}",
        )

    # Update task to launching state
    _update_frontmatter(ctx.filepath, {
        'pipeline_status': 'launching',
        'launch_mode': 'active',
    })

    # Launch pipeline via launch_pipeline.py
    launch_script = WORKSPACE / 'scripts' / 'launch_pipeline.py'
    if launch_script.exists():
        try:
            result = subprocess.run(
                ['python3', str(launch_script), slug,
                 '--template', template,
                 '--bypass-concurrency',
                 '--kickoff'],
                capture_output=True, text=True, timeout=30,
                cwd=str(WORKSPACE),
            )
            if result.returncode == 0:
                return HookResult(
                    action=f"Launched pipeline for {ctx.coord} (template: {template})",
                    f_label_suffix=f"launch:{ctx.coord}",
                    cascades=[{'coord': ctx.coord, 'field': 'pipeline_status', 'value': 'launching'}],
                )
            else:
                return HookResult(
                    action=f"Pipeline launch failed for {ctx.coord}: {result.stderr[:200]}",
                    f_label_suffix=f"launch-fail:{ctx.coord}",
                )
        except subprocess.TimeoutExpired:
            return HookResult(
                action=f"Pipeline launch timed out for {ctx.coord}",
                f_label_suffix=f"launch-timeout:{ctx.coord}",
            )

    return HookResult(
        action=f"Pipeline launch script not found, {ctx.coord} marked as launching",
        f_label_suffix=f"launch-pending:{ctx.coord}",
    )


def _pipeline_stage_rewind_condition(ctx: EditContext) -> bool:
    """Pipeline stage field set to an earlier stage."""
    if ctx.field_key not in ('pending_action', 'stage', 'current_stage'):
        return False
    if not ctx.new_value or not ctx.old_value:
        return False
    return ctx.new_value != ctx.old_value


def _pipeline_stage_rewind_handler(ctx: EditContext) -> HookResult | None:
    """Rewind pipeline to the specified stage."""
    try:
        from pipeline_rewind import rewind_to_stage
    except ImportError:
        return HookResult(
            action=f"pipeline_rewind module not available",
            f_label_suffix="rewind-unavailable",
        )

    version = ctx.all_fields.get('version', ctx.slug)
    target_stage = ctx.new_value

    if ctx.dry_run:
        return HookResult(
            action=f"[dry-run] Would rewind {ctx.coord} to stage: {target_stage}",
            f_label_suffix=f"rewind:{ctx.coord}",
        )

    try:
        result = rewind_to_stage(version, target_stage)
        rewound = result.get('rewound_stages', [])
        return HookResult(
            action=f"Rewound {ctx.coord} to {target_stage} ({len(rewound)} stages reset)",
            f_label_suffix=f"rewind:{ctx.coord}",
            cascades=[{'coord': ctx.coord, 'field': 'pending_action', 'value': target_stage}],
        )
    except Exception as e:
        return HookResult(
            action=f"Rewind failed for {ctx.coord}: {e}",
            f_label_suffix=f"rewind-fail:{ctx.coord}",
        )


def _pipeline_reset_condition(ctx: EditContext) -> bool:
    """Pipeline reset flag set to true."""
    if ctx.field_key != 'reset':
        return False
    return str(ctx.new_value).lower() in ('true', '1', 'yes')


def _pipeline_reset_handler(ctx: EditContext) -> HookResult | None:
    """Reset current phase of the pipeline."""
    try:
        from pipeline_rewind import reset_current_phase
    except ImportError:
        return HookResult(
            action=f"pipeline_rewind module not available",
            f_label_suffix="reset-unavailable",
        )

    version = ctx.all_fields.get('version', ctx.slug)

    if ctx.dry_run:
        return HookResult(
            action=f"[dry-run] Would reset current phase of {ctx.coord}",
            f_label_suffix=f"reset:{ctx.coord}",
        )

    try:
        result = reset_current_phase(version)
        # Clear the reset flag after execution
        _update_frontmatter(ctx.filepath, {'reset': 'false'})
        return HookResult(
            action=f"Reset {ctx.coord} to phase {result.get('phase', '?')} start",
            f_label_suffix=f"reset:{ctx.coord}",
            cascades=[{'coord': ctx.coord, 'field': 'reset', 'value': 'false'}],
        )
    except Exception as e:
        return HookResult(
            action=f"Reset failed for {ctx.coord}: {e}",
            f_label_suffix=f"reset-fail:{ctx.coord}",
        )


def _pipeline_phase_rewind_condition(ctx: EditContext) -> bool:
    """Pipeline phase field set to a lower number."""
    if ctx.field_key not in ('current_phase', 'phase'):
        return False
    try:
        new_phase = int(ctx.new_value)
        old_phase = int(ctx.old_value) if ctx.old_value else 999
        return new_phase < old_phase
    except (ValueError, TypeError):
        return False


def _pipeline_phase_rewind_handler(ctx: EditContext) -> HookResult | None:
    """Rewind pipeline to the start of the specified phase."""
    try:
        from pipeline_rewind import rewind_to_phase
    except ImportError:
        return HookResult(
            action=f"pipeline_rewind module not available",
            f_label_suffix="phase-rewind-unavailable",
        )

    version = ctx.all_fields.get('version', ctx.slug)
    target_phase = int(ctx.new_value)

    if ctx.dry_run:
        return HookResult(
            action=f"[dry-run] Would rewind {ctx.coord} to phase {target_phase}",
            f_label_suffix=f"phase-rewind:{ctx.coord}",
        )

    try:
        result = rewind_to_phase(version, target_phase)
        return HookResult(
            action=f"Rewound {ctx.coord} to phase {target_phase} ({result.get('target_stage', '?')})",
            f_label_suffix=f"phase-rewind:{ctx.coord}",
        )
    except Exception as e:
        return HookResult(
            action=f"Phase rewind failed for {ctx.coord}: {e}",
            f_label_suffix=f"phase-rewind-fail:{ctx.coord}",
        )


# ═══════════════════════════════════════════════════════════════════════
# Helper: update frontmatter fields on a .md file
# ═══════════════════════════════════════════════════════════════════════

def _update_frontmatter(filepath: Path, updates: dict):
    """Update specific frontmatter fields in a .md file, preserving everything else."""
    import re as _re

    text = filepath.read_text()
    m = _re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, _re.DOTALL)
    if not m:
        return

    fm_text = m.group(1)
    body = m.group(2)

    lines = fm_text.splitlines()
    updated_keys = set()

    for i, line in enumerate(lines):
        kv = _re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if kv:
            key = kv.group(1)
            if key in updates:
                value = updates[key]
                lines[i] = f'{key}: {value}'
                updated_keys.add(key)

    # Add any fields not already present
    for key, value in updates.items():
        if key not in updated_keys:
            lines.append(f'{key}: {value}')

    new_fm = '\n'.join(lines)
    new_text = f'---\n{new_fm}\n---\n{body}'
    filepath.write_text(new_text)


# ═══════════════════════════════════════════════════════════════════════
# Register all hooks at module load
# ═══════════════════════════════════════════════════════════════════════

register(
    name='task-status-open-queue',
    prefix='t', field_key='status',
    condition=_task_status_to_open_condition,
    handler=_task_status_to_open_handler,
)

register(
    name='task-status-active-launch',
    prefix='t', field_key='status',
    condition=_task_status_to_active_condition,
    handler=_task_status_to_active_handler,
)

register(
    name='pipeline-stage-rewind',
    prefix='p', field_key='*',
    condition=_pipeline_stage_rewind_condition,
    handler=_pipeline_stage_rewind_handler,
)

register(
    name='pipeline-reset-phase',
    prefix='p', field_key='reset',
    condition=_pipeline_reset_condition,
    handler=_pipeline_reset_handler,
)

register(
    name='pipeline-phase-rewind',
    prefix='p', field_key='*',
    condition=_pipeline_phase_rewind_condition,
    handler=_pipeline_phase_rewind_handler,
)
