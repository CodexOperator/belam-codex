#!/usr/bin/env python3
"""
wal_watcher.py — SQLite WAL polling + HTML canvas dashboard

Part of Orchestration V3: Real-Time Monitoring Suite.

Monitors temporal.db WAL file for changes and renders a live HTML dashboard
via OpenClaw canvas. NOT a daemon — designed to run as a background exec
session, killable on demand.

Change detection: monitors temporal.db-wal file size + mtime. When either
changes, a write has occurred. Fallback: if WAL file doesn't exist (DB in
rollback mode), polls temporal.db mtime directly. Also monitors main DB
mtime to catch WAL checkpoint resets (WAL size → 0).

Usage:
    python3 scripts/wal_watcher.py                        # start watcher
    python3 scripts/wal_watcher.py --interval 5           # 5s poll interval
    python3 scripts/wal_watcher.py --no-canvas            # terminal only
    python3 scripts/wal_watcher.py --once                 # single render
    python3 scripts/wal_watcher.py --db /path/to/db       # custom DB path
"""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable
from html import escape as html_escape

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
DEFAULT_DB_PATH = WORKSPACE / 'data' / 'temporal.db'

# Default polling interval in seconds
DEFAULT_INTERVAL = 2.0


class WALWatcher:
    """Lightweight SQLite WAL change detector for live dashboard.

    Polls SQLite WAL for changes at configurable intervals.
    When changes detected, re-renders dashboard and pushes to canvas.

    NOT a daemon — designed to run in a background exec session
    managed by OpenClaw, killable on demand.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH,
                 interval_seconds: float = DEFAULT_INTERVAL,
                 use_canvas: bool = True):
        self.db_path = db_path
        self.wal_path = Path(str(db_path) + '-wal')
        self.interval = interval_seconds
        self.use_canvas = use_canvas
        self._last_wal_size = 0
        self._last_wal_mtime = 0.0
        self._last_db_mtime = 0.0
        self._running = False
        self._render_count = 0

    def detect_changes(self) -> bool:
        """Check if WAL file has changed since last check.

        Returns True if a change was detected. Also monitors main DB
        mtime to catch WAL checkpoint resets (WAL size → 0).
        """
        changed = False

        # Check WAL file
        if self.wal_path.exists():
            try:
                stat = self.wal_path.stat()
                if stat.st_size != self._last_wal_size or stat.st_mtime != self._last_wal_mtime:
                    changed = True
                self._last_wal_size = stat.st_size
                self._last_wal_mtime = stat.st_mtime
            except OSError:
                pass

        # Check main DB file (catches WAL checkpoints)
        if self.db_path.exists():
            try:
                stat = self.db_path.stat()
                if stat.st_mtime != self._last_db_mtime:
                    changed = True
                self._last_db_mtime = stat.st_mtime
            except OSError:
                pass

        return changed

    def get_dashboard_data(self) -> Optional[dict]:
        """Query temporal DB for dashboard data."""
        try:
            from temporal_overlay import TemporalOverlay
            overlay = TemporalOverlay(workspace=WORKSPACE, db_path=self.db_path)
            if not overlay.available:
                return None
            dashboard = overlay.get_dashboard()

            # Add dependency graph
            try:
                from dependency_graph import get_all_deps
                dashboard['dependencies'] = get_all_deps(self.db_path)
            except (ImportError, Exception):
                dashboard['dependencies'] = []

            # Add timeline data for each pipeline
            timelines = {}
            for p in dashboard.get('pipelines', []):
                ver = p.get('version')
                if ver:
                    tl = overlay.get_timeline(ver)
                    if tl:
                        timelines[ver] = tl
            dashboard['timelines'] = timelines

            overlay.close()
            return dashboard
        except Exception as e:
            print(f"[wal_watcher] dashboard error: {e}", file=sys.stderr)
            return None

    def render_html_dashboard(self, dashboard: dict) -> str:
        """Render dashboard as self-contained HTML."""
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        pipelines = dashboard.get('pipelines', [])
        agents = dashboard.get('agents', [])
        handoffs = dashboard.get('recent_handoffs', [])
        stats = dashboard.get('stats', {})
        deps = dashboard.get('dependencies', [])

        # Build pipeline cards
        pipeline_cards = []
        for p in pipelines:
            ver = html_escape(p.get('version', '?'))
            stage = html_escape(p.get('current_stage', '?'))
            agent = html_escape(p.get('current_agent', '?'))
            locked = '🔒' if p.get('locked_by') else ''
            updated = html_escape(p.get('updated_at', '?')[:19])
            pipeline_cards.append(f"""
            <div class="card pipeline-card">
                <div class="card-header">{locked} {ver}</div>
                <div class="card-body">
                    <div class="field"><span class="label">Stage:</span> <code>{stage}</code></div>
                    <div class="field"><span class="label">Agent:</span> {agent}</div>
                    <div class="field"><span class="label">Updated:</span> {updated}</div>
                </div>
            </div>""")

        # Build agent indicators
        agent_items = []
        for a in agents:
            name = html_escape(a.get('agent', '?'))
            status = a.get('status', '?')
            stale = a.get('stale_seconds')
            if 'stale' in status:
                color = '#e74c3c'  # red
            elif status == 'working':
                color = '#2ecc71'  # green
            elif status == 'idle':
                color = '#f39c12'  # yellow
            else:
                color = '#95a5a6'  # gray
            stale_str = f' ({stale}s stale)' if stale else ''
            agent_items.append(
                f'<span class="agent-badge" style="background:{color}">'
                f'{html_escape(name)}: {html_escape(status)}{stale_str}</span>'
            )

        # Build dependency graph
        dep_items = []
        dep_icons = {'satisfied': '✅', 'pending': '⏳', 'blocked': '🚫'}
        for d in deps:
            src = html_escape(d.get('source_version', '?'))
            tgt = html_escape(d.get('target_version', '?'))
            status = d.get('status', 'pending')
            icon = dep_icons.get(status, '❓')
            dep_items.append(f'<div class="dep-row">{src} ──{icon}──→ {tgt}</div>')

        # Build recent handoffs
        handoff_items = []
        status_emojis = {
            'dispatched': '📤', 'acknowledged': '👀', 'working': '⚙️',
            'completed': '✅', 'blocked': '🚫', 'timed_out': '⏰',
        }
        for h in handoffs[:8]:
            src = html_escape(h.get('source_agent', '?'))
            tgt = html_escape(h.get('target_agent', '?'))
            ver = html_escape(h.get('version', '?'))
            se = status_emojis.get(h.get('status', ''), '❓')
            ts = html_escape(h.get('dispatched_at', '')[:16])
            handoff_items.append(
                f'<div class="handoff-row">{ts} {src} → {tgt} ({ver}) {se}</div>'
            )

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="10">
<title>Orchestration Dashboard</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace;
         background: #1a1a2e; color: #e0e0e0; padding: 16px; }}
  h1 {{ color: #bb86fc; font-size: 1.3em; margin-bottom: 12px; }}
  h2 {{ color: #03dac6; font-size: 1.1em; margin: 16px 0 8px 0; }}
  .stats {{ color: #888; font-size: 0.85em; margin-bottom: 16px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
           gap: 12px; }}
  .card {{ background: #16213e; border-radius: 8px; overflow: hidden; }}
  .card-header {{ background: #0f3460; padding: 8px 12px; font-weight: bold;
                  font-size: 0.9em; }}
  .card-body {{ padding: 8px 12px; font-size: 0.85em; }}
  .field {{ margin: 4px 0; }}
  .label {{ color: #888; }}
  code {{ background: #0d1b2a; padding: 2px 6px; border-radius: 3px; color: #03dac6; }}
  .agent-badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px;
                  margin: 2px 4px; font-size: 0.8em; color: #fff; }}
  .dep-row, .handoff-row {{ font-size: 0.85em; padding: 3px 0;
                            font-family: monospace; }}
  .footer {{ margin-top: 20px; color: #555; font-size: 0.75em; text-align: center; }}
</style>
</head>
<body>
  <h1>🏭 Orchestration Dashboard</h1>
  <div class="stats">
    {html_escape(str(stats.get('total_pipelines', 0)))} pipelines ·
    {html_escape(str(stats.get('active_agents', 0)))}/{html_escape(str(stats.get('total_agents', 0)))} agents active ·
    {html_escape(str(stats.get('pending_handoffs', 0)))} pending handoffs ·
    Render #{html_escape(str(self._render_count))}
  </div>

  <h2>Pipelines</h2>
  <div class="grid">{''.join(pipeline_cards) if pipeline_cards else '<div class="card"><div class="card-body">No active pipelines</div></div>'}</div>

  <h2>Agents</h2>
  <div>{''.join(agent_items) if agent_items else '<span style="color:#888">No agents registered</span>'}</div>

  {'<h2>Dependencies</h2><div>' + chr(10).join(dep_items) + '</div>' if dep_items else ''}

  <h2>Recent Handoffs</h2>
  <div>{''.join(handoff_items) if handoff_items else '<div style="color:#888">No handoffs</div>'}</div>

  <div class="footer">Last updated: {now} · Polling every {self.interval}s</div>
</body>
</html>"""
        return html

    def render_terminal(self, dashboard: dict) -> str:
        """Render dashboard for terminal output."""
        try:
            from monitoring_views import render_turn_by_turn
            from temporal_overlay import TemporalOverlay
            overlay = TemporalOverlay(workspace=WORKSPACE, db_path=self.db_path)
            result = render_turn_by_turn(overlay=overlay)
            overlay.close()
            return result
        except (ImportError, Exception):
            # Fallback
            lines = [f"Dashboard (render #{self._render_count})"]
            for p in dashboard.get('pipelines', []):
                lines.append(f"  {p.get('version','?')}: {p.get('current_stage','?')} ({p.get('current_agent','?')})")
            return '\n'.join(lines)

    def push_to_canvas(self, html: str) -> None:
        """Push HTML to OpenClaw canvas."""
        try:
            import urllib.parse
            # Write HTML to temp file and use file:// URL
            html_path = self.db_path.parent / 'dashboard.html'
            html_path.write_text(html, encoding='utf-8')
            # Use canvas present with file URL
            subprocess.run(
                ['openclaw', 'canvas', 'present', '--url', f'file://{html_path}'],
                capture_output=True, timeout=10,
            )
        except Exception as e:
            print(f"[wal_watcher] canvas push error: {e}", file=sys.stderr)

    def run(self, callback: Callable[[dict], None] = None) -> None:
        """Main loop: poll WAL, re-render on change.

        Default callback: push HTML to OpenClaw canvas (or terminal).
        Ctrl+C / SIGTERM to stop.
        """
        self._running = True

        def _handle_signal(signum, frame):
            self._running = False
            print("\n[wal_watcher] Stopping...", file=sys.stderr)

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        print(f"[wal_watcher] Monitoring {self.db_path} every {self.interval}s "
              f"(canvas={'on' if self.use_canvas else 'off'})", file=sys.stderr)

        # Initial render
        self._do_render(callback)

        while self._running:
            try:
                time.sleep(self.interval)
                if not self._running:
                    break
                if self.detect_changes():
                    self._do_render(callback)
            except Exception as e:
                print(f"[wal_watcher] error: {e}", file=sys.stderr)

        print(f"[wal_watcher] Stopped after {self._render_count} renders.",
              file=sys.stderr)

    def _do_render(self, callback: Callable = None) -> None:
        """Execute a single render cycle."""
        self._render_count += 1
        dashboard = self.get_dashboard_data()
        if not dashboard:
            return

        if callback:
            callback(dashboard)
            return

        if self.use_canvas:
            html = self.render_html_dashboard(dashboard)
            self.push_to_canvas(html)
            ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
            print(f"[wal_watcher] Render #{self._render_count} at {ts}", file=sys.stderr)
        else:
            output = self.render_terminal(dashboard)
            print(f"\033[2J\033[H{output}")  # Clear screen + render

    def render_once(self) -> str:
        """Single render — returns HTML string."""
        self._render_count += 1
        dashboard = self.get_dashboard_data()
        if not dashboard:
            return "<html><body>No dashboard data available</body></html>"
        return self.render_html_dashboard(dashboard)


# ─── CLI ──────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='WAL Watcher — live dashboard')
    parser.add_argument('--interval', type=float, default=DEFAULT_INTERVAL,
                        help=f'Poll interval in seconds (default: {DEFAULT_INTERVAL})')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB_PATH,
                        help='Database file path')
    parser.add_argument('--no-canvas', action='store_true',
                        help='Terminal output only (no canvas push)')
    parser.add_argument('--once', action='store_true',
                        help='Single render to stdout')
    args = parser.parse_args()

    watcher = WALWatcher(
        db_path=args.db,
        interval_seconds=args.interval,
        use_canvas=not args.no_canvas,
    )

    if args.once:
        html = watcher.render_once()
        print(html)
    else:
        watcher.run()
