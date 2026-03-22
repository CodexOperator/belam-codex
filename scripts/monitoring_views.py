#!/usr/bin/env python3
"""
monitoring_views.py — View registry and renderers for .v namespace

Part of Orchestration V3: Real-Time Monitoring Suite.

Provides:
  - VIEW_REGISTRY (dict): authoritative source of truth for view types (FLAG-2)
  - parse_view_coord(): parse .v coordinate suffixes
  - resolve_view(): resolve a full .v coordinate to rendered content
  - render_turn_by_turn() (.v1): snapshot dashboard per agent turn
  - render_live_diff() (.v2): diffs between agent turns
  - render_timeline() (.v3): stage progression with durations and bottlenecks
  - render_agent_context() (.v4): decisions, flags, learnings
  - render_r_label_trail() (.v5): real-time R-label narrative (Phase 2)
  - list_views(): list available view types
  - RenderClient: thin UDS client for render engine queries (Phase 2)
  - compute_f_r_causal_chain(): F-label → R-label mapping for revert preview

FLAG-2 (MED) addressed: VIEW_REGISTRY dict is the single authoritative source of
truth for view types. Each entry includes metadata (name, description) alongside the
renderer. The view_config DB table is optional persistence for external tooling
(MCP in t4) — list_views() reads from VIEW_REGISTRY, not the DB.

Usage:
    python3 scripts/monitoring_views.py list                  # list view types
    python3 scripts/monitoring_views.py render v1 [pipeline]  # render a view
    python3 scripts/monitoring_views.py render v3 <pipeline>  # timeline
    python3 scripts/monitoring_views.py parse "e0p3.v2"       # test coordinate parsing
"""

import json
import os
import re
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Callable, Any

import socket as _socket

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
DEFAULT_DB_PATH = WORKSPACE / 'data' / 'temporal.db'


# ─── RenderClient (Phase 2: thin UDS client for render engine queries) ────────

class RenderClient:
    """Thin UDS client for monitoring views to query the render engine.

    Single-shot queries: connect → send JSON-line → read JSON-line → close.
    Graceful: returns None if engine not running. All methods are safe to
    call regardless of render engine availability.
    """

    SOCKET = Path.home() / '.belam_render.sock'

    def __init__(self, timeout: float = 2.0):
        self._timeout = timeout

    def query(self, cmd: str, **kwargs) -> dict | None:
        """Single-shot UDS query. Returns response dict or None."""
        if not self.SOCKET.exists():
            return None
        try:
            s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            s.settimeout(self._timeout)
            s.connect(str(self.SOCKET))
            msg = json.dumps({"cmd": cmd, **kwargs}) + '\n'
            s.sendall(msg.encode('utf-8'))
            resp = b''
            while b'\n' not in resp:
                chunk = s.recv(65536)
                if not chunk:
                    break
                resp += chunk
            s.close()
            if resp:
                return json.loads(resp.split(b'\n', 1)[0])
        except Exception:
            pass
        return None

    def get_tree_node(self, coord: str) -> dict | None:
        """Get a single primitive node from RAM tree."""
        resp = self.query('tree', coord=coord)
        if resp and resp.get('ok'):
            return resp.get('node')
        return None

    def get_namespace(self, prefix: str) -> list[dict]:
        """Get all nodes in a namespace from RAM tree."""
        resp = self.query('tree', prefix=prefix)
        return resp.get('nodes', []) if resp and resp.get('ok') else []

    def get_diff_since(self, timestamp: float) -> str:
        """Get render diffs since timestamp as Δ/+/− formatted text."""
        resp = self.query('diff_since', timestamp=timestamp)
        return resp.get('delta', '') if resp and resp.get('ok') else ''

    def get_diffs_structured(self, timestamp: float) -> list[dict]:
        """Get render diffs since timestamp as structured data.

        Falls back to parsing the delta text if structured endpoint not available.
        Used by compute_f_r_causal_chain for structured diff analysis (FLAG-3).
        """
        # Try structured query first (future render engine enhancement)
        resp = self.query('diff_since_structured', timestamp=timestamp)
        if resp and resp.get('ok') and 'entries' in resp:
            return resp['entries']
        # Fallback: parse the Δ/+/− text format
        delta_text = self.get_diff_since(timestamp)
        return self._parse_delta_text(delta_text) if delta_text else []

    def _parse_delta_text(self, text: str) -> list[dict]:
        """Parse Δ/+/− formatted diff text into structured entries."""
        entries = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            entry = {'raw': line}
            if line.startswith('Δ '):
                entry['type'] = 'change'
                parts = line[2:].split(None, 1)
                if parts:
                    entry['coord'] = parts[0]
                    entry['detail'] = parts[1] if len(parts) > 1 else ''
            elif line.startswith('+ '):
                entry['type'] = 'add'
                entry['coord'] = line[2:].split(None, 1)[0] if len(line) > 2 else ''
            elif line.startswith('− ') or line.startswith('- '):
                entry['type'] = 'remove'
                entry['coord'] = line[2:].split(None, 1)[0] if len(line) > 2 else ''
            else:
                entry['type'] = 'unknown'
            entries.append(entry)
        return entries

    def get_supermap(self) -> str:
        """Get current supermap from RAM."""
        resp = self.query('supermap')
        return resp.get('content', '') if resp and resp.get('ok') else ''

    def is_available(self) -> bool:
        """Check if render engine is running."""
        return self.SOCKET.exists()


# ─── Types ───────────────────────────────────────────────────────────────────────

@dataclass
class ViewResult:
    """Result of resolving and rendering a .v coordinate."""
    view_type: int                       # 1-4
    view_name: str                       # "turn-by-turn", "live-diff", etc.
    pipeline: Optional[str]              # Version string or None (global)
    persona: Optional[str]               # Persona filter or None
    content: str                         # Rendered text output
    generated_at: str = ''               # ISO timestamp

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()


@dataclass
class ViewEntry:
    """Registry entry for a view type (FLAG-2: authoritative metadata lives here)."""
    number: int
    name: str
    description: str
    renderer: Callable  # function(pipeline, persona, overlay) -> str


def _get_overlay():
    """Lazy-load TemporalOverlay with graceful degradation."""
    try:
        from temporal_overlay import TemporalOverlay
        overlay = TemporalOverlay(workspace=WORKSPACE)
        if overlay.available:
            return overlay
    except ImportError:
        pass
    return None


# ─── Coordinate Parsing ─────────────────────────────────────────────────────────

# Patterns:
#   e0p3.v2  → pipeline_ref='p3', view_type=2
#   e0v1     → pipeline_ref=None, view_type=1
#   e0.v     → pipeline_ref=None, view_type=None  (list views)
#   e0p3     → pipeline_ref='p3', view_type=None  (no view — backward compat)

_VIEW_COORD_RE = re.compile(
    r'^(?:e0)?'              # optional e0 prefix
    r'(p\d+)?'               # optional pipeline ref (p1, p2, ...)
    r'(?:\.v|v)'             # .v or v separator
    r'(\d+)?'                # optional view type number
    r'$'
)

_PIPELINE_ONLY_RE = re.compile(
    r'^(?:e0)?(p\d+)$'      # e0p3 with no view suffix
)


def parse_view_coord(coord: str) -> tuple[Optional[str], Optional[int]]:
    """Parse .v coordinate suffix.

    Returns (pipeline_ref, view_type):
        'e0p3.v2' → ('p3', 2)
        'e0v1'    → (None, 1)
        'e0.v'    → (None, None)
        'e0p3'    → ('p3', None)   # no view suffix — backward compat

    Returns (None, None) for unparseable coordinates.
    """
    coord = coord.strip()

    # Try pipeline-only first (no view suffix)
    m = _PIPELINE_ONLY_RE.match(coord)
    if m:
        return (m.group(1), None)

    # Try view coordinate
    m = _VIEW_COORD_RE.match(coord)
    if m:
        pipeline_ref = m.group(1)  # 'p3' or None
        view_num_str = m.group(2)  # '2' or None
        view_type = int(view_num_str) if view_num_str else None
        return (pipeline_ref, view_type)

    # Handle bare "e0.v" or just ".v"
    if coord in ('e0.v', '.v', 'e0v', 'v'):
        return (None, None)

    return (None, None)


def _resolve_pipeline_ref(pipeline_ref: str) -> Optional[str]:
    """Resolve p-coordinate to version string using orchestration engine."""
    if not pipeline_ref:
        return None
    try:
        from orchestration_engine import resolve_pipeline
        return resolve_pipeline(pipeline_ref)
    except ImportError:
        return None


# ─── View Renderers ──────────────────────────────────────────────────────────────

def render_turn_by_turn(pipeline: str = None, persona: str = None,
                        overlay=None) -> str:
    """v1: Snapshot dashboard for agent context injection.

    When pipeline=None: all active pipelines summary.
    When pipeline set: detailed single-pipeline view.
    Persona filtering applied via overlay.get_dashboard(persona=).
    """
    if overlay is None:
        overlay = _get_overlay()
    if overlay is None:
        return "(Temporal DB unavailable)"

    dashboard = overlay.get_dashboard(persona=persona)
    if not dashboard:
        return "(No dashboard data)"

    lines = []
    if pipeline:
        # Single pipeline mode
        target = None
        for p in dashboard.get('pipelines', []):
            if p.get('version') == pipeline:
                target = p
                break
        if not target:
            return f"Pipeline not found: {pipeline}"

        lines.append(f"📊 Pipeline: {pipeline}")
        lines.append(f"  Stage: {target.get('current_stage', '?')}")
        lines.append(f"  Agent: {target.get('current_agent', '?')}")
        locked = target.get('locked_by')
        if locked:
            lines.append(f"  Lock: 🔒 {locked}")
        lines.append(f"  Updated: {target.get('updated_at', '?')[:19]}")

        # Agent presence for this pipeline
        for a in dashboard.get('agents', []):
            if a.get('current_pipeline') == pipeline:
                stale = f" (stale {a['stale_seconds']}s)" if a.get('stale_seconds') else ''
                lines.append(f"  Agent {a['agent']}: {a['status']}{stale}")

        # Recent handoffs for this pipeline
        handoffs = [h for h in dashboard.get('recent_handoffs', [])
                    if h.get('version') == pipeline]
        if handoffs:
            lines.append(f"  Recent handoffs:")
            for h in handoffs[:3]:
                lines.append(f"    {h.get('source_agent','?')} → {h.get('target_agent','?')} "
                             f"({h.get('status','?')})")
    else:
        # Global mode — all pipelines
        pipelines = dashboard.get('pipelines', [])
        lines.append(f"📊 Active Pipelines ({len(pipelines)})")
        for p in pipelines:
            ver = p.get('version', '?')
            stage = p.get('current_stage', '?')
            agent = p.get('current_agent', '?')
            locked = '🔒' if p.get('locked_by') else ''
            active = '→' if p.get('active_for_persona') else ' '
            lines.append(f"  {active}{ver:<35} {stage:<28} {agent} {locked}")

        # Agent summary
        agents = dashboard.get('agents', [])
        if agents:
            active_count = sum(1 for a in agents
                               if a.get('status') not in ('idle', 'offline (stale)'))
            lines.append(f"\n  Agents: {active_count}/{len(agents)} active")

        # Stats
        stats = dashboard.get('stats', {})
        if stats.get('pending_handoffs'):
            lines.append(f"  Pending handoffs: {stats['pending_handoffs']}")

    return '\n'.join(lines)


def render_live_diff(pipeline: str = None, persona: str = None,
                     overlay=None, since: str = None,
                     render_client: RenderClient = None) -> str:
    """v2: Diffs since last agent turn (or since timestamp).

    Phase 2 FLAG-2 fix: uses overlay.get_transitions_since() public API
    instead of private overlay._get_conn(). When render_client is available,
    enriches output with render engine diffs.
    """
    if overlay is None:
        overlay = _get_overlay()
    if overlay is None:
        return "(Temporal DB unavailable)"

    if not since:
        # Default: last 30 minutes
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        since = cutoff.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    try:
        transitions = overlay.get_transitions_since(since, version=pipeline)
    except Exception as e:
        return f"(Error querying transitions: {e})"

    if not transitions:
        since_display = since[:19] if since else '?'
        return f"No changes since {since_display}"

    lines = [f"Live Diff (since {since[:19]})"]
    lines.append("─" * 50)

    # Group by pipeline
    by_pipeline = {}
    for t in transitions:
        ver = t.get('version', '?')
        if ver not in by_pipeline:
            by_pipeline[ver] = []
        by_pipeline[ver].append(t)

    for ver, trans in by_pipeline.items():
        lines.append(f"\n  {ver}:")
        for t in trans:
            action = t.get('action', '?')
            ts = t.get('timestamp', '?')[:19]

            if action == 'dep_resolved':
                lines.append(f"    {ts} 🔗 {t.get('notes', 'dependency resolved')}")
            elif action == 'revert':
                lines.append(f"    {ts} ⮌ {t.get('from_stage','?')} → {t.get('to_stage','?')}")
            else:
                marker = '→' if action == 'complete' else '⚠' if action == 'block' else '·'
                lines.append(f"    {ts} {marker} {t.get('from_stage','?')} → "
                             f"{t.get('to_stage','?')} ({t.get('agent','?')})")
                if t.get('notes'):
                    note = t['notes'][:80]
                    lines.append(f"              {note}")

    return '\n'.join(lines)


def render_timeline(pipeline: str = None, persona: str = None,
                    overlay=None, at: str = None) -> str:
    """v3: Timeline with stage progression, durations, bottlenecks.

    Uses get_timeline() + get_stage_durations().
    Bottleneck: stage duration > 2× median of all stages.
    Time-travel scrubber: if `at` is set, adds cursor marker.
    """
    if overlay is None:
        overlay = _get_overlay()
    if overlay is None:
        return "(Temporal DB unavailable)"

    if not pipeline:
        return "(Timeline requires a pipeline. Use e0p{N}.v3)"

    timeline = overlay.get_timeline(pipeline)
    if not timeline:
        return f"No timeline data for {pipeline}"

    lines = [f"Timeline: {pipeline}"]
    lines.append("─" * 55)

    # Compute durations between transitions
    durations = []
    for i, t in enumerate(timeline):
        dur = t.get('duration_seconds')
        if dur is not None and dur > 0:
            durations.append(dur)

    median_dur = statistics.median(durations) if durations else 0
    bottleneck_threshold = median_dur * 2 if median_dur > 0 else float('inf')

    # Maximum bar width
    max_dur = max(durations) if durations else 1
    BAR_WIDTH = 20

    total_seconds = 0
    at_marker_placed = False

    for i, t in enumerate(timeline):
        stage = t.get('to_stage', '?')
        ts = t.get('timestamp', '?')[:19]
        dur = t.get('duration_seconds')
        agent = t.get('agent', '?')
        action = t.get('action', '?')

        # Action marker
        if action == 'revert':
            action_icon = '⮌'
        elif action == 'dep_resolved':
            action_icon = '🔗'
        else:
            action_icon = ' '

        if dur is not None and dur > 0:
            total_seconds += dur
            # Duration bar
            bar_len = max(1, int((dur / max_dur) * BAR_WIDTH))
            bar = '█' * bar_len
            dur_str = _format_duration(dur)

            # Bottleneck marker
            bottleneck = ' ⚠ BOTTLENECK' if dur > bottleneck_threshold else ''

            lines.append(f"  {stage:<25} │{bar:<{BAR_WIDTH}}│ {dur_str:>6}  {ts}{bottleneck}")
        else:
            lines.append(f"  {stage:<25} │{'·':<{BAR_WIDTH}}│        {ts}")

        # Time-travel cursor
        if at and not at_marker_placed:
            next_ts = timeline[i + 1].get('timestamp', '') if i + 1 < len(timeline) else None
            if next_ts and at <= next_ts:
                lines.append(f"  {'▼ YOU ARE HERE':^25} │{'':^{BAR_WIDTH}}│")
                at_marker_placed = True

    # If at is after all transitions, place cursor at end
    if at and not at_marker_placed:
        lines.append(f"  {'▼ YOU ARE HERE':^25} │{'':^{BAR_WIDTH}}│")

    lines.append(f"{'':>28}{'':>{BAR_WIDTH}} ───")
    lines.append(f"{'':>28}{'':>{BAR_WIDTH}} {_format_duration(total_seconds)} total")

    return '\n'.join(lines)


def render_agent_context(pipeline: str = None, persona: str = None,
                         overlay=None, agent: str = None) -> str:
    """v4: Agent context — decisions, flags, learnings.

    When agent=None: all agents for the pipeline.
    Uses get_design_lineage() for narrative format.

    FLAG-3 (LOW) addressed: heartbeat_extended() fields (tokens_used,
    decisions_this_turn) are deferred — not wired into .v4 in Phase 1.
    These fields will be consumed when heartbeat_extended is populated
    by agent sessions in a future phase.
    """
    if overlay is None:
        overlay = _get_overlay()
    if overlay is None:
        return "(Temporal DB unavailable)"

    if not pipeline:
        return "(Agent context requires a pipeline. Use e0p{N}.v4)"

    agents_to_show = [agent] if agent else ['architect', 'critic', 'builder']
    lines = [f"Agent Context: {pipeline}"]
    lines.append("─" * 50)

    found_any = False
    for ag in agents_to_show:
        lineage = overlay.get_design_lineage(pipeline, ag)
        if lineage:
            found_any = True
            emoji = {'architect': '🏗️', 'critic': '🔍', 'builder': '🔨'}.get(ag, '👤')
            lines.append(f"\n{emoji} {ag.title()}")
            lines.append(lineage)

    if not found_any:
        lines.append(f"\n  No agent context recorded for {pipeline}")

    return '\n'.join(lines)


def render_r_label_trail(pipeline: str = None, persona: str = None,
                         overlay=None, render_client: RenderClient = None,
                         window_minutes: int = 30) -> str:
    """v5: R-label trail — real-time narrative of script-pilot decisions.

    Shows the render engine's diff stream as a temporal narrative:
    - Each DiffEntry becomes an R-label line
    - Grouped by time window (default 30 min)
    - Pipeline-filterable
    - Shows what changed, when, and (via F-label correlation) why

    When render engine is not available, falls back to DB state transitions
    rendered as an R-label-style narrative.
    """
    lines = []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    cutoff_ts = cutoff.timestamp()

    # Primary: render engine diffs (R-labels from RAM tree changes)
    if render_client is None:
        render_client = RenderClient()

    r_labels = []
    if render_client.is_available():
        delta_text = render_client.get_diff_since(cutoff_ts)
        if delta_text and delta_text.strip():
            for line in delta_text.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                # Filter by pipeline if specified
                if pipeline and pipeline not in line:
                    continue
                r_labels.append(line)

    # Secondary: DB state transitions (F-labels as complementary context)
    f_labels = []
    if overlay is None:
        overlay = _get_overlay()
    if overlay:
        since_iso = cutoff.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        try:
            transitions = overlay.get_transitions_since(since_iso, version=pipeline)
            for t in transitions:
                ts = t.get('timestamp', '?')[:19]
                action = t.get('action', '?')
                from_s = t.get('from_stage', '?')
                to_s = t.get('to_stage', '?')
                agent = t.get('agent', '?')
                notes = t.get('notes', '')

                if action == 'dep_resolved':
                    f_labels.append(f"  F {ts} 🔗 {notes[:60]}")
                elif action == 'revert':
                    f_labels.append(f"  F {ts} ⮌ {from_s} → {to_s}")
                else:
                    marker = '→' if action == 'complete' else '⚠' if action == 'block' else '·'
                    f_labels.append(f"  F {ts} {marker} {from_s} → {to_s} ({agent})")
        except Exception:
            pass

    # Compose trail
    scope = f" [{pipeline}]" if pipeline else ""
    lines.append(f"R-Label Trail{scope} (last {window_minutes}min)")
    lines.append("─" * 55)

    if r_labels:
        lines.append("\n  ── Render Engine (R-labels) ──")
        for rl in r_labels:
            lines.append(f"  R {rl}")

    if f_labels:
        lines.append("\n  ── Orchestration (F-labels) ──")
        lines.extend(f_labels)

    if not r_labels and not f_labels:
        lines.append(f"\n  (No activity in last {window_minutes} minutes)")

    # Interleaving summary
    if r_labels and f_labels:
        lines.append(f"\n  Summary: {len(r_labels)} R-labels, {len(f_labels)} F-labels")

    return '\n'.join(lines)


def _format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    else:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h{m}m" if m else f"{h}h"


# ─── View Registry (FLAG-2: authoritative source of truth) ───────────────────────

# VIEW_REGISTRY is the SINGLE SOURCE OF TRUTH for view types.
# The view_config DB table is optional persistence for external tooling (MCP).
# list_views() reads from here, not the DB.

VIEW_REGISTRY: dict[int, ViewEntry] = {
    1: ViewEntry(
        number=1,
        name='turn-by-turn',
        description='Snapshot dashboard injected per agent turn',
        renderer=render_turn_by_turn,
    ),
    2: ViewEntry(
        number=2,
        name='live-diff',
        description='Continuous diffs between agent turns',
        renderer=render_live_diff,
    ),
    3: ViewEntry(
        number=3,
        name='timeline',
        description='Stage progression with durations and bottlenecks',
        renderer=render_timeline,
    ),
    4: ViewEntry(
        number=4,
        name='agent-context',
        description='Decisions, flags, learnings for pipeline agents',
        renderer=render_agent_context,
    ),
    5: ViewEntry(
        number=5,
        name='r-label-trail',
        description='Real-time R-label narrative of script-pilot decisions',
        renderer=render_r_label_trail,
    ),
}


# ─── View Resolution ────────────────────────────────────────────────────────────

def list_views() -> str:
    """List all registered view types. Called by e0.v / e0v.

    Reads from VIEW_REGISTRY (authoritative), not the DB (FLAG-2).
    """
    lines = ["Available View Types (.v namespace)"]
    lines.append("─" * 50)
    for num, entry in sorted(VIEW_REGISTRY.items()):
        lines.append(f"  .v{num}  {entry.name:<18} {entry.description}")
    lines.append("")
    lines.append("Usage: e0p{N}.v{M} (scoped) or e0v{M} (global)")
    return '\n'.join(lines)


def resolve_view(coord: str, persona: str = None,
                 overlay=None) -> ViewResult:
    """Resolve a .v coordinate to rendered content.

    1. Parse coordinate → (pipeline_ref, view_type)
    2. Resolve pipeline_ref → version string (or None for global)
    3. Look up renderer in VIEW_REGISTRY
    4. Call renderer with (pipeline, persona, overlay)
    5. Return ViewResult
    """
    pipeline_ref, view_type = parse_view_coord(coord)

    # List views if no view type specified
    if view_type is None:
        content = list_views()
        return ViewResult(
            view_type=0,
            view_name='list',
            pipeline=None,
            persona=persona,
            content=content,
        )

    # Look up renderer
    entry = VIEW_REGISTRY.get(view_type)
    if not entry:
        available = ', '.join(f'.v{k}' for k in sorted(VIEW_REGISTRY.keys()))
        content = f"Unknown view type .v{view_type}. Available: {available}"
        return ViewResult(
            view_type=view_type,
            view_name='unknown',
            pipeline=None,
            persona=persona,
            content=content,
        )

    # Resolve pipeline reference
    pipeline_version = None
    if pipeline_ref:
        pipeline_version = _resolve_pipeline_ref(pipeline_ref)
        if not pipeline_version:
            content = f"Could not resolve pipeline reference: {pipeline_ref}"
            return ViewResult(
                view_type=view_type,
                view_name=entry.name,
                pipeline=pipeline_ref,
                persona=persona,
                content=content,
            )

    # Get overlay
    if overlay is None:
        overlay = _get_overlay()

    # Render
    content = entry.renderer(
        pipeline=pipeline_version,
        persona=persona,
        overlay=overlay,
    )

    return ViewResult(
        view_type=view_type,
        view_name=entry.name,
        pipeline=pipeline_version,
        persona=persona,
        content=content,
    )


# ─── CLI ──────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    args = sys.argv[1:]

    if not args or args[0] == 'list':
        print(list_views())

    elif args[0] == 'render':
        if len(args) < 2:
            print("Usage: monitoring_views.py render <v1|v2|v3|v4> [pipeline] [--persona p]")
            sys.exit(1)
        # Parse view type
        vt_str = args[1].lstrip('v')
        try:
            view_type = int(vt_str)
        except ValueError:
            print(f"Invalid view type: {args[1]}")
            sys.exit(1)

        pipeline = args[2] if len(args) > 2 and not args[2].startswith('--') else None
        persona = None
        if '--persona' in args:
            idx = args.index('--persona')
            if idx + 1 < len(args):
                persona = args[idx + 1]

        entry = VIEW_REGISTRY.get(view_type)
        if not entry:
            print(f"Unknown view type: v{view_type}")
            sys.exit(1)

        overlay = _get_overlay()
        result = entry.renderer(pipeline=pipeline, persona=persona, overlay=overlay)
        print(result)

    elif args[0] == 'parse':
        if len(args) < 2:
            print("Usage: monitoring_views.py parse <coord>")
            sys.exit(1)
        ref, vt = parse_view_coord(args[1])
        print(f"  pipeline_ref: {ref}")
        print(f"  view_type: {vt}")

    elif args[0] == 'resolve':
        if len(args) < 2:
            print("Usage: monitoring_views.py resolve <coord> [--persona p]")
            sys.exit(1)
        persona = None
        if '--persona' in args:
            idx = args.index('--persona')
            if idx + 1 < len(args):
                persona = args[idx + 1]
        result = resolve_view(args[1], persona=persona)
        print(f"View: .v{result.view_type} ({result.view_name})")
        print(f"Pipeline: {result.pipeline or '(global)'}")
        print(f"Generated: {result.generated_at}")
        print("─" * 50)
        print(result.content)

    else:
        print(f"Unknown command: {args[0]}")
        print("Commands: list, render, parse, resolve")
        sys.exit(1)
