#!/usr/bin/env python3
"""
One-time migration: add pipeline_template, current_stage, pipeline_status,
launch_mode fields to all task .md frontmatter.

Usage:
  python3 scripts/migrate_task_schema_v2.py --dry-run   # preview changes
  python3 scripts/migrate_task_schema_v2.py              # apply changes
"""

import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
TASKS_DIR = WORKSPACE / 'tasks'

NEW_FIELDS = {
    'pipeline_template': '',
    'current_stage': '',
    'pipeline_status': '',
    'launch_mode': 'queued',
}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text.
    Returns (fields_dict, body_text).
    """
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, re.DOTALL)
    if not m:
        return {}, text

    fm_text = m.group(1)
    body = m.group(2)
    fields = {}
    field_order = []

    for line in fm_text.splitlines():
        kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if kv:
            key = kv.group(1)
            value = kv.group(2).strip()
            fields[key] = value
            field_order.append(key)

    fields['_order'] = field_order
    return fields, body


def rebuild_frontmatter(fields: dict, body: str) -> str:
    """Rebuild .md file from fields dict and body text."""
    order = fields.get('_order', [])
    lines = ['---']
    for key in order:
        if key.startswith('_'):
            continue
        lines.append(f'{key}: {fields[key]}')
    lines.append('---')
    if body:
        lines.append(body)
    return '\n'.join(lines)


def migrate_task(path: Path, dry_run: bool) -> dict:
    """Migrate a single task file. Returns summary dict."""
    text = path.read_text()
    fields, body = parse_frontmatter(text)

    if not fields:
        return {'file': path.name, 'status': 'skip', 'reason': 'no frontmatter'}

    if fields.get('primitive') != 'task':
        return {'file': path.name, 'status': 'skip', 'reason': 'not a task primitive'}

    added = []
    order = fields.get('_order', [])

    for key, default in NEW_FIELDS.items():
        if key not in fields:
            fields[key] = default
            order.append(key)
            added.append(key)

    # Propagate existing 'pipeline' field to pipeline_status if set
    if fields.get('pipeline') and not fields.get('pipeline_status'):
        fields['pipeline_status'] = 'in_pipeline'
        if 'pipeline_status' not in added:
            added.append('pipeline_status (propagated)')

    if not added:
        return {'file': path.name, 'status': 'skip', 'reason': 'already migrated'}

    fields['_order'] = order
    new_text = rebuild_frontmatter(fields, body)

    if dry_run:
        return {'file': path.name, 'status': 'dry-run', 'added': added}

    path.write_text(new_text)
    return {'file': path.name, 'status': 'migrated', 'added': added}


def main():
    dry_run = '--dry-run' in sys.argv

    if not TASKS_DIR.is_dir():
        print(f"Tasks directory not found: {TASKS_DIR}")
        sys.exit(1)

    task_files = sorted(TASKS_DIR.glob('*.md'))
    print(f"{'[DRY RUN] ' if dry_run else ''}Migrating {len(task_files)} task files...\n")

    migrated = 0
    skipped = 0

    for path in task_files:
        result = migrate_task(path, dry_run)
        status = result['status']

        if status in ('migrated', 'dry-run'):
            migrated += 1
            added_str = ', '.join(result.get('added', []))
            print(f"  + {result['file']}: {added_str}")
        else:
            skipped += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done: {migrated} migrated, {skipped} skipped")


if __name__ == '__main__':
    main()
