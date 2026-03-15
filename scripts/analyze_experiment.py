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
    'baseline': 'quant_baseline.ipynb',
    'stock': 'snn_stock_predictor.ipynb',
}


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


def main():
    parser = argparse.ArgumentParser(description='Experiment Analysis Pipeline')
    parser.add_argument('--notebook', '-n', help='Specific notebook key (v1, v2, v3, baseline, stock)')
    parser.add_argument('--detect', '-d', action='store_true', help='Auto-detect changed notebooks')
    parser.add_argument('--quiet', '-q', action='store_true', help='No output unless changes found')
    parser.add_argument('--list', '-l', action='store_true', help='List pending analysis briefs')
    args = parser.parse_args()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
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
