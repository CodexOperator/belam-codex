#!/usr/bin/env python3
"""
Dynamic persona configuration loader.

Reads render_config and mode_access from persona .md files instead of
hardcoded PERSONA_CONFIGS in codex_engine.py. Supports per-template
overrides from pipeline template YAML.

Replaces the static dict at codex_engine.py ~line 1225 with:
    from persona_loader import load_persona_config, load_persona_access
    persona_cfg = load_persona_config(persona, template_name=active_template)
"""

import re
from pathlib import Path
from typing import Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

WORKSPACE = Path(__file__).resolve().parent.parent
PERSONAS_DIR = WORKSPACE / 'personas'
TEMPLATES_DIR = WORKSPACE / 'templates'

# Cache with mtime-based invalidation
_persona_cache: dict[str, tuple[float, dict]] = {}
_template_override_cache: dict[str, tuple[float, dict]] = {}

# Fallback configs if persona .md files don't have render_config yet
_FALLBACK_CONFIGS = {
    'architect': {
        'render_config': {'full': ['d', 'k', 't', 'p', 's', 'w'], 'summary': ['l']},
        'mode_access': [0, 1, 2],
    },
    'builder': {
        'render_config': {'full': ['t', 'c', 'p', 's', 'w', 'k'], 'summary': ['l', 'd']},
        'mode_access': [0, 1, 2, 3],
    },
    'critic': {
        'render_config': {'full': ['l', 'd', 't', 'p'], 'summary': ['k']},
        'mode_access': [0, 1],
    },
}


def _parse_persona_file(persona: str) -> dict:
    """Parse persona .md file, return frontmatter dict with caching."""
    path = PERSONAS_DIR / f'{persona}.md'
    if not path.exists():
        return _FALLBACK_CONFIGS.get(persona, {})

    mtime = path.stat().st_mtime
    cached = _persona_cache.get(persona)
    if cached and cached[0] == mtime:
        return cached[1]

    text = path.read_text()
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return _FALLBACK_CONFIGS.get(persona, {})

    fm_text = m.group(1)

    # Try YAML parsing first
    if HAS_YAML:
        try:
            data = yaml.safe_load(fm_text)
            if isinstance(data, dict):
                _persona_cache[persona] = (mtime, data)
                return data
        except yaml.YAMLError:
            pass

    # Manual parsing fallback
    data = _parse_frontmatter_manual(fm_text)
    _persona_cache[persona] = (mtime, data)
    return data


def _parse_frontmatter_manual(fm_text: str) -> dict:
    """Minimal YAML frontmatter parser for persona fields."""
    data = {}
    current_key = None
    current_dict = None

    for line in fm_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Top-level key: value
        m = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if m and not line.startswith(' '):
            key = m.group(1)
            value = m.group(2).strip()

            if value == '':
                # Start of nested dict
                current_key = key
                current_dict = {}
                data[key] = current_dict
            elif value.startswith('[') and value.endswith(']'):
                # Inline list
                items = [x.strip().strip('"').strip("'")
                         for x in value[1:-1].split(',') if x.strip()]
                # Try to convert to ints
                try:
                    items = [int(x) for x in items]
                except ValueError:
                    pass
                data[key] = items
            else:
                data[key] = value
                current_key = None
                current_dict = None
        elif current_dict is not None:
            # Nested key: value
            nm = re.match(r'^\s+(\w[\w_-]*)\s*:\s*(.*)', line)
            if nm:
                nkey = nm.group(1)
                nvalue = nm.group(2).strip()
                if nvalue.startswith('[') and nvalue.endswith(']'):
                    items = [x.strip().strip('"').strip("'")
                             for x in nvalue[1:-1].split(',') if x.strip()]
                    current_dict[nkey] = items
                else:
                    current_dict[nkey] = nvalue

    return data


def _parse_template_overrides(template_name: str) -> dict:
    """Parse persona_overrides from a template .md file."""
    if not template_name:
        return {}

    path = TEMPLATES_DIR / f'{template_name}-pipeline.md'
    if not path.exists():
        return {}

    mtime = path.stat().st_mtime
    cached = _template_override_cache.get(template_name)
    if cached and cached[0] == mtime:
        return cached[1]

    text = path.read_text()

    # Look for persona_overrides in the YAML block
    m = re.search(
        r'## Stage Transitions.*?```yaml\s*\n(.*?)```',
        text, re.DOTALL,
    )
    if not m:
        _template_override_cache[template_name] = (mtime, {})
        return {}

    yaml_block = m.group(1)

    if HAS_YAML:
        try:
            data = yaml.safe_load(yaml_block)
            overrides = data.get('persona_overrides', {}) if isinstance(data, dict) else {}
            _template_override_cache[template_name] = (mtime, overrides)
            return overrides
        except yaml.YAMLError:
            pass

    _template_override_cache[template_name] = (mtime, {})
    return {}


def load_persona_config(persona: str, template_name: str = None) -> dict[str, str]:
    """Load render config for a persona.

    Returns dict mapping namespace prefix to render mode:
        {'t': 'full', 'l': 'summary', 'p': 'tree', ...}

    Resolution order:
        1. Template persona_overrides (if template_name given)
        2. Persona .md render_config
        3. Fallback hardcoded config

    Args:
        persona: Persona role name ('architect', 'builder', 'critic')
        template_name: Optional template slug for per-template overrides
    """
    persona_data = _parse_persona_file(persona)

    # Get base render_config
    render_config = persona_data.get('render_config', {})

    # If no render_config in .md, use fallback
    if not render_config:
        fallback = _FALLBACK_CONFIGS.get(persona, {})
        render_config = fallback.get('render_config', {})

    # Apply template overrides
    if template_name:
        overrides = _parse_template_overrides(template_name)
        persona_override = overrides.get(persona, {})
        if persona_override:
            # Override replaces the entire render_config for this persona
            render_config = persona_override

    # Convert from {full: [t,c,p], summary: [l], tree: [p]} format
    # to {t: 'full', c: 'full', p: 'tree', l: 'summary'} format
    result = {}
    for mode in ('tree', 'full', 'summary'):  # tree wins over full if both
        prefixes = render_config.get(mode, [])
        if isinstance(prefixes, list):
            for prefix in prefixes:
                result[prefix] = mode

    return result


def load_persona_access(persona: str) -> set[int]:
    """Load e-mode access set from persona .md.

    Returns set of allowed mode numbers (e.g., {0, 1, 2}).
    """
    persona_data = _parse_persona_file(persona)

    mode_access = persona_data.get('mode_access', None)

    if mode_access is None:
        fallback = _FALLBACK_CONFIGS.get(persona, {})
        mode_access = fallback.get('mode_access', [0, 1, 2, 3])

    if isinstance(mode_access, list):
        try:
            return {int(x) for x in mode_access}
        except (ValueError, TypeError):
            pass

    return {0, 1, 2, 3}


def clear_cache():
    """Clear all caches (for testing)."""
    _persona_cache.clear()
    _template_override_cache.clear()


if __name__ == '__main__':
    """Dump persona configs for verification."""
    for persona in ('architect', 'builder', 'critic'):
        print(f"\n{'=' * 50}")
        print(f"  Persona: {persona}")
        print(f"{'=' * 50}")

        config = load_persona_config(persona)
        access = load_persona_access(persona)

        print(f"  Render config: {config}")
        print(f"  Mode access: {sorted(access)}")

        # Test with template overrides
        for tmpl in ('builder-first', 'research'):
            override_config = load_persona_config(persona, template_name=tmpl)
            if override_config != config:
                print(f"  Override ({tmpl}): {override_config}")

    print()
