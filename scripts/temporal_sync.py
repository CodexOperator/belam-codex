#!/usr/bin/env python3
"""
temporal_sync.py — Filesystem → Temporal DB reconciliation

Reads pipeline _state.json files from the filesystem and upserts them into the
temporal SQLite database. Ensures the temporal overlay stays consistent with
the filesystem source of truth.

Reconciliation scope (Critic FLAG-6 — documented explicitly):
  - pipeline_state: FULL SYNC — filesystem is source of truth
  - state_transition: NOT SYNCED — these are created by the temporal overlay
    during live operation. Historical transitions from before temporal was
    enabled are NOT retroactively created (would require git log parsing).
  - handoff: NOT SYNCED — created live by temporal overlay
  - agent_context: NOT SYNCED — SQLite-native data (see FLAG-3 resolution:
    since SQLite IS on the filesystem, this is inherently backed up)
  - agent_presence: NOT SYNCED — ephemeral heartbeat data

Designed for periodic execution (e.g., every 15min as part of sweep).
Idempotent — safe to run repeatedly.

Usage:
    python3 scripts/temporal_sync.py                    # Full sync
    python3 scripts/temporal_sync.py --pipeline <ver>   # Single pipeline
    python3 scripts/temporal_sync.py --dry-run           # Preview only
    python3 scripts/temporal_sync.py --json              # JSON output
    python3 scripts/temporal_sync.py --export-context    # Export agent_context to JSON files (FLAG-3 backup)
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── Paths ───────────────────────────────────────────────────────────────────────

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
BUILDS_DIR = WORKSPACE / 'pipeline_builds'
RESEARCH_BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
PIPELINES_DIR = WORKSPACE / 'pipelines'

# Ensure scripts dir is on path for imports
sys.path.insert(0, str(WORKSPACE / 'scripts'))


def discover_pipeline_states() -> list:
    """Find all *_state.json files in the builds directory."""
    states = []
    if not BUILDS_DIR.exists():
        return states

    for f in sorted(BUILDS_DIR.glob('*_state.json')):
        try:
            with open(f) as fh:
                data = json.load(fh)
                data['_source_file'] = str(f)
                states.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[sync] Warning: Could not read {f}: {e}", file=sys.stderr)
    return states


def parse_pipeline_frontmatter(pipeline_md: Path) -> dict:
    """Extract YAML frontmatter from a pipeline markdown file."""
    if not pipeline_md.exists():
        return {}
    try:
        content = pipeline_md.read_text()
        if content.startswith('---'):
            end = content.find('---', 3)
            if end > 0:
                # Simple YAML parsing (key: value lines)
                frontmatter = {}
                for line in content[3:end].strip().split('\n'):
                    if ':' in line:
                        key, _, value = line.partition(':')
                        key = key.strip()
                        value = value.strip()
                        # Handle YAML arrays [a, b, c]
                        if value.startswith('[') and value.endswith(']'):
                            value = [v.strip().strip("'\"")
                                     for v in value[1:-1].split(',')]
                        frontmatter[key] = value
                return frontmatter
    except IOError:
        pass
    return {}


def _infer_agent(stage: str) -> str:
    """Infer current agent from stage name (FLAG-3 fix).

    Maps pending_action/current_stage to the agent who owns it.
    """
    if not stage:
        return ''
    stage_lower = stage.lower()
    if 'architect' in stage_lower:
        return 'architect'
    elif 'critic' in stage_lower:
        return 'critic'
    elif 'builder' in stage_lower:
        return 'builder'
    elif stage_lower in ('phase1_complete', 'phase2_complete'):
        return 'architect'  # Architect owns completion stages
    return ''


def sync_pipeline_state(state_data: dict, overlay, dry_run: bool = False) -> dict:
    """Sync a single pipeline's state to the temporal DB.

    Returns: {'version': str, 'action': 'created'|'updated'|'unchanged'|'error', ...}
    """
    version = state_data.get('version', state_data.get('pipeline', ''))
    if not version:
        return {'version': '?', 'action': 'error', 'reason': 'No version field'}

    # Extract current state from JSON
    # FLAG-3 fix: pending_action → current_stage when current_stage is empty.
    # State JSON may use pending_action as the canonical "what stage is next" field.
    current_stage = state_data.get('current_stage', '') or state_data.get('pending_action', '')
    current_agent = state_data.get('current_agent', '') or _infer_agent(current_stage)
    status = state_data.get('status', 'unknown')

    # Also check the pipeline markdown for additional metadata
    pipeline_md = PIPELINES_DIR / f'{version}.md'
    frontmatter = parse_pipeline_frontmatter(pipeline_md)
    if frontmatter.get('status'):
        status = frontmatter['status']
    tags = json.dumps(frontmatter.get('tags', []))
    priority = frontmatter.get('priority', 'medium')

    # Check current temporal state
    try:
        conn = overlay._get_conn()
        existing = conn.execute(
            "SELECT * FROM pipeline_state WHERE version = ?",
            (version,)
        ).fetchone()
    except Exception as e:
        return {'version': version, 'action': 'error', 'reason': str(e)}

    result = {'version': version, 'source': state_data.get('_source_file', '')}

    if dry_run:
        if existing:
            # Check if anything changed
            if (existing['current_stage'] == current_stage and
                    existing['current_agent'] == current_agent and
                    existing['status'] == status):
                result['action'] = 'unchanged'
            else:
                result['action'] = 'would_update'
                result['changes'] = {
                    'stage': f"{existing['current_stage']} → {current_stage}",
                    'agent': f"{existing['current_agent']} → {current_agent}",
                    'status': f"{existing['status']} → {status}",
                }
        else:
            result['action'] = 'would_create'
        return result

    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    try:
        if existing:
            if (existing['current_stage'] == current_stage and
                    existing['current_agent'] == current_agent and
                    existing['status'] == status):
                result['action'] = 'unchanged'
            else:
                conn.execute(
                    "UPDATE pipeline_state SET "
                    "status = ?, current_stage = ?, current_agent = ?, "
                    "tags = ?, priority = ?, updated_at = ? "
                    "WHERE version = ?",
                    (status, current_stage, current_agent,
                     tags, priority, now, version)
                )
                conn.commit()
                result['action'] = 'updated'
        else:
            # Get creation time from state JSON or use now
            created = state_data.get('created_at', now)
            conn.execute(
                "INSERT INTO pipeline_state "
                "(version, status, current_stage, current_agent, "
                "tags, priority, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (version, status, current_stage, current_agent,
                 tags, priority, created, now)
            )
            conn.commit()
            result['action'] = 'created'
    except Exception as e:
        result['action'] = 'error'
        result['reason'] = str(e)

    return result


def export_agent_contexts(overlay, output_dir: Path = None) -> list:
    """Export all agent_context rows to JSON files (FLAG-3 backup).

    Writes to pipeline_builds/{version}_agent_context.json.
    """
    if not overlay.available:
        return []

    output_dir = output_dir or BUILDS_DIR
    conn = overlay._get_conn()
    rows = conn.execute("SELECT * FROM agent_context").fetchall()

    exported = []
    # Group by version
    by_version = {}
    for row in rows:
        row_dict = dict(row)
        version = row_dict['version']
        if version not in by_version:
            by_version[version] = {}
        by_version[version][row_dict['agent']] = {
            'accumulated_context': json.loads(row_dict.get('accumulated_context', '{}')),
            'session_count': row_dict.get('session_count', 0),
            'total_tokens_used': row_dict.get('total_tokens_used', 0),
            'last_session_id': row_dict.get('last_session_id', ''),
            'last_active_at': row_dict.get('last_active_at', ''),
            'created_at': row_dict.get('created_at', ''),
        }

    for version, agents in by_version.items():
        output_file = output_dir / f'{version}_agent_context.json'
        try:
            with open(output_file, 'w') as f:
                json.dump({
                    'version': version,
                    'agents': agents,
                    'exported_at': datetime.now(timezone.utc).isoformat(),
                }, f, indent=2)
            exported.append(str(output_file))
        except IOError as e:
            print(f"[sync] Error exporting context for {version}: {e}",
                  file=sys.stderr)

    return exported


def run_sync(pipeline_filter: str = None, dry_run: bool = False,
             json_output: bool = False) -> dict:
    """Run the full sync process."""
    from temporal_overlay import TemporalOverlay

    overlay = TemporalOverlay()
    if not overlay.available:
        return {'ok': False, 'error': 'Temporal DB not available'}

    states = discover_pipeline_states()
    if pipeline_filter:
        states = [s for s in states
                  if s.get('version', s.get('pipeline', '')) == pipeline_filter]

    results = []
    for state_data in states:
        result = sync_pipeline_state(state_data, overlay, dry_run=dry_run)
        results.append(result)

    summary = {
        'ok': True,
        'total': len(results),
        'created': sum(1 for r in results if r['action'] == 'created'),
        'updated': sum(1 for r in results if r['action'] == 'updated'),
        'unchanged': sum(1 for r in results if r['action'] == 'unchanged'),
        'errors': sum(1 for r in results if r['action'] == 'error'),
        'dry_run': dry_run,
        'results': results,
        'synced_at': datetime.now(timezone.utc).isoformat(),
    }

    overlay.close()
    return summary


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Temporal DB sync')
    parser.add_argument('--pipeline', '-p', help='Sync a specific pipeline only')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Preview changes without writing')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--export-context', action='store_true',
                        help='Export agent_context to JSON files (FLAG-3 backup)')
    args = parser.parse_args()

    if args.export_context:
        from temporal_overlay import TemporalOverlay
        overlay = TemporalOverlay()
        if not overlay.available:
            print("❌ Temporal DB not available", file=sys.stderr)
            sys.exit(1)
        exported = export_agent_contexts(overlay)
        if args.json:
            print(json.dumps({'exported': exported}))
        else:
            if exported:
                print(f"✅ Exported agent context to {len(exported)} files:")
                for f in exported:
                    print(f"  {f}")
            else:
                print("No agent context to export")
        overlay.close()
        sys.exit(0)

    summary = run_sync(
        pipeline_filter=args.pipeline,
        dry_run=args.dry_run,
        json_output=args.json,
    )

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        if not summary.get('ok'):
            print(f"❌ Sync failed: {summary.get('error', 'unknown')}")
            sys.exit(1)

        prefix = '[DRY RUN] ' if args.dry_run else ''
        print(f"{prefix}✅ Temporal sync complete:")
        print(f"  Total pipelines: {summary['total']}")
        if args.dry_run:
            would_create = sum(1 for r in summary['results']
                               if r['action'] == 'would_create')
            would_update = sum(1 for r in summary['results']
                               if r['action'] == 'would_update')
            print(f"  Would create: {would_create}")
            print(f"  Would update: {would_update}")
        else:
            print(f"  Created: {summary['created']}")
            print(f"  Updated: {summary['updated']}")
        print(f"  Unchanged: {summary['unchanged']}")
        if summary['errors']:
            print(f"  ⚠️ Errors: {summary['errors']}")
            for r in summary['results']:
                if r['action'] == 'error':
                    print(f"    {r['version']}: {r.get('reason', '?')}")
