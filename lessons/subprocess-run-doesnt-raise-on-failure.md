---
primitive: lesson
severity: high
date: 2026-03-19
context: run_experiment.py papermill detection set papermill_available=True even when papermill wasn't installed
tags: [python, debugging, infrastructure]
downstream: [memory/2026-03-19_191633_supervised-builder-experiment-runner-wor]
promotion_status: exploratory
doctrine_richness: 7
contradicts: []
---

# subprocess.run Does Not Raise on Non-Zero Exit Code

## What Happened

`run_experiment.py` checked for papermill availability with:
```python
try:
    subprocess.run([sys.executable, '-m', 'papermill', '--version'],
                  capture_output=True, timeout=10)
    papermill_available = True
except Exception:
    pass
```

`subprocess.run()` returns normally even when the command fails (exit code 1). No exception is raised. So `papermill_available` was set to `True` even though papermill wasn't installed. The runner then tried to use papermill and failed.

## The Fix

Always check `returncode`:
```python
result = subprocess.run([sys.executable, '-m', 'papermill', '--version'],
                       capture_output=True, timeout=10)
papermill_available = result.returncode == 0
```

Or use `check=True` to make it raise `CalledProcessError` on non-zero exit.

## Pattern

This is a general Python gotcha: `subprocess.run()` only raises exceptions for OS-level failures (command not found, timeout), NOT for non-zero exit codes. Any "is this tool installed?" check that relies on try/except around `subprocess.run()` without `check=True` will silently pass.
