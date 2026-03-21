#!/usr/bin/env python3
"""SpacetimeDB Temporal Overlay for Orchestration Engine V2.

This is an OVERLAY — it enhances V2 with temporal capabilities
(state history, persistent agent context, real-time presence)
without replacing the filesystem-based state management.

Graceful degradation: if SpacetimeDB is unavailable, all methods
return None/False and V2 continues operating normally.

Addresses Critic FLAGs:
  FLAG-1: Uses reducers for writes, sanitized SQL for reads (analytics only)
  FLAG-2: Split reducers (log_transition + advance_pipeline)
  FLAG-3: agent_context filesystem backup via export_context()
  FLAG-5: Presence TTL detection in get_dashboard()
  FLAG-6: Reconciliation clearly scoped to pipeline_state only

Usage:
    from temporal_overlay import TemporalOverlay

    overlay = TemporalOverlay(workspace=Path('.'))
    if overlay.available:
        overlay.record_transition('pipeline-v5', 'design', 'build', 'builder', 'complete', 'Done')
"""

import json
import subprocess
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

# Heartbeat TTL: agents not seen in this many seconds are marked stale (FLAG-5)
HEARTBEAT_TTL_SECONDS = 300  # 5 minutes


class TemporalOverlay:
    """SpacetimeDB integration for the Orchestration Engine V2.

    Graceful degradation: if SpacetimeDB is unavailable, all public methods
    return None (queries) or False (mutations), and V2 continues on filesystem.
    """

    def __init__(self, workspace: Path, spacetime_url: str = 'http://localhost:3000',
                 db_name: str = 'belam-orchestration'):
        self.workspace = Path(workspace)
        self.spacetime_url = spacetime_url
        self.db_name = db_name
        self._available: Optional[bool] = None
        self._spacetime_bin: Optional[str] = None

    @property
    def spacetime_bin(self) -> str:
        """Locate the spacetime CLI binary."""
        if self._spacetime_bin is None:
            # Check common install locations
            for path in [
                os.path.expanduser('~/.local/bin/spacetime'),
                '/usr/local/bin/spacetime',
                'spacetime',  # PATH lookup
            ]:
                try:
                    result = subprocess.run(
                        [path, 'version', 'list'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        self._spacetime_bin = path
                        break
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            if self._spacetime_bin is None:
                self._spacetime_bin = 'spacetime'  # Fallback
        return self._spacetime_bin

    @property
    def available(self) -> bool:
        """Check if SpacetimeDB is running and the module is published."""
        if self._available is None:
            try:
                result = subprocess.run(
                    [self.spacetime_bin, 'sql', self.db_name,
                     'SELECT COUNT(*) FROM pipeline_state'],
                    capture_output=True, text=True, timeout=5
                )
                self._available = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._available = False
        return self._available

    def reset_availability(self):
        """Force re-check of SpacetimeDB availability on next access."""
        self._available = None

    # ─── State Mutations (via reducers — FLAG-1) ───────────────────

    def record_transition(self, version: str, from_stage: str, to_stage: str,
                          agent: str, action: str, notes: str = '',
                          session_id: str = '', duration_seconds: Optional[int] = None) -> bool:
        """Record a state transition in the temporal log.

        FLAG-2 fix: calls log_transition reducer (logging only),
        separate from advance_pipeline (state mutation).
        """
        if not self.available:
            return False
        return self._call_reducer('log_transition', [
            version, from_stage, to_stage, agent, action, notes,
            session_id or 'unknown',
            duration_seconds,  # Option<u64> — None maps to null
        ])

    def advance_pipeline(self, version: str, completed_stage: str,
                         next_stage: str, source_agent: str,
                         target_agent: str, notes: str = '') -> bool:
        """Advance pipeline state and create handoff record.

        FLAG-2 fix: separated from log_transition. Call this AFTER
        record_transition for full audit trail + state advancement.
        """
        if not self.available:
            return False
        return self._call_reducer('advance_pipeline', [
            version, completed_stage, next_stage,
            source_agent, target_agent, notes,
        ])

    def upsert_pipeline(self, version: str, status: str,
                        current_stage: str, current_agent: str,
                        tags: str = '[]', priority: str = 'medium') -> bool:
        """Create or update a pipeline state record."""
        if not self.available:
            return False
        return self._call_reducer('upsert_pipeline', [
            version, status, current_stage, current_agent, tags, priority,
        ])

    def verify_handoff(self, handoff_id: int) -> bool:
        """Mark a handoff as verified/acknowledged."""
        if not self.available:
            return False
        return self._call_reducer('verify_handoff', [handoff_id])

    def heartbeat(self, agent: str, pipeline: Optional[str] = None,
                  stage: Optional[str] = None,
                  session_id: Optional[str] = None) -> bool:
        """Update agent presence."""
        if not self.available:
            return False
        return self._call_reducer('heartbeat', [
            agent, pipeline, stage, session_id,
        ])

    def update_agent_context(self, version: str, agent: str,
                              context_delta: dict, session_id: str,
                              tokens_used: int = 0) -> bool:
        """Accumulate agent context for persistent pipeline memory.

        context_delta is merged using RFC 7396 with array concatenation:
        - Object keys: deep merge
        - Arrays: concatenated (decisions, flags, questions accumulate)
        - Null values: delete the key
        - Primitives: new overwrites old
        """
        if not self.available:
            return False
        return self._call_reducer('update_agent_context', [
            version, agent, json.dumps(context_delta),
            session_id, tokens_used,
        ])

    # ─── Queries (sanitized SQL for analytics — FLAG-1) ────────────

    def get_pipeline(self, version: str) -> Optional[dict]:
        """Get current state of a specific pipeline."""
        if not self.available:
            return None
        result = self._query(
            "SELECT * FROM pipeline_state WHERE version = '{}'".format(
                self._sanitize(version)
            )
        )
        return result[0] if result else None

    def get_all_pipelines(self) -> Optional[List[dict]]:
        """Get all pipeline states."""
        if not self.available:
            return None
        return self._query("SELECT * FROM pipeline_state ORDER BY updated_at DESC")

    def get_agent_context(self, version: str, agent: str) -> Optional[dict]:
        """Retrieve persistent agent context for a pipeline."""
        if not self.available:
            return None
        key = f"{version}:{agent}"
        result = self._query(
            "SELECT * FROM agent_context WHERE key = '{}'".format(
                self._sanitize(key)
            )
        )
        if result:
            ctx_str = result[0].get('accumulated_context', '{}')
            try:
                return json.loads(ctx_str)
            except json.JSONDecodeError:
                return {}
        return {}

    def get_timeline(self, version: str) -> Optional[List[dict]]:
        """Get full transition timeline for a pipeline."""
        if not self.available:
            return None
        return self._query(
            "SELECT * FROM state_transition WHERE version = '{}' "
            "ORDER BY timestamp ASC".format(self._sanitize(version))
        )

    def get_recent_handoffs(self, limit: int = 10) -> Optional[List[dict]]:
        """Get recent handoffs across all pipelines."""
        if not self.available:
            return None
        return self._query(
            f"SELECT * FROM handoff ORDER BY dispatched_at DESC LIMIT {int(limit)}"
        )

    def get_agent_presence(self) -> Optional[List[dict]]:
        """Get all agent presence records with TTL check (FLAG-5)."""
        if not self.available:
            return None
        agents = self._query("SELECT * FROM agent_presence ORDER BY agent")
        if agents:
            now = datetime.now(timezone.utc)
            for agent in agents:
                # FLAG-5: Mark stale agents
                heartbeat_str = agent.get('last_heartbeat', '')
                try:
                    last_hb = datetime.fromisoformat(heartbeat_str.replace('Z', '+00:00'))
                    if (now - last_hb).total_seconds() > HEARTBEAT_TTL_SECONDS:
                        agent['status'] = f"offline (stale — last seen {heartbeat_str})"
                except (ValueError, TypeError):
                    pass  # Can't parse timestamp, leave status as-is
        return agents

    def get_dashboard(self) -> Optional[dict]:
        """Get autoclave dashboard snapshot.

        Returns structured dict with pipelines, agents (with TTL check),
        and recent handoffs.
        """
        if not self.available:
            return None
        return {
            'pipelines': self.get_all_pipelines() or [],
            'agents': self.get_agent_presence() or [],
            'recent_handoffs': self.get_recent_handoffs() or [],
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }

    def time_travel(self, version: str, at: str) -> Optional[dict]:
        """Query pipeline state at a past timestamp.

        Uses state_transition table to reconstruct state at any point.
        `at` should be an ISO-8601 timestamp string.
        """
        if not self.available:
            return None
        transitions = self._query(
            "SELECT * FROM state_transition WHERE version = '{}' "
            "AND timestamp <= '{}' ORDER BY timestamp DESC LIMIT 1".format(
                self._sanitize(version), self._sanitize(at)
            )
        )
        if transitions:
            return transitions[0]
        return None

    # ─── Agent Context Filesystem Backup (FLAG-3) ──────────────────

    def export_context(self, version: str) -> bool:
        """Export agent_context to filesystem for backup.

        FLAG-3 fix: agent_context is SpacetimeDB-native data without
        filesystem equivalent. This method writes snapshots to
        pipeline_builds/{version}_agent_context.json for durability.
        """
        if not self.available:
            return False

        results = self._query(
            "SELECT * FROM agent_context WHERE version = '{}'".format(
                self._sanitize(version)
            )
        )
        if results is None:
            return False

        output_path = (
            self.workspace / 'machinelearning' / 'snn_applied_finance' /
            'research' / 'pipeline_builds' / f'{version}_agent_context.json'
        )
        try:
            output_path.write_text(json.dumps(results, indent=2, default=str))
            return True
        except OSError:
            return False

    def export_all_contexts(self) -> int:
        """Export all agent contexts to filesystem. Returns count exported."""
        if not self.available:
            return 0

        all_contexts = self._query("SELECT DISTINCT version FROM agent_context")
        if not all_contexts:
            return 0

        count = 0
        for row in all_contexts:
            version = row.get('version', '')
            if version and self.export_context(version):
                count += 1
        return count

    # ─── Filesystem Reconciliation (FLAG-6: scoped to pipeline_state) ─

    def sync_from_filesystem(self, pipeline_dir: Optional[Path] = None) -> dict:
        """Reconcile filesystem state → SpacetimeDB pipeline_state table.

        FLAG-6 clarification: This sync covers pipeline_state ONLY.
        state_transition and handoff entries created by the temporal
        layer have no filesystem equivalent. agent_context is backed
        up separately via export_context().

        Args:
            pipeline_dir: Directory containing *_state.json files.
                         Defaults to research/pipeline_builds/

        Returns:
            Dict with counts: {'synced': N, 'errors': N, 'skipped': N}
        """
        if not self.available:
            return {'synced': 0, 'errors': 0, 'skipped': 0, 'available': False}

        if pipeline_dir is None:
            pipeline_dir = (
                self.workspace / 'machinelearning' / 'snn_applied_finance' /
                'research' / 'pipeline_builds'
            )

        stats = {'synced': 0, 'errors': 0, 'skipped': 0}

        if not pipeline_dir.is_dir():
            return stats

        for state_file in sorted(pipeline_dir.glob('*_state.json')):
            try:
                state = json.loads(state_file.read_text())
                version = state.get('version', '')
                if not version:
                    stats['skipped'] += 1
                    continue

                # Map filesystem state to SpacetimeDB fields
                status = state.get('status', 'unknown')
                current_stage = state.get('pending_action', '')
                current_agent = state.get('current_agent', '')

                success = self.upsert_pipeline(
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
                    stats['errors'] += 1
            except (json.JSONDecodeError, OSError) as e:
                stats['errors'] += 1

        return stats

    # ─── Persistent Agent Context Model ────────────────────────────

    class PersistentAgentContext:
        """Pipeline-scoped context that persists across agent sessions.

        Provides typed methods for accumulating structured context
        while storing as JSON blob in SpacetimeDB.
        """

        def __init__(self, overlay: 'TemporalOverlay', version: str, agent: str):
            self.overlay = overlay
            self.version = version
            self.agent = agent
            self._context: Optional[dict] = None

        def load(self) -> dict:
            """Load accumulated context from SpacetimeDB.

            Returns structured dict with:
            - design_decisions: list of {decision, rationale, stage, timestamp}
            - open_questions: list of {question, raised_by, stage}
            - resolved_questions: list of {question, answer, resolved_by, stage}
            - critic_flags: list of {flag_id, description, status, resolution}
            - key_artifacts: list of {path, description, stage}
            - performance_notes: list of {metric, value, context, stage}
            """
            if self._context is None:
                self._context = self.overlay.get_agent_context(
                    self.version, self.agent
                ) or self._empty_context()
            return self._context

        def save(self, session_id: str = '', tokens_used: int = 0) -> bool:
            """Save accumulated context delta to SpacetimeDB."""
            if self._context is None:
                return False
            return self.overlay.update_agent_context(
                self.version, self.agent, self._context,
                session_id, tokens_used,
            )

        def append_decision(self, decision: str, rationale: str, stage: str):
            """Record an architectural decision made during this session."""
            ctx = self.load()
            ctx.setdefault('design_decisions', []).append({
                'decision': decision,
                'rationale': rationale,
                'stage': stage,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })

        def append_flag_resolution(self, flag_id: str, resolution: str, stage: str):
            """Record how a critic flag was resolved."""
            ctx = self.load()
            flags = ctx.setdefault('critic_flags', [])
            # Update existing flag or append new
            for flag in flags:
                if flag.get('flag_id') == flag_id:
                    flag['status'] = 'resolved'
                    flag['resolution'] = resolution
                    return
            flags.append({
                'flag_id': flag_id,
                'status': 'resolved',
                'resolution': resolution,
                'stage': stage,
            })

        def append_artifact(self, path: str, description: str, stage: str):
            """Record a key artifact produced during this session."""
            ctx = self.load()
            ctx.setdefault('key_artifacts', []).append({
                'path': path,
                'description': description,
                'stage': stage,
            })

        def get_design_lineage(self) -> str:
            """Return a narrative of design evolution across sessions.

            This is what gets injected into the dispatch payload alongside
            the standard files_to_read.
            """
            ctx = self.load()
            lines = []

            decisions = ctx.get('design_decisions', [])
            if decisions:
                lines.append("### Key Decisions")
                for d in decisions:
                    lines.append(f"- **{d['decision']}** ({d.get('stage', '?')}): {d.get('rationale', '')}")

            flags = ctx.get('critic_flags', [])
            open_flags = [f for f in flags if f.get('status') != 'resolved']
            resolved_flags = [f for f in flags if f.get('status') == 'resolved']

            if open_flags:
                lines.append("\n### Unresolved Flags")
                for f in open_flags:
                    lines.append(f"- {f.get('flag_id', '?')}: {f.get('description', '')}")

            if resolved_flags:
                lines.append("\n### Resolved Flags")
                for f in resolved_flags:
                    lines.append(f"- {f.get('flag_id', '?')}: {f.get('resolution', '')}")

            questions = ctx.get('open_questions', [])
            if questions:
                lines.append("\n### Open Questions")
                for q in questions:
                    lines.append(f"- {q.get('question', '')} (raised by {q.get('raised_by', '?')})")

            return '\n'.join(lines) if lines else "(No prior context)"

        @staticmethod
        def _empty_context() -> dict:
            return {
                'design_decisions': [],
                'open_questions': [],
                'resolved_questions': [],
                'critic_flags': [],
                'key_artifacts': [],
                'performance_notes': [],
            }

    def get_persistent_context(self, version: str, agent: str) -> 'PersistentAgentContext':
        """Get a PersistentAgentContext instance for a pipeline+agent pair."""
        return self.PersistentAgentContext(self, version, agent)

    # ─── Internal Helpers ──────────────────────────────────────────

    @staticmethod
    def _sanitize(value: str) -> str:
        """Sanitize a string for SQL interpolation (FLAG-1).

        Escapes single quotes per SQL standard. Used only for
        analytics/read queries — all writes go through reducers.
        """
        return value.replace("'", "''")

    def _call_reducer(self, reducer: str, args: list) -> bool:
        """Call a SpacetimeDB reducer via CLI.

        Args are passed as JSON array. SpacetimeDB CLI handles
        parameter serialization, avoiding SQL injection entirely.
        """
        try:
            # Convert args to JSON-compatible format
            json_args = json.dumps(args, default=str)
            result = subprocess.run(
                [self.spacetime_bin, 'call', self.db_name, reducer, json_args],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _query(self, sql: str) -> Optional[List[dict]]:
        """Run a SQL query against SpacetimeDB.

        Used for analytics/read queries only. All inputs are
        sanitized via _sanitize() before interpolation.
        """
        try:
            result = subprocess.run(
                [self.spacetime_bin, 'sql', self.db_name, sql],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return self._parse_sql_output(result.stdout)
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    @staticmethod
    def _parse_sql_output(output: str) -> List[dict]:
        """Parse spacetime sql CLI output into list of dicts.

        SpacetimeDB CLI outputs pipe-delimited table format:
        | col1 | col2 | col3 |
        |------|------|------|
        | val1 | val2 | val3 |
        """
        lines = output.strip().split('\n')
        if len(lines) < 2:
            return []

        # Find header line (first line with | delimiters)
        header_idx = None
        for i, line in enumerate(lines):
            if '|' in line and not all(c in '|-+ ' for c in line):
                header_idx = i
                break
        if header_idx is None:
            return []

        headers = [h.strip() for h in lines[header_idx].split('|') if h.strip()]

        results = []
        for line in lines[header_idx + 1:]:
            # Skip separator lines
            if all(c in '|-+ ' for c in line):
                continue
            values = [v.strip() for v in line.split('|') if v.strip()]
            if len(values) == len(headers):
                results.append(dict(zip(headers, values)))

        return results


# ─── CLI Interface ─────────────────────────────────────────────────

def main():
    """CLI interface for temporal overlay operations."""
    import argparse

    parser = argparse.ArgumentParser(description='Temporal Overlay for Orchestration Engine V2')
    parser.add_argument('action', choices=[
        'status', 'dashboard', 'timeline', 'timetravel',
        'sync', 'export-context', 'presence',
    ])
    parser.add_argument('--version', '-v', help='Pipeline version')
    parser.add_argument('--at', help='Timestamp for time-travel query')
    parser.add_argument('--workspace', '-w', default='.', help='Workspace root')
    parser.add_argument('--db-name', default='belam-orchestration', help='SpacetimeDB database name')

    args = parser.parse_args()
    overlay = TemporalOverlay(workspace=Path(args.workspace), db_name=args.db_name)

    if args.action == 'status':
        print(f"SpacetimeDB available: {overlay.available}")
        print(f"Database: {overlay.db_name}")
        print(f"Binary: {overlay.spacetime_bin}")

    elif args.action == 'dashboard':
        dashboard = overlay.get_dashboard()
        if dashboard:
            print(json.dumps(dashboard, indent=2, default=str))
        else:
            print("SpacetimeDB unavailable — dashboard not available")

    elif args.action == 'timeline':
        if not args.version:
            parser.error("--version required for timeline")
        timeline = overlay.get_timeline(args.version)
        if timeline:
            for entry in timeline:
                print(f"  {entry.get('timestamp', '?')} | {entry.get('from_stage', '?')} → {entry.get('to_stage', '?')} | {entry.get('agent', '?')} | {entry.get('action', '?')}")
        else:
            print("No timeline data (SpacetimeDB unavailable or no transitions)")

    elif args.action == 'timetravel':
        if not args.version or not args.at:
            parser.error("--version and --at required for timetravel")
        state = overlay.time_travel(args.version, args.at)
        if state:
            print(json.dumps(state, indent=2, default=str))
        else:
            print("No state found at that timestamp")

    elif args.action == 'sync':
        stats = overlay.sync_from_filesystem()
        print(f"Sync results: {json.dumps(stats)}")

    elif args.action == 'export-context':
        if args.version:
            success = overlay.export_context(args.version)
            print(f"Export {'successful' if success else 'failed'}")
        else:
            count = overlay.export_all_contexts()
            print(f"Exported {count} pipeline contexts")

    elif args.action == 'presence':
        agents = overlay.get_agent_presence()
        if agents:
            for a in agents:
                print(f"  {a.get('agent', '?')}: {a.get('status', '?')} — pipeline={a.get('current_pipeline', '-')}")
        else:
            print("No presence data")


if __name__ == '__main__':
    main()
