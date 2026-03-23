#!/usr/bin/env python3
"""
codex_watch.py — Live Diff Daemon for the Codex Engine.

Monitors all primitive directories for filesystem changes and emits R-label
diffs into a buffer file (~/.belam_live_diffs.log). Agents consume diffs via
`R diffs` (--read-diffs) at turn-start instead of polling the full engine.

DEPENDENCY: Requires the `watchdog` Python library.
    pip3 install watchdog

Usage:
    codex_watch.py --watch          Start the daemon in the foreground (caller backgrounded it)
    codex_watch.py --read-diffs     Read and clear the diff buffer (called by `R diffs`)
    codex_watch.py --status         Show whether the daemon is running
    codex_watch.py --stop           Stop a running daemon

Architecture notes:
    - R-labels ONLY for daemon-emitted diffs (view layer, not mutation layer)
    - F-labels are reserved for agent-initiated mutations via codex_engine.py
    - Reuses get_primitives(), render_zoom(), get_render_tracker() from codex_engine
    - Do NOT duplicate rendering logic here
    - See decisions/live-diff-streaming-architecture.md for full design
"""

import argparse
import datetime
import fcntl
import json
import os
import re
import signal
import sys
import threading
import time
from pathlib import Path

# ─── Paths ──────────────────────────────────────────────────────────────────────

WORKSPACE = Path(os.environ.get('BELAM_WORKSPACE', Path.home() / '.openclaw/workspace'))
SCRIPTS_DIR = WORKSPACE / 'scripts'

DIFF_BUFFER_FILE = Path.home() / '.belam_live_diffs.log'
PID_FILE = Path.home() / '.belam_watch.pid'
MAX_BUFFER_ENTRIES = 50

# ─── Engine Import ──────────────────────────────────────────────────────────────

# Add scripts dir to path so we can import codex_engine
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from codex_engine import (
        get_primitives,
        render_zoom,
        get_render_tracker,
        NAMESPACE,
        WORKSPACE as ENGINE_WORKSPACE,
    )
    ENGINE_AVAILABLE = True
except ImportError as e:
    ENGINE_AVAILABLE = False
    _engine_import_error = str(e)

# ─── Watchdog Import ────────────────────────────────────────────────────────────
# DEPENDENCY: pip3 install watchdog
# As of 2026-03-21, watchdog is NOT installed in this environment.

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # Stub base class so PrimitiveChangeHandler can be defined unconditionally
    class FileSystemEventHandler:  # type: ignore[no-redef]
        def dispatch(self, event): pass

# ─── Primitive Directory Map ────────────────────────────────────────────────────

# Map from absolute directory path → namespace prefix
# Built at daemon startup from NAMESPACE config in codex_engine
def _build_dir_map():
    """Return dict: abs_dir_path_str → prefix for all watchable namespaces."""
    dir_map = {}
    skip = {'s', 'md'}  # skills (subdirs) and daily (mixed with weeklies/entries) handled specially
    for prefix, (type_label, rel_dir, special) in NAMESPACE.items():
        if special == 'skills':
            continue  # SKILL.md files deep in subdirs — skip for now
        abs_dir = WORKSPACE / rel_dir
        dir_map[str(abs_dir)] = prefix
    return dir_map

# ─── Ignored Path Patterns ──────────────────────────────────────────────────────

_IGNORE_PATTERNS = [
    re.compile(r'(^|[/\\])\.git([/\\]|$)'),
    re.compile(r'__pycache__'),
    re.compile(r'\.pyc$'),
    re.compile(r'\.pyo$'),
    re.compile(r'\.tmp$'),
    re.compile(r'\.swp$'),
    re.compile(r'\.swo$'),
    re.compile(r'~$'),
    re.compile(r'(^|[/\\])\.#'),          # emacs lock files
    re.compile(r'(^|[/\\])#[^/\\]+#$'),   # emacs autosave
]

_IGNORE_FILENAMES = {
    'codex_engine.py',
    'codex_watch.py',
    '.belam_live_diffs.log',
    '.belam_watch.pid',
    '.belam_render_state.json',
}


def _should_ignore(path_str: str) -> bool:
    """Return True if this path should be ignored."""
    fname = Path(path_str).name

    if fname in _IGNORE_FILENAMES:
        return True

    for pat in _IGNORE_PATTERNS:
        if pat.search(path_str):
            return True

    # Only process .md files
    if not path_str.endswith('.md'):
        return True

    return False


# ─── Coordinate Resolution ──────────────────────────────────────────────────────

def _path_to_coords(changed_path: str, dir_map: dict) -> list:
    """Given a changed file path, return list of coordinate strings (e.g. ['d12']).

    Handles the case where the file is new (not yet in the index) by using
    the slug to search. Returns empty list if path cannot be mapped.
    """
    p = Path(changed_path)
    slug = p.stem

    # Find which namespace directory this file belongs to
    matched_prefix = None
    for dir_path, prefix in dir_map.items():
        try:
            p.relative_to(dir_path)
            matched_prefix = prefix
            break
        except ValueError:
            continue

    if matched_prefix is None:
        return []

    # Special case: daily memory files (YYYY-MM-DD.md in memory/)
    daily_pat = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    if daily_pat.match(slug) and matched_prefix == 'md':
        matched_prefix = 'md'

    try:
        primitives = get_primitives(matched_prefix, active_only=False)
    except Exception:
        return []

    for i, (prim_slug, prim_fp) in enumerate(primitives, 1):
        if prim_slug == slug:
            return [f"{matched_prefix}{i}"]

    # File not in index yet (new primitive) — approximate as last+1
    return [f"{matched_prefix}{len(primitives) + 1}"]


# ─── Diff Buffer ────────────────────────────────────────────────────────────────

def _append_diff(coord: str, slug: str, label: str, diff_text: str):
    """Append a diff entry to the buffer file. Enforces MAX_BUFFER_ENTRIES."""
    entry = {
        'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'coord': coord,
        'slug': slug,
        'label': label,
        'diff': diff_text,
    }
    entry_line = json.dumps(entry, ensure_ascii=False) + '\n'

    try:
        with open(DIFF_BUFFER_FILE, 'a+', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                # Read current entries
                f.seek(0)
                lines = f.readlines()
                lines.append(entry_line)

                # Trim to max size (drop oldest)
                if len(lines) > MAX_BUFFER_ENTRIES:
                    lines = lines[-MAX_BUFFER_ENTRIES:]

                # Rewrite
                f.seek(0)
                f.truncate()
                f.writelines(lines)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        # Don't crash the daemon on buffer write errors
        _log(f"[codex_watch] buffer write error: {e}")


def _read_and_clear_diffs() -> list:
    """Read all diff entries from buffer and truncate the file. Returns list of entry dicts."""
    if not DIFF_BUFFER_FILE.exists():
        return []

    entries = []
    try:
        with open(DIFF_BUFFER_FILE, 'r+', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
                f.seek(0)
                f.truncate()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[codex_watch] error reading diffs: {e}", file=sys.stderr)

    return entries


# ─── Rendering ──────────────────────────────────────────────────────────────────

def _render_coord_diff(coord: str) -> tuple:
    """Re-render a coordinate and register with RenderTracker.

    Returns (label_str, diff_text) where label_str is e.g. 'R42'.
    diff_text is the full rendered output with R-label prepended.
    """
    try:
        raw = render_zoom([coord])
    except Exception as e:
        raw = f"[render error for {coord}: {e}]"

    try:
        tracker = get_render_tracker()
        label_int, output = tracker.track_render(raw)
        label_str = f"R{label_int}"
        return label_str, output
    except Exception as e:
        return 'R?', raw


# ─── Debouncer ──────────────────────────────────────────────────────────────────

class Debouncer:
    """Debounce filesystem events: wait 500ms after last event before processing."""

    DEBOUNCE_SECONDS = 0.5

    def __init__(self, callback):
        self._callback = callback
        self._pending = {}   # path_str → threading.Timer
        self._lock = threading.Lock()

    def schedule(self, path_str: str):
        with self._lock:
            # Cancel any existing timer for this path
            if path_str in self._pending:
                self._pending[path_str].cancel()

            t = threading.Timer(
                self.DEBOUNCE_SECONDS,
                self._fire,
                args=[path_str],
            )
            self._pending[path_str] = t
            t.start()

    def _fire(self, path_str: str):
        with self._lock:
            self._pending.pop(path_str, None)
        self._callback(path_str)

    def cancel_all(self):
        with self._lock:
            for t in self._pending.values():
                t.cancel()
            self._pending.clear()


# ─── Event Handler ──────────────────────────────────────────────────────────────

class PrimitiveChangeHandler(FileSystemEventHandler):
    """Watchdog event handler for primitive directory changes."""

    def __init__(self, dir_map: dict):
        super().__init__()
        self._dir_map = dir_map
        self._debouncer = Debouncer(self._process_change)
        # Cache: coord → last rendered content hash (for true diff detection)
        self._last_state = {}

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        # Treat destination as a creation
        self._handle_event(event.dest_path)

    def _handle_event(self, path_str: str):
        if _should_ignore(path_str):
            return
        _log(f"[watch] event: {path_str}")
        self._debouncer.schedule(path_str)

    def _process_change(self, path_str: str):
        """Called after debounce: identify coordinate, re-render, write diff."""
        coords = _path_to_coords(path_str, self._dir_map)
        if not coords:
            _log(f"[watch] could not map to coord: {path_str}")
            return

        slug = Path(path_str).stem

        for coord in coords:
            label_str, diff_text = _render_coord_diff(coord)

            # Skip if content hasn't actually changed (pin reference means identical)
            if '📌' in diff_text:
                _log(f"[watch] {coord} unchanged (pin {label_str})")
                continue

            _log(f"[watch] {coord} changed → {label_str}")
            _append_diff(coord, slug, label_str, diff_text)

    def shutdown(self):
        self._debouncer.cancel_all()


# ─── Logging ────────────────────────────────────────────────────────────────────

def _log(msg: str):
    """Simple timestamped stderr log for daemon mode."""
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


# ─── PID Management ─────────────────────────────────────────────────────────────

def _write_pid():
    PID_FILE.write_text(str(os.getpid()))


def _read_pid() -> int | None:
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None


def _clear_pid():
    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        pass


def _is_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


# ─── Daemon ─────────────────────────────────────────────────────────────────────

def run_daemon():
    """Main daemon loop. Runs in foreground; caller is responsible for backgrounding."""
    if not WATCHDOG_AVAILABLE:
        print(
            "ERROR: watchdog library not installed.\n"
            "Install it with:  pip3 install watchdog\n"
            "See decisions/live-diff-streaming-architecture.md for details.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not ENGINE_AVAILABLE:
        print(f"ERROR: could not import codex_engine: {_engine_import_error}", file=sys.stderr)
        sys.exit(1)

    # Check if already running
    existing_pid = _read_pid()
    if existing_pid and _is_running(existing_pid):
        print(f"Daemon already running (PID {existing_pid})", file=sys.stderr)
        sys.exit(1)

    _write_pid()
    _log(f"codex_watch daemon started (PID {os.getpid()})")
    _log(f"Workspace: {WORKSPACE}")
    _log(f"Diff buffer: {DIFF_BUFFER_FILE}")

    dir_map = _build_dir_map()
    _log(f"Watching {len(dir_map)} directories")
    for d, prefix in sorted(dir_map.items()):
        _log(f"  [{prefix}] {d}")

    handler = PrimitiveChangeHandler(dir_map)
    observer = Observer()

    for dir_path_str in dir_map:
        dir_path = Path(dir_path_str)
        if dir_path.exists():
            observer.schedule(handler, str(dir_path), recursive=False)
        else:
            _log(f"  [warn] directory does not exist, skipping: {dir_path_str}")

    # Signal handling for clean shutdown
    _stop_event = threading.Event()

    def _handle_signal(signum, frame):
        _log(f"Received signal {signum}, shutting down...")
        _stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    observer.start()
    _log("Observer started. Waiting for filesystem events...")

    try:
        while not _stop_event.is_set():
            _stop_event.wait(timeout=1.0)
    finally:
        _log("Stopping observer...")
        observer.stop()
        observer.join()
        handler.shutdown()
        _clear_pid()
        _log("Daemon stopped cleanly.")


# ─── CLI Commands ────────────────────────────────────────────────────────────────

def cmd_read_diffs():
    """Read and clear the diff buffer. Called by `R diffs`."""
    entries = _read_and_clear_diffs()

    if not entries:
        print("(no diffs since last check)")
        return

    for entry in entries:
        ts = entry.get('ts', '?')
        coord = entry.get('coord', '?')
        label = entry.get('label', '?')
        diff = entry.get('diff', '')
        # Human-readable timestamp
        try:
            dt = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
            ts_human = dt.strftime('%Y-%m-%d %H:%M UTC')
        except Exception:
            ts_human = ts

        print(f"[{ts_human}] {coord} changed → {label}")
        print(diff)
        print("---")

    print(f"({len(entries)} diff{'s' if len(entries) != 1 else ''} since last check)")


def cmd_status():
    """Show daemon status."""
    pid = _read_pid()
    if pid is None:
        print("codex_watch: NOT running (no PID file)")
        return

    if _is_running(pid):
        print(f"codex_watch: RUNNING (PID {pid})")
        # Show buffer size
        if DIFF_BUFFER_FILE.exists():
            try:
                with open(DIFF_BUFFER_FILE, 'r', encoding='utf-8') as f:
                    count = sum(1 for line in f if line.strip())
                print(f"Diff buffer: {count} entries in {DIFF_BUFFER_FILE}")
            except Exception:
                pass
        else:
            print("Diff buffer: empty")
    else:
        print(f"codex_watch: STALE PID file (PID {pid} not running)")
        print(f"  Remove with: rm {PID_FILE}")


def cmd_stop():
    """Stop the daemon."""
    pid = _read_pid()
    if pid is None:
        print("codex_watch: not running (no PID file)")
        return

    if not _is_running(pid):
        print(f"codex_watch: stale PID file (PID {pid} not running), cleaning up")
        _clear_pid()
        return

    _log(f"Sending SIGTERM to PID {pid}")
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait up to 5s for clean shutdown
        for _ in range(50):
            time.sleep(0.1)
            if not _is_running(pid):
                print(f"codex_watch: stopped (PID {pid})")
                return
        print(f"codex_watch: PID {pid} did not stop within 5s — try SIGKILL manually")
    except PermissionError:
        print(f"codex_watch: permission denied sending signal to PID {pid}")
    except ProcessLookupError:
        print(f"codex_watch: PID {pid} already gone")
        _clear_pid()


# ─── Entry Point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='codex_watch — Live Diff Daemon for the Codex Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  --watch        Start the live diff daemon (foreground; use & or nohup to background)
  --read-diffs   Read and clear the accumulated diff buffer (called by `R diffs`)
  --status       Show whether the daemon is running
  --stop         Stop a running daemon

Dependency: pip3 install watchdog
Design doc: decisions/live-diff-streaming-architecture.md
        """,
    )
    parser.add_argument('--watch', action='store_true', help='Start the daemon')
    parser.add_argument('--read-diffs', action='store_true', help='Read and clear diff buffer')
    parser.add_argument('--status', action='store_true', help='Show daemon status')
    parser.add_argument('--stop', action='store_true', help='Stop the daemon')

    args = parser.parse_args()

    if args.watch:
        run_daemon()
    elif args.read_diffs:
        cmd_read_diffs()
    elif args.status:
        cmd_status()
    elif args.stop:
        cmd_stop()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
