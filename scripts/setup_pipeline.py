#!/usr/bin/env python3
"""
Pipeline Setup Automation

Automates the notebook builder pipeline setup runbook:
  1. Validates spec
  2. Generates design brief
  3. Ensures agent workspace symlinks
  4. Verifies agent tool permissions
  5. Creates pipeline tracking primitive
  6. Verifies global skills access
  7. Optionally kicks off the pipeline

Usage:
    python3 scripts/setup_pipeline.py --spec specs/v4_spec.yaml
    python3 scripts/setup_pipeline.py --spec specs/v5_spec.yaml --kickoff
    python3 scripts/setup_pipeline.py --verify v4
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

HOME = Path.home()
OPENCLAW_DIR = HOME / '.openclaw'
WORKSPACE = OPENCLAW_DIR / 'workspace'
FINANCE_DIR = WORKSPACE / 'SNN_research' / 'machinelearning' / 'snn_applied_finance'
AGENTS = ['architect', 'critic', 'builder']

SHARED_DIRS = [
    'skills', 'templates', 'lessons', 'tasks', 'decisions',
    'scripts', 'pipelines', 'runbooks',
]


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
    fail("Gateway not reachable at 127.0.0.1:18789")
    return False


def validate_spec(spec_path):
    """Validate the spec file."""
    print(f"\n📋 Validating spec: {spec_path}")
    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    required = ['version', 'name', 'description', 'experiments']
    missing = [k for k in required if k not in spec]
    if missing:
        fail(f"Missing required fields: {missing}")
        return None

    n_exp = sum(
        len(e.get('input_modes', ['continuous'])) * len(e.get('encodings', ['rate']))
        for e in spec['experiments']
    )
    ok(f"Spec valid: {spec['name']}")
    info(f"{len(spec['experiments'])} experiment groups, ~{n_exp} total experiments")
    return spec


def generate_design_brief(spec_path):
    """Run build_notebook.py to generate the design brief."""
    print("\n📝 Generating design brief...")
    result = subprocess.run(
        ['python3', str(WORKSPACE / 'scripts' / 'build_notebook.py'), '--spec', str(spec_path)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        for line in result.stdout.strip().split('\n'):
            ok(line.lstrip('✅ '))
        return True
    else:
        fail(f"build_notebook.py failed: {result.stderr}")
        return False


def ensure_symlinks():
    """Create symlinks from shared workspace to agent workspaces."""
    print("\n🔗 Checking agent workspace symlinks...")
    for agent in AGENTS:
        ws = OPENCLAW_DIR / f'workspace-{agent}'
        if not ws.exists():
            warn(f"workspace-{agent} doesn't exist — skipping")
            continue

        for dirname in SHARED_DIRS:
            src = WORKSPACE / dirname
            dst = ws / dirname
            if not src.exists():
                continue
            if dst.exists() or dst.is_symlink():
                continue  # already set up
            dst.symlink_to(src)
            ok(f"Linked {dirname} → workspace-{agent}")

        # SNN_research symlink
        snn_dst = ws / 'SNN_research'
        snn_src = WORKSPACE / 'SNN_research'
        if snn_src.exists() and not snn_dst.exists():
            snn_dst.symlink_to(snn_src)
            ok(f"Linked SNN_research → workspace-{agent}")

    ok("All symlinks verified")


def check_tool_permissions():
    """Verify architect and critic have write/edit access."""
    print("\n🔐 Checking agent tool permissions...")
    config_path = OPENCLAW_DIR / 'openclaw.json'
    if not config_path.exists():
        fail("openclaw.json not found")
        return False

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
    """Verify global skills are accessible."""
    print("\n🧠 Checking skills access...")
    skills_dir = OPENCLAW_DIR / 'skills'
    if not skills_dir.exists():
        warn("~/.openclaw/skills/ doesn't exist")
        return

    skills = [p.name for p in skills_dir.iterdir() if p.is_dir() or p.is_symlink()]
    if skills:
        ok(f"Global skills: {', '.join(sorted(skills))}")
    else:
        warn("No skills found in ~/.openclaw/skills/")


def create_pipeline_primitive(spec):
    """Create the pipeline tracking primitive."""
    print("\n📊 Creating pipeline tracking primitive...")
    version = spec['version']
    name_slug = spec['name'].lower().replace(' ', '-').replace('—', '-')[:50]
    pipeline_dir = WORKSPACE / 'pipelines'
    pipeline_dir.mkdir(exist_ok=True)

    # Check if already exists
    existing = list(pipeline_dir.glob(f'{version}-*.md'))
    if existing:
        info(f"Pipeline primitive already exists: {existing[0].name}")
        return

    # Build experiment summary
    groups = []
    total = 0
    for exp in spec['experiments']:
        n_modes = len(exp.get('input_modes', ['continuous']))
        n_enc = len(exp.get('encodings', ['rate']))
        n = n_modes * n_enc
        total += n
        arch = exp.get('architecture', {})
        groups.append(
            f"| {exp['name'][:30]} | {arch.get('neurons', '?')} | "
            f"{', '.join(exp.get('encodings', ['?']))} | "
            f"{exp.get('output_scheme', '?')} | {n} |"
        )

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    content = f"""---
primitive: pipeline
status: phase1_design
priority: high
version: {version}
spec_file: SNN_research/machinelearning/snn_applied_finance/specs/{version}_spec.yaml
output_notebook: SNN_research/machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_{version}.ipynb
agents: [architect, critic, builder]
tags: [snn, finance, auto-generated]
project: snn-applied-finance
started: {now}
---

# Pipeline: {spec['name']}

## Description
{spec.get('description', '(no description)')}

## Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| spec_created | {now} | setup_pipeline.py | Auto-generated from spec |

## Experiment Matrix
| Group | Neurons | Encodings | Output | Experiments |
|-------|---------|-----------|--------|-------------|
{chr(10).join(groups)}
| **Total** | | | | **{total}** |

## Artifacts
- **Spec:** `snn_applied_finance/specs/{version}_spec.yaml`
- **Design Brief:** `snn_applied_finance/research/pipeline_builds/{version}_design_brief.md`
- **Phase 1 Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_{version}_autonomous.ipynb` (pending)
- **Final Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_{version}.ipynb` (Phase 2)
"""

    out_path = pipeline_dir / f'{version}-{name_slug[:30]}.md'
    out_path.write_text(content)
    ok(f"Created {out_path.relative_to(WORKSPACE)}")


def verify_existing(version):
    """Verify an existing pipeline setup is complete."""
    print(f"\n🔍 Verifying pipeline setup for {version}...")

    # Check spec
    spec_path = FINANCE_DIR / 'specs' / f'{version}_spec.yaml'
    if spec_path.exists():
        ok(f"Spec exists: {spec_path.name}")
    else:
        fail(f"Spec not found: {spec_path}")

    # Check design brief
    brief_path = FINANCE_DIR / 'research' / 'pipeline_builds' / f'{version}_design_brief.md'
    if brief_path.exists():
        ok(f"Design brief exists: {brief_path.name}")
    else:
        warn(f"Design brief not found")

    # Check pipeline primitive
    pipelines = list((WORKSPACE / 'pipelines').glob(f'{version}-*.md'))
    if pipelines:
        ok(f"Pipeline primitive: {pipelines[0].name}")
    else:
        warn("No pipeline primitive found")

    # Check symlinks
    ensure_symlinks()

    # Check permissions
    check_tool_permissions()

    # Check skills
    check_skills()

    print(f"\n✅ Verification complete for {version}")


def main():
    parser = argparse.ArgumentParser(description='Pipeline Setup Automation')
    parser.add_argument('--spec', '-s', help='Path to spec YAML file')
    parser.add_argument('--verify', '-v', help='Verify existing pipeline setup')
    parser.add_argument('--kickoff', '-k', action='store_true',
                        help='Kick off the pipeline after setup')
    args = parser.parse_args()

    if args.verify:
        verify_existing(args.verify)
        return

    if not args.spec:
        parser.print_help()
        return

    print("🚀 Notebook Builder Pipeline Setup")
    print("=" * 50)

    # Step 0: Gateway check
    check_gateway()

    # Step 1: Validate spec
    spec = validate_spec(args.spec)
    if not spec:
        sys.exit(1)

    # Step 2: Generate design brief
    if not generate_design_brief(args.spec):
        sys.exit(1)

    # Step 3: Ensure symlinks
    ensure_symlinks()

    # Step 4: Check permissions
    check_tool_permissions()

    # Step 5: Create pipeline primitive
    create_pipeline_primitive(spec)

    # Step 6: Check skills
    check_skills()

    print("\n" + "=" * 50)
    print(f"✅ Pipeline setup complete for {spec['version']}")
    print(f"\nNext steps:")
    print(f"  1. Shael kicks off in group chat, OR")
    print(f"  2. Belam sends via: sessions_send(label='architect', message='...')")

    if args.kickoff:
        print(f"\n🚀 Kickoff requested — sending to architect agent...")
        # This would use sessions_send via OpenClaw API
        # For now, print the command
        print(f"  TODO: Integrate with OpenClaw sessions_send API")
        print(f"  Manual: message @BelamArchitect in the group chat")


if __name__ == '__main__':
    main()
