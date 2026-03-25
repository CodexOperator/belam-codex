# Spec: Pipeline Stall Recovery

## Problem

Builder agents time out or crash mid-stage. The pipeline state file stays at the dispatched stage (e.g. `p1_builder_implement`) indefinitely because no process advances it. Heartbeat sees "still building" and skips. The pipeline is effectively dead until a human notices.

## Solution

A lightweight recovery script (`scripts/pipeline_stall_recovery.py`) that:

1. Scans all non-archived pipelines for stalls
2. Detects when a pipeline has been in the same stage for longer than a configurable threshold
3. Checks if the dispatched agent process is still alive (PID from state)
4. If agent is dead and stage is stale:
   a. Re-dispatches the same agent to the same session (session mode: `continue`) with a longer timeout
   b. Logs the recovery attempt to the pipeline state file
   c. Caps retries (max 3 recovery attempts per stage to prevent infinite loops)

## Detection Logic

```python
def is_stalled(state_json, threshold_minutes=30):
    """A pipeline is stalled when:
    1. status_updated is older than threshold_minutes ago
    2. dispatch_claimed is False (agent never picked it up) OR
       the dispatched PID is no longer running
    3. status is an active stage (not archived, not *_complete)
    """
```

## Recovery Action

```python
def recover(pipeline_version, state):
    """
    1. Check retry count (state.recovery_attempts[stage] < 3)
    2. Re-dispatch via pipeline_orchestrate.py:
       - Same stage (don't advance — let the agent finish or re-do)
       - Session mode: continue (resume existing context)
       - Timeout: original_timeout * 1.5 (escalating)
    3. Update state:
       - last_dispatched = now
       - recovery_attempts[stage] += 1
       - recovery_log.append({time, stage, attempt, reason})
    4. Log to stdout for heartbeat capture
    """
```

## Configuration

- `STALL_THRESHOLD_MINUTES`: 30 (default) — how long before a stage is considered stalled
- `MAX_RECOVERY_ATTEMPTS`: 3 — per stage, not per pipeline
- `TIMEOUT_ESCALATION`: 1.5x — each retry gets 50% more time
- `BASE_TIMEOUT_SECONDS`: 600 (10min) — default agent timeout

## Integration

Add to HEARTBEAT.md as a new task (lightweight, runs every heartbeat):
```
python3 scripts/pipeline_stall_recovery.py --threshold 30 --dry-run  # first, verify
python3 scripts/pipeline_stall_recovery.py --threshold 30            # then, recover
```

## Deliverables

1. `scripts/pipeline_stall_recovery.py` — the recovery script
2. `tests/test_stall_recovery.py` — unit tests with mock state files
3. Integration notes for HEARTBEAT.md (do NOT modify HEARTBEAT.md directly)

## Anti-patterns

- Do NOT advance the stage on recovery — re-dispatch to the SAME stage so the agent can finish
- Do NOT recover archived or completed pipelines
- Do NOT exceed MAX_RECOVERY_ATTEMPTS — after 3 failures, log an alert and stop
- Do NOT modify pipeline_orchestrate.py — use it as-is via subprocess or import
