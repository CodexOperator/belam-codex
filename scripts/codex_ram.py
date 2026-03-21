#!/usr/bin/env python3
"""
codex_ram.py — In-memory state layer for workspace primitives.

Provides speculative branching, diff, merge, and rollback without
touching disk until explicit checkpoint.  Pure-Python dict-based
implementation — designed as a drop-in for a future dulwich backend.

Usage:
    ram = CodexRAM(workspace_path)
    ram.snapshot()                    # load current disk state into RAM
    ram.branch('speculative-edit')    # create speculative branch
    ram.write('tasks/foo.md', content)  # write to RAM tree
    diff = ram.diff('main')          # diff against main branch
    ram.merge('main')                # merge speculative into main
    ram.checkpoint()                 # flush dirty files to disk
    ram.rollback()                   # discard speculative branch
"""

from pathlib import Path
from typing import Optional
import time


# Directories to snapshot (primitive-bearing subdirs)
_SNAPSHOT_DIRS = (
    'tasks', 'decisions', 'lessons', 'pipelines', 'commands',
    'knowledge', 'projects', 'modes', 'personas', 'skills',
    'memory/entries', 'memory/weekly',
)


class CodexRAM:
    """In-memory state tree with speculative branching.

    FLAG-4 addressed: tracks a dirty set so checkpoint() only writes
    files that were actually modified since the last snapshot/checkpoint.
    """

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self._trees: dict[str, dict[str, str]] = {}  # branch → {relpath: content}
        self._current: str = 'main'
        self._dirty: dict[str, set[str]] = {}  # branch → set of dirty relpaths
        self._history: list[tuple[float, str, str, Optional[str]]] = []

    # ── Snapshot (disk → RAM) ───────────────────────────────────────────────

    def snapshot(self) -> int:
        """Load current disk state into RAM main branch. Returns file count."""
        tree: dict[str, str] = {}
        for subdir in _SNAPSHOT_DIRS:
            dirpath = self.workspace / subdir
            if not dirpath.exists():
                continue
            for f in dirpath.rglob('*.md'):
                relpath = str(f.relative_to(self.workspace))
                try:
                    tree[relpath] = f.read_text(encoding='utf-8', errors='replace')
                except Exception:
                    pass
        self._trees['main'] = tree
        self._dirty['main'] = set()
        self._current = 'main'
        self._history.append((time.time(), 'main', 'snapshot', None))
        return len(tree)

    # ── Branching ───────────────────────────────────────────────────────────

    def branch(self, name: str) -> None:
        """Create a new branch from current, switch to it."""
        self._trees[name] = dict(self._trees[self._current])
        self._dirty[name] = set()
        self._current = name
        self._history.append((time.time(), name, 'branch', None))

    def switch(self, name: str) -> None:
        """Switch to an existing branch."""
        if name not in self._trees:
            raise KeyError(f"Branch '{name}' does not exist")
        self._current = name

    def branches(self) -> list[str]:
        """List all branches."""
        return list(self._trees.keys())

    # ── Read / Write / Delete ───────────────────────────────────────────────

    def read(self, path: str) -> Optional[str]:
        """Read file from current RAM branch."""
        return self._trees.get(self._current, {}).get(path)

    def write(self, path: str, content: str) -> None:
        """Write file to current RAM branch (marks dirty)."""
        self._trees.setdefault(self._current, {})[path] = content
        self._dirty.setdefault(self._current, set()).add(path)
        self._history.append((time.time(), self._current, 'write', path))

    def delete(self, path: str) -> bool:
        """Delete file from current RAM branch."""
        tree = self._trees.get(self._current, {})
        if path in tree:
            del tree[path]
            self._dirty.setdefault(self._current, set()).add(path)
            self._history.append((time.time(), self._current, 'delete', path))
            return True
        return False

    # ── Diff / Merge ────────────────────────────────────────────────────────

    def diff(self, other_branch: str = 'main') -> dict:
        """Diff current branch against another. Returns {added, modified, deleted}."""
        current = self._trees.get(self._current, {})
        other = self._trees.get(other_branch, {})

        added = sorted(set(current.keys()) - set(other.keys()))
        deleted = sorted(set(other.keys()) - set(current.keys()))
        modified = sorted(
            p for p in current.keys() & other.keys()
            if current[p] != other[p]
        )
        return {'added': added, 'modified': modified, 'deleted': deleted}

    def merge(self, target: str = 'main') -> dict:
        """Merge current branch into target. Returns diff applied."""
        d = self.diff(target)
        target_tree = self._trees.setdefault(target, {})
        current_tree = self._trees.get(self._current, {})

        for path in d['added'] + d['modified']:
            target_tree[path] = current_tree[path]
            self._dirty.setdefault(target, set()).add(path)
        for path in d['deleted']:
            target_tree.pop(path, None)
            self._dirty.setdefault(target, set()).add(path)

        self._history.append((time.time(), self._current, 'merge', target))
        return d

    # ── Checkpoint (RAM → disk) ─────────────────────────────────────────────

    def checkpoint(self) -> int:
        """Flush only dirty files from current branch to disk. Returns count written."""
        tree = self._trees.get(self._current, {})
        dirty = self._dirty.get(self._current, set())
        written = 0
        for path in list(dirty):
            fp = self.workspace / path
            if path in tree:
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(tree[path], encoding='utf-8')
                written += 1
            else:
                # Deleted in RAM — remove from disk if present
                if fp.exists():
                    fp.unlink()
                    written += 1
        dirty.clear()
        self._history.append((time.time(), self._current, 'checkpoint', None))
        return written

    # ── Rollback ────────────────────────────────────────────────────────────

    def rollback(self) -> None:
        """Discard current branch, switch to main."""
        if self._current != 'main':
            self._trees.pop(self._current, None)
            self._dirty.pop(self._current, None)
            self._history.append((time.time(), self._current, 'rollback', None))
            self._current = 'main'

    # ── Stats ───────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return branch stats."""
        return {
            'current': self._current,
            'branches': {
                name: {'files': len(tree), 'dirty': len(self._dirty.get(name, set()))}
                for name, tree in self._trees.items()
            },
            'history_length': len(self._history),
        }
