---
name: launch-pipeline
description: >
  Launch and kick off implementation pipelines from open tasks. Use when:
  (1) a heartbeat finds eligible open tasks with met dependencies,
  (2) user says "launch pipeline", "kick off", "start pipeline", or "spawn pipeline",
  (3) an analysis gate opens and downstream tasks become eligible.
  Handles the full flow: gate checking → pipeline creation → orchestrator kickoff → task status update.
  NOT for: checking pipeline status (use pipelines skill), updating existing pipeline stages
  (agents use pipeline_orchestrate.py directly), or creating analysis pipelines (use R pipeline analyze).
---

# Launch Pipeline

## Quick Start

Kick off an existing (already-created) pipeline:
```bash
R kickoff <version>
```

Create AND kick off a new pipeline from scratch:
```bash
R pipeline launch <version> --desc "..." --priority <p> --tags <t> --project <proj> --kickoff
```

## Decision Flow

Before launching, check these gates in order:

### 1. Is the task eligible?

```bash
# Read the task file
cat tasks/<task-slug>.md
```

Check:
- `status: open` (not `in_pipeline`, `blocked`, or `done`)
- `depends_on` — all listed dependencies must be `status: done` or `status: in_pipeline` with completion
- No existing pipeline for this task (`R pipelines` — check version names)

### 2. Does it need the analysis gate?

**Gate-blocked tasks** (new notebook versions like `build-equilibrium-snn`):
```bash
R pipeline v4-deep-analysis
```
- Must show `analysis_phase2_complete` or later
- If gate is NOT open → skip, do not launch

**Gate-free tasks** (ensemble stacking, validation, infrastructure):
- Tasks with `depends_on: []` that aren't new notebook versions
- Proceed directly

### 3. Pipeline or sub-agent?

| Task Type | Action |
|-----------|--------|
| New notebook version | Full pipeline (`R pipeline launch`) |
| Experiment validation | Full pipeline |
| Ensemble/stacking | Full pipeline |
| Infrastructure/config | Single sub-agent (no pipeline needed) |
| Data collection | Single sub-agent |

### 4. Create and kick off

For a full pipeline:
```bash
R pipeline launch <version> \
  --desc "<from task description>" \
  --priority <task priority> \
  --tags <comma,separated,tags> \
  --project <task project> \
  --kickoff
```

For an already-created pipeline that was never kicked off:
```bash
R kickoff <version>
```

### 5. Update the task

After launching, update the task's status via coordinate edit:
```
e1{task_coord} status in_pipeline
```
Example: `e1t3 status in_pipeline` sets task 3's status.

## What `R kickoff` / `e0` does

1. Completes `pipeline_created` stage → triggers architect_design transition
2. Orchestrator **saves memory** for the calling agent (auto-consolidation)
3. Updates state + markdown + Telegram group notification
4. Determines next agent (architect) from transition map
5. Wakes architect via fresh session (UUID4)
6. Architect gets full context: files to read, pipeline state, orchestrator commands, memory protocol
7. Writes handoff record to `pipelines/handoffs/` for verification
8. **On timeout (10 min):** checkpoint-and-resume kicks in automatically
   - Scans for partial artifacts the architect created
   - Writes checkpoint to architect's memory files
   - Wakes architect again with fresh session + resume context
   - Up to 5 resume cycles (60 min total) before alerting Shael

## Agent Session Model

All agents (architect, critic, builder) run on **Opus** with:
- **Fresh session per handoff** — no session reuse, prevents stale context
- **10-minute window** per session (600s timeout)
- **Memory files as continuity** — agents read `memory/YYYY-MM-DD.md` at session start
- **Auto memory consolidation** — orchestrator writes `--notes` and `--learnings` to agent memory before handoff
- **Auto-Wiggum dispatch** — `--wiggum` flag (default for `e0 t{n}`) uses `auto_wiggum.py` for steer-timer-aware dispatch. Steers agent at 80% timeout to wrap up cleanly. Falls back to `pipeline_stall_recovery.py` (cron, every 15min) if agent dies.
- **Checkpoint-and-resume** — on timeout, partial work is preserved and a fresh session continues

### Wiggum Dispatch

```bash
# e0 t{n} now uses wiggum by default
python3 scripts/launch_pipeline.py {slug} --kickoff --wiggum
python3 scripts/launch_pipeline.py {slug} --kickoff --wiggum --wiggum-timeout 900  # 15min
```

The auto-recovery chain:
1. `auto_wiggum.py` steers agent at 80% timeout → agent wraps up
2. `pipeline_stall_recovery.py` (cron) catches dead agents within 15min → re-dispatches with escalating timeout
3. Max 3 retries per stage → alerts for manual intervention

## Analysis Pipelines

For post-experiment analysis (after Colab run produces pkl files):
```bash
R pipeline analyze <source-version> \
  --desc "..." \
  --priority <p> \
  --kickoff
```

## Batch Kickoff

⚠️ **One pipeline at a time.** Each kickoff gives the architect a single pipeline to focus on.
Space kickoffs apart to let the agent finish before receiving the next:

```bash
R kickoff build-equilibrium-snn
# Wait for architect to complete design (check with: R pipeline build-equilibrium-snn)
R kickoff stack-specialists
# Wait again...
R kickoff validate-scheme-b
```

If kicking off multiple in sequence without waiting:
```bash
for ver in build-equilibrium-snn stack-specialists validate-scheme-b; do
  R kickoff "$ver"
  sleep 5
done
```

## Troubleshooting

If kickoff fails (architect doesn't respond):
```bash
R handoffs              # Check pending handoffs
R orchestrate <ver> verify  # Retry failed handoffs
```

If agent times out repeatedly:
- Check `pipelines/handoffs/` for timeout records
- Check agent memory: `cat ~/.openclaw/workspace-architect/memory/$(date -u +%Y-%m-%d).md`
- Checkpoint-and-resume handles up to 5 retries automatically
- After 5 retries, Telegram alert is sent for manual intervention
