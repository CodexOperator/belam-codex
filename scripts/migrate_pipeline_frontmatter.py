#!/usr/bin/env python3
"""
Add reactive fields to pipeline .md frontmatter:
  pending_action, current_phase, dispatch_claimed, last_updated, reset

Usage:
  python3 scripts/migrate_pipeline_frontmatter.py --dry-run
  python3 scripts/migrate_pipeline_frontmatter.py
"""

import json
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PIPELINES_DIR = WORKSPACE / 'pipelines'
BUILDS_DIR = WORKSPACE / 'pipeline_builds'

NEW_FIELDS = {
    'pending_action': '',
    'current_phase': '',
    'dispatch_claimed': 'false',
    'last_updated': '',
    'reset': 'false',
}


def find_state_json(version: str) -> dict:
    """Find and load _state.json for a pipeline version."""
    for candidate in [
        BUILDS_DIR / version / '_state.json',
        BUILDS_DIR / f'{version}_state.json',
    ]:
        if candidate.exists():
            try:
                return json.loads(candidate.read_text())
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def migrate_pipeline(path: Path, dry_run: bool) -> dict:
    text = path.read_text()
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, re.DOTALL)
    if not m:
        return {'file': path.name, 'status': 'skip', 'reason': 'no frontmatter'}

    fm_text = m.group(1)
    body = m.group(2)

    # Parse fields
    fields = {}
    order = []
    for line in fm_text.splitlines():
        kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if kv:
            fields[kv.group(1)] = kv.group(2).strip()
            order.append(kv.group(1))

    if fields.get('primitive') != 'pipeline':
        return {'file': path.name, 'status': 'skip', 'reason': 'not a pipeline'}

    # Try to get state from JSON
    version = fields.get('version', path.stem)
    state = find_state_json(version)

    added = []
    for key, default in NEW_FIELDS.items():
        if key not in fields:
            # Pull from state JSON if available
            value = state.get(key, default)
            if isinstance(value, bool):
                value = 'true' if value else 'false'
            fields[key] = str(value) if value else default
            order.append(key)
            added.append(key)

    if not added:
        return {'file': path.name, 'status': 'skip', 'reason': 'already migrated'}

    if dry_run:
        return {'file': path.name, 'status': 'dry-run', 'added': added}

    # Rebuild
    lines = ['---']
    for key in order:
        lines.append(f'{key}: {fields[key]}')
    lines.append('---')
    if body:
        lines.append(body)
    path.write_text('\n'.join(lines))

    return {'file': path.name, 'status': 'migrated', 'added': added}


def main():
    dry_run = '--dry-run' in sys.argv
    pipeline_files = sorted(PIPELINES_DIR.glob('*.md'))
    print(f"{'[DRY RUN] ' if dry_run else ''}Migrating {len(pipeline_files)} pipeline files...\n")

    migrated = 0
    for path in pipeline_files:
        result = migrate_pipeline(path, dry_run)
        if result['status'] in ('migrated', 'dry-run'):
            migrated += 1
            print(f"  + {result['file']}: {', '.join(result.get('added', []))}")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done: {migrated} migrated")


if __name__ == '__main__':
    main()
