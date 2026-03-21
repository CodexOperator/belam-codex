#!/usr/bin/env python3
"""
codex_ram.py — In-memory git-backed RAM state for the Codex Engine.

Provides a dulwich MemoryRepo-backed cache of workspace primitives for fast
reads, speculative writes, and snapshot/diff capabilities. Disk remains the
source of truth — all changes must be explicitly flushed via ram_flush().

Graceful degradation: if dulwich is not installed, RamState is a no-op stub
that returns None/False for all operations. The engine should check
`ram.available` before relying on RAM state.

Activation: opt-in via BELAM_RAM=1 env var (Critic Q3 response).

Uses codex_codec.from_codex() / to_codex() as the serialization boundary
(per Critic FLAG-1: correct API names).

Branch/merge deferred to V1.1 (per Critic FLAG-2: no consumer exists yet).
Diff returns list of (coord, field, old_value, new_value) tuples
(per Critic FLAG-3: specified output format).
"""

import os
import sys
import json
import datetime
from pathlib import Path
from collections import OrderedDict

# ─── Graceful degradation ──────────────────────────────────────────────────────

try:
    from dulwich.objects import Blob, Tree, Commit, S_IFREG
    from dulwich.object_store import MemoryObjectStore
    from dulwich.repo import BaseRepo
    HAS_DULWICH = True
except ImportError:
    HAS_DULWICH = False

try:
    sys.path.insert(0, str(Path(__file__).parent))
    from codex_codec import from_codex, to_codex
    HAS_CODEC = True
except ImportError:
    HAS_CODEC = False

# ─── Constants ──────────────────────────────────────────────────────────────────

WORKSPACE = Path(os.environ.get('BELAM_WORKSPACE', Path.home() / '.openclaw/workspace'))

# Directories that contain primitives (namespace → subdirectory)
PRIMITIVE_DIRS = {
    'pipelines': 'pipelines',
    'tasks': 'tasks',
    'decisions': 'decisions',
    'lessons': 'lessons',
    'commands': 'commands',
    'knowledge': 'knowledge',
    'modes': 'modes',
    'personas': 'personas',
    'projects': 'projects',
    'skills': 'skills',
}


# ─── RamState ───────────────────────────────────────────────────────────────────

class RamState:
    """In-memory git-backed workspace state.

    All methods return None/False on failure — never raises, never breaks
    the calling engine. Check `self.available` before relying on results.

    Lifecycle:
        ram = RamState()
        ram.init()           # scan disk, build initial tree
        data = ram.read(coord)  # fast in-memory read
        ram.write(coord, data)  # mark dirty, write to RAM
        ram.snapshot(msg)    # create in-memory commit snapshot
        diff = ram.diff(sha1, sha2)  # compare two snapshots
        ram.flush()          # write dirty entries back to disk
        ram.discard()        # drop all changes, re-sync from disk
    """

    def __init__(self):
        self.available = HAS_DULWICH and HAS_CODEC
        self._store = None       # MemoryObjectStore
        self._entries = {}       # coord_key -> {path, data_dict, dirty}
        self._snapshots = []     # list of (sha_hex, message, timestamp)
        self._initialized = False

    def init(self):
        """Scan disk primitives and build initial RAM tree.

        Returns True on success, False/None on failure.
        """
        if not self.available:
            return None
        try:
            self._store = MemoryObjectStore()
            self._entries = {}
            self._scan_disk()
            self._initialized = True
            return True
        except Exception as e:
            print(f"ram_init error: {e}", file=sys.stderr)
            self._initialized = False
            return False

    def _scan_disk(self):
        """Read all primitives from disk into RAM entries."""
        for ns_name, subdir in PRIMITIVE_DIRS.items():
            dirpath = WORKSPACE / subdir
            if not dirpath.is_dir():
                continue
            for fp in sorted(dirpath.glob('*.md')):
                try:
                    text = fp.read_text(encoding='utf-8', errors='replace')
                    if not text.startswith('---'):
                        continue
                    data = from_codex(text)
                    if not data:
                        continue
                    # Key: namespace/slug (e.g., "tasks/my-task")
                    slug = fp.stem
                    key = f"{subdir}/{slug}"
                    self._entries[key] = {
                        'path': str(fp),
                        'data': data,
                        'dirty': False,
                        'namespace': ns_name,
                        'slug': slug,
                    }
                except Exception:
                    continue  # skip unparseable files

    def read(self, coord_key):
        """Read a primitive from RAM by key (e.g., 'tasks/my-task').

        Returns the data dict, or None if not found/not initialized.
        """
        if not self._initialized:
            return None
        try:
            entry = self._entries.get(coord_key)
            return entry['data'] if entry else None
        except Exception:
            return None

    def read_by_coord(self, prefix, index):
        """Read a primitive by coordinate (prefix + 1-based index).

        Returns (key, data_dict) or (None, None).
        """
        if not self._initialized:
            return None, None
        try:
            # Find all entries for this namespace prefix
            from codex_engine import NAMESPACE, get_primitives
            if prefix not in NAMESPACE:
                return None, None
            _, subdir, _ = NAMESPACE[prefix]
            # Get sorted primitives to match index
            matching = sorted(
                [(k, v) for k, v in self._entries.items() if k.startswith(f"{subdir}/")],
                key=lambda x: x[0]
            )
            if 1 <= index <= len(matching):
                key, entry = matching[index - 1]
                return key, entry['data']
            return None, None
        except Exception:
            return None, None

    def write(self, coord_key, data):
        """Write data to RAM (marks dirty, does NOT touch disk).

        Returns True on success, False on failure.
        """
        if not self._initialized:
            return False
        try:
            if coord_key in self._entries:
                self._entries[coord_key]['data'] = data
                self._entries[coord_key]['dirty'] = True
            else:
                # New entry — derive path from key
                parts = coord_key.split('/', 1)
                if len(parts) != 2:
                    return False
                subdir, slug = parts
                fp = WORKSPACE / subdir / f"{slug}.md"
                self._entries[coord_key] = {
                    'path': str(fp),
                    'data': data,
                    'dirty': True,
                    'namespace': subdir,
                    'slug': slug,
                }
            return True
        except Exception:
            return False

    def snapshot(self, message="snapshot"):
        """Create an in-memory snapshot (commit) of current state.

        Returns snapshot SHA hex string, or None on failure.
        Uses dulwich object store to create real git tree + commit objects.
        """
        if not self._initialized or not self._store:
            return None
        try:
            # Build tree from current entries
            tree = Tree()
            for key, entry in sorted(self._entries.items()):
                # Serialize data back to .codex format
                codex_text = to_codex(entry['data'])
                blob = Blob.from_string(codex_text.encode('utf-8'))
                self._store.add_object(blob)
                # Use key as path in tree (e.g., "tasks/my-task")
                name = key.encode('utf-8')
                tree.add(name, S_IFREG | 0o644, blob.id)

            self._store.add_object(tree)

            # Create commit
            now = datetime.datetime.now(datetime.timezone.utc)
            timestamp = int(now.timestamp())
            timezone = 0  # UTC

            commit = Commit()
            commit.tree = tree.id
            commit.author = b"codex-ram <ram@belam.local>"
            commit.committer = commit.author
            commit.encoding = b"UTF-8"
            commit.message = message.encode('utf-8')
            commit.author_time = timestamp
            commit.author_timezone = timezone
            commit.commit_time = timestamp
            commit.commit_timezone = timezone

            # Parent is previous snapshot if exists
            if self._snapshots:
                commit.parents = [bytes.fromhex(self._snapshots[-1][0])]
            else:
                commit.parents = []

            self._store.add_object(commit)

            sha_hex = commit.id.hex()
            self._snapshots.append((sha_hex, message, now.isoformat()))
            return sha_hex
        except Exception as e:
            print(f"ram_snapshot error: {e}", file=sys.stderr)
            return None

    def diff(self, sha1=None, sha2=None):
        """Diff two snapshots, or current state vs last snapshot.

        Returns list of (coord_key, field, old_value, new_value) tuples.
        Per Critic FLAG-3: specified output format.

        If sha1/sha2 omitted, diffs current dirty state against last snapshot.
        """
        if not self._initialized:
            return None
        try:
            if sha1 is None and sha2 is None:
                # Diff dirty entries against their clean state
                changes = []
                for key, entry in self._entries.items():
                    if entry['dirty']:
                        # We don't have the clean version stored separately,
                        # so report the entry as changed
                        changes.append((key, '*', '<previous>', '<current>'))
                return changes

            if not self._store:
                return None

            # Load trees from snapshots
            def _load_tree_data(sha_hex):
                commit_obj = self._store[bytes.fromhex(sha_hex)]
                tree_obj = self._store[commit_obj.tree]
                entries = {}
                for item in tree_obj.items():
                    name = item.path.decode('utf-8')
                    blob = self._store[item.sha]
                    text = blob.data.decode('utf-8')
                    try:
                        entries[name] = from_codex(text)
                    except Exception:
                        entries[name] = {'_raw': text}
                return entries

            data1 = _load_tree_data(sha1) if sha1 else {}
            data2 = _load_tree_data(sha2) if sha2 else {}

            changes = []
            all_keys = set(data1.keys()) | set(data2.keys())
            for key in sorted(all_keys):
                d1 = data1.get(key, {})
                d2 = data2.get(key, {})
                if key not in data1:
                    changes.append((key, '*', None, '<added>'))
                elif key not in data2:
                    changes.append((key, '*', '<removed>', None))
                else:
                    # Compare field by field
                    all_fields = set(d1.keys()) | set(d2.keys())
                    for field in sorted(all_fields):
                        v1 = d1.get(field)
                        v2 = d2.get(field)
                        if v1 != v2:
                            changes.append((key, field, v1, v2))
            return changes
        except Exception as e:
            print(f"ram_diff error: {e}", file=sys.stderr)
            return None

    def branch(self, name):
        """Create a speculative branch for 'what if' edits.

        Creates a shallow copy of current entries on a named branch,
        switches to it. All subsequent read/write ops target this branch.
        Merge back with merge(). Discard with rollback().
        """
        if not self._initialized:
            return False
        # Deep-copy entries to isolate branch
        import copy
        self._branches = getattr(self, '_branches', {'main': self._entries})
        self._branches['main'] = self._entries  # ensure main is tracked
        self._branches[name] = copy.deepcopy(self._entries)
        self._current_branch = name
        self._entries = self._branches[name]
        return True

    def merge(self, target='main'):
        """Merge current branch into target. Returns count of entries merged."""
        if not self._initialized:
            return None
        branches = getattr(self, '_branches', {})
        if target not in branches:
            return None
        current = self._entries
        target_entries = branches[target]
        merged = 0
        for key, entry in current.items():
            if entry['dirty']:
                target_entries[key] = entry
                merged += 1
        # Switch back to target
        self._entries = target_entries
        self._current_branch = target
        return merged

    def rollback(self):
        """Discard current branch and switch back to main."""
        branches = getattr(self, '_branches', {})
        current = getattr(self, '_current_branch', 'main')
        if current != 'main' and current in branches:
            del branches[current]
        if 'main' in branches:
            self._entries = branches['main']
        self._current_branch = 'main'

    def flush(self):
        """Write all dirty entries back to disk via codex_codec.

        Returns number of entries flushed, or None on failure.
        """
        if not self._initialized:
            return None
        try:
            count = 0
            for key, entry in self._entries.items():
                if not entry['dirty']:
                    continue
                fp = Path(entry['path'])
                codex_text = to_codex(entry['data'])
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(codex_text, encoding='utf-8')
                entry['dirty'] = False
                count += 1
            return count
        except Exception as e:
            print(f"ram_flush error: {e}", file=sys.stderr)
            return None

    def discard(self):
        """Drop all changes and re-sync from disk.

        Returns True on success.
        """
        if not self.available:
            return None
        try:
            self._entries = {}
            self._snapshots = []
            self._store = MemoryObjectStore() if HAS_DULWICH else None
            self._scan_disk()
            self._initialized = True
            return True
        except Exception as e:
            print(f"ram_discard error: {e}", file=sys.stderr)
            return False

    def stats(self):
        """Return RAM state statistics dict."""
        if not self._initialized:
            return None
        dirty_count = sum(1 for e in self._entries.values() if e['dirty'])
        return {
            'total_entries': len(self._entries),
            'dirty_entries': dirty_count,
            'snapshots': len(self._snapshots),
            'namespaces': len(set(e['namespace'] for e in self._entries.values())),
            'available': self.available,
            'initialized': self._initialized,
        }

    def list_dirty(self):
        """Return list of dirty coord keys."""
        if not self._initialized:
            return []
        return [k for k, v in self._entries.items() if v['dirty']]

    def list_snapshots(self):
        """Return list of (sha_hex, message, timestamp) tuples."""
        return list(self._snapshots)


# ─── Module-level convenience ───────────────────────────────────────────────────

_global_ram = None


def get_ram():
    """Get or create the global RamState instance.

    Only initializes if BELAM_RAM=1 is set (opt-in, per Critic Q3).
    Returns RamState (may be a no-op stub if dulwich unavailable).
    """
    global _global_ram
    if _global_ram is not None:
        return _global_ram

    _global_ram = RamState()

    if os.environ.get('BELAM_RAM', '').strip() == '1':
        result = _global_ram.init()
        if result:
            stats = _global_ram.stats()
            print(f"ram: initialized ({stats['total_entries']} primitives, "
                  f"{stats['namespaces']} namespaces)", file=sys.stderr)
        elif result is None:
            print("ram: dulwich not available, RAM state disabled", file=sys.stderr)
        else:
            print("ram: initialization failed", file=sys.stderr)

    return _global_ram


# ─── CLI ────────────────────────────────────────────────────────────────────────

def _cli():
    """Simple CLI for testing RAM state."""
    import argparse
    parser = argparse.ArgumentParser(description='Codex RAM State')
    parser.add_argument('command', choices=['init', 'stats', 'list', 'dirty', 'snapshot', 'flush', 'discard'],
                        help='RAM command')
    parser.add_argument('--message', '-m', default='cli-snapshot', help='Snapshot message')
    args = parser.parse_args()

    # Force RAM activation for CLI usage
    os.environ['BELAM_RAM'] = '1'
    ram = get_ram()

    if not ram.available:
        print("ERROR: dulwich not installed. Install with: pip install dulwich")
        sys.exit(1)

    if not ram._initialized:
        ram.init()

    if args.command == 'init':
        print(f"RAM initialized: {ram.stats()}")
    elif args.command == 'stats':
        stats = ram.stats()
        if stats:
            for k, v in stats.items():
                print(f"  {k}: {v}")
        else:
            print("RAM not initialized")
    elif args.command == 'list':
        for key in sorted(ram._entries.keys()):
            dirty = ' [dirty]' if ram._entries[key]['dirty'] else ''
            print(f"  {key}{dirty}")
    elif args.command == 'dirty':
        dirty = ram.list_dirty()
        if dirty:
            for k in dirty:
                print(f"  {k}")
        else:
            print("No dirty entries")
    elif args.command == 'snapshot':
        sha = ram.snapshot(args.message)
        if sha:
            print(f"Snapshot: {sha[:12]}  {args.message}")
        else:
            print("Snapshot failed")
    elif args.command == 'flush':
        count = ram.flush()
        print(f"Flushed {count} entries" if count is not None else "Flush failed")
    elif args.command == 'discard':
        ram.discard()
        print("Discarded all changes, re-synced from disk")


if __name__ == '__main__':
    _cli()
