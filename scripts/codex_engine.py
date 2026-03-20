#!/usr/bin/env python3
"""
codex_engine.py — Codex Engine for the belam workspace CLI.

Unified primitive navigation, namespace resolution, and rendering system.
All output is plain ASCII/Unicode (tree chars ╶─ │ are fine), no colors.
Designed for LLM context — compact, token-efficient.
"""

import os
import sys
import re
import json
import hashlib
import datetime
import subprocess
from collections import OrderedDict, deque
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# ─── Configuration ─────────────────────────────────────────────────────────────

WORKSPACE = Path(os.environ.get('BELAM_WORKSPACE', Path.home() / '.openclaw/workspace'))
RENDER_STATE_FILE = Path.home() / '.belam_render_state.json'
EXCLUDED_STATUSES = {'superseded', 'archived'}

# Namespace map: prefix → (type_label, subdirectory_relative_to_workspace, special_mode)
# special_mode: None | 'skills' | 'daily'
NAMESPACE = {
    'p':  ('pipelines',   'pipelines',       None),
    'w':  ('workspaces',  'projects',        None),
    't':  ('tasks',       'tasks',           None),
    'd':  ('decisions',   'decisions',       None),
    'l':  ('lessons',     'lessons',         None),
    'c':  ('commands',    'commands',        None),
    'k':  ('knowledge',   'knowledge',       None),
    's':  ('skills',      'skills',          'skills'),
    'm':  ('memory',      'memory/entries',  None),
    'md': ('daily',       'memory',          'daily'),
    'mw': ('weekly',      'memory/weekly',   None),
}

# Sorted prefixes: longer ones first (md/mw before m)
PREFIXES_SORTED = sorted(NAMESPACE.keys(), key=lambda x: -len(x))

# Map type words found in ref paths to prefixes
TYPE_WORD_TO_PREFIX = {
    'pipeline': 'p', 'pipelines': 'p',
    'workspace': 'w', 'workspaces': 'w', 'project': 'w', 'projects': 'w',
    'task': 't', 'tasks': 't',
    'decision': 'd', 'decisions': 'd',
    'lesson': 'l', 'lessons': 'l',
    'command': 'c', 'commands': 'c',
    'knowledge': 'k',
    'skill': 's', 'skills': 's',
    'memory': 'm', 'memory_log': 'm',
    'daily': 'md',
    'weekly': 'mw',
}

# Regex for coordinate args: e.g. t3, t1-t3, md2, mw1, p, m
COORD_RE = re.compile(r'^(md|mw|[a-z]+)(\d+)?(?:-\d+)?$', re.IGNORECASE)
# Regex for range coords: e.g. t1-t3
RANGE_RE = re.compile(r'^(md|mw|[a-z]+)(\d+)-(\d+)$', re.IGNORECASE)
# Regex for field selectors: digits, B, B1, B1-15
FIELD_RE = re.compile(r'^(\d+|[Bb]\d*(?:-\d+)?)$')

# ─── Primitive Discovery ────────────────────────────────────────────────────────

def get_primitives(prefix):
    """Return sorted list of (slug, filepath) for all primitives of given prefix."""
    _, directory, special = NAMESPACE[prefix]
    base = WORKSPACE / directory

    if special == 'skills':
        # Each skill is a subdirectory with a SKILL.md file
        items = []
        if base.exists():
            for d in sorted(base.iterdir()):
                if d.is_dir() and (d / 'SKILL.md').exists():
                    items.append((d.name, d / 'SKILL.md'))
        return items

    elif special == 'daily':
        # YYYY-MM-DD.md files in memory/ directory
        pat = re.compile(r'^\d{4}-\d{2}-\d{2}\.md$')
        items = []
        if base.exists():
            for f in base.iterdir():
                if f.is_file() and pat.match(f.name):
                    items.append((f.stem, f))
        # Sort newest first
        items.sort(key=lambda x: x[0], reverse=True)
        return items

    else:
        items = []
        if base.exists():
            for f in sorted(base.glob('*.md')):
                items.append((f.stem, f))
        return items


def _quick_status(filepath):
    """Read just the frontmatter status of a file without full parse. Returns str or None."""
    try:
        text = filepath.read_text(encoding='utf-8', errors='replace')
        if not text.startswith('---'):
            return None
        end = text.find('\n---', 3)
        if end < 0:
            return None
        fm = text[3:end]
        m = re.search(r'^status:\s*["\']?(\w+)["\']?', fm, re.MULTILINE)
        if m:
            return m.group(1).lower()
    except Exception:
        pass
    return None


def build_slug_index():
    """Build reverse index: slug → coord (e.g. 'indexed-command-interface' → 'd9').
    Also maps 'decision/indexed-command-interface' style refs."""
    index = {}
    for prefix in NAMESPACE:
        primitives = get_primitives(prefix)
        for i, (slug, filepath) in enumerate(primitives, 1):
            coord = f'{prefix}{i}'
            # Direct slug lookup
            index[slug.lower()] = coord
            # Also strip type prefixes for path-style refs like 'decision/foo'
            for type_word in TYPE_WORD_TO_PREFIX:
                prefix_path = type_word + '/'
                if slug.lower().startswith(prefix_path):
                    bare = slug[len(prefix_path):]
                    index[bare.lower()] = coord
    return index


def resolve_edge_ref(ref_str, slug_index):
    """Convert ref like 'decision/indexed-command-interface' → coord like 'd9'."""
    if not ref_str:
        return None
    ref = str(ref_str).lower().strip().strip('"\'')

    # Direct lookup
    if ref in slug_index:
        return slug_index[ref]

    # Strip type prefix: 'decision/foo' → 'foo', 'decisions/foo' → 'foo'
    for type_word in TYPE_WORD_TO_PREFIX:
        prefix_path = type_word + '/'
        if ref.startswith(prefix_path):
            bare = ref[len(prefix_path):]
            if bare in slug_index:
                return slug_index[bare]

    # Last resort: try just the last segment after /
    if '/' in ref:
        bare = ref.rsplit('/', 1)[1]
        if bare in slug_index:
            return slug_index[bare]

    return None


# ─── Primitive Loading ──────────────────────────────────────────────────────────

def _parse_inline_value(v_str):
    """Parse a scalar YAML inline value string into a Python object."""
    v = v_str.strip()
    if not v:
        return None
    # Inline list: [a, b, c]
    if v.startswith('[') and v.endswith(']'):
        inner = v[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in inner.split(','):
            item = item.strip().strip('"\'')
            if item:
                items.append(item)
        return items
    # Booleans
    if v.lower() in ('true', 'yes'):
        return True
    if v.lower() in ('false', 'no'):
        return False
    # Null
    if v.lower() in ('null', '~'):
        return None
    # Quoted string
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    # Integer
    try:
        return int(v)
    except ValueError:
        pass
    # Float
    try:
        return float(v)
    except ValueError:
        pass
    return v


def parse_frontmatter(text):
    """Parse YAML frontmatter. Returns (OrderedDict of fields, body_str).

    Falls back to a simple line parser if PyYAML is unavailable or YAML is malformed.
    The fallback handles inline lists [a, b, c] and block list items (- value).
    """
    if not text.startswith('---'):
        return OrderedDict(), text

    end = text.find('\n---', 3)
    if end < 0:
        return OrderedDict(), text

    fm_text = text[3:end].strip()
    body = text[end + 4:].lstrip('\n')

    if HAS_YAML:
        try:
            raw = yaml.safe_load(fm_text)
            if isinstance(raw, dict):
                return OrderedDict(raw), body
        except Exception:
            pass  # Fall through to robust fallback

    # Fallback: line-by-line parser that handles inline lists and block lists
    fields = OrderedDict()
    current_key = None

    for line in fm_text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Block list item: starts with "- "
        if stripped.startswith('- ') and current_key is not None:
            item = stripped[2:].strip().strip('"\'')
            existing = fields.get(current_key)
            if isinstance(existing, list):
                # Avoid duplicates from mixed inline+block
                if item not in existing:
                    existing.append(item)
            else:
                # Upgrade scalar to list, start fresh
                fields[current_key] = [item]
            continue

        # Key-value line
        if ':' in stripped:
            k, _, v = stripped.partition(':')
            k = k.strip()
            v_raw = v.strip()
            if k and not k.startswith('-'):
                fields[k] = _parse_inline_value(v_raw)
                current_key = k

    return fields, body


def load_primitive(filepath, ptype=None):
    """Load a markdown primitive. Returns structured dict or None."""
    fp = Path(filepath)
    if not fp.exists():
        return None

    try:
        text = fp.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None

    fields_raw, body = parse_frontmatter(text)

    # Number the fields 1-based
    fields = OrderedDict()
    for i, (k, v) in enumerate(fields_raw.items(), 1):
        fields[i] = {'key': k, 'value': v}

    # Split body into lines, strip trailing blanks
    body_lines = body.split('\n')
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    return {
        'fields': fields,
        'body': body_lines,
        'filepath': str(fp),
        'slug': fp.stem if fp.name != 'SKILL.md' else fp.parent.name,
        'type': ptype or 'unknown',
    }


# ─── Coordinate Resolution ──────────────────────────────────────────────────────

def resolve_coords(args):
    """Parse args into (resolved_list, field_selections).

    Args can be a string (space-split) or list of strings.

    resolved_list: list of dicts with keys: prefix, index, filepath, slug, type
    field_selections: list of strings like '1', '3', 'B', 'B1-15'
    """
    if isinstance(args, str):
        args = args.split()

    resolved = []
    field_selections = []

    for arg in args:
        arg = arg.strip()
        if not arg:
            continue

        # Check for range pattern first: t1-t3 or t1-3
        range_m = re.match(r'^(md|mw|[a-z]+)(\d+)-(?:md|mw|[a-z]+)?(\d+)$', arg, re.IGNORECASE)
        if range_m:
            prefix_raw = range_m.group(1).lower()
            start_i = int(range_m.group(2))
            end_i = int(range_m.group(3))
            prefix = _normalize_prefix(prefix_raw)
            if prefix:
                primitives = get_primitives(prefix)
                type_label = NAMESPACE[prefix][0]
                for i in range(start_i, end_i + 1):
                    if 1 <= i <= len(primitives):
                        slug, fp = primitives[i - 1]
                        resolved.append({
                            'prefix': prefix, 'index': i,
                            'filepath': fp, 'slug': slug, 'type': type_label,
                        })
            continue

        # Check for coord pattern: md2, t3, p, m
        coord_m = re.match(r'^(md|mw|[a-z]+)(\d+)?$', arg, re.IGNORECASE)
        if coord_m:
            prefix_raw = coord_m.group(1).lower()
            idx_str = coord_m.group(2)
            prefix = _normalize_prefix(prefix_raw)
            if prefix:
                primitives = get_primitives(prefix)
                type_label = NAMESPACE[prefix][0]
                if idx_str is None:
                    # All items of this type
                    for i, (slug, fp) in enumerate(primitives, 1):
                        resolved.append({
                            'prefix': prefix, 'index': i,
                            'filepath': fp, 'slug': slug, 'type': type_label,
                        })
                else:
                    idx = int(idx_str)
                    if 1 <= idx <= len(primitives):
                        slug, fp = primitives[idx - 1]
                        resolved.append({
                            'prefix': prefix, 'index': idx,
                            'filepath': fp, 'slug': slug, 'type': type_label,
                        })
                continue

        # Check for field selector: digit(s) or B...
        if FIELD_RE.match(arg):
            field_selections.append(arg)
            continue

        # Unknown arg — skip silently

    return resolved, field_selections


def _normalize_prefix(prefix_raw):
    """Map raw lowercase prefix string to canonical NAMESPACE key."""
    for p in PREFIXES_SORTED:
        if prefix_raw == p:
            return p
    return None


# ─── Value Formatting ───────────────────────────────────────────────────────────

def _format_value(v):
    """Format a frontmatter value compactly for display."""
    if v is None:
        return 'null'
    if isinstance(v, list):
        if not v:
            return '[]'
        items = [str(x) for x in v]
        return '[' + ', '.join(items) + ']'
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    # Quote strings with spaces (but not list-looking or empty strings)
    if s and ' ' in s and not s.startswith('['):
        return f'"{s}"'
    return s if s else '""'


# ─── R-Label Tracker ────────────────────────────────────────────────────────────

class RenderTracker:
    """Session-scoped render tracking with dedup via content hash.

    State persists in ~/.belam_render_state.json across CLI invocations.
    Each render gets a sequential R-label (R0, R1, ...).
    Identical renders return pin reference: R📌R{n}.
    """

    def __init__(self, state_file=None):
        self.state_file = Path(state_file or RENDER_STATE_FILE)
        self._load()

    def _load(self):
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    self.state = json.load(f)
                return
            except Exception:
                pass
        self.state = self._fresh_state()

    def _fresh_state(self):
        return {
            'session_start': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'renders': [],
            'next_r': 0,
            'next_f': 1,
            'f_stack': [],
        }

    def _save(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def _normalize(content):
        """Normalize content for stable hashing — strip volatile timestamps."""
        # Replace [YYYY-MM-DD HH:MM UTC] patterns (supermap header timestamp)
        normalized = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC\]', '[TIMESTAMP]', content)
        return normalized

    @staticmethod
    def _hash(content):
        normalized = RenderTracker._normalize(content)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]

    def track_render(self, content):
        """Register a render. Returns (label_int, final_output_string).

        If content matches a previous render: returns (old_label, 'R📌R{n}').
        Otherwise: assigns next label, prepends 'R{n} ' to first line.
        """
        h = self._hash(content)

        for render in self.state['renders']:
            if render['hash'] == h:
                pin = f"R📌R{render['label']}"
                return render['label'], pin

        label = self.state['next_r']
        self.state['renders'].append({
            'label': label,
            'hash': h,
            'content_preview': content[:100],
        })
        self.state['next_r'] = label + 1
        self._save()

        # Prepend R-label to first line
        lines = content.split('\n')
        if lines:
            lines[0] = f"R{label} {lines[0]}"
        return label, '\n'.join(lines)

    def next_f_label(self):
        """Get and increment the next F-label. Returns string like 'F1'."""
        label_num = self.state.get('next_f', 1)
        self.state['next_f'] = label_num + 1
        self._save()
        return f"F{label_num}"

    def push_f_label(self, f_record):
        """Push an F-label record onto the undo stack."""
        if 'f_stack' not in self.state:
            self.state['f_stack'] = []
        self.state['f_stack'].append(f_record)
        self._save()

    def pop_f_label(self, label=None):
        """Pop an F-label from the stack. If label given, find and remove that specific one."""
        if 'f_stack' not in self.state:
            return None
        stack = self.state['f_stack']
        if not stack:
            return None
        if label is None:
            record = stack.pop()
        else:
            for i, rec in enumerate(stack):
                if rec.get('label') == label:
                    record = stack.pop(i)
                    break
            else:
                return None
        self._save()
        return record

    def reset(self):
        """Reset session state (new session)."""
        self.state = self._fresh_state()
        self._save()


_tracker = None


def get_render_tracker():
    global _tracker
    if _tracker is None:
        _tracker = RenderTracker()
    return _tracker


# ─── Supermap Renderer ──────────────────────────────────────────────────────────

def _supermap_summary(prefix, slug, filepath, slug_index):
    """Generate a compact one-line summary for a primitive in the supermap."""
    # Load frontmatter quickly
    field_map = {}
    try:
        text = filepath.read_text(encoding='utf-8', errors='replace')
        fm_raw, _ = parse_frontmatter(text)
        field_map = dict(fm_raw)
    except Exception:
        pass

    parts = []

    if prefix in ('p', 't'):
        status = str(field_map.get('status', ''))
        priority = str(field_map.get('priority', ''))
        sp = '/'.join(filter(None, [status, priority]))
        if sp:
            parts.append(sp)

    elif prefix == 'l':
        confidence = str(field_map.get('confidence', ''))
        if confidence:
            parts.append(confidence)

    elif prefix == 'w':
        status = str(field_map.get('status', ''))
        if status:
            parts.append(status)

    elif prefix == 'c':
        cmd = str(field_map.get('command', ''))
        desc = str(field_map.get('description', ''))
        if desc:
            short = desc[:40] + ('...' if len(desc) > 40 else '')
            parts.append(short)

    elif prefix == 'k':
        desc = str(field_map.get('description', ''))
        if desc:
            short = desc[:50] + ('...' if len(desc) > 50 else '')
            parts.append(short)

    # Edge refs: prefer downstream → then upstream ←
    edge_parts = []
    downstream = field_map.get('downstream', [])
    if isinstance(downstream, list) and downstream:
        refs = []
        for r in downstream[:3]:
            c = resolve_edge_ref(r, slug_index)
            if c:
                refs.append(c)
        if refs:
            edge_parts.append('→' + ','.join(refs))

    upstream = field_map.get('upstream', [])
    if isinstance(upstream, list) and upstream and not edge_parts:
        refs = []
        for r in upstream[:3]:
            c = resolve_edge_ref(r, slug_index)
            if c:
                refs.append(c)
        if refs:
            edge_parts.append('←' + ','.join(refs))

    if edge_parts:
        parts.append(' '.join(edge_parts))

    summary = slug
    if parts:
        summary = slug + '  ' + '  '.join(parts)
    return summary


def render_supermap():
    """Render the full supermap ASCII tree. Returns string (without R-label)."""
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    slug_index = build_slug_index()

    lines = []
    lines.append(f"╶─ Codex Engine Supermap [{now}]")

    SHOW_ORDER = ['p', 't', 'd', 'l', 'w', 'c', 'k', 's']

    for prefix in SHOW_ORDER:
        type_label = NAMESPACE[prefix][0]
        primitives = get_primitives(prefix)  # all, including excluded

        # Filter excluded statuses for display, but preserve original 1-based index
        display = []  # list of (original_index, slug, fp)
        for i, (slug, fp) in enumerate(primitives, 1):
            st = _quick_status(fp)
            if st and st in EXCLUDED_STATUSES:
                continue
            display.append((i, slug, fp))

        count = len(display)
        MAX_SHOW = 5 if count > 10 else count

        lines.append(f"╶─ {prefix:<3} {type_label} ({count})")
        for orig_i, slug, fp in display[:MAX_SHOW]:
            coord = f"{prefix}{orig_i}"
            summary = _supermap_summary(prefix, slug, fp, slug_index)
            lines.append(f"│  ╶─ {coord:<5} {summary}")

        if count > MAX_SHOW:
            lines.append(f"│  ... (+{count - MAX_SHOW} more)")

    # ── Memory section ──────────────────────────────────────────────────────────
    lines.append("╶─ m   memory")

    today = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    all_entries = get_primitives('m')  # sorted alphabetically → chronologically

    # Today's entries: filter by date prefix, show 5 most recent
    today_entries = [(s, fp) for s, fp in all_entries if s.startswith(today)]
    today_sorted = sorted(today_entries, key=lambda x: x[0], reverse=True)[:5]

    lines.append(f"│  ╶─ today ({len(today_entries)} entries)")
    if today_sorted:
        for slug, fp in today_sorted:
            # Global coord index (1-based across all entries)
            global_idx = next((i for i, (s, _) in enumerate(all_entries, 1) if s == slug), '?')
            # Extract time: YYYY-MM-DD_HHMMSS_slug → HH:MM
            parts_fn = slug.split('_', 2)
            time_str = ''
            if len(parts_fn) >= 2 and len(parts_fn[1]) == 6:
                t = parts_fn[1]
                time_str = f"{t[:2]}:{t[2:4]}"
            # Get content preview from 'content' field or body
            preview = _entry_preview(fp)
            lines.append(f"│  │  ╶─ m{global_idx} [{time_str}] {preview}")
    else:
        lines.append("│  │  (no entries today)")

    # Dailies (3 most recent)
    dailies = get_primitives('md')  # newest first
    all_daily_count = len(dailies)
    lines.append(f"│  ╶─ dailies ({all_daily_count})")
    for i, (slug, fp) in enumerate(dailies[:3], 1):
        entry_count, tags = _daily_stats(fp)
        tag_str = f"[{','.join(str(t) for t in tags[:3])}]" if tags else ''
        lines.append(f"│  │  ╶─ md{i} {slug}  {entry_count} entries  {tag_str}")

    # Weeklies (3 most recent)
    weeklies = get_primitives('mw')
    all_weekly_count = len(weeklies)
    lines.append(f"│  ╶─ weeklies ({all_weekly_count})")
    if weeklies:
        for i, (slug, fp) in enumerate(weeklies[:3], 1):
            period, tags = _weekly_meta(fp, slug)
            tag_str = f"[{','.join(str(t) for t in tags[:3])}]" if tags else ''
            lines.append(f"│     ╶─ mw{i} {period}  {tag_str}")
    else:
        lines.append("│     (none)")

    return '\n'.join(lines)


def _entry_preview(fp):
    """Get short content preview from a memory entry file."""
    try:
        text = fp.read_text(encoding='utf-8', errors='replace')
        fm_raw, body = parse_frontmatter(text)
        content = fm_raw.get('content', '')
        if not content:
            content = body.split('\n')[0] if body.strip() else ''
        s = str(content).strip()
        return s[:65] + ('...' if len(s) > 65 else '')
    except Exception:
        return str(fp.stem)


def _daily_stats(fp):
    """Count ## section headers and extract tags from a daily memory file."""
    try:
        text = fp.read_text(encoding='utf-8', errors='replace')
        headers = re.findall(r'^## ', text, re.MULTILINE)
        count = len(headers)
        # Try frontmatter tags
        tags = []
        if text.startswith('---') and HAS_YAML:
            end = text.find('\n---', 3)
            if end > 0:
                try:
                    fm = yaml.safe_load(text[3:end]) or {}
                    tags = fm.get('tags', [])
                except Exception:
                    pass
        return count, tags
    except Exception:
        return 0, []


def _weekly_meta(fp, slug_fallback):
    """Extract period and tags from a weekly memory file."""
    try:
        text = fp.read_text(encoding='utf-8', errors='replace')
        if text.startswith('---') and HAS_YAML:
            end = text.find('\n---', 3)
            if end > 0:
                try:
                    fm = yaml.safe_load(text[3:end]) or {}
                    period = fm.get('period', slug_fallback)
                    tags = fm.get('tags', [])
                    return str(period), tags
                except Exception:
                    pass
    except Exception:
        pass
    return slug_fallback, []


# ─── Zoom Renderer ──────────────────────────────────────────────────────────────

def render_zoom(coords_or_args, field_selections=None):
    """Render zoom view for given coordinates.

    coords_or_args: list of args (coord strings + optional field selectors),
                    or a single space-joined string.
    field_selections: explicit field selectors (overrides any parsed from args).

    Returns string (without R-label).
    """
    if isinstance(coords_or_args, str):
        coords_or_args = coords_or_args.split()

    resolved, auto_fields = resolve_coords(coords_or_args)
    if field_selections is None:
        field_selections = auto_fields

    if not resolved:
        return "No primitives found for given coordinates."

    lines = []
    first = True

    for item in resolved:
        prefix = item['prefix']
        idx = item['index']
        slug = item['slug']
        fp = item['filepath']
        ptype = item['type']
        coord = f"{prefix}{idx}"

        if not first:
            lines.append('')  # blank separator between primitives
        first = False

        lines.append(f"╶─ {coord} {slug}")

        prim = load_primitive(fp, ptype)
        if not prim:
            lines.append(f"   (file not found: {fp})")
            continue

        fields = prim['fields']
        body = prim['body']

        # Determine which fields and body sections to show
        show_field_nums = set()
        show_body = None   # None | 'summary' | 'all' | 'range'
        body_range = None  # (start, end) 1-based

        if not field_selections:
            show_field_nums = set(fields.keys())
            show_body = 'summary'
        else:
            for sel in field_selections:
                sel_upper = sel.upper()
                if sel_upper == 'B':
                    show_body = 'all'
                elif sel_upper.startswith('B') and len(sel_upper) > 1:
                    rest = sel_upper[1:]
                    if '-' in rest:
                        parts = rest.split('-', 1)
                        try:
                            s = int(parts[0])
                            e = int(parts[1].lstrip('B'))
                            body_range = (s, e)
                            show_body = 'range'
                        except ValueError:
                            show_body = 'all'
                    else:
                        try:
                            ln = int(rest)
                            body_range = (ln, ln)
                            show_body = 'range'
                        except ValueError:
                            show_body = 'all'
                else:
                    try:
                        show_field_nums.add(int(sel))
                    except ValueError:
                        pass

        # Render fields
        if show_field_nums and fields:
            max_key_len = max(len(info['key']) for info in fields.values())
            max_key_len = max(max_key_len, 8)
            for fnum, info in fields.items():
                if fnum not in show_field_nums:
                    continue
                key = info['key']
                val = _format_value(info['value'])
                lines.append(f"   ╶─ {fnum:<3} {key:<{max_key_len + 1}} {val}")

        # Render body
        if show_body == 'summary':
            lines.append(f"   ╶─ B   body  [{len(body)} lines]")
        elif show_body == 'all':
            lines.append(f"   ╶─ B   body")
            for i, line in enumerate(body, 1):
                lines.append(f"   │  B{i:<5} {line}")
        elif show_body == 'range' and body_range:
            s, e = body_range
            e = min(e, len(body))
            lines.append(f"   ╶─ B   body  [lines {s}-{e}]")
            for i in range(s, e + 1):
                if 1 <= i <= len(body):
                    lines.append(f"   │  B{i:<5} {body[i - 1]}")

    return '\n'.join(lines)


# ─── Graph Renderer ─────────────────────────────────────────────────────────────

def _load_all_primitives_edges():
    """Load all primitives, returning a dict: coord → {slug, upstream_coords, downstream_coords}.

    upstream_coords/downstream_coords are lists of coord strings (e.g. 'd12', 'l5').
    Also builds and returns slug_index.
    """
    slug_index = build_slug_index()
    graph = {}  # coord → {slug, upstream_coords, downstream_coords}

    for prefix in NAMESPACE:
        primitives = get_primitives(prefix)
        for i, (slug, filepath) in enumerate(primitives, 1):
            coord = f'{prefix}{i}'
            # Load frontmatter for upstream/downstream
            try:
                text = filepath.read_text(encoding='utf-8', errors='replace')
                fm_raw, _ = parse_frontmatter(text)
            except Exception:
                fm_raw = {}

            upstream_raw = fm_raw.get('upstream', []) or []
            downstream_raw = fm_raw.get('downstream', []) or []

            if isinstance(upstream_raw, str):
                upstream_raw = [upstream_raw]
            if isinstance(downstream_raw, str):
                downstream_raw = [downstream_raw]

            upstream_coords = []
            for ref in upstream_raw:
                c = resolve_edge_ref(str(ref), slug_index)
                if c:
                    upstream_coords.append(c)

            downstream_coords = []
            for ref in downstream_raw:
                c = resolve_edge_ref(str(ref), slug_index)
                if c:
                    downstream_coords.append(c)

            graph[coord] = {
                'slug': slug,
                'upstream_coords': upstream_coords,
                'downstream_coords': downstream_coords,
            }

    return graph, slug_index


def _graph_label(coord, graph):
    """Return 'coord slug' display label."""
    node = graph.get(coord)
    if node:
        return f"{coord} {node['slug']}"
    return coord


def render_graph(args):
    """Render graph view for given coordinates.

    Syntax:
      render_graph(['d2'])                → single node local graph (depth 1)
      render_graph(['d2', '--depth', '2'])→ multi-hop graph
      render_graph(['d2', 'l5'])          → path between two nodes
    Returns string (without R-label).
    """
    if isinstance(args, str):
        args = args.split()

    # Parse args: pull out --depth N, collect coord tokens
    depth = 1
    coord_tokens = []
    i = 0
    while i < len(args):
        if args[i] in ('--depth', '-d') and i + 1 < len(args):
            try:
                depth = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i].startswith('--depth='):
            try:
                depth = int(args[i].split('=', 1)[1])
            except ValueError:
                pass
            i += 1
        else:
            coord_tokens.append(args[i])
            i += 1

    # Resolve coord tokens to primitives
    resolved, _ = resolve_coords(coord_tokens)
    if not resolved:
        return "graph: no primitives found for given coordinates."

    graph, slug_index = _load_all_primitives_edges()

    lines = []

    if len(resolved) == 2 and depth == 1:
        # Path mode: find shortest path(s) between two nodes
        src_item = resolved[0]
        dst_item = resolved[1]
        src_coord = f"{src_item['prefix']}{src_item['index']}"
        dst_coord = f"{dst_item['prefix']}{dst_item['index']}"

        paths = _bfs_paths(src_coord, dst_coord, graph, max_depth=6)

        header = f"╶─ path: {src_coord} → {dst_coord}"
        lines.append(header)
        if not paths:
            lines.append(f"  (no path found between {_graph_label(src_coord, graph)} and {_graph_label(dst_coord, graph)})")
        else:
            for path in paths:
                # Display: indent under source
                src_label = _graph_label(path[0], graph)
                lines.append(f"  {src_label}")
                # Build the path string
                path_parts = []
                for j in range(1, len(path)):
                    path_parts.append(f"→ {_graph_label(path[j], graph)}")
                    if path[j] == dst_coord:
                        suffix = " (direct)" if len(path) == 2 else ""
                        lines.append(f"    {'  '.join(path_parts)}{suffix}")
                        break

    elif len(resolved) == 1 or depth > 1:
        # Single-node or multi-hop mode
        root_item = resolved[0]
        root_coord = f"{root_item['prefix']}{root_item['index']}"

        if depth == 1:
            # Simple flat display: show upstream ← and downstream →
            node = graph.get(root_coord, {})
            header = f"╶─ {_graph_label(root_coord, graph)}"
            lines.append(header)

            upstream = node.get('upstream_coords', [])
            downstream = node.get('downstream_coords', [])

            if upstream:
                lines.append("  upstream:")
                for c in upstream:
                    lines.append(f"    ← {_graph_label(c, graph)}")
            if downstream:
                lines.append("  downstream:")
                for c in downstream:
                    lines.append(f"    → {_graph_label(c, graph)}")
            if not upstream and not downstream:
                lines.append("  (no edges)")

        else:
            # Multi-hop: BFS up to `depth` levels, show tree
            header = f"╶─ {_graph_label(root_coord, graph)}"
            lines.append(header)

            visited = {root_coord}
            # Queue: (coord, current_depth, prefix_chars)
            # We'll use a recursive-style expansion
            _render_graph_tree(root_coord, graph, depth, 1, visited, lines, "  ")

    else:
        # Multiple root nodes at depth 1: show each independently
        for item in resolved:
            coord = f"{item['prefix']}{item['index']}"
            node = graph.get(coord, {})
            lines.append(f"╶─ {_graph_label(coord, graph)}")
            upstream = node.get('upstream_coords', [])
            downstream = node.get('downstream_coords', [])
            if upstream:
                lines.append("  upstream:")
                for c in upstream:
                    lines.append(f"    ← {_graph_label(c, graph)}")
            if downstream:
                lines.append("  downstream:")
                for c in downstream:
                    lines.append(f"    → {_graph_label(c, graph)}")
            if not upstream and not downstream:
                lines.append("  (no edges)")
            lines.append("")

    return '\n'.join(lines)


def _render_graph_tree(coord, graph, max_depth, current_depth, visited, lines, indent):
    """Recursively render the graph tree for multi-hop view."""
    node = graph.get(coord, {})
    upstream = node.get('upstream_coords', [])
    downstream = node.get('downstream_coords', [])
    all_edges = [('←', c) for c in upstream] + [('→', c) for c in downstream]

    for dir_sym, neighbor in all_edges:
        label = _graph_label(neighbor, graph)
        already_visited = neighbor in visited
        visited.add(neighbor)

        if current_depth < max_depth and not already_visited:
            lines.append(f"{indent}{dir_sym} {label}")
            _render_graph_tree(neighbor, graph, max_depth, current_depth + 1, visited, lines, indent + "│  ")
        else:
            suffix = " [...]" if not already_visited else " [visited]"
            lines.append(f"{indent}{dir_sym} {label}{suffix if current_depth >= max_depth and not already_visited else ''}")


def _bfs_paths(src, dst, graph, max_depth=6):
    """Find all shortest paths from src to dst using BFS over directed edges.

    Returns list of paths (each path is a list of coord strings).
    Treats all edges as undirected for path-finding purposes.
    """
    if src == dst:
        return [[src]]

    # BFS: queue of paths
    queue = deque([[src]])
    visited_at_depth = {}  # coord → depth first seen
    shortest_len = None
    found_paths = []

    while queue:
        path = queue.popleft()
        current = path[-1]
        current_depth = len(path)

        if shortest_len and current_depth > shortest_len:
            break
        if current_depth > max_depth:
            break

        node = graph.get(current, {})
        # Follow both directions for path finding
        neighbors = node.get('downstream_coords', []) + node.get('upstream_coords', [])

        for neighbor in neighbors:
            if neighbor in path:  # avoid cycles
                continue

            new_path = path + [neighbor]

            if neighbor == dst:
                if shortest_len is None:
                    shortest_len = len(new_path)
                if len(new_path) <= shortest_len:
                    found_paths.append(new_path)
            elif shortest_len is None:
                prev_depth = visited_at_depth.get(neighbor)
                if prev_depth is None or current_depth < prev_depth:
                    visited_at_depth[neighbor] = current_depth
                    queue.append(new_path)

    return found_paths


# ─── Execute Action ──────────────────────────────────────────────────────────────

def execute_action(args):
    """Execute an action via belam command dispatch.

    Syntax:
      execute_action(['status'])           → belam status --raw
      execute_action(['p5', 'run'])        → belam run validate-scheme-b --raw
      execute_action(['t1', 'complete'])   → belam edit ... --set status=complete --raw
      execute_action(['m', 'log', 'msg'])  → belam log "msg" --raw

    Always passes --raw to avoid recursion through the index engine.
    """
    if isinstance(args, str):
        args = args.split()

    if not args:
        print("execute: no action specified. Usage: belam -x [coord] <action> [args...]")
        return

    belam_bin = '/home/ubuntu/.local/bin/belam'

    # ── General (no-coord) actions ────────────────────────────────────────────
    GENERAL_ACTIONS = {
        'autorun': ['autorun'],
        'auto':    ['autorun'],
        'status':  ['status'],
        's':       ['status'],
        'consolidate': ['consolidate'],
        'cons':    ['consolidate'],
        'audit':   ['audit'],
        'au':      ['audit'],
    }

    first = args[0].lower()

    if first in GENERAL_ACTIONS:
        cmd_args = GENERAL_ACTIONS[first] + list(args[1:]) + ['--raw']
        _belam_exec(belam_bin, cmd_args)
        return

    # ── Coord-based actions ───────────────────────────────────────────────────
    # Resolve first arg as a coordinate
    resolved, _ = resolve_coords([args[0]])

    if not resolved:
        # Maybe it's a general action spelled differently
        print(f"execute: unknown action or unresolved coordinate: {args[0]!r}")
        print("Usage: belam -x [coord] <action> [extra args...]")
        return

    item = resolved[0]
    prefix = item['prefix']
    slug = item['slug']
    coord = f"{prefix}{item['index']}"
    action = args[1].lower() if len(args) > 1 else ''
    extra = list(args[2:])

    if not action:
        print(f"execute: no action specified for {coord} ({slug})")
        return

    # ── Pipeline actions (p prefix) ───────────────────────────────────────────
    if prefix == 'p':
        pipeline_action_map = {
            'run':          ['run', slug],
            'analyze':      ['analyze', slug],
            'analyze-local': ['analyze-local', slug],
            'al':           ['analyze-local', slug],
            'kickoff':      ['kickoff', slug],
            'kick':         ['kickoff', slug],
            'report':       ['report', slug],
            'revise':       ['revise', slug],
            'rev':          ['revise', slug],
            'status':       ['pipeline', slug],
        }
        if action in pipeline_action_map:
            cmd_args = pipeline_action_map[action] + extra + ['--raw']
            _belam_exec(belam_bin, cmd_args)
        else:
            print(f"execute: unknown pipeline action {action!r}")
            print(f"  Available: {', '.join(sorted(pipeline_action_map.keys()))}")
        return

    # ── Task actions (t prefix) ───────────────────────────────────────────────
    if prefix == 't':
        status_map = {
            'complete':  'complete',
            'done':      'complete',
            'activate':  'active',
            'active':    'active',
            'block':     'blocked',
            'blocked':   'blocked',
            'open':      'open',
        }
        if action in status_map:
            new_status = status_map[action]
            # Delegate to edit_primitive.py via belam edit
            cmd_args = ['edit', f'tasks/{slug}.md', '--set', f'status={new_status}', '--raw']
            _belam_exec(belam_bin, cmd_args)
        else:
            print(f"execute: unknown task action {action!r}")
            print(f"  Available: complete, activate, block, open")
        return

    # ── Memory actions (m prefix) ─────────────────────────────────────────────
    if prefix == 'm':
        if action == 'log':
            msg = ' '.join(extra) if extra else ''
            cmd_args = ['log', msg, '--raw']
            _belam_exec(belam_bin, cmd_args)
        else:
            print(f"execute: unknown memory action {action!r}")
            print(f"  Available: log")
        return

    # ── Fallback ───────────────────────────────────────────────────────────────
    print(f"execute: no action mapping for prefix={prefix!r} action={action!r}")
    print(f"  Coord {coord} ({slug}) — action {action!r} not supported for this primitive type.")


def _belam_exec(belam_bin, cmd_args):
    """Run belam with the given args, streaming stdout/stderr."""
    cmd = [belam_bin] + [str(a) for a in cmd_args]
    result = subprocess.run(cmd, check=False)
    if result.returncode not in (0, 2):
        sys.exit(result.returncode)


# ─── Mutation Helpers ──────────────────────────────────────────────────────────

# Prefix → singular type word (for ref format like "task/my-slug")
PREFIX_TO_TYPE_WORD = {
    'p': 'pipeline', 'w': 'project', 't': 'task', 'd': 'decision',
    'l': 'lesson', 'c': 'command', 'k': 'knowledge', 's': 'skill',
}

# Prefix → create_primitive.py type argument
PREFIX_TO_CREATE_TYPE = {
    't': 'task', 'd': 'decision', 'l': 'lesson',
    'w': 'project', 'c': 'command', 's': 'skill',
}

TASK_VALID_STATUSES = {'open', 'active', 'in_pipeline', 'blocked', 'complete'}
TASK_VALID_PRIORITIES = {'low', 'medium', 'high', 'critical'}


def _get_valid_pipeline_stages():
    """Extract valid pipeline stage names from pipeline_update.py source."""
    try:
        src = (WORKSPACE / 'scripts' / 'pipeline_update.py').read_text(encoding='utf-8')
        keys = re.findall(r"^\s+'([a-z][a-z0-9_]+)':\s+\(", src, re.MULTILINE)
        values = re.findall(r":\s+\('([a-z][a-z0-9_]+)'", src)
        stages = set(keys) | set(values)
        return stages if stages else None
    except Exception:
        return None


def _format_yaml_value(v):
    """Format a Python value for YAML frontmatter output (inline lists, quoted strings)."""
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(v)
    if isinstance(v, list):
        if not v:
            return '[]'
        items = []
        for item in v:
            s = str(item)
            if any(c in s for c in ' ,"\':[]{}\n') or not s:
                s = '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
            items.append(s)
        return '[' + ', '.join(items) + ']'
    s = str(v)
    if not s:
        return '""'
    needs_quote = (
        s[0] in ' \t' or s[-1] in ' \t' or
        any(c in s for c in ':#{}[],&*?|<>=!%@`') or
        s.lower() in ('true', 'false', 'null', 'yes', 'no', 'on', 'off') or
        '\n' in s
    )
    if needs_quote:
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return s


def _write_frontmatter_file(filepath, fields, body_lines):
    """Rewrite a primitive file preserving field order. Lists written inline."""
    fp = Path(filepath)
    out_lines = ['---']
    for fnum in sorted(fields.keys()):
        info = fields[fnum]
        out_lines.append(f"{info['key']}: {_format_yaml_value(info['value'])}")
    out_lines.append('---')
    if body_lines:
        out_lines.append('')
        out_lines.extend(body_lines)
    fp.write_text('\n'.join(out_lines) + '\n', encoding='utf-8')


def _coerce_value(new_value_str, old_value):
    """Coerce new_value_str to match the type of old_value."""
    if isinstance(old_value, list):
        s = new_value_str.strip()
        if s.startswith('[') and s.endswith(']'):
            inner = s[1:-1].strip()
            return [x.strip().strip('"\'') for x in inner.split(',') if x.strip()] if inner else []
        return [x.strip().strip('"\'') for x in s.split(',') if x.strip()] if s else []
    if isinstance(old_value, bool):
        return new_value_str.lower() in ('true', 'yes', '1')
    if isinstance(old_value, int):
        try:
            return int(new_value_str)
        except ValueError:
            return new_value_str
    return new_value_str


def _validate_field(prefix, field_key, new_value):
    """Validate a field value for primitive type. Returns (ok, error_msg)."""
    if prefix == 't':
        if field_key == 'status' and new_value not in TASK_VALID_STATUSES:
            return False, f"Invalid task status '{new_value}'. Must be one of: {', '.join(sorted(TASK_VALID_STATUSES))}"
        if field_key == 'priority' and new_value not in TASK_VALID_PRIORITIES:
            return False, f"Invalid task priority '{new_value}'. Must be one of: {', '.join(sorted(TASK_VALID_PRIORITIES))}"
    elif prefix == 'p':
        if field_key == 'status':
            valid_stages = _get_valid_pipeline_stages()
            if valid_stages is not None and new_value not in valid_stages:
                return False, f"Invalid pipeline status '{new_value}'. Must be a valid stage name."
    return True, None


def _parse_edit_args(raw_args):
    """Parse edit args → list of (resolved_item, field_num, new_value_str).

    Pattern: coord field_num value [field_num value ...] [coord field_num value ...]
    Returns None on parse error.
    """
    edits = []
    i = 0
    current_item = None
    while i < len(raw_args):
        arg = raw_args[i]
        # Try as coord: letters+digits (but NOT pure digits)
        coord_m = re.match(r'^(md|mw|[a-z]+)(\d+)$', arg, re.IGNORECASE)
        if coord_m:
            prefix_raw = coord_m.group(1).lower()
            idx_str = coord_m.group(2)
            prefix = _normalize_prefix(prefix_raw)
            if prefix:
                primitives = get_primitives(prefix)
                idx = int(idx_str)
                if 1 <= idx <= len(primitives):
                    slug, fp = primitives[idx - 1]
                    current_item = {
                        'prefix': prefix, 'index': idx,
                        'filepath': fp, 'slug': slug,
                        'type': NAMESPACE[prefix][0],
                        'coord': f'{prefix}{idx}',
                    }
                    i += 1
                    continue
                else:
                    print(f"Error: {arg} out of range (max {len(primitives)})")
                    return None
        if current_item is None:
            print(f"Error: expected coordinate before '{arg}'")
            return None
        # Try as field_num value pair
        if re.match(r'^\d+$', arg):
            field_num = int(arg)
            i += 1
            if i >= len(raw_args):
                print(f"Error: field {field_num} has no value")
                return None
            edits.append((current_item, field_num, raw_args[i]))
            i += 1
        else:
            print(f"Error: expected field number or coordinate, got '{arg}'")
            return None
    return edits


def _apply_inverse_op(op):
    """Apply the inverse of a recorded operation. Returns (ok, err_msg)."""
    fp = Path(op['filepath'])
    prim = load_primitive(fp)
    if not prim:
        return False, f"File not found: {op['filepath']}"
    for fnum, info in prim['fields'].items():
        if info['key'] == op['field_key']:
            info['value'] = op['old_value']
            _write_frontmatter_file(fp, prim['fields'], prim['body'])
            return True, None
    return False, f"Field '{op['field_key']}' not found in {op['filepath']}"


def _run_embed_primitives():
    """Run embed_primitives.py to update AGENTS.md/MEMORY.md indexes."""
    import subprocess as _sp
    try:
        r = _sp.run(
            [sys.executable, str(WORKSPACE / 'scripts' / 'embed_primitives.py')],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0
    except Exception:
        return False


def _sync_reverse_links(source_item, field_key, old_refs, new_refs,
                        cascade_counter, f_label, output_lines, cascades):
    """When upstream/downstream changes, update reverse links on target primitives."""
    old_set = set(str(r) for r in (old_refs or []))
    new_set = set(str(r) for r in (new_refs or []))
    added = new_set - old_set
    removed = old_set - new_set
    if not added and not removed:
        return

    slug_index = build_slug_index()
    src_ref = f"{PREFIX_TO_TYPE_WORD.get(source_item['prefix'], source_item['prefix'])}/{source_item['slug']}"
    # upstream changes ↔ affect target's downstream; downstream ↔ target's upstream
    reverse_field = 'upstream' if field_key == 'downstream' else 'downstream'

    for ref in list(added) + list(removed):
        is_added = ref in added
        ref_clean = str(ref).lower().strip().strip('"\'')
        coord = slug_index.get(ref_clean)
        if not coord and '/' in ref_clean:
            coord = slug_index.get(ref_clean.split('/', 1)[1])
        if not coord:
            continue
        cm = re.match(r'^(md|mw|[a-z]+)(\d+)$', coord)
        if not cm:
            continue
        t_prefix, t_idx = cm.group(1), int(cm.group(2))
        t_prims = get_primitives(t_prefix)
        if t_idx < 1 or t_idx > len(t_prims):
            continue
        t_slug, t_fp = t_prims[t_idx - 1]
        t_prim = load_primitive(t_fp, NAMESPACE[t_prefix][0])
        if not t_prim:
            continue
        rev_fnum = next((fn for fn, fi in t_prim['fields'].items() if fi['key'] == reverse_field), None)
        if rev_fnum is None:
            continue
        cur = t_prim['fields'][rev_fnum]['value']
        if not isinstance(cur, list):
            cur = []
        old_list = list(cur)
        if is_added:
            if src_ref in cur:
                continue
            new_list = old_list + [src_ref]
        else:
            if src_ref not in cur:
                continue
            new_list = [r for r in old_list if r != src_ref]
        t_prim['fields'][rev_fnum]['value'] = new_list
        _write_frontmatter_file(t_fp, t_prim['fields'], t_prim['body'])
        cascade_counter[0] += 1
        sub_label = f"{f_label}.{cascade_counter[0]}"
        action = "added" if is_added else "removed"
        output_lines.append(f"   └─ {sub_label} ↔ {coord}.{reverse_field} ← {action} {src_ref}")
        cascades.append({
            'filepath': str(t_fp), 'coord': coord,
            'field_key': reverse_field, 'old_value': old_list, 'new_value': new_list,
        })


# ─── Mutation Functions ─────────────────────────────────────────────────────────

def execute_edit(args):
    """Handle -e mode: edit primitive fields and write back.

    Usage: belam -e <coord> <field_num> <value> [<field_num> <value> ...] [<coord> ...]
    """
    if not args:
        print("Usage: belam -e <coord> <field_num> <value> [<field_num> <value> ...]")
        return 1

    edits = _parse_edit_args(args)
    if edits is None:
        return 1
    if not edits:
        print("No edits specified.")
        return 1

    tracker = get_render_tracker()

    # Group by coord (preserving order), load each primitive once
    coord_order = []
    coord_edits = {}   # coord → [(field_num, new_value_str), ...]
    coord_items = {}   # coord → resolved_item
    for item, field_num, new_val_str in edits:
        c = item['coord']
        if c not in coord_edits:
            coord_order.append(c)
            coord_edits[c] = []
            coord_items[c] = item
        coord_edits[c].append((field_num, new_val_str))

    # Load primitives
    loaded = {}
    for coord in coord_order:
        item = coord_items[coord]
        prim = load_primitive(item['filepath'], item['type'])
        if not prim:
            print(f"Error: cannot load primitive {coord} ({item['filepath']})")
            return 1
        loaded[coord] = prim

    # Validate all field edits before writing anything
    for item, field_num, new_val_str in edits:
        coord = item['coord']
        prim = loaded[coord]
        if field_num not in prim['fields']:
            print(f"Error: field {field_num} not found in {coord} (fields 1–{max(prim['fields'].keys())})")
            return 1
        field_info = prim['fields'][field_num]
        new_val = _coerce_value(new_val_str, field_info['value'])
        ok, err = _validate_field(item['prefix'], field_info['key'], new_val)
        if not ok:
            print(f"Error: {err}")
            return 1

    # Apply edits
    f_label = tracker.next_f_label()
    operations = []
    cascades = []
    output_lines = []
    first_line = True
    cascade_counter = [0]

    for coord in coord_order:
        item = coord_items[coord]
        prim = loaded[coord]
        for field_num, new_val_str in coord_edits[coord]:
            fi = prim['fields'][field_num]
            field_key = fi['key']
            old_val = fi['value']
            new_val = _coerce_value(new_val_str, old_val)

            operations.append({
                'filepath': str(item['filepath']), 'coord': coord,
                'field_num': field_num, 'field_key': field_key,
                'old_value': old_val, 'new_value': new_val,
            })
            prim['fields'][field_num]['value'] = new_val

            old_fmt = _format_value(old_val)
            new_fmt = _format_value(new_val)
            diff = f"Δ {coord}.{field_num} {field_key} {old_fmt}→{new_fmt}"
            if first_line:
                output_lines.append(f"{f_label} {diff}")
                first_line = False
            else:
                output_lines.append(f"   {diff}")

            # Cascade: task completion may unblock dependents
            if item['prefix'] == 't' and field_key == 'status' and new_val == 'complete':
                all_tasks = get_primitives('t')
                for j, (ts, tfp) in enumerate(all_tasks, 1):
                    if str(tfp) == str(item['filepath']):
                        continue
                    tp = load_primitive(tfp, 'tasks')
                    if not tp:
                        continue
                    deps_value = next(
                        (fi2['value'] for fi2 in tp['fields'].values() if fi2['key'] == 'depends_on'),
                        None
                    )
                    if not isinstance(deps_value, list) or not deps_value:
                        continue
                    dep_slugs = [str(d).split('/')[-1] for d in deps_value]
                    if item['slug'] not in dep_slugs:
                        continue
                    # Check all deps complete
                    all_met = True
                    dep_parts = []
                    for dep_ref in deps_value:
                        dep_slug = str(dep_ref).split('/')[-1]
                        found_met = False
                        for k, (ks, kfp) in enumerate(all_tasks, 1):
                            if ks == dep_slug:
                                if str(kfp) == str(item['filepath']):
                                    found_met = (new_val == 'complete')
                                else:
                                    found_met = (_quick_status(kfp) == 'complete')
                                dep_parts.append(f"{dep_slug} {'✓' if found_met else '✗'}")
                                break
                        else:
                            dep_parts.append(f"{dep_slug} ?")
                        if not found_met:
                            all_met = False
                    if all_met:
                        cascade_counter[0] += 1
                        sub_label = f"{f_label}.{cascade_counter[0]}"
                        dep_str = ', '.join(dep_parts)
                        output_lines.append(f"   └─ {sub_label} ⚡ t{j} unblocked (depends_on: {dep_str})")
                        cascades.append({'type': 'unblocked', 'coord': f't{j}'})

            # Cascade: bidirectional upstream/downstream sync
            if field_key in ('upstream', 'downstream'):
                _sync_reverse_links(
                    item, field_key, old_val, new_val,
                    cascade_counter, f_label, output_lines, cascades,
                )

        # Write file
        _write_frontmatter_file(item['filepath'], prim['fields'], prim['body'])

    # Track F-label for undo
    tracker.push_f_label({
        'label': f_label,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'operations': operations,
        'cascades': cascades,
    })

    _run_embed_primitives()
    print('\n'.join(output_lines))
    return 0


def execute_create(args):
    """Handle -n mode: create a new primitive via create_primitive.py.

    Usage: belam -n <type_prefix> <title words...>
    Prefixes: t=task, d=decision, l=lesson, w=project, c=command, s=skill
    """
    import subprocess as _sp

    if not args or len(args) < 2:
        print("Usage: belam -n <type_prefix> <title>")
        print("  Prefixes: " + ', '.join(f"{k}={v}" for k, v in sorted(PREFIX_TO_CREATE_TYPE.items())))
        return 1

    type_prefix = args[0].lower()
    title = ' '.join(args[1:])
    type_name = PREFIX_TO_CREATE_TYPE.get(type_prefix)
    if not type_name:
        print(f"Error: unknown type prefix '{type_prefix}'. Supported: {', '.join(sorted(PREFIX_TO_CREATE_TYPE.keys()))}")
        return 1

    tracker = get_render_tracker()
    f_label = tracker.next_f_label()

    result = _sp.run(
        [sys.executable, str(WORKSPACE / 'scripts' / 'create_primitive.py'), type_name, title],
        capture_output=True, text=True, cwd=str(WORKSPACE),
    )

    if result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode

    # Parse created file path from stdout
    created_path = None
    for line in result.stdout.split('\n'):
        m = re.search(r'✅ Created: (.+)', line)
        if m:
            rel = m.group(1).strip()
            created_path = WORKSPACE / rel
            break

    if not created_path or not created_path.exists():
        # Fallback: just print subprocess output
        print(result.stdout)
        return 0

    # Load and render the created primitive
    prim = load_primitive(created_path, type_name)
    if not prim:
        print(result.stdout)
        return 0

    slug = prim['slug']
    # Find coord by matching filepath in the namespace
    coord = f"{type_prefix}?"
    try:
        primitives = get_primitives(type_prefix)
        for i, (s, fp) in enumerate(primitives, 1):
            if str(fp) == str(created_path):
                coord = f"{type_prefix}{i}"
                break
    except Exception:
        pass

    output_lines = [f"{f_label} + {coord} {slug} [{type_name} created]"]
    if prim['fields']:
        max_key_len = max(len(fi['key']) for fi in prim['fields'].values())
        max_key_len = max(max_key_len, 8)
        for fnum, fi in prim['fields'].items():
            val = _format_value(fi['value'])
            output_lines.append(f"   ╶─ {fnum:<3} {fi['key']:<{max_key_len + 1}} {val}")

    # Track F-label (create is not undo-able via simple field restore, mark as create)
    tracker.push_f_label({
        'label': f_label,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'operations': [],
        'cascades': [],
        'create': {'filepath': str(created_path), 'type': type_name},
    })

    print('\n'.join(output_lines))
    return 0


def execute_undo(args):
    """Handle -z mode: undo a previous F-label edit.

    Usage: belam -z [F-label]  (e.g. belam -z or belam -z F1)
    """
    tracker = get_render_tracker()

    label = None
    if args:
        label = args[0]
        if not label.upper().startswith('F'):
            print(f"Error: expected F-label like 'F1', got '{label}'")
            return 1
        label = label.upper() if label[0].islower() else label

    record = tracker.pop_f_label(label)
    if record is None:
        if label:
            print(f"Error: F-label '{label}' not found in undo stack.")
        else:
            print("Nothing to undo.")
        return 1

    f_label = record['label']
    output_lines = [f"F⏪{f_label}"]

    # Undo cascades first (reverse order)
    for cascade in reversed(record.get('cascades', [])):
        if 'field_key' not in cascade:
            continue  # non-reversible cascade (e.g. unblocked marker)
        ok, err = _apply_inverse_op(cascade)
        if ok:
            old_fmt = _format_value(cascade['new_value'])
            new_fmt = _format_value(cascade['old_value'])
            coord = cascade.get('coord', Path(cascade['filepath']).stem)
            output_lines.append(f"   Δ {coord}.{cascade['field_key']} {old_fmt}→{new_fmt}  [cascade ↩]")

    # Undo primary operations (reverse order)
    for op in reversed(record.get('operations', [])):
        ok, err = _apply_inverse_op(op)
        if ok:
            old_fmt = _format_value(op['new_value'])
            new_fmt = _format_value(op['old_value'])
            coord = op.get('coord', Path(op['filepath']).stem)
            field_num = op.get('field_num', '?')
            output_lines.append(f"   Δ {coord}.{field_num} {op['field_key']} {old_fmt}→{new_fmt}")

    _run_embed_primitives()
    print('\n'.join(output_lines))
    return 0


# ─── Action Registry ────────────────────────────────────────────────────────────

ACTION_REGISTRY = {
    # Memory
    'log':              {'script': 'log_memory.py',             'description': 'Quick memory entry'},
    'consolidate':      {'script': 'consolidate_memories.py',   'description': 'Run memory consolidation'},
    'cons':             {'alias': 'consolidate'},

    # Pipelines
    'pipelines':        {'script': 'pipeline_dashboard.py',     'description': 'List all pipelines'},
    'pl':               {'alias': 'pipelines'},
    'kickoff':          {'script': 'pipeline_orchestrate.py',   'args_prefix': ['kickoff'],       'description': 'Kick off a pipeline'},
    'kick':             {'alias': 'kickoff'},
    'ko':               {'alias': 'kickoff'},
    'revise':           {'handler': 'revise',                   'description': 'Trigger Phase 1 revision'},
    'rev':              {'alias': 'revise'},
    'autorun':          {'script': 'pipeline_autorun.py',       'description': 'Auto-kick gated/stalled pipelines'},
    'auto':             {'alias': 'autorun'},
    'cleanup':          {'script': 'cleanup_stale_sessions.py', 'description': 'Kill stale sessions'},
    'clean':            {'alias': 'cleanup'},
    'handoffs':         {'script': 'pipeline_orchestrate.py',   'args_prefix': ['--check-pending'], 'description': 'Check stuck handoffs'},

    # Experiments
    'run':              {'script': 'pipeline_orchestrate.py',   'needs_version': True,  'args_suffix': ['run-experiment'],  'description': 'Run experiments'},
    'analyze':          {'script': 'analyze_experiment.py',     'description': 'Run experiment analysis'},
    'analyze-local':    {'script': 'pipeline_orchestrate.py',   'needs_version': True,  'args_suffix': ['local-analysis'],  'description': 'Orchestrated local analysis'},
    'al':               {'alias': 'analyze-local'},
    'report':           {'script': 'pipeline_orchestrate.py',   'needs_version': True,  'args_suffix': ['report-build'],    'description': 'Build LaTeX report'},

    # Primitives
    'create':           {'script': 'create_primitive.py',       'description': 'Create a new primitive'},
    'new':              {'alias': 'create'},
    'edit':             {'script': 'edit_primitive.py',         'description': 'Edit a primitive'},
    'audit':            {'script': 'audit_primitives.py',       'description': 'Audit primitive consistency'},
    'au':               {'alias': 'audit'},
    'embed-primitives': {'script': 'embed_primitives.py',       'description': 'Regenerate indexes'},
    'ep':               {'alias': 'embed-primitives'},
    'link':             {'handler': 'link',                     'description': 'Wire relationships'},
    'ln':               {'alias': 'link'},

    # Notebooks
    'build':            {'script': 'build_notebook.py',         'description': 'Build a notebook'},
    'notebooks':        {'handler': 'notebooks',                'description': 'List notebooks'},
    'nb':               {'alias': 'notebooks'},

    # Other
    'status':           {'handler': 'status',                   'description': 'Workspace overview'},
    'conversations':    {'script': 'export_agent_conversations.py', 'description': 'Export conversations'},
    'conv':             {'alias': 'conversations'},
    'knowledge-sync':   {'script': 'weekly_knowledge_sync.py',  'description': 'Weekly knowledge sync'},
    'ks':               {'alias': 'knowledge-sync'},
    'transcribe':       {'script': 'transcribe_audio.py',       'description': 'Transcribe audio'},
    'tr':               {'alias': 'transcribe'},
    'queue-revision':   {'script': 'create_revision_request.py', 'description': 'Queue revision request'},
    'qr':               {'alias': 'queue-revision'},
    'help':             {'handler': 'help',                     'description': 'Show help'},
}

# Resolved set of all known action words (including aliases)
_ALL_ACTION_WORDS = set(ACTION_REGISTRY.keys())


def _resolve_alias(word):
    """Resolve an alias to its canonical action word. Returns the word itself if not an alias."""
    entry = ACTION_REGISTRY.get(word)
    if entry and 'alias' in entry:
        return entry['alias']
    return word


def is_coordinate(arg):
    """Return True if arg looks like a primitive coordinate (e.g. t1, p5, md2, t, md, t1-t3).
    Does NOT match action words or flags."""
    if not arg or arg.startswith('-'):
        return False
    # Must start with known prefix letters only: single letters or md/mw
    # Pattern: (md|mw|[a-z])(\d+)?(-\d+)?  — must not contain other non-digit chars after prefix
    m = re.match(r'^(md|mw|[a-z])(\d+)?(?:-(\d+))?$', arg, re.IGNORECASE)
    if not m:
        return False
    prefix = m.group(1).lower()
    # Must be a known namespace prefix
    return prefix in NAMESPACE


def _run_script(script_name, extra_args):
    """Run a scripts/ python file with given args. Returns exit code."""
    scripts_dir = WORKSPACE / 'scripts'
    script_path = scripts_dir / script_name
    cmd = [sys.executable, str(script_path)] + [str(a) for a in extra_args]
    result = subprocess.run(cmd, cwd=str(WORKSPACE))
    return result.returncode


def dispatch_action(action_word, remaining_args):
    """Dispatch an action word with remaining args. Returns exit code."""
    canonical = _resolve_alias(action_word)
    entry = ACTION_REGISTRY.get(canonical)
    if not entry:
        print(f"dispatch_action: unknown action '{action_word}'")
        return 1

    belam_bin = '/home/ubuntu/.local/bin/belam'

    # ── Handler-based dispatch ─────────────────────────────────────────────────
    if 'handler' in entry:
        handler = entry['handler']

        if handler == 'status':
            result = subprocess.run([belam_bin, '--raw', 'status'] + list(remaining_args), cwd=str(WORKSPACE))
            return result.returncode

        elif handler == 'notebooks':
            result = subprocess.run([belam_bin, '--raw', 'notebooks'] + list(remaining_args), cwd=str(WORKSPACE))
            return result.returncode

        elif handler == 'revise':
            # revise <version> --context "..." [rest]
            if not remaining_args:
                print("Usage: belam revise <version> --context \"revision directions...\"")
                return 1
            version = remaining_args[0]
            rest = list(remaining_args[1:])
            scripts_dir = WORKSPACE / 'scripts'
            cmd = [sys.executable, str(scripts_dir / 'pipeline_orchestrate.py'), version, 'revise'] + rest
            result = subprocess.run(cmd, cwd=str(WORKSPACE))
            return result.returncode

        elif handler == 'link':
            scripts_dir = WORKSPACE / 'scripts'
            cmd = [sys.executable, str(scripts_dir / 'belam_index.py'), 'link'] + list(remaining_args)
            result = subprocess.run(cmd, cwd=str(WORKSPACE))
            return result.returncode

        elif handler == 'help':
            _print_action_help()
            return 0

        else:
            print(f"dispatch_action: unknown handler '{handler}'")
            return 1

    # ── Script-based dispatch ──────────────────────────────────────────────────
    if 'script' in entry:
        script_name = entry['script']
        args_prefix = entry.get('args_prefix', [])
        args_suffix = entry.get('args_suffix', [])
        needs_version = entry.get('needs_version', False)

        if needs_version:
            if not remaining_args:
                print(f"Usage: belam {canonical} <version> [options]")
                return 1
            version = remaining_args[0]
            extra = list(remaining_args[1:])
            # e.g. pipeline_orchestrate.py <version> run-experiment [extra]
            cmd_args = args_prefix + [version] + extra + args_suffix
        else:
            cmd_args = args_prefix + list(remaining_args) + args_suffix

        return _run_script(script_name, cmd_args)

    print(f"dispatch_action: malformed entry for '{canonical}': {entry}")
    return 1


def _print_action_help():
    """Print compact help grouped by category."""
    categories = [
        ('Memory',     ['log', 'consolidate']),
        ('Pipelines',  ['pipelines', 'kickoff', 'revise', 'autorun', 'cleanup', 'handoffs', 'queue-revision']),
        ('Experiments',['run', 'analyze', 'analyze-local', 'report']),
        ('Primitives', ['create', 'edit', 'audit', 'embed-primitives', 'link']),
        ('Notebooks',  ['build', 'notebooks']),
        ('Other',      ['status', 'conversations', 'knowledge-sync', 'transcribe', 'help']),
    ]
    # Build alias map: canonical → [aliases]
    alias_map = {}
    for word, entry in ACTION_REGISTRY.items():
        if 'alias' in entry:
            target = entry['alias']
            alias_map.setdefault(target, []).append(word)

    print("belam — action words\n")
    for cat_name, words in categories:
        print(f"  {cat_name}")
        for word in words:
            entry = ACTION_REGISTRY.get(word, {})
            desc = entry.get('description', '')
            aliases = alias_map.get(word, [])
            alias_str = f"  ({', '.join(aliases)})" if aliases else ''
            print(f"    {word:<20} {desc}{alias_str}")
        print()


# ─── Main Entry Point ───────────────────────────────────────────────────────────

def main(args=None):
    """Main entry point. Parses args, renders, tracks, prints."""
    if args is None:
        args = sys.argv[1:]

    # --boot: inject supermap into AGENTS.md for OpenClaw auto-injection, no R-labels
    if '--boot' in args:
        content = render_supermap()
        agents_path = Path(__file__).resolve().parent.parent / 'AGENTS.md'
        start_marker = '<!-- BEGIN:SUPERMAP -->'
        end_marker = '<!-- END:SUPERMAP -->'
        section = f"{start_marker}\n\n## Codex Engine Supermap\n\n```\n{content}\n```\n\n{end_marker}"

        text = agents_path.read_text(encoding='utf-8')
        if start_marker in text and end_marker in text:
            import re as _re
            text = _re.sub(
                f'{_re.escape(start_marker)}.*?{_re.escape(end_marker)}',
                section, text, flags=_re.DOTALL,
            )
        else:
            # Append before primitives section or at end
            prim_marker = '<!-- BEGIN:PRIMITIVES -->'
            if prim_marker in text:
                text = text.replace(prim_marker, f"{section}\n{prim_marker}")
            else:
                text = text.rstrip() + f"\n\n{section}\n"
        agents_path.write_text(text, encoding='utf-8')
        return

    tracker = get_render_tracker()

    if not args:
        # Supermap mode
        content = render_supermap()
        _, output = tracker.track_render(content)
        print(output)
        return

    # Strip --raw/--plain flags (passed through by belam)
    clean_args = [a for a in args if a not in ('--raw', '--plain')]

    if not clean_args:
        content = render_supermap()
        _, output = tracker.track_render(content)
        print(output)
        return

    first = clean_args[0]

    # 1. -e flag → edit mode
    if first == '-e':
        sys.exit(execute_edit(clean_args[1:]))

    # 2. -n flag → create mode
    if first == '-n':
        sys.exit(execute_create(clean_args[1:]))

    # 3. -z flag → undo mode
    if first == '-z':
        sys.exit(execute_undo(clean_args[1:]))

    # 4. -g flag → graph mode
    if first == '-g':
        content = render_graph(clean_args[1:])
        _, output = tracker.track_render(content)
        print(output)
        return

    # 5. -x flag → explicit execute mode
    if first == '-x':
        execute_action(clean_args[1:])
        return

    # 6. First arg is a coordinate → zoom/view mode
    if is_coordinate(first):
        content = render_zoom(clean_args)
        _, output = tracker.track_render(content)
        print(output)
        return

    # 7. First arg is a known action word → implicit execute / action dispatch
    if first in _ALL_ACTION_WORDS:
        rc = dispatch_action(first, clean_args[1:])
        sys.exit(rc)

    # 8. Nothing matched → fall through (exit code 2 signals bash to try legacy dispatch)
    sys.exit(2)


if __name__ == '__main__':
    main()
