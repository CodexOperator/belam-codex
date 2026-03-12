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

## Task 2: Periodic Git Commits

Check for uncommitted changes in the machinelearning repo:

1. Run `cd SNN_research/machinelearning && git status --short`
2. If there are new/modified files:
   - `git add -A && git commit -m "Auto-commit: experiment results and research updates" && git push origin`
3. If no changes, skip silently.
