# Spec: Auto-Wiggum Runner

## Problem

The Ralph Wiggum pattern (spawn agent → steer at threshold → let it wrap up) currently requires Belam to be alive and orchestrating. If the gateway crashes or the main session is busy, nobody spawns agents or sends steer messages. The steer_timer.sh is tied to a parent session that may not survive.

## Solution

A standalone script (`scripts/auto_wiggum.py`) that:

1. Resets a target agent session (fresh context)
2. Sends a task message to the agent
3. Runs its own timer (no dependency on parent session)
4. At the steer threshold (default 80% of timeout), sends a wrap-up steer message
5. At hard timeout, logs result and exits
6. Can be called from cron, heartbeat, or CLI

## Usage

```bash
# Basic: send task to builder with 10min timeout
python3 scripts/auto_wiggum.py --agent builder --timeout 600 --task "Implement feature X"

# With custom steer ratio
python3 scripts/auto_wiggum.py --agent sage --timeout 300 --steer-ratio 0.7 --task "Extract memories from session abc"

# With task file (for long prompts)
python3 scripts/auto_wiggum.py --agent builder --timeout 600 --task-file specs/my-task.md

# Pipeline-aware: include pipeline context automatically
python3 scripts/auto_wiggum.py --agent builder --timeout 600 --pipeline my-pipeline --stage p1_builder_implement

# Complete a pipeline stage on success
python3 scripts/auto_wiggum.py --agent builder --timeout 600 --pipeline my-pipeline --stage p1_builder_implement --complete-on-exit
```

## Architecture

```
auto_wiggum.py
├── reset_agent_session(agent)          # openclaw session reset
├── send_task(agent, task_text)         # openclaw session send  
├── wait_and_steer(timeout, ratio)      # sleep → steer at threshold
├── poll_completion(agent, timeout)     # check if agent finished early
└── finalize(pipeline, stage)           # optional: mark stage complete
```

## Session Control

Uses OpenClaw CLI for session management (same as pipeline_orchestrate.py):
- Reset: `openclaw session reset agent:{agent}:main`
- Send: `openclaw session send agent:{agent}:main "{message}"`
- These work even when the gateway is running but Belam's main session is dead

## Steer Message

At steer threshold, send:
```
⏰ WRAP UP — You have {remaining}s left before hard timeout.
Finish what you're doing NOW:
1. Write any remaining files
2. Run tests if applicable  
3. If working on a pipeline, run: python3 scripts/pipeline_orchestrate.py {version} complete {stage}
4. Summarize what you completed and what remains

Do NOT start new work. Wrap up cleanly.
```

## Pipeline Integration

When `--pipeline` and `--stage` are provided:
- Prepend pipeline context to task (read pipeline state, spec, prior reviews)
- On `--complete-on-exit`: after timeout, check if agent completed the stage. If not, mark it as needing recovery (stall_recovery will pick it up).

## Deliverables

1. `scripts/auto_wiggum.py` — the standalone runner
2. `tests/test_auto_wiggum.py` — unit tests (mock subprocess calls)
3. Integration notes for use with stall_recovery.py

## Error Handling

- If session reset fails: log error, exit 1
- If session send fails: retry once, then exit 1  
- If gateway is down: log error, exit 1 (stall_recovery cron will retry later)
- All output to stdout for log capture

## Anti-patterns

- Do NOT import openclaw internals — use CLI subprocess calls only
- Do NOT block indefinitely — always respect hard timeout
- Do NOT modify pipeline state directly — use pipeline_orchestrate.py
- Do NOT depend on Belam's main session being alive
