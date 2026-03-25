# Pipeline Notification Fix — Test Results

**Date:** 2026-03-25  
**Task:** Ensure all pipeline stage transitions send Telegram group notifications

## Changes Made

### Fix 1: `scripts/pipeline_update.py`
- Added `system` and `coordinator` to `AGENT_DISPLAY`
- Fixed `_get_bot_token()`: when agent maps to a non-group-member account key (system, coordinator, belam-main, etc.), falls back through architect → builder → critic bot tokens instead of silently returning `None`

### Fix 2: `scripts/launch_pipeline.py`
- Added `notify_group()` call after successful `fire_and_forget_dispatch()` on kickoff
- Uses `system` agent (falls back to group member bot token)

### Fix 3: `scripts/orchestration_engine.py`
- Added `notify_group()` call inside `fire_and_forget_dispatch()` after successful Popen
- Wrapped in try/except to never block dispatch on notification failure

## Test Results

```
system token: found
belam-main token: found
coordinator token: found
architect token: found
critic token: found
builder token: found

AGENT_DISPLAY entries:
  architect: ('🏗️ Architect', 'architect')
  critic: ('🔍 Critic', 'critic')
  builder: ('🔨 Builder', 'builder')
  system: ('🤖 System', 'default')
  coordinator: ('🔮 Belam', 'default')
  belam-main: ('🔮 Belam', 'default')
  main: ('🔮 Belam', 'default')
  unknown: ('🔮 Belam', 'default')
```

All three modified files pass syntax check ✅

## Coverage

| Code Path | Before | After |
|-----------|--------|-------|
| `pipeline_update.py cmd_complete()` | ✅ notifies | ✅ notifies (now works for system agent too) |
| `pipeline_update.py cmd_start()` | ✅ notifies | ✅ notifies |
| `pipeline_update.py cmd_block()` | ✅ notifies | ✅ notifies |
| `orchestration_engine.py fire_and_forget_dispatch()` | ❌ silent | ✅ notifies |
| `launch_pipeline.py --kickoff` | ❌ silent | ✅ notifies (via fire_and_forget_dispatch) |
| `pipeline_orchestrate.py orchestrate_complete_task()` | ✅ notifies | ✅ notifies |

## Design: Single Notification Point

`fire_and_forget_dispatch()` is the single notification point for all dispatches. `launch_pipeline.py --kickoff` relies on it rather than sending its own, avoiding duplicates.
