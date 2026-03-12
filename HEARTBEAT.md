# HEARTBEAT.md — Autonomous Experiment Monitor

## Task: Monitor SNN Experiments

Check the experiment runner status and report progress:

1. Read `SNN_research/snn_standard_model/runner_state.json`
2. If `status` is `"running"`:
   - Report how many completed vs total
   - Check for failures — if any new failures, alert the user
   - Reply HEARTBEAT_OK if things are progressing normally
3. If `status` is `"finished"`:
   - Report final results summary to the user (completed count, failed count)
   - Spawn a sub-agent with task: "Read SNN_research/snn_standard_model/runner_state.json and all JSON files in SNN_research/snn_standard_model/experiments/. Update SNN_research/snn_standard_model/reports/SNN_Progress_Report.md with Phase 2 and Phase 3 results. Fill in all PENDING tables. Write analysis comparing Synaptic and Alpha models to the Leaky baseline. Commit changes."
   - After spawning, clear this task from HEARTBEAT.md (replace with comment-only version)
4. If `runner_state.json` doesn't exist:
   - Check `SNN_research/snn_standard_model/experiment_plan.py --status` to see if experiments remain
   - If remaining > 0: run `cd SNN_research/snn_standard_model && nohup python3 run_all_remaining.py > runner_output.log 2>&1 &` to restart
   - If remaining == 0: all done, clear this task
