---
primitive: memory_log
timestamp: "2026-03-19T15:06:31Z"
category: technical
importance: 3
tags: [infrastructure, experiments, pipeline, orchestration]
source: "session"
content: "Built pipeline-integrated local experiment runner. New stages: local_experiment_running → local_experiment_complete, slotting between phase1_complete and Phase 2. Five components: (1) run_experiment.py — parametric pipeline-aware wrapper that reads notebook from pipeline frontmatter, auto-updates stages, spawns builder agent for error recovery with retry loop. (2) pipeline_update.py — new STAGE_TRANSITIONS, STATUS_BUMPS, START_STATUS_BUMPS for experiment stages. (3) pipeline_orchestrate.py — orchestrate_local_run() launches experiments in background with PID tracking. (4) pipeline_autorun.py — check_experiment_eligible() auto-triggers experiments from phase1_complete, check_running_experiments() monitors active runs and recovers dead processes. (5) belam CLI — 'belam run <ver>' command. Pipeline template + all 3 active pipelines updated with experiment section. Flow: phase1_complete → autorun detects → launches run_experiment.py → self-reports via pipeline_update → experiment_complete → Phase 2 auto-triggers. Builder agent invoked for runtime errors with up to 2 retry cycles."
status: consolidated
---

# Memory Entry

**2026-03-19T15:06:31Z** · `technical` · importance 3/5

Built pipeline-integrated local experiment runner. New stages: local_experiment_running → local_experiment_complete, slotting between phase1_complete and Phase 2. Five components: (1) run_experiment.py — parametric pipeline-aware wrapper that reads notebook from pipeline frontmatter, auto-updates stages, spawns builder agent for error recovery with retry loop. (2) pipeline_update.py — new STAGE_TRANSITIONS, STATUS_BUMPS, START_STATUS_BUMPS for experiment stages. (3) pipeline_orchestrate.py — orchestrate_local_run() launches experiments in background with PID tracking. (4) pipeline_autorun.py — check_experiment_eligible() auto-triggers experiments from phase1_complete, check_running_experiments() monitors active runs and recovers dead processes. (5) belam CLI — 'belam run <ver>' command. Pipeline template + all 3 active pipelines updated with experiment section. Flow: phase1_complete → autorun detects → launches run_experiment.py → self-reports via pipeline_update → experiment_complete → Phase 2 auto-triggers. Builder agent invoked for runtime errors with up to 2 retry cycles.

---
*Source: session*
*Tags: infrastructure, experiments, pipeline, orchestration*
