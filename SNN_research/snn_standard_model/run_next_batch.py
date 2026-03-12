#!/usr/bin/env python3
"""
Run the next batch of experiments from the master plan.
Designed to be called repeatedly — skips completed experiments automatically.

Usage:
    python run_next_batch.py [--max N]   # run at most N experiments (default: 5)
    python run_next_batch.py --status     # just print status
"""

import sys
import os
import argparse
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment_infrastructure import train_and_evaluate, save_result
from experiment_plan import get_all_remaining, get_status, RESULTS_DIR


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=5, help="Max experiments to run this batch")
    parser.add_argument("--status", action="store_true", help="Just print status and exit")
    args = parser.parse_args()

    status = get_status()
    print("=== Experiment Status ===")
    for phase, info in status.items():
        print(f"  {phase}: {info['done']}/{info['total']} ({info['status']})")

    if args.status:
        remaining = get_all_remaining()
        print(f"\nRemaining: {len(remaining)} experiments")
        return

    remaining = get_all_remaining()
    if not remaining:
        print("\n✅ ALL EXPERIMENTS COMPLETE!")
        return

    batch = remaining[:args.max]
    print(f"\nRunning batch of {len(batch)} experiments ({len(remaining)} total remaining)...")
    print("=" * 60)

    results_summary = []
    for i, (phase, config) in enumerate(batch):
        print(f"\n[{i+1}/{len(batch)}] {phase} — {config.experiment_id}")
        print(f"  Model={config.neuron_model} alpha={config.alpha} beta={config.beta} "
              f"steps={config.num_steps} epochs={config.num_epochs}")

        t0 = time.time()
        try:
            result = train_and_evaluate(config)
            path = save_result(result, directory=RESULTS_DIR)
            elapsed = time.time() - t0
            summary = {
                "experiment_id": config.experiment_id,
                "phase": phase,
                "test_acc": round(result.final_test_acc, 4),
                "time": round(elapsed, 1),
                "status": "OK",
            }
            results_summary.append(summary)
            print(f"  ✅ test_acc={result.final_test_acc:.4f} time={elapsed:.1f}s → {os.path.basename(path)}")
        except Exception as e:
            elapsed = time.time() - t0
            summary = {
                "experiment_id": config.experiment_id,
                "phase": phase,
                "error": str(e),
                "time": round(elapsed, 1),
                "status": "FAILED",
            }
            results_summary.append(summary)
            print(f"  ❌ FAILED: {e}")

    # Final summary
    print("\n" + "=" * 60)
    print("BATCH COMPLETE")
    print("=" * 60)
    for s in results_summary:
        if s["status"] == "OK":
            print(f"  ✅ {s['experiment_id']}: test_acc={s['test_acc']} time={s['time']}s")
        else:
            print(f"  ❌ {s['experiment_id']}: {s['error']}")

    # Updated status
    new_status = get_status()
    new_remaining = get_all_remaining()
    print(f"\nRemaining after this batch: {len(new_remaining)} experiments")
    for phase, info in new_status.items():
        print(f"  {phase}: {info['done']}/{info['total']} ({info['status']})")


if __name__ == "__main__":
    main()
