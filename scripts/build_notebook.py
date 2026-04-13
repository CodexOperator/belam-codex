#!/usr/bin/env python3
"""
Notebook Builder Pipeline — Two-Phase Multi-Agent Architecture

Phase 1 (Autonomous):
    Agents create, review, and build the notebook entirely from their own
    knowledge (techniques tracker, prior results, knowledge files).
    No human input — agents work from spec + accumulated research context.
    
    Flow: Spec → Architect designs → Critic reviews design → Builder implements
          → Critic code-reviews → v4_autonomous.ipynb

Phase 2 (Human-in-the-loop):
    Human (Shael) reviews the autonomous output, provides tweaks and feedback.
    Agents rebuild incorporating human input as highest-priority signal.
    
    Flow: Shael reviews → provides feedback → Architect revises → Critic reviews
          → Builder rebuilds → Critic code-reviews → v4_final.ipynb

This mirrors the analysis pipeline philosophy: Shael's tweaks are the
highest-signal data. Phase 1 gives agents their best shot; Phase 2
incorporates the irreplaceable human design intuition.

Usage:
    # Phase 1 — Generate autonomous build from spec:
    python3 scripts/build_notebook.py --spec specs/v4_spec.yaml
    
    # Phase 2 — Incorporate human feedback on autonomous build:
    python3 scripts/build_notebook.py --revise v4 --feedback "path/to/feedback.md"
    
    # List pending builds:
    python3 scripts/build_notebook.py --list
    
    # Check status of a build:
    python3 scripts/build_notebook.py --status v4

The actual multi-round agent flow is orchestrated by Belam:
    Phase 1: Belam reads spec → spawns Architect → sends to Critic → spawns Builder → sends to Critic
    Phase 2: Belam reads Shael's feedback → spawns Architect (revision) → Critic → Builder → Critic
"""

import argparse
import json
import os
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get(
    'WORKSPACE',
    os.path.expanduser('~/.openclaw/workspace')
))
FINANCE_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance'
SPECS_DIR = FINANCE_DIR / 'specs'
NOTEBOOKS_DIR = FINANCE_DIR / 'notebooks'
PIPELINE_DIR = WORKSPACE / 'pipeline_builds'

PIPELINE_STAGES = [
    # Phase 1: Autonomous
    'spec_validated',
    'design_brief_generated', 
    'architect_designed',
    'critic_reviewed_design',
    'builder_implemented',
    'critic_reviewed_code',
    'phase1_complete',           # Autonomous notebook ready for Shael review
    # Phase 2: Human-in-the-loop
    'human_feedback_received',
    'architect_revised',
    'critic_reviewed_revision',
    'builder_rebuilt',
    'critic_reviewed_rebuild',
    'phase2_complete',           # Final notebook incorporating Shael's input
]


def validate_spec(spec_path):
    """Validate a notebook build spec file."""
    with open(spec_path) as f:
        spec = yaml.safe_load(f)
    
    required = ['version', 'name', 'description', 'experiments']
    missing = [k for k in required if k not in spec]
    if missing:
        print(f"ERROR: Spec missing required fields: {missing}")
        return None
    
    for i, exp in enumerate(spec['experiments']):
        exp_required = ['name', 'architecture']
        exp_missing = [k for k in exp_required if k not in exp]
        if exp_missing:
            print(f"ERROR: Experiment {i} missing fields: {exp_missing}")
            return None
    
    return spec


def generate_design_brief(spec, spec_path):
    """Generate a structured design brief for the architect agent."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    version = spec['version']
    
    brief = f"""---
generated: {now}
spec_file: {spec_path}
version: {version}
stage: design_brief_generated
type: notebook_build_brief
---

# Notebook Build Brief: {spec['name']}

## Description
{spec['description']}

## Version
{version}

## Base Notebook
{spec.get('base_notebook', 'snn_crypto_predictor_v3.ipynb')} — inherit data pipeline, walk-forward splits, evaluation utilities, visualization sections.

## Experiments to Implement

"""
    
    for i, exp in enumerate(spec['experiments']):
        brief += f"""### Experiment Group {i+1}: {exp['name']}
"""
        if 'description' in exp:
            brief += f"{exp['description']}\n\n"
        
        arch = exp['architecture']
        brief += f"**Architecture:** {arch.get('type', 'SNN')} — "
        if 'layers' in arch:
            brief += f"Layers: {arch['layers']}\n"
        if 'neurons' in arch:
            brief += f"Total neurons: ~{arch['neurons']}\n"
        if 'hidden_sizes' in arch:
            brief += f"Hidden sizes: {arch['hidden_sizes']}\n"
        
        if 'input_modes' in exp:
            brief += f"**Input modes:** {', '.join(exp['input_modes'])}\n"
        if 'encodings' in exp:
            brief += f"**Encodings:** {', '.join(exp['encodings'])}\n"
        if 'output_scheme' in exp:
            brief += f"**Output scheme:** {exp['output_scheme']}\n"
        if 'notes' in exp:
            brief += f"**Notes:** {exp['notes']}\n"
        brief += "\n"
    
    if 'output_scheme_details' in spec:
        brief += f"""## Output Scheme Details
{spec['output_scheme_details']}

"""
    
    if 'training_config' in spec:
        tc = spec['training_config']
        brief += "## Training Configuration\n"
        for k, v in tc.items():
            brief += f"- **{k}:** {v}\n"
        brief += "\n"
    
    if 'hardware' in spec:
        brief += f"## Target Hardware\n{spec['hardware']}\n\n"
    
    if 'constraints' in spec:
        brief += "## Constraints\n"
        for c in spec['constraints']:
            brief += f"- {c}\n"
        brief += "\n"
    
    if 'prior_learnings' in spec:
        brief += "## Prior Learnings to Incorporate\n"
        for l in spec['prior_learnings']:
            brief += f"- {l}\n"
        brief += "\n"
    
    brief += """## Agent Instructions

### For Architect
Design the notebook structure:
1. Define all model classes (with exact layer sizes, neuron counts)
2. Define encoding/decoding functions for each scheme
3. Define the experiment matrix (all combinations to run)
4. Specify evaluation metrics and success criteria
5. Document the differential output scheme implementation

### For Critic (Design Review)
Review the design for:
1. Statistical hygiene (walk-forward integrity, enough folds, proper baselines)
2. Overfitting risks (model complexity vs data size)
3. Missing controls or baselines
4. Encoding/decoding correctness
5. Output scheme mathematical soundness

### For Builder
Implement the notebook:
1. Inherit proven code from base notebook (data, features, splits, eval)
2. Implement new model classes and encoding functions
3. Build the experiment loop
4. Add all visualizations and summary tables
5. Test on CPU first (small subset), ensure it runs clean

### For Critic (Code Review)
Review the implementation for:
1. Correctness of tensor shapes and alignment
2. Data leakage risks
3. GPU compatibility
4. Proper gradient flow through differential output
5. Memory efficiency for nano networks
"""
    
    return brief


def update_pipeline_state(version, stage, notes=None):
    """Update the pipeline state file for a build."""
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = PIPELINE_DIR / f'{version}_state.json'
    
    state = {}
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
    
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    state['version'] = version
    state['current_stage'] = stage
    state['last_updated'] = now
    
    if 'history' not in state:
        state['history'] = []
    state['history'].append({
        'stage': stage,
        'timestamp': now,
        'notes': notes,
    })
    
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    
    return state


def get_pipeline_status(version):
    """Get current pipeline status for a version."""
    state_file = PIPELINE_DIR / f'{version}_state.json'
    if not state_file.exists():
        return None
    with open(state_file) as f:
        return json.load(f)


def list_builds():
    """List all pipeline builds and their status."""
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    states = list(PIPELINE_DIR.glob('*_state.json'))
    
    if not states:
        print("No builds found.")
        return
    
    for sf in sorted(states):
        with open(sf) as f:
            state = json.load(f)
        stage_idx = PIPELINE_STAGES.index(state['current_stage']) if state['current_stage'] in PIPELINE_STAGES else -1
        progress = f"{stage_idx + 1}/{len(PIPELINE_STAGES)}"
        print(f"  {state['version']:10s} | {state['current_stage']:30s} | {progress} | {state['last_updated']}")


def generate_revision_brief(version, feedback_path=None, feedback_text=None):
    """Generate a revision brief incorporating human feedback for Phase 2."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Read the Phase 1 design
    phase1_design = read_file_safe(PIPELINE_DIR / f'{version}_architect_design.md')
    phase1_critique = read_file_safe(PIPELINE_DIR / f'{version}_critic_design_review.md')
    
    # Read feedback
    feedback = ''
    if feedback_path:
        feedback = Path(feedback_path).read_text()
    elif feedback_text:
        feedback = feedback_text
    
    brief = f"""---
generated: {now}
version: {version}
phase: 2
type: revision_brief
status: pending_review
---

# Phase 2 Revision Brief: {version}

## Human Feedback (HIGHEST PRIORITY)
These are Shael's observations, tweaks, and design decisions after reviewing
the Phase 1 autonomous output. Every item here takes precedence over the
original autonomous design.

{feedback}

## Phase 1 Design (for reference)
The autonomous design that Shael reviewed:

{phase1_design[:10000] if phase1_design else '(design file not found)'}

## Phase 1 Critique (for reference)
The critic's review of the autonomous design:

{phase1_critique[:5000] if phase1_critique else '(critique file not found)'}

## Agent Instructions (Phase 2)

### For Architect (Revision)
1. Read Shael's feedback carefully — this is the highest-signal input
2. Revise the design to incorporate ALL feedback items
3. Flag any feedback that conflicts with statistical hygiene (but implement it unless dangerous)
4. Write revised design to `{version}_architect_design_v2.md`

### For Critic (Revision Review)
1. Verify all human feedback items are addressed
2. Check that revisions don't introduce new issues
3. Lighter review than Phase 1 — focus on the CHANGES

### For Builder (Rebuild)
1. Start from the Phase 1 notebook
2. Apply all design revisions
3. Mark changed sections with comments (# PHASE 2: ...)
4. Output as `snn_crypto_predictor_{version}.ipynb` (replaces Phase 1 version)

### For Critic (Code Review)
1. Diff-focused review — what changed from Phase 1?
2. Verify feedback items are correctly implemented
3. Final sign-off
"""
    
    return brief


def main():
    parser = argparse.ArgumentParser(description='Notebook Builder Pipeline (Two-Phase)')
    parser.add_argument('--spec', '-s', help='Path to spec YAML file (Phase 1)')
    parser.add_argument('--revise', '-r', help='Version to revise (Phase 2)')
    parser.add_argument('--feedback', '-f', help='Path to feedback file for Phase 2')
    parser.add_argument('--feedback-text', help='Inline feedback text for Phase 2')
    parser.add_argument('--list', '-l', action='store_true', help='List all builds')
    parser.add_argument('--status', help='Check status of a specific version')
    parser.add_argument('--validate', '-v', help='Validate a spec file only')
    args = parser.parse_args()
    
    if args.list:
        list_builds()
        return
    
    if args.status:
        status = get_pipeline_status(args.status)
        if status:
            print(f"Version: {status['version']}")
            print(f"Stage: {status['current_stage']}")
            print(f"Updated: {status['last_updated']}")
            print("\nHistory:")
            for h in status['history']:
                print(f"  {h['timestamp']} — {h['stage']}" + (f" ({h['notes']})" if h.get('notes') else ''))
        else:
            print(f"No build found for version: {args.status}")
        return
    
    if args.validate:
        spec = validate_spec(args.validate)
        if spec:
            print(f"✅ Spec valid: {spec['name']} — {len(spec['experiments'])} experiment groups")
        return
    
    if args.revise:
        version = args.revise
        status = get_pipeline_status(version)
        if not status:
            print(f"ERROR: No build found for version '{version}'. Run Phase 1 first.")
            sys.exit(1)
        
        if not args.feedback and not args.feedback_text:
            print("ERROR: Phase 2 requires --feedback <path> or --feedback-text <text>")
            sys.exit(1)
        
        PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
        
        brief = generate_revision_brief(
            version,
            feedback_path=args.feedback,
            feedback_text=args.feedback_text
        )
        brief_path = PIPELINE_DIR / f'{version}_revision_brief.md'
        brief_path.write_text(brief)
        
        update_pipeline_state(version, 'human_feedback_received',
                            notes='Phase 2 initiated with human feedback')
        
        print(f"✅ Phase 2 revision brief generated: {brief_path.relative_to(WORKSPACE)}")
        print(f"\nNext: Belam orchestrates Architect (revision) → Critic → Builder → Critic")
        return
    
    if args.spec:
        spec = validate_spec(args.spec)
        if not spec:
            sys.exit(1)
        
        version = spec['version']
        PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate design brief
        brief = generate_design_brief(spec, args.spec)
        brief_path = PIPELINE_DIR / f'{version}_design_brief.md'
        brief_path.write_text(brief)
        
        update_pipeline_state(version, 'design_brief_generated')
        
        print(f"✅ Spec validated: {spec['name']}")
        print(f"✅ Phase 1 design brief generated: {brief_path.relative_to(WORKSPACE)}")
        print(f"   {len(spec['experiments'])} experiment groups defined")
        print(f"\nPhase 1: Belam orchestrates Architect → Critic → Builder → Critic")
        print(f"Phase 2: After Shael reviews, run --revise {version} --feedback <path>")
        return
    
    parser.print_help()


if __name__ == '__main__':
    main()
