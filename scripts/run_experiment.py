#!/usr/bin/env python3
"""
Pipeline-aware experiment runner.

Wraps notebook execution as a pipeline stage. Extracts experiment code from
the pipeline's notebook, runs it locally, and self-reports via pipeline_update.

Features:
  - Parametric: reads notebook path from pipeline frontmatter
  - Auto-updates pipeline stage (start → running → complete/error)
  - Error recovery: spawns builder agent to fix errors, retries
  - Background-friendly: designed to be launched by orchestrator

Usage:
    python3 scripts/run_experiment.py <version>                    # Run pipeline's experiments
    python3 scripts/run_experiment.py <version> --dry-run          # Quick validation
    python3 scripts/run_experiment.py <version> --workers 2        # Override workers
    python3 scripts/run_experiment.py <version> --max-retries 3    # Error recovery attempts
    python3 scripts/run_experiment.py <version> --no-recovery      # Skip builder agent on errors
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
SCRIPTS = WORKSPACE / 'scripts'
BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
PIPELINES_DIR = WORKSPACE / 'pipelines'
ML_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance'
RESULTS_BASE = ML_DIR / 'notebooks' / 'local_results'

PIPELINE_UPDATE = SCRIPTS / 'pipeline_update.py'
PIPELINE_ORCHESTRATE = SCRIPTS / 'pipeline_orchestrate.py'

# Builder agent recovery timeout (seconds)
BUILDER_RECOVERY_TIMEOUT = 300  # 5 minutes per fix attempt

# PID file for process tracking
PID_DIR = BUILDS_DIR


def load_pipeline_frontmatter(version: str) -> dict:
    """Load frontmatter from pipeline primitive."""
    path = PIPELINES_DIR / f'{version}.md'
    if not path.exists():
        return {}
    content = path.read_text()
    if not content.startswith('---'):
        return {}
    end = content.index('---', 3)
    result = {}
    for line in content[3:end].strip().split('\n'):
        if ':' in line and not line.startswith(' '):
            key, _, val = line.partition(':')
            val = val.strip().strip('"').strip("'")
            if val.startswith('[') and val.endswith(']'):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(',')]
            result[key.strip()] = val
    return result


def load_state_json(version: str) -> dict:
    """Load pipeline state."""
    state_file = BUILDS_DIR / f'{version}_state.json'
    if state_file.exists():
        return json.load(open(state_file))
    return {}


def run_pipeline_update(args: list) -> tuple:
    """Call pipeline_update.py."""
    cmd = [sys.executable, str(PIPELINE_UPDATE)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0, result.stdout + result.stderr


def run_orchestrate(args: list, timeout: int = 700) -> tuple:
    """Call pipeline_orchestrate.py."""
    cmd = [sys.executable, str(PIPELINE_ORCHESTRATE)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode == 0, result.stdout + result.stderr


def write_pid_file(version: str) -> Path:
    """Write PID file for process tracking."""
    pid_file = PID_DIR / f'{version}_experiment.pid'
    pid_file.write_text(json.dumps({
        'pid': os.getpid(),
        'version': version,
        'started': datetime.now(timezone.utc).isoformat(),
    }))
    return pid_file


def remove_pid_file(version: str):
    """Remove PID file."""
    pid_file = PID_DIR / f'{version}_experiment.pid'
    if pid_file.exists():
        pid_file.unlink()


def get_notebook_path(version: str, frontmatter: dict) -> Path:
    """Resolve the notebook path for this pipeline."""
    # Check frontmatter first
    nb = frontmatter.get('output_notebook', '')
    if nb:
        path = WORKSPACE / nb
        if path.exists():
            return path

    # Convention fallback
    path = ML_DIR / 'notebooks' / f'snn_crypto_predictor_{version}.ipynb'
    if path.exists():
        return path

    return None


def get_results_dir(version: str) -> Path:
    """Get/create results directory for this pipeline."""
    results_dir = RESULTS_BASE / version
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def extract_and_run_notebook(notebook_path: Path, results_dir: Path, version: str,
                              dry_run: bool = False, workers: int = None,
                              resume: bool = False) -> dict:
    """
    Execute a notebook's experiments using papermill or nbconvert,
    falling back to the existing run_local.py pattern.

    Returns dict with: success, errors, results_path, elapsed, error_details
    """
    start_time = time.time()
    log_file = results_dir / 'run.log'

    # Strategy: Use jupyter nbconvert --execute for full notebook execution
    # This runs ALL cells including data loading, model defs, experiments, analysis
    env = os.environ.copy()
    env['RESULTS_DIR'] = str(results_dir)
    env['PIPELINE_VERSION'] = version

    # Check if papermill is available (preferred — parameterizable)
    papermill_available = False
    try:
        subprocess.run([sys.executable, '-m', 'papermill', '--version'],
                      capture_output=True, timeout=10)
        papermill_available = True
    except Exception:
        pass

    # Check if nbconvert is available
    nbconvert_available = False
    try:
        subprocess.run([sys.executable, '-m', 'nbconvert', '--version'],
                      capture_output=True, timeout=10)
        nbconvert_available = True
    except Exception:
        pass

    output_notebook = results_dir / f'{notebook_path.stem}_executed.ipynb'

    if papermill_available:
        cmd = [
            sys.executable, '-m', 'papermill',
            str(notebook_path), str(output_notebook),
            '-p', 'results_dir', str(results_dir),
            '-p', 'pipeline_version', version,
            '--log-output', '--log-level', 'INFO',
        ]
        if dry_run:
            cmd.extend(['-p', 'dry_run', 'True'])
    elif nbconvert_available:
        cmd = [
            sys.executable, '-m', 'nbconvert',
            '--to', 'notebook', '--execute',
            '--output', str(output_notebook),
            '--ExecutePreprocessor.timeout=-1',
            f'--ExecutePreprocessor.kernel_name=python3',
            str(notebook_path),
        ]
    else:
        # Fallback: check if run_local.py exists and can handle this pipeline
        run_local = ML_DIR / 'scripts' / 'run_local.py'
        if run_local.exists():
            cmd = [sys.executable, str(run_local)]
            if dry_run:
                cmd.append('--dry-run')
            if workers:
                cmd.extend(['--workers', str(workers)])
            if resume:
                cmd.append('--resume')
            # Override results dir via env
            env['RESULTS_DIR_OVERRIDE'] = str(results_dir)
        else:
            return {
                'success': False,
                'errors': ['No execution method available (papermill/nbconvert/run_local.py)'],
                'elapsed': 0,
            }

    print(f"  📋 Command: {' '.join(cmd[:5])}...")
    print(f"  📂 Results: {results_dir}")

    # Execute with output streaming to log
    with open(log_file, 'w') as log:
        log.write(f"Pipeline: {version}\n")
        log.write(f"Notebook: {notebook_path}\n")
        log.write(f"Started: {datetime.now(timezone.utc).isoformat()}\n")
        log.write(f"Command: {' '.join(cmd)}\n")
        log.write(f"{'='*60}\n\n")
        log.flush()

        try:
            proc = subprocess.Popen(
                cmd, stdout=log, stderr=subprocess.STDOUT,
                env=env, cwd=str(ML_DIR),
            )
            proc.wait()  # Block until complete
            elapsed = time.time() - start_time

            log.write(f"\n{'='*60}\n")
            log.write(f"Completed: {datetime.now(timezone.utc).isoformat()}\n")
            log.write(f"Exit code: {proc.returncode}\n")
            log.write(f"Elapsed: {elapsed/60:.1f} minutes\n")

            if proc.returncode != 0:
                # Read last 50 lines for error context
                log.flush()
                error_lines = Path(log_file).read_text().split('\n')[-50:]
                return {
                    'success': False,
                    'errors': [f'Process exited with code {proc.returncode}'],
                    'error_details': '\n'.join(error_lines),
                    'elapsed': elapsed,
                    'log_file': str(log_file),
                }

            return {
                'success': True,
                'errors': [],
                'elapsed': elapsed,
                'results_dir': str(results_dir),
                'log_file': str(log_file),
                'output_notebook': str(output_notebook) if output_notebook.exists() else None,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            log.write(f"\nEXCEPTION: {e}\n{traceback.format_exc()}\n")
            return {
                'success': False,
                'errors': [str(e)],
                'error_details': traceback.format_exc(),
                'elapsed': elapsed,
                'log_file': str(log_file),
            }


def attempt_builder_recovery(version: str, error_details: str, notebook_path: Path,
                              attempt: int) -> bool:
    """
    Spawn builder agent to fix experiment errors.

    Creates a bug report file, wakes the builder with fix instructions,
    waits for completion, then returns True if fix was applied.
    """
    print(f"\n  🔧 Builder recovery attempt {attempt}...")

    # Write error report for builder
    bug_report = BUILDS_DIR / f'{version}_experiment_error.md'
    bug_report.write_text(f"""---
type: experiment_error
version: {version}
attempt: {attempt}
timestamp: {datetime.now(timezone.utc).isoformat()}
---

# Experiment Execution Error — {version}

## Error Details
```
{error_details[-3000:]}
```

## Notebook
`{notebook_path}`

## Instructions
1. Read the error traceback above
2. Open the notebook and fix the bug
3. The error is likely in model definition, data pipeline, or experiment runner code
4. Do NOT change experiment configurations or hyperparameters — only fix bugs
5. After fixing, commit changes with message: "fix: experiment error {version} attempt {attempt}"
6. Complete via: `python3 scripts/pipeline_orchestrate.py {version} complete experiment_bug_fix --agent builder --notes "Fixed: <description>"`

## Constraints
- Fix bugs only — do not alter experiment design
- If the error is in shared infrastructure (data loading, encodings), fix it carefully
- If you cannot determine the fix, block with a clear description
""")

    # Wake builder via orchestrator
    try:
        handoff_msg = (
            f"🔧 EXPERIMENT BUG FIX REQUEST — {version}\n\n"
            f"The local experiment runner hit an error on attempt {attempt}.\n\n"
            f"Read the full error report: pipeline_builds/{version}_experiment_error.md\n"
            f"Notebook: {notebook_path.relative_to(WORKSPACE)}\n\n"
            f"Fix the bug, commit, and complete via orchestrator.\n"
            f"Do NOT change experiment design — only fix runtime bugs."
        )

        # Use sessions_send via openclaw CLI
        result = subprocess.run(
            ['openclaw', 'gateway', 'sessions', 'send',
             '--agent', 'builder', '--session', 'main',
             '--message', handoff_msg,
             '--timeout', str(BUILDER_RECOVERY_TIMEOUT)],
            capture_output=True, text=True, timeout=BUILDER_RECOVERY_TIMEOUT + 60,
        )

        if result.returncode == 0:
            print(f"  ✅ Builder responded")
            # Check if builder committed a fix
            git_check = subprocess.run(
                ['git', 'log', '--oneline', '-1', '--since=5 minutes ago'],
                capture_output=True, text=True, cwd=str(ML_DIR),
            )
            if 'fix:' in git_check.stdout.lower() or 'experiment' in git_check.stdout.lower():
                print(f"  ✅ Builder committed a fix: {git_check.stdout.strip()}")
                return True
            else:
                print(f"  ⚠️  Builder responded but no fix commit detected")
                return True  # Trust the builder, retry anyway
        else:
            print(f"  ❌ Builder wake failed: {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ⏱️  Builder timed out after {BUILDER_RECOVERY_TIMEOUT}s")
        return False
    except Exception as e:
        print(f"  ❌ Builder recovery failed: {e}")
        return False


def write_results_summary(version: str, results_dir: Path, run_result: dict):
    """Write experiment results summary for Phase 2 consumption."""
    summary_path = BUILDS_DIR / f'{version}_experiment_results.md'

    # Try to read the log for the results table
    log_file = results_dir / 'run.log'
    log_content = ''
    if log_file.exists():
        log_content = log_file.read_text()

    # Extract the POOLED RESULTS section if present
    pooled_section = ''
    if 'POOLED RESULTS' in log_content:
        start = log_content.index('POOLED RESULTS')
        # Find the end (next section or EOF)
        lines = log_content[start:].split('\n')
        pooled_lines = []
        for i, line in enumerate(lines):
            if i > 2 and line.startswith('==='):
                break
            pooled_lines.append(line)
        pooled_section = '\n'.join(pooled_lines)

    # List result files
    result_files = sorted(results_dir.glob('*'))
    file_list = '\n'.join(f'- `{f.name}` ({f.stat().st_size / 1024:.1f} KB)' for f in result_files)

    summary_path.write_text(f"""---
type: experiment_results
version: {version}
timestamp: {datetime.now(timezone.utc).isoformat()}
elapsed_minutes: {run_result.get('elapsed', 0) / 60:.1f}
success: {run_result.get('success', False)}
errors: {len(run_result.get('errors', []))}
---

# Experiment Results — {version}

## Run Summary
- **Status:** {'✅ Complete' if run_result.get('success') else '❌ Failed'}
- **Duration:** {run_result.get('elapsed', 0) / 60:.1f} minutes
- **Results dir:** `{results_dir}`
- **Errors:** {len(run_result.get('errors', []))}

## Results
```
{pooled_section}
```

## Output Files
{file_list}

## Plots
{'See accuracy_summary.png, learning curves, and spike rate plots in results dir.' if (results_dir / 'accuracy_summary.png').exists() else 'No plots generated.'}

## For Phase 2 Analysis
The Phase 2 architect should:
1. Review the pooled results table above
2. Examine the plots in `{results_dir.relative_to(WORKSPACE)}/`
3. Load the pickle files for deeper analysis if needed
4. Design the Phase 2 analysis notebook sections accordingly
""")
    return summary_path


def send_notification(version: str, title: str, body: str):
    """Send Telegram notification about experiment status."""
    try:
        from pipeline_update import send_telegram_notification
        send_telegram_notification(version, title, body)
    except Exception:
        print(f"  ⚠️  Could not send notification: {title}")


def main():
    parser = argparse.ArgumentParser(description='Pipeline-aware experiment runner')
    parser.add_argument('version', help='Pipeline version to run experiments for')
    parser.add_argument('--dry-run', action='store_true', help='Quick validation run')
    parser.add_argument('--workers', type=int, default=None, help='Override worker count')
    parser.add_argument('--max-retries', type=int, default=2, help='Max builder recovery attempts')
    parser.add_argument('--no-recovery', action='store_true', help='Skip builder agent on errors')
    parser.add_argument('--resume', action='store_true', help='Resume from previous partial run')
    args = parser.parse_args()

    version = args.version
    print(f"\n{'═' * 70}")
    print(f"  🧪 EXPERIMENT RUNNER — {version}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'═' * 70}\n")

    # Load pipeline info
    fm = load_pipeline_frontmatter(version)
    if not fm:
        print(f"❌ Pipeline not found: {version}")
        sys.exit(1)

    # Verify pipeline is at phase1_complete
    state = load_state_json(version)
    pending = state.get('pending_action', '')
    status = fm.get('status', '')
    if status not in ('phase1_complete', 'experiment_running') and \
       pending not in ('phase1_complete', 'local_experiment_running', 'local_experiment_complete'):
        print(f"⚠️  Pipeline {version} is at status={status}, pending={pending}")
        print(f"   Expected phase1_complete — proceeding anyway (manual override)")

    # Get notebook path
    notebook_path = get_notebook_path(version, fm)
    if not notebook_path:
        print(f"❌ No notebook found for {version}")
        print(f"   Checked: output_notebook={fm.get('output_notebook', 'N/A')}")
        sys.exit(1)

    print(f"  📓 Notebook: {notebook_path.relative_to(WORKSPACE)}")

    # Set up results directory
    results_dir = get_results_dir(version)
    print(f"  📂 Results: {results_dir.relative_to(WORKSPACE)}")

    # Write PID file for tracking
    pid_file = write_pid_file(version)
    print(f"  🆔 PID: {os.getpid()}")

    # Update pipeline stage: start running
    print(f"\n  📊 Updating pipeline stage → local_experiment_running")
    run_pipeline_update([
        version, 'start', 'local_experiment_running',
        '--agent', 'system',
        '--notes', f'Local experiment run started (PID: {os.getpid()})'
    ])

    # Run experiments with retry loop
    attempt = 0
    max_attempts = args.max_retries + 1
    run_result = None

    while attempt < max_attempts:
        attempt += 1
        print(f"\n{'─' * 50}")
        print(f"  🔬 Execution attempt {attempt}/{max_attempts}")
        print(f"{'─' * 50}")

        run_result = extract_and_run_notebook(
            notebook_path, results_dir, version,
            dry_run=args.dry_run,
            workers=args.workers,
            resume=args.resume or (attempt > 1),  # Auto-resume on retries
        )

        if run_result['success']:
            print(f"\n  ✅ Experiments completed in {run_result['elapsed']/60:.1f} minutes")
            break

        print(f"\n  ❌ Execution failed: {run_result['errors']}")

        # Attempt builder recovery if not last attempt and recovery enabled
        if attempt < max_attempts and not args.no_recovery:
            error_details = run_result.get('error_details', '\n'.join(run_result.get('errors', [])))
            recovered = attempt_builder_recovery(version, error_details, notebook_path, attempt)
            if not recovered:
                print(f"  ⚠️  Builder could not fix — stopping retries")
                break
        else:
            if attempt >= max_attempts:
                print(f"  ⚠️  Max retries ({args.max_retries}) exhausted")

    # Write results summary
    summary_path = write_results_summary(version, results_dir, run_result)
    print(f"\n  📝 Results summary: {summary_path.relative_to(WORKSPACE)}")

    # Auto-run data analysis prep if experiments succeeded
    if run_result and run_result['success']:
        print(f"\n  📊 Running analysis data prep...")
        try:
            analyze_cmd = [
                sys.executable, str(SCRIPTS / 'analyze_local_results.py'),
                version, '--extra-plots',
            ]
            analyze_result = subprocess.run(
                analyze_cmd, capture_output=True, text=True,
                cwd=str(WORKSPACE), timeout=300,
            )
            print(analyze_result.stdout)
            if analyze_result.returncode != 0:
                print(f"  ⚠️  Analysis prep had warnings: {analyze_result.stderr[:200]}")
            else:
                print(f"  ✅ Analysis data prep complete")
        except Exception as e:
            print(f"  ⚠️  Analysis prep failed (non-fatal): {e}")

    # Update pipeline stage
    if run_result and run_result['success']:
        # Complete the stage — triggers transition to local_experiment_complete
        print(f"\n  📊 Completing stage → local_experiment_complete")
        run_pipeline_update([
            version, 'complete', 'local_experiment_running',
            '--agent', 'system',
            '--notes', f'Experiments complete. {run_result["elapsed"]/60:.1f}min, results at {results_dir.relative_to(WORKSPACE)}'
        ])

        send_notification(version,
            f"✅ Experiments complete — {version}",
            f"Local run finished in {run_result['elapsed']/60:.1f}min. "
            f"Results at <code>{results_dir.relative_to(WORKSPACE)}</code>")

    else:
        # Failed — notify but don't transition (leave at running for manual intervention)
        errors_summary = '; '.join(run_result.get('errors', ['Unknown error']))[:200]
        run_pipeline_update([
            version, 'start', 'local_experiment_running',
            '--agent', 'system',
            '--notes', f'EXPERIMENT FAILED after {attempt} attempts: {errors_summary}'
        ])

        send_notification(version,
            f"❌ Experiment run FAILED — {version}",
            f"Failed after {attempt} attempt(s). "
            f"Error: <code>{errors_summary[:200]}</code>\n"
            f"Manual intervention needed. Check: <code>{results_dir}/run.log</code>")

    # Cleanup
    remove_pid_file(version)

    print(f"\n{'═' * 70}")
    print(f"  {'✅ SUCCESS' if run_result and run_result['success'] else '❌ FAILED'} — {version}")
    print(f"{'═' * 70}\n")

    sys.exit(0 if run_result and run_result['success'] else 1)


if __name__ == '__main__':
    main()
