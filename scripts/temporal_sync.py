#!/usr/bin/env python3
"""Reconcile filesystem state → SpacetimeDB for the V2 temporal overlay.

Reads all pipeline _state.json files and upserts into SpacetimeDB.
Idempotent — safe to run repeatedly. Designed for sweep integration.

FLAG-6 clarification: This sync covers pipeline_state table ONLY.
- state_transition entries are temporal-layer-native (no filesystem equivalent)
- handoff entries partially overlap with pipelines/handoffs/*.json but
  are temporal-layer-native for delivery tracking
- agent_context is backed up separately via temporal_overlay.export_context()

Usage:
    python3 scripts/temporal_sync.py                    # Full sync
    python3 scripts/temporal_sync.py --pipeline p3      # Single pipeline
    python3 scripts/temporal_sync.py --dry-run           # Preview only
    python3 scripts/temporal_sync.py --export-contexts   # Also backup agent contexts
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from temporal_overlay import TemporalOverlay


def main():
    parser = argparse.ArgumentParser(
        description='Reconcile filesystem pipeline state → SpacetimeDB'
    )
    parser.add_argument('--pipeline', '-p', help='Sync a single pipeline version')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('--export-contexts', action='store_true',
                        help='Also export agent contexts to filesystem (FLAG-3 backup)')
    parser.add_argument('--workspace', '-w',
                        default=str(Path(__file__).parent.parent),
                        help='Workspace root directory')
    parser.add_argument('--db-name', default='belam-orchestration',
                        help='SpacetimeDB database name')
    parser.add_argument('--verbose', '-v', action='store_true')

    args = parser.parse_args()
    workspace = Path(args.workspace)
    overlay = TemporalOverlay(workspace=workspace, db_name=args.db_name)

    if not overlay.available:
        print("⚠ SpacetimeDB unavailable — cannot sync")
        print(f"  Binary: {overlay.spacetime_bin}")
        print(f"  Database: {overlay.db_name}")
        print("\n  Ensure SpacetimeDB is running:")
        print("    spacetime start")
        print(f"    spacetime publish {overlay.db_name} scripts/temporal_schema/")
        sys.exit(1)

    pipeline_dir = (
        workspace / 'machinelearning' / 'snn_applied_finance' /
        'research' / 'pipeline_builds'
    )

    if not pipeline_dir.is_dir():
        print(f"Pipeline directory not found: {pipeline_dir}")
        sys.exit(1)

    # Collect state files
    state_files = sorted(pipeline_dir.glob('*_state.json'))
    if args.pipeline:
        state_files = [f for f in state_files if args.pipeline in f.stem]

    if not state_files:
        print(f"No state files found" + (f" matching '{args.pipeline}'" if args.pipeline else ""))
        sys.exit(0)

    print(f"📊 Temporal Sync: {len(state_files)} pipeline(s)")
    print(f"   Database: {overlay.db_name}")
    print(f"   Mode: {'dry-run' if args.dry_run else 'live'}")
    print()

    stats = {'synced': 0, 'errors': 0, 'skipped': 0}

    for state_file in state_files:
        try:
            state = json.loads(state_file.read_text())
            version = state.get('version', '')
            if not version:
                if args.verbose:
                    print(f"  ⏭ {state_file.name}: no version field")
                stats['skipped'] += 1
                continue

            status = state.get('status', 'unknown')
            current_stage = state.get('pending_action', '')
            current_agent = state.get('current_agent', '')

            if args.verbose or args.dry_run:
                print(f"  {'🔍' if args.dry_run else '📤'} {version}: "
                      f"status={status}, stage={current_stage}, agent={current_agent}")

            if not args.dry_run:
                success = overlay.upsert_pipeline(
                    version=version,
                    status=status,
                    current_stage=current_stage,
                    current_agent=current_agent,
                    tags=json.dumps(state.get('tags', [])),
                    priority=state.get('priority', 'medium'),
                )
                if success:
                    stats['synced'] += 1
                else:
                    print(f"  ❌ {version}: upsert failed")
                    stats['errors'] += 1
            else:
                stats['synced'] += 1  # Would have synced

        except (json.JSONDecodeError, OSError) as e:
            print(f"  ❌ {state_file.name}: {e}")
            stats['errors'] += 1

    print(f"\n{'Preview' if args.dry_run else 'Results'}: "
          f"{stats['synced']} synced, {stats['errors']} errors, {stats['skipped']} skipped")

    # Optional: export agent contexts to filesystem (FLAG-3)
    if args.export_contexts and not args.dry_run:
        print("\n📦 Exporting agent contexts to filesystem...")
        count = overlay.export_all_contexts()
        print(f"   Exported {count} pipeline context(s)")


if __name__ == '__main__':
    main()
