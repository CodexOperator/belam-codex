# HEARTBEAT.md — Autonomous Experiment Monitor

## Task 1: Monitor SNN Experiments

✅ **COMPLETED 2026-03-12 23:58 UTC**
- All 26 experiments finished successfully (0 failures)
- Report synthesis agent spawned to update SNN_Progress_Report.md
- (Task archive below)

<!--
## COMPLETED TASK ARCHIVE

Check the experiment runner status and report progress:

1. Read `SNN_research/machinelearning/snn_standard_model/runner_state.json`
2. If `status` is `"running"`:
   - Report how many completed vs total
   - Check for failures — if any new failures, alert the user
   - Reply HEARTBEAT_OK if things are progressing normally
3. If `status` is `"finished"`:
   - Report final results summary to the user (completed count, failed count)
   - Spawn a sub-agent with task: "Read SNN_research/machinelearning/snn_standard_model/runner_state.json and all JSON files in SNN_research/machinelearning/snn_standard_model/experiments/. Update SNN_research/machinelearning/snn_standard_model/reports/SNN_Progress_Report.md with Phase 2 and Phase 3 results. Fill in all PENDING tables. Write analysis comparing Synaptic and Alpha models to the Leaky baseline. Commit changes to the machinelearning git repo."
   - After spawning, clear this task from HEARTBEAT.md (replace with comment-only version) ✅
4. If `runner_state.json` doesn't exist:
   - Check `SNN_research/machinelearning/snn_standard_model/experiment_plan.py --status` to see if experiments remain
   - If remaining > 0: run `cd SNN_research/machinelearning/snn_standard_model && nohup python3 run_all_remaining.py > runner_output.log 2>&1 &` to restart
   - If remaining == 0: all done, clear this task
-->

## Task 2: Review Open Tasks & Pipelines

Scan `tasks/` and `pipelines/` for open primitives:
1. Run `grep -l "status: open\|status: blocked" tasks/*.md 2>/dev/null`
2. Run `grep -l "status: phase1_\|status: phase2_" pipelines/*.md 2>/dev/null`
3. If any blocked tasks exist, alert the user with task name and blocker
4. If any active pipelines exist, report their current stage
5. Otherwise skip silently

## Task 3: Experiment Analysis Pipeline

Detect new experiment results and extract lessons:

1. Run `python3 /home/ubuntu/.openclaw/workspace/scripts/analyze_experiment.py --detect --quiet`
2. If briefs were generated, spawn a sub-agent with task:
   "Read all pending analysis briefs in SNN_research/machinelearning/snn_applied_finance/research/pipeline_output/ (files with 'status: pending_review'). For each brief:
   1. Read the code changes section carefully — these are Shael's manual tweaks and represent high-signal design decisions
   2. Read the results and analysis sections
   3. Create lesson primitives in workspace/lessons/ for significant findings
   4. Update research/TECHNIQUES_TRACKER.md with new results or status changes
   5. Update the brief's frontmatter to 'status: processed'
   6. If any finding changes architectural direction, update the relevant *_KNOWLEDGE.md file
   7. If the analysis reveals a compelling follow-up experiment worth pursuing (strong signal, clear hypothesis, high expected information gain), generate a Phase 3 proposal:
      python3 /home/ubuntu/.openclaw/workspace/scripts/analyze_experiment.py --propose-auto '{\"version\":\"<ver>\",\"id\":\"<next_id>\",\"hypothesis\":\"<what_to_test>\",\"justification\":\"<why_its_worth_gpu_time>\",\"score\":<1-10>,\"proposed_by\":\"<your_agent_role>\",\"gpu_min\":<estimated_minutes>,\"colab_code\":\"<optional_python_code>\"}'
      Score ≥ 7 = auto-approved, 4-6 = flagged for Shael, < 4 = rejected. Be honest with scores.
   8. Commit changes to the machinelearning repo"
3. If no briefs generated, skip silently

**Manual trigger:** Shael can also say "analyze [v2/v3/baseline]" to trigger analysis of a specific notebook immediately.

## Task 3b: Phase 3 Autonomous Research Gate

Check for pending Phase 3 proposals and auto-trigger approved iterations:

1. Run `ls /home/ubuntu/.openclaw/workspace/SNN_research/machinelearning/snn_applied_finance/research/pipeline_builds/*phase3*proposal*.md 2>/dev/null`
2. If proposals exist, check each for `status: approved` that hasn't been built yet:
   - Read the proposal file
   - Verify the pipeline's Phase 2 is complete: `python3 /home/ubuntu/.openclaw/workspace/scripts/analyze_experiment.py --check-gate <version>`
   - If gate is LOCKED: skip, do NOT build (Phase 2 must complete first)
   - If gate is OPEN and status is `approved`: spawn builder agent with the proposal
   - If status is `pending_review`: alert Shael with the hypothesis and justification score
3. If no proposals exist, skip silently

**Autonomous proposal generation:** During Task 3 analysis, if the analysis agent identifies a compelling follow-up experiment (justification ≥ 7), it may generate a Phase 3 proposal via:
```
python3 scripts/analyze_experiment.py --propose-auto '{"version":"v4","id":"01","hypothesis":"...","justification":"...","score":8,"proposed_by":"agent"}'
```
The gate check is enforced by the script — proposals cannot be created if Phase 2 isn't complete.

## Task 3c: Pipeline Archival Check

Check if any completed pipelines should be archived:

1. Run `python3 /home/ubuntu/.openclaw/workspace/scripts/launch_pipeline.py --list`
2. For any pipeline with status `phase2_complete` or `phase3_complete`:
   - Run `python3 /home/ubuntu/.openclaw/workspace/scripts/launch_pipeline.py <version> --check-archive`
   - If archivable (no pending phase 3 proposals): auto-archive with `--archive`
   - If not archivable: skip silently (pending iterations will be caught by Task 3b)
3. If no completed pipelines, skip silently

## Task 4: Export Agent Conversations

Export inter-agent conversation transcripts to readable logs:

1. Run `python3 /home/ubuntu/.openclaw/workspace/scripts/export_agent_conversations.py --since 2`
2. This exports conversations from the last 2 hours to `snn_applied_finance/conversations/`
3. Skip silently if no new conversations.

## Task 6: Memory Maintenance

Check if daily memory entries need consolidation:

1. Run `python3 /home/ubuntu/.openclaw/workspace/scripts/consolidate_memories.py --check 2>/dev/null`
2. If entries need consolidation (exit code 0 with output), run `python3 /home/ubuntu/.openclaw/workspace/scripts/consolidate_memories.py`
3. Skip silently if nothing to consolidate

## Task 5: Periodic Git Commits

Check for uncommitted changes in the machinelearning repo:

1. Run `cd SNN_research/machinelearning && git status --short`
2. If there are new/modified files:
   - `git add -A && git commit -m "Auto-commit: experiment results and research updates" && git push origin`
3. If no changes, skip silently.

## Task 6: Memory Maintenance

Check if daily memory entries need consolidation:

1. Run `python3 /home/ubuntu/.openclaw/workspace/scripts/consolidate_memories.py --check`
2. If entries need consolidation (exit code 1), run `python3 /home/ubuntu/.openclaw/workspace/scripts/consolidate_memories.py`
3. Skip silently if nothing to consolidate (exit code 0)
