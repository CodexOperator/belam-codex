---
primitive: memory_log
timestamp: "2026-03-23T08:10:35Z"
category: event
importance: 4
tags: [instance:main, pipeline, orchestration, bugfix, e0]
source: "session"
content: "Unclaimed dispatch recovery gap found and patched in e0 sweep. Shael asked to re-kick p1 critic stage (codex-engine-v3-legendary-map) using e0 instead of manual kick, to test edge case handling. Found dispatch_claimed=false was ignored by _is_pipeline_already_dispatched() — a sent-but-unclaimed dispatch looked identical to an actively running one. Also discovered e0 routes through orchestration_engine.py sweep(), not pipeline_autorun.py main(). Fixed both files: patched _is_pipeline_already_dispatched() to treat unclaimed dispatches older than 5min as failed, added check_unclaimed_dispatches() helper to orchestration_engine.py, wired it into sweep() as new 'Unclaimed Dispatch Recovery' step. Also fixed pending_action field check — state JSON uses agent role names (e.g. 'critic') not stage names (e.g. 'phase2_critic_code_review'). Fix worked: sweep successfully re-kicked the critic for p1."
status: consolidated
---

# Memory Entry

**2026-03-23T08:10:35Z** · `event` · importance 4/5

Unclaimed dispatch recovery gap found and patched in e0 sweep. Shael asked to re-kick p1 critic stage (codex-engine-v3-legendary-map) using e0 instead of manual kick, to test edge case handling. Found dispatch_claimed=false was ignored by _is_pipeline_already_dispatched() — a sent-but-unclaimed dispatch looked identical to an actively running one. Also discovered e0 routes through orchestration_engine.py sweep(), not pipeline_autorun.py main(). Fixed both files: patched _is_pipeline_already_dispatched() to treat unclaimed dispatches older than 5min as failed, added check_unclaimed_dispatches() helper to orchestration_engine.py, wired it into sweep() as new 'Unclaimed Dispatch Recovery' step. Also fixed pending_action field check — state JSON uses agent role names (e.g. 'critic') not stage names (e.g. 'phase2_critic_code_review'). Fix worked: sweep successfully re-kicked the critic for p1.

---
*Source: session*
*Tags: instance:main, pipeline, orchestration, bugfix, e0*
