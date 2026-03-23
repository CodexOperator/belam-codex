---
primitive: lesson
date: 2026-03-23
source: orchestration_engine.py fire_and_forget_dispatch()
confidence: high
upstream: [unclaimed-dispatch-recovery-in-sweep]
downstream: []
tags: [instance:main, orchestration, pipeline, bug-fix]
---

# fire-and-forget-dispatch-timeout-1-killed-all-agents

## Context

`fire_and_forget_dispatch()` in `orchestration_engine.py` spawns pipeline agents via `subprocess.Popen` with `start_new_session=True`. It was also passing `--timeout 1` to the `openclaw agent` CLI to "make it return quickly." Every dispatched agent (critic, builder, architect) was being killed after 1 second — appearing as `abortedLastRun: true` with 0 tokens processed. This triggered repeated unclaimed_recovery loops in e0 sweeps.

## What Happened

Shael noticed the critic for `codex-engine-v3-legendary-map/phase2_critic_code_review` kept showing as dispatched but never ran. The e0 sweep's unclaimed_recovery fired repeatedly. Investigation of the critic's session transcript showed it started at 08:08:41 and was aborted at 08:08:42 — exactly 1 second. Traced to `'--timeout', '1'` in the Popen command array in `orchestration_engine.py`. The `--timeout` flag sets the **agent's maximum runtime**, not CLI wait time. Fixed by removing the flag entirely (commit `724d787f`). `Popen` with `start_new_session=True` already returns immediately.

## Lesson

`openclaw agent --timeout` sets the **agent's runtime limit**, not how long the CLI blocks. When using `Popen` for fire-and-forget dispatch, no `--timeout` flag is needed — the process detaches immediately.

## Application

- Never pass `--timeout 1` (or any short timeout) to `openclaw agent` in background dispatch paths.
- Verify agent timeout flags in any orchestration code that spawns agents.
- When agents abort in ~1s with 0 tokens, check for aggressive timeout flags before investigating other causes.
- This was the root cause of ALL unclaimed dispatch recoveries prior to 2026-03-23.
