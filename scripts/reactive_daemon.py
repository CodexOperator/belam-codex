#!/usr/bin/env python3
"""
OpenClaw Reactive Daemon.

Polls tasks/ and pipelines/ directories for frontmatter changes every N seconds.
When changes are detected, fires reactive handlers (pipeline launch, rewind, etc.).
Manages a task launch queue with configurable spacing between launches.

Usage:
  python3 scripts/reactive_daemon.py --loop --interval 30 --queue-spacing 1h
  python3 scripts/reactive_daemon.py --once   # single tick, then exit
  python3 scripts/reactive_daemon.py --status  # show daemon state

Options:
  --loop                Run continuously
  --once                Run one tick and exit
  --interval N          Seconds between ticks (default: 30)
  --queue-spacing SPEC  Time between queued launches: 0, 30s, 30m, 1h, 2h (default: 0)
  --dry-run             Log what would happen without acting
  --status              Show current daemon state and exit
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('OPENCLAW_WORKSPACE', Path(__file__).resolve().parent.parent))
TASKS_DIR = WORKSPACE / 'tasks'
PIPELINES_DIR = WORKSPACE / 'pipelines'
STATE_DIR = WORKSPACE / 'state'
CONFIG_PATH = STATE_DIR / 'orchestration_config.json'
DAEMON_STATE_PATH = STATE_DIR / 'daemon_state.json'
LOG_PATH = WORKSPACE / 'logs' / 'reactive_daemon.log'

MAX_CONCURRENT = 1

PRIORITY_ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}


@dataclass
class Snapshot:
    mtime: float
    frontmatter: dict


def parse_interval(spec: str) -> int:
    """Parse human-friendly interval spec to seconds.
    Accepts: 0, 30, 30s, 30m, 1h, 2h
    """
    spec = str(spec).strip().lower()
    if not spec or spec == '0':
        return 0
    m = re.match(r'^(\d+)\s*(s|m|h)?$', spec)
    if not m:
        raise ValueError(f"Invalid interval: {spec}. Use: 0, 30s, 30m, 1h, 2h")
    value = int(m.group(1))
    unit = m.group(2) or 's'
    multiplier = {'s': 1, 'm': 60, 'h': 3600}
    return value * multiplier[unit]


def parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a .md file."""
    try:
        text = path.read_text()
    except OSError:
        return {}
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return {}
    fields = {}
    for line in m.group(1).splitlines():
        kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if kv:
            val = kv.group(2).strip()
            if val.lower() in ('true', 'false'):
                val = val.lower() == 'true'
            fields[kv.group(1)] = val
    return fields


def count_active_pipelines() -> int:
    """Count pipelines with active (non-archived, non-complete) status."""
    count = 0
    for f in PIPELINES_DIR.glob('*.md'):
        fm = parse_frontmatter(f)
        status = str(fm.get('status', ''))
        if status and status not in ('archived', 'complete', 'done', ''):
            pending = str(fm.get('pending_action', ''))
            # Consider active if has a pending agent action
            if pending and not pending.endswith('_complete'):
                count += 1
    return count


def get_queued_tasks() -> list[tuple[Path, dict]]:
    """Get tasks with pipeline_status=queued, sorted by priority."""
    queued = []
    for f in TASKS_DIR.glob('*.md'):
        fm = parse_frontmatter(f)
        if fm.get('pipeline_status') == 'queued' and fm.get('pipeline_template'):
            queued.append((f, fm))
    queued.sort(key=lambda x: PRIORITY_ORDER.get(str(x[1].get('priority', 'medium')), 2))
    return queued


def load_orchestration_config() -> dict:
    """Load orchestration config (written by e0 cadence command)."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def log(msg: str):
    """Append to daemon log."""
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, 'a') as f:
            f.write(line + '\n')
    except OSError:
        pass


class ReactiveDaemon:

    def __init__(self, queue_spacing_seconds: int = 0, dry_run: bool = False):
        self.snapshots: dict[str, Snapshot] = {}
        self.queue_spacing_seconds = queue_spacing_seconds
        self.last_launch_at: float | None = None
        self.dry_run = dry_run
        self.tick_count = 0
        self._load_state()

    def _load_state(self):
        """Load persistent state from disk."""
        if DAEMON_STATE_PATH.exists():
            try:
                data = json.loads(DAEMON_STATE_PATH.read_text())
                self.last_launch_at = data.get('last_launch_at')
                # Restore snapshots (mtime only, frontmatter re-parsed)
                for path_str, snap_data in data.get('snapshots', {}).items():
                    self.snapshots[path_str] = Snapshot(
                        mtime=snap_data.get('mtime', 0),
                        frontmatter=snap_data.get('frontmatter', {}),
                    )
            except (json.JSONDecodeError, OSError):
                pass

    def _save_state(self):
        """Persist daemon state to disk."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            'last_launch_at': self.last_launch_at,
            'tick_count': self.tick_count,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'snapshots': {
                path_str: {'mtime': snap.mtime, 'frontmatter': snap.frontmatter}
                for path_str, snap in self.snapshots.items()
            },
        }
        DAEMON_STATE_PATH.write_text(json.dumps(data, indent=2, default=str))

    def tick(self):
        """Single check cycle."""
        self.tick_count += 1

        # Check for e0 cadence override
        config = load_orchestration_config()
        cadence_override = config.get('queue_cadence_seconds')
        if cadence_override is not None:
            self.queue_spacing_seconds = int(cadence_override)

        # Detect changes
        changed = self._detect_changes()
        for path, old_fm, new_fm in changed:
            self._handle_change(path, old_fm, new_fm)

        # Check queued task launches
        self._check_queued_launches()

        self._save_state()

    def _detect_changes(self) -> list[tuple[Path, dict, dict]]:
        """Fast mtime scan of tasks/ and pipelines/ directories."""
        changed = []
        import itertools

        dirs_to_scan = []
        if TASKS_DIR.is_dir():
            dirs_to_scan.append(TASKS_DIR.glob('*.md'))
        if PIPELINES_DIR.is_dir():
            dirs_to_scan.append(PIPELINES_DIR.glob('*.md'))

        for md_path in itertools.chain(*dirs_to_scan):
            path_key = str(md_path)
            try:
                st = md_path.stat()
            except OSError:
                continue

            snap = self.snapshots.get(path_key)
            if snap and snap.mtime == st.st_mtime:
                continue  # fast path: unchanged

            new_fm = parse_frontmatter(md_path)
            if snap and snap.frontmatter != new_fm:
                changed.append((md_path, snap.frontmatter, new_fm))

            self.snapshots[path_key] = Snapshot(st.st_mtime, new_fm)

        return changed

    def _handle_change(self, path: Path, old_fm: dict, new_fm: dict):
        """Dispatch reactive handlers based on field diffs."""
        prefix = 't' if '/tasks/' in str(path) else 'p'
        slug = path.stem

        for key in set(old_fm) | set(new_fm):
            old_val = old_fm.get(key)
            new_val = new_fm.get(key)
            if old_val != new_val:
                self._fire_reactive(prefix, key, old_val, new_val, path, new_fm, slug)

    def _fire_reactive(self, prefix: str, key: str, old_val, new_val,
                       path: Path, fm: dict, slug: str):
        """Fire reactive handler for a specific field change."""
        # Task status changes
        if prefix == 't' and key == 'status':
            template = fm.get('pipeline_template', '')
            if new_val == 'open' and template:
                log(f"REACTIVE: {slug} status->open with template={template}, queuing")
                if not self.dry_run:
                    self._update_frontmatter(path, {
                        'pipeline_status': 'queued',
                        'launch_mode': fm.get('launch_mode', 'queued'),
                    })

            elif new_val == 'active' and template:
                log(f"REACTIVE: {slug} status->active with template={template}, launching immediately")
                if not self.dry_run:
                    self._launch_pipeline(slug, template, bypass_concurrency=True)

        # Pipeline reset flag
        if prefix == 'p' and key == 'reset' and str(new_val).lower() in ('true', '1', 'yes'):
            log(f"REACTIVE: pipeline {slug} reset flag set, resetting current phase")
            if not self.dry_run:
                try:
                    sys.path.insert(0, str(Path(__file__).parent))
                    from pipeline_rewind import reset_current_phase
                    reset_current_phase(slug)
                    self._update_frontmatter(path, {'reset': 'false'})
                except Exception as e:
                    log(f"  ERROR: reset failed: {e}")

        # Pipeline stage/phase rewind
        if prefix == 'p' and key in ('pending_action', 'current_stage') and new_val and old_val:
            if new_val != old_val:
                log(f"REACTIVE: pipeline {slug} stage changed {old_val}->{new_val}")
                # Rewind handled by post_edit_hooks when changed via e1
                # Daemon handles external edits (vim, etc.)

    def _check_queued_launches(self):
        """Launch queued tasks when pipeline slots are free, respecting queue_spacing."""
        active_count = count_active_pipelines()
        if active_count >= MAX_CONCURRENT:
            return

        # Respect queue spacing
        if self.last_launch_at and self.queue_spacing_seconds > 0:
            elapsed = time.time() - self.last_launch_at
            if elapsed < self.queue_spacing_seconds:
                return

        queued = get_queued_tasks()
        if not queued:
            return

        # Launch ONE task per tick
        path, fm = queued[0]
        slug = path.stem
        template = fm.get('pipeline_template', '')

        if template:
            log(f"QUEUE: launching {slug} (template={template}, queue_spacing={self.queue_spacing_seconds}s)")
            if not self.dry_run:
                self._launch_pipeline(slug, template, bypass_concurrency=False)
                self.last_launch_at = time.time()

    def _launch_pipeline(self, slug: str, template: str, bypass_concurrency: bool = False):
        """Launch a pipeline for a task."""
        task_path = TASKS_DIR / f'{slug}.md'
        self._update_frontmatter(task_path, {'pipeline_status': 'launching'})

        launch_script = WORKSPACE / 'scripts' / 'launch_pipeline.py'
        if not launch_script.exists():
            log(f"  WARN: launch_pipeline.py not found")
            return

        cmd = ['python3', str(launch_script), slug, '--template', template, '--kickoff']
        if bypass_concurrency:
            cmd.append('--bypass-concurrency')

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
                cwd=str(WORKSPACE),
            )
            if result.returncode == 0:
                log(f"  OK: pipeline launched for {slug}")
                self._update_frontmatter(task_path, {'pipeline_status': 'in_pipeline'})
            else:
                log(f"  FAIL: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            log(f"  TIMEOUT: launch timed out for {slug}")

    def _update_frontmatter(self, path: Path, updates: dict):
        """Update frontmatter fields in a .md file."""
        text = path.read_text()
        m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, re.DOTALL)
        if not m:
            return
        fm_lines = m.group(1).splitlines()
        body = m.group(2)
        updated_keys = set()
        for i, line in enumerate(fm_lines):
            kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
            if kv and kv.group(1) in updates:
                fm_lines[i] = f'{kv.group(1)}: {updates[kv.group(1)]}'
                updated_keys.add(kv.group(1))
        for key, val in updates.items():
            if key not in updated_keys:
                fm_lines.append(f'{key}: {val}')
        path.write_text(f'---\n' + '\n'.join(fm_lines) + f'\n---\n{body}')

    def show_status(self):
        """Print daemon status."""
        config = load_orchestration_config()
        cadence = config.get('queue_cadence_seconds', self.queue_spacing_seconds)
        cadence_label = config.get('queue_cadence_label', f'{cadence}s')

        active = count_active_pipelines()
        queued = get_queued_tasks()

        print(f"OpenClaw Reactive Daemon Status")
        print(f"  Tick count: {self.tick_count}")
        print(f"  Queue cadence: {cadence_label} ({cadence}s)")
        print(f"  Active pipelines: {active}/{MAX_CONCURRENT}")
        print(f"  Queued tasks: {len(queued)}")
        if queued:
            for path, fm in queued[:5]:
                print(f"    - {path.stem} [{fm.get('priority', '?')}] template={fm.get('pipeline_template', '?')}")
        print(f"  Last launch: {datetime.fromtimestamp(self.last_launch_at, tz=timezone.utc).strftime('%Y-%m-%d %H:%M') if self.last_launch_at else 'never'}")
        print(f"  Tracked files: {len(self.snapshots)}")


def main():
    args = sys.argv[1:]

    interval = 30
    queue_spacing = 0
    dry_run = '--dry-run' in args
    loop_mode = '--loop' in args
    once_mode = '--once' in args
    status_mode = '--status' in args

    for i, a in enumerate(args):
        if a == '--interval' and i + 1 < len(args):
            interval = int(args[i + 1])
        elif a == '--queue-spacing' and i + 1 < len(args):
            queue_spacing = parse_interval(args[i + 1])

    daemon = ReactiveDaemon(queue_spacing_seconds=queue_spacing, dry_run=dry_run)

    if status_mode:
        daemon.show_status()
        return

    if once_mode or not loop_mode:
        daemon.tick()
        if once_mode:
            return

    if loop_mode:
        log(f"Starting reactive daemon (interval={interval}s, cadence={queue_spacing}s, dry_run={dry_run})")
        try:
            while True:
                daemon.tick()
                time.sleep(interval)
        except KeyboardInterrupt:
            log("Daemon stopped by user")


if __name__ == '__main__':
    main()
