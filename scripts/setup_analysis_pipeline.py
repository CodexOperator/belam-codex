#!/usr/bin/env python3
"""
Analysis Pipeline Setup

Validates pkl files, generates the design brief from pkl metadata, creates
the pipeline primitive, and optionally kicks off the architect agent.

Usage:
    python3 scripts/setup_analysis_pipeline.py --pkl-dir notebooks/snn_crypto_predictor_v4_pkl/ \\
        --version v4-analysis --source-version v4

    python3 scripts/setup_analysis_pipeline.py \\
        --pkl-dir notebooks/snn_crypto_predictor_v4_pkl/ \\
        --version v4-analysis --source-version v4 \\
        --kickoff

    python3 scripts/setup_analysis_pipeline.py --verify v4-analysis
"""

import argparse
import json
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
OPENCLAW_DIR = HOME / '.openclaw'
WORKSPACE = OPENCLAW_DIR / 'workspace'
FINANCE_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance'
BUILDS_DIR = FINANCE_DIR / 'research' / 'pipeline_builds'
NOTEBOOKS_DIR = FINANCE_DIR / 'notebooks'
AGENTS = ['architect', 'critic', 'builder']

SHARED_DIRS = [
    'skills', 'templates', 'lessons', 'tasks', 'decisions',
    'scripts', 'pipelines', 'runbooks',
]

# Expected pkl keys that indicate valid SNN result data
EXPECTED_RESULT_KEYS = {
    'accuracy', 'acc', 'val_acc', 'test_acc',
    'sharpe', 'sharpe_ratio',
    'results', 'experiments', 'records',
    'fold_results', 'metrics',
    'experiment_id', 'exp_id', 'name',
}


def ok(msg):
    print(f"  ✅ {msg}")

def warn(msg):
    print(f"  ⚠️  {msg}")

def fail(msg):
    print(f"  ❌ {msg}")

def info(msg):
    print(f"  ℹ️  {msg}")


def check_gateway():
    """Verify gateway is running."""
    print("\n🔧 Checking gateway...")
    try:
        import urllib.request
        resp = urllib.request.urlopen('http://127.0.0.1:18789/health', timeout=5)
        data = json.loads(resp.read())
        if data.get('ok'):
            ok("Gateway running and healthy")
            return True
    except Exception:
        pass
    warn("Gateway not reachable at 127.0.0.1:18789 — agent kickoff will not work")
    return False


def validate_pkl_files(pkl_dir):
    """Validate pkl files exist and contain expected data structure."""
    print(f"\n📂 Validating pkl files in: {pkl_dir}")

    pkl_path = WORKSPACE / pkl_dir if not Path(pkl_dir).is_absolute() else Path(pkl_dir)

    if not pkl_path.exists():
        fail(f"Directory not found: {pkl_path}")
        return None, []

    pkl_files = list(pkl_path.glob('*.pkl'))
    if not pkl_files:
        pkl_files = list(pkl_path.rglob('*.pkl'))

    if not pkl_files:
        fail(f"No .pkl files found in {pkl_path}")
        return None, []

    ok(f"Found {len(pkl_files)} pkl file(s)")

    validated = []
    issues = []
    all_fields = set()

    for pkl_file in sorted(pkl_files):
        size_kb = pkl_file.stat().st_size / 1024
        try:
            with open(pkl_file, 'rb') as f:
                data = pickle.load(f)

            file_info = {
                'path': pkl_file,
                'name': pkl_file.name,
                'size_kb': round(size_kb, 1),
                'valid': False,
                'fields': [],
                'record_count': 0,
                'type': type(data).__name__,
            }

            if isinstance(data, dict):
                file_info['fields'] = list(data.keys())
                all_fields.update(data.keys())
                # Check for any expected keys
                found_expected = EXPECTED_RESULT_KEYS.intersection(set(data.keys()))
                if found_expected:
                    file_info['valid'] = True
                    # Try to count records
                    for key in ('results', 'experiments', 'records'):
                        if key in data and isinstance(data[key], (list, dict)):
                            file_info['record_count'] = len(data[key])
                            break
                    ok(f"{pkl_file.name} ({size_kb:.1f} KB) — keys: {list(data.keys())[:8]}")
                else:
                    file_info['valid'] = True  # Still valid, just different structure
                    warn(f"{pkl_file.name} — no standard result keys found. Keys: {list(data.keys())[:8]}")

            elif isinstance(data, list):
                file_info['record_count'] = len(data)
                file_info['valid'] = True
                if data and isinstance(data[0], dict):
                    file_info['fields'] = list(data[0].keys())
                    all_fields.update(data[0].keys())
                    found_expected = EXPECTED_RESULT_KEYS.intersection(set(data[0].keys()))
                    ok(f"{pkl_file.name} ({size_kb:.1f} KB) — {len(data)} records, keys: {list(data[0].keys())[:8]}")
                else:
                    ok(f"{pkl_file.name} ({size_kb:.1f} KB) — list of {type(data[0]).__name__ if data else 'empty'}, {len(data)} items")
            else:
                file_info['valid'] = True
                warn(f"{pkl_file.name} — unusual type: {type(data).__name__}")

            validated.append(file_info)

        except Exception as e:
            fail(f"{pkl_file.name} — failed to load: {e}")
            issues.append(f"{pkl_file.name}: {e}")

    if issues:
        print(f"\n  ⚠️  {len(issues)} file(s) had errors:")
        for issue in issues:
            print(f"     • {issue}")

    valid_count = sum(1 for v in validated if v['valid'])
    info(f"{valid_count}/{len(validated)} files validated successfully")
    info(f"All detected fields: {', '.join(sorted(all_fields)[:30])}")

    return pkl_path, validated


def generate_design_brief(version, source_version, description, pkl_path, validated_files):
    """Generate a design brief from pkl metadata."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    total_records = sum(v.get('record_count', 0) for v in validated_files)
    all_fields = set()
    for v in validated_files:
        all_fields.update(v.get('fields', []))

    # Build file inventory table
    rows = []
    for v in validated_files:
        status = '✅' if v['valid'] else '❌'
        count = v['record_count'] if v['record_count'] > 0 else '?'
        rows.append(
            f"| {status} | {v['name']:<45} | {v['size_kb']:>8} KB | {v['type']:<10} | {count:<10} |"
        )

    file_table = '\n'.join(rows) if rows else '| ❌ | (no valid pkl files) | — | — | — |'
    fields_str = ', '.join(f'`{k}`' for k in sorted(all_fields)[:25])
    if len(all_fields) > 25:
        fields_str += f' ... (+{len(all_fields) - 25} more)'

    brief = f"""# Analysis Design Brief: {version}
_Auto-generated by setup_analysis_pipeline.py on {now}_

## Overview
- **Analysis Version:** `{version}`
- **Source Experiment:** `{source_version}`
- **Description:** {description}
- **Pkl Source:** `{pkl_path}`
- **Pkl Files:** {len(validated_files)} files
- **Estimated Records:** {total_records if total_records > 0 else 'auto-detection unavailable — check manually'}

## File Inventory

| Valid | File | Size | Type | Records |
|-------|------|------|------|---------|
{file_table}

## Detected Fields Across All Files
{fields_str if fields_str else '_(could not detect — inspect pkl files manually)_'}

## Research Questions for Architect

Design the analysis notebook to systematically address:

### Primary Questions
1. **Performance Distribution** — Distribution of accuracy / abstention-accuracy / Sharpe across all experiments
2. **Top Configurations** — Which architecture × encoding × output scheme combinations win?
3. **Scale Effects** — How does performance scale with network size?
4. **Encoding Sensitivity** — Which encoding (rate, delta, equilibrium) shows strongest signal?
5. **Fold Stability** — How consistent is performance across walk-forward folds?

### Secondary Questions
6. **Failure Modes** — What characterizes bottom-performing experiments?
7. **Cross-Phase Comparison** — If source has multiple phases, how do they compare?
8. **Statistical Significance** — Which differences survive Bonferroni correction?
9. **Interaction Effects** — Are there encoding × scale × output interactions?
10. **Anomalies** — Any outlier experiments that deserve special attention?

## Notebook Output
- **Notebook:** `snn_applied_finance/notebooks/crypto_{source_version}_analysis.ipynb`
- **Upload:** Colab upload (zip or individual pkl files — notebook handles both)

## Architect Instructions
1. Read `research/ANALYSIS_AGENT_ROLES.md`
2. **Read skill at `~/.openclaw/workspace/skills/quant-workflow/SKILL.md` before designing**
3. Design the full notebook structure (Sections 0-5 for Phase 1, Section 6+ for Phase 2)
4. Specify each statistical test with: test name, H0, expected outcome, correction method
5. Specify each visualization with: chart type, axes, what pattern it reveals
6. Write complete design to `research/pipeline_builds/{version}_architect_analysis_design.md`
7. Run: `python3 scripts/pipeline_update.py {version} complete analysis_architect_design "Design complete" architect`
8. Ping Critic via `sessions_send` (timeoutSeconds: 0)
9. Post update to Telegram group -5243763228
"""

    return brief


def ensure_symlinks():
    """Create symlinks from shared workspace to agent workspaces."""
    print("\n🔗 Checking agent workspace symlinks...")
    for agent in AGENTS:
        ws = OPENCLAW_DIR / f'workspace-{agent}'
        if not ws.exists():
            continue

        for dirname in SHARED_DIRS:
            src = WORKSPACE / dirname
            dst = ws / dirname
            if not src.exists():
                continue
            if dst.exists() or dst.is_symlink():
                continue
            try:
                dst.symlink_to(src)
                ok(f"Linked {dirname} → workspace-{agent}")
            except Exception as e:
                warn(f"Could not link {dirname} → workspace-{agent}: {e}")

        snn_dst = ws / 'machinelearning'
        snn_src = WORKSPACE / 'machinelearning'
        if snn_src.exists() and not snn_dst.exists() and not snn_dst.is_symlink():
            try:
                snn_dst.symlink_to(snn_src)
                ok(f"Linked machinelearning → workspace-{agent}")
            except Exception as e:
                warn(f"Could not link machinelearning → workspace-{agent}: {e}")

    ok("Symlinks verified")


def check_tool_permissions():
    """Verify architect has write/edit access."""
    print("\n🔐 Checking agent tool permissions...")
    config_path = OPENCLAW_DIR / 'openclaw.json'
    if not config_path.exists():
        warn("openclaw.json not found — cannot verify permissions")
        return True

    with open(config_path) as f:
        config = json.load(f)

    issues = []
    for agent_conf in config.get('agents', {}).get('list', []):
        aid = agent_conf.get('id')
        if aid not in ('architect', 'critic'):
            continue
        denied = agent_conf.get('tools', {}).get('deny', [])
        if 'write' in denied or 'edit' in denied:
            issues.append(f"{aid} has tools.deny={denied}")

    if issues:
        for issue in issues:
            fail(issue)
        info("Fix in openclaw.json and restart gateway")
        return False

    ok("Architect and Critic have write/edit access")
    return True


def check_skills():
    """Verify analysis-relevant skills are accessible."""
    print("\n🧠 Checking skills access...")
    workspace_skills = WORKSPACE / 'skills'
    required_skills = ['quant-workflow', 'quant-infrastructure']
    found = []
    missing = []

    for skill in required_skills:
        skill_path = workspace_skills / skill / 'SKILL.md'
        if skill_path.exists():
            found.append(skill)
            ok(f"Skill available: {skill}")
        else:
            missing.append(skill)
            fail(f"Skill missing: {skill} (expected at {skill_path})")

    if missing:
        info("Analysis agents require these skills — add them before launching")
        return False
    return True


def create_pipeline_primitive(version, source_version, description, pkl_dir):
    """Create the analysis pipeline tracking primitive."""
    print("\n📊 Creating pipeline tracking primitive...")
    pipelines_dir = WORKSPACE / 'pipelines'
    pipelines_dir.mkdir(exist_ok=True)

    pf = pipelines_dir / f'{version}.md'
    if pf.exists():
        info(f"Pipeline primitive already exists: {pf.name}")
        return pf

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    content = f"""---
primitive: analysis_pipeline
status: analysis_phase1_design
priority: high
version: {version}
source_version: {source_version}
source_pkl_dir: {pkl_dir}
output_notebook: machinelearning/snn_applied_finance/notebooks/crypto_{source_version}_analysis.ipynb
agents: [architect, critic, builder]
tags: [snn, analysis, {source_version}]
project: snn-applied-finance
started: {now}
---

# Analysis Pipeline: {version.upper()}

## Description
{description}

## Source Data
- **Source Version:** `{source_version}`
- **Pkl Files:** `{pkl_dir}`

## Phase 1: Autonomous Analysis
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | {now} | setup_analysis_pipeline.py | Auto-created from pkl validation |

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

    pf.write_text(content)
    ok(f"Created {pf.relative_to(WORKSPACE)}")

    # Create state JSON
    BUILDS_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        'version': version,
        'pipeline_type': 'analysis',
        'source_version': source_version,
        'source_pkl_dir': str(pkl_dir),
        'status': 'analysis_phase1_design',
        'created': now,
        'pending_action': 'analysis_architect_design',
    }
    state_file = BUILDS_DIR / f'{version}_state.json'
    if not state_file.exists():
        state_file.write_text(json.dumps(state, indent=2))
        ok(f"Created state: {state_file.relative_to(WORKSPACE)}")
    else:
        info(f"State file already exists: {state_file.name}")

    return pf


def verify_existing(version):
    """Verify an existing analysis pipeline setup."""
    print(f"\n🔍 Verifying analysis pipeline setup for {version}...")

    pf = WORKSPACE / 'pipelines' / f'{version}.md'
    if pf.exists():
        ok(f"Pipeline primitive: {pf.name}")
    else:
        fail(f"Pipeline primitive not found: pipelines/{version}.md")

    brief = BUILDS_DIR / f'{version}_design_brief.md'
    if brief.exists():
        ok(f"Design brief: {brief.name}")
    else:
        warn(f"Design brief not found: {brief.name}")

    state = BUILDS_DIR / f'{version}_state.json'
    if state.exists():
        ok(f"State file: {state.name}")
        data = json.loads(state.read_text())
        info(f"  Status: {data.get('status', 'unknown')}")
        info(f"  Pending: {data.get('pending_action', 'none')}")
    else:
        warn(f"State file not found: {state.name}")

    ensure_symlinks()
    check_tool_permissions()
    check_skills()

    print(f"\n✅ Verification complete for {version}")


def main():
    parser = argparse.ArgumentParser(description='Analysis Pipeline Setup')
    parser.add_argument('--pkl-dir', help='Path to pkl result files directory')
    parser.add_argument('--version', '-v', help='Analysis version key (e.g. v4-analysis)')
    parser.add_argument('--source-version', '-s', help='Source experiment version (e.g. v4)',
                        dest='source_version')
    parser.add_argument('--desc', '-d', help='Pipeline description',
                        default='SNN experiment results analysis')
    parser.add_argument('--verify', help='Verify an existing pipeline setup')
    parser.add_argument('--kickoff', '-k', action='store_true',
                        help='Print architect kickoff task after setup')
    args = parser.parse_args()

    if args.verify:
        verify_existing(args.verify)
        return

    if not args.pkl_dir:
        parser.print_help()
        sys.exit(1)
    if not args.version:
        print("❌ --version required")
        sys.exit(1)
    if not args.source_version:
        print("❌ --source-version required (e.g. v4)")
        sys.exit(1)

    print("🔬 Analysis Pipeline Setup")
    print("=" * 50)

    # Step 0: Gateway check
    check_gateway()

    # Step 1: Validate pkl files
    pkl_path, validated = validate_pkl_files(args.pkl_dir)
    if pkl_path is None:
        print("\n⚠️  Continuing without valid pkl files — update design brief manually")
        validated = []

    # Step 2: Ensure symlinks
    ensure_symlinks()

    # Step 3: Check tool permissions
    check_tool_permissions()

    # Step 4: Check skills
    check_skills()

    # Step 5: Create pipeline primitive + state JSON
    pf = create_pipeline_primitive(
        args.version, args.source_version, args.desc, args.pkl_dir
    )

    # Step 6: Generate design brief
    print("\n📝 Generating design brief...")
    brief_content = generate_design_brief(
        args.version, args.source_version, args.desc,
        pkl_path or Path(args.pkl_dir), validated
    )
    brief_file = BUILDS_DIR / f'{args.version}_design_brief.md'
    if not brief_file.exists():
        brief_file.write_text(brief_content)
        ok(f"Design brief: {brief_file.relative_to(WORKSPACE)}")
    else:
        info(f"Design brief already exists: {brief_file.name}")

    print("\n" + "=" * 50)
    print(f"✅ Analysis pipeline setup complete for {args.version}")
    print(f"\nFiles:")
    print(f"  pipelines/{args.version}.md")
    print(f"  research/pipeline_builds/{args.version}_design_brief.md")
    print(f"  research/pipeline_builds/{args.version}_state.json")

    if args.kickoff:
        print(f"\n🚀 Architect kickoff task:")
        print(f"""
  Spawn architect agent with:
  "Read pipelines/{args.version}.md and research/pipeline_builds/{args.version}_design_brief.md.
  Read research/ANALYSIS_AGENT_ROLES.md.
  Read skill at ~/.openclaw/workspace/skills/quant-workflow/SKILL.md.
  Design the analysis notebook for {args.source_version} pkl results.
  Write design to research/pipeline_builds/{args.version}_architect_analysis_design.md.
  Run: python3 scripts/pipeline_update.py {args.version} complete analysis_architect_design 'Design complete' architect"
""")
    else:
        print(f"\nNext: spawn architect agent (see launch_analysis_pipeline.py output for task text)")


if __name__ == '__main__':
    main()
