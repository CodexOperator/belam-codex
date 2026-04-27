#!/usr/bin/env python3
"""
Implementation Pipeline Launcher

Creates a new pipeline instance from the template, sets up the build directory,
and optionally kicks off the Phase 1 architect agent.

Usage:
    # Create pipeline with description:
    python3 scripts/launch_pipeline.py v5 --desc "Equilibrium streaming with opponent-coded output"
    
    # Create with tags and priority:
    python3 scripts/launch_pipeline.py v5 --desc "..." --priority critical --tags snn,equilibrium,streaming
    
    # Create and immediately start Phase 1 architect:
    python3 scripts/launch_pipeline.py v5 --desc "..." --start
    
    # List active pipelines:
    python3 scripts/launch_pipeline.py --list
    
    # Archive a completed pipeline:
    python3 scripts/launch_pipeline.py v3 --archive
    
    # Check archival eligibility:
    python3 scripts/launch_pipeline.py v4 --check-archive
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

import yaml
from pathlib import Path

from pipeline_paths import (
    path_value,
    pipeline_builds_frontmatter_value,
    resolve_workspace_path,
    workspace_relative_path,
)

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
PIPELINES_DIR = WORKSPACE / 'pipelines'
FINANCE_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance'
BUILDS_DIR = FINANCE_DIR / 'research' / 'pipeline_builds'
SPECS_DIR = FINANCE_DIR / 'specs'
NOTEBOOKS_DIR = FINANCE_DIR / 'notebooks'


def list_pipelines():
    """List all pipeline instances with status."""
    if not PIPELINES_DIR.exists():
        print("No pipelines directory found.")
        return
    
    pipelines = sorted(PIPELINES_DIR.glob('*.md'))
    if not pipelines:
        print("No active pipelines.")
        return
    
    print(f"\n{'Version':<10} {'Status':<25} {'Priority':<10} {'Started':<12} {'Phase 3 Iters'}")
    print("─" * 80)
    
    for pf in pipelines:
        content = pf.read_text()
        # Extract frontmatter fields
        status = _extract_field(content, 'status') or 'unknown'
        priority = _extract_field(content, 'priority') or '—'
        started = _extract_field(content, 'started') or '—'
        version = pf.stem
        
        # Count phase 3 iterations
        phase3_count = content.count('| ') - content.count('| ID |') - content.count('| Stage |')
        # Rough count from iteration log table
        iter_rows = len(re.findall(r'\| \w+-\d+ \|', content))
        
        status_icon = {
            'archived': '📦',
            'phase1_': '🔨',
            'phase2_': '🔄',
            'phase3_': '🔬',
        }
        icon = '📦' if status == 'archived' else next(
            (v for k, v in status_icon.items() if status.startswith(k)), '❓'
        )
        
        print(f"{icon} {version:<8} {status:<25} {priority:<10} {started:<12} {iter_rows if iter_rows else '—'}")
    
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
    
    # Check for pending phase 3 proposals
    pending_proposals = list(BUILDS_DIR.glob(f'{version}_phase3_*_proposal.md'))
    has_pending = False
    for pp in pending_proposals:
        pp_content = pp.read_text()
        if 'status: approved' in pp_content or 'status: pending_review' in pp_content:
            has_pending = True
            break
    
    if has_pending:
        print(f"⏳ {version} has pending/approved Phase 3 proposals — cannot archive yet")
        return False
    
    archivable_statuses = ('phase1_complete', 'phase2_complete', 'phase3_complete',
                            'local_analysis_complete')
    if status and any(s in status for s in archivable_statuses):
        print(f"✅ {version} is eligible for archival (status: {status}, no pending iterations)")
        return True
    
    print(f"⏳ {version} not ready for archival (status: {status})")
    return False


def archive_pipeline(version, force=False):
    """Archive a completed pipeline."""
    pf = PIPELINES_DIR / f'{version}.md'
    if not pf.exists():
        print(f"❌ No pipeline found: {version}")
        sys.exit(1)
    
    if not check_archivable(version):
        if not force:
            print("Use --force to archive anyway.")
            sys.exit(1)
        print(f"⚠️  Force-archiving {version}")
    
    content = pf.read_text()
    # Update status to archived
    content = re.sub(r'^status:\s*.+$', 'status: archived', content, count=1, flags=re.MULTILINE)
    # Add archived date
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    content = re.sub(r'^(started:.+)$', f'\\1\narchived: {now}', content, count=1, flags=re.MULTILINE)
    pf.write_text(content)
    
    # Also update state JSON so plugins (pipeline-context) see the archive
    state_file = BUILDS_DIR / f'{version}_state.json'
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            state['status'] = 'archived'
            state_file.write_text(json.dumps(state, indent=2))
        except Exception:
            pass  # Don't fail archive on state JSON issues
    
    print(f"📦 {version} archived")
    
    # Auto-archive pipelines that this one supersedes
    archived_superseded = auto_archive_superseded_pipelines(version)
    if archived_superseded:
        for s in archived_superseded:
            print(f"  📦 Superseded pipeline auto-archived: {s}")
    
    # Auto-archive associated tasks whose work has moved downstream
    archived_tasks = auto_archive_downstream_tasks(version)
    if archived_tasks:
        for t in archived_tasks:
            print(f"  📋 Task auto-archived: {t}")


def auto_archive_superseded_pipelines(active_version=None):
    """Auto-archive pipelines that are superseded by active ones.
    
    Checks the 'supersedes' field in pipeline frontmatter. If pipeline A
    has 'supersedes: B' and A is active (not archived), then B should be
    archived — its work has moved forward into A.
    
    Can be called standalone (checks all pipelines) or with a specific
    active_version to only check what that version supersedes.
    """
    archived = []
    
    for pf in sorted(PIPELINES_DIR.glob('*.md')):
        content = pf.read_text()
        status = _extract_field(content, 'status')
        if status and 'archived' in status:
            continue  # Skip already-archived pipelines
        
        version = pf.stem
        
        # If called with a specific version, only check that one
        if active_version and version != active_version:
            continue
        
        # Check what this pipeline supersedes
        supersedes = _extract_field(content, 'supersedes')
        if not supersedes:
            continue
        
        # supersedes can be a single value or comma-separated list
        superseded_versions = [s.strip() for s in supersedes.split(',')]
        
        for sv in superseded_versions:
            sv_file = PIPELINES_DIR / f'{sv}.md'
            if not sv_file.exists():
                continue
            sv_content = sv_file.read_text()
            sv_status = _extract_field(sv_content, 'status')
            if sv_status and 'archived' in sv_status:
                continue  # Already archived
            
            # Archive the superseded pipeline
            print(f"  🔄 {sv} superseded by {version} — archiving")
            sv_content = re.sub(r'^status:\s*.+$', 'status: archived', sv_content, count=1, flags=re.MULTILINE)
            now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            if 'archived:' not in sv_content:
                sv_content = re.sub(r'^(started:.+)$', f'\\1\narchived: {now}\narchive_reason: superseded by {version}', sv_content, count=1, flags=re.MULTILINE)
            sv_file.write_text(sv_content)
            
            # Sync state JSON
            state_file = BUILDS_DIR / f'{sv}_state.json'
            if state_file.exists():
                try:
                    state = json.loads(state_file.read_text())
                    state['status'] = 'archived'
                    state_file.write_text(json.dumps(state, indent=2))
                except Exception:
                    pass
            
            archived.append(sv)
    
    return archived


def auto_archive_downstream_tasks(pipeline_version=None):
    """Auto-archive tasks whose work has provably moved downstream.
    
    Rules:
    1. Task status is 'complete' → work is done, archive it
    2. Task status is 'in_pipeline' AND its pipeline is archived → archive it
    3. Task has an open/active continuation task for the same pipeline
       (phase-continuation) AND the task itself is not the latest continuation
       → archive it
    
    Safety: never archive a task with status 'open' or 'active' unless Rule 3
    proves a continuation exists AND the task's pipeline is archived.
    
    If pipeline_version is given, only check tasks associated with that pipeline.
    Otherwise check all non-archived tasks.
    """
    tasks_dir = WORKSPACE / 'tasks'
    if not tasks_dir.exists():
        return []
    
    archived = []
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Build index of all tasks and pipeline statuses
    task_index = {}
    for tf in sorted(tasks_dir.glob('*.md')):
        content = tf.read_text()
        task_index[tf.stem] = {
            'path': tf,
            'status': _extract_field(content, 'status') or 'unknown',
            'pipeline': _extract_field(content, 'pipeline') or '',
            'phase': _extract_field(content, 'phase') or '',
            'depends_on': _parse_list_field(content, 'depends_on'),
            'downstream': _parse_list_field(content, 'downstream'),
            'content': content,
        }
    
    pipeline_statuses = {}
    if PIPELINES_DIR.exists():
        for pf in PIPELINES_DIR.glob('*.md'):
            pc = pf.read_text()
            pipeline_statuses[pf.stem] = _extract_field(pc, 'status') or 'unknown'
    
    for slug, info in task_index.items():
        if info['status'] in ('archived', 'superseded'):
            continue
        
        # Filter: if pipeline_version given, only process tasks for that pipeline
        if pipeline_version:
            if info['pipeline'] != pipeline_version and pipeline_version not in slug:
                continue
        
        should_archive = False
        reason = ''
        
        # Rule 1: Task is complete → work is done
        if info['status'] == 'complete':
            should_archive = True
            reason = 'status: complete'
        
        # Rule 2: Task is in_pipeline and its pipeline is archived
        if not should_archive and info['status'] == 'in_pipeline' and info['pipeline']:
            pipe_status = pipeline_statuses.get(info['pipeline'], '')
            if pipe_status == 'archived':
                should_archive = True
                reason = f"pipeline {info['pipeline']} archived"
        
        # Rule 2b: Task is in_pipeline, no explicit pipeline field, but we can
        # infer the pipeline from the task slug matching an archived pipeline
        if not should_archive and info['status'] == 'in_pipeline' and not info['pipeline']:
            for pipe_ver, pipe_stat in pipeline_statuses.items():
                if pipe_stat == 'archived' and pipe_ver in slug:
                    should_archive = True
                    reason = f"inferred pipeline {pipe_ver} archived"
                    break
        
        # Rule 3: Task references a pipeline that's archived AND a later
        # phase-continuation task exists (so this task is not the latest).
        # Only applies to non-complete tasks (open tasks waiting on a reopened pipeline).
        if not should_archive and info['status'] == 'open' and info['pipeline']:
            pipe_status = pipeline_statuses.get(info['pipeline'], '')
            if pipe_status == 'archived':
                # Check if another non-archived task exists for the same pipeline
                # with a LATER phase number
                my_phase = int(info['phase']) if info['phase'].isdigit() else 0
                for other_slug, other_info in task_index.items():
                    if other_slug == slug:
                        continue
                    if other_info['status'] in ('archived', 'superseded'):
                        continue
                    if other_info.get('pipeline') == info['pipeline']:
                        other_phase = int(other_info['phase']) if other_info.get('phase', '').isdigit() else 0
                        if other_phase > my_phase:
                            should_archive = True
                            reason = f"continuation task {other_slug} (phase {other_phase}) supersedes (phase {my_phase})"
                            break
        
        if should_archive:
            _archive_task(info['path'], now, reason)
            archived.append(slug)
    
    return archived


def _archive_task(task_path, date_str, reason=''):
    """Archive a single task file."""
    content = task_path.read_text()
    content = re.sub(r'^status:\s*.+$', 'status: archived', content, count=1, flags=re.MULTILINE)
    # Add archived date if not present
    if not re.search(r'^archived:', content, re.MULTILINE):
        content = re.sub(r'^(created:.+)$', f'\\1\narchived: {date_str}', content, count=1, flags=re.MULTILINE)
    if reason:
        content = re.sub(r'^(archived:.+)$', f'\\1\narchive_reason: {reason}', content, count=1, flags=re.MULTILINE)
    task_path.write_text(content)


def _parse_list_field(content, field):
    """Parse a YAML list field like 'depends_on: [a, b, c]' into a Python list."""
    match = re.search(rf'^{field}:\s*\[([^\]]*)\]', content, re.MULTILINE)
    if not match:
        return []
    raw = match.group(1).strip()
    if not raw:
        return []
    return [item.strip().strip('"').strip("'") for item in raw.split(',')]


def link_tasks_to_pipeline(pipeline_version):
    """Auto-set the pipeline field on tasks associated with a pipeline.
    
    Matching strategy (in order):
    1. Task already has pipeline: <version> → skip (already linked)
    2. Task slug matches the pipeline version exactly → link
    3. Task slug is a prefix/suffix match (e.g., task 'codex-engine-v3-foo'
       matches pipeline 'codex-engine-v3') → link
    4. Task's depends_on references a task that's linked to this pipeline → link
    
    Only links tasks that don't already have a pipeline field set.
    Returns list of (task_slug, match_reason) tuples.
    """
    tasks_dir = WORKSPACE / 'tasks'
    if not tasks_dir.exists():
        return []
    
    linked = []
    
    for tf in sorted(tasks_dir.glob('*.md')):
        content = tf.read_text()
        status = _extract_field(content, 'status')
        if status in ('archived', 'superseded'):
            continue
        
        existing_pipeline = _extract_field(content, 'pipeline')
        if existing_pipeline:
            continue  # Already linked
        
        slug = tf.stem
        reason = ''
        
        # Strategy 2: Exact slug match (task slug == pipeline version)
        if slug == pipeline_version:
            reason = 'exact slug match'
        
        # Strategy 3: Task slug starts with pipeline version
        # (e.g., codex-engine-v3-legendary-map starts with codex-engine-v3)
        elif slug.startswith(pipeline_version + '-'):
            reason = f'slug prefix: {pipeline_version}'
        
        # Strategy 3b: Pipeline version starts with task slug
        # (e.g., pipeline codex-engine-v2-modes matches task codex-engine-v2-modes-mcp-temporal)
        # Only if the task slug is long enough to be meaningful (>10 chars)
        elif len(slug) > 10 and pipeline_version.startswith(slug):
            reason = f'pipeline prefix: {slug}'
        
        if reason:
            # Insert pipeline field into frontmatter
            content = re.sub(
                r'^(tags:\s*.+)$',
                f'\\1\npipeline: {pipeline_version}',
                content, count=1, flags=re.MULTILINE
            )
            tf.write_text(content)
            linked.append((slug, reason))
    
    return linked


def create_pipeline(version, description, priority='high', tags=None, project='snn-applied-finance',
                    pipeline_type='research', supersedes='', project_root=None,
                    builds_dir=None, pipeline_builds_dir=None, spec_file=None,
                    output_notebook=None):
    """Create a new pipeline instance."""
    pf = PIPELINES_DIR / f'{version}.md'
    if pf.exists():
        print(f"❌ Pipeline {version} already exists: {pf}")
        sys.exit(1)
    
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    is_infra = pipeline_type == 'infrastructure'
    project_root_value = path_value(project_root) or workspace_relative_path(WORKSPACE, FINANCE_DIR)
    builds_dir_value = pipeline_builds_frontmatter_value(
        WORKSPACE,
        pipeline_builds_dir or builds_dir,
        BUILDS_DIR,
    )
    spec_file_value = None if is_infra else (
        path_value(spec_file)
        or f'{project_root_value}/specs/{version}_spec.yaml'
    )
    output_notebook_value = None if is_infra else (
        path_value(output_notebook)
        or f'{project_root_value}/notebooks/snn_crypto_predictor_{version}.ipynb'
    )

    # Parse template for pipeline_fields and seed phase_map when template exists
    template_type = pipeline_type
    parsed = None
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from template_parser import parse_template
        parsed = parse_template(pipeline_type)
        if parsed and parsed.get('pipeline_fields', {}).get('type'):
            template_type = parsed['pipeline_fields']['type']
    except Exception:
        parsed = None  # Fall back to using pipeline_type as-is

    phase_map = None
    if parsed:
        template_file = WORKSPACE / 'templates' / f'{pipeline_type}-pipeline.md'
        if template_file.exists():
            content = template_file.read_text()
            match = re.search(r'## Stage Transitions.*?```yaml\s*\n(.*?)```', content, re.DOTALL)
            if match:
                try:
                    template_yaml = yaml.safe_load(match.group(1)) or {}
                except Exception:
                    template_yaml = {}
                if isinstance(template_yaml, dict) and isinstance(template_yaml.get('phases'), dict):
                    phase_map = dict(template_yaml.get('phases', {}))
                    if 'block_routing' in template_yaml:
                        phase_map['block_routing'] = template_yaml.get('block_routing', {})
                    if 'auto_complete_on_clean_pass' in template_yaml:
                        phase_map['auto_complete_on_clean_pass'] = template_yaml.get('auto_complete_on_clean_pass', False)
                    if 'complete_task_agent' in template_yaml:
                        phase_map['complete_task_agent'] = template_yaml.get('complete_task_agent', 'architect')

    # Build frontmatter
    frontmatter = {
        'primitive': 'pipeline',
        'status': 'phase1_design',
        'priority': priority,
        'type': template_type,
        'version': version,
        'project_root': project_root_value,
        'pipeline_builds_dir': builds_dir_value,
    }
    if not is_infra:
        frontmatter['spec_file'] = spec_file_value
        frontmatter['output_notebook'] = output_notebook_value
    frontmatter['agents'] = ['architect', 'critic', 'builder']
    frontmatter['supersedes'] = supersedes
    frontmatter['tags'] = tags if tags else ['snn', 'finance']
    frontmatter['project'] = project
    frontmatter['started'] = now
    if phase_map:
        frontmatter['phase_map'] = phase_map

    fm_text = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
    fm_lines = ['---', fm_text, '---']
    
    # Build body
    if is_infra:
        notebook_section = """## Type
Infrastructure pipeline — no notebook, no experiment. Deliverables are code, hooks, plugins, and config files.
At phase1_complete, this pipeline is ready for human review and archival (no experiment/analysis phases)."""
    else:
        notebook_section = f"""## Notebook Convention
**All phases live in a single notebook** (`{output_notebook_value}`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis."""
    
    if is_infra:
        artifacts_section = f"""## Artifacts
- **Project Root:** `{project_root_value}`
- **Build Artifacts:** `{builds_dir_value}/`
- **State:** `{builds_dir_value}/{version}_state.json`
"""
    else:
        artifacts_section = f"""## Artifacts
- **Project Root:** `{project_root_value}`
- **Spec:** `{spec_file_value}`
- **Design:** `{builds_dir_value}/{version}_architect_design.md`
- **Review:** `{builds_dir_value}/{version}_critic_design_review.md`
- **State:** `{builds_dir_value}/{version}_state.json`
- **Notebook:** `{output_notebook_value}`
"""

    # Create pipeline instance
    content = '\n'.join(fm_lines) + f"""

# Implementation Pipeline: {version.upper()}

## Description
{description}

{notebook_section}

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | {now} | belam-main | Pipeline instance created |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Feedback
_(Shael's feedback goes here when Phase 1 is complete and reviewed)_

## Phase 3: Iterative Research (Autonomous or Human-Triggered)
_Status: LOCKED — requires Phase 2 completion before activation_

**Gate condition:** `phase2_complete` must be set before any Phase 3 iteration can proceed.

### How Phase 3 Works

1. **Human-triggered:** Shael says "try X" → iteration created and built
2. **Agent-triggered:** Analysis reveals compelling follow-up → proposal generated:
   - Score ≥ 7: auto-approved
   - Score 4-6: flagged for Shael's review
   - Score < 4: rejected, logged only

### Iteration Log

| ID | Hypothesis | Proposed By | Status | Result |
|----|-----------|-------------|--------|--------|

{artifacts_section}"""
    
    # Create directories
    PIPELINES_DIR.mkdir(parents=True, exist_ok=True)
    builds_dir_path = resolve_workspace_path(WORKSPACE, builds_dir_value)
    if builds_dir_path is not None:
        builds_dir_path.mkdir(parents=True, exist_ok=True)
    if spec_file_value:
        spec_path = resolve_workspace_path(WORKSPACE, spec_file_value)
        if spec_path is not None:
            spec_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write pipeline file
    pf.write_text(content)
    
    # Create initial state JSON
    state = {
        'version': version,
        'status': 'phase1_design',
        'created': now,
        'phase1': {'stage': 'design', 'started': now},
        'phase2': {'stage': 'queued'},
        'phase3': {'gate': 'locked', 'iterations': []},
    }
    state_file = builds_dir_path / f'{version}_state.json'
    state_file.write_text(json.dumps(state, indent=2))
    
    print(f"✅ Pipeline created: {pf}")
    print(f"   State: {state_file}")
    print(f"   Status: phase1_design")
    if spec_file_value:
        print(f"   Next: Create spec at {spec_file_value}, then spawn architect agent")
    else:
        print(f"   Next: Spawn architect agent")
    
    # Auto-link tasks to this pipeline
    linked = link_tasks_to_pipeline(version)
    if linked:
        for task_slug, reason in linked:
            print(f"   📋 Linked task: {task_slug} ({reason})")
    
    return pf


def main():
    parser = argparse.ArgumentParser(description='Implementation Pipeline Launcher')
    parser.add_argument('version', nargs='?', help='Version key (v4, v5, ...)')
    parser.add_argument('--desc', '-d', help='Pipeline description')
    parser.add_argument('--priority', '-p', default='high', choices=['critical', 'high', 'medium', 'low'])
    parser.add_argument('--tags', '-t', help='Comma-separated tags')
    parser.add_argument('--type', default='research',
                        help='Pipeline type: research, infrastructure, or a template name (e.g. builder-first)')
    parser.add_argument('--template', default=None,
                        help='Pipeline template name (e.g. builder-first). Sets --type to the template name.')
    parser.add_argument('--project', default='snn-applied-finance')
    parser.add_argument('--supersedes', default='', help='Pipeline version this one supersedes (auto-archives the old one)')
    parser.add_argument('--project-root', help='Workspace-relative or absolute project root for pipeline artifacts')
    parser.add_argument('--builds-dir', help='Workspace-relative or absolute pipeline_builds dir')
    parser.add_argument('--pipeline-builds-dir', help='Alias for --builds-dir')
    parser.add_argument('--spec-file', help='Workspace-relative or absolute spec file path')
    parser.add_argument('--output-notebook', help='Workspace-relative or absolute notebook output path')
    parser.add_argument('--list', '-l', action='store_true', help='List all pipelines')
    parser.add_argument('--archive', action='store_true', help='Archive a completed pipeline')
    parser.add_argument('--force', action='store_true', help='Force archive even if gate check fails')
    parser.add_argument('--check-archive', action='store_true', help='Check if a pipeline can be archived')
    parser.add_argument('--check-supersedes', action='store_true', help='Auto-archive pipelines superseded by active ones')
    parser.add_argument('--start', action='store_true', help='Start Phase 1 immediately (prints agent task)')
    parser.add_argument('--kickoff', '-k', action='store_true',
                        help='Send task to architect agent via sessions_send after creation')
    parser.add_argument('--wiggum', '-w', action='store_true',
                        help='Use auto_wiggum.py for dispatch (steer timer + auto-recovery)')
    parser.add_argument('--wiggum-timeout', type=int, default=600,
                        help='Timeout in seconds for wiggum dispatch (default: 600)')
    args = parser.parse_args()
    
    if args.list:
        list_pipelines()
        return
    
    if args.check_supersedes:
        archived = auto_archive_superseded_pipelines()
        if archived:
            for a in archived:
                print(f"📦 Auto-archived superseded pipeline: {a}")
        else:
            print("✅ No superseded pipelines to archive.")
        return
    
    if not args.version:
        parser.print_help()
        return
    
    if args.check_archive:
        check_archivable(args.version)
        return
    
    if args.archive:
        archive_pipeline(args.version, force=args.force)
        return
    
    if not args.desc:
        print("❌ --desc required when creating a new pipeline")
        sys.exit(1)
    
    # Template overrides type
    pipeline_type = args.template if args.template else args.type
    
    tags = [t.strip() for t in args.tags.split(',')] if args.tags else None
    pf = create_pipeline(args.version, args.desc, args.priority, tags, args.project,
                         pipeline_type=pipeline_type, supersedes=args.supersedes,
                         project_root=args.project_root,
                         builds_dir=args.builds_dir,
                         pipeline_builds_dir=args.pipeline_builds_dir,
                         spec_file=args.spec_file,
                         output_notebook=args.output_notebook)
    
    if args.kickoff or args.start:
        print(f"\n🚀 Kicking off (fire-and-forget)...")
        sys.path.insert(0, str(Path(__file__).parent))
        from orchestration_engine import fire_and_forget_dispatch, resolve_transition
        from pipeline_orchestrate import orchestrate_status

        # Resolve first stage from template (or default to architect_design)
        transition = resolve_transition(args.version, 'pipeline_created')
        if transition:
            first_stage, first_agent, _ = transition
        else:
            first_stage, first_agent = 'architect_design', 'architect'

        # 0. Reset agent session for clean context
        from pipeline_orchestrate import reset_agent_session
        print(f"   🔄 Resetting {first_agent} session for fresh context...")
        reset_agent_session(first_agent)

        # 1. State transition
        orchestrate_status(args.version, first_stage)
        print(f"   ✅ State: {first_stage}")

        # 2. Dispatch — use auto_wiggum if --wiggum flag set, otherwise fire-and-forget
        wiggum_flag = getattr(args, 'wiggum', False)
        wiggum_timeout = getattr(args, 'wiggum_timeout', 600)
        if wiggum_flag:
            # Use auto_wiggum.py for steer-timer-aware dispatch
            wiggum_script = str(Path(__file__).parent / 'auto_wiggum.py')
            task_msg = (
                f"Pipeline {args.version} stage {first_stage}. "
                f"Read the pipeline file at pipelines/{args.version}.md and any spec/design docs. "
                f"Implement the stage, run tests, then complete: "
                f"python3 scripts/pipeline_orchestrate.py {args.version} complete {first_stage}"
            )
            import subprocess as _sp
            wiggum_cmd = [
                sys.executable, wiggum_script,
                '--agent', first_agent,
                '--timeout', str(wiggum_timeout),
                '--task', task_msg,
                '--pipeline', args.version,
                '--stage', first_stage,
                # Default (no flag): restart stage on hard timeout — safe recovery path.
                # Use --complete-on-exit only if caller explicitly wants forward-advance.
                '--restart-on-exit',
            ]
            # Launch in background (nohup-style)
            proc = _sp.Popen(
                wiggum_cmd,
                stdout=open(f'/tmp/wiggum_{args.version}.log', 'a'),
                stderr=_sp.STDOUT,
                cwd=str(WORKSPACE),
                start_new_session=True,
            )
            print(f"   ✅ {first_agent.title()} dispatched via auto_wiggum (pid={proc.pid}, timeout={wiggum_timeout}s)")
            print(f"   📋 Steer at {int(wiggum_timeout * 0.8)}s, hard timeout at {wiggum_timeout}s")
            print(f"   📄 Log: /tmp/wiggum_{args.version}.log")
        else:
            # Classic fire-and-forget dispatch
            result = fire_and_forget_dispatch(args.version, first_stage, first_agent)
            if result['success']:
                print(f"   ✅ {first_agent.title()} dispatched (pid={result['pid']})")
            else:
                print(f"   ⚠️  Dispatch failed: {result['error']}")
                print(f"   Manual fallback: python3 scripts/orchestration_engine.py dispatch {args.version}")
    else:
        print(f"\n🚀 Pipeline created. Kick off with:")
        print(f"   R kickoff {args.version}")
        print(f"\n   Or re-run with --kickoff to send automatically:")
        print(f"   python3 scripts/launch_pipeline.py {args.version} ... --kickoff")


if __name__ == '__main__':
    main()
