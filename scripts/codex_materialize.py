#!/usr/bin/env python3
"""
codex_materialize.py — Reactive .codex materialization engine (V3).

Generates .codex files as materialized views of workspace state.
These are format-layer files — derived from canonical .md primitives,
not sources of truth.

Usage:
  python3 codex_materialize.py --boot     # boot-time: full materialize + inject into AGENTS.md
  python3 codex_materialize.py --full     # full re-materialization (debug/manual)
  python3 codex_materialize.py --diff     # show temporal diff since last materialization
"""

import json
import hashlib
import datetime
import re
import sys
from pathlib import Path

# ── Lazy imports from codex_engine ──────────────────────────────────────────────

_engine = None

def _get_engine():
    """Lazy import codex_engine to avoid circular imports."""
    global _engine
    if _engine is None:
        sys.path.insert(0, str(Path(__file__).parent))
        import codex_engine
        _engine = codex_engine
    return _engine


class CodexMaterializer:
    """Generates and maintains .codex materialized views."""

    def __init__(self, workspace):
        self.workspace = Path(workspace)
        self.state_dir = self.workspace / 'state'
        self.hash_file = self.state_dir / 'materialize_hashes.json'
        self.codex_file = self.workspace / 'CODEX.codex'

    def materialize_full(self):
        """Full workspace materialization.

        Returns: {
            'codex_path': Path to CODEX.codex,
            'diff': temporal diff string (empty on first run),
            'hash': content hash of current state,
            'primitives_count': int,
        }
        """
        engine = _get_engine()

        # 1. Render supermap
        supermap = engine.render_supermap()

        # 2. Compute hash of rendered content (strip volatile timestamps)
        content_hash = self._hash_content(supermap)

        # 3. Load previous hashes for diff
        old_hashes = self._load_hashes()
        old_prim_hashes = old_hashes.get('primitive_hashes', {})

        # 4. Compute per-primitive hashes for change detection
        new_prim_hashes = {}
        changes = []
        primitives_count = 0

        for prefix in engine.NAMESPACE:
            try:
                prims = engine.get_primitives(prefix, active_only=True)
            except Exception:
                continue
            for i, (slug, fp) in enumerate(prims, 1):
                coord = f"{prefix}{i}"
                primitives_count += 1
                try:
                    text = fp.read_text(encoding='utf-8', errors='replace')
                    prim_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
                except Exception:
                    prim_hash = 'error'
                new_prim_hashes[coord] = {'hash': prim_hash, 'slug': slug}

                old_entry = old_prim_hashes.get(coord, {})
                if not old_entry:
                    changes.append(f"+ {coord}  {slug}  (added)")
                elif old_entry.get('hash') != prim_hash:
                    old_slug = old_entry.get('slug', '?')
                    if old_slug != slug:
                        changes.append(f"Δ {coord}  {old_slug}→{slug}  (reassigned)")
                    else:
                        changes.append(f"Δ {coord}  {slug}  (modified)")

        # Detect removed primitives
        for coord, entry in old_prim_hashes.items():
            if coord not in new_prim_hashes:
                changes.append(f"- {coord}  {entry.get('slug', '?')}  (removed)")

        # 5. Build diff string
        diff_str = ''
        if changes and old_prim_hashes:  # skip diff on first run
            now_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            since_str = old_hashes.get('last_materialize', 'unknown')
            diff_str = f"Changes since {since_str}:\n" + '\n'.join(sorted(changes))

        # 6. Write CODEX.codex as multi-doc stream
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        sort_mode = getattr(engine, '_current_sort_mode', 'alpha')

        codex_content = f"---\ntype: supermap\ngenerated: {now_str}\nsort_mode: {sort_mode}\nhash: {content_hash}\n---\n{supermap}"
        if diff_str:
            codex_content += f"\n---\ntype: diff\nsince: {old_hashes.get('last_materialize', now_str)}\nchanges: {len(changes)}\n---\n{diff_str}"

        self.codex_file.write_text(codex_content, encoding='utf-8')

        # 7. Update hash file
        new_hashes = {
            'last_materialize': now_str,
            'supermap_hash': content_hash,
            'primitive_hashes': new_prim_hashes,
            'sort_mode': sort_mode,
        }
        self._save_hashes(new_hashes)

        return {
            'codex_path': self.codex_file,
            'diff': diff_str,
            'hash': content_hash,
            'primitives_count': primitives_count,
        }

    def materialize_affected(self, coords):
        """Incremental materialization after mutation.

        Only updates the diff log in the hash file — full re-render is deferred
        to the next boot. This keeps post-mutation overhead minimal.
        """
        if not coords:
            return

        engine = _get_engine()
        hashes = self._load_hashes()
        prim_hashes = hashes.get('primitive_hashes', {})
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        for coord in coords:
            # Resolve the coordinate to find current file
            try:
                # Extract prefix and index from coord (e.g., 't1' → 't', 1)
                m = re.match(r'^(md|mw|[a-z]+)(\d+)$', coord, re.IGNORECASE)
                if not m:
                    continue
                prefix = m.group(1).lower()
                idx = int(m.group(2))
                if prefix not in engine.NAMESPACE:
                    continue
                prims = engine.get_primitives(prefix, active_only=True)
                if idx < 1 or idx > len(prims):
                    continue
                slug, fp = prims[idx - 1]
                text = fp.read_text(encoding='utf-8', errors='replace')
                prim_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
                prim_hashes[coord] = {'hash': prim_hash, 'slug': slug}
            except Exception:
                continue

        hashes['primitive_hashes'] = prim_hashes
        hashes['last_incremental'] = now_str
        self._save_hashes(hashes)

    def compute_diff(self, since=None):
        """Compute temporal diff since last materialization or given timestamp.

        Returns codex-formatted diff string.
        """
        engine = _get_engine()
        old_hashes = self._load_hashes()
        old_prim_hashes = old_hashes.get('primitive_hashes', {})

        if not old_prim_hashes:
            return "(no previous materialization — cannot compute diff)"

        changes = []
        for prefix in engine.NAMESPACE:
            try:
                prims = engine.get_primitives(prefix, active_only=True)
            except Exception:
                continue
            for i, (slug, fp) in enumerate(prims, 1):
                coord = f"{prefix}{i}"
                try:
                    text = fp.read_text(encoding='utf-8', errors='replace')
                    prim_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
                except Exception:
                    prim_hash = 'error'

                old_entry = old_prim_hashes.get(coord, {})
                if not old_entry:
                    changes.append(f"+ {coord}  {slug}  (added)")
                elif old_entry.get('hash') != prim_hash:
                    changes.append(f"Δ {coord}  {slug}  (modified)")

        for coord, entry in old_prim_hashes.items():
            # Check if coord still exists in current namespace
            m = re.match(r'^(md|mw|[a-z]+)(\d+)$', coord, re.IGNORECASE)
            if not m:
                continue
            prefix = m.group(1).lower()
            idx = int(m.group(2))
            try:
                prims = engine.get_primitives(prefix, active_only=True)
                if idx > len(prims):
                    changes.append(f"- {coord}  {entry.get('slug', '?')}  (removed)")
            except Exception:
                pass

        if not changes:
            return "(no changes since last materialization)"

        since_str = since or old_hashes.get('last_materialize', 'unknown')
        return f"Changes since {since_str}:\n" + '\n'.join(sorted(changes))

    def inject_into_agents_md(self, content):
        """Replace the SUPERMAP section in AGENTS.md.

        Reuses existing BEGIN:SUPERMAP/END:SUPERMAP markers.
        """
        agents_path = self.workspace / 'AGENTS.md'
        if not agents_path.exists():
            return

        start_marker = '<!-- BEGIN:SUPERMAP -->'
        end_marker = '<!-- END:SUPERMAP -->'
        section = f"{start_marker}\n\n## Codex Engine Supermap\n\n```\n{content}\n```\n\n{end_marker}"

        text = agents_path.read_text(encoding='utf-8')
        if start_marker in text and end_marker in text:
            text = re.sub(
                f'{re.escape(start_marker)}.*?{re.escape(end_marker)}',
                section, text, flags=re.DOTALL,
            )
        else:
            prim_marker = '<!-- BEGIN:PRIMITIVES -->'
            if prim_marker in text:
                text = text.replace(prim_marker, f"{section}\n{prim_marker}")
            else:
                text = text.rstrip() + f"\n\n{section}\n"

        agents_path.write_text(text, encoding='utf-8')

    def boot(self):
        """Boot-time entry point. Full materialize + inject."""
        result = self.materialize_full()
        # Read supermap from the generated CODEX.codex
        supermap_content = self._read_supermap_from_codex(result['codex_path'])
        self.inject_into_agents_md(supermap_content)

    def _read_supermap_from_codex(self, codex_path):
        """Extract supermap content from a CODEX.codex multi-doc stream."""
        try:
            text = codex_path.read_text(encoding='utf-8')
            # Parse multi-doc: find the supermap section (after first closing ---)
            # Format: ---\nfrontmatter\n---\nsupermap content\n---\ndiff frontmatter\n---\ndiff
            parts = text.split('\n---\n')
            if len(parts) >= 2:
                # parts[0] = "---\nfrontmatter"
                # parts[1] = "supermap content" (possibly followed by more sections)
                # But we need to handle the format carefully
                # The content after the closing --- of frontmatter is the supermap
                # Find closing --- of first frontmatter block
                if text.startswith('---\n'):
                    after_open = text[4:]
                    close_idx = after_open.find('\n---\n')
                    if close_idx >= 0:
                        rest = after_open[close_idx + 5:]
                        # Rest starts with supermap, may contain more --- separators
                        # Find the next --- that starts a new doc (type: diff)
                        next_doc = rest.find('\n---\ntype:')
                        if next_doc >= 0:
                            return rest[:next_doc].strip()
                        # No diff section — all of rest is supermap
                        return rest.strip()
            # Fallback: render fresh
            engine = _get_engine()
            return engine.render_supermap()
        except Exception:
            engine = _get_engine()
            return engine.render_supermap()

    def _load_hashes(self):
        """Load hash state from disk."""
        if self.hash_file.exists():
            try:
                return json.loads(self.hash_file.read_text(encoding='utf-8'))
            except Exception:
                pass
        return {}

    def _save_hashes(self, hashes):
        """Save hash state to disk. Preserves sort_mode if present."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        # Merge with existing to preserve sort_mode from engine
        existing = self._load_hashes()
        if 'sort_mode' in existing and 'sort_mode' not in hashes:
            hashes['sort_mode'] = existing['sort_mode']
        self.hash_file.write_text(json.dumps(hashes, indent=2), encoding='utf-8')

    def _hash_content(self, content):
        """Hash content, stripping volatile timestamps."""
        normalized = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC\]', '[TIMESTAMP]', content)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:12]


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Codex materialization engine')
    parser.add_argument('--boot', action='store_true', help='Boot-time: full materialize + inject into AGENTS.md')
    parser.add_argument('--full', action='store_true', help='Full re-materialization')
    parser.add_argument('--diff', action='store_true', help='Show temporal diff since last materialization')
    parser.add_argument('--workspace', type=str, default=None, help='Workspace path')
    args = parser.parse_args()

    workspace = Path(args.workspace) if args.workspace else Path.home() / '.openclaw' / 'workspace'

    materializer = CodexMaterializer(workspace)

    if args.boot:
        materializer.boot()
        print("Boot materialization complete.")

    elif args.full:
        result = materializer.materialize_full()
        print(f"Full materialization complete: {result['primitives_count']} primitives, hash={result['hash']}")
        if result['diff']:
            print()
            print(result['diff'])

    elif args.diff:
        diff = materializer.compute_diff()
        print(diff)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
