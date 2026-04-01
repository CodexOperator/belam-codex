#!/usr/bin/env python3
"""
Pipeline rewind engine.

Provides three rewind operations for pipelines:
  - rewind_to_stage: rewind to a specific stage
  - rewind_to_phase: rewind to the start of a specific phase
  - reset_current_phase: rewind to the start of the current phase

All operations:
  1. Validate the target using template_parser stage ordering
  2. Mark later stages as 'rewound' in _state.json (preserving audit trail)
  3. Update pending_action and clear dispatch_claimed
  4. Update .md frontmatter (source of truth)

Usage:
  python3 scripts/pipeline_rewind.py <version> --stage <stage>
  python3 scripts/pipeline_rewind.py <version> --phase <n>
  python3 scripts/pipeline_rewind.py <version> --reset
  python3 scripts/pipeline_rewind.py <version> --stage <stage> --dry-run
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PIPELINES_DIR = WORKSPACE / 'pipelines'
BUILDS_DIR = WORKSPACE / 'pipeline_builds'

# Add scripts dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def _load_pipeline(version: str) -> tuple[Path, dict, Path, dict]:
    """Load pipeline .md frontmatter and _state.json.

    Returns: (md_path, md_fields, state_path, state_dict)
    Raises: FileNotFoundError if pipeline not found.
    """
    # Find pipeline .md
    md_path = None
    for f in PIPELINES_DIR.glob('*.md'):
        text = f.read_text()
        m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
        if m:
            fm = m.group(1)
            if re.search(rf'version:\s*{re.escape(version)}', fm):
                md_path = f
                break
    if not md_path:
        # Try slug-based lookup
        candidate = PIPELINES_DIR / f'{version}.md'
        if candidate.exists():
            md_path = candidate

    if not md_path:
        raise FileNotFoundError(f"Pipeline not found: {version}")

    # Parse .md frontmatter
    text = md_path.read_text()
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    md_fields = {}
    if m:
        for line in m.group(1).splitlines():
            kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
            if kv:
                md_fields[kv.group(1)] = kv.group(2).strip()

    # Find _state.json
    state_path = None
    state = {}
    # Try subdirectory first
    subdir_state = BUILDS_DIR / version / '_state.json'
    flat_state = BUILDS_DIR / f'{version}_state.json'
    if subdir_state.exists():
        state_path = subdir_state
    elif flat_state.exists():
        state_path = flat_state

    if state_path:
        try:
            state = json.loads(state_path.read_text())
        except (json.JSONDecodeError, OSError):
            state = {}

    return md_path, md_fields, state_path, state


def _get_template_for_pipeline(md_fields: dict) -> str:
    """Determine template name from pipeline .md fields."""
    ptype = md_fields.get('type', '')
    if 'builder-first' in ptype or 'infrastructure' in ptype:
        return 'builder-first'
    return 'research'


def _update_md_frontmatter(md_path: Path, updates: dict):
    """Update specific frontmatter fields in pipeline .md."""
    text = md_path.read_text()
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, re.DOTALL)
    if not m:
        return

    fm_text = m.group(1)
    body = m.group(2)
    lines = fm_text.splitlines()
    updated_keys = set()

    for i, line in enumerate(lines):
        kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if kv and kv.group(1) in updates:
            key = kv.group(1)
            lines[i] = f'{key}: {updates[key]}'
            updated_keys.add(key)

    for key, value in updates.items():
        if key not in updated_keys:
            lines.append(f'{key}: {value}')

    new_fm = '\n'.join(lines)
    md_path.write_text(f'---\n{new_fm}\n---\n{body}')


def rewind_to_stage(version: str, target_stage: str, dry_run: bool = False) -> dict:
    """Rewind pipeline to target_stage.

    Marks all stages after target as 'rewound' (preserving audit trail).
    Sets pending_action = target_stage, clears dispatch_claimed.

    Returns dict with: version, target_stage, rewound_stages, phase
    """
    from template_parser import parse_template, get_stage_order

    md_path, md_fields, state_path, state = _load_pipeline(version)
    template_name = _get_template_for_pipeline(md_fields)
    stage_order = get_stage_order(template_name)

    if not stage_order:
        raise ValueError(f"Could not get stage order for template: {template_name}")

    # Validate target stage exists
    if target_stage not in stage_order:
        raise ValueError(f"Stage '{target_stage}' not found in template '{template_name}'. "
                         f"Valid stages: {', '.join(stage_order)}")

    target_idx = stage_order.index(target_stage)

    # Find stages to mark as rewound (everything after target)
    rewound_stages = []
    stages_dict = state.get('stages', {})
    for stage_name in stage_order[target_idx + 1:]:
        if stage_name in stages_dict:
            rewound_stages.append(stage_name)

    # Determine phase from target stage
    from template_parser import stage_phase
    phase = stage_phase(template_name, target_stage)

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')

    if dry_run:
        return {
            'version': version,
            'target_stage': target_stage,
            'rewound_stages': rewound_stages,
            'phase': phase,
            'dry_run': True,
        }

    # Mark rewound stages
    for stage_name in rewound_stages:
        if stage_name in stages_dict:
            stages_dict[stage_name]['status'] = 'rewound'
            stages_dict[stage_name]['rewound_at'] = now

    # Clear target stage if it exists (so it can be re-executed)
    if target_stage in stages_dict:
        stages_dict[target_stage]['status'] = 'pending'
        stages_dict[target_stage].pop('completed_at', None)

    # Update state
    state['pending_action'] = target_stage
    state['dispatch_claimed'] = False
    state['last_updated'] = now
    state['current_phase'] = phase

    # Write state JSON
    if state_path:
        state_path.write_text(json.dumps(state, indent=2))

    # Write-through to .md
    _update_md_frontmatter(md_path, {
        'pending_action': target_stage,
        'dispatch_claimed': 'false',
        'last_updated': now,
        'current_phase': str(phase),
        'status': f'p{phase}_active',
    })

    return {
        'version': version,
        'target_stage': target_stage,
        'rewound_stages': rewound_stages,
        'phase': phase,
    }


def rewind_to_phase(version: str, target_phase: int, dry_run: bool = False) -> dict:
    """Rewind to first stage of target_phase.

    Returns dict with: version, target_stage, target_phase, rewound_stages
    """
    from template_parser import get_phase_first_stage

    md_path, md_fields, state_path, state = _load_pipeline(version)
    template_name = _get_template_for_pipeline(md_fields)
    first_stage = get_phase_first_stage(template_name, target_phase)

    if not first_stage:
        raise ValueError(f"Could not find first stage of phase {target_phase} "
                         f"in template '{template_name}'")

    result = rewind_to_stage(version, first_stage, dry_run=dry_run)
    result['target_phase'] = target_phase
    return result


def reset_current_phase(version: str, dry_run: bool = False) -> dict:
    """Detect current phase, rewind to its first stage.

    Returns dict with: version, target_stage, phase, rewound_stages
    """
    from template_parser import stage_phase, get_phase_first_stage

    md_path, md_fields, state_path, state = _load_pipeline(version)
    template_name = _get_template_for_pipeline(md_fields)

    # Determine current phase from pending_action or status
    pending = state.get('pending_action', '') or md_fields.get('pending_action', '')
    if pending:
        current_phase = stage_phase(template_name, pending)
    else:
        # Try to extract from status field (e.g., 'p2_complete' -> phase 2)
        status = state.get('status', '') or md_fields.get('status', '')
        m = re.match(r'p(\d+)', status)
        current_phase = int(m.group(1)) if m else 1

    if not current_phase:
        current_phase = 1

    result = rewind_to_phase(version, current_phase, dry_run=dry_run)
    return result


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  pipeline_rewind.py <version> --stage <stage> [--dry-run]")
        print("  pipeline_rewind.py <version> --phase <n> [--dry-run]")
        print("  pipeline_rewind.py <version> --reset [--dry-run]")
        sys.exit(1)

    version = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    try:
        if '--stage' in sys.argv:
            idx = sys.argv.index('--stage')
            target_stage = sys.argv[idx + 1]
            result = rewind_to_stage(version, target_stage, dry_run=dry_run)
        elif '--phase' in sys.argv:
            idx = sys.argv.index('--phase')
            target_phase = int(sys.argv[idx + 1])
            result = rewind_to_phase(version, target_phase, dry_run=dry_run)
        elif '--reset' in sys.argv:
            result = reset_current_phase(version, dry_run=dry_run)
        else:
            print("Specify --stage, --phase, or --reset")
            sys.exit(1)

        prefix = '[DRY RUN] ' if dry_run else ''
        print(f"{prefix}Rewind {version}:")
        print(f"  Target: {result.get('target_stage', '?')}")
        print(f"  Phase: {result.get('phase', '?')}")
        rewound = result.get('rewound_stages', [])
        if rewound:
            print(f"  Rewound stages: {', '.join(rewound)}")
        else:
            print(f"  No stages to rewind")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
