#!/usr/bin/env python3
"""
Pipeline-aware experiment runner with builder agent supervision.

Instead of mechanically executing notebooks and reactively fixing errors,
this spawns a builder agent to supervise the entire experiment lifecycle:

  1. Builder reads the notebook and validates it can run
  2. Builder creates a standalone runner script from the notebook
  3. Builder runs experiments, fixing bugs as they occur
  4. Builder creates lesson/decision primitives for significant findings
  5. Builder reports completion with results summary

Features:
  - Proactive error handling via supervised builder agent
  - Automatic primitive creation (lessons, decisions) from findings
  - Pipeline stage auto-updates (start → running → complete/error)
  - Checkpoint-and-resume on builder timeout
  - Fallback to direct execution for simple cases

Usage:
    python3 scripts/run_experiment.py <version>                    # Supervised run
    python3 scripts/run_experiment.py <version> --direct           # Skip builder, run directly
    python3 scripts/run_experiment.py <version> --dry-run          # Quick validation
    python3 scripts/run_experiment.py <version> --max-retries 3    # Builder resume attempts
"""

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
SCRIPTS = WORKSPACE / 'scripts'
BUILDS_DIR = WORKSPACE / 'pipeline_builds'
RESEARCH_BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
PIPELINES_DIR = WORKSPACE / 'pipelines'
ML_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance'
RESULTS_BASE = ML_DIR / 'notebooks' / 'local_results'

PIPELINE_UPDATE = SCRIPTS / 'pipeline_update.py'
PIPELINE_ORCHESTRATE = SCRIPTS / 'pipeline_orchestrate.py'

# Timeouts
BUILDER_TIMEOUT = 600       # 10 minutes per builder session
BUILDER_MAX_RESUMES = 5     # Max checkpoint-and-resume cycles
DIRECT_RUN_TIMEOUT = 14400  # 4 hours for direct execution


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


def run_pipeline_update(args: list) -> tuple:
    """Call pipeline_update.py."""
    cmd = [sys.executable, str(PIPELINE_UPDATE)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0, result.stdout + result.stderr


def get_notebook_path(version: str, frontmatter: dict) -> Path:
    """Resolve the notebook path for this pipeline."""
    nb = frontmatter.get('output_notebook', '')
    if nb:
        path = WORKSPACE / nb
        if path.exists():
            return path
    path = ML_DIR / 'notebooks' / f'crypto_{version}_predictor.ipynb'
    if path.exists():
        return path
    # Legacy fallback
    path = ML_DIR / 'notebooks' / f'snn_crypto_predictor_{version}.ipynb'
    if path.exists():
        return path
    return None


def get_results_dir(version: str) -> Path:
    """Get/create results directory for this pipeline."""
    results_dir = RESULTS_BASE / version
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def write_pid_file(version: str) -> Path:
    """Write PID file for process tracking."""
    pid_file = BUILDS_DIR / f'{version}_experiment.pid'
    pid_file.write_text(json.dumps({
        'pid': os.getpid(),
        'version': version,
        'started': datetime.now(timezone.utc).isoformat(),
    }))
    return pid_file


def remove_pid_file(version: str):
    """Remove PID file."""
    pid_file = BUILDS_DIR / f'{version}_experiment.pid'
    if pid_file.exists():
        pid_file.unlink()


def reset_agent_session(agent: str):
    """Reset agent sessions for clean dispatch."""
    for session_key in [f'agent:{agent}:main']:
        try:
            subprocess.run(
                ['openclaw', 'gateway', 'sessions', 'reset', session_key],
                capture_output=True, text=True, timeout=10,
            )
        except Exception:
            pass


def wake_builder(message: str, timeout: int = BUILDER_TIMEOUT) -> dict:
    """
    Wake builder agent via openclaw agent CLI.
    Returns {success, response, error}.
    """
    cmd = [
        'openclaw', 'agent',
        '--agent', 'builder',
        '--message', message,
        '--timeout', str(timeout),
        '--json',
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 30,
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                status = data.get('status', 'unknown')
                response_text = ''
                payloads = data.get('result', {}).get('payloads', [])
                if payloads:
                    response_text = payloads[0].get('text', '')
                return {
                    'success': status == 'ok',
                    'response': response_text,
                    'error': None,
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'response': result.stdout[:500],
                    'error': 'Failed to parse JSON response',
                }
        else:
            return {
                'success': False,
                'response': '',
                'error': f'Exit code {result.returncode}: {result.stderr[:500]}',
            }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'response': '',
            'error': f'Builder timed out after {timeout}s',
        }
    except Exception as e:
        return {
            'success': False,
            'response': '',
            'error': str(e),
        }


def build_supervisor_task(version: str, notebook_path: Path, results_dir: Path,
                          attempt: int = 1, checkpoint: str = None,
                          dry_run: bool = False, phase: str = None) -> str:
    """
    Build the task message for the supervising builder agent.
    """
    # Read pipeline spec if it exists
    spec_path = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'specs' / f'{version}_spec.yaml'
    spec_info = ""
    if spec_path.exists():
        spec_info = f"\n\n## Spec File\nRead the full experiment spec at: `{spec_path.relative_to(WORKSPACE)}`"

    # Auto-detect phase from pipeline state if not explicitly set
    if phase is None:
        state_file = BUILDS_DIR / f'{version}_state.json'
        if state_file.exists():
            try:
                state = json.load(open(state_file))
                if state.get('status') in ('phase2_complete', 'experiment_running') and \
                   state.get('stages', {}).get('phase2_complete', {}).get('status') == 'complete':
                    phase = '2'
            except Exception:
                pass

    # Check for prior run logs
    prior_log = ""
    log_file = results_dir / 'run.log'
    if log_file.exists() and attempt > 1:
        log_content = log_file.read_text()
        # Get last 100 lines for error context
        last_lines = '\n'.join(log_content.split('\n')[-100:])
        prior_log = f"\n\n## Prior Run Log (last 100 lines)\n```\n{last_lines}\n```"

    checkpoint_ctx = ""
    if checkpoint:
        checkpoint_ctx = f"\n\n## Checkpoint Context\nThis is resume attempt {attempt}. Previous work:\n{checkpoint}"

    dry_run_note = ""
    if dry_run:
        dry_run_note = "\n\n**DRY RUN MODE:** Run only 1-2 experiments with minimal epochs to validate the pipeline works. Don't run the full suite."

    return f"""🧪 SUPERVISED EXPERIMENT RUN — {version}

You are supervising the experiment execution for pipeline `{version}`.

## Your Mission
1. **Read and understand** the notebook at `{notebook_path.relative_to(WORKSPACE)}`
2. **Create a standalone Python runner script** at `{results_dir.relative_to(WORKSPACE)}/run_supervised.py` that extracts and runs all experiments from the notebook
3. **Execute the runner**, fixing any bugs you encounter in the notebook code
4. **Save results** to `{results_dir.relative_to(WORKSPACE)}/`
5. **Create primitives** for significant findings (lessons, decisions)
6. **Report completion** via: `python3 scripts/pipeline_orchestrate.py {version} complete local_experiment_running --agent builder --notes "RESULTS: <summary>"`

## Key Details
- **Notebook:** `{notebook_path.relative_to(WORKSPACE)}`
- **Results dir:** `{results_dir.relative_to(WORKSPACE)}/`
- **Pipeline version:** {version}
- **Workspace:** {WORKSPACE}{spec_info}{prior_log}{checkpoint_ctx}{dry_run_note}

## Pickle Discipline (CRITICAL)
- **Save a .pkl file after EVERY experiment run** — not just at the end. Each experiment should produce `{results_dir.relative_to(WORKSPACE)}/<experiment_id>_results.pkl`
- **Load existing .pkl files** from prior phases/runs before starting. Check `{results_dir.relative_to(WORKSPACE)}/` for any `*.pkl` files and import them into your results dict
- **Final aggregate pickle** at the end: save all results into `{results_dir.relative_to(WORKSPACE)}/{version}_results.pkl`
- If the run crashes mid-way, saved pkl files let us resume without re-running completed experiments
{f"""
## Phase {phase} Only (IMPORTANT)
This pipeline has completed Phase {int(phase)-1} experiments already. **DO NOT re-run Phase {int(phase)-1} cells.**
- Phase {int(phase)-1} results are already saved in `{results_dir.relative_to(WORKSPACE)}/`
- **Load Phase {int(phase)-1} pkl files** — some Phase {phase} experiments may depend on prior results (e.g., saved predictions, model weights)
- **Only extract and run cells from the Phase {phase} section** of the notebook
- Look for the Phase {phase} header/section marker in the notebook to identify the correct cells
""" if phase else ""}
## Creating the Runner Script
Extract from the notebook:
- All imports, data loading, model definitions
- The experiment matrix/configurations
- Training loop and evaluation functions
- Results collection and saving

The runner should:
- Accept `--dry-run` for quick validation
- Accept `--resume` to skip completed experiments
- Save incremental results (pickle + CSV) after each experiment
- Print progress updates
- Save final summary as `results_summary.json`

## When You Encounter Bugs
1. **Fix the bug** in the notebook AND the runner script
2. **Commit the fix:** `cd machinelearning && git add -A && git commit -m "fix({version}): <description>"`
3. **Create a lesson primitive** if the bug reveals a pattern worth remembering:
   `python3 scripts/create_primitive.py lesson "<title>" --severity high --tags snn,debugging --body "<what happened and how to avoid>"`
4. **Retry** the experiment run

## When You Find Significant Results
- Create lesson primitives for patterns worth remembering
- If a result changes architectural direction, create a decision primitive
- Note surprising findings in the results summary

## Completion
When ALL experiments finish successfully:
1. Save `results_summary.json` with per-experiment accuracy, sharpe, timing
2. Run data analysis prep: `python3 scripts/analyze_local_results.py {version} --extra-plots`
3. Commit: `cd machinelearning && git add -A && git commit -m "results({version}): experiment run complete"`
4. Complete: `python3 scripts/pipeline_orchestrate.py {version} complete local_experiment_running --agent builder --notes "RESULTS: <experiment_count> experiments, top accuracy: <best>%"`

## If You Cannot Complete
If you run out of time or hit an unfixable issue:
1. Save your progress to `{results_dir.relative_to(WORKSPACE)}/checkpoint.json` (which experiments completed, what's left)
2. Commit any fixes you've made
3. Block: `python3 scripts/pipeline_orchestrate.py {version} block local_experiment_running --agent builder --notes "CHECKPOINT: <what's done, what's left>"`

The runner will resume you with checkpoint context.
"""


def run_supervised(version: str, notebook_path: Path, results_dir: Path,
                   dry_run: bool = False, max_retries: int = BUILDER_MAX_RESUMES,
                   phase: str = None) -> dict:
    """
    Run experiments with builder agent supervision.

    The builder agent creates, executes, and debugs a runner script
    extracted from the notebook. On timeout, checkpoint-and-resume kicks in.
    """
    attempt = 0
    checkpoint = None

    while attempt < max_retries:
        attempt += 1
        print(f"\n{'─' * 50}")
        print(f"  🤖 Builder supervision — attempt {attempt}/{max_retries}")
        print(f"{'─' * 50}")

        # Reset builder session for clean dispatch
        reset_agent_session('builder')

        # Build task message
        task = build_supervisor_task(
            version, notebook_path, results_dir,
            attempt=attempt, checkpoint=checkpoint, dry_run=dry_run,
            phase=phase,
        )

        # Wake builder
        result = wake_builder(task, timeout=BUILDER_TIMEOUT)

        if result['error'] and 'timed out' in result['error'].lower():
            print(f"  ⏱️  Builder timed out — checking for checkpoint...")

            # Check for checkpoint
            checkpoint_file = results_dir / 'checkpoint.json'
            if checkpoint_file.exists():
                checkpoint = checkpoint_file.read_text()
                print(f"  📋 Found checkpoint — will resume")
            else:
                # Read builder's memory for context
                from datetime import date
                memory_file = WORKSPACE / 'agents' / 'builder' / 'memory' / f'{date.today().isoformat()}.md'
                if memory_file.exists():
                    content = memory_file.read_text()
                    # Extract last entry
                    entries = content.split('\n## ')
                    if len(entries) > 1:
                        checkpoint = f"Builder memory from last session:\n{entries[-1][:2000]}"
                        print(f"  📋 Using builder memory as checkpoint")
                    else:
                        checkpoint = "Previous attempt timed out. Check results dir for partial output."
                else:
                    checkpoint = "Previous attempt timed out. Check results dir for partial output."

            continue

        if result['error']:
            print(f"  ❌ Builder error: {result['error']}")
            # Check if the error is recoverable
            if attempt < max_retries:
                checkpoint = f"Builder error: {result['error']}"
                continue
            break

        if result['success']:
            print(f"  ✅ Builder completed successfully")

            # Verify results exist
            results_files = list(results_dir.glob('*.pkl')) + list(results_dir.glob('*.csv'))
            summary_file = results_dir / 'results_summary.json'

            if summary_file.exists() or results_files:
                print(f"  📊 Results found: {len(results_files)} data files")
                return {
                    'success': True,
                    'errors': [],
                    'response': result['response'][:500],
                    'attempts': attempt,
                }
            else:
                # Builder said success but no results — check pipeline state
                state_file = BUILDS_DIR / f'{version}_state.json'
                if state_file.exists():
                    state = json.load(open(state_file))
                    if state.get('pending_action') in ('local_experiment_complete', 'local_analysis_architect'):
                        print(f"  ✅ Pipeline already advanced — builder completed the stage")
                        return {
                            'success': True,
                            'errors': [],
                            'response': result['response'][:500],
                            'attempts': attempt,
                        }

                print(f"  ⚠️  Builder claims success but no results found — retrying")
                checkpoint = "Previous attempt completed but no result files were saved. Make sure to save results to the results dir."
                continue

        # Builder responded but didn't succeed cleanly
        print(f"  ⚠️  Builder response unclear: {result['response'][:200]}")
        checkpoint = f"Previous attempt response: {result['response'][:1000]}"

    return {
        'success': False,
        'errors': [f'Builder failed after {attempt} attempts'],
        'attempts': attempt,
    }


def run_direct(notebook_path: Path, results_dir: Path, version: str,
               dry_run: bool = False, workers: int = None,
               resume: bool = False) -> dict:
    """
    Direct execution fallback (no builder supervision).
    Tries nbconvert, then run_local.py.
    """
    start_time = time.time()
    log_file = results_dir / 'run.log'
    env = os.environ.copy()
    env['RESULTS_DIR'] = str(results_dir)
    env['PIPELINE_VERSION'] = version

    # Check for supervised runner from prior builder session
    supervised_runner = results_dir / 'run_supervised.py'
    if supervised_runner.exists():
        cmd = [sys.executable, str(supervised_runner)]
        if dry_run:
            cmd.append('--dry-run')
        if resume:
            cmd.append('--resume')
        print(f"  📋 Using builder-created runner: {supervised_runner.name}")
    else:
        # Check nbconvert
        try:
            check = subprocess.run(
                [sys.executable, '-m', 'nbconvert', '--version'],
                capture_output=True, timeout=10,
            )
            nbconvert_available = check.returncode == 0
        except Exception:
            nbconvert_available = False

        if nbconvert_available:
            output_notebook = results_dir / f'{notebook_path.stem}_executed.ipynb'
            cmd = [
                sys.executable, '-m', 'nbconvert',
                '--to', 'notebook', '--execute',
                '--output', str(output_notebook),
                '--ExecutePreprocessor.timeout=-1',
                f'--ExecutePreprocessor.kernel_name=python3',
                str(notebook_path),
            ]
        else:
            # Fallback: run_local.py (equilibrium-specific)
            run_local = ML_DIR / 'scripts' / 'run_local.py'
            if run_local.exists():
                cmd = [sys.executable, str(run_local)]
                if dry_run:
                    cmd.append('--dry-run')
                if workers:
                    cmd.extend(['--workers', str(workers)])
                if resume:
                    cmd.append('--resume')
                env['RESULTS_DIR_OVERRIDE'] = str(results_dir)
            else:
                return {
                    'success': False,
                    'errors': ['No execution method available (nbconvert/run_local.py/run_supervised.py)'],
                    'elapsed': 0,
                }

    print(f"  📋 Command: {' '.join(cmd[:5])}...")

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
            proc.wait()
            elapsed = time.time() - start_time

            log.write(f"\n{'='*60}\n")
            log.write(f"Completed: {datetime.now(timezone.utc).isoformat()}\n")
            log.write(f"Exit code: {proc.returncode}\n")
            log.write(f"Elapsed: {elapsed/60:.1f} minutes\n")

            if proc.returncode != 0:
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


def write_results_summary(version: str, results_dir: Path, run_result: dict):
    """Write experiment results summary for Phase 2 consumption."""
    summary_path = BUILDS_DIR / f'{version}_experiment_results.md'

    log_file = results_dir / 'run.log'
    pooled_section = ''
    if log_file.exists():
        log_content = log_file.read_text()
        if 'POOLED RESULTS' in log_content:
            start = log_content.index('POOLED RESULTS')
            lines = log_content[start:].split('\n')
            pooled_lines = []
            for i, line in enumerate(lines):
                if i > 2 and line.startswith('==='):
                    break
                pooled_lines.append(line)
            pooled_section = '\n'.join(pooled_lines)

    result_files = sorted(results_dir.glob('*'))
    file_list = '\n'.join(f'- `{f.name}` ({f.stat().st_size / 1024:.1f} KB)' for f in result_files)

    summary_path.write_text(f"""---
type: experiment_results
version: {version}
timestamp: {datetime.now(timezone.utc).isoformat()}
success: {run_result.get('success', False)}
errors: {len(run_result.get('errors', []))}
---

# Experiment Results — {version}

## Run Summary
- **Status:** {'✅ Complete' if run_result.get('success') else '❌ Failed'}
- **Attempts:** {run_result.get('attempts', 1)}

## Results
```
{pooled_section}
```

## Output Files
{file_list}
""")
    return summary_path


def main():
    parser = argparse.ArgumentParser(description='Pipeline experiment runner with builder supervision')
    parser.add_argument('version', help='Pipeline version to run experiments for')
    parser.add_argument('--dry-run', action='store_true', help='Quick validation run')
    parser.add_argument('--direct', action='store_true', help='Skip builder, run notebook directly')
    parser.add_argument('--workers', type=int, default=None, help='Override worker count (direct mode)')
    parser.add_argument('--max-retries', type=int, default=5, help='Max builder resume attempts')
    parser.add_argument('--resume', action='store_true', help='Resume from previous partial run')
    parser.add_argument('--analyze-local', action='store_true', help='Chain analysis after experiments')
    parser.add_argument('--phase', type=str, default=None, help='Only run experiments from this phase (e.g., "2" for Phase 2 cells only)')
    args = parser.parse_args()

    version = args.version
    print(f"\n{'═' * 70}")
    print(f"  🧪 EXPERIMENT RUNNER — {version}")
    print(f"  {'🤖 Supervised' if not args.direct else '⚡ Direct'} mode")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'═' * 70}\n")

    # Load pipeline info
    fm = load_pipeline_frontmatter(version)
    if not fm:
        print(f"❌ Pipeline not found: {version}")
        sys.exit(1)

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

    # Write PID file
    pid_file = write_pid_file(version)
    print(f"  🆔 PID: {os.getpid()}")

    # Update pipeline stage → running
    print(f"\n  📊 Updating pipeline stage → local_experiment_running")
    run_pipeline_update([
        version, 'start', 'local_experiment_running',
        '--agent', 'system',
        '--notes', f'Experiment run started (PID: {os.getpid()}, mode: {"supervised" if not args.direct else "direct"})'
    ])

    # Run experiments
    if args.direct:
        run_result = run_direct(
            notebook_path, results_dir, version,
            dry_run=args.dry_run,
            workers=args.workers,
            resume=args.resume,
        )
    else:
        run_result = run_supervised(
            version, notebook_path, results_dir,
            dry_run=args.dry_run,
            max_retries=args.max_retries,
            phase=args.phase,
        )

    # Write results summary
    summary_path = write_results_summary(version, results_dir, run_result)
    print(f"\n  📝 Results summary: {summary_path.relative_to(WORKSPACE)}")

    # Run analysis prep if direct mode succeeded
    if run_result.get('success') and args.direct:
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
            if analyze_result.returncode == 0:
                print(f"  ✅ Analysis data prep complete")
            else:
                print(f"  ⚠️  Analysis prep warnings: {analyze_result.stderr[:200]}")
        except Exception as e:
            print(f"  ⚠️  Analysis prep failed (non-fatal): {e}")

    # Update pipeline stage based on result
    if run_result.get('success'):
        # In supervised mode, builder may have already completed the stage
        # Check state before double-completing
        state_file = BUILDS_DIR / f'{version}_state.json'
        already_completed = False
        if state_file.exists():
            state = json.load(open(state_file))
            if state.get('pending_action') in ('local_experiment_complete', 'local_analysis_architect'):
                already_completed = True

        if not already_completed:
            print(f"\n  📊 Completing stage → local_experiment_complete")
            run_pipeline_update([
                version, 'complete', 'local_experiment_running',
                '--agent', 'system',
                '--notes', f'Experiments complete. Results at {results_dir.relative_to(WORKSPACE)}'
            ])
    else:
        errors_summary = '; '.join(run_result.get('errors', ['Unknown error']))[:200]
        run_pipeline_update([
            version, 'start', 'local_experiment_running',
            '--agent', 'system',
            '--notes', f'EXPERIMENT FAILED after {run_result.get("attempts", 1)} attempts: {errors_summary}'
        ])

    # Chain analysis if requested
    if run_result.get('success') and args.analyze_local:
        print(f"\n  🔬 Chaining local analysis...")
        try:
            from pipeline_orchestrate import orchestrate_local_analysis
            orchestrate_local_analysis(version)
        except Exception as e:
            print(f"  ⚠️  Analysis chain failed: {e}")

    # Cleanup
    remove_pid_file(version)

    print(f"\n{'═' * 70}")
    print(f"  {'✅ SUCCESS' if run_result.get('success') else '❌ FAILED'} — {version}")
    print(f"{'═' * 70}\n")

    sys.exit(0 if run_result.get('success') else 1)


if __name__ == '__main__':
    main()
