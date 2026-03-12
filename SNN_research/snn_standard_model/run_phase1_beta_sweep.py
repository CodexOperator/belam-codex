"""
Task 1.2 — Leaky Beta Sweep (Rate Coding) on MNIST
Sweeps beta × num_steps with 1 epoch each, saves results incrementally.
"""

import sys
import os

# Ensure the module can be imported when run from this directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment_infrastructure import (
    ExperimentConfig, ExperimentResult,
    train_and_evaluate, save_result, load_result, compare_results,
)

BETAS = [0.5, 0.7, 0.8, 0.9, 0.95, 0.99]
NUM_STEPS_LIST = [25, 50, 100]
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments")


def main():
    results = []
    total = len(BETAS) * len(NUM_STEPS_LIST)
    idx = 0

    for beta in BETAS:
        for num_steps in NUM_STEPS_LIST:
            idx += 1
            exp_id = f"beta{beta}_steps{num_steps}"
            print(f"\n[{idx}/{total}] Running: beta={beta}, num_steps={num_steps}")

            config = ExperimentConfig(
                experiment_id=exp_id,
                neuron_model="Leaky",
                dataset="MNIST",
                encoding="rate",
                beta=beta,
                num_steps=num_steps,
                threshold=1.0,
                reset_mechanism="subtract",
                learn_beta=False,
                learn_alpha=False,
                inhibition=False,
                batch_size=128,
                lr=5e-4,
                optimizer_name="Adam",
                num_epochs=1,
                hidden_size=1000,
                seed=42,
            )

            result = train_and_evaluate(config)
            path = save_result(result, directory=RESULTS_DIR)
            results.append(result)
            print(f"  → test_acc={result.final_test_acc:.4f}  "
                  f"wall_clock={result.wall_clock_time:.1f}s  saved={os.path.basename(path)}")

    # Summary table
    print("\n" + "=" * 80)
    print("PHASE 1.2 — Beta Sweep Summary (Rate Coding, MNIST, 1 epoch)")
    print("=" * 80)
    df = compare_results(results)
    # Reorder for readability
    df = df.sort_values(["num_steps", "beta"])
    print(df[["experiment_id", "beta", "num_steps",
              "final_train_acc", "final_test_acc",
              "best_test_acc", "wall_clock_s"]].to_string(index=False))
    print("=" * 80)


if __name__ == "__main__":
    main()
