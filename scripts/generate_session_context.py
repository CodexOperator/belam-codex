#!/usr/bin/env python3
"""
generate_session_context.py — Dynamic session bootstrap context generator.

Reads current workspace state and outputs a markdown briefing to stdout.
Any agent can run this at session start to get fully up to speed.

Usage:
    python3 scripts/generate_session_context.py                         # Full briefing
    python3 scripts/generate_session_context.py --brief                 # Short version
    python3 scripts/generate_session_context.py --role architect        # Role-specific
    python3 scripts/generate_session_context.py --pipeline v4-analysis  # Pipeline-specific
    python3 scripts/generate_session_context.py --role architect --pipeline v4-analysis
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
BUILDS_DIR = WORKSPACE / 'SNN_research' / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> dict:
    """Parse YAML-ish frontmatter between --- delimiters."""
    meta = {}
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return meta
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '---':
            break
        if ':' in line:
            key, _, val = line.partition(':')
            meta[key.strip()] = val.strip()
    return meta


def extract_docstring(filepath: Path) -> str:
    """Extract the first docstring from a Python file."""
    try:
        content = filepath.read_text(errors='replace')
        # Try triple-quoted docstring
        for quote in ('"""', "'''"):
            start = content.find(quote)
            if start != -1:
                end = content.find(quote, start + 3)
                if end != -1:
                    doc = content[start + 3:end].strip()
                    # Return first non-empty line
                    for line in doc.split('\n'):
                        line = line.strip()
                        if line:
                            return line
    except Exception:
        pass
    return '(no description)'


def truncate(text: str, max_chars: int = 300) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + '…'


# ---------------------------------------------------------------------------
# Section A: Active Pipelines
# ---------------------------------------------------------------------------

def section_active_pipelines(brief: bool = False) -> str:
    pipelines_dir = WORKSPACE / 'pipelines'
    if not pipelines_dir.exists():
        return "## A. Active Pipelines\n_No pipelines directory found._\n"

    lines = ["## A. Active Pipelines\n"]
    found = 0

    for md_file in sorted(pipelines_dir.glob('*.md')):
        try:
            content = md_file.read_text(errors='replace')
            meta = parse_frontmatter(content)
            version = meta.get('version', md_file.stem)
            status = meta.get('status', 'unknown')
            priority = meta.get('priority', '')
            primitive = meta.get('primitive', 'pipeline')

            # Try to load state JSON for richer info
            pending_action = meta.get('pending_action', '')
            state_path = BUILDS_DIR / f'{version}_state.json'
            if state_path.exists():
                try:
                    state = json.loads(state_path.read_text())
                    status = state.get('status', status)
                    pending_action = state.get('pending_action', pending_action)
                except Exception:
                    pass

            priority_tag = f' `{priority}`' if priority else ''
            lines.append(f"### `{version}`{priority_tag}")
            lines.append(f"- **Status:** {status}")
            lines.append(f"- **Type:** {primitive}")
            if pending_action:
                lines.append(f"- **Pending Action:** `{pending_action}`")

            if not brief:
                # Extract description from body
                body = re.sub(r'^---.*?---\s*', '', content, flags=re.DOTALL)
                for line in body.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        lines.append(f"- **Description:** {truncate(line, 200)}")
                        break

            lines.append('')
            found += 1
        except Exception as e:
            lines.append(f"### {md_file.name}\n_Error reading: {e}_\n")

    if found == 0:
        lines.append('_No pipelines found._\n')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Section B: Recent Memories
# ---------------------------------------------------------------------------

def section_recent_memories(brief: bool = False) -> str:
    memory_dir = WORKSPACE / 'memory'
    if not memory_dir.exists():
        return "## B. Recent Memories\n_No memory directory found._\n"

    lines = ["## B. Recent Memories\n"]
    today = datetime.now(timezone.utc).date()
    dates_to_check = [today - timedelta(days=i) for i in range(2)]

    found_any = False
    for date in dates_to_check:
        fname = memory_dir / f'{date.isoformat()}.md'
        if fname.exists():
            try:
                content = fname.read_text(errors='replace')
                lines.append(f"### {date.isoformat()}")
                if brief:
                    # Only first 600 chars
                    lines.append(truncate(content.strip(), 600))
                else:
                    # Up to 1500 chars
                    lines.append(truncate(content.strip(), 1500))
                lines.append('')
                found_any = True
            except Exception as e:
                lines.append(f"_Error reading {fname.name}: {e}_\n")

    if not found_any:
        lines.append('_No recent memory files found (checked last 2 days)._\n')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Section C: Available Scripts
# ---------------------------------------------------------------------------

def section_available_scripts(brief: bool = False) -> str:
    scripts_dir = WORKSPACE / 'scripts'
    if not scripts_dir.exists():
        return "## C. Available Scripts\n_No scripts directory found._\n"

    lines = ["## C. Available Scripts\n"]
    scripts = sorted(scripts_dir.glob('*.py'))
    for script in scripts:
        desc = extract_docstring(script)
        if brief:
            lines.append(f"- `{script.name}` — {truncate(desc, 120)}")
        else:
            lines.append(f"- **`{script.name}`** — {desc}")

    if not scripts:
        lines.append('_No Python scripts found._')

    lines.append('')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Section D: Available Skills
# ---------------------------------------------------------------------------

def section_available_skills(brief: bool = False) -> str:
    skills_dir = WORKSPACE / 'skills'
    if not skills_dir.exists():
        # Also check openclaw system skills
        return "## D. Available Skills\n_No local skills directory found._\n"

    lines = ["## D. Available Skills\n"]
    found = 0

    for skill_dir in sorted(skills_dir.iterdir()):
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.exists():
            continue
        try:
            content = skill_md.read_text(errors='replace')
            meta = parse_frontmatter(content)
            name = meta.get('name', skill_dir.name)
            desc = meta.get('description', '')
            if not desc:
                # Try to extract from body
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('---') and ':' not in line[:20]:
                        desc = line
                        break
            lines.append(f"- **`{name}`** — {truncate(desc, 150)}")
            found += 1
        except Exception as e:
            lines.append(f"- `{skill_dir.name}` — (error: {e})")

    if found == 0:
        lines.append('_No skills found._')

    lines.append('')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Section E: Recent Lessons
# ---------------------------------------------------------------------------

def section_recent_lessons(brief: bool = False) -> str:
    lessons_dir = WORKSPACE / 'lessons'
    if not lessons_dir.exists():
        return "## E. Recent Lessons\n_No lessons directory found._\n"

    lines = ["## E. Recent Lessons\n"]

    # Collect all lesson files, sort by modification time (newest first)
    lesson_files = list(lessons_dir.glob('*.md')) + list(lessons_dir.glob('*.yaml'))
    lesson_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    lesson_files = lesson_files[:5]  # last 5

    for lf in lesson_files:
        try:
            content = lf.read_text(errors='replace')
            meta = parse_frontmatter(content)
            date = meta.get('date', '')
            title = lf.stem.replace('-', ' ').replace('_', ' ').title()

            # For yaml lessons, try to extract title from content
            if lf.suffix == '.yaml':
                for line in content.split('\n'):
                    if line.strip().startswith('title:'):
                        title = line.split(':', 1)[1].strip().strip('"\'')
                        break
            else:
                # md: look for first # heading
                for line in content.split('\n'):
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break

            date_str = f' ({date})' if date else ''
            lines.append(f"### {title}{date_str}")

            if not brief:
                # Show first substantive paragraph
                body = re.sub(r'^---.*?---\s*', '', content, flags=re.DOTALL).strip()
                # Skip headings
                paras = [p.strip() for p in body.split('\n\n') if p.strip() and not p.strip().startswith('#')]
                if paras:
                    lines.append(truncate(paras[0], 300))
            lines.append('')
        except Exception as e:
            lines.append(f"- {lf.name} (error: {e})\n")

    if not lesson_files:
        lines.append('_No lessons found._\n')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Section F: Role Context
# ---------------------------------------------------------------------------

def section_role_context(role: str) -> str:
    lines = [f"## F. Role Context: `{role}`\n"]

    # Check agents/ directory for agent definition
    agent_md = WORKSPACE / 'agents' / f'{role}.md'
    if agent_md.exists():
        try:
            content = agent_md.read_text(errors='replace')
            lines.append("### Agent Definition")
            lines.append(truncate(content, 1200))
            lines.append('')
        except Exception as e:
            lines.append(f"_Error reading agent file: {e}_\n")

    # Check for knowledge file
    knowledge_candidates = [
        WORKSPACE / 'SNN_research' / 'machinelearning' / 'snn_applied_finance' / 'research' / f'{role.upper()}_KNOWLEDGE.md',
        WORKSPACE / 'knowledge' / f'{role}-knowledge.md',
        WORKSPACE / f'{role.upper()}_KNOWLEDGE.md',
    ]
    for kf in knowledge_candidates:
        if kf.exists():
            try:
                content = kf.read_text(errors='replace')
                lines.append(f"### Knowledge File: `{kf.name}`")
                lines.append(truncate(content, 2000))
                lines.append('')
                break
            except Exception as e:
                lines.append(f"_Error reading knowledge file: {e}_\n")

    if len(lines) == 1:
        lines.append(f'_No role context found for `{role}`. Expected: `agents/{role}.md` or `*_KNOWLEDGE.md`._\n')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Section G: Pipeline Context
# ---------------------------------------------------------------------------

def section_pipeline_context(pipeline: str) -> str:
    lines = [f"## G. Pipeline Context: `{pipeline}`\n"]

    # Pipeline definition
    pipeline_md = WORKSPACE / 'pipelines' / f'{pipeline}.md'
    if pipeline_md.exists():
        try:
            content = pipeline_md.read_text(errors='replace')
            lines.append("### Pipeline Definition")
            lines.append(truncate(content, 2500))
            lines.append('')
        except Exception as e:
            lines.append(f"_Error reading pipeline definition: {e}_\n")
    else:
        lines.append(f"_Pipeline definition not found: `pipelines/{pipeline}.md`_\n")

    # State JSON
    state_path = BUILDS_DIR / f'{pipeline}_state.json'
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
            lines.append("### Current State (JSON)")
            lines.append("```json")
            lines.append(json.dumps(state, indent=2)[:1500])
            lines.append("```\n")
        except Exception as e:
            lines.append(f"_Error reading state JSON: {e}_\n")

    # Latest artifacts in pipeline_builds
    if BUILDS_DIR.exists():
        artifacts = sorted(
            [f for f in BUILDS_DIR.glob(f'{pipeline}_*.md')],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if artifacts:
            lines.append("### Latest Artifacts")
            for a in artifacts[:3]:
                lines.append(f"- `{a.name}` (modified {datetime.fromtimestamp(a.stat().st_mtime).strftime('%Y-%m-%d %H:%M')})")
            lines.append('')

            # Show content of the most recent artifact
            latest = artifacts[0]
            try:
                content = latest.read_text(errors='replace')
                lines.append(f"### Latest Artifact Content: `{latest.name}`")
                lines.append(truncate(content, 2000))
                lines.append('')
            except Exception:
                pass

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description='Generate session bootstrap context')
    parser.add_argument('--brief', action='store_true', help='Short version (reduced detail)')
    parser.add_argument('--role', type=str, help='Role-specific context (architect/critic/builder)')
    parser.add_argument('--pipeline', type=str, help='Pipeline-specific context (e.g. v4-analysis)')
    return parser.parse_args()


def main():
    args = parse_args()
    brief = args.brief

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    mode = 'brief' if brief else 'full'
    extras = []
    if args.role:
        extras.append(f'role={args.role}')
    if args.pipeline:
        extras.append(f'pipeline={args.pipeline}')
    extra_str = f' | {", ".join(extras)}' if extras else ''

    sections = [
        f"# Session Context Briefing\n",
        f"_Generated: {now} | Mode: {mode}{extra_str}_\n",
        "---\n",
        section_active_pipelines(brief),
        section_recent_memories(brief),
        section_available_scripts(brief),
        section_available_skills(brief),
        section_recent_lessons(brief),
    ]

    if args.role:
        sections.append(section_role_context(args.role))

    if args.pipeline:
        sections.append(section_pipeline_context(args.pipeline))

    print('\n'.join(sections))


if __name__ == '__main__':
    main()
