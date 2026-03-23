#!/usr/bin/env python3
"""
codex_render.py — Codex Render Engine (V3 Phase 2).

Persistent foreground process holding the full primitive tree in RAM.
Read-side daemon: detects disk changes, produces diffs, serves context.

Usage:
  codex_render.py                    # Start render engine (foreground)
  codex_render.py --test             # Start in test mode (in-memory branch)
  codex_render.py --status           # Query running engine status
  codex_render.py --diff             # Get current delta from running engine
  codex_render.py --context          # Get assembled context from running engine
  codex_render.py --anchor-reset     # Reset diff anchor on running engine
  codex_render.py --commit [msg]     # Commit test mode changes
  codex_render.py --discard          # Discard test mode changes
  codex_render.py --buffer [format]  # Get render buffer (dense/json/pretty)
  codex_render.py --stop             # Send shutdown signal
"""

from __future__ import annotations

import ctypes
import ctypes.util
import datetime
import hashlib
import json
import os
import select
import signal
import socket
import struct
import sys
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable

# ── Lazy engine import ──────────────────────────────────────────────────────────

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        sys.path.insert(0, str(Path(__file__).parent))
        import codex_engine
        _engine = codex_engine
    return _engine


# ── Configuration ───────────────────────────────────────────────────────────────

WORKSPACE = Path(os.environ.get('BELAM_WORKSPACE', Path.home() / '.openclaw/workspace'))
RUNTIME_DIR = WORKSPACE / '.codex_runtime'
RUNTIME_DIR.mkdir(exist_ok=True)
SOCKET_PATH = RUNTIME_DIR / 'render.sock'
PID_FILE = RUNTIME_DIR / 'render.pid'
TEST_MODE_FLAG = RUNTIME_DIR / 'test_mode'
CODEX_SNAPSHOT = WORKSPACE / 'CODEX.codex'


# ═══════════════════════════════════════════════════════════════════════════════
# §1  Data Structures
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PrimitiveNode:
    """Single primitive loaded into RAM."""
    coord: str
    prefix: str
    index: int
    slug: str
    filepath: str
    ptype: str
    frontmatter: dict
    body: list[str]
    content_hash: str
    mtime: float
    edges_out: list[str] = field(default_factory=list)
    edges_in: list[str] = field(default_factory=list)
    raw_text: str = ''


@dataclass
class DiffEntry:
    """Single change detected between disk and RAM."""
    kind: str        # 'modified', 'added', 'removed', 'reassigned'
    coord: str
    slug: str
    field_diffs: list = field(default_factory=list)  # [(field, old, new), ...]
    timestamp: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# §2  CodexTree — RAM Primitive Index
# ═══════════════════════════════════════════════════════════════════════════════

class CodexTree:
    """Full primitive tree held in RAM. Coordinate-addressable."""

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or WORKSPACE
        self.nodes: dict[str, PrimitiveNode] = {}
        self.by_slug: dict[str, PrimitiveNode] = {}
        self.by_prefix: dict[str, list[PrimitiveNode]] = {}
        self.namespace_counts: dict[str, int] = {}
        self.load_time: float = 0.0
        self.supermap_cache: str | None = None
        self._lock = threading.RLock()
        self._filepath_to_coord: dict[str, str] = {}
        self.test_mode: TestMode | None = None
        # D7: Per-node concurrency locks — two agents editing different coords don't block
        self._node_locks: dict[str, threading.Lock] = {}
        self._global_create_lock = threading.Lock()  # serialize node creation/deletion

    def load_full(self) -> None:
        """Load entire primitive tree from disk into RAM."""
        engine = _get_engine()
        t0 = time.time()

        with self._lock:
            self.nodes.clear()
            self.by_slug.clear()
            self.by_prefix.clear()
            self.namespace_counts.clear()
            self._filepath_to_coord.clear()
            self.supermap_cache = None

            for prefix in engine.NAMESPACE:
                primitives = engine.get_primitives(prefix, active_only=False)
                type_label = engine.NAMESPACE[prefix][0]
                ns_nodes = []

                for i, (slug, fp) in enumerate(primitives, 1):
                    coord = f"{prefix}{i}"
                    node = self._load_node(coord, prefix, i, slug, fp, type_label)
                    if node:
                        self.nodes[coord] = node
                        self.by_slug[slug] = node
                        self._filepath_to_coord[str(fp)] = coord
                        ns_nodes.append(node)

                self.by_prefix[prefix] = ns_nodes
                self.namespace_counts[prefix] = len(ns_nodes)

        self.load_time = time.time() - t0

    def _load_node(self, coord: str, prefix: str, index: int,
                   slug: str, filepath: Path, ptype: str) -> PrimitiveNode | None:
        """Load a single primitive from disk into a PrimitiveNode."""
        try:
            raw = self._read_file(filepath)
            if raw is None:
                return None
        except Exception:
            return None

        engine = _get_engine()
        fm_raw, body_str = engine.parse_frontmatter(raw)
        fm = dict(fm_raw) if fm_raw else {}
        body_lines = body_str.split('\n') if body_str else []
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()

        content_hash = hashlib.sha256(raw.encode('utf-8', errors='replace')).hexdigest()[:16]

        edges_out, edges_in = self._extract_edges(fm)

        try:
            mtime = filepath.stat().st_mtime
        except Exception:
            mtime = 0.0

        return PrimitiveNode(
            coord=coord, prefix=prefix, index=index,
            slug=slug, filepath=str(filepath), ptype=ptype,
            frontmatter=fm, body=body_lines,
            content_hash=content_hash, mtime=mtime,
            edges_out=edges_out, edges_in=edges_in,
            raw_text=raw,
        )

    def _read_file(self, filepath: Path) -> str | None:
        """Read file content, checking test mode overlay first."""
        fp = Path(filepath)
        if self.test_mode:
            relpath = str(fp.relative_to(self.workspace))
            content = self.test_mode.read(relpath)
            if content is not None:
                return content
        if fp.exists():
            return fp.read_text(encoding='utf-8', errors='replace')
        return None

    @staticmethod
    def _extract_edges(fm: dict) -> tuple[list[str], list[str]]:
        """Extract edge references from frontmatter."""
        out, inp = [], []
        for key in ('depends_on', 'related', 'refs', 'edges'):
            val = fm.get(key)
            if isinstance(val, list):
                out.extend(str(v) for v in val)
            elif isinstance(val, str) and val:
                out.append(val)
        return out, inp

    def get(self, coord: str) -> PrimitiveNode | None:
        return self.nodes.get(coord)

    def get_by_slug(self, slug: str) -> PrimitiveNode | None:
        return self.by_slug.get(slug)

    def get_namespace(self, prefix: str) -> list[PrimitiveNode]:
        return self.by_prefix.get(prefix, [])

    # ── D7: Per-node lock accessor ──────────────────────────────────────────
    def _get_node_lock(self, coord: str) -> threading.Lock:
        """Get or create a per-node lock. Thread-safe via global lock."""
        with self._global_create_lock:
            if coord not in self._node_locks:
                self._node_locks[coord] = threading.Lock()
            return self._node_locks[coord]

    # ── D1: RAM-first write path ────────────────────────────────────────────
    def apply_edits(self, coord: str, field_edits: list[dict],
                    body_op: dict | None = None) -> list[dict]:
        """Apply field edits and/or body operation to a node in RAM.

        Args:
            coord: coordinate string (e.g. 't5')
            field_edits: [{'field': 'status', 'value': 'active'}, ...]
            body_op: {'op': 'replace'|'append'|'line', 'value': '...', 'line': N}

        Returns:
            List of changes: [{'field': 'status', 'old': ..., 'new': ...}, ...]
        """
        with self._get_node_lock(coord):
            return self._apply_edits_unlocked(coord, field_edits, body_op)

    def _apply_edits_unlocked(self, coord: str, field_edits: list[dict],
                              body_op: dict | None = None) -> list[dict]:
        node = self.nodes.get(coord)
        if not node:
            raise KeyError(f"No node at {coord}")

        changes = []
        for edit in field_edits:
            field_key = edit['field']
            new_val = edit['value']
            old_val = node.frontmatter.get(field_key)
            node.frontmatter[field_key] = new_val
            changes.append({'field': field_key, 'old': old_val, 'new': new_val})

        if body_op:
            op = body_op['op']
            val = body_op['value']
            if op == 'replace':
                old_len = len(node.body)
                node.body = val.split('\n') if isinstance(val, str) else val
                changes.append({'field': 'body', 'op': 'replace',
                                'old_len': old_len, 'new_len': len(node.body)})
            elif op == 'append':
                added = val.split('\n') if isinstance(val, str) else val
                node.body.extend(added)
                changes.append({'field': 'body', 'op': 'append', 'added_len': len(added)})
            elif op == 'line':
                line_num = body_op.get('line', len(node.body))
                lines = node.body
                if 0 < line_num <= len(lines):
                    lines[line_num - 1] = val
                else:
                    lines.append(val)
                changes.append({'field': 'body', 'op': 'line', 'line': line_num})

        node.mtime = time.time()
        # Regenerate raw_text and content_hash
        node.raw_text = self._serialize_node(node)
        node.content_hash = hashlib.sha256(
            node.raw_text.encode('utf-8', errors='replace')).hexdigest()[:16]
        self.supermap_cache = None  # invalidate
        return changes

    def create_node(self, namespace: str, title: str,
                    frontmatter: dict, body: str = '') -> PrimitiveNode:
        """Create a new primitive in RAM and assign the next coordinate.

        Uses global lock to serialize coordinate allocation.
        """
        with self._global_create_lock:
            prefix = namespace
            existing = self.by_prefix.get(prefix, [])
            next_idx = len(existing) + 1
            coord = f"{prefix}{next_idx}"

            engine = _get_engine()
            ptype = engine.NAMESPACE.get(prefix, (prefix,))[0]

            fm = dict(frontmatter)
            fm.setdefault('primitive', ptype)
            slug = title.lower().replace(' ', '-')
            fm.setdefault('title', title)

            body_lines = body.split('\n') if isinstance(body, str) else body

            node = PrimitiveNode(
                coord=coord, prefix=prefix, index=next_idx,
                slug=slug, filepath='',  # set after flush
                ptype=ptype, frontmatter=fm, body=body_lines,
                content_hash='', mtime=time.time(),
            )
            node.raw_text = self._serialize_node(node)
            node.content_hash = hashlib.sha256(
                node.raw_text.encode('utf-8', errors='replace')).hexdigest()[:16]

            self.nodes[coord] = node
            self.by_slug[slug] = node
            if prefix not in self.by_prefix:
                self.by_prefix[prefix] = []
            self.by_prefix[prefix].append(node)
            self.namespace_counts[prefix] = len(self.by_prefix[prefix])
            self.supermap_cache = None
            return node

    def next_coord(self, prefix: str) -> str:
        """Return the next available coordinate for a namespace."""
        existing = self.by_prefix.get(prefix, [])
        return f"{prefix}{len(existing) + 1}"

    @staticmethod
    def _serialize_node(node: PrimitiveNode) -> str:
        """Serialize a PrimitiveNode to frontmatter + body markdown."""
        import yaml
        fm = dict(node.frontmatter)
        body_str = '\n'.join(node.body) if node.body else ''
        if fm:
            fm_text = yaml.dump(fm, default_flow_style=False,
                                allow_unicode=True, sort_keys=False,
                                width=float('inf')).rstrip('\n')
            result = f"---\n{fm_text}\n---\n"
        else:
            result = ''
        if body_str:
            result += body_str
        return result

    # ── D2: Snapshot load/save ──────────────────────────────────────────────
    def save_to_codex(self, path: Path | None = None) -> None:
        """Write all nodes to a .codex snapshot file for fast hydration."""
        path = path or CODEX_SNAPSHOT
        docs = []
        for coord in sorted(self.nodes.keys(),
                            key=lambda c: (c.rstrip('0123456789'), int(c.lstrip('abcdefghijklmnopqrstuvwxyz') or '0'))):
            node = self.nodes[coord]
            doc = dict(node.frontmatter)
            doc['__coord__'] = coord
            doc['__slug__'] = node.slug
            doc['__filepath__'] = node.filepath
            doc['__prefix__'] = node.prefix
            doc['__index__'] = node.index
            doc['__ptype__'] = node.ptype
            if node.body:
                doc['body'] = '\n'.join(node.body)
            docs.append(doc)
        from codex_codec import to_codex
        parts = [to_codex(d) for d in docs]
        path.write_text('\n---\n'.join(parts), encoding='utf-8')

    def load_from_codex(self, path: Path | None = None) -> bool:
        """Load tree from .codex snapshot. Returns True if successful."""
        path = path or CODEX_SNAPSHOT
        if not path.exists():
            return False
        try:
            import io
            from codex_codec import codex_to_json_stream
            content = path.read_text(encoding='utf-8')
            try:
                docs = list(codex_to_json_stream(io.StringIO(content)))
            except Exception:
                # .codex file malformed — fall back to disk scan
                return False
            with self._lock:
                self.nodes.clear()
                self.by_slug.clear()
                self.by_prefix.clear()
                self.namespace_counts.clear()
                self._filepath_to_coord.clear()

                for doc in docs:
                    coord = doc.pop('__coord__', None)
                    slug = doc.pop('__slug__', '')
                    filepath = doc.pop('__filepath__', '')
                    prefix = doc.pop('__prefix__', '')
                    index = doc.pop('__index__', 0)
                    ptype = doc.pop('__ptype__', '')
                    body_str = doc.pop('body', '')
                    body_lines = body_str.split('\n') if body_str else []

                    if not coord:
                        continue

                    fm = doc  # remaining keys are frontmatter
                    raw = self._serialize_node_from_parts(fm, body_lines)
                    content_hash = hashlib.sha256(
                        raw.encode('utf-8', errors='replace')).hexdigest()[:16]

                    node = PrimitiveNode(
                        coord=coord, prefix=prefix, index=index,
                        slug=slug, filepath=filepath, ptype=ptype,
                        frontmatter=fm, body=body_lines,
                        content_hash=content_hash,
                        mtime=Path(filepath).stat().st_mtime if filepath and Path(filepath).exists() else 0.0,
                        raw_text=raw,
                    )
                    self.nodes[coord] = node
                    self.by_slug[slug] = node
                    if filepath:
                        self._filepath_to_coord[filepath] = coord
                    if prefix not in self.by_prefix:
                        self.by_prefix[prefix] = []
                    self.by_prefix[prefix].append(node)

                for prefix in self.by_prefix:
                    self.namespace_counts[prefix] = len(self.by_prefix[prefix])

            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def _serialize_node_from_parts(fm: dict, body_lines: list[str]) -> str:
        import yaml
        body_str = '\n'.join(body_lines) if body_lines else ''
        if fm:
            fm_text = yaml.dump(fm, default_flow_style=False,
                                allow_unicode=True, sort_keys=False,
                                width=float('inf')).rstrip('\n')
            result = f"---\n{fm_text}\n---\n"
        else:
            result = ''
        if body_str:
            result += body_str
        return result

    def _scan_primitive_files(self) -> set[str]:
        """Scan disk for all primitive file stems (for ghost node detection)."""
        engine = _get_engine()
        files = set()
        for prefix, (_, directory, _) in engine.NAMESPACE.items():
            if directory is None:
                continue
            d = self.workspace / directory
            if d.is_dir():
                for f in d.iterdir():
                    if f.suffix == '.md' and not f.name.startswith('.'):
                        files.add(str(f))
        return files

    def apply_disk_change(self, filepath: Path) -> DiffEntry | None:
        """Update a single node from disk. Returns diff entry or None if unchanged."""
        fp_str = str(filepath)

        with self._lock:
            coord = self._filepath_to_coord.get(fp_str)

            if coord is None:
                # New file — need full namespace reindex
                prefix = self._filepath_to_prefix(filepath)
                if prefix:
                    return self._reindex_single_new(filepath, prefix)
                return None

            old_node = self.nodes.get(coord)
            if not old_node:
                return None

            try:
                raw = self._read_file(filepath)
                if raw is None:
                    return None
            except Exception:
                return None

            new_hash = hashlib.sha256(raw.encode('utf-8', errors='replace')).hexdigest()[:16]
            if new_hash == old_node.content_hash:
                return None

            engine = _get_engine()
            fm_raw, body_str = engine.parse_frontmatter(raw)
            fm = dict(fm_raw) if fm_raw else {}
            body_lines = body_str.split('\n') if body_str else []
            while body_lines and not body_lines[-1].strip():
                body_lines.pop()

            # Compute field diffs
            field_diffs = []
            for k in set(list(old_node.frontmatter.keys()) + list(fm.keys())):
                old_v = str(old_node.frontmatter.get(k, ''))
                new_v = str(fm.get(k, ''))
                if old_v != new_v:
                    field_diffs.append((k, old_v, new_v))

            # Update node in place
            old_node.frontmatter = fm
            old_node.body = body_lines
            old_node.content_hash = new_hash
            old_node.raw_text = raw
            old_node.edges_out, old_node.edges_in = self._extract_edges(fm)
            try:
                old_node.mtime = filepath.stat().st_mtime
            except Exception:
                pass

            self.supermap_cache = None

            return DiffEntry(
                kind='modified', coord=coord, slug=old_node.slug,
                field_diffs=field_diffs, timestamp=time.time(),
            )

    def apply_deletion(self, filepath: Path) -> DiffEntry | None:
        """Handle file deletion — remove node, trigger reindex."""
        fp_str = str(filepath)
        with self._lock:
            coord = self._filepath_to_coord.get(fp_str)
            if not coord:
                return None
            node = self.nodes.pop(coord, None)
            if not node:
                return None
            self.by_slug.pop(node.slug, None)
            del self._filepath_to_coord[fp_str]
            self.supermap_cache = None

            # FLAG-3: reindex namespace for DELETE events (coords shift)
            self.reindex_namespace(node.prefix)

            return DiffEntry(
                kind='removed', coord=coord, slug=node.slug,
                timestamp=time.time(),
            )

    def reindex_namespace(self, prefix: str) -> list[DiffEntry]:
        """Re-read a namespace from disk and reindex. Returns reassignment diffs."""
        engine = _get_engine()
        primitives = engine.get_primitives(prefix, active_only=False)
        type_label = engine.NAMESPACE[prefix][0]
        diffs = []

        # Remove old entries for this prefix
        old_coords = [c for c, n in self.nodes.items() if n.prefix == prefix]
        for c in old_coords:
            n = self.nodes.pop(c)
            self.by_slug.pop(n.slug, None)
            self._filepath_to_coord.pop(n.filepath, None)

        ns_nodes = []
        for i, (slug, fp) in enumerate(primitives, 1):
            coord = f"{prefix}{i}"
            node = self._load_node(coord, prefix, i, slug, fp, type_label)
            if node:
                self.nodes[coord] = node
                self.by_slug[slug] = node
                self._filepath_to_coord[str(fp)] = coord
                ns_nodes.append(node)

                # Check if this is a reassignment
                was_coord = None
                for oc in old_coords:
                    if oc != coord:
                        # check if same slug had different coord
                        pass
                # Simplified: just mark as reassigned if we care
                # (the diff engine captures the before/after anyway)

        self.by_prefix[prefix] = ns_nodes
        self.namespace_counts[prefix] = len(ns_nodes)
        self.supermap_cache = None
        return diffs

    def _reindex_single_new(self, filepath: Path, prefix: str) -> DiffEntry | None:
        """Handle a new file by reindexing its namespace."""
        # FLAG-3: CREATE events → reindex full namespace
        self.reindex_namespace(prefix)
        # Find the newly added node
        fp_str = str(filepath)
        coord = self._filepath_to_coord.get(fp_str)
        if coord and coord in self.nodes:
            node = self.nodes[coord]
            return DiffEntry(
                kind='added', coord=coord, slug=node.slug,
                timestamp=time.time(),
            )
        return None

    def _filepath_to_prefix(self, filepath: Path) -> str | None:
        """Determine which namespace prefix a filepath belongs to."""
        engine = _get_engine()
        try:
            rel = filepath.relative_to(self.workspace)
        except ValueError:
            return None
        rel_str = str(rel)
        for prefix, (_, directory, _) in engine.NAMESPACE.items():
            if rel_str.startswith(directory + '/') or rel_str.startswith(directory + os.sep):
                return prefix
        return None

    def render_supermap(self) -> str:
        """Render supermap from RAM tree (cached)."""
        if self.supermap_cache is not None:
            return self.supermap_cache

        engine = _get_engine()
        # Render from the engine (reads disk, but we could optimize later)
        content = engine.render_supermap()
        self.supermap_cache = content
        return content

    def to_codec_view(self, level: str = 'dense') -> str:
        """Compress tree into context-injectable format."""
        if level == 'dense':
            return self.render_supermap()
        elif level == 'summary':
            lines = [self.render_supermap(), '']
            for prefix in _get_engine().SHOW_ORDER:
                nodes = self.get_namespace(prefix)
                if nodes:
                    lines.append(f"## {prefix} — {len(nodes)} primitives")
                    for n in nodes[:10]:
                        status = n.frontmatter.get('status', '')
                        priority = n.frontmatter.get('priority', '')
                        lines.append(f"  {n.coord} {n.slug}  {status}/{priority}")
            return '\n'.join(lines)
        elif level == 'full':
            lines = [self.render_supermap(), '']
            for prefix in _get_engine().SHOW_ORDER:
                for n in self.get_namespace(prefix):
                    lines.append(f"### {n.coord} — {n.slug}")
                    for k, v in n.frontmatter.items():
                        lines.append(f"  {k}: {v}")
                    lines.append('')
            return '\n'.join(lines)
        elif level == 'deep':
            lines = [self.render_supermap(), '']
            for prefix in _get_engine().SHOW_ORDER:
                for n in self.get_namespace(prefix):
                    lines.append(f"### {n.coord} — {n.slug}")
                    lines.append(n.raw_text)
                    lines.append('')
            return '\n'.join(lines)
        return self.render_supermap()


# ═══════════════════════════════════════════════════════════════════════════════
# §3  Diff Engine — Anchor-Based Change Tracking
# ═══════════════════════════════════════════════════════════════════════════════

class DiffEngine:
    """Tracks changes relative to an anchor point."""

    def __init__(self, tree: CodexTree):
        self.tree = tree
        self._anchor_hashes: dict[str, str] = {}
        self._anchor_time: float = 0.0
        self._diffs: list[DiffEntry] = []
        self._lock = threading.Lock()

    def set_anchor(self) -> None:
        """Snapshot current tree state as the anchor."""
        with self._lock:
            self._anchor_hashes = {
                coord: node.content_hash
                for coord, node in self.tree.nodes.items()
            }
            self._anchor_time = time.time()
            self._diffs.clear()

    def record(self, entry: DiffEntry) -> None:
        with self._lock:
            self._diffs.append(entry)

    def get_delta(self) -> str:
        """Render accumulated diffs in Δ/+/− format."""
        with self._lock:
            if not self._diffs:
                return ''

            # Count distinct coords that changed
            changed_coords = set()
            for d in self._diffs:
                changed_coords.add(d.coord)

            lines = [f"R{{n}}Δ ({len(changed_coords)} coords shifted)"]
            for d in self._diffs:
                if d.kind == 'modified':
                    detail_parts = []
                    for fname, old_v, new_v in d.field_diffs:
                        detail_parts.append(f"{fname} {old_v}→{new_v}")
                    detail = '  '.join(detail_parts) if detail_parts else 'content changed'
                    lines.append(f"  Δ {d.coord:<5} {detail}")
                elif d.kind == 'added':
                    lines.append(f"  + {d.coord:<5} {d.slug}")
                elif d.kind == 'removed':
                    lines.append(f"  − {d.coord:<5} {d.slug} (removed)")
                elif d.kind == 'reassigned':
                    lines.append(f"  ↻ {d.coord:<5} {d.slug} (reassigned)")

            return '\n'.join(lines)

    def get_delta_since(self, timestamp: float) -> str:
        """Get diffs since a specific timestamp."""
        with self._lock:
            filtered = [d for d in self._diffs if d.timestamp >= timestamp]
            if not filtered:
                return ''
            lines = []
            for d in filtered:
                if d.kind == 'modified':
                    lines.append(f"  Δ {d.coord:<5} {d.slug}")
                elif d.kind == 'added':
                    lines.append(f"  + {d.coord:<5} {d.slug}")
                elif d.kind == 'removed':
                    lines.append(f"  − {d.coord:<5} {d.slug}")
            return '\n'.join(lines)

    def has_changes(self) -> bool:
        with self._lock:
            return len(self._diffs) > 0

    @property
    def anchor_time(self) -> float:
        return self._anchor_time


# ═══════════════════════════════════════════════════════════════════════════════
# §4  InotifyWatcher — Linux File Change Detection (ctypes, zero deps)
# ═══════════════════════════════════════════════════════════════════════════════

# inotify constants
IN_MODIFY    = 0x00000002
IN_CREATE    = 0x00000100
IN_DELETE    = 0x00000200
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO  = 0x00000080
IN_NONBLOCK  = 0x00000800
IN_CLOEXEC   = 0x00080000

# inotify_event header: int wd, uint32 mask, uint32 cookie, uint32 len
EVENT_HEADER_SIZE = struct.calcsize('iIII')


class InotifyWatcher:
    """Watch workspace directories for file changes using Linux inotify via ctypes."""

    def __init__(self, workspace: Path, callback: Callable[[Path, str], None]):
        self.workspace = workspace
        self.callback = callback
        self._fd: int = -1
        self._watches: dict[int, Path] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        self._coalesce_window = 0.1  # 100ms

    def start(self) -> None:
        """Initialize inotify fd, add watches for all namespace directories."""
        libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
        self._inotify_init1 = libc.inotify_init1
        self._inotify_init1.argtypes = [ctypes.c_int]
        self._inotify_init1.restype = ctypes.c_int

        self._inotify_add_watch = libc.inotify_add_watch
        self._inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        self._inotify_add_watch.restype = ctypes.c_int

        self._fd = self._inotify_init1(IN_NONBLOCK | IN_CLOEXEC)
        if self._fd < 0:
            raise OSError(f"inotify_init1 failed: errno {ctypes.get_errno()}")

        mask = IN_MODIFY | IN_CREATE | IN_DELETE | IN_MOVED_FROM | IN_MOVED_TO

        engine = _get_engine()
        watched_dirs = set()

        for prefix, (_, directory, special) in engine.NAMESPACE.items():
            if directory is None:
                continue
            dirpath = self.workspace / directory
            if dirpath.exists() and dirpath.is_dir():
                watched_dirs.add(dirpath)

        # Also watch workspace root for context files (SOUL.md, AGENTS.md, etc.)
        watched_dirs.add(self.workspace)

        for dirpath in watched_dirs:
            wd = self._inotify_add_watch(
                self._fd,
                str(dirpath).encode('utf-8'),
                mask,
            )
            if wd >= 0:
                self._watches[wd] = dirpath

        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True, name='inotify')
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1

    def _watch_loop(self) -> None:
        """Read events from inotify fd, coalesce within 100ms window."""
        pending: dict[str, str] = {}  # filepath → event_type

        while self._running:
            try:
                readable, _, _ = select.select([self._fd], [], [], 1.0)
            except (ValueError, OSError):
                break

            if not readable:
                # Flush pending on timeout too
                if pending:
                    self._flush_pending(pending)
                    pending.clear()
                continue

            try:
                buf = os.read(self._fd, 8192)
            except OSError:
                continue

            events = self._parse_events(buf)
            for filepath, event_type in events:
                pending[str(filepath)] = event_type

            # Wait coalesce window, then flush
            time.sleep(self._coalesce_window)

            # Read any additional events that arrived during coalesce
            try:
                while True:
                    readable2, _, _ = select.select([self._fd], [], [], 0)
                    if not readable2:
                        break
                    buf2 = os.read(self._fd, 8192)
                    for fp, et in self._parse_events(buf2):
                        pending[str(fp)] = et
            except OSError:
                pass

            self._flush_pending(pending)
            pending.clear()

    def _flush_pending(self, pending: dict[str, str]) -> None:
        for fp_str, event_type in pending.items():
            try:
                self.callback(Path(fp_str), event_type)
            except Exception:
                pass

    def _parse_events(self, buf: bytes) -> list[tuple[Path, str]]:
        """Parse raw inotify_event structs."""
        events = []
        offset = 0
        while offset < len(buf):
            if offset + EVENT_HEADER_SIZE > len(buf):
                break
            wd, mask, cookie, name_len = struct.unpack_from('iIII', buf, offset)
            offset += EVENT_HEADER_SIZE
            if name_len > 0:
                name_bytes = buf[offset:offset + name_len]
                offset += name_len
                name = name_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='replace')
            else:
                name = ''
                offset += name_len

            if not name:
                continue

            dirpath = self._watches.get(wd)
            if not dirpath:
                continue

            filepath = dirpath / name

            if mask & IN_MODIFY:
                events.append((filepath, 'modified'))
            elif mask & (IN_CREATE | IN_MOVED_TO):
                events.append((filepath, 'created'))
            elif mask & (IN_DELETE | IN_MOVED_FROM):
                events.append((filepath, 'deleted'))

        return events


class StatPoller:
    """Fallback: poll file mtimes every 500ms."""

    def __init__(self, workspace: Path, callback: Callable[[Path, str], None]):
        self.workspace = workspace
        self.callback = callback
        self._mtimes: dict[str, float] = {}
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._running = True
        self._scan_all()  # initial snapshot
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name='statpoll')
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _scan_all(self) -> dict[str, float]:
        """Scan all namespace dirs, return filepath→mtime."""
        engine = _get_engine()
        current = {}
        for prefix, (_, directory, _) in engine.NAMESPACE.items():
            if directory is None:
                continue
            dirpath = self.workspace / directory
            if dirpath.exists() and dirpath.is_dir():
                for f in dirpath.iterdir():
                    if f.is_file() and f.suffix == '.md':
                        try:
                            current[str(f)] = f.stat().st_mtime
                        except OSError:
                            pass
        # Context files
        for fname in ('SOUL.md', 'IDENTITY.md', 'USER.md', 'TOOLS.md', 'AGENTS.md'):
            fp = self.workspace / fname
            if fp.exists():
                try:
                    current[str(fp)] = fp.stat().st_mtime
                except OSError:
                    pass
        return current

    def _poll_loop(self) -> None:
        while self._running:
            time.sleep(0.5)
            current = self._scan_all()

            # Detect modifications and new files
            for fp_str, mtime in current.items():
                old_mtime = self._mtimes.get(fp_str)
                if old_mtime is None:
                    self.callback(Path(fp_str), 'created')
                elif mtime != old_mtime:
                    self.callback(Path(fp_str), 'modified')

            # Detect deletions
            for fp_str in set(self._mtimes) - set(current):
                self.callback(Path(fp_str), 'deleted')

            self._mtimes = current


# ═══════════════════════════════════════════════════════════════════════════════
# §5  Session Manager — UDS Multi-Agent Server
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentSession:
    """One agent's connection to the render engine."""
    session_id: str
    agent_name: str
    connected_at: float
    last_active: float
    anchor_time: float
    subscribe_patterns: list = field(default_factory=list)  # Phase 2: pattern filter


class SessionManager:
    """Manages multiple agent connections via Unix domain socket."""

    def __init__(self, tree: CodexTree, diff_engine: DiffEngine,
                 context_assembler: ContextAssembler | None = None):
        self.tree = tree
        self.diff_engine = diff_engine
        self.context = context_assembler
        self._sessions: dict[str, AgentSession] = {}
        self._client_conns: dict[str, socket.socket] = {}
        self._server_sock: socket.socket | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        # Engine-level refs (set by CodexRenderEngine after construction)
        self._engine_ref = None

    def start(self) -> None:
        """Bind UDS, start accept thread."""
        if SOCKET_PATH.exists():
            # Check if stale
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect(str(SOCKET_PATH))
                s.close()
                raise RuntimeError("Another render engine is already running")
            except (ConnectionRefusedError, OSError):
                SOCKET_PATH.unlink(missing_ok=True)

        self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(str(SOCKET_PATH))
        self._server_sock.listen(5)
        self._server_sock.settimeout(1.0)

        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True, name='uds-accept')
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        # Close all client connections
        with self._lock:
            for sid, conn in self._client_conns.items():
                try:
                    conn.close()
                except Exception:
                    pass
            self._client_conns.clear()
            self._sessions.clear()

        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
        SOCKET_PATH.unlink(missing_ok=True)

    def notify_all(self, msg: dict) -> None:
        """Send a notification to all connected clients."""
        data = (json.dumps(msg) + '\n').encode('utf-8')
        with self._lock:
            dead = []
            for sid, conn in self._client_conns.items():
                try:
                    conn.sendall(data)
                except Exception:
                    dead.append(sid)
            for sid in dead:
                self._client_conns.pop(sid, None)
                self._sessions.pop(sid, None)

    # ── D1/D6: Flush a single node from RAM to disk ────────────────────────
    def _flush_to_disk(self, coord: str) -> None:
        """Write a single node from RAM to its disk file. Synchronous.

        D6: Suppressed in test mode (dulwich overlay handles writes).
        FLAG-2 (LOW): logs warning on failure — RAM stays correct.
        """
        # D6: Test mode flush suppression
        if self._engine_ref and self._engine_ref.test and self._engine_ref.test.is_active():
            return
        node = self.tree.get(coord)
        if not node or not node.filepath:
            return
        try:
            content = node.raw_text or CodexTree._serialize_node(node)
            Path(node.filepath).write_text(content, encoding='utf-8')
        except Exception as e:
            import logging
            logging.getLogger('codex_render').warning(f"Flush failed for {coord}: {e}")

    def _accept_loop(self) -> None:
        while self._running:
            try:
                conn, _ = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
            t.start()

    def _handle_client(self, conn: socket.socket) -> None:
        """Handle one agent's session."""
        conn.settimeout(30.0)
        session_id = uuid.uuid4().hex[:12]
        buf = b''

        try:
            while self._running:
                try:
                    chunk = conn.recv(65536)
                except socket.timeout:
                    continue
                if not chunk:
                    break

                buf += chunk
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    if not line.strip():
                        continue
                    # D3: Raw ping support (backwards compat with cockpit plugin)
                    if line.strip() == b'ping':
                        try:
                            conn.sendall(b'pong\n')
                        except Exception:
                            pass
                        continue
                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        self._send(conn, {'ok': False, 'error': 'invalid JSON'})
                        continue

                    resp = self._dispatch(msg, session_id, conn)
                    self._send(conn, resp)
        except Exception:
            pass
        finally:
            with self._lock:
                self._client_conns.pop(session_id, None)
                self._sessions.pop(session_id, None)
            try:
                conn.close()
            except Exception:
                pass

    def _dispatch(self, msg: dict, session_id: str, conn: socket.socket) -> dict:
        """Dispatch a client command."""
        cmd = msg.get('cmd', '')

        if cmd == 'attach':
            agent = msg.get('agent', 'unknown')
            now = time.time()
            session = AgentSession(
                session_id=session_id, agent_name=agent,
                connected_at=now, last_active=now,
                anchor_time=self.diff_engine.anchor_time,
            )
            with self._lock:
                self._sessions[session_id] = session
                self._client_conns[session_id] = conn
            return {'ok': True, 'session_id': session_id, 'tree_size': len(self.tree.nodes)}

        elif cmd == 'tree':
            coord = msg.get('coord')
            prefix = msg.get('prefix')
            if coord:
                node = self.tree.get(coord)
                if node:
                    return {'ok': True, 'node': _node_to_dict(node)}
                return {'ok': False, 'error': f'coord {coord} not found'}
            elif prefix:
                nodes = self.tree.get_namespace(prefix)
                return {'ok': True, 'nodes': [_node_to_dict(n) for n in nodes]}
            return {'ok': False, 'error': 'specify coord or prefix'}

        elif cmd == 'supermap':
            return {'ok': True, 'content': self.tree.render_supermap()}

        elif cmd == 'diff':
            return {'ok': True, 'delta': self.diff_engine.get_delta()}

        elif cmd == 'diff_since':
            ts = msg.get('timestamp', 0.0)
            return {'ok': True, 'delta': self.diff_engine.get_delta_since(ts)}

        elif cmd == 'anchor_reset':
            self.diff_engine.set_anchor()
            return {'ok': True, 'message': 'anchor reset'}

        elif cmd == 'refresh':
            # Phase 2: Hint to re-scan a specific file or namespace.
            # Used by orchestration_engine._post_state_change() for sub-100ms
            # R-label latency after F-label generation (instead of anchor_reset
            # which would wipe the diff buffer — Critic FLAG-1).
            filepath = msg.get('filepath')
            prefix = msg.get('prefix')
            if filepath:
                p = Path(filepath)
                if p.exists():
                    diff = self.tree.apply_disk_change(p)
                    if diff:
                        self.diff_engine.record(diff)
                        self.notify_all({'event': 'change', 'diff': asdict(diff)})
                    return {'ok': True, 'refreshed': filepath}
                return {'ok': False, 'error': f'file not found: {filepath}'}
            elif prefix:
                nodes = self.tree.get_namespace(prefix)
                count = len(nodes) if nodes else 0
                return {'ok': True, 'reindexed': count}
            return {'ok': False, 'error': 'specify filepath or prefix'}

        elif cmd == 'subscribe':
            # Phase 2: Explicit subscription with optional pattern filtering.
            # Clients already receive push notifications via attach, but this
            # allows filtering by coordinate prefix patterns.
            patterns = msg.get('patterns', [])
            with self._lock:
                session = self._sessions.get(session_id)
                if session:
                    session.subscribe_patterns = patterns
            return {'ok': True, 'patterns': patterns}

        elif cmd == 'codec':
            level = msg.get('level', 'dense')
            prefix = msg.get('prefix')
            return {'ok': True, 'content': self.tree.to_codec_view(level)}

        elif cmd == 'context':
            if self.context:
                mode = msg.get('mode', 'codex')
                return {'ok': True, 'content': self.context.assemble(mode=mode)}
            return {'ok': False, 'error': 'context assembler not available'}

        elif cmd == 'buffer':
            fmt = msg.get('format', 'dense')
            if fmt == 'dense':
                return {'ok': True, 'content': self.tree.render_supermap()}
            elif fmt == 'diff':
                return {'ok': True, 'content': self.diff_engine.get_delta()}
            elif fmt == 'json':
                nodes = []
                for prefix in _get_engine().SHOW_ORDER:
                    for n in self.tree.get_namespace(prefix):
                        nodes.append(_node_to_dict(n))
                return {'ok': True, 'content': json.dumps(nodes)}
            return {'ok': True, 'content': self.tree.render_supermap()}

        elif cmd == 'status':
            test_mode = False
            test_status = None
            if self._engine_ref and self._engine_ref.test:
                test_mode = True
                test_status = self._engine_ref.test.status()
            return {
                'ok': True,
                'sessions': len(self._sessions),
                'tree_size': len(self.tree.nodes),
                'uptime_s': time.time() - self.diff_engine.anchor_time,
                'diffs': len(self.diff_engine._diffs),
                'test_mode': test_mode,
                'test_status': test_status,
            }

        elif cmd == 'test_write':
            if self._engine_ref and self._engine_ref.test:
                fp = msg.get('filepath', '')
                content = msg.get('content', '')
                self._engine_ref.test.write(fp, content)
                # Also update tree
                abs_path = self.tree.workspace / fp
                diff = self.tree.apply_disk_change(abs_path)
                if diff:
                    self.diff_engine.record(diff)
                return {'ok': True}
            return {'ok': False, 'error': 'not in test mode'}

        elif cmd == 'test_commit':
            if self._engine_ref and self._engine_ref.test:
                commit_msg = msg.get('message', 'test mode commit')
                sha = self._engine_ref.test.commit(commit_msg)
                return {'ok': True, 'commit': sha}
            return {'ok': False, 'error': 'not in test mode'}

        elif cmd == 'test_discard':
            if self._engine_ref and self._engine_ref.test:
                self._engine_ref.test.discard()
                self.tree.load_full()
                self.diff_engine.set_anchor()
                return {'ok': True}
            return {'ok': False, 'error': 'not in test mode'}

        elif cmd == 'stop':
            if self._engine_ref:
                self._engine_ref._running = False
            return {'ok': True, 'message': 'shutdown initiated'}

        elif cmd == 'detach':
            return {'ok': True, 'message': 'detached'}

        # ── D3: ping/pong health check ──────────────────────────────
        elif cmd == 'ping':
            uptime = time.time() - self._engine_ref._start_time if self._engine_ref else 0
            return {'ok': True, 'msg': 'pong',
                    'uptime': uptime, 'nodes': len(self.tree.nodes)}

        # ── D3: per-session diff (uses agent's own anchor) ──────────
        elif cmd == 'my_diff':
            with self._lock:
                session = self._sessions.get(session_id)
            if session:
                return {'ok': True,
                        'delta': self.diff_engine.get_delta_since(session.anchor_time)}
            return {'ok': False, 'error': 'not attached — call attach first'}

        # ── D1: RAM-first write (edit existing node) ────────────────
        elif cmd == 'write':
            coord = msg.get('coord')
            edits = msg.get('edits', [])
            body_op = msg.get('body_op')
            node = self.tree.get(coord)
            if not node:
                return {'ok': False, 'error': f'coord {coord} not found'}
            try:
                changes = self.tree.apply_edits(coord, edits, body_op)
            except Exception as e:
                return {'ok': False, 'error': str(e)}
            diff = DiffEntry(kind='modified', coord=coord,
                             slug=node.slug,
                             field_diffs=[(c['field'], c.get('old'), c.get('new')) for c in changes],
                             timestamp=time.time())
            self.diff_engine.record(diff)
            self.notify_all({'event': 'change', 'diff': asdict(diff)})
            self._flush_to_disk(coord)
            return {'ok': True, 'coord': coord, 'changes': len(changes)}

        # ── D1: RAM-first create (new primitive) ────────────────────
        elif cmd == 'create':
            namespace = msg.get('namespace')
            title = msg.get('title', 'untitled')
            frontmatter = msg.get('frontmatter', {})
            body = msg.get('body', '')
            if not namespace:
                return {'ok': False, 'error': 'namespace required'}
            try:
                node = self.tree.create_node(namespace, title, frontmatter, body)
            except Exception as e:
                return {'ok': False, 'error': str(e)}
            diff = DiffEntry(kind='added', coord=node.coord,
                             slug=node.slug,
                             field_diffs=[('__created__', None, title)],
                             timestamp=time.time())
            self.diff_engine.record(diff)
            self.notify_all({'event': 'create', 'diff': asdict(diff)})
            self._flush_to_disk(node.coord)
            return {'ok': True, 'coord': node.coord, 'title': title}

        return {'ok': False, 'error': f'unknown command: {cmd}'}

    @staticmethod
    def _send(conn: socket.socket, msg: dict) -> None:
        try:
            data = (json.dumps(msg) + '\n').encode('utf-8')
            conn.sendall(data)
        except Exception:
            pass


def _json_safe(obj):
    """Make an object JSON-serializable (handle datetime, Path, etc.)."""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def _node_to_dict(node: PrimitiveNode) -> dict:
    """Serialize a PrimitiveNode to a JSON-safe dict (omitting raw_text for size)."""
    return {
        'coord': node.coord,
        'prefix': node.prefix,
        'index': node.index,
        'slug': node.slug,
        'ptype': node.ptype,
        'frontmatter': _json_safe(node.frontmatter),
        'content_hash': node.content_hash,
        'mtime': node.mtime,
        'edges_out': node.edges_out,
        'edges_in': node.edges_in,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# §6  Test Mode — dulwich Overlay Branch
# ═══════════════════════════════════════════════════════════════════════════════

class TestMode:
    """In-memory overlay for risk-free experimentation.

    Uses a dict overlay with read-through to disk.
    Commit merges overlay to disk via dulwich.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.branch_name: str = ''
        self.base_commit: str = ''
        self._overlay: dict[str, str] = {}
        self._deleted: set[str] = set()

    def start(self) -> str:
        """Initialize test mode. Create flag file (FLAG-1)."""
        self.branch_name = f'test/session-{uuid.uuid4().hex[:8]}'

        # Try to read HEAD from git
        try:
            from dulwich.repo import Repo
            repo = Repo(str(self.workspace))
            self.base_commit = repo.head().decode('ascii')
        except Exception:
            self.base_commit = 'no-git'

        # FLAG-1: Create flag file so engine can check test mode with stat() not UDS
        TEST_MODE_FLAG.write_text(self.branch_name, encoding='utf-8')

        return self.branch_name

    def write(self, filepath: str, content: str) -> None:
        """Intercept a write — store in RAM overlay."""
        self._overlay[filepath] = content
        self._deleted.discard(filepath)

    def read(self, filepath: str) -> str | None:
        """Read from overlay first, then disk."""
        if filepath in self._deleted:
            return None
        if filepath in self._overlay:
            return self._overlay[filepath]
        disk_path = self.workspace / filepath
        if disk_path.exists():
            return disk_path.read_text(encoding='utf-8', errors='replace')
        return None

    def delete(self, filepath: str) -> None:
        self._deleted.add(filepath)
        self._overlay.pop(filepath, None)

    def commit(self, message: str = 'test mode commit') -> str:
        """Merge RAM overlay to disk, then git commit via dulwich."""
        # Write overlay to disk
        for relpath, content in self._overlay.items():
            target = self.workspace / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')

        # Apply deletions
        for relpath in self._deleted:
            target = self.workspace / relpath
            if target.exists():
                target.unlink()

        # Git commit via dulwich
        sha = 'no-git'
        try:
            from dulwich.repo import Repo
            repo = Repo(str(self.workspace))
            all_paths = list(self._overlay.keys()) + list(self._deleted)
            repo.stage([p.encode('utf-8') if isinstance(p, str) else p for p in all_paths])
            commit_sha = repo.do_commit(
                message.encode('utf-8'),
                committer=b'codex-render <render@belam>',
            )
            sha = commit_sha.decode('ascii') if isinstance(commit_sha, bytes) else str(commit_sha)
        except Exception as exc:
            sha = f'commit-failed: {exc}'

        self._overlay.clear()
        self._deleted.clear()
        self._cleanup_flag()
        return sha

    def discard(self) -> None:
        """Discard all changes."""
        self._overlay.clear()
        self._deleted.clear()
        self._cleanup_flag()

    def is_active(self) -> bool:
        """D6: Check if test mode is currently active (has a branch)."""
        return bool(self.branch_name)

    def status(self) -> dict:
        return {
            'branch': self.branch_name,
            'modified': len(self._overlay),
            'deleted': len(self._deleted),
            'base_commit': self.base_commit,
            'files': list(self._overlay.keys()),
        }

    def _cleanup_flag(self) -> None:
        """Remove test mode flag file."""
        TEST_MODE_FLAG.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# §7  Context Assembler — Replaces Manual File Loading
# ═══════════════════════════════════════════════════════════════════════════════

class ContextAssembler:
    """Assembles agent context from the RAM tree."""

    CONTEXT_FILES = [
        ('SOUL.md',     'soul',     True),
        ('IDENTITY.md', 'identity', True),
        ('USER.md',     'user',     True),
        ('TOOLS.md',    'tools',    False),
    ]

    def __init__(self, workspace: Path, tree: CodexTree, diff_engine: DiffEngine):
        self.workspace = workspace
        self.tree = tree
        self.diff_engine = diff_engine
        self._context_cache: dict[str, str] = {}
        self._context_hashes: dict[str, str] = {}

    def assemble(self, agent: str = 'main',
                 include_memory: bool = True,
                 budget_tokens: int | None = None,
                 mode: str = 'codex') -> str:
        """Assemble context for an agent.

        mode='codex'  — mirrors the new codex layer injection protocol:
                        legend (prependSystemContext) + stubs + supermap + diffs
        mode='legacy' — full raw workspace file injection (old behavior)
        """
        if mode == 'legacy':
            return self._assemble_legacy(agent, include_memory, budget_tokens)

        # ── Codex layer mode: mirrors what the agent actually sees ──
        sections = []

        # 1. Dense legend (prependSystemContext)
        legend = self._load_context_file('codex_legend.md')
        if legend:
            sections.append(f"## prependSystemContext (legend)\n\n{legend}")
        else:
            sections.append("<!-- codex_legend.md not found — legend not injected -->")

        # 2. Project Context section (what bootstrapFiles array produces)
        stubs = []
        stubs.append("## Project Context (bootstrapFiles)\n")
        stubs.append(f"### AGENTS.md (stub)\n# Codex Layer Active\nRead your role primitive: agents/{agent}.md")

        # CODEX.codex — supermap from RAM tree
        supermap = self.tree.render_supermap()
        stubs.append(f"### CODEX.codex\n```\n{supermap}\n```")

        # HEARTBEAT.md — stays as-is
        heartbeat = self._load_context_file('HEARTBEAT.md')
        if heartbeat:
            stubs.append(f"### HEARTBEAT.md\n{heartbeat}")

        # MEMORY.md — compressed boot index
        try:
            import subprocess
            mem_index = subprocess.check_output(
                ['python3', 'scripts/codex_engine.py', '--memory-boot-index'],
                cwd=str(self.workspace), timeout=10, encoding='utf-8'
            ).strip()
            stubs.append(f"### MEMORY.md (boot index)\n{mem_index}")
        except Exception:
            stubs.append("### MEMORY.md (stub)\nMemory: check memory/ directory for today + yesterday.")

        # Stubs for replaced files
        for fname in ('SOUL.md', 'IDENTITY.md', 'USER.md', 'TOOLS.md'):
            stubs.append(f"### {fname}\n[Legend active — injected via before_prompt_build]")

        sections.append('\n\n'.join(stubs))

        # 3. appendSystemContext — diffs
        delta = self.diff_engine.get_delta()
        if delta:
            sections.append(f"## appendSystemContext (diffs)\n\n```\n{delta}\n```")

        full = '\n\n---\n\n'.join(sections)

        if budget_tokens and self._estimate_tokens(full) > budget_tokens:
            full = self._compress_to_budget(sections, budget_tokens)

        return full

    def _assemble_legacy(self, agent: str = 'main',
                         include_memory: bool = True,
                         budget_tokens: int | None = None) -> str:
        """Legacy assembly — full raw workspace files (old behavior)."""
        sections = []

        for filename, key, required in self.CONTEXT_FILES:
            content = self._load_context_file(filename)
            if content:
                sections.append(content)
            elif required:
                sections.append(f"<!-- {filename} not found -->")

        supermap = self.tree.render_supermap()
        sections.append(f"## Codex Engine Supermap\n\n```\n{supermap}\n```")

        if include_memory:
            mem = self._assemble_memory()
            if mem:
                sections.append(mem)

        delta = self.diff_engine.get_delta()
        if delta:
            sections.append(f"## Changes Since Last Context\n\n```\n{delta}\n```")

        full = '\n\n---\n\n'.join(sections)

        if budget_tokens and self._estimate_tokens(full) > budget_tokens:
            full = self._compress_to_budget(sections, budget_tokens)

        return full

    def _load_context_file(self, filename: str) -> str | None:
        """Load a context file with hash-based caching."""
        path = self.workspace / filename
        if not path.exists():
            return None
        try:
            raw = path.read_bytes()
        except Exception:
            return None
        current_hash = hashlib.sha256(raw).hexdigest()[:12]
        if self._context_hashes.get(filename) == current_hash:
            return self._context_cache.get(filename)
        content = raw.decode('utf-8', errors='replace')
        self._context_cache[filename] = content
        self._context_hashes[filename] = current_hash
        return content

    def invalidate_context_file(self, filename: str) -> None:
        """FLAG-2: Explicit invalidation for context files on inotify events."""
        self._context_hashes.pop(filename, None)
        self._context_cache.pop(filename, None)

    def _assemble_memory(self) -> str | None:
        """Assemble memory section from RAM tree's daily namespace."""
        today = datetime.date.today().strftime('%Y-%m-%d')
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        sections = []
        for date_str in [today, yesterday]:
            node = self.tree.get_by_slug(date_str)
            if node and node.raw_text:
                sections.append(f"### Memory: {date_str}\n\n{node.raw_text}")

        return '\n\n'.join(sections) if sections else None

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return int(len(text) / 3.5)

    def _compress_to_budget(self, sections: list[str], budget: int) -> str:
        """Progressively compress sections to fit token budget."""
        # Strategy: drop optional sections, truncate large ones
        result_sections = list(sections)

        # 1. Drop TOOLS.md (index 3 if present)
        if len(result_sections) > 3:
            tools_idx = 3
            result = '\n\n---\n\n'.join(result_sections[:tools_idx] + result_sections[tools_idx + 1:])
            if self._estimate_tokens(result) <= budget:
                return result

        # 2. Truncate memory section
        for i, s in enumerate(result_sections):
            if s.startswith('### Memory:'):
                result_sections[i] = s[:500] + '\n...(truncated)'

        # 3. Compress supermap
        for i, s in enumerate(result_sections):
            if 'Codex Engine Supermap' in s:
                result_sections[i] = f"## Codex Engine Supermap\n\n```\n{self.tree.to_codec_view('dense')}\n```"

        result = '\n\n---\n\n'.join(result_sections)
        if self._estimate_tokens(result) > budget:
            result = result[:int(budget * 3.5)]
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# §8  Dashboard Server — Buffer Exposure for Canvas/tmux
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardServer:
    """Exposes render buffer for canvas/tmux consumption."""

    def __init__(self, tree: CodexTree, diff_engine: DiffEngine):
        self.tree = tree
        self.diff_engine = diff_engine

    def get_buffer(self, fmt: str = 'dense') -> str:
        if fmt == 'dense':
            return self.tree.render_supermap()
        elif fmt == 'json':
            nodes = []
            for prefix in _get_engine().SHOW_ORDER:
                for n in self.tree.get_namespace(prefix):
                    nodes.append(_node_to_dict(n))
            return json.dumps(nodes, indent=2)
        elif fmt == 'pretty':
            lines = ['# Codex Render Buffer\n']
            for prefix in _get_engine().SHOW_ORDER:
                ns = self.tree.get_namespace(prefix)
                if ns:
                    lines.append(f"## {_get_engine().NAMESPACE[prefix][0]} ({len(ns)})")
                    for n in ns:
                        status = n.frontmatter.get('status', '')
                        lines.append(f"- **{n.coord}** {n.slug} — {status}")
                    lines.append('')
            return '\n'.join(lines)
        elif fmt == 'diff':
            return self.diff_engine.get_delta() or '(no changes since anchor)'
        elif fmt == 'status':
            return json.dumps({
                'tree_size': len(self.tree.nodes),
                'uptime_s': time.time() - self.diff_engine.anchor_time,
                'diffs': len(self.diff_engine._diffs),
            }, indent=2)
        return self.tree.render_supermap()


# ═══════════════════════════════════════════════════════════════════════════════
# §9  CodexRenderEngine — Main Process Orchestration
# ═══════════════════════════════════════════════════════════════════════════════

# Context file names to watch for invalidation (FLAG-2)
CONTEXT_FILENAMES = {'SOUL.md', 'IDENTITY.md', 'USER.md', 'TOOLS.md', 'AGENTS.md', 'MEMORY.md'}


class CodexRenderEngine:
    """Main render engine process. Foreground, session-scoped."""

    def __init__(self, workspace: Path, test_mode: bool = False):
        self.workspace = workspace
        self.tree = CodexTree(workspace)
        self.diff_engine = DiffEngine(self.tree)
        self.context = ContextAssembler(workspace, self.tree, self.diff_engine)
        self.dashboard = DashboardServer(self.tree, self.diff_engine)
        self.watcher: InotifyWatcher | StatPoller | None = None
        self.sessions = SessionManager(self.tree, self.diff_engine, self.context)
        self.sessions._engine_ref = self
        self.test: TestMode | None = None
        self._running = False
        self._start_time = 0.0

        if test_mode:
            self.test = TestMode(workspace)
            self.tree.test_mode = self.test

    def start(self) -> None:
        """Boot sequence."""
        self._start_time = time.time()

        # 1. D2: Try .codex snapshot hydration (fast path), fall back to disk scan
        hydrated = False
        if CODEX_SNAPSHOT.exists():
            try:
                snapshot_mtime = CODEX_SNAPSHOT.stat().st_mtime
                # Check if any primitive file is newer than snapshot
                disk_files = self.tree._scan_primitive_files()
                if disk_files:
                    latest_disk = max(Path(f).stat().st_mtime for f in disk_files if Path(f).exists())
                else:
                    latest_disk = 0
                if snapshot_mtime >= latest_disk:
                    if self.tree.load_from_codex(CODEX_SNAPSHOT):
                        # FLAG-1 (MED): Ghost node detection — compare file count
                        snapshot_files = {n.filepath for n in self.tree.nodes.values() if n.filepath}
                        if len(snapshot_files - disk_files) == 0:
                            hydrated = True
                        else:
                            # Ghost nodes detected — rebuild from disk
                            pass
            except Exception:
                pass

        if not hydrated:
            self.tree.load_full()
            # Write fresh snapshot for next startup
            try:
                self.tree.save_to_codex()
            except Exception:
                pass

        # 2. Anchor
        self.diff_engine.set_anchor()

        # 3. File watcher
        watcher_type = 'poll'
        try:
            self.watcher = InotifyWatcher(self.workspace, self._on_file_change)
            self.watcher.start()
            watcher_type = 'inotify'
        except Exception:
            self.watcher = StatPoller(self.workspace, self._on_file_change)
            self.watcher.start()

        # 4. Session server
        self.sessions.start()

        # 5. Test mode
        if self.test:
            branch = self.test.start()
            print(f"Test mode: branch {branch}")

        # 6. Boot status
        print(f"Codex Render Engine started")
        print(f"  Tree: {len(self.tree.nodes)} primitives loaded in {self.tree.load_time:.2f}s")
        print(f"  Watcher: {watcher_type}")
        print(f"  Socket: {SOCKET_PATH}")
        if self.test:
            print(f"  Test mode: {self.test.branch_name}")

        self._running = True

        # 7. Main loop
        self._main_loop()

    def _main_loop(self) -> None:
        """Block until SIGINT/SIGTERM."""
        def _shutdown(signum, frame):
            print("\nShutting down...")
            self._running = False

        def _status(signum, frame):
            self._print_status()

        def _anchor_reset(signum, frame):
            self.diff_engine.set_anchor()
            print("Diff anchor reset.")

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGUSR1, _status)
        signal.signal(signal.SIGUSR2, _anchor_reset)

        while self._running:
            time.sleep(0.5)

        self._cleanup()

    def _cleanup(self) -> None:
        """Clean shutdown."""
        if self.test and self.test._overlay:
            print(f"Test mode has {len(self.test._overlay)} uncommitted changes — discarding.")
            self.test.discard()

        # D2: Save .codex snapshot on shutdown for fast restart
        try:
            self.tree.save_to_codex()
        except Exception:
            pass

        self.sessions.stop()
        if self.watcher:
            self.watcher.stop()

        # Remove test mode flag
        TEST_MODE_FLAG.unlink(missing_ok=True)

    def _on_file_change(self, filepath: Path, event_type: str) -> None:
        """Callback from inotify/poller when a file changes.

        FLAG-2: Explicit context file invalidation.
        FLAG-3: CREATE/DELETE → reindex_namespace, MODIFY → apply_disk_change.
        """
        # Only care about .md files and .codex files
        if filepath.suffix not in ('.md', '.codex'):
            return

        # FLAG-2: Check if this is a context file and invalidate cache
        if filepath.name in CONTEXT_FILENAMES:
            self.context.invalidate_context_file(filepath.name)
            # Context files are not primitives — don't process further
            if filepath.parent == self.workspace:
                return

        if event_type == 'modified':
            diff = self.tree.apply_disk_change(filepath)
            if diff:
                self.diff_engine.record(diff)
                self.sessions.notify_all({'event': 'change', 'diff': asdict(diff)})

        elif event_type == 'created':
            # FLAG-3: CREATE → reindex namespace (new file shifts coordinates)
            prefix = self.tree._filepath_to_prefix(filepath)
            if prefix:
                diff_entry = self.tree._reindex_single_new(filepath, prefix)
                if diff_entry:
                    self.diff_engine.record(diff_entry)
                    self.sessions.notify_all({'event': 'change', 'diff': asdict(diff_entry)})

        elif event_type == 'deleted':
            diff = self.tree.apply_deletion(filepath)
            if diff:
                self.diff_engine.record(diff)
                self.sessions.notify_all({'event': 'change', 'diff': asdict(diff)})

    def _print_status(self) -> None:
        uptime = time.time() - self._start_time
        print(f"\n=== Codex Render Engine Status ===")
        print(f"  Uptime: {uptime:.0f}s")
        print(f"  Tree: {len(self.tree.nodes)} nodes")
        print(f"  Sessions: {len(self.sessions._sessions)}")
        print(f"  Diffs since anchor: {len(self.diff_engine._diffs)}")
        if self.test:
            s = self.test.status()
            print(f"  Test mode: {s['modified']} modified, {s['deleted']} deleted")


# ═══════════════════════════════════════════════════════════════════════════════
# §10  Client Helper — For codex_engine.py Integration
# ═══════════════════════════════════════════════════════════════════════════════

def _signal_render_engine(cmd: str, **kwargs) -> dict | None:
    """Send a command to the render engine if it's running. Non-blocking.

    Returns response dict or None if engine isn't running.
    Single-shot: send one JSON-line command, read one JSON-line response, close.
    """
    if not SOCKET_PATH.exists():
        return None
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect(str(SOCKET_PATH))
        msg = json.dumps({"cmd": cmd, **kwargs}) + '\n'
        s.sendall(msg.encode('utf-8'))
        # Read response until newline
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


def check_test_mode() -> bool:
    """Check if render engine is in test mode via flag file (FLAG-1: no UDS round-trip)."""
    return TEST_MODE_FLAG.exists()


def intercept_write(filepath: str, content: str) -> bool:
    """Send write to render engine's test mode overlay. Returns True if intercepted."""
    resp = _signal_render_engine('test_write', filepath=filepath, content=content)
    return resp is not None and resp.get('ok', False)


# ═══════════════════════════════════════════════════════════════════════════════
# §11  CLI — Argument Parsing & Client Commands
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Codex Render Engine')
    parser.add_argument('--test', action='store_true', help='Start in test mode')
    parser.add_argument('--status', action='store_true', help='Query running engine')
    parser.add_argument('--diff', action='store_true', help='Get current delta')
    parser.add_argument('--context', action='store_true', help='Get assembled context')
    parser.add_argument('--legacy', action='store_true', help='Use legacy (full file) context mode')
    parser.add_argument('--anchor-reset', action='store_true', help='Reset diff anchor')
    parser.add_argument('--commit', nargs='?', const='test commit', help='Commit test changes')
    parser.add_argument('--discard', action='store_true', help='Discard test changes')
    parser.add_argument('--buffer', nargs='?', const='dense', help='Get render buffer')
    parser.add_argument('--stop', action='store_true', help='Shutdown running engine')
    parser.add_argument('--workspace', type=str, default=None)

    args = parser.parse_args()

    # Client commands
    if args.status:
        resp = _signal_render_engine('status')
        if resp:
            print(json.dumps(resp, indent=2))
        else:
            print("Render engine not running")
        return

    if args.diff:
        resp = _signal_render_engine('diff')
        if resp and resp.get('ok'):
            print(resp.get('delta', '(no changes)') or '(no changes)')
        else:
            print("Render engine not running")
        return

    if args.context:
        mode = 'legacy' if args.legacy else 'codex'
        resp = _signal_render_engine('context', mode=mode)
        if resp and resp.get('ok'):
            print(resp.get('content', ''))
        else:
            print("Render engine not running")
        return

    if args.anchor_reset:
        resp = _signal_render_engine('anchor_reset')
        print(resp.get('message', 'done') if resp else "Render engine not running")
        return

    if args.commit is not None:
        resp = _signal_render_engine('test_commit', message=args.commit)
        if resp and resp.get('ok'):
            print(f"Committed: {resp.get('commit', '?')}")
        else:
            print(resp.get('error', 'Render engine not running') if resp else "Render engine not running")
        return

    if args.discard:
        resp = _signal_render_engine('test_discard')
        if resp and resp.get('ok'):
            print("Changes discarded")
        else:
            print(resp.get('error', 'Render engine not running') if resp else "Render engine not running")
        return

    if args.buffer is not None:
        resp = _signal_render_engine('buffer', format=args.buffer)
        if resp and resp.get('ok'):
            print(resp.get('content', ''))
        else:
            print("Render engine not running")
        return

    if args.stop:
        resp = _signal_render_engine('stop')
        print(resp.get('message', 'done') if resp else "Render engine not running")
        return

    # Server mode
    workspace = Path(args.workspace) if args.workspace else WORKSPACE
    engine = CodexRenderEngine(workspace, test_mode=args.test)
    engine.start()


if __name__ == '__main__':
    main()
