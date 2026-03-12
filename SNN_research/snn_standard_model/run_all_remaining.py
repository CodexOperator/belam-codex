#!/usr/bin/env python3
"""
Run ALL remaining experiments sequentially.
Designed to run as a background process. Saves progress to a state file
that the heartbeat can monitor.
"""

import sys
import os
import json
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment_infrastructure import train_and_evaluate, save_result
from experiment_plan import get_all_remaining, get_status, RESULTS_DIR

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runner_state.json")


def update_state(state):
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def main():
    state = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "completed": [],
        "failed": [],
        "current": None,
        "total_remaining_at_start": 0,
    }

    remaining = get_all_remaining()
    state["total_remaining_at_start"] = len(remaining)
    update_state(state)

    if not remaining:
        state["status"] = "all_complete"
        update_state(state)
        print("✅ ALL EXPERIMENTS ALREADY COMPLETE!")
        return

    print(f"Starting {len(remaining)} experiments...")
    print("=" * 60)

    for i, (phase, config) in enumerate(remaining):
        state["current"] = {
            "index": i + 1,
            "total": len(remaining),
            "experiment_id": config.experiment_id,
            "phase": phase,
            "model": config.neuron_model,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        update_state(state)

        print(f"\n[{i+1}/{len(remaining)}] {phase} — {config.experiment_id}")
        print(f"  Model={config.neuron_model} alpha={config.alpha} beta={config.beta} "
              f"steps={config.num_steps} epochs={config.num_epochs}")

        t0 = time.time()
        try:
            result = train_and_evaluate(config)
            path = save_result(result, directory=RESULTS_DIR)
            elapsed = time.time() - t0

            state["completed"].append({
                "experiment_id": config.experiment_id,
                "phase": phase,
                "test_acc": round(result.final_test_acc, 4),
                "time": round(elapsed, 1),
            })
            print(f"  ✅ test_acc={result.final_test_acc:.4f} time={elapsed:.1f}s")

        except Exception as e:
            elapsed = time.time() - t0
            state["failed"].append({
                "experiment_id": config.experiment_id,
                "phase": phase,
                "error": str(e),
                "time": round(elapsed, 1),
            })
            print(f"  ❌ FAILED: {e}")

        update_state(state)

    state["status"] = "finished"
    state["current"] = None
    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    update_state(state)

    # Final summary
    print("\n" + "=" * 60)
    print("ALL EXPERIMENTS COMPLETE")
    print(f"  ✅ Completed: {len(state['completed'])}")
    print(f"  ❌ Failed: {len(state['failed'])}")

    final_status = get_status()
    for phase, info in final_status.items():
        print(f"  {phase}: {info['done']}/{info['total']} ({info['status']})")


if __name__ == "__main__":
    main()
