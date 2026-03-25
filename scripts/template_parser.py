#!/usr/bin/env python3
"""
Parse pipeline template YAML from markdown files.

Templates live in templates/{name}-pipeline.md and contain a fenced YAML block
under `## Stage Transitions` with transitions, status_bumps, start_status_bumps,
human_gates, and pipeline_fields.

Returns structured dicts matching the shape of the hardcoded constants in
pipeline_update.py:
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

    if HAS_YAML:
        result = _parse_with_yaml(yaml_block)
    else:
        result = _parse_manually(yaml_block)

    _cache[template_name] = result
    return result


def _parse_with_yaml(yaml_block: str) -> dict | None:
    """Parse YAML block using PyYAML."""
    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError:
        return _parse_manually(yaml_block)

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

        # Handle remaining elements: gate: human, session: mode
        session_mode = 'fresh'  # default
        is_gate = False
        for item in value[3:]:
            if isinstance(item, dict):
                if 'session' in item:
                    session_mode = item['session']
                if 'gate' in item:
                    if item['gate'] == 'human':
                        is_gate = True
                        human_gates.add(next_stage)
            elif isinstance(item, str):
                # Handle "session: fresh" parsed as string in some YAML configs
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

    Handles the specific YAML format used in pipeline templates.
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
            # Parse: stage_name: [next_stage, agent, "message", session: mode]
            # Also handles: gate: human
            m = re.match(
                r'\s+(\w+):\s*\[(.+)\]',
                line
            )
            if m:
                stage = m.group(1)
                inner = m.group(2)

                # Parse the list elements carefully (message may contain commas)
                parts = _parse_yaml_list(inner)
                if len(parts) >= 3:
                    next_stage = parts[0].strip()
                    agent = parts[1].strip()
                    message = parts[2].strip().strip('"').strip("'")

                    if current_section == 'block_transitions':
                        block_transitions[stage] = (next_stage, agent, message)
                    else:
                        # Extract session mode and gate from remaining parts
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
                # Parse inline list: stages: [a, b, c]
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


def _parse_yaml_list(inner: str) -> list[str]:
    """Parse a YAML inline list, handling quoted strings with commas.

    E.g.: 'builder_implement, builder, "Task spec ready, go.", session: fresh'
    → ['builder_implement', 'builder', 'Task spec ready, go.', 'session: fresh']
    """
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


def clear_cache():
    """Clear the template parse cache (useful for testing)."""
    _cache.clear()


if __name__ == '__main__':
    """Dump parsed templates for verification."""
    import json as _json

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
        for stage, (next_stage, agent, msg, session_mode) in sorted(result['transitions'].items()):
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
