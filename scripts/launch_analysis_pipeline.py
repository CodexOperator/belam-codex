#!/usr/bin/env python3
"""
Analysis Pipeline Launcher

Creates a new analysis pipeline instance from the analysis template, sets up
the build directory, and generates a design brief from pkl file metadata.

Usage:
    # Create analysis pipeline:
    python3 scripts/launch_analysis_pipeline.py v4-analysis \\
        --desc "Deep analysis of V4 differential output experiment results" \\
        --source-pkl "notebooks/snn_crypto_predictor_v4_pkl/" \\
        --source-version v4

    # Create with tags and priority:
    python3 scripts/launch_analysis_pipeline.py v4-analysis \\
        --desc "..." --source-pkl "..." --source-version v4 \\
        --priority critical --tags analysis,v4,differential

    # List active analysis pipelines:
    python3 scripts/launch_analysis_pipeline.py --list

    # Archive a completed analysis pipeline:
    python3 scripts/launch_analysis_pipeline.py v4-analysis --archive

    # Check archival eligibility:
    python3 scripts/launch_analysis_pipeline.py v4-analysis --check-archive
"""

import argparse
import json
import os
import pickle
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
PIPELINES_DIR = WORKSPACE / 'pipelines'
FINANCE_DIR = WORKSPACE / 'SNN_research' / 'machinelearning' / 'snn_applied_finance'
BUILDS_DIR = FINANCE_DIR / 'research' / 'pipeline_builds'
NOTEBOOKS_DIR = FINANCE_DIR / 'notebooks'


def list_pipelines():
    """List all analysis pipeline instances with status."""
    if not PIPELINES_DIR.exists():
        print("No pipelines directory found.")
        return

    pipelines = sorted(PIPELINES_DIR.glob('*-analysis*.md'))
    if not pipelines:
        print("No active analysis pipelines.")
        return

    print(f"\n{'Version':<20} {'Status':<35} {'Priority':<10} {'Started':<12} {'Source'}")
    print("─" * 90)

    for pf in pipelines:
        content = pf.read_text()
        status = _extract_field(content, 'status') or 'unknown'
        priority = _extract_field(content, 'priority') or '—'
        started = _extract_field(content, 'started') or '—'
        source_version = _extract_field(content, 'source_version') or '—'
        version = pf.stem

        icon = '📦' if status == 'archived' else (
            '🔬' if 'phase2' in status else
            '📊' if 'phase1' in status else '❓'
        )

        print(f"{icon} {version:<18} {status:<35} {priority:<10} {started:<12} {source_version}")

    print()


def _extract_field(content, field):
    """Extract a YAML frontmatter field value."""
    match = re.search(rf'^{field}:\s*(.+)$', content, re.MULTILINE)
    return match.group(1).strip() if match else None


def check_archivable(version):
    """Check if a pipeline can be archived."""
    pf = PIPELINES_DIR / f'{version}.md'
    if not pf.exists():
        print(f"❌ No pipeline found: {version}")
        return False

    content = pf.read_text()
    status = _extract_field(content, 'status')

    if status in ('analysis_phase2_complete', 'archived'):
        if status == 'archived':
            print(f"📦 {version} is already archived")
        else:
            print(f"✅ {version} is eligible for archival (status: {status})")
        return status != 'archived'

    print(f"⏳ {version} not ready for archival (status: {status})")
    return False


def archive_pipeline(version):
    """Archive a completed analysis pipeline."""
    pf = PIPELINES_DIR / f'{version}.md'
    if not pf.exists():
        print(f"❌ No pipeline found: {version}")
        sys.exit(1)

    if not check_archivable(version):
        print("Use --force to archive anyway.")
        sys.exit(1)

    content = pf.read_text()
    content = re.sub(r'^status:\s*.+$', 'status: archived', content, count=1, flags=re.MULTILINE)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    content = re.sub(r'^(started:.+)$', f'\\1\narchived: {now}', content, count=1, flags=re.MULTILINE)
    pf.write_text(content)
    print(f"📦 {version} archived")


def scan_pkl_metadata(pkl_dir):
    """Scan pkl files and extract metadata for the design brief."""
    pkl_path = WORKSPACE / pkl_dir if not Path(pkl_dir).is_absolute() else Path(pkl_dir)

    metadata = {
        'pkl_dir': str(pkl_path),
        'files': [],
        'total_files': 0,
        'experiments': [],
        'fields': [],
        'groups': [],
        'experiment_count': 0,
        'sample_keys': [],
        'errors': [],
    }

    if not pkl_path.exists():
        metadata['errors'].append(f"Directory not found: {pkl_path}")
        return metadata

    pkl_files = list(pkl_path.glob('*.pkl'))
    if not pkl_files:
        # Try subdirectories
        pkl_files = list(pkl_path.rglob('*.pkl'))

    metadata['total_files'] = len(pkl_files)

    for pkl_file in sorted(pkl_files):
        file_info = {
            'name': pkl_file.name,
            'size_kb': round(pkl_file.stat().st_size / 1024, 1),
        }

        try:
            with open(pkl_file, 'rb') as f:
                data = pickle.load(f)

            if isinstance(data, dict):
                file_info['type'] = 'dict'
                file_info['keys'] = list(data.keys())[:20]  # cap at 20
                if metadata['fields'] == []:
                    metadata['fields'] = list(data.keys())[:50]
                # Try to extract experiment count
                for key in ('results', 'experiments', 'records'):
                    if key in data and isinstance(data[key], (list, dict)):
                        val = data[key]
                        file_info['experiment_count'] = len(val)
                        metadata['experiment_count'] += len(val)
                        break
            elif isinstance(data, list):
                file_info['type'] = 'list'
                file_info['length'] = len(data)
                metadata['experiment_count'] += len(data)
                if data and isinstance(data[0], dict) and metadata['fields'] == []:
                    metadata['fields'] = list(data[0].keys())[:50]
                    file_info['sample_keys'] = list(data[0].keys())[:10]
            else:
                file_info['type'] = type(data).__name__

        except Exception as e:
            file_info['error'] = str(e)
            metadata['errors'].append(f"{pkl_file.name}: {e}")

        metadata['files'].append(file_info)

    return metadata


def generate_design_brief(version, source_version, description, pkl_dir, metadata):
    """Generate a design brief from pkl metadata."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    # Build file inventory table
    file_rows = []
    for f in metadata['files']:
        size = f.get('size_kb', '?')
        ftype = f.get('type', '?')
        count = f.get('experiment_count', f.get('length', '?'))
        error = f.get('error', '')
        row = f"| {f['name']:<45} | {size:>8} KB | {ftype:<10} | {count if not error else '❌ ' + error[:30]:<15} |"
        file_rows.append(row)

    file_table = '\n'.join(file_rows) if file_rows else '| (no pkl files found) | — | — | — |'

    # Build fields list
    fields_str = ', '.join(f'`{k}`' for k in metadata['fields'][:20])
    if len(metadata['fields']) > 20:
        fields_str += f' ... (+{len(metadata["fields"]) - 20} more)'

    errors_section = ''
    if metadata['errors']:
        errors_section = '\n## ⚠️ Errors During Scan\n'
        for e in metadata['errors']:
            errors_section += f'- {e}\n'

    brief = f"""# Analysis Design Brief: {version}
_Auto-generated by launch_analysis_pipeline.py on {now}_

## Overview
- **Analysis Version:** `{version}`
- **Source Experiment:** `{source_version}`
- **Description:** {description}
- **Pkl Source Directory:** `{metadata['pkl_dir']}`

## Data Inventory

| File | Size | Type | Experiments |
|------|------|------|-------------|
{file_table}

**Total pkl files:** {metadata['total_files']}
**Estimated total experiments/records:** {metadata['experiment_count'] if metadata['experiment_count'] > 0 else '(could not auto-detect — check manually)'}

## Detected Fields
{fields_str if fields_str else '_(could not detect — pkl files may need manual inspection)_'}

## Research Questions (Architect Must Address)

The architect should design the analysis notebook to answer:

1. **Performance Distribution:** What is the distribution of accuracy / Sharpe / abstention-accuracy across all experiments?
2. **Best Configurations:** Which architecture × encoding × output scheme combinations perform best?
3. **Scale Effects:** How does performance scale with network size (nano-5 → medium-192)?
4. **Encoding Sensitivity:** Which encoding (rate, delta, equilibrium) shows the strongest signal?
5. **Stability Analysis:** How consistent is performance across walk-forward folds?
6. **Failure Mode Analysis:** What characterizes the bottom-performing experiments?
7. **Cross-Phase Comparison:** (If source version has multiple phases) How does Phase 1 vs Phase 2 performance differ?
8. **Statistical Validation:** Which performance differences are statistically significant?

## Notebook Output Target
- **Notebook:** `snn_applied_finance/notebooks/crypto_{source_version}_analysis.ipynb`
- **Upload method:** Colab upload (zip or individual pkl files)

## Architect Instructions
1. Read `research/ANALYSIS_AGENT_ROLES.md`
2. Read skill at `~/.openclaw/workspace/skills/quant-workflow/SKILL.md`
3. Design the full analysis notebook structure addressing all research questions above
4. Specify exact statistical tests, visualizations, and pattern-discovery approaches
5. Write design to `research/pipeline_builds/{version}_architect_analysis_design.md`
6. Run: `python3 scripts/pipeline_update.py {version} complete analysis_architect_design "Design complete" architect`
{errors_section}"""

    return brief


def create_pipeline(version, description, source_version, source_pkl, priority='high', tags=None,
                    project='snn-applied-finance'):
    """Create a new analysis pipeline instance."""
    pf = PIPELINES_DIR / f'{version}.md'
    if pf.exists():
        print(f"❌ Pipeline {version} already exists: {pf}")
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    tags_list = tags or ['snn', 'analysis', source_version]
    tags_str = f"[{', '.join(tags_list)}]"

    # Read template
    template_path = WORKSPACE / 'templates' / 'analysis_pipeline.md'
    if template_path.exists():
        template = template_path.read_text()
        # Strip YAML frontmatter from template (we build our own)
        template_body_match = re.search(r'^---\n.*?^---\n(.+)', template, re.DOTALL | re.MULTILINE)
        template_body = template_body_match.group(1) if template_body_match else ''
    else:
        template_body = ''
        print(f"⚠️  Template not found at {template_path} — using minimal content")

    # Build pipeline instance content
    content = f"""---
primitive: analysis_pipeline
status: analysis_phase1_design
priority: {priority}
version: {version}
source_version: {source_version}
source_pkl_dir: {source_pkl}
output_notebook: SNN_research/machinelearning/snn_applied_finance/notebooks/crypto_{source_version}_analysis.ipynb
agents: [architect, critic, builder]
tags: {tags_str}
project: {project}
started: {now}
---

# Analysis Pipeline: {version.upper()}

## Description
{description}

## Source Data
- **Source Version:** `{source_version}`
- **Pkl Files:** `{source_pkl}`
- **Upload Method:** Individual pkl files OR single zip — notebook handles both

## Notebook Convention
**Both analysis phases live in a single notebook** (`crypto_{source_version}_analysis.ipynb`).
Phase 1 sections are autonomous statistical analysis; Phase 2 sections are appended after Shael's direction.

## Agent Coordination Protocol

**Filesystem-first:** All data exchange between agents happens via shared files, never through `sessions_send` message payloads.

| Action | Method | Example |
|--------|--------|---------|
| Share design/review/fix | Write file to `research/pipeline_builds/` | `{version}_architect_analysis_design.md` |
| Track stage transitions | `python3 scripts/pipeline_update.py {version} complete {{stage}} "{{notes}}" {{agent}}` | Auto-updates state JSON, markdown, pending_action |
| Block a stage (Critic) | `python3 scripts/pipeline_update.py {version} block {{stage}} "{{notes}}" {{agent}} --artifact {{file}}` | Sets pending_action to fix step |
| Notify another agent | `sessions_send` with `timeoutSeconds: 0` | "Analysis design ready" |
| Update Shael / group | `message` tool to group chat | "Phase 1 analysis complete — 5 findings" |

**Never** use `sessions_send` with a timeout > 0. Write the file first, ping second.

### Pipeline Update Script — Mandatory Usage
Every stage transition MUST go through `pipeline_update.py`. Always follow its printed ping instructions.

## Phase 1: Autonomous Analysis
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | {now} | belam-main | Analysis pipeline created |

## Phase 2: Directed Analysis (Human-in-the-Loop)
_Status: Queued — triggers after Phase 1 completion and Shael's input_

### Shael's Direction
_(Populated after Phase 1 completion)_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|

## Artifacts
- **Design Brief:** `snn_applied_finance/research/pipeline_builds/{version}_design_brief.md`
- **Architect Design:** `snn_applied_finance/research/pipeline_builds/{version}_architect_analysis_design.md`
- **Critic Review:** `snn_applied_finance/research/pipeline_builds/{version}_critic_analysis_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/{version}_state.json`
- **Notebook:** `snn_applied_finance/notebooks/crypto_{source_version}_analysis.ipynb`
"""

    # Create directories
    PIPELINES_DIR.mkdir(parents=True, exist_ok=True)
    BUILDS_DIR.mkdir(parents=True, exist_ok=True)

    # Write pipeline file
    pf.write_text(content)

    # Create initial state JSON
    state = {
        'version': version,
        'pipeline_type': 'analysis',
        'source_version': source_version,
        'source_pkl_dir': source_pkl,
        'status': 'analysis_phase1_design',
        'created': now,
        'phase1': {'stage': 'analysis_architect_design', 'started': now},
        'phase2': {'stage': 'queued'},
        'pending_action': 'analysis_architect_design',
    }
    state_file = BUILDS_DIR / f'{version}_state.json'
    state_file.write_text(json.dumps(state, indent=2))

    print(f"✅ Analysis pipeline created: {pf}")
    print(f"   State: {state_file}")
    print(f"   Status: analysis_phase1_design")

    return pf, state_file


def main():
    parser = argparse.ArgumentParser(description='Analysis Pipeline Launcher')
    parser.add_argument('version', nargs='?', help='Analysis version key (e.g. v4-analysis)')
    parser.add_argument('--desc', '-d', help='Pipeline description')
    parser.add_argument('--source-pkl', '-p', help='Path to pkl result files directory',
                        dest='source_pkl')
    parser.add_argument('--source-version', '-s', help='Source experiment version (e.g. v4)',
                        dest='source_version')
    parser.add_argument('--priority', default='high', choices=['critical', 'high', 'medium', 'low'])
    parser.add_argument('--tags', '-t', help='Comma-separated tags')
    parser.add_argument('--project', default='snn-applied-finance')
    parser.add_argument('--list', '-l', action='store_true', help='List all analysis pipelines')
    parser.add_argument('--archive', action='store_true', help='Archive a completed pipeline')
    parser.add_argument('--check-archive', action='store_true',
                        help='Check if a pipeline can be archived')
    args = parser.parse_args()

    if args.list:
        list_pipelines()
        return

    if not args.version:
        parser.print_help()
        return

    if args.check_archive:
        check_archivable(args.version)
        return

    if args.archive:
        archive_pipeline(args.version)
        return

    # Creating a new pipeline — validate required args
    if not args.desc:
        print("❌ --desc required when creating a new analysis pipeline")
        sys.exit(1)
    if not args.source_pkl:
        print("❌ --source-pkl required (path to pkl files directory)")
        sys.exit(1)
    if not args.source_version:
        print("❌ --source-version required (e.g. v4)")
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(',')] if args.tags else None

    print(f"\n🔬 Creating analysis pipeline: {args.version}")
    print(f"   Source: {args.source_version} pkl files at {args.source_pkl}")

    # Scan pkl metadata
    print(f"\n📂 Scanning pkl files...")
    metadata = scan_pkl_metadata(args.source_pkl)

    if metadata['errors'] and metadata['total_files'] == 0:
        print(f"⚠️  Could not find pkl files at {args.source_pkl}")
        print(f"   Pipeline will be created anyway — update design brief manually")
    else:
        print(f"   Found {metadata['total_files']} pkl files")
        if metadata['experiment_count'] > 0:
            print(f"   Estimated experiments/records: {metadata['experiment_count']}")

    # Create pipeline
    pf, state_file = create_pipeline(
        args.version, args.desc, args.source_version, args.source_pkl,
        args.priority, tags, args.project
    )

    # Generate design brief
    print(f"\n📝 Generating design brief...")
    brief = generate_design_brief(
        args.version, args.source_version, args.desc, args.source_pkl, metadata
    )
    brief_file = BUILDS_DIR / f'{args.version}_design_brief.md'
    brief_file.write_text(brief)
    print(f"   ✅ Design brief: {brief_file}")

    print(f"\n{'─' * 60}")
    print(f"✅ Analysis pipeline ready: {args.version}")
    print(f"\n📋 Files created:")
    print(f"   {pf.relative_to(WORKSPACE)}")
    print(f"   {state_file.relative_to(WORKSPACE)}")
    print(f"   {brief_file.relative_to(WORKSPACE)}")
    print(f"\n🚀 Next step — spawn the architect:")
    print(f"""
   Spawn architect agent with task:
   "Read pipelines/{args.version}.md and research/pipeline_builds/{args.version}_design_brief.md.
   Read research/ANALYSIS_AGENT_ROLES.md.
   Read skill at ~/.openclaw/workspace/skills/quant-workflow/SKILL.md.
   Design the analysis notebook for {args.source_version} pkl results.
   Write design to research/pipeline_builds/{args.version}_architect_analysis_design.md.
   Run: python3 scripts/pipeline_update.py {args.version} complete analysis_architect_design 'Design complete' architect"
""")


if __name__ == '__main__':
    main()
