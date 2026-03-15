#!/usr/bin/env python3
"""
Experiment Analysis Pipeline

Analyzes notebook experiments — results, Shael's code tweaks, and generates
structured lessons as primitives.

Usage:
    # Manual trigger (specific notebook):
    python3 scripts/analyze_experiment.py --notebook v3
    
    # Manual trigger (detect all new changes):
    python3 scripts/analyze_experiment.py --detect
    
    # Called by heartbeat (auto-detect mode):
    python3 scripts/analyze_experiment.py --detect --quiet

What it does:
    1. Detects new/changed notebooks and result files via git diff
    2. Extracts Shael's code tweaks (diff between notebook versions)
    3. Reads run results and deep analysis
    4. Generates a structured analysis brief for the agent
    5. Outputs to research/pipeline_output/ for agent consumption

The agent then reads the pipeline output and:
    - Creates/updates lesson primitives
    - Updates TECHNIQUES_TRACKER.md
    - Updates MEMORY.md if warranted
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FINANCE_DIR = Path(os.environ.get(
    'FINANCE_DIR',
    os.path.expanduser('~/.openclaw/workspace/SNN_research/machinelearning/snn_applied_finance')
))
NOTEBOOKS_DIR = FINANCE_DIR / 'notebooks'
RESEARCH_DIR = FINANCE_DIR / 'research'
OUTPUT_DIR = RESEARCH_DIR / 'pipeline_output'
REPO_DIR = FINANCE_DIR.parent  # machinelearning/

NOTEBOOK_ALIASES = {
    'v1': 'snn_crypto_predictor.ipynb',
    'v2': 'snn_crypto_predictor_v2.ipynb',
    'v3': 'snn_crypto_predictor_v3.ipynb',
    'v4': 'snn_crypto_predictor_v4.ipynb',
    'baseline': 'quant_baseline.ipynb',
    'stock': 'snn_stock_predictor.ipynb',
}

PIPELINE_DIR = Path(os.environ.get(
    'PIPELINE_DIR',
    os.path.expanduser('~/.openclaw/workspace/pipelines')
))
BUILDS_DIR = RESEARCH_DIR / 'pipeline_builds'


def git_run(*args, cwd=None):
    """Run a git command and return stdout."""
    result = subprocess.run(
        ['git'] + list(args),
        capture_output=True, text=True,
        cwd=cwd or REPO_DIR
    )
    return result.stdout.strip()


def detect_changes():
    """Detect new/changed notebooks and results since last analysis."""
    # Check for changes not yet analyzed
    marker = OUTPUT_DIR / '.last_analysis'
    
    changes = {
        'notebooks': [],
        'results': [],
        'analyses': [],
    }
    
    if marker.exists():
        since = marker.read_text().strip()
        # Files changed since last analysis
        diff = git_run('diff', '--name-only', since, 'HEAD', '--',
                       'snn_applied_finance/notebooks/',
                       'snn_applied_finance/research/')
    else:
        # First run — check last 5 commits
        diff = git_run('diff', '--name-only', 'HEAD~5', 'HEAD', '--',
                       'snn_applied_finance/notebooks/',
                       'snn_applied_finance/research/')
    
    if not diff:
        # Also check uncommitted changes
        diff = git_run('diff', '--name-only', '--',
                       'snn_applied_finance/notebooks/',
                       'snn_applied_finance/research/')
        diff += '\n' + git_run('diff', '--name-only', '--cached', '--',
                               'snn_applied_finance/notebooks/',
                               'snn_applied_finance/research/')
    
    for line in diff.split('\n'):
        line = line.strip()
        if not line:
            continue
        if 'notebooks/' in line and line.endswith('.ipynb'):
            changes['notebooks'].append(line)
        elif 'run_results' in line or 'results' in line:
            changes['results'].append(line)
        elif 'analysis' in line or 'deep_analysis' in line:
            changes['analyses'].append(line)
    
    return changes


def get_notebook_diff(notebook_name):
    """Get the diff of a specific notebook to see Shael's tweaks."""
    nb_path = f'snn_applied_finance/notebooks/{notebook_name}'
    
    # Get diff from last 3 commits
    diff = git_run('log', '-3', '--patch', '--', nb_path)
    
    if not diff:
        return None
    
    # Filter to meaningful code changes (skip output cells, metadata)
    meaningful_lines = []
    for line in diff.split('\n'):
        # Skip notebook output/metadata noise
        if any(skip in line for skip in [
            '"execution_count"', '"output_type"', '"image/png"',
            '"text/plain"', '"data":', '"metadata":', '"outputs":',
            '\\n",' # multiline string continuations in output
        ]):
            continue
        if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
            meaningful_lines.append(line)
    
    return '\n'.join(meaningful_lines) if meaningful_lines else None


def read_file_safe(path):
    """Read a file, return None if missing."""
    try:
        return Path(path).read_text()
    except (FileNotFoundError, IsADirectoryError):
        return None


def find_related_files(notebook_key):
    """Find results, analyses, and critiques for a notebook version."""
    related = {}
    
    patterns = {
        'run_results': f'{notebook_key}_run_results.md',
        'deep_analysis': f'{notebook_key}_deep_analysis.md',
        'critique': f'{notebook_key}_critique.md',
        'proposal': f'proposal_{notebook_key}*.md',
    }
    
    for key, pattern in patterns.items():
        if '*' in pattern:
            matches = list(RESEARCH_DIR.glob(pattern))
            if matches:
                related[key] = matches[0].read_text()
        else:
            content = read_file_safe(RESEARCH_DIR / pattern)
            if content:
                related[key] = content
    
    return related


def generate_analysis_brief(notebook_key, notebook_name, diff, related_files):
    """Generate a structured analysis brief for the agent."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    brief = f"""---
generated: {now}
notebook: {notebook_name}
version_key: {notebook_key}
type: experiment_analysis_brief
status: pending_review
---

# Experiment Analysis Brief: {notebook_key}

## Notebook
`notebooks/{notebook_name}`

"""
    
    if diff:
        brief += f"""## Code Changes (Shael's Tweaks)

These are the meaningful code changes made to the notebook. Each tweak represents
a design decision worth understanding and potentially extracting as a lesson.

```diff
{diff[:5000]}
```

### Questions for Analysis
- What problem was each tweak solving?
- Do any tweaks represent a pattern we should codify?
- Should any tweaks be reflected in TECHNIQUES_TRACKER.md?

"""
    
    if 'run_results' in related_files:
        brief += f"""## Run Results

{related_files['run_results'][:8000]}

"""
    
    if 'deep_analysis' in related_files:
        brief += f"""## Deep Analysis

{related_files['deep_analysis'][:8000]}

"""
    
    if 'critique' in related_files:
        brief += f"""## Critique

{related_files['critique'][:5000]}

"""
    
    brief += """## Agent Instructions

After reviewing this brief:
1. Extract lessons as primitives in `tasks/` or `lessons/` 
2. Update `research/TECHNIQUES_TRACKER.md` with any new findings
3. Update the relevant `*_KNOWLEDGE.md` files if warranted
4. Mark this brief as `status: processed` in the frontmatter
5. If Shael's tweaks reveal a recurring pattern, create a decision primitive

Focus especially on:
- What Shael changed and WHY (the tweaks are the highest-signal data)
- What the results tell us about the solution space
- What to try next based on the analysis
"""
    
    return brief


def check_phase2_complete(version_key):
    """Check if a pipeline's Phase 2 is complete (gate for Phase 3)."""
    pipeline_files = list(PIPELINE_DIR.glob(f'*{version_key}*.md'))
    if not pipeline_files:
        # No pipeline file — allow (manual notebooks without pipeline tracking)
        return True
    for pf in pipeline_files:
        content = pf.read_text()
        if 'status: phase2_complete' in content or 'status: phase3_' in content:
            return True
    return False


def generate_phase3_proposal(version_key, iteration_id, hypothesis, justification_text, 
                              justification_score, proposed_by='agent', estimated_gpu_min=30,
                              expected_outcome='', colab_code=None):
    """Generate a Phase 3 iteration proposal for agent-driven research."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    BUILDS_DIR.mkdir(parents=True, exist_ok=True)
    
    proposal = f"""---
generated: {now}
version_key: {version_key}
iteration_id: {iteration_id}
type: phase3_proposal
status: {'approved' if justification_score >= 7 else 'pending_review' if justification_score >= 4 else 'rejected'}
proposed_by: {proposed_by}
justification_score: {justification_score}
estimated_gpu_minutes: {estimated_gpu_min}
---

# Phase 3 Proposal: {version_key} — Iteration {iteration_id}

## Hypothesis
{hypothesis}

## Expected Outcome
{expected_outcome or 'TBD — agent will determine based on prior results'}

## Justification (Score: {justification_score}/10)
{justification_text}

## Estimated GPU Time
~{estimated_gpu_min} minutes

## Proposed By
{proposed_by} at {now}
"""
    
    if colab_code:
        proposal += f"""
## Colab Code Addition

```python
{colab_code}
```
"""

    proposal += """
## Agent Instructions

If this proposal is `approved`:
1. Add this iteration to the pipeline's Phase 3 Iteration Log
2. Build the experiment (update existing notebook or create a new cell block)
3. If GPU code is included, add it to the Colab notebook with clear section markers
4. Run through the standard architect → critic → builder flow if the change is substantial
5. After results: update TECHNIQUES_TRACKER, create lesson primitives, update the Iteration Log with results

If `pending_review`:
- Flag this in the next heartbeat alert for Shael's approval
- Do NOT proceed with building until status changes to `approved`

If `rejected`:
- Log the hypothesis in TECHNIQUES_TRACKER as "proposed but rejected (low justification)"
- No further action needed
"""
    
    output_path = BUILDS_DIR / f'{version_key}_phase3_{iteration_id}_proposal.md'
    output_path.write_text(proposal)
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Experiment Analysis Pipeline')
    parser.add_argument('--notebook', '-n', help='Specific notebook key (v1, v2, v3, v4, baseline, stock)')
    parser.add_argument('--detect', '-d', action='store_true', help='Auto-detect changed notebooks')
    parser.add_argument('--quiet', '-q', action='store_true', help='No output unless changes found')
    parser.add_argument('--list', '-l', action='store_true', help='List pending analysis briefs')
    parser.add_argument('--propose', action='store_true', help='Generate a Phase 3 proposal (interactive)')
    parser.add_argument('--propose-auto', metavar='JSON', help='Generate Phase 3 proposal from JSON: {"version":"v4","id":"01","hypothesis":"...","justification":"...","score":8,"proposed_by":"agent","gpu_min":30}')
    parser.add_argument('--check-gate', metavar='VERSION', help='Check if Phase 2 is complete for a version (exit 0=open, 1=locked)')
    args = parser.parse_args()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.check_gate:
        is_open = check_phase2_complete(args.check_gate)
        if is_open:
            print(f"✅ Phase 3 gate OPEN for {args.check_gate} — Phase 2 complete")
            sys.exit(0)
        else:
            print(f"🔒 Phase 3 gate LOCKED for {args.check_gate} — Phase 2 not yet complete")
            sys.exit(1)
    
    if args.propose_auto:
        data = json.loads(args.propose_auto)
        version = data['version']
        if not check_phase2_complete(version):
            print(f"🔒 Phase 3 gate LOCKED for {version} — cannot propose until Phase 2 completes")
            sys.exit(1)
        path = generate_phase3_proposal(
            version_key=version,
            iteration_id=data['id'],
            hypothesis=data['hypothesis'],
            justification_text=data['justification'],
            justification_score=data['score'],
            proposed_by=data.get('proposed_by', 'agent'),
            estimated_gpu_min=data.get('gpu_min', 30),
            expected_outcome=data.get('expected_outcome', ''),
            colab_code=data.get('colab_code'),
        )
        status = 'APPROVED' if data['score'] >= 7 else 'PENDING REVIEW' if data['score'] >= 4 else 'REJECTED'
        print(f"📝 Phase 3 proposal generated: {path.name} [{status}]")
        return
    
    if args.propose:
        print("Phase 3 Proposal Generator")
        print("=" * 40)
        version = input("Notebook version (v1/v2/v3/v4): ").strip()
        if not check_phase2_complete(version):
            print(f"🔒 Phase 3 gate LOCKED for {version} — Phase 2 not complete yet")
            sys.exit(1)
        iteration_id = input("Iteration ID (e.g., 01, 02): ").strip()
        hypothesis = input("Hypothesis: ").strip()
        justification = input("Justification: ").strip()
        score = int(input("Justification score (1-10): ").strip())
        proposed_by = input("Proposed by (shael/belam/architect/critic/builder): ").strip() or 'agent'
        gpu_min = int(input("Estimated GPU minutes [30]: ").strip() or '30')
        path = generate_phase3_proposal(version, iteration_id, hypothesis, justification, 
                                         score, proposed_by, gpu_min)
        status = 'APPROVED' if score >= 7 else 'PENDING REVIEW' if score >= 4 else 'REJECTED'
        print(f"\n📝 Proposal generated: {path.name} [{status}]")
        return
    
    if args.list:
        pending = list(OUTPUT_DIR.glob('*.md'))
        pending = [p for p in pending if p.name != '.last_analysis']
        if pending:
            for p in sorted(pending):
                content = p.read_text()
                status = 'pending' if 'status: pending_review' in content else 'processed'
                print(f"  {'🔄' if status == 'pending' else '✅'} {p.name} [{status}]")
        else:
            print("  No analysis briefs found.")
        return
    
    notebooks_to_analyze = []
    
    if args.notebook:
        key = args.notebook.lower()
        if key in NOTEBOOK_ALIASES:
            notebooks_to_analyze.append((key, NOTEBOOK_ALIASES[key]))
        else:
            print(f"Unknown notebook: {key}. Options: {', '.join(NOTEBOOK_ALIASES.keys())}")
            sys.exit(1)
    
    elif args.detect:
        changes = detect_changes()
        
        if not any(changes.values()):
            if not args.quiet:
                print("No new changes detected.")
            return
        
        # Map changed files back to notebook keys
        for nb_path in changes['notebooks']:
            nb_name = os.path.basename(nb_path)
            for key, name in NOTEBOOK_ALIASES.items():
                if name == nb_name:
                    notebooks_to_analyze.append((key, name))
                    break
        
        # Also check for new results without corresponding notebook changes
        for result_path in changes['results']:
            for key in NOTEBOOK_ALIASES:
                if key in result_path and not any(k == key for k, _ in notebooks_to_analyze):
                    notebooks_to_analyze.append((key, NOTEBOOK_ALIASES[key]))
    
    else:
        parser.print_help()
        return
    
    if not notebooks_to_analyze:
        if not args.quiet:
            print("No notebooks to analyze.")
        return
    
    generated = []
    for key, name in notebooks_to_analyze:
        if not args.quiet:
            print(f"Analyzing {key} ({name})...")
        
        diff = get_notebook_diff(name)
        related = find_related_files(key)
        
        if not diff and not related:
            if not args.quiet:
                print(f"  No diff or related files found for {key}, skipping.")
            continue
        
        brief = generate_analysis_brief(key, name, diff, related)
        
        output_path = OUTPUT_DIR / f'brief_{key}_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.md'
        output_path.write_text(brief)
        generated.append(output_path)
        
        if not args.quiet:
            print(f"  → {output_path.relative_to(FINANCE_DIR)}")
    
    # Update marker
    current_head = git_run('rev-parse', 'HEAD')
    if current_head:
        (OUTPUT_DIR / '.last_analysis').write_text(current_head)
    
    if generated:
        print(f"\n{len(generated)} analysis brief(s) ready for agent review.")
        print("Agent will extract lessons, update trackers, and process findings.")
    

if __name__ == '__main__':
    main()
