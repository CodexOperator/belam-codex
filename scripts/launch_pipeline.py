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
from pathlib import Path

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
    
    if status and 'phase2_complete' in status or 'phase3_complete' in status:
        print(f"✅ {version} is eligible for archival (status: {status}, no pending iterations)")
        return True
    
    print(f"⏳ {version} not ready for archival (status: {status})")
    return False


def archive_pipeline(version):
    """Archive a completed pipeline."""
    pf = PIPELINES_DIR / f'{version}.md'
    if not pf.exists():
        print(f"❌ No pipeline found: {version}")
        sys.exit(1)
    
    if not check_archivable(version):
        print("Use --force to archive anyway.")
        sys.exit(1)
    
    content = pf.read_text()
    # Update status to archived
    content = re.sub(r'^status:\s*.+$', 'status: archived', content, count=1, flags=re.MULTILINE)
    # Add archived date
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    content = re.sub(r'^(started:.+)$', f'\\1\narchived: {now}', content, count=1, flags=re.MULTILINE)
    pf.write_text(content)
    print(f"📦 {version} archived")


def create_pipeline(version, description, priority='high', tags=None, project='snn-applied-finance'):
    """Create a new pipeline instance."""
    pf = PIPELINES_DIR / f'{version}.md'
    if pf.exists():
        print(f"❌ Pipeline {version} already exists: {pf}")
        sys.exit(1)
    
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    tags_str = f"[{', '.join(tags)}]" if tags else '[snn, finance]'
    
    # Create pipeline instance
    content = f"""---
primitive: pipeline
status: phase1_design
priority: {priority}
version: {version}
spec_file: machinelearning/snn_applied_finance/specs/{version}_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_{version}.ipynb
agents: [architect, critic, builder]
tags: {tags_str}
project: {project}
started: {now}
---

# Implementation Pipeline: {version.upper()}

## Description
{description}

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_{version}.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

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

## Artifacts
- **Spec:** `snn_applied_finance/specs/{version}_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/{version}_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/{version}_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/{version}_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_{version}.ipynb`
"""
    
    # Create directories
    PIPELINES_DIR.mkdir(parents=True, exist_ok=True)
    BUILDS_DIR.mkdir(parents=True, exist_ok=True)
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    
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
    state_file = BUILDS_DIR / f'{version}_state.json'
    state_file.write_text(json.dumps(state, indent=2))
    
    print(f"✅ Pipeline created: {pf}")
    print(f"   State: {state_file}")
    print(f"   Status: phase1_design")
    print(f"   Next: Create spec at specs/{version}_spec.yaml, then spawn architect agent")
    
    return pf


def main():
    parser = argparse.ArgumentParser(description='Implementation Pipeline Launcher')
    parser.add_argument('version', nargs='?', help='Version key (v4, v5, ...)')
    parser.add_argument('--desc', '-d', help='Pipeline description')
    parser.add_argument('--priority', '-p', default='high', choices=['critical', 'high', 'medium', 'low'])
    parser.add_argument('--tags', '-t', help='Comma-separated tags')
    parser.add_argument('--project', default='snn-applied-finance')
    parser.add_argument('--list', '-l', action='store_true', help='List all pipelines')
    parser.add_argument('--archive', action='store_true', help='Archive a completed pipeline')
    parser.add_argument('--check-archive', action='store_true', help='Check if a pipeline can be archived')
    parser.add_argument('--start', action='store_true', help='Start Phase 1 immediately (prints agent task)')
    parser.add_argument('--kickoff', '-k', action='store_true',
                        help='Send task to architect agent via sessions_send after creation')
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
    
    if not args.desc:
        print("❌ --desc required when creating a new pipeline")
        sys.exit(1)
    
    tags = [t.strip() for t in args.tags.split(',')] if args.tags else None
    pf = create_pipeline(args.version, args.desc, args.priority, tags, args.project)
    
    architect_task = (
        f"🔨 New Builder Pipeline: {args.version}\n\n"
        f"You've been assigned as architect for a new BUILDER pipeline.\n\n"
        f"**Read these files first:**\n"
        f"1. `pipelines/{args.version}.md` — the pipeline instance\n"
        f"2. `machinelearning/snn_applied_finance/specs/{args.version}_spec.yaml` — experiment spec\n"
        f"3. `machinelearning/snn_applied_finance/research/AGENT_SOUL.md` — agent principles\n"
        f"4. `machinelearning/snn_applied_finance/research/ARCHITECT_KNOWLEDGE.md` — your knowledge base\n\n"
        f"**Your task:** Design the full notebook architecture following the Implementation Pipeline flow.\n"
        f"Write design to `machinelearning/snn_applied_finance/research/pipeline_builds/{args.version}_architect_design.md`.\n"
        f"Then run: `python3 scripts/pipeline_update.py {args.version} complete architect_design 'Design complete' architect`\n"
        f"Post update to group chat. The script will tell you to ping the critic next."
    )

    if args.kickoff or args.start:
        print(f"\n🚀 Sending task to architect agent via sessions_send...")
        import subprocess as sp
        result = sp.run(
            ['openclaw', 'sessions', 'send',
             '--session', 'agent:architect:telegram:group:-5243763228',
             '--message', architect_task,
             '--timeout', '0'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"   ✅ Task sent to architect agent")
        else:
            print(f"   ⚠️  Failed to send via CLI, falling back to manual instructions")
            print(f"   Send manually via sessions_send to: agent:architect:telegram:group:-5243763228")
    else:
        print(f"\n🚀 Next step — send to architect agent:")
        print(f"   Session: agent:architect:telegram:group:-5243763228")
        print(f"   Use sessions_send with timeoutSeconds: 0")
        print(f"\n   Or re-run with --kickoff to send automatically:")
        print(f"   python3 scripts/launch_pipeline.py {args.version} ... --kickoff")


if __name__ == '__main__':
    main()
