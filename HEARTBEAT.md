# HEARTBEAT.md — Context-Aware Orchestrator

## Orchestrator Reference

**Before executing tasks below, read `templates/heartbeat.md`** for the full decision framework, script reference, gate rules, and anti-patterns. That file is your HOW — this file is your WHAT.

---

## Task 1: Pipeline & Task Orchestration

The primary heartbeat responsibility: move work forward.

1. **Check active pipelines:** `belam pipelines`
   - If any pipeline stage is stalled (>2h since last update with no agent activity), alert Shael
   - If a pipeline just completed a phase, check what downstream work is now unblocked

2. **Check open tasks:** `grep -l "status: open" tasks/*.md`
   - For each open task, read its `depends_on` field
   - If dependencies are met AND no pipeline already exists for this task → **eligible for pipeline spawn**
   - Use the decision framework in `templates/heartbeat.md` (Task-to-Pipeline Mapping) to decide whether to spawn a full pipeline or a focused sub-agent
   - **Gate check:** If the task is a new notebook version, verify the analysis gate is clear first
   - **Non-gated tasks** (infrastructure, ensemble stacking, validation) can proceed independently
   - **All research tasks produce Colab notebooks** — non-pipeline tasks go to `notebooks/standalone/`

3. **Spawn pipelines for eligible tasks:**
   - Implementation: `python3 scripts/launch_pipeline.py {ver} --desc "..." --priority {p} --tags {t} --project {proj} --kickoff`
   - Analysis: `python3 scripts/launch_analysis_pipeline.py {ver}-analysis --source-version {ver} --desc "..." --kickoff`
   - After spawning, update the task's `status: in_pipeline` and add `pipeline: {version}`

4. **If nothing to do:** skip silently

## Task 2: Experiment Analysis Pipeline

Detect new experiment results and extract lessons:

1. Run `python3 scripts/analyze_experiment.py --detect --quiet`
2. If briefs were generated, spawn a sub-agent with task:
   "Read all pending analysis briefs in machinelearning/snn_applied_finance/research/pipeline_output/ (files with 'status: pending_review'). For each brief:
   1. Read the code changes section — these are Shael's manual tweaks (highest-signal data)
   2. Create lesson primitives in workspace/lessons/ for significant findings
   3. Update research/TECHNIQUES_TRACKER.md with new results
   4. Update the brief's frontmatter to 'status: processed'
   5. If findings change architectural direction, update the relevant *_KNOWLEDGE.md
   6. If analysis reveals a compelling follow-up (score ≥ 7), generate Phase 3 proposal:
      `python3 scripts/analyze_experiment.py --propose-auto '{...}'`
   7. Commit changes to the machinelearning repo"
3. If no briefs, skip silently

## Task 3: Phase 3 Iteration Chain Gate

Manage the interleaved Phase 3 iteration chain between main and analysis pipelines.

1. Check if analysis Phase 2 is complete (gate for all Phase 3 work):
   - `belam pipeline v4-deep-analysis` → must show `analysis_phase2_complete`
   - If not complete: skip all Phase 3 work silently
2. If gate is open, check iteration chain state:
   - Find the latest main pipeline Phase 3 iteration ID (from `pipelines/v4.md` iteration log)
   - Check if there are pending/in-progress analysis Phase 3 iterations for that main iteration
   - **If analysis iterations are pending/in-progress:** do NOT spawn new main iterations — wait
   - **If all analysis iterations for current main iter are complete AND none pending:** next main iteration is eligible
3. Check for Phase 3 proposals (`*phase3*proposal*.md`):
   - `status: approved` + chain clear → spawn builder agent
   - `status: pending_review` → alert Shael with hypothesis + score
4. If no proposals or chain is blocked, skip silently

## Task 4: Pipeline Archival

1. `python3 scripts/launch_pipeline.py --list`
2. For any pipeline at `phase2_complete` or `phase3_complete`:
   - `python3 scripts/launch_pipeline.py <version> --check-archive`
   - If archivable → auto-archive with `--archive`
3. Skip silently if nothing to archive

## Task 5: Git Commits

1. `cd machinelearning && git status --short`
2. If uncommitted changes: `git add -A && git commit -m "Auto-commit: research updates" && git push origin`
3. Skip silently if clean

## Task 6: Memory Maintenance

1. `python3 scripts/consolidate_memories.py --check 2>/dev/null`
2. If entries need consolidation, run `python3 scripts/consolidate_memories.py`
3. Skip silently if nothing to consolidate

## Task 7: Agent Conversation Export

1. `python3 scripts/export_agent_conversations.py --since 2`
2. Skip silently if no new conversations

---

## Completed Tasks (Archive)

### ~~Task: Monitor SNN Standard Model Experiments~~
✅ **COMPLETED 2026-03-12 23:58 UTC** — All 26 experiments finished (0 failures). Report synthesis complete.
