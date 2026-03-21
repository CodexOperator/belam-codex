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

Phase 1 Critic FLAGs (all resolved):
  FLAG-1 (MED): SQL injection → All queries use parameterized placeholders (?)
  FLAG-2 (MED): Reducer mismatch → Split into log_transition() + advance_pipeline()
  FLAG-3 (MED): agent_context backup → SQLite DB IS on filesystem; auto-backed up
  FLAG-4 (LOW): merge_json → Deep merge: objects recursive, arrays concatenated, primitives overwrite
  FLAG-5 (LOW): Agent presence TTL → Python-side check in get_dashboard()
  FLAG-6 (LOW): Reconciliation scope → Documented as pipeline_state only; others noted

Phase 2 features:
  R1: F-label/R-label causal coupling via time_travel_revert()
      - State-level revert with F-labels (⮌ format) and R-label hints
      - Critic Phase 2 FLAG-1 (MED): time_travel() returns transition not state
        → handled by using to_stage as target state
  R2: Persona-filtered dashboard views
      - get_dashboard(persona=) for filtered views
      - format_dashboard_for_prompt() for dispatch injection
      - PERSONA_STAGE_FILTERS config per agent role
  FLAG-1: record_transition() dead code removed
  FLAG-2: _format_dashboard() dynamic column widths

Usage (standalone):
    python3 scripts/temporal_overlay.py dashboard                  # Full dashboard
    python3 scripts/temporal_overlay.py dashboard --persona builder # Filtered view
    python3 scripts/temporal_overlay.py timeline <version>         # Pipeline timeline
    python3 scripts/temporal_overlay.py timetravel <ver> <iso-ts>  # Read-only query
    python3 scripts/temporal_overlay.py revert <ver> <iso-ts>      # State-level revert
    python3 scripts/temporal_overlay.py agents                     # Agent presence
    python3 scripts/temporal_overlay.py context <ver> <agent>      # Agent context
    python3 scripts/temporal_overlay.py stats                      # Duration analytics
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


# ─── Persona Stage Filters (Phase 2 R2) ─────────────────────────────────────────

PERSONA_STAGE_FILTERS = {
    'architect': {
        'show_stages': [
            'architect_design', 'architect_design_revision',
            'phase1_complete', 'phase2_architect_design', 'phase2_architect_revision',
            'phase2_complete', 'analysis_architect_design',
            # Cross-phase visibility (Critic Phase 2 FLAG-2): architect needs to see
            # builder output when reviewing Phase 2 completeness, plus critic reviews.
            'critic_design_review', 'critic_code_review',
            'builder_implementation', 'phase2_builder_implementation',
        ],
        'show_sections': ['pipelines', 'agents', 'recent_handoffs', 'stats', 'bottleneck_analysis'],
        'highlight_fields': ['design_decisions', 'open_questions', 'critic_flags'],
    },
    'critic': {
        'show_stages': [
            'critic_design_review', 'critic_code_review',
            'phase2_critic_design_review', 'phase2_critic_code_review',
            'analysis_critic_review', 'local_analysis_critic_review',
            # Cross-phase visibility (Critic Phase 2 FLAG-2): critic reviews builder
            # output and should see what stage is pending review.
            'builder_implementation', 'phase2_builder_implementation',
        ],
        'show_sections': ['pipelines', 'recent_handoffs', 'stats'],
        'highlight_fields': ['critic_flags', 'checklist', 'flag_resolutions'],
    },
    'builder': {
        'show_stages': [
            'builder_implementation', 'builder_apply_blocks',
            'phase2_builder_implementation',
            'analysis_builder_implementation', 'local_analysis_builder',
        ],
        'show_sections': ['pipelines', 'stats'],
        'highlight_fields': ['files_to_modify', 'partial_work', 'test_checklist'],
    },
}


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

    # record_transition() REMOVED — Phase 2 FLAG-1 fix.
    # Was dead code with broken atomicity: sub-methods each called conn.commit(),
    # breaking the outer BEGIN IMMEDIATE transaction. V2 integration calls
    # log_transition() + advance_pipeline() + create_handoff() individually
    # via _post_state_change(). See Critic code review FLAG-1 (MED).

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

    # ─── Autoclave Dashboard (Phase 2 R2: persona-filtered views) ────────────

    def get_dashboard(self, persona: str = None) -> Optional[dict]:
        """Get autoclave dashboard — optionally filtered by persona.

        Phase 2 R2: When persona is None, returns full unfiltered dashboard
        (for Shael / coordinator). When persona is set, returns a filtered
        view showing only persona-relevant state.

        Global coordinates are NEVER remapped — filtering only hides
        irrelevant rows (design decision D4).

        Returns:
          {
            "pipelines": [...],
            "agents": [...],          # With TTL applied (FLAG-5)
            "recent_handoffs": [...],
            "stats": { ... },
            "persona": str|None,      # Active persona filter
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

            # Compute stats (always full, unfiltered)
            active_agents = sum(1 for a in agents
                                if a.get('status') not in ('idle', 'offline (stale)'))

            dashboard = {
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
                'persona': persona,
            }

            # Apply persona filter if specified (R2)
            if persona and persona in PERSONA_STAGE_FILTERS:
                dashboard = self._apply_persona_filter(dashboard, persona)

            return dashboard
        except Exception as e:
            print(f"[temporal] get_dashboard error: {e}", file=sys.stderr)
            return None

    def _apply_persona_filter(self, dashboard: dict, persona: str) -> dict:
        """Apply persona-based filtering to dashboard data.

        Filtering is ADDITIVE HIDING, not coordinate remapping (D4).
        Pipelines are all shown but marked as active_for_persona or not.
        Handoffs are filtered to those involving this persona's agent.
        Sections are filtered per persona config.
        """
        pf = PERSONA_STAGE_FILTERS.get(persona, {})
        show_stages = set(pf.get('show_stages', []))
        show_sections = set(pf.get('show_sections', []))

        # Mark pipelines as active for this persona
        for p in dashboard['pipelines']:
            stage = p.get('current_stage', '')
            p['active_for_persona'] = stage in show_stages

        # Filter handoffs to those involving this persona
        dashboard['recent_handoffs'] = [
            h for h in dashboard['recent_handoffs']
            if h.get('source_agent') == persona or h.get('target_agent') == persona
        ]

        # Filter sections
        if 'agents' not in show_sections:
            dashboard['agents'] = []
        if 'recent_handoffs' not in show_sections:
            dashboard['recent_handoffs'] = []
        if 'stats' not in show_sections:
            dashboard['stats'] = {}

        # Add persona metadata
        dashboard['highlight_fields'] = pf.get('highlight_fields', [])

        return dashboard

    def format_dashboard_for_prompt(self, persona: str = None,
                                    max_lines: int = 80) -> Optional[str]:
        """Render dashboard as text for task prompt injection (Phase 2 R2).

        Returns formatted string suitable for inclusion in dispatch payload.
        Uses persona-specific highlighting when persona is set.
        Orchestration sets the view, agents don't choose (D5).

        Args:
            persona: Filter by persona ('architect', 'critic', 'builder', or None)
            max_lines: Cap output at this many lines (Critic Q3: prevent context bloat)
        """
        dashboard = self.get_dashboard(persona=persona)
        if not dashboard:
            return None

        emoji_map = {'architect': '🏗️', 'critic': '🔍', 'builder': '🔨'}
        lines = []

        if persona:
            emoji = emoji_map.get(persona, '👤')
            lines.append(f"### {emoji} Autoclave Dashboard — {persona.title()} View")
        else:
            lines.append("### 🏭 Autoclave Dashboard — Full View")

        # Pipelines
        lines.append("\n**Pipelines:**")
        for p in dashboard.get('pipelines', []):
            ver = p.get('version', '?')
            stage = p.get('current_stage', '?')
            agent = p.get('current_agent', '?')
            locked = '🔒' if p.get('locked_by') else ''

            # Persona-specific highlighting
            if persona and p.get('active_for_persona'):
                lines.append(f"  **→ {ver}** | stage: `{stage}` | agent: {agent} {locked}")
            else:
                lines.append(f"  · {ver} | stage: `{stage}` | agent: {agent} {locked}")

        # Agents (if shown)
        if dashboard.get('agents'):
            lines.append("\n**Agents:**")
            for a in dashboard['agents']:
                name = a.get('agent', '?')
                emoji = emoji_map.get(name, '👤')
                status = a.get('status', '?')
                pipeline = a.get('current_pipeline', '')
                stale = f" (stale {a['stale_seconds']}s)" if a.get('stale_seconds') else ''
                detail = f" on {pipeline}" if pipeline else ''
                lines.append(f"  {emoji} {name}: {status}{detail}{stale}")

        # Recent handoffs (if shown)
        if dashboard.get('recent_handoffs'):
            lines.append("\n**Recent Handoffs:**")
            status_emoji = {
                'dispatched': '📤', 'acknowledged': '👀',
                'working': '⚙️', 'completed': '✅',
                'blocked': '🚫', 'timed_out': '⏰',
            }
            for h in dashboard['recent_handoffs'][:5]:
                src = h.get('source_agent', '?')
                tgt = h.get('target_agent', '?')
                ver = h.get('version', '?')
                se = status_emoji.get(h.get('status', ''), '❓')
                ts = h.get('dispatched_at', '')[:16]
                lines.append(f"  {ts} {src} → {tgt} ({ver}) {se}")

        # Stats (if shown)
        stats = dashboard.get('stats', {})
        if stats:
            lines.append(f"\n📊 {stats.get('total_pipelines', 0)} pipelines | "
                         f"{stats.get('active_agents', 0)}/{stats.get('total_agents', 0)} "
                         f"agents active | {stats.get('pending_handoffs', 0)} pending")

        # Cap at max_lines to prevent context bloat (Critic Q3)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines.append(f"\n... (truncated to {max_lines} lines)")

        return '\n'.join(lines)

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

    # ─── Time-Travel Revert (Phase 2 R1: F-label/R-label causal coupling) ───

    def time_travel_revert(self, version: str, target_timestamp: str) -> Optional[dict]:
        """Revert pipeline state to a past timestamp.

        This is the WRITE counterpart to time_travel() (which is read-only).
        Implements Phase 2 R1: F-label/R-label causal coupling.

        1. Queries state at target_timestamp via time_travel()
           NOTE (Critic Phase 2 FLAG-1 MED): time_travel() returns a TRANSITION
           record, not a state snapshot. The 'to_stage' field IS the state
           at that timestamp (the stage the pipeline transitioned INTO).
        2. Reads current state from pipeline_state table
        3. Computes diff between current and target state
        4. Applies filesystem revert (_state.json, pipeline markdown)
        5. Logs a revert transition (action='revert') in temporal DB
        6. Returns RevertResult dict with F-labels (⮌) and R-label hints

        Returns None on failure (graceful degradation).
        State-level revert only — does NOT revert file contents (V3 concern).
        """
        if not self.available:
            return None
        try:
            # 1. Get target state via time_travel (returns transition, not state)
            target_transition = self.time_travel(version, target_timestamp)
            if not target_transition:
                print(f"[temporal] revert: no state found for {version} at {target_timestamp}",
                      file=sys.stderr)
                return None

            # The state AT the target timestamp is the to_stage of the last transition
            target_stage = target_transition.get('to_stage', '')
            target_agent = target_transition.get('agent', '')

            # 2. Get current state from pipeline_state table
            conn = self._get_conn()
            current_row = conn.execute(
                "SELECT current_stage, current_agent, status FROM pipeline_state "
                "WHERE version = ?",
                (version,)
            ).fetchone()
            if not current_row:
                print(f"[temporal] revert: no current state for {version}", file=sys.stderr)
                return None

            current_stage = current_row['current_stage']
            current_agent = current_row['current_agent']

            # 3. Check for no-op (current == target)
            if current_stage == target_stage:
                return {
                    'success': True,
                    'version': version,
                    'reverted_from': current_stage,
                    'reverted_to': target_stage,
                    'target_timestamp': target_timestamp,
                    'f_labels': [],
                    'affected_coords': [],
                    'r_label_hint': {},
                    'transition_id': None,
                    'noop': True,
                }

            # 4. Compute F-labels for the revert (using ⮌ not Δ)
            f_labels = []
            coord = self._get_pipeline_coord_safe(version)
            f_labels.append(f"⮌ {coord}.stage {current_stage} → {target_stage}")
            if current_agent != target_agent:
                f_labels.append(f"⮌ {coord}.agent {current_agent} → {target_agent}")

            # 5. Apply filesystem revert
            fs_success = self._apply_filesystem_revert(
                version, target_stage, target_agent, current_stage
            )

            # 6. Log the revert transition in temporal DB
            self.log_transition(
                version=version,
                from_stage=current_stage,
                to_stage=target_stage,
                agent='system',
                action='revert',
                notes=f"Time-travel revert to {target_timestamp}. "
                      f"Reverted {current_stage} → {target_stage}",
            )

            # 7. Advance pipeline state back to target
            self.advance_pipeline(version, target_stage, target_agent)

            # 8. Build R-label hint for cockpit re-render
            r_label_hint = {
                'affected_coords': [coord],
                'sections': ['pipelines'],
                'reason': 'time_travel_revert',
                'timestamp': target_timestamp,
                'reverted_from': current_stage,
                'reverted_to': target_stage,
            }

            # Get the transition_id of the revert we just logged
            last_transition = conn.execute(
                "SELECT id FROM state_transition WHERE version = ? "
                "AND action = 'revert' ORDER BY id DESC LIMIT 1",
                (version,)
            ).fetchone()
            transition_id = last_transition['id'] if last_transition else None

            return {
                'success': True,
                'version': version,
                'reverted_from': current_stage,
                'reverted_to': target_stage,
                'target_timestamp': target_timestamp,
                'f_labels': f_labels,
                'affected_coords': [coord],
                'r_label_hint': r_label_hint,
                'transition_id': transition_id,
                'filesystem_reverted': fs_success,
            }

        except Exception as e:
            print(f"[temporal] time_travel_revert error: {e}", file=sys.stderr)
            return None

    def _get_pipeline_coord_safe(self, version: str) -> str:
        """Get p-coordinate for a pipeline, with fallback."""
        try:
            # Try to use the engine's coord function if available
            from orchestration_engine import _get_pipeline_coord
            return _get_pipeline_coord(version)
        except (ImportError, Exception):
            return f'p({version[:20]})'

    def _apply_filesystem_revert(self, version: str, target_stage: str,
                                  target_agent: str, current_stage: str) -> bool:
        """Apply state-level revert to filesystem artifacts.

        Reverts _state.json and pipeline markdown to reflect the target stage.
        Does NOT revert file contents (git-level revert is a V3 concern).
        """
        try:
            # Update _state.json
            builds_dir = self.workspace / 'machinelearning' / 'snn_applied_finance' / \
                         'research' / 'pipeline_builds'
            state_file = builds_dir / f'{version}_state.json'

            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)

                # Update pending_action to target stage
                state['pending_action'] = target_stage
                state['current_agent'] = target_agent
                state['last_updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')

                # Add revert marker
                if 'reverts' not in state:
                    state['reverts'] = []
                state['reverts'].append({
                    'from_stage': current_stage,
                    'to_stage': target_stage,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                })

                with open(state_file, 'w') as f:
                    json.dump(state, f, indent=4)

            # Update pipeline markdown (add revert entry to stage history)
            pipelines_dir = self.workspace / 'pipelines'
            md_file = pipelines_dir / f'{version}.md'
            if md_file.exists():
                with open(md_file, 'r') as f:
                    content = f.read()

                now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                revert_entry = (
                    f"   ⮌ {target_stage:<30} {now}   system"
                    f"{'':>20}Reverted from {current_stage}\n"
                )

                # Append to the end of the file
                with open(md_file, 'a') as f:
                    f.write(revert_entry)

            return True
        except Exception as e:
            print(f"[temporal] filesystem revert error: {e}", file=sys.stderr)
            return False

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
    """Format dashboard for terminal output.

    Phase 2 FLAG-2 fix: dynamic column widths based on actual content,
    with max caps to prevent overflow.
    """
    lines = []

    # Compute dynamic column widths for pipelines (FLAG-2 fix)
    pipelines = dashboard.get('pipelines', [])
    MAX_VER_WIDTH = 40
    MAX_STAGE_WIDTH = 30
    MAX_AGENT_WIDTH = 12
    ver_width = min(MAX_VER_WIDTH, max((len(p.get('version', '?')) for p in pipelines), default=10))
    stage_width = min(MAX_STAGE_WIDTH, max((len(p.get('current_stage', '?')) for p in pipelines), default=10))
    agent_width = min(MAX_AGENT_WIDTH, max((len(p.get('current_agent', '?')) for p in pipelines), default=8))

    # Header
    total_width = ver_width + stage_width + agent_width + 12  # padding
    total_width = max(total_width, 50)

    persona = dashboard.get('persona')
    emoji_map = {'architect': '🏗️', 'critic': '🔍', 'builder': '🔨'}

    if persona:
        title = f"  {emoji_map.get(persona, '👤')} AUTOCLAVE — {persona.title()} View"
    else:
        title = "  🏭 AUTOCLAVE — Pipeline Orchestration Dashboard"

    lines.append(f"┌{'─' * total_width}┐")
    lines.append(f"│{title:<{total_width}}│")
    lines.append(f"├{'─' * total_width}┤")

    # Pipelines
    lines.append(f"│{'':^{total_width}}│")
    lines.append(f"│{'  ACTIVE PIPELINES':<{total_width}}│")
    for p in pipelines:
        ver = p.get('version', '?')[:MAX_VER_WIDTH]
        stage = p.get('current_stage', '?')[:MAX_STAGE_WIDTH]
        agent = p.get('current_agent', '?')[:MAX_AGENT_WIDTH]
        locked = '🔒' if p.get('locked_by') else '  '
        active_marker = '→' if p.get('active_for_persona') else ' '
        row = f"  {locked}{active_marker}{ver:<{ver_width}} {stage:<{stage_width}} {agent:<{agent_width}}"
        lines.append(f"│{row:<{total_width}}│")

    # Agents
    agents = dashboard.get('agents', [])
    if agents:
        lines.append(f"│{'':^{total_width}}│")
        lines.append(f"│{'  AGENTS':<{total_width}}│")
        for a in agents:
            name = a.get('agent', '?')
            emoji = emoji_map.get(name, '👤')
            status = a.get('status', '?')
            pipeline = a.get('current_pipeline', '')
            stale = f" (stale {a['stale_seconds']}s)" if a.get('stale_seconds') else ''
            detail = f" ({pipeline})" if pipeline else ''
            row = f"  {emoji} {name}: {status}{detail}{stale}"
            lines.append(f"│{row:<{total_width}}│")

    # Recent handoffs
    handoffs = dashboard.get('recent_handoffs', [])
    if handoffs:
        lines.append(f"│{'':^{total_width}}│")
        lines.append(f"│{'  RECENT HANDOFFS':<{total_width}}│")
        status_emoji_map = {
            'dispatched': '📤', 'acknowledged': '👀',
            'working': '⚙️', 'completed': '✅',
            'blocked': '🚫', 'timed_out': '⏰',
        }
        for h in handoffs[:5]:
            src = h.get('source_agent', '?')
            tgt = h.get('target_agent', '?')
            ver = h.get('version', '?')
            se = status_emoji_map.get(h.get('status', ''), '❓')
            ts = h.get('dispatched_at', '')[:16]
            row = f"  {ts} {src}→{tgt} ({ver}) {se}"
            lines.append(f"│{row:<{total_width}}│")

    # Stats
    stats = dashboard.get('stats', {})
    if stats:
        lines.append(f"│{'':^{total_width}}│")
        stat_line = (f"  📊 {stats.get('total_pipelines', 0)} pipelines | "
                     f"{stats.get('active_agents', 0)}/{stats.get('total_agents', 0)} agents active | "
                     f"{stats.get('pending_handoffs', 0)} pending")
        lines.append(f"│{stat_line:<{total_width}}│")

    lines.append(f"└{'─' * total_width}┘")
    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Temporal overlay CLI')
    parser.add_argument('command', choices=['dashboard', 'timeline', 'timetravel',
                                           'revert', 'agents', 'context', 'stats',
                                           'status'],
                        help='Command to run')
    parser.add_argument('args', nargs='*', help='Command arguments')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--persona', choices=['architect', 'critic', 'builder'],
                        help='Persona filter for dashboard (Phase 2 R2)')
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
        # Phase 2 R2: persona-filtered dashboard
        persona = args.persona
        dashboard = overlay.get_dashboard(persona=persona)
        if args.json:
            print(json.dumps(dashboard, indent=2))
        else:
            # Use prompt format if persona, terminal format otherwise
            if persona:
                prompt_view = overlay.format_dashboard_for_prompt(persona=persona)
                if prompt_view:
                    print(prompt_view)
                else:
                    print(_format_dashboard(dashboard))
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
                    action_marker = '⮌' if t.get('action') == 'revert' else '→'
                    print(f"  {t['timestamp'][:19]} | {t['from_stage']} {action_marker} "
                          f"{t['to_stage']} | {t['agent']} | {t['action']}{duration}")

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

    elif args.command == 'revert':
        # Phase 2 R1: time-travel revert
        if len(args.args) < 2:
            print("Usage: temporal_overlay.py revert <version> <iso-timestamp>",
                  file=sys.stderr)
            sys.exit(1)
        result = overlay.time_travel_revert(args.args[0], args.args[1])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result:
                if result.get('noop'):
                    print(f"⚪ No-op: {args.args[0]} already at target state "
                          f"({result['reverted_to']})")
                else:
                    print(f"⮌ Reverted {args.args[0]}: "
                          f"{result['reverted_from']} → {result['reverted_to']}")
                    for fl in result.get('f_labels', []):
                        print(f"  {fl}")
                    if result.get('r_label_hint'):
                        print(f"  R-label hint: re-render {result['r_label_hint'].get('affected_coords', [])}")
                    if not result.get('filesystem_reverted'):
                        print("  ⚠️ Filesystem revert failed (temporal DB updated only)")
            else:
                print(f"❌ Revert failed for {args.args[0]} at {args.args[1]}")

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
