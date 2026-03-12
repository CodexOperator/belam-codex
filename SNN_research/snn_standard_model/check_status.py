#!/usr/bin/env python3
"""Quick status check for the experiment runner. Exit codes:
  0 = running or finished successfully
  1 = error
Output: one-line summary suitable for heartbeat reporting.
"""
import json
import os
import sys

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runner_state.json")

def main():
    if not os.path.exists(STATE_FILE):
        print("NO_RUNNER: No experiment runner state found")
        return

    with open(STATE_FILE) as f:
        state = json.load(f)

    status = state.get("status", "unknown")
    completed = len(state.get("completed", []))
    failed = len(state.get("failed", []))
    total = state.get("total_remaining_at_start", 0)
    current = state.get("current")

    if status == "finished":
        # Get last few results for summary
        last_results = state.get("completed", [])[-3:]
        accs = [f"{r['experiment_id']}={r['test_acc']}" for r in last_results]
        print(f"FINISHED: {completed}/{total} done, {failed} failed. Last: {', '.join(accs)}")
    elif status == "running":
        cur_info = ""
        if current:
            cur_info = f" Now: {current['experiment_id']} ({current['index']}/{current['total']})"
        recent = state.get("completed", [])[-1:] 
        recent_info = ""
        if recent:
            r = recent[0]
            recent_info = f" Last: {r['experiment_id']}={r['test_acc']}"
        print(f"RUNNING: {completed}/{total} done, {failed} failed.{cur_info}{recent_info}")
    elif status == "all_complete":
        print("ALL_COMPLETE: All experiments were already done before runner started")
    else:
        print(f"UNKNOWN: status={status}, completed={completed}, failed={failed}")


if __name__ == "__main__":
    main()
