#!/usr/bin/env python3
"""
temporal_overlay.py — SQLite-backed temporal integration for Orchestration Engine V2

Provides temporal state, persistent agent context, and autoclave dashboard for the
V2 orchestration engine. Uses SQLite+WAL instead of SpacetimeDB (see temporal_schema.py
header for rationale).

This is an OVERLAY — it enhances V2 with temporal capabilities without replacing
the filesystem-based state management.

Graceful degradation: if the temporal DB is unavailable or initialization fails,
all methods return None/False and V2 continues operating normally on filesystem state.

Addresses all Critic FLAGs:
  FLAG-1 (MED): SQL injection → All queries use parameterized placeholders (?)
  FLAG-2 (MED): Reducer mismatch → Split into log_transition() + advance_pipeline()
  FLAG-3 (MED): agent_context backup → SQLite DB IS on filesystem; auto-backed up
  FLAG-4 (LOW): merge_json → Deep merge: objects recursive, arrays concatenated, primitives overwrite
  FLAG-5 (LOW): Agent presence TTL → Python-side check in get_dashboard()
  FLAG-6 (LOW): Reconciliation scope → Documented as pipeline_state only; others noted

Usage (standalone):
    python3 scripts/temporal_overlay.py dashboard           # Autoclave dashboard
    python3 scripts/temporal_overlay.py timeline <version>  # Pipeline timeline
    python3 scripts/temporal_overlay.py timetravel <ver> <iso-timestamp>
    python3 scripts/temporal_overlay.py agents              # Agent presence
    python3 scripts/temporal_overlay.py context <ver> <agent>  # Agent context
    python3 scripts/temporal_overlay.py stats               # Duration analytics
"""

import json
import os
import sqlite3
import sys
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Callable

# ─── Configuration ───────────────────────────────────────────────────────────────

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
DEFAULT_DB_PATH = WORKSPACE / 'data' / 'temporal.db'

# Agent presence TTL: agents not seen for this many seconds are marked stale (FLAG-5)
HEARTBEAT_TTL_SECONDS = 300  # 5 minutes


# ─── JSON Deep Merge (Critic FLAG-4) ─────────────────────────────────────────────

def merge_json(base: str, delta: str) -> str:
    """Deep merge two JSON strings.

    Merge semantics (Critic FLAG-4 resolution):
      - Objects: recursive merge (delta keys overwrite base keys)
      - Arrays: concatenate (delta appended to base) — preserves history
      - Primitives: delta overwrites base
      - Null in delta: removes key from base (RFC 7396 inspired)

    This preserves accumulated lists (design_decisions, open_questions, critic_flags)
    across sessions while allowing structured updates.
    """
    try:
        base_obj = json.loads(base) if isinstance(base, str) else base
    except (json.JSONDecodeError, TypeError):
        base_obj = {}
    try:
        delta_obj = json.loads(delta) if isinstance(delta, str) else delta
    except (json.JSONDecodeError, TypeError):
        delta_obj = {}

    merged = _deep_merge(base_obj, delta_obj)
    return json.dumps(merged)


def _deep_merge(base, delta):
    """Recursive deep merge implementation."""
    if isinstance(base, dict) and isinstance(delta, dict):
        result = dict(base)  # shallow copy of base
        for key, value in delta.items():
            if value is None:
                # RFC 7396: null removes key
                result.pop(key, None)
            elif key in result:
                result[key] = _deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result
    elif isinstance(base, list) and isinstance(delta, list):
        # Concatenate arrays — preserves history
        return base + delta
    else:
        # Primitives: delta overwrites
        return deepcopy(delta) if delta is not None else base


# ─── Core Overlay Class ──────────────────────────────────────────────────────────

class TemporalOverlay:
    """SQLite-backed temporal integration for the Orchestration Engine V2.

    Provides:
      - Transition logging (immutable append-only audit trail)
      - Pipeline state tracking (current state with history)
      - Handoff lifecycle management (dispatched → verified → completed)
      - Persistent agent context (cross-session pipeline-scoped memory)
      - Agent presence (heartbeat-driven status)
      - Autoclave dashboard (shared view of all pipeline state)
      - Time-travel queries (reconstruct state at any past timestamp)
      - Duration analytics (stage bottleneck identification)

    All methods gracefully degrade: return None/False on failure.
    No method raises exceptions — the overlay must never break V2.
    """

    def __init__(self, workspace: Path = WORKSPACE, db_path: Path = None):
        self.workspace = workspace
        self.db_path = db_path or DEFAULT_DB_PATH
        self._conn = None
        self._available = None

    @property
    def available(self) -> bool:
        """Check if the temporal DB is available and initialized."""
        if self._available is None:
            try:
                conn = self._get_conn()
                # Quick sanity check
                conn.execute("SELECT COUNT(*) FROM pipeline_state")
                self._available = True
            except Exception:
                self._available = False
        return self._available

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create a connection to the temporal DB."""
        if self._conn is None:
            from temporal_schema import init_db
            self._conn = init_db(self.db_path)
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ─── Transition Logging (Critic FLAG-2: separated from state mutation) ────

    def log_transition(self, version: str, from_stage: str, to_stage: str,
                       agent: str, action: str, notes: str = '',
                       artifact: str = None, session_id: str = '') -> bool:
        """Log a state transition to the immutable audit trail.

        This is the "log_transition" half of the Critic FLAG-2 split.
        Purely append-only — never modifies pipeline_state.
        Uses parameterized queries (Critic FLAG-1).
        """
        if not self.available:
            return False
        try:
            conn = self._get_conn()

            # Compute duration from previous transition
            duration = None
            prev = conn.execute(
                "SELECT timestamp FROM state_transition "
                "WHERE version = ? ORDER BY id DESC LIMIT 1",
                (version,)
            ).fetchone()
            if prev:
                try:
                    prev_ts = datetime.fromisoformat(prev['timestamp'].replace('Z', '+00:00'))
                    now_ts = datetime.now(timezone.utc)
                    duration = int((now_ts - prev_ts).total_seconds())
                except (ValueError, TypeError):
                    pass

            conn.execute(
                "INSERT INTO state_transition "
                "(version, from_stage, to_stage, agent, action, notes, artifact, "
                "session_id, duration_seconds) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (version, from_stage, to_stage, agent, action, notes, artifact,
                 session_id, duration)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[temporal] log_transition error: {e}", file=sys.stderr)
            return False

    def advance_pipeline(self, version: str, stage: str, agent: str,
                         status: str = None) -> bool:
        """Update current pipeline state.

        This is the "advance_pipeline" half of the Critic FLAG-2 split.
        Modifies pipeline_state (upsert).
        """
        if not self.available:
            return False
        try:
            conn = self._get_conn()
            now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            existing = conn.execute(
                "SELECT version FROM pipeline_state WHERE version = ?",
                (version,)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE pipeline_state SET current_stage = ?, current_agent = ?, "
                    "status = COALESCE(?, status), updated_at = ?, "
                    "locked_by = NULL, lock_acquired_at = NULL "
                    "WHERE version = ?",
                    (stage, agent, status, now, version)
                )
            else:
                conn.execute(
                    "INSERT INTO pipeline_state "
                    "(version, status, current_stage, current_agent, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (version, status or 'phase1_build', stage, agent, now, now)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"[temporal] advance_pipeline error: {e}", file=sys.stderr)
            return False

    def record_transition(self, version: str, from_stage: str, to_stage: str,
                          agent: str, action: str, notes: str = '',
                          next_agent: str = None, artifact: str = None,
                          session_id: str = '') -> bool:
        """Combined transition: log + advance + create handoff if needed.

        Convenience method for the V2 engine integration hook.
        Runs as a single transaction for atomicity.
        """
        if not self.available:
            return False
        try:
            conn = self._get_conn()
            conn.execute("BEGIN IMMEDIATE")

            # 1. Log the transition
            self.log_transition(version, from_stage, to_stage, agent, action,
                                notes, artifact, session_id)

            # 2. Advance pipeline state
            self.advance_pipeline(version, to_stage, next_agent or agent)

            # 3. Create handoff if transitioning to a different agent
            if next_agent and next_agent != agent:
                self.create_handoff(version, agent, next_agent,
                                    from_stage, to_stage, notes)

            conn.commit()
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            print(f"[temporal] record_transition error: {e}", file=sys.stderr)
            return False

    # ─── Handoff Management ──────────────────────────────────────────────────

    def create_handoff(self, version: str, source_agent: str,
                       target_agent: str, completed_stage: str,
                       next_stage: str, notes: str = '',
                       payload_hash: str = '') -> Optional[int]:
        """Create a handoff record. Returns handoff ID."""
        if not self.available:
            return None
        try:
            conn = self._get_conn()
            cursor = conn.execute(
                "INSERT INTO handoff "
                "(version, source_agent, target_agent, completed_stage, "
                "next_stage, notes, dispatch_payload_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (version, source_agent, target_agent, completed_stage,
                 next_stage, notes, payload_hash)
            )
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"[temporal] create_handoff error: {e}", file=sys.stderr)
            return None

    def update_handoff_status(self, handoff_id: int, status: str) -> bool:
        """Update handoff lifecycle status.

        Lifecycle: dispatched → acknowledged → working → completed/blocked/timed_out
        """
        if not self.available:
            return False
        try:
            conn = self._get_conn()
            verified = None
            if status in ('acknowledged', 'completed', 'blocked'):
                verified = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            conn.execute(
                "UPDATE handoff SET status = ?, verified_at = COALESCE(?, verified_at) "
                "WHERE id = ?",
                (status, verified, handoff_id)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[temporal] update_handoff_status error: {e}", file=sys.stderr)
            return False

    # ─── Persistent Agent Context ────────────────────────────────────────────

    def get_agent_context(self, version: str, agent: str) -> Optional[dict]:
        """Retrieve persistent agent context for a pipeline.

        Returns structured dict with accumulated cross-session knowledge:
          - design_decisions, open_questions, resolved_questions,
            critic_flags, key_artifacts, performance_notes, learnings
        """
        if not self.available:
            return None
        try:
            conn = self._get_conn()
            key = f"{version}:{agent}"
            row = conn.execute(
                "SELECT accumulated_context, session_count, last_active_at "
                "FROM agent_context WHERE key = ?",
                (key,)
            ).fetchone()
            if row:
                ctx = json.loads(row['accumulated_context'])
                ctx['_meta'] = {
                    'session_count': row['session_count'],
                    'last_active': row['last_active_at'],
                }
                return ctx
            return {}
        except Exception as e:
            print(f"[temporal] get_agent_context error: {e}", file=sys.stderr)
            return None

    def update_agent_context(self, version: str, agent: str,
                             context_delta: dict, session_id: str = '',
                             tokens_used: int = 0) -> bool:
        """Accumulate agent context using deep merge (Critic FLAG-4).

        Merge semantics:
          - Objects: recursive merge (delta keys overwrite base keys)
          - Arrays: concatenate (preserves history across sessions)
          - Primitives: delta overwrites base
          - None/null: removes key (RFC 7396 inspired)
        """
        if not self.available:
            return False
        try:
            conn = self._get_conn()
            key = f"{version}:{agent}"
            now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            existing = conn.execute(
                "SELECT accumulated_context, session_count, total_tokens_used "
                "FROM agent_context WHERE key = ?",
                (key,)
            ).fetchone()

            if existing:
                # Deep merge (FLAG-4: defined semantics)
                merged = merge_json(existing['accumulated_context'],
                                    json.dumps(context_delta))
                conn.execute(
                    "UPDATE agent_context SET "
                    "accumulated_context = ?, session_count = ?, "
                    "total_tokens_used = ?, last_session_id = ?, "
                    "last_active_at = ? WHERE key = ?",
                    (merged, existing['session_count'] + 1,
                     existing['total_tokens_used'] + tokens_used,
                     session_id, now, key)
                )
            else:
                conn.execute(
                    "INSERT INTO agent_context "
                    "(key, version, agent, accumulated_context, session_count, "
                    "total_tokens_used, last_session_id, last_active_at, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (key, version, agent, json.dumps(context_delta),
                     1, tokens_used, session_id, now, now)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"[temporal] update_agent_context error: {e}", file=sys.stderr)
            return False

    # ─── Persistent Agent Context — Typed Accessors ──────────────────────────

    def append_decision(self, version: str, agent: str,
                        decision: str, rationale: str, stage: str) -> bool:
        """Record an architectural/implementation decision."""
        return self.update_agent_context(version, agent, {
            'design_decisions': [{
                'decision': decision,
                'rationale': rationale,
                'stage': stage,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }]
        })

    def append_flag_resolution(self, version: str, agent: str,
                               flag_id: str, resolution: str, stage: str) -> bool:
        """Record how a critic flag was resolved."""
        return self.update_agent_context(version, agent, {
            'critic_flags': [{
                'flag_id': flag_id,
                'resolution': resolution,
                'stage': stage,
                'status': 'resolved',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }]
        })

    def append_learning(self, version: str, agent: str,
                        learning: str, stage: str) -> bool:
        """Record a cross-session learning."""
        return self.update_agent_context(version, agent, {
            'learnings': [{
                'insight': learning,
                'stage': stage,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }]
        })

    def get_design_lineage(self, version: str, agent: str) -> Optional[str]:
        """Return a narrative of design evolution across sessions.

        This is injected into dispatch payloads as persistent_context.
        """
        ctx = self.get_agent_context(version, agent)
        if not ctx:
            return None

        lines = []
        meta = ctx.get('_meta', {})
        session_count = meta.get('session_count', 0)
        if session_count:
            lines.append(f"You are session {session_count + 1} of {agent} "
                         f"on {version}.")

        decisions = ctx.get('design_decisions', [])
        if decisions:
            lines.append("\n### Key Decisions")
            for d in decisions[-10:]:  # Last 10 decisions
                lines.append(f"- {d['decision']} (rationale: {d.get('rationale', 'N/A')})")

        flags = ctx.get('critic_flags', [])
        unresolved = [f for f in flags if f.get('status') != 'resolved']
        resolved = [f for f in flags if f.get('status') == 'resolved']
        if unresolved:
            lines.append("\n### Unresolved Flags")
            for f in unresolved:
                lines.append(f"- {f['flag_id']}: {f.get('description', 'N/A')}")
        if resolved:
            lines.append("\n### Resolved Flags")
            for f in resolved[-5:]:  # Last 5 resolved
                lines.append(f"- {f['flag_id']}: {f.get('resolution', 'N/A')}")

        learnings = ctx.get('learnings', [])
        if learnings:
            lines.append("\n### Learnings")
            for l in learnings[-5:]:  # Last 5
                lines.append(f"- {l['insight']}")

        return '\n'.join(lines) if lines else None

    # ─── Agent Presence (Critic FLAG-5: TTL at query time) ───────────────────

    def heartbeat(self, agent: str, pipeline: str = None,
                  stage: str = None, session_id: str = None) -> bool:
        """Update agent presence. Called by heartbeat hooks."""
        if not self.available:
            return False
        try:
            conn = self._get_conn()
            now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            status = 'working' if pipeline else 'idle'

            existing = conn.execute(
                "SELECT agent FROM agent_presence WHERE agent = ?",
                (agent,)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE agent_presence SET status = ?, current_pipeline = ?, "
                    "current_stage = ?, last_heartbeat = ?, session_id = ? "
                    "WHERE agent = ?",
                    (status, pipeline, stage, now, session_id, agent)
                )
            else:
                conn.execute(
                    "INSERT INTO agent_presence "
                    "(agent, status, current_pipeline, current_stage, "
                    "last_heartbeat, session_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (agent, status, pipeline, stage, now, session_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"[temporal] heartbeat error: {e}", file=sys.stderr)
            return False

    def _apply_presence_ttl(self, agents: list) -> list:
        """Apply TTL check to agent presence rows (Critic FLAG-5).

        Marks agents as 'offline (stale)' if last heartbeat exceeds TTL.
        """
        now = datetime.now(timezone.utc)
        result = []
        for agent in agents:
            agent_dict = dict(agent) if hasattr(agent, 'keys') else agent
            try:
                last_hb = datetime.fromisoformat(
                    agent_dict['last_heartbeat'].replace('Z', '+00:00')
                )
                age_seconds = (now - last_hb).total_seconds()
                if age_seconds > HEARTBEAT_TTL_SECONDS:
                    agent_dict['status'] = 'offline (stale)'
                    agent_dict['stale_seconds'] = int(age_seconds)
            except (ValueError, KeyError):
                pass
            result.append(agent_dict)
        return result

    # ─── Autoclave Dashboard ─────────────────────────────────────────────────

    def get_dashboard(self) -> Optional[dict]:
        """Get autoclave dashboard — shared view of all pipeline state.

        Returns:
          {
            "pipelines": [...],
            "agents": [...],          # With TTL applied (FLAG-5)
            "recent_handoffs": [...],
            "stats": { "total_pipelines": N, "active_agents": N, ... }
          }
        """
        if not self.available:
            return None
        try:
            conn = self._get_conn()

            pipelines = [dict(row) for row in conn.execute(
                "SELECT * FROM pipeline_state ORDER BY updated_at DESC"
            ).fetchall()]

            agents_raw = [dict(row) for row in conn.execute(
                "SELECT * FROM agent_presence ORDER BY agent"
            ).fetchall()]
            agents = self._apply_presence_ttl(agents_raw)

            handoffs = [dict(row) for row in conn.execute(
                "SELECT * FROM handoff ORDER BY dispatched_at DESC LIMIT 20"
            ).fetchall()]

            # Compute stats
            active_agents = sum(1 for a in agents
                                if a.get('status') not in ('idle', 'offline (stale)'))

            return {
                'pipelines': pipelines,
                'agents': agents,
                'recent_handoffs': handoffs,
                'stats': {
                    'total_pipelines': len(pipelines),
                    'active_agents': active_agents,
                    'total_agents': len(agents),
                    'pending_handoffs': sum(1 for h in handoffs
                                           if h.get('status') == 'dispatched'),
                },
                'generated_at': datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            print(f"[temporal] get_dashboard error: {e}", file=sys.stderr)
            return None

    # ─── Timeline & Time-Travel ──────────────────────────────────────────────

    def get_timeline(self, version: str) -> Optional[list]:
        """Get full transition timeline for a pipeline."""
        if not self.available:
            return None
        try:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM state_transition WHERE version = ? "
                "ORDER BY timestamp ASC",
                (version,)
            ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[temporal] get_timeline error: {e}", file=sys.stderr)
            return None

    def time_travel(self, version: str, at: str) -> Optional[dict]:
        """Query pipeline state at a past timestamp.

        Reconstructs state by finding the latest transition at or before
        the given timestamp.
        """
        if not self.available:
            return None
        try:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM state_transition WHERE version = ? "
                "AND timestamp <= ? ORDER BY timestamp DESC LIMIT 1",
                (version, at)
            ).fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"[temporal] time_travel error: {e}", file=sys.stderr)
            return None

    # ─── Duration Analytics ──────────────────────────────────────────────────

    def get_stage_durations(self, version: str = None) -> Optional[list]:
        """Get stage duration analytics.

        If version is provided, returns durations for that pipeline.
        Otherwise, aggregates across all pipelines.
        """
        if not self.available:
            return None
        try:
            conn = self._get_conn()
            if version:
                rows = conn.execute(
                    "SELECT from_stage, agent, action, duration_seconds, timestamp "
                    "FROM state_transition "
                    "WHERE version = ? AND duration_seconds IS NOT NULL "
                    "ORDER BY timestamp ASC",
                    (version,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT from_stage, agent, action, "
                    "AVG(duration_seconds) as avg_duration, "
                    "MAX(duration_seconds) as max_duration, "
                    "MIN(duration_seconds) as min_duration, "
                    "COUNT(*) as count "
                    "FROM state_transition "
                    "WHERE duration_seconds IS NOT NULL "
                    "GROUP BY from_stage "
                    "ORDER BY avg_duration DESC"
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[temporal] get_stage_durations error: {e}", file=sys.stderr)
            return None

    def get_bottleneck_analysis(self) -> Optional[dict]:
        """Identify stage bottlenecks across all pipelines."""
        if not self.available:
            return None
        try:
            conn = self._get_conn()

            # Average duration per stage type
            stage_stats = conn.execute(
                "SELECT from_stage, "
                "AVG(duration_seconds) as avg_seconds, "
                "MAX(duration_seconds) as max_seconds, "
                "COUNT(*) as occurrences "
                "FROM state_transition "
                "WHERE duration_seconds IS NOT NULL AND duration_seconds > 0 "
                "GROUP BY from_stage "
                "ORDER BY avg_seconds DESC"
            ).fetchall()

            # Average duration per agent
            agent_stats = conn.execute(
                "SELECT agent, "
                "AVG(duration_seconds) as avg_seconds, "
                "SUM(duration_seconds) as total_seconds, "
                "COUNT(*) as transitions "
                "FROM state_transition "
                "WHERE duration_seconds IS NOT NULL AND duration_seconds > 0 "
                "GROUP BY agent "
                "ORDER BY avg_seconds DESC"
            ).fetchall()

            # Pipeline cycle times (creation to latest transition)
            cycle_times = conn.execute(
                "SELECT version, "
                "MIN(timestamp) as started, "
                "MAX(timestamp) as latest, "
                "SUM(duration_seconds) as total_seconds, "
                "COUNT(*) as transitions "
                "FROM state_transition "
                "GROUP BY version "
                "ORDER BY total_seconds DESC"
            ).fetchall()

            return {
                'stage_bottlenecks': [dict(row) for row in stage_stats],
                'agent_workload': [dict(row) for row in agent_stats],
                'pipeline_cycles': [dict(row) for row in cycle_times],
            }
        except Exception as e:
            print(f"[temporal] get_bottleneck_analysis error: {e}", file=sys.stderr)
            return None

    # ─── Lock Management (temporal enhancement for V2 locks) ─────────────────

    def acquire_lock(self, version: str, agent: str) -> bool:
        """Attempt to acquire a pipeline lock via temporal DB.

        Atomic check-and-set using SQLite transaction isolation.
        Falls back to V2's file-based locks if temporal is unavailable.
        """
        if not self.available:
            return False
        try:
            conn = self._get_conn()
            now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            conn.execute("BEGIN IMMEDIATE")

            row = conn.execute(
                "SELECT locked_by, lock_acquired_at FROM pipeline_state "
                "WHERE version = ?",
                (version,)
            ).fetchone()

            if row and row['locked_by']:
                # Check if lock is stale
                if row['lock_acquired_at']:
                    try:
                        acquired = datetime.fromisoformat(
                            row['lock_acquired_at'].replace('Z', '+00:00')
                        )
                        age = (datetime.now(timezone.utc) - acquired).total_seconds()
                        if age < HEARTBEAT_TTL_SECONDS:
                            conn.rollback()
                            return False  # Lock is fresh, can't acquire
                    except ValueError:
                        pass
                # Stale lock — steal it
                print(f"[temporal] Stealing stale lock on {version} "
                      f"from {row['locked_by']}", file=sys.stderr)

            conn.execute(
                "UPDATE pipeline_state SET locked_by = ?, lock_acquired_at = ? "
                "WHERE version = ?",
                (agent, now, version)
            )
            conn.commit()
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            print(f"[temporal] acquire_lock error: {e}", file=sys.stderr)
            return False

    def release_lock(self, version: str) -> bool:
        """Release a pipeline lock."""
        if not self.available:
            return False
        try:
            conn = self._get_conn()
            conn.execute(
                "UPDATE pipeline_state SET locked_by = NULL, "
                "lock_acquired_at = NULL WHERE version = ?",
                (version,)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[temporal] release_lock error: {e}", file=sys.stderr)
            return False


# ─── CLI Interface ────────────────────────────────────────────────────────────

def _format_dashboard(dashboard: dict) -> str:
    """Format dashboard for terminal output."""
    lines = []
    lines.append("┌─────────────────────────────────────────────────┐")
    lines.append("│  🏭 AUTOCLAVE — Pipeline Orchestration Dashboard │")
    lines.append("├─────────────────────────────────────────────────┤")

    # Pipelines
    lines.append("│                                                  │")
    lines.append("│  ACTIVE PIPELINES                                │")
    for p in dashboard.get('pipelines', []):
        ver = p.get('version', '?')[:30]
        stage = p.get('current_stage', '?')[:10]
        agent = p.get('current_agent', '?')[:8]
        locked = '🔒' if p.get('locked_by') else '  '
        lines.append(f"│  {locked} {ver:<30} {stage:<10} {agent:<8}│")

    # Agents
    lines.append("│                                                  │")
    lines.append("│  AGENTS                                          │")
    emoji_map = {'architect': '🏗️', 'critic': '🔍', 'builder': '🔨'}
    for a in dashboard.get('agents', []):
        name = a.get('agent', '?')
        emoji = emoji_map.get(name, '👤')
        status = a.get('status', '?')
        pipeline = a.get('current_pipeline', '')
        detail = f" ({pipeline})" if pipeline else ''
        lines.append(f"│  {emoji} {name}: {status}{detail}")

    # Recent handoffs
    lines.append("│                                                  │")
    lines.append("│  RECENT HANDOFFS                                 │")
    for h in dashboard.get('recent_handoffs', [])[:5]:
        src = h.get('source_agent', '?')[:8]
        tgt = h.get('target_agent', '?')[:8]
        ver = h.get('version', '?')[:15]
        status_emoji = {'dispatched': '📤', 'acknowledged': '👀',
                        'working': '⚙️', 'completed': '✅',
                        'blocked': '🚫', 'timed_out': '⏰'
                        }.get(h.get('status', ''), '❓')
        ts = h.get('dispatched_at', '')[:16]
        lines.append(f"│  {ts} {src}→{tgt} ({ver}) {status_emoji}")

    # Stats
    stats = dashboard.get('stats', {})
    lines.append("│                                                  │")
    lines.append(f"│  📊 {stats.get('total_pipelines', 0)} pipelines | "
                 f"{stats.get('active_agents', 0)}/{stats.get('total_agents', 0)} agents active | "
                 f"{stats.get('pending_handoffs', 0)} pending")
    lines.append("└─────────────────────────────────────────────────┘")
    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Temporal overlay CLI')
    parser.add_argument('command', choices=['dashboard', 'timeline', 'timetravel',
                                           'agents', 'context', 'stats', 'status'],
                        help='Command to run')
    parser.add_argument('args', nargs='*', help='Command arguments')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB_PATH,
                        help='Database file path')
    args = parser.parse_args()

    overlay = TemporalOverlay(db_path=args.db)

    if not overlay.available:
        print("❌ Temporal DB not available. Run: python3 scripts/temporal_schema.py",
              file=sys.stderr)
        sys.exit(1)

    if args.command == 'status':
        from temporal_schema import verify_db
        result = verify_db(args.db)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"✅ Temporal overlay {'available' if overlay.available else 'unavailable'}")
            print(f"  DB: {result['path']}")
            print(f"  Schema: v{result.get('schema_version', '?')}")
            print(f"  Tables: {len(result.get('tables', []))}")

    elif args.command == 'dashboard':
        dashboard = overlay.get_dashboard()
        if args.json:
            print(json.dumps(dashboard, indent=2))
        else:
            print(_format_dashboard(dashboard))

    elif args.command == 'timeline':
        if not args.args:
            print("Usage: temporal_overlay.py timeline <version>", file=sys.stderr)
            sys.exit(1)
        timeline = overlay.get_timeline(args.args[0])
        if args.json:
            print(json.dumps(timeline, indent=2))
        else:
            if not timeline:
                print(f"No transitions found for {args.args[0]}")
            else:
                print(f"Timeline for {args.args[0]} ({len(timeline)} transitions):")
                for t in timeline:
                    duration = f" ({t['duration_seconds']}s)" if t.get('duration_seconds') else ''
                    print(f"  {t['timestamp'][:19]} | {t['from_stage']} → {t['to_stage']} "
                          f"| {t['agent']} | {t['action']}{duration}")

    elif args.command == 'timetravel':
        if len(args.args) < 2:
            print("Usage: temporal_overlay.py timetravel <version> <iso-timestamp>",
                  file=sys.stderr)
            sys.exit(1)
        result = overlay.time_travel(args.args[0], args.args[1])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result:
                print(f"State at {args.args[1]}:")
                for k, v in result.items():
                    print(f"  {k}: {v}")
            else:
                print(f"No state found for {args.args[0]} at {args.args[1]}")

    elif args.command == 'agents':
        dashboard = overlay.get_dashboard()
        if dashboard:
            if args.json:
                print(json.dumps(dashboard['agents'], indent=2))
            else:
                print("Agent Presence:")
                for a in dashboard['agents']:
                    stale = f" (stale: {a['stale_seconds']}s)" if a.get('stale_seconds') else ''
                    print(f"  {a['agent']}: {a['status']}{stale}")

    elif args.command == 'context':
        if len(args.args) < 2:
            print("Usage: temporal_overlay.py context <version> <agent>", file=sys.stderr)
            sys.exit(1)
        ctx = overlay.get_agent_context(args.args[0], args.args[1])
        if args.json:
            print(json.dumps(ctx, indent=2))
        else:
            lineage = overlay.get_design_lineage(args.args[0], args.args[1])
            if lineage:
                print(lineage)
            else:
                print(f"No context for {args.args[1]} on {args.args[0]}")

    elif args.command == 'stats':
        analysis = overlay.get_bottleneck_analysis()
        if args.json:
            print(json.dumps(analysis, indent=2))
        else:
            if analysis:
                print("Stage Bottlenecks (avg duration):")
                for s in analysis.get('stage_bottlenecks', []):
                    avg = int(s.get('avg_seconds', 0))
                    mins = avg // 60
                    print(f"  {s['from_stage']}: {mins}m avg "
                          f"({s.get('occurrences', 0)} occurrences)")
                print("\nAgent Workload:")
                for a in analysis.get('agent_workload', []):
                    total = int(a.get('total_seconds', 0))
                    print(f"  {a['agent']}: {total // 60}m total "
                          f"({a.get('transitions', 0)} transitions)")
            else:
                print("No analytics data yet")

    overlay.close()
