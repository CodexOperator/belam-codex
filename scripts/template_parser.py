#!/usr/bin/env python3
"""
Parse pipeline template YAML from markdown files.

Templates live in templates/{name}-pipeline.md and contain a fenced YAML block
under `## Stage Transitions` with either:
  A) Legacy format: transitions, status_bumps, etc. as flat dicts
  B) Phase-based format: phases: with numbered phase containers

Returns structured dicts matching the shape consumed by pipeline_update.py:
  - transitions: stage → (next_stage, agent, message, session_mode)
  - block_transitions: stage → (next_stage, agent, message)
  - status_bumps: stage → status_string
  - start_status_bumps: stage → status_string
  - human_gates: set of stages
  - first_agent: str
  - pipeline_fields: dict with 'type' and 'stages'
"""

import re
import sys
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'

# Cache parsed templates
_cache: dict[str, dict | None] = {}


def parse_template(template_name: str) -> dict | None:
    """Parse templates/{template_name}-pipeline.md, return structured transitions.

    Returns dict with keys:
      - first_agent: str
      - transitions: dict  (stage → (next_stage, agent, message, session_mode))
      - block_transitions: dict  (stage → (next_stage, agent, message))
      - status_bumps: dict  (stage → status_string)
      - start_status_bumps: dict  (stage → status_string)
      - human_gates: set[str]
      - pipeline_fields: dict  (type, stages)

    Returns None if template not found or unparseable.
    """
    if template_name in _cache:
        return _cache[template_name]

    template_file = TEMPLATES_DIR / f'{template_name}-pipeline.md'
    if not template_file.exists():
        _cache[template_name] = None
        return None

    content = template_file.read_text()

    # Extract YAML code block after "## Stage Transitions"
    match = re.search(
        r'## Stage Transitions.*?```yaml\s*\n(.*?)```',
        content, re.DOTALL
    )
    if not match:
        _cache[template_name] = None
        return None

    yaml_block = match.group(1)

    # Detect format: phase-based vs legacy
    if HAS_YAML:
        try:
            data = yaml.safe_load(yaml_block)
        except yaml.YAMLError:
            data = None

        if isinstance(data, dict) and 'phases' in data:
            result = _parse_phase_based(data)
        elif isinstance(data, dict):
            result = _parse_legacy_yaml(data)
        else:
            result = _parse_manually(yaml_block)
    else:
        # Manual parser — check for phases: key
        if re.search(r'^phases:\s*$', yaml_block, re.MULTILINE):
            result = _parse_phase_based_manual(yaml_block)
        else:
            result = _parse_manually(yaml_block)

    _cache[template_name] = result
    return result


# ═══════════════════════════════════════════════════════════════════════
# Phase-based format parser (new)
# ═══════════════════════════════════════════════════════════════════════

def _parse_phase_based(data: dict) -> dict | None:
    """Parse the new phases: YAML format into the standard output shape."""
    first_agent = data.get('first_agent', 'architect')
    pipeline_type = data.get('type', 'unknown')
    phases = data.get('phases', {})
    block_routing = data.get('block_routing', {})
    complete_task_agent = data.get('complete_task_agent', 'architect')

    # Also parse any extra_transitions for backward compat / special cases
    extra_transitions = data.get('extra_transitions', {})
    extra_block_transitions = data.get('extra_block_transitions', {})

    transitions = {}
    block_transitions = {}
    status_bumps = {}
    start_status_bumps = {}
    human_gates = set()
    all_stage_names = []

    sorted_phase_nums = sorted(int(k) for k in phases.keys())

    for phase_num in sorted_phase_nums:
        phase = phases[phase_num]
        stages = phase.get('stages', [])
        gate = phase.get('gate', 'human')

        # Generate stage names for this phase
        phase_stage_names = []
        for stage_def in stages:
            role = stage_def['role']
            action = stage_def['action']
            name = f'p{phase_num}_{role}_{action}'
            phase_stage_names.append(name)
        
        complete_name = f'p{phase_num}_complete'
        all_stage_names.extend(phase_stage_names)
        all_stage_names.append(complete_name)

        # Generate transitions within the phase
        for i, stage_def in enumerate(stages):
            name = phase_stage_names[i]
            role = stage_def['role']
            session = stage_def.get('session', 'fresh')

            if i + 1 < len(stages):
                # Transition to next stage in phase
                next_name = phase_stage_names[i + 1]
                next_role = stages[i + 1]['role']
                next_action = stages[i + 1]['action']
                msg = f'Phase {phase_num}: {role} {stage_def["action"]} complete. Next: {next_role} {next_action}.'
                next_session = stages[i + 1].get('session', 'fresh')
                transitions[name] = (next_name, next_role, msg, next_session)
            else:
                # Last stage → phase complete
                msg = f'Phase {phase_num} stages complete. Phase review.'
                transitions[name] = (complete_name, 'system', msg, 'fresh')
                if gate == 'human':
                    human_gates.add(complete_name)

        # Phase complete → next phase (if auto gate) or human gate
        if gate == 'auto':
            # Find next phase
            idx = sorted_phase_nums.index(phase_num)
            if idx + 1 < len(sorted_phase_nums):
                next_phase_num = sorted_phase_nums[idx + 1]
                next_phase = phases[next_phase_num]
                next_stages = next_phase.get('stages', [])
                if next_stages:
                    next_first = f'p{next_phase_num}_{next_stages[0]["role"]}_{next_stages[0]["action"]}'
                    next_role = next_stages[0]['role']
                    msg = f'Phase {phase_num} complete (auto-gate). Starting phase {next_phase_num}.'
                    transitions[complete_name] = (next_first, next_role, msg, 'fresh')
        elif gate == 'human':
            # Human gate — transition exists to next phase but is gated
            idx = sorted_phase_nums.index(phase_num)
            if idx + 1 < len(sorted_phase_nums):
                next_phase_num = sorted_phase_nums[idx + 1]
                next_phase = phases[next_phase_num]
                next_stages = next_phase.get('stages', [])
                if next_stages:
                    next_first = f'p{next_phase_num}_{next_stages[0]["role"]}_{next_stages[0]["action"]}'
                    next_role = next_stages[0]['role']
                    msg = f'Phase {phase_num} complete. Awaiting human approval for phase {next_phase_num}.'
                    transitions[complete_name] = (next_first, next_role, msg, 'fresh')

        # Generate status bumps for this phase
        for i, stage_def in enumerate(stages):
            name = phase_stage_names[i]
            role = stage_def['role']
            action = stage_def['action']
            status_bumps[name] = f'p{phase_num}_{action}'
            start_status_bumps[name] = f'p{phase_num}_active'

        status_bumps[complete_name] = f'p{phase_num}_complete'
        start_status_bumps[complete_name] = f'p{phase_num}_complete'

    # pipeline_created → first stage of phase 1
    if sorted_phase_nums:
        first_phase = sorted_phase_nums[0]
        first_phase_stages = phases[first_phase].get('stages', [])
        if first_phase_stages:
            first_stage_name = f'p{first_phase}_{first_phase_stages[0]["role"]}_{first_phase_stages[0]["action"]}'
            transitions['pipeline_created'] = (
                first_stage_name,
                first_phase_stages[0]['role'],
                f'Pipeline created. Starting phase {first_phase}.',
                'fresh',
            )
            status_bumps[first_stage_name] = f'p{first_phase}_{first_phase_stages[0]["action"]}'

    # Generate block transitions from block_routing
    for blocker_role, routing in block_routing.items():
        for blocker_action, fix_target in routing.items():
            # Support both string ("builder") and dict ({ agent: builder, session: continue }) formats
            if isinstance(fix_target, dict):
                fix_role = fix_target.get('agent', fix_target.get('role', ''))
                block_session_mode = fix_target.get('session', 'fresh')
            else:
                fix_role = fix_target
                block_session_mode = 'fresh'

            # For every phase, generate block transitions for matching stages
            for phase_num in sorted_phase_nums:
                phase = phases[phase_num]
                stages_list = phase.get('stages', [])
                phase_stage_names_local = [
                    f'p{phase_num}_{s["role"]}_{s["action"]}' for s in stages_list
                ]

                for i, stage_def in enumerate(stages_list):
                    if stage_def['role'] == blocker_role and stage_def['action'] == blocker_action:
                        block_stage = phase_stage_names_local[i]
                        fix_stage = f'p{phase_num}_{fix_role}_fix_blocks'
                        # Find the fix_role's last stage before the blocker for re-entry
                        fix_msg = f'Phase {phase_num}: {blocker_role} blocked at {blocker_action}. {fix_role} fix required.'

                        # 4-tuple: (fix_stage, fix_role, fix_msg, session_mode)
                        block_transitions[block_stage] = (fix_stage, fix_role, fix_msg, block_session_mode)

                        # The fix stage transitions back to the blocker — always fresh (cross-agent)
                        transitions[fix_stage] = (block_stage, blocker_role,
                                                  f'Blocks fixed. Re-review by {blocker_role}.', 'fresh')

    # Add extra transitions (for backward compat / special cases defined in template)
    for stage, value in extra_transitions.items():
        if isinstance(value, list) and len(value) >= 3:
            session_mode = 'fresh'
            for item in value[3:]:
                if isinstance(item, dict) and 'session' in item:
                    session_mode = item['session']
                elif isinstance(item, str) and item.startswith('session:'):
                    session_mode = item.split(':', 1)[1].strip()
            transitions[stage] = (value[0], value[1], value[2], session_mode)

    for stage, value in extra_block_transitions.items():
        if isinstance(value, list) and len(value) >= 3:
            block_transitions[stage] = (value[0], value[1], value[2])

    return {
        'first_agent': first_agent,
        'transitions': transitions,
        'block_transitions': block_transitions,
        'status_bumps': status_bumps,
        'start_status_bumps': start_status_bumps,
        'human_gates': human_gates,
        'pipeline_fields': {
            'type': pipeline_type,
            'stages': all_stage_names,
        },
        'complete_task_agent': complete_task_agent,
    }


# ═══════════════════════════════════════════════════════════════════════
# Legacy format parser (existing behavior preserved)
# ═══════════════════════════════════════════════════════════════════════

def _parse_legacy_yaml(data: dict) -> dict | None:
    """Parse legacy YAML block using PyYAML (flat transitions dict)."""
    if not isinstance(data, dict):
        return None

    first_agent = data.get('first_agent', 'architect')
    pipeline_fields = data.get('pipeline_fields', {})
    human_gates_list = data.get('human_gates', [])
    human_gates = set(human_gates_list) if human_gates_list else set()

    # Parse transitions
    raw_transitions = data.get('transitions', {})
    transitions = {}
    for stage, value in raw_transitions.items():
        if not isinstance(value, list) or len(value) < 3:
            continue
        next_stage = value[0]
        agent = value[1]
        message = value[2]

        session_mode = 'fresh'
        for item in value[3:]:
            if isinstance(item, dict):
                if 'session' in item:
                    session_mode = item['session']
                if 'gate' in item:
                    if item['gate'] == 'human':
                        human_gates.add(next_stage)
            elif isinstance(item, str):
                if item.startswith('session:'):
                    session_mode = item.split(':', 1)[1].strip()

        transitions[stage] = (next_stage, agent, message, session_mode)

    # Parse block_transitions if present
    raw_blocks = data.get('block_transitions', {})
    block_transitions = {}
    for stage, value in raw_blocks.items():
        if not isinstance(value, list) or len(value) < 3:
            continue
        block_transitions[stage] = (value[0], value[1], value[2])

    # Parse status_bumps
    status_bumps = data.get('status_bumps', {})
    start_status_bumps = data.get('start_status_bumps', {})

    return {
        'first_agent': first_agent,
        'transitions': transitions,
        'block_transitions': block_transitions,
        'status_bumps': status_bumps,
        'start_status_bumps': start_status_bumps,
        'human_gates': human_gates,
        'pipeline_fields': pipeline_fields,
    }


def _parse_manually(yaml_block: str) -> dict | None:
    """Fallback manual parser when PyYAML is not available.

    Handles the specific YAML format used in pipeline templates (legacy format).
    """
    transitions = {}
    block_transitions = {}
    status_bumps = {}
    start_status_bumps = {}
    human_gates = set()
    first_agent = 'architect'
    pipeline_fields = {}

    current_section = None

    for line in yaml_block.splitlines():
        stripped = line.strip()
        if stripped.startswith('#') or not stripped:
            continue

        # Top-level keys (not indented)
        if not line.startswith('  ') and ':' in stripped:
            if stripped.startswith('first_agent:'):
                first_agent = stripped.split(':', 1)[1].strip()
                current_section = None
                continue
            elif stripped == 'transitions:':
                current_section = 'transitions'
                continue
            elif stripped == 'block_transitions:':
                current_section = 'block_transitions'
                continue
            elif stripped == 'status_bumps:':
                current_section = 'status_bumps'
                continue
            elif stripped == 'start_status_bumps:':
                current_section = 'start_status_bumps'
                continue
            elif stripped == 'human_gates:':
                current_section = 'human_gates'
                continue
            elif stripped.startswith('pipeline_fields:'):
                current_section = 'pipeline_fields'
                continue
            else:
                current_section = None
                continue

        if current_section == 'transitions' or current_section == 'block_transitions':
            m = re.match(r'\s+(\w+):\s*\[(.+)\]', line)
            if m:
                stage = m.group(1)
                inner = m.group(2)
                parts = _parse_yaml_list(inner)
                if len(parts) >= 3:
                    next_stage = parts[0].strip()
                    agent = parts[1].strip()
                    message = parts[2].strip().strip('"').strip("'")

                    if current_section == 'block_transitions':
                        block_transitions[stage] = (next_stage, agent, message)
                    else:
                        session_mode = 'fresh'
                        for part in parts[3:]:
                            part = part.strip()
                            if part.startswith('session:'):
                                session_mode = part.split(':', 1)[1].strip()
                            elif part.startswith('gate:'):
                                gate_val = part.split(':', 1)[1].strip()
                                if gate_val == 'human':
                                    human_gates.add(next_stage)
                        transitions[stage] = (next_stage, agent, message, session_mode)

        elif current_section == 'status_bumps':
            m = re.match(r'\s+([\w]+):\s+(\S+)', line)
            if m:
                status_bumps[m.group(1)] = m.group(2)

        elif current_section == 'start_status_bumps':
            m = re.match(r'\s+([\w]+):\s+(\S+)', line)
            if m:
                start_status_bumps[m.group(1)] = m.group(2)

        elif current_section == 'human_gates':
            m = re.match(r'\s+-\s+(\w+)', line)
            if m:
                human_gates.add(m.group(1))

        elif current_section == 'pipeline_fields':
            if 'type:' in stripped:
                pipeline_fields['type'] = stripped.split(':', 1)[1].strip()
            elif 'stages:' in stripped:
                stages_match = re.search(r'\[([^\]]+)\]', stripped)
                if stages_match:
                    pipeline_fields['stages'] = [
                        s.strip() for s in stages_match.group(1).split(',')
                    ]

    if not transitions:
        return None

    return {
        'first_agent': first_agent,
        'transitions': transitions,
        'block_transitions': block_transitions,
        'status_bumps': status_bumps,
        'start_status_bumps': start_status_bumps,
        'human_gates': human_gates,
        'pipeline_fields': pipeline_fields,
    }


def _parse_phase_based_manual(yaml_block: str) -> dict | None:
    """Minimal fallback for phase-based format without PyYAML.

    This is a simplified parser — for full functionality, install PyYAML.
    """
    # Without PyYAML, we can't reliably parse nested YAML structures.
    # Return None and let the caller fall back to hardcoded constants.
    return None


def _parse_yaml_list(inner: str) -> list[str]:
    """Parse a YAML inline list, handling quoted strings with commas."""
    parts = []
    current = ''
    in_quotes = False
    quote_char = None

    for ch in inner:
        if in_quotes:
            if ch == quote_char:
                in_quotes = False
                current += ch
            else:
                current += ch
        elif ch in ('"', "'"):
            in_quotes = True
            quote_char = ch
            current += ch
        elif ch == ',':
            parts.append(current.strip())
            current = ''
        else:
            current += ch

    if current.strip():
        parts.append(current.strip())

    return parts


# ═══════════════════════════════════════════════════════════════════════
# Legacy stage name mapping for backward compatibility
# ═══════════════════════════════════════════════════════════════════════

# Maps old stage names (from existing pipeline files) to new phase-based names.
# Used by get_transitions_for_pipeline() in pipeline_update.py when a pipeline's
# pending_action uses an old name.
LEGACY_STAGE_MAP = {
    # Builder-first legacy → phase-based
    'builder_implement':           'p1_builder_implement',
    'builder_bugfix':              'p1_builder_bugfix',
    'critic_review':               'p1_critic_review',
    'phase1_complete':             'p1_complete',
    'builder_apply_blocks':        'p1_builder_fix_blocks',
    'phase2_architect_design':     'p2_architect_design',
    'phase2_builder_implement':    'p2_builder_implement',
    'phase2_builder_bugfix':       'p2_builder_bugfix',
    'phase2_critic_review':        'p2_critic_review',
    'phase2_complete':             'p2_complete',
    'phase2_builder_apply_blocks': 'p2_builder_fix_blocks',

    # Research legacy → phase-based
    'architect_design':                'p1_architect_design',
    'critic_design_review':            'p1_critic_design_review',
    'builder_implementation':          'p1_builder_implement',
    'builder_verification':            'p1_builder_verify',
    'critic_code_review':              'p1_critic_code_review',
    'local_experiment_running':        'p2_system_experiment_run',
    'local_experiment_complete':       'p2_system_experiment_complete',
    'local_analysis_architect':        'p2_architect_analysis',
    'local_analysis_critic_review':    'p2_critic_analysis_review',
    'local_analysis_builder':          'p2_builder_analysis_scripts',
    'local_analysis_code_review':      'p2_critic_analysis_code_review',
    'local_analysis_report_build':     'p2_system_report_build',
    'local_analysis_complete':         'p2_complete',
    'phase2_architect_design':         'p3_architect_design',
    'phase2_critic_design_review':     'p3_critic_design_review',
    'phase2_builder_implementation':   'p3_builder_implement',
    'phase2_builder_verification':     'p3_builder_verify',
    'phase2_critic_code_review':       'p3_critic_code_review',
    'phase3_architect_design':         'p4_architect_design',
    'phase3_critic_review':            'p4_critic_review',
    'phase3_builder_implementation':   'p4_builder_implement',
    'phase3_critic_code_review':       'p4_critic_code_review',
    'phase3_complete':                 'p4_complete',
}

# Reverse map: new → old (for backward compat messages)
REVERSE_LEGACY_MAP = {v: k for k, v in LEGACY_STAGE_MAP.items()}


def resolve_stage_name(stage: str, transitions: dict) -> str:
    """Resolve a stage name, trying the exact name first, then legacy mapping.

    Returns the resolved stage name that exists in the transitions dict.
    """
    if stage in transitions:
        return stage
    # Try legacy mapping
    mapped = LEGACY_STAGE_MAP.get(stage)
    if mapped and mapped in transitions:
        return mapped
    # Try reverse mapping (new name given, transitions use old names)
    rev_mapped = REVERSE_LEGACY_MAP.get(stage)
    if rev_mapped and rev_mapped in transitions:
        return rev_mapped
    return stage  # Return original, let caller handle the miss


def clear_cache():
    """Clear the template parse cache (useful for testing)."""
    _cache.clear()


if __name__ == '__main__':
    """Dump parsed templates for verification."""

    templates = ['builder-first', 'research']
    for name in templates:
        print(f"\n{'═' * 70}")
        print(f"  Template: {name}")
        print(f"{'═' * 70}")

        result = parse_template(name)
        if result is None:
            print(f"  ❌ Failed to parse or not found")
            continue

        print(f"\n  first_agent: {result['first_agent']}")
        print(f"  pipeline_fields: {result['pipeline_fields']}")
        print(f"  human_gates: {result['human_gates']}")

        print(f"\n  transitions ({len(result['transitions'])}):")
        for stage, val in sorted(result['transitions'].items()):
            next_stage, agent, msg, session_mode = val
            gate_marker = ' [HUMAN GATE]' if next_stage in result['human_gates'] else ''
            print(f"    {stage:45s} → {next_stage:35s} ({agent}, {session_mode}){gate_marker}")

        if result['block_transitions']:
            print(f"\n  block_transitions ({len(result['block_transitions'])}):")
            for stage, (next_stage, agent, msg) in sorted(result['block_transitions'].items()):
                print(f"    {stage:45s} → {next_stage:35s} ({agent})")

        print(f"\n  status_bumps ({len(result['status_bumps'])}):")
        for stage, status in sorted(result['status_bumps'].items()):
            print(f"    {stage:45s} → {status}")

        if result['start_status_bumps']:
            print(f"\n  start_status_bumps ({len(result['start_status_bumps'])}):")
            for stage, status in sorted(result['start_status_bumps'].items()):
                print(f"    {stage:45s} → {status}")

    print()
