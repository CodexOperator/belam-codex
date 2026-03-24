#!/usr/bin/env python3
"""
Pipeline Verification Runner — Run test specs and report results.

Parses {version}_test_spec.md, executes automated/file-check/import-check tests,
writes results to {version}_test_results.md and {version}_test_results.json.

Single-run test executor. The iteration loop (run → fix → rerun) is handled
at the agent/orchestrator level, not here.

Usage:
    python3 scripts/pipeline_verify.py <version> [--workspace <path>] [--dry-run]
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Default workspace
WORKSPACE = Path(__file__).parent.parent
BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
ALT_BUILDS_DIR = WORKSPACE / 'pipeline_builds'


def parse_test_spec(spec_path: Path) -> list[dict]:
    """Parse test_spec.md into a list of test definitions.

    Expected format per test block:
        ### T{n}: {description}
        **Type:** automated | file-check | import-check | manual
        **Command:**
        ```bash
        <command>
        ```
        **Pass criteria:** <criteria string>
        **Covers:** D{n}
    """
    content = spec_path.read_text(encoding='utf-8')
    tests = []

    # Split on ### T{n}: headers
    blocks = re.split(r'### (T\d+):\s*', content)
    for i in range(1, len(blocks), 2):
        test_id = blocks[i]
        body = blocks[i + 1]

        test = {'id': test_id, 'description': ''}

        # Extract description (first line of body)
        desc_line = body.strip().split('\n')[0].strip()
        test['description'] = desc_line

        # Extract type
        type_match = re.search(r'\*\*Type:\*\*\s*(\w[\w-]*)', body)
        test['type'] = type_match.group(1) if type_match else 'automated'

        # Extract command (code block after **Command:**)
        cmd_match = re.search(
            r'\*\*Command:\*\*\s*```(?:bash|python3?)?\n(.+?)```',
            body, re.DOTALL
        )
        test['command'] = cmd_match.group(1).strip() if cmd_match else None

        # Extract pass criteria
        pass_match = re.search(
            r'\*\*Pass criteria:\*\*\s*(.+?)(?:\n\*\*|\n###|\n---|\Z)',
            body, re.DOTALL
        )
        test['pass_criteria'] = pass_match.group(1).strip() if pass_match else None

        # Extract covers
        covers_match = re.search(r'\*\*Covers:\*\*\s*(.+?)(?:\n|$)', body)
        test['covers'] = covers_match.group(1).strip() if covers_match else None

        tests.append(test)

    return tests


def check_pass_criteria(criteria: str, exit_code: int, stdout: str) -> bool:
    """Evaluate pass criteria against test output."""
    if not criteria:
        return exit_code == 0

    passed = True

    # Check exit code
    if re.search(r'exit\s*code\s*0', criteria, re.IGNORECASE):
        if exit_code != 0:
            passed = False

    # Check for "contains" patterns (quoted strings)
    contains_patterns = re.findall(r'contains?\s+"([^"]+)"', criteria, re.IGNORECASE)
    for pattern in contains_patterns:
        if pattern not in stdout:
            passed = False

    # Check for "stdout contains" without quotes
    stdout_match = re.search(r'stdout\s+contains?\s+(\S+)', criteria, re.IGNORECASE)
    if stdout_match and stdout_match.group(1) not in stdout:
        passed = False

    return passed


def run_test(test: dict, workspace: Path) -> dict:
    """Run a single test and return result dict."""
    result = {
        'id': test['id'],
        'type': test['type'],
        'description': test.get('description', ''),
        'covers': test.get('covers', ''),
    }

    if test['type'] == 'manual':
        result['status'] = 'SKIP'
        result['note'] = 'Manual test — requires human inspection'
        return result

    if not test.get('command'):
        result['status'] = 'SKIP'
        result['note'] = 'No command specified'
        return result

    try:
        proc = subprocess.run(
            test['command'], shell=True, capture_output=True, text=True,
            timeout=60, cwd=str(workspace)
        )
        result['exit_code'] = proc.returncode
        result['stdout'] = proc.stdout[:2000]
        result['stderr'] = proc.stderr[:500]

        criteria = test.get('pass_criteria', 'Exit code 0')
        passed = check_pass_criteria(criteria, proc.returncode, proc.stdout)
        result['status'] = 'PASS' if passed else 'FAIL'

    except subprocess.TimeoutExpired:
        result['status'] = 'TIMEOUT'
        result['note'] = 'Test exceeded 60s timeout'
    except Exception as e:
        result['status'] = 'ERROR'
        result['error'] = str(e)

    return result


def write_results_md(path: Path, version: str, results: list[dict]) -> None:
    """Write test results as markdown."""
    now = datetime.now(timezone.utc).isoformat()
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    skipped = sum(1 for r in results if r['status'] == 'SKIP')
    total = len(results)

    lines = [
        f'# Test Results: {version}',
        f'**Run:** {now}',
        f'**Summary:** {passed}/{total} passed, {failed} failed, {skipped} skipped',
        f'**Verdict:** {"✅ GREEN" if failed == 0 else "❌ RED"}',
        '',
        '| Test | Status | Description | Covers |',
        '|------|--------|-------------|--------|',
    ]
    for r in results:
        status_icon = {
            'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭️',
            'TIMEOUT': '⏰', 'ERROR': '💥'
        }.get(r['status'], '?')
        lines.append(
            f"| {r['id']} | {status_icon} {r['status']} | "
            f"{r.get('description', '')[:60]} | {r.get('covers', '')} |"
        )

    # Failure details
    failures = [r for r in results if r['status'] in ('FAIL', 'ERROR', 'TIMEOUT')]
    if failures:
        lines.append('')
        lines.append('## Failure Details')
        for r in failures:
            lines.append(f"\n### {r['id']}: {r['status']}")
            if r.get('exit_code') is not None:
                lines.append(f"Exit code: {r['exit_code']}")
            if r.get('stderr'):
                lines.append(f"```\n{r['stderr'][:500]}\n```")
            if r.get('stdout'):
                lines.append(f"Stdout (truncated):\n```\n{r['stdout'][:500]}\n```")
            if r.get('error'):
                lines.append(f"Error: {r['error']}")
            if r.get('note'):
                lines.append(f"Note: {r['note']}")

    path.write_text('\n'.join(lines), encoding='utf-8')


def run_all(version: str, workspace: Path, dry_run: bool = False) -> dict:
    """Run full test suite for a pipeline version.

    Returns dict with status (GREEN/RED/NO_SPEC/NO_TESTS), counts, results.
    """
    # Find test spec
    spec_path = BUILDS_DIR / f'{version}_test_spec.md'
    if not spec_path.exists():
        spec_path = ALT_BUILDS_DIR / f'{version}_test_spec.md'
    if not spec_path.exists():
        return {'status': 'NO_SPEC', 'error': f'Test spec not found for {version}'}

    tests = parse_test_spec(spec_path)
    if not tests:
        return {'status': 'NO_TESTS', 'error': 'No tests found in spec'}

    if dry_run:
        print(f"Found {len(tests)} tests in {spec_path.name}:")
        for t in tests:
            print(f"  {t['id']}: [{t['type']}] {t.get('description', '')[:80]}")
        return {
            'status': 'DRY_RUN',
            'tests': len(tests),
            'test_ids': [t['id'] for t in tests],
        }

    # Run tests
    results = []
    for test in tests:
        print(f"  Running {test['id']}... ", end='', flush=True)
        result = run_test(test, workspace)
        print(result['status'])
        results.append(result)

    # Write results (markdown + JSON)
    results_dir = spec_path.parent
    write_results_md(results_dir / f'{version}_test_results.md', version, results)

    json_results = {
        'version': version,
        'run_at': datetime.now(timezone.utc).isoformat(),
        'results': results,
    }
    with open(results_dir / f'{version}_test_results.json', 'w') as f:
        json.dump(json_results, f, indent=2, default=str)

    # Summary
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    skipped = sum(1 for r in results if r['status'] == 'SKIP')
    errored = sum(1 for r in results if r['status'] in ('ERROR', 'TIMEOUT'))

    return {
        'status': 'GREEN' if failed == 0 and errored == 0 else 'RED',
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'errored': errored,
        'total': len(results),
        'results': results,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    version = sys.argv[1]
    workspace = WORKSPACE
    dry_run = '--dry-run' in sys.argv

    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == '--workspace' and i + 1 < len(sys.argv):
            workspace = Path(sys.argv[i + 1])

    print(f"{'=' * 60}")
    print(f"  PIPELINE VERIFICATION: {version}")
    print(f"{'=' * 60}")

    result = run_all(version, workspace, dry_run=dry_run)
    print(f"\n{'=' * 60}")

    if result['status'] in ('NO_SPEC', 'NO_TESTS', 'DRY_RUN'):
        print(f"  {result['status']}: {result.get('error', 'OK')}")
        sys.exit(0 if result['status'] == 'DRY_RUN' else 1)

    verdict = '✅ GREEN — all tests passed' if result['status'] == 'GREEN' \
        else f"❌ RED — {result['failed']} failed, {result.get('errored', 0)} errors"
    print(f"  {verdict}")
    print(f"  Passed: {result['passed']}/{result['total']}  "
          f"Skipped: {result['skipped']}")
    print(f"{'=' * 60}")

    # Print JSON for machine consumption
    print(json.dumps({k: v for k, v in result.items() if k != 'results'},
                     indent=2))
    sys.exit(0 if result['status'] == 'GREEN' else 1)


if __name__ == '__main__':
    main()
