#!/usr/bin/env python3
"""
Sync workspace knowledge to the portable knowledge-repo.

Copies/updates all reproducible workspace artifacts into the knowledge-repo
so it can be cloned elsewhere to bootstrap a new OpenClaw instance.

Usage:
    python3 scripts/sync_knowledge_repo.py          # Dry run (show what would change)
    python3 scripts/sync_knowledge_repo.py --apply   # Actually sync
    python3 scripts/sync_knowledge_repo.py --diff     # Show file diffs
"""

import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
REPO = WORKSPACE / 'knowledge-repo'
ML_RESEARCH = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research'

# ── What to sync ──────────────────────────────────────────────────────────────

# (source_path, repo_dest_path)  — relative to WORKSPACE or absolute
SYNC_FILES = {
    # ── Core workspace docs ──────────────────────────────────────────────
    'SOUL.md':       'SOUL.md',
    'AGENTS.md':     'AGENTS.md',
    'IDENTITY.md':   'IDENTITY.md',
    'HEARTBEAT.md':  'HEARTBEAT.md',
    'TOOLS.md':      'TOOLS.md',
    'USER.md':       'USER.md',

    # ── Templates ────────────────────────────────────────────────────────
    'templates/task.md':              'templates/task.md',
    'templates/lesson.md':           'templates/lesson.md',
    'templates/decision.md':         'templates/decision.md',
    'templates/project.md':          'templates/project.md',
    'templates/pipeline.md':         'templates/pipeline.md',
    'templates/analysis_pipeline.md':'templates/analysis_pipeline.md',
    'templates/memory_log.md':       'templates/memory_log.md',
    'templates/agent.md':            'templates/agent.md',
    'templates/runbook.md':          'templates/runbook.md',
    'templates/orchestrator.md':     'templates/orchestrator.md',
}

# Directories to sync (all .py files in scripts/, all .md in primitives)
SYNC_DIRS = {
    # (source_dir, dest_dir, glob_pattern)
    'scripts': ('scripts', 'scripts', '*.py'),
    'tasks': ('tasks', 'tasks', '*.md'),
    'projects': ('projects', 'projects', '*.md'),
    'decisions': ('decisions', 'decisions', '*.md'),
    'lessons': ('lessons', 'lessons', '*.md'),
}

# Skills directories (full recursive copy)
SKILL_DIRS = [
    'skills/derivative-specialist',
    'skills/predictionmarket-specialist',
    'skills/quant-infrastructure',
    'skills/quant-workflow',
    'skills/pipelines',
]

# Agent workspace configs — each agent's key .md files
AGENT_CONFIGS = {
    'architect': ['SOUL.md', 'AGENTS.md', 'IDENTITY.md', 'HEARTBEAT.md', 'TOOLS.md'],
    'critic':    ['SOUL.md', 'AGENTS.md', 'IDENTITY.md', 'HEARTBEAT.md', 'TOOLS.md'],
    'builder':   ['SOUL.md', 'AGENTS.md', 'IDENTITY.md', 'HEARTBEAT.md', 'TOOLS.md'],
}

# Research-specific agent docs (from the machinelearning repo)
RESEARCH_DOCS = {
    'AGENT_SOUL.md':              'research/AGENT_SOUL.md',
    'ANALYSIS_AGENT_ROLES.md':    'research/ANALYSIS_AGENT_ROLES.md',
    'ARCHITECT_KNOWLEDGE.md':     'research/ARCHITECT_KNOWLEDGE.md',
    'CRITIC_KNOWLEDGE.md':        'research/CRITIC_KNOWLEDGE.md',
    'BUILDER_KNOWLEDGE.md':       'research/BUILDER_KNOWLEDGE.md',
    'TECHNIQUES_TRACKER.md':      'research/TECHNIQUES_TRACKER.md',
}

# Memory directories — main workspace + all agent workspaces
MEMORY_SOURCES = {
    'main': WORKSPACE / 'memory',
}
# Add agent memory dirs
for _agent in AGENT_CONFIGS:
    _agent_ws = Path(os.path.expanduser(f'~/.openclaw/workspace-{_agent}'))
    MEMORY_SOURCES[_agent] = _agent_ws / 'memory'

# CLI tool
BELAM_CLI = Path(os.path.expanduser('~/.local/bin/belam'))


def needs_update(src: Path, dst: Path) -> bool:
    """Check if dst needs updating from src."""
    if not dst.exists():
        return True
    if not src.exists():
        return False
    return not filecmp.cmp(src, dst, shallow=False)


def sync_file(src: Path, dst: Path, dry_run: bool) -> str:
    """Sync a single file. Returns status string."""
    if not src.exists():
        return f'  ⚠️  SKIP (missing): {src}'
    
    if not needs_update(src, dst):
        return None  # Up to date
    
    action = 'NEW' if not dst.exists() else 'UPDATE'
    if dry_run:
        return f'  {"🆕" if action == "NEW" else "📝"} {action}: {dst.relative_to(REPO)}'
    
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f'  {"🆕" if action == "NEW" else "📝"} {action}: {dst.relative_to(REPO)}'


def sync_dir(src_dir: Path, dst_dir: Path, pattern: str, dry_run: bool) -> list:
    """Sync all matching files from src_dir to dst_dir."""
    results = []
    if not src_dir.exists():
        results.append(f'  ⚠️  SKIP (missing dir): {src_dir}')
        return results
    
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    for src_file in sorted(src_dir.glob(pattern)):
        if src_file.is_file():
            dst_file = dst_dir / src_file.name
            result = sync_file(src_file, dst_file, dry_run)
            if result:
                results.append(result)
    
    # Check for files in dst that no longer exist in src (orphans)
    if dst_dir.exists():
        for dst_file in sorted(dst_dir.glob(pattern)):
            src_file = src_dir / dst_file.name
            if not src_file.exists():
                results.append(f'  🗑️  ORPHAN: {dst_file.relative_to(REPO)} (not in workspace)')
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Sync workspace knowledge to portable repo')
    parser.add_argument('--apply', action='store_true', help='Actually sync (default is dry run)')
    parser.add_argument('--diff', action='store_true', help='Show file diffs')
    args = parser.parse_args()
    
    dry_run = not args.apply
    
    if dry_run:
        print('\n🔍 DRY RUN — showing what would change (use --apply to sync)\n')
    else:
        print('\n🔄 SYNCING knowledge repo...\n')
    
    all_results = []
    
    # ── Core files ────────────────────────────────────────────────────────
    print('📄 Core workspace files')
    for src_rel, dst_rel in SYNC_FILES.items():
        src = WORKSPACE / src_rel
        dst = REPO / dst_rel
        result = sync_file(src, dst, dry_run)
        if result:
            all_results.append(result)
            print(result)
    
    # ── Directories ───────────────────────────────────────────────────────
    for label, (src_rel, dst_rel, pattern) in SYNC_DIRS.items():
        print(f'\n📁 {label}/')
        results = sync_dir(WORKSPACE / src_rel, REPO / dst_rel, pattern, dry_run)
        all_results.extend(results)
        for r in results:
            print(r)
        if not results:
            print('  ✅ Up to date')
    
    # ── Skills ────────────────────────────────────────────────────────────
    print(f'\n🎯 Skills')
    for skill_rel in SKILL_DIRS:
        src_dir = WORKSPACE / skill_rel
        dst_dir = REPO / skill_rel
        if not src_dir.exists():
            print(f'  ⚠️  SKIP (missing): {skill_rel}')
            continue
        for src_file in sorted(src_dir.rglob('*')):
            if src_file.is_file() and not any(p.startswith('.') for p in src_file.parts):
                rel = src_file.relative_to(WORKSPACE)
                dst_file = REPO / rel
                result = sync_file(src_file, dst_file, dry_run)
                if result:
                    all_results.append(result)
                    print(result)
    
    # ── Agent workspace configs ───────────────────────────────────────────
    print(f'\n🤖 Agent workspace configs')
    for agent, files in AGENT_CONFIGS.items():
        agent_ws = Path(os.path.expanduser(f'~/.openclaw/workspace-{agent}'))
        dst_agent_dir = REPO / 'agent-workspaces' / agent
        for fname in files:
            src = agent_ws / fname
            dst = dst_agent_dir / fname
            result = sync_file(src, dst, dry_run)
            if result:
                all_results.append(result)
                print(result)
    
    # ── Agent primitives (agents/*.md) ────────────────────────────────────
    print(f'\n📋 Agent primitives')
    # These might be in workspace/agents/ or defined inline in knowledge-repo
    agents_dir = WORKSPACE / 'agents'
    if agents_dir.exists():
        results = sync_dir(agents_dir, REPO / 'agents', '*.md', dry_run)
        all_results.extend(results)
        for r in results:
            print(r)
    
    # ── Research docs ─────────────────────────────────────────────────────
    print(f'\n📚 Research agent docs')
    for src_name, dst_rel in RESEARCH_DOCS.items():
        src = ML_RESEARCH / src_name
        dst = REPO / dst_rel
        result = sync_file(src, dst, dry_run)
        if result:
            all_results.append(result)
            print(result)
    
    # ── Memory ─────────────────────────────────────────────────────────────
    print(f'\n🧠 Memory (main + agents)')
    for mem_label, mem_src in MEMORY_SOURCES.items():
        if not mem_src.exists():
            continue
        dst_mem_dir = REPO / 'memory' / mem_label if mem_label != 'main' else REPO / 'memory' / 'main'
        # Sync daily logs (*.md at top level)
        results = sync_dir(mem_src, dst_mem_dir, '*.md', dry_run)
        all_results.extend(results)
        for r in results:
            print(r)
        # Sync entries/ subdirectory
        entries_src = mem_src / 'entries'
        entries_dst = dst_mem_dir / 'entries'
        if entries_src.exists():
            results = sync_dir(entries_src, entries_dst, '*.md', dry_run)
            all_results.extend(results)
            for r in results:
                print(r)
        # Sync archive/entries/ subdirectory
        archive_src = mem_src / 'archive' / 'entries'
        archive_dst = dst_mem_dir / 'archive' / 'entries'
        if archive_src.exists():
            results = sync_dir(archive_src, archive_dst, '*.md', dry_run)
            all_results.extend(results)
            for r in results:
                print(r)
    # Also sync MEMORY.md (the curated long-term memory)
    result = sync_file(WORKSPACE / 'MEMORY.md', REPO / 'MEMORY.md', dry_run)
    if result:
        all_results.append(result)
        print(result)

    # ── R CLI ─────────────────────────────────────────────────────────
    print(f'\n🔮 R CLI')
    dst_belam = REPO / 'bin' / 'belam'
    result = sync_file(BELAM_CLI, dst_belam, dry_run)
    if result:
        all_results.append(result)
        print(result)
        if not dry_run:
            os.chmod(dst_belam, 0o755)
    
    # ── Summary ───────────────────────────────────────────────────────────
    print(f'\n{"─" * 60}')
    if all_results:
        print(f'  {len(all_results)} changes {"would be made" if dry_run else "applied"}')
        if dry_run:
            print(f'  Run with --apply to sync')
    else:
        print('  ✅ Everything up to date!')
    print()


if __name__ == '__main__':
    main()
