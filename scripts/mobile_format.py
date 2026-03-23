#!/usr/bin/env python3
"""
mobile_format.py — Mobile auto-formatter for belam/codex CLI output.

Reformats wide CLI output for narrow screens (Telegram, mobile chat).
Default target width: 38 chars.

Usage:
  python3 codex_engine.py | python3 mobile_format.py
  python3 codex_engine.py t1 | python3 mobile_format.py
  R pipelines 2>&1 | python3 mobile_format.py
  python3 mobile_format.py --width 40 < output.txt
  python3 mobile_format.py --raw < output.txt   # passthrough
"""

import sys
import re
import argparse
import textwrap

# ─── ANSI stripping ────────────────────────────────────────────────────────────

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mABCDEFGHJKLMSTfhin]|\x1b\([AB]|\x1b[=>]')

def strip_ansi(text: str) -> str:
    return ANSI_RE.sub('', text)

# ─── Status / priority emoji ───────────────────────────────────────────────────

STATUS_EMOJI = {
    'active':                  '🔵',
    'open':                    '⚪',
    'complete':                '✅',
    'completed':               '✅',
    'in_pipeline':             '🔄',
    'local_analysis_complete': '🔵',
    'archived':                '📦',
    'superseded':              '🗂',
}
PRIORITY_EMOJI = {
    'critical': '🔴',
    'high':     '🟠',
    'medium':   '🟡',
    'low':      '🟢',
}

def status_em(s: str) -> str:
    s = s.lower().strip()
    return STATUS_EMOJI.get(s, PRIORITY_EMOJI.get(s, ''))

SECTION_ICONS = {
    'pipeline': '📦', 'pipelines': '📦',
    'task':     '📋', 'tasks':     '📋',
    'decision': '📐', 'decisions': '📐',
    'memory':   '🧠',
    'daily':    '🧠', 'dailies':   '🧠',
    'weekly':   '🧠', 'weeklies':  '🧠',
    'knowledge':'📚',
    'skill':    '🛠',  'skills':    '🛠',
    'lesson':   '💡', 'lessons':   '💡',
    'command':  '⚙️',  'commands':  '⚙️',
    'workspace':'🗂',  'workspaces':'🗂',
}

# ─── Smart word wrap ───────────────────────────────────────────────────────────

def wrap(text: str, width: int, cont: str = '  ') -> list[str]:
    """Wrap text at width; continuation lines get `cont` prefix."""
    if len(text) <= width:
        return [text]
    effective = width - len(cont)
    if effective < 10:
        effective = width
        cont = ''
    wrapper = textwrap.TextWrapper(
        width=width,
        subsequent_indent=cont,
        break_long_words=True,
        break_on_hyphens=True,
    )
    result = wrapper.wrap(text)
    return result if result else [text]

def trunc(text: str, limit: int = 60) -> str:
    """Truncate to limit chars, adding ellipsis."""
    if len(text) > limit:
        return text[:limit - 1] + '…'
    return text

# ─── Tree-line parsing ─────────────────────────────────────────────────────────
#
# Codex engine outputs tree-structured text like:
#   R0 ╶─ Codex Engine Supermap [timestamp]
#   ╶─ p   pipelines (1)
#   │  ╶─ p1    validate-scheme-b  local_analysis_complete/high
#   │  ╶─ t1    build-codex-engine  active/critical  ←d22,m66,d15
#   │  ... (+24 more)
#   │  ╶─ m89 [01:27] Some memory text...
#   │  │  ╶─ md1 2026-03-22  0 entries
#
# Detail view (codex_engine.py t1):
#   R0 ╶─ t1 build-codex-engine
#      ╶─ 1   primitive   task
#      ╶─ 2   status      active
#      ╶─ B   body  [164 lines]

# Strip the optional "R\d+ " prefix and any tree drawing chars from a line
RENDER_PREFIX_RE = re.compile(r'^R\d+\s+')
# Tree characters at start: ╶─, │  ╶─, etc.
TREE_STRIP_RE    = re.compile(r'^[\s│]*[╶╠╚├└╞╟│][-─]+\s*')
# Detect if a line starts with tree chars (is tree-formatted)
TREE_LINE_RE     = re.compile(r'^[\s│]*[╶╠╚├└╞╟│]')

# Coordinate pattern: t1, p2, w3, md3, mw1, etc.
COORD_RE = re.compile(r'^(md|mw|[ptdlcwksm])\d+$', re.IGNORECASE)

def strip_tree(line: str) -> str:
    """Remove render prefix and tree drawing characters."""
    s = RENDER_PREFIX_RE.sub('', line)
    m = TREE_STRIP_RE.match(s)
    if m:
        return s[m.end():].strip()
    # Continuation lines like "│  ... (+24 more)" — strip leading │ and spaces
    s = re.sub(r'^[\s│╎]+', '', s)
    return s.strip()


# ─── Line classifiers ──────────────────────────────────────────────────────────

def is_tree_line(line: str) -> bool:
    return bool(TREE_LINE_RE.match(line)) or bool(RENDER_PREFIX_RE.match(line))

def is_namespace_section(content: str) -> bool:
    """Single namespace letter + section word: 'p   pipelines (1)', 't   tasks (9)'"""
    m = re.match(
        r'^([ptdlcwksm])\s{2,}(pipelines?|tasks?|decisions?|memory|knowledge|skills?|lessons?|commands?|workspaces?)\b',
        content, re.IGNORECASE
    )
    return bool(m)

def is_section_label(content: str) -> bool:
    """'pipelines (1)', 'tasks (9)', 'memory', etc."""
    m = re.match(r'^(pipelines?|tasks?|decisions?|memory|daily|dailies|weekly|weeklies|knowledge|skills?|lessons?|commands?|workspaces?)\b', content, re.IGNORECASE)
    return bool(m)

def is_coord_entry(content: str) -> bool:
    """'t1    build-codex-engine  active/critical'"""
    tok = content.split()[0] if content else ''
    return bool(COORD_RE.match(tok))

def is_numbered_field(content: str) -> bool:
    """'1   primitive   task' or '2   status   active'"""
    m = re.match(r'^(\d+|[Bb])\s{2,}', content)
    return bool(m)

def is_more_line(content: str) -> bool:
    return bool(re.match(r'^\.\.\.\s*\(\+\d+', content))

def is_memory_entry(content: str) -> bool:
    """'m89 [01:27] Some text' or 'm88 ...'"""
    return bool(re.match(r'^m\d+\s+\[', content))

def is_daily_entry(content: str) -> bool:
    """'md1 2026-03-22  0 entries' etc."""
    return bool(re.match(r'^(md|mw)\d+\s+', content, re.IGNORECASE))

def is_today_block(content: str) -> bool:
    """'today (2 entries)'"""
    return bool(re.match(r'^today\s+\(\d+', content, re.IGNORECASE))

def is_dailies_block(content: str) -> bool:
    return bool(re.match(r'^(dailies|weeklies)\s+\(\d+', content, re.IGNORECASE))


# ─── Supermap formatter ────────────────────────────────────────────────────────

def format_coord_entry(content: str, width: int) -> list[str]:
    """
    'p1    validate-scheme-b  local_analysis_complete/high'
    →
    📍 p1 validate-scheme-b
       🔵 local_analysis_complete
       🟠 high
    """
    parts = re.split(r'  +', content.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return [content]

    coord = parts[0]
    slug  = parts[1] if len(parts) > 1 else ''
    tail  = parts[2:]

    header = f'📍 {coord} {slug}'
    out = wrap(header, width, cont='   ')

    for part in tail:
        # status/priority compound: "active/critical" → "🔵 active/critical"
        if '/' in part:
            segs = part.split('/')
            em = status_em(segs[0]) or status_em(segs[1])
            label = f'   {em} {part}' if em else f'   {part}'
        else:
            em = status_em(part)
            label = f'   {em} {part}' if em else f'   {part}'
        out.extend(wrap(label, width, cont='     '))

    return out

def format_section_header(content: str, width: int) -> list[str]:
    """'pipelines (1)' → '\\n📦 pipelines (1)'"""
    m = re.match(r'^(\w+)\s*(.*)', content, re.IGNORECASE)
    if not m:
        return [f'\n{content}']
    typename = m.group(1).lower()
    rest = m.group(2).strip()
    icon = SECTION_ICONS.get(typename, '▪️')
    label = f'{typename} {rest}'.strip()
    return [f'\n{icon} {label}']

def format_memory_entry(content: str, width: int) -> list[str]:
    """'m89 [01:27] Codex Engine V2 features...' → '🧠 m89 [01:27] ...(truncated)'"""
    m = re.match(r'^(m\d+)\s+(\[\S+\])\s+(.*)', content)
    if not m:
        return [f'  {trunc(content, 60)}']
    coord, timestamp, text = m.group(1), m.group(2), m.group(3)
    text_short = trunc(text, 50)
    line = f'  🧠 {coord} {timestamp} {text_short}'
    return wrap(line, width, cont='       ')

def format_daily_entry(content: str, width: int) -> list[str]:
    """'md1 2026-03-22  0 entries' → '  📅 md1 2026-03-22 (0)'
       'mw1 2026-03-09 → 2026-03-15' → '  📅 mw1 2026-03-09→2026-03-15'"""
    # With entry count
    m = re.match(r'^(md\d+|mw\d+)\s+([\d\-→\s]+?)\s*(\d+)\s+entries?', content)
    if m:
        coord, date, count = m.group(1), m.group(2).strip(), m.group(3)
        return [f'  📅 {coord} {date} ({count})']
    # Without count (weekly range)
    m2 = re.match(r'^(md\d+|mw\d+)\s+(.*)', content)
    if m2:
        coord, rest = m2.group(1), m2.group(2).strip()
        return wrap(f'  📅 {coord} {rest}', width, cont='       ')
    return [f'  {content}']

def format_numbered_field(content: str, width: int) -> list[str]:
    """'1   primitive   task' → '  primitive: task'"""
    m = re.match(r'^(\d+|[Bb])\s{2,}(\w+)\s{2,}(.+)', content)
    if m:
        num, fname, fval = m.group(1), m.group(2), m.group(3).strip()
        if num.upper() == 'B':
            return []  # skip body line
        fval = trunc(fval, 60)
        return wrap(f'  {fname}: {fval}', width, cont='    ')
    # Could be just "B  body  [N lines]"
    m2 = re.match(r'^[Bb]\s{2,}', content)
    if m2:
        return []
    return [f'  {content}']


# ─── Pipeline dashboard formatter ─────────────────────────────────────────────

def format_pipeline_dashboard(lines: list[str], width: int) -> list[str]:
    """
    Format R pipeline dashboard output for mobile.
    Handles the VALIDATE-SCHEME-B style blocks.
    """
    out = []
    i = 0
    PIPE_HEADER_RE = re.compile(
        r'^\s{2}([\w\-]+)\s+(🟡|🟠|🔴|🟢|⚪)\s+(\w+)\s+(started|created|updated)\s+([\d\-]+)'
    )
    STATUS_LINE_RE = re.compile(r'^\s*(❓|✅|🔵|🔄|📦)\s*(.*)')
    DIVIDER_LINE_RE = re.compile(r'^[─═\-─]{4,}')
    ARCHIVED_RE = re.compile(r'^\s*📦\s+Archived:\s*(.*)')
    SECTION_TITLE_RE = re.compile(r'^\s*🔬\s+(.*)')

    while i < len(lines):
        raw = lines[i]
        s = raw.strip()

        if not s or DIVIDER_LINE_RE.match(s) or re.match(r'^[═]{4,}', s):
            i += 1
            continue

        # Section title: "🔬 PIPELINE DASHBOARD ..."
        m = SECTION_TITLE_RE.match(s)
        if m:
            out.append(f'\n🔬 {m.group(1).strip()}')
            i += 1
            continue

        # Pipeline header: "  VALIDATE-SCHEME-B  🟡 high  started 2026-03-17"
        m = PIPE_HEADER_RE.match(raw)
        if m:
            name = m.group(1).lower()
            prio_em = m.group(2)
            prio = m.group(3)
            verb = m.group(4)
            date = m.group(5)
            out.append(f'\n📋 {name}')
            out.append(f'   {prio_em} {prio} · {verb} {date}')
            i += 1
            continue

        # Status line: "❓ local_analysis_complete"
        m = STATUS_LINE_RE.match(s)
        if m:
            em = m.group(1)
            status = m.group(2).strip()
            out.extend(wrap(f'   {em} {status}', width, cont='     '))
            i += 1
            continue

        # Archived list: "📦 Archived: a, b, c"
        m = ARCHIVED_RE.match(s)
        if m:
            names = m.group(1).strip()
            out.append('\n📦 Archived:')
            for n in re.split(r',\s*', names):
                out.append(f'   • {n.strip()}')
            i += 1
            continue

        # Description / Latest / Tags — truncate long lines
        if s.startswith(('Statistical', 'Latest:', 'Tags:')):
            s_trunc = trunc(s, 70)
            out.extend(wrap(f'   {s_trunc}', width, cont='     '))
            i += 1
            continue

        # Generic: wrap
        if len(s) <= width:
            out.append(s)
        else:
            out.extend(wrap(s, width, cont='  '))
        i += 1

    return out


# ─── Main formatting engine ────────────────────────────────────────────────────

def detect_dashboard(lines: list[str]) -> bool:
    """Detect if input looks like a R pipeline dashboard."""
    for ln in lines[:5]:
        if '🔬' in ln or 'PIPELINE DASHBOARD' in ln:
            return True
    return False

def format_mobile(raw: str, width: int = 38, fmt: str = 'telegram') -> str:
    """Transform raw CLI output into mobile-friendly text."""
    text = strip_ansi(raw)
    lines = text.splitlines()

    if not lines:
        return ''

    # ── Route to specialized formatters ───────────────────────────────────────
    if detect_dashboard(lines):
        result_lines = format_pipeline_dashboard(lines, width)
        return _finalize(result_lines)

    # ── Codex engine tree output ───────────────────────────────────────────────
    out = []
    for line in lines:
        s = line.strip()

        # Skip blank
        if not s:
            if out and out[-1] != '':
                out.append('')
            continue

        # Skip pure dividers
        if re.match(r'^[─═\-═]{4,}$', s):
            continue

        # ── Render header: "R0 ╶─ Codex Engine Supermap [...]" ────────────────
        m = re.match(r'^R(\d+)\s+[╶│][-─]+\s+(.*)', line)
        if m:
            content = m.group(2).strip()
            # Is it a primitive header? e.g. "t1 build-codex-engine"
            m2 = re.match(r'^([ptdlcksm]\d+|md\d+|mw\d+)\s+([\w\-]+)(.*)', content, re.IGNORECASE)
            if m2:
                coord = m2.group(1)
                slug  = m2.group(2)
                out.append(f'📍 {coord} {slug}')
            else:
                # General header
                out.append(f'🔮 {content}')
            continue

        # Only process further as tree lines if they look like it
        if is_tree_line(line):
            content = strip_tree(line)

            if not content:
                continue

            # "today (2 entries)"
            if is_today_block(content):
                m = re.match(r'^today\s+\((\d+)', content, re.IGNORECASE)
                count = m.group(1) if m else ''
                out.append(f'\n🧠 today ({count} entries)')
                continue

            # "dailies (8)" / "weeklies (1)"
            if is_dailies_block(content):
                m = re.match(r'^(\w+)\s+\((\d+)', content, re.IGNORECASE)
                label = m.group(1).lower() if m else content
                count = m.group(2) if m else ''
                out.append(f'\n📅 {label} ({count})')
                continue

            # Namespace section: "p   pipelines (1)", "t   tasks (9)"
            if is_namespace_section(content):
                # Strip the leading letter and collapse to section label
                m = re.match(r'^[ptdlcwksm]\s+(.*)', content, re.IGNORECASE)
                label = m.group(1).strip() if m else content
                out.extend(format_section_header(label, width))
                continue

            # Section label: "pipelines (1)"
            if is_section_label(content):
                out.extend(format_section_header(content, width))
                continue

            # Numbered fields from detail view: "1   primitive   task"
            if is_numbered_field(content):
                out.extend(format_numbered_field(content, width))
                continue

            # Memory entry: "m89 [01:27] ..."
            if is_memory_entry(content):
                out.extend(format_memory_entry(content, width))
                continue

            # Daily/weekly entry: "md1 2026-03-22  0 entries"
            if is_daily_entry(content):
                out.extend(format_daily_entry(content, width))
                continue

            # Coordinate entry: "t1    build-codex-engine  active/critical  ←d22"
            if is_coord_entry(content):
                out.extend(format_coord_entry(content, width))
                continue

            # More line: "... (+24 more)"
            if is_more_line(content):
                m = re.match(r'\.\.\.\s*\(\+(\d+)', content)
                n = m.group(1) if m else '?'
                out.append(f'   … (+{n} more)')
                continue

            # Fallback: wrap the content
            out.extend(wrap(content, width, cont='  '))
            continue

        # ── Non-tree lines: generic wrap ──────────────────────────────────────
        if len(s) <= width:
            out.append(s)
        else:
            out.extend(wrap(s, width, cont='  '))

    return _finalize(out)


def _finalize(lines: list[str]) -> str:
    """Collapse multiple blanks, strip trailing whitespace."""
    result = []
    blank_count = 0
    for ln in lines:
        ln = ln.rstrip()
        if ln == '':
            blank_count += 1
            if blank_count <= 1:
                result.append(ln)
        else:
            blank_count = 0
            result.append(ln)
    return '\n'.join(result).strip()


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Mobile formatter for belam/codex CLI output.'
    )
    parser.add_argument('file', nargs='?', help='Input file (default: stdin)')
    parser.add_argument('--width', '-w', type=int, default=38,
                        help='Target line width (default: 38)')
    parser.add_argument('--format', '-f', default='telegram',
                        choices=['telegram', 'plain'],
                        help='Output format (default: telegram)')
    parser.add_argument('--raw', action='store_true',
                        help='Passthrough: strip ANSI only, no reformatting')
    args = parser.parse_args()

    if args.file:
        with open(args.file, 'r', encoding='utf-8', errors='replace') as fh:
            raw = fh.read()
    else:
        raw = sys.stdin.read()

    if args.raw:
        print(strip_ansi(raw), end='')
        return

    result = format_mobile(raw, width=args.width, fmt=args.format)
    print(result)


if __name__ == '__main__':
    main()
