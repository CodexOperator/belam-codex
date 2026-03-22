#!/usr/bin/env python3
"""
dependency_graph.py — Cross-pipeline dependency tracking and cascading resolution

Part of Orchestration V3: Real-Time Monitoring Suite.

Provides:
  - register_dependency(): explicit dep registration (FLAG-5: no task-name scraping)
  - resolve_downstream_deps(): cascading resolution with cycle detection (FLAG-1)
  - check_deps_satisfied(): upstream dep check for a pipeline
  - render_dependency_graph(): text-based graph rendering
  - preview_revert_deps(): dry-run showing what deps would be affected by a revert

Integration: Called from orchestration_engine._post_state_change() on phase completion
or archive. Uses graceful degradation — failures are non-fatal.

Usage:
    python3 scripts/dependency_graph.py list                    # show dep graph
    python3 scripts/dependency_graph.py register <src> <tgt>    # register dep
    python3 scripts/dependency_graph.py check <version>         # check deps met
    python3 scripts/dependency_graph.py resolve <version>       # resolve downstream
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
DEFAULT_DB_PATH = WORKSPACE / 'data' / 'temporal.db'


# ─── Dependency CRUD ─────────────────────────────────────────────────────────────

def _get_conn(db_path: Path = DEFAULT_DB_PATH) -> Optional[sqlite3.Connection]:
    """Get DB connection with graceful degradation."""
    try:
        if not db_path.exists():
            return None
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    except Exception:
        return None


def register_dependency(source_version: str, target_version: str,
                        dep_type: str = 'completion',
                        db_path: Path = DEFAULT_DB_PATH) -> bool:
    """Register a pipeline dependency (FLAG-5: explicit, not scraped).

    Args:
        source_version: Upstream pipeline that must complete first
        target_version: Downstream pipeline that depends on source
        dep_type: 'completion' | 'archive' | 'gate'

    Returns True on success.
    """
    conn = _get_conn(db_path)
    if not conn:
        return False
    try:
        # Check for duplicate
        existing = conn.execute(
            "SELECT id FROM pipeline_dependency "
            "WHERE source_version = ? AND target_version = ? AND dep_type = ?",
            (source_version, target_version, dep_type)
        ).fetchone()
        if existing:
            return True  # Already registered

        conn.execute(
            "INSERT INTO pipeline_dependency (source_version, target_version, dep_type) "
            "VALUES (?, ?, ?)",
            (source_version, target_version, dep_type)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[dep_graph] register error: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()


def remove_dependency(source_version: str, target_version: str,
                      db_path: Path = DEFAULT_DB_PATH) -> bool:
    """Remove a pipeline dependency."""
    conn = _get_conn(db_path)
    if not conn:
        return False
    try:
        conn.execute(
            "DELETE FROM pipeline_dependency "
            "WHERE source_version = ? AND target_version = ?",
            (source_version, target_version)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[dep_graph] remove error: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()


def get_all_deps(db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Get all registered dependencies."""
    conn = _get_conn(db_path)
    if not conn:
        return []
    try:
        rows = conn.execute(
            "SELECT * FROM pipeline_dependency ORDER BY created_at"
        ).fetchall()
        return [dict(row) for row in rows]
    except Exception:
        return []
    finally:
        conn.close()


# ─── Dependency Resolution (FLAG-1: cycle detection via _visited set) ────────────

def resolve_downstream_deps(version: str, action: str = 'complete',
                            db_path: Path = DEFAULT_DB_PATH,
                            _visited: set = None) -> list[dict]:
    """Resolve downstream deps when a pipeline completes or archives.

    FLAG-1 (MED) addressed: _visited set parameter prevents cycles.
    If version is already in _visited, we skip it (log warning).

    Args:
        version: Pipeline that just completed/archived
        action: 'complete' or 'archive'
        db_path: Path to temporal DB
        _visited: Set of already-processed versions (cycle detection)

    Returns list of resolution dicts:
        [{'target': str, 'dep_satisfied': str, 'all_deps_met': bool, 'eligible': bool}]
    """
    # FLAG-1: Initialize visited set on first call, detect cycles
    if _visited is None:
        _visited = set()
    if version in _visited:
        print(f"[dep_graph] WARNING: cycle detected — {version} already visited, "
              f"skipping", file=sys.stderr)
        return []
    _visited.add(version)

    conn = _get_conn(db_path)
    if not conn:
        return []

    results = []
    try:
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        # Find downstream deps where this version is the source
        downstream = conn.execute(
            "SELECT id, target_version, dep_type, status "
            "FROM pipeline_dependency "
            "WHERE source_version = ? AND status = 'pending'",
            (version,)
        ).fetchall()

        for dep in downstream:
            target = dep['target_version']
            dep_type = dep['dep_type']

            # Check if this action satisfies the dep type
            satisfies = False
            if dep_type == 'completion' and action in ('complete', 'archive'):
                satisfies = True
            elif dep_type == 'archive' and action == 'archive':
                satisfies = True
            elif dep_type == 'gate':
                satisfies = True  # Gates resolve on any completion

            if not satisfies:
                continue

            # Mark this dep as satisfied
            conn.execute(
                "UPDATE pipeline_dependency SET status = 'satisfied', satisfied_at = ? "
                "WHERE id = ?",
                (now, dep['id'])
            )

            # Check if ALL deps for the target are now satisfied
            remaining = conn.execute(
                "SELECT COUNT(*) as cnt FROM pipeline_dependency "
                "WHERE target_version = ? AND status = 'pending'",
                (target,)
            ).fetchone()
            all_met = remaining['cnt'] == 0

            # Log resolution event as a state_transition (visible in .v2 live diff)
            try:
                conn.execute(
                    "INSERT INTO state_transition "
                    "(version, from_stage, to_stage, agent, action, notes) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (target, 'dep_pending', 'dep_satisfied', 'system', 'dep_resolved',
                     f"Dependency satisfied: {version} ({dep_type}). "
                     f"All deps met: {all_met}")
                )
            except Exception:
                pass  # state_transition logging is best-effort

            results.append({
                'target': target,
                'dep_satisfied': version,
                'dep_type': dep_type,
                'all_deps_met': all_met,
                'eligible': all_met,
            })

        conn.commit()
        return results

    except Exception as e:
        print(f"[dep_graph] resolve error: {e}", file=sys.stderr)
        return []
    finally:
        conn.close()


def check_deps_satisfied(version: str,
                         db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Check if all upstream deps for a pipeline are satisfied.

    Returns: {'all_met': bool, 'deps': [...], 'blocking': [...]}
    """
    conn = _get_conn(db_path)
    if not conn:
        return {'all_met': True, 'deps': [], 'blocking': []}
    try:
        rows = conn.execute(
            "SELECT source_version, dep_type, status, satisfied_at "
            "FROM pipeline_dependency WHERE target_version = ?",
            (version,)
        ).fetchall()
        deps = [dict(row) for row in rows]
        blocking = [d for d in deps if d['status'] == 'pending']
        return {
            'all_met': len(blocking) == 0,
            'deps': deps,
            'blocking': blocking,
        }
    except Exception:
        return {'all_met': True, 'deps': [], 'blocking': []}
    finally:
        conn.close()


# ─── Graph Rendering ─────────────────────────────────────────────────────────────

def render_dependency_graph(db_path: Path = DEFAULT_DB_PATH) -> str:
    """Render cross-pipeline dependency graph as text."""
    deps = get_all_deps(db_path)
    if not deps:
        return "No pipeline dependencies registered."

    lines = ["Pipeline Dependencies", "─" * 50]
    status_icons = {
        'satisfied': '✅',
        'pending': '⏳',
        'blocked': '🚫',
    }

    for dep in deps:
        src = dep['source_version']
        tgt = dep['target_version']
        status = dep.get('status', 'pending')
        icon = status_icons.get(status, '❓')
        dep_type = dep.get('dep_type', 'completion')
        suffix = f" [{dep_type}]" if dep_type != 'completion' else ''
        lines.append(f"  {src} ──{icon}──→ {tgt}{suffix}")

    lines.append("")
    lines.append("  Legend: ✅ satisfied  ⏳ pending  🚫 blocked")
    return '\n'.join(lines)


def compute_f_r_causal_chain(f_labels: list[str],
                             db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Given F-labels from a revert, compute full causal chain.

    Phase 2: Full implementation replacing Phase 1 stub.
    1. Parses F-labels into structured (coord, field, old_value, new_value)
    2. Queries render engine for corresponding R-labels
    3. Walks dependency graph for cascading effects
    4. Checks handoff table for orphaned handoffs

    Returns:
        f_labels: original F-labels
        r_labels: corresponding render-side changes
        cascading_deps: [{target, was_satisfied_by, now_suspect}]
        orphaned_handoffs: [{handoff_id, target_agent, completed_stage}]
        impact_summary: human-readable one-liner
    """
    # 1. Parse F-labels into structured changes
    parsed_changes = []
    for fl in f_labels:
        change = {'raw': fl, 'coord': None, 'field': None,
                  'old_value': None, 'new_value': None}
        # Parse "F{N} Δ {coord}.{field} {old} → {new}"
        match = re.match(r'F\d+\s+Δ\s+(\S+)\.(\S+)\s+(\S+)\s+→\s+(\S+)', fl)
        if match:
            change['coord'] = match.group(1)
            change['field'] = match.group(2)
            change['old_value'] = match.group(3)
            change['new_value'] = match.group(4)
        elif '.stage' in fl:
            parts = fl.split('.stage')
            change['coord'] = parts[0].split()[-1] if parts else None
            change['field'] = 'stage'
        elif '.agent' in fl:
            parts = fl.split('.agent')
            change['coord'] = parts[0].split()[-1] if parts else None
            change['field'] = 'agent'
        elif '.lock' in fl:
            parts = fl.split('.lock')
            change['coord'] = parts[0].split()[-1] if parts else None
            change['field'] = 'lock'
        parsed_changes.append(change)

    # 2. Query render engine for R-labels
    r_labels = []
    try:
        from monitoring_views import RenderClient
        rc = RenderClient()
        if rc.is_available():
            # Get recent diffs (last 5 min window for correlation)
            import time
            diffs = rc.get_diffs_structured(time.time() - 300)
            for d in diffs:
                d_coord = d.get('coord', '')
                # Correlate: R-label matches if same coordinate appears in F-labels
                for pc in parsed_changes:
                    if pc.get('coord') and pc['coord'] in d_coord:
                        r_labels.append(f"R {d.get('raw', d_coord)}")
                        break
        else:
            # Fallback: generate predicted R-labels from F-label structure
            for pc in parsed_changes:
                coord = pc.get('coord', '?')
                field = pc.get('field', '?')
                if field == 'stage':
                    r_labels.append(f"R Δ supermap.{coord} stage field")
                    r_labels.append(f"R Δ dashboard.pipelines row {coord}")
                elif field == 'agent':
                    r_labels.append(f"R Δ supermap.{coord} agent field")
                elif field == 'lock':
                    r_labels.append(f"R Δ supermap.{coord} lock indicator")
    except ImportError:
        # Fallback without RenderClient
        for pc in parsed_changes:
            coord = pc.get('coord', '?')
            field = pc.get('field', '?')
            if coord and field:
                r_labels.append(f"R Δ supermap.{coord} {field} field")

    # 3. Walk dependency graph for cascading effects
    cascading_deps = []
    orphaned_handoffs = []
    conn = _get_conn(db_path)
    if conn:
        try:
            # Extract affected versions from parsed changes
            affected_versions = set()
            for pc in parsed_changes:
                coord = pc.get('coord')
                if coord and coord.startswith('p'):
                    # Resolve p-coordinate to version
                    try:
                        from orchestration_engine import resolve_pipeline
                        ver = resolve_pipeline(coord)
                        if ver:
                            affected_versions.add(ver)
                    except ImportError:
                        pass

            for ver in affected_versions:
                # Check downstream deps that were satisfied by this version
                satisfied = conn.execute(
                    "SELECT target_version, dep_type, satisfied_at "
                    "FROM pipeline_dependency "
                    "WHERE source_version = ? AND status = 'satisfied'",
                    (ver,)
                ).fetchall()

                for dep in satisfied:
                    # A stage revert may invalidate downstream satisfaction
                    stage_reverted = any(
                        pc.get('field') == 'stage' for pc in parsed_changes
                        if pc.get('coord')
                    )
                    if stage_reverted:
                        cascading_deps.append({
                            'target': dep['target_version'],
                            'was_satisfied_by': ver,
                            'dep_type': dep['dep_type'],
                            'now_suspect': True,
                        })

                # 4. Check for orphaned handoffs
                active_handoffs = conn.execute(
                    "SELECT id, target_agent, completed_stage, next_stage "
                    "FROM handoff "
                    "WHERE version = ? AND status IN ('dispatched', 'acknowledged', 'working')",
                    (ver,)
                ).fetchall()

                for h in active_handoffs:
                    orphaned_handoffs.append({
                        'handoff_id': h['id'],
                        'target_agent': h['target_agent'],
                        'completed_stage': h['completed_stage'],
                        'next_stage': h['next_stage'],
                    })

        except Exception:
            pass
        finally:
            conn.close()

    # Build impact summary
    parts = []
    if r_labels:
        parts.append(f"{len(r_labels)} R-label(s)")
    if cascading_deps:
        parts.append(f"{len(cascading_deps)} suspect dep(s)")
    if orphaned_handoffs:
        parts.append(f"{len(orphaned_handoffs)} orphaned handoff(s)")
    impact_summary = ', '.join(parts) if parts else 'No downstream impact detected'

    return {
        'f_labels': f_labels,
        'r_labels': r_labels,
        'cascading_deps': cascading_deps,
        'orphaned_handoffs': orphaned_handoffs,
        'impact_summary': impact_summary,
    }


def preview_revert_deps(version: str, target_stage: str,
                        current_stage: str,
                        db_path: Path = DEFAULT_DB_PATH) -> str:
    """Preview what dependency changes a revert would cause."""
    lines = [f"Dependency impact preview: {version}",
             f"  Revert: {current_stage} → {target_stage}", ""]

    conn = _get_conn(db_path)
    if not conn:
        lines.append("  (No temporal DB — cannot assess dep impact)")
        return '\n'.join(lines)

    try:
        # Check if this version satisfied any downstream deps
        satisfied = conn.execute(
            "SELECT target_version, dep_type FROM pipeline_dependency "
            "WHERE source_version = ? AND status = 'satisfied'",
            (version,)
        ).fetchall()

        if satisfied:
            lines.append("  ⚠ Downstream deps previously satisfied by this pipeline:")
            for dep in satisfied:
                lines.append(f"    → {dep['target_version']} ({dep['dep_type']})")
            lines.append("  Note: Revert does NOT un-satisfy deps (manual re-evaluation needed)")
        else:
            lines.append("  No downstream dependencies affected.")

        return '\n'.join(lines)
    except Exception:
        return '\n'.join(lines + ["  (Error checking deps)"])
    finally:
        conn.close()


# ─── CLI ──────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    args = sys.argv[1:]
    json_mode = '--json' in args
    if json_mode:
        args.remove('--json')

    if not args:
        print(render_dependency_graph())
        sys.exit(0)

    cmd = args[0]

    if cmd == 'list':
        if json_mode:
            print(json.dumps(get_all_deps(), indent=2))
        else:
            print(render_dependency_graph())

    elif cmd == 'register':
        if len(args) < 3:
            print("Usage: dependency_graph.py register <source> <target> [dep_type]")
            sys.exit(1)
        dep_type = args[3] if len(args) > 3 else 'completion'
        ok = register_dependency(args[1], args[2], dep_type)
        print(f"{'✅' if ok else '❌'} {'Registered' if ok else 'Failed'}: "
              f"{args[1]} → {args[2]} ({dep_type})")

    elif cmd == 'remove':
        if len(args) < 3:
            print("Usage: dependency_graph.py remove <source> <target>")
            sys.exit(1)
        ok = remove_dependency(args[1], args[2])
        print(f"{'✅' if ok else '❌'} {'Removed' if ok else 'Failed'}: {args[1]} → {args[2]}")

    elif cmd == 'check':
        if len(args) < 2:
            print("Usage: dependency_graph.py check <version>")
            sys.exit(1)
        result = check_deps_satisfied(args[1])
        if json_mode:
            print(json.dumps(result, indent=2))
        else:
            status = '✅ All deps met' if result['all_met'] else '⏳ Deps pending'
            print(f"{status} for {args[1]}")
            for d in result['deps']:
                icon = '✅' if d['status'] == 'satisfied' else '⏳'
                print(f"  {icon} {d['source_version']} ({d['dep_type']})")

    elif cmd == 'resolve':
        if len(args) < 2:
            print("Usage: dependency_graph.py resolve <version> [action]")
            sys.exit(1)
        action = args[2] if len(args) > 2 else 'complete'
        results = resolve_downstream_deps(args[1], action)
        if json_mode:
            print(json.dumps(results, indent=2))
        else:
            if results:
                for r in results:
                    icon = '✅' if r['all_deps_met'] else '⏳'
                    print(f"  {icon} {r['target']}: dep on {r['dep_satisfied']} satisfied. "
                          f"All met: {r['all_deps_met']}")
            else:
                print(f"  No downstream deps to resolve for {args[1]}")

    elif cmd == 'graph':
        print(render_dependency_graph())

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: list, register, remove, check, resolve, graph")
        sys.exit(1)
