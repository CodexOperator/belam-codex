"""
Resume Phase 1.2 beta sweep — skips already-completed experiments.
"""
import sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment_infrastructure import (
    ExperimentConfig, train_and_evaluate, save_result, load_result, compare_results,
)

BETAS = [0.5, 0.7, 0.8, 0.9, 0.95, 0.99]
NUM_STEPS_LIST = [25, 50, 100]
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments")

def get_completed():
    """Return set of (beta, num_steps) already done."""
    done = set()
    for f in glob.glob(os.path.join(RESULTS_DIR, "*.json")):
        with open(f) as fh:
            d = json.load(fh)
        c = d["config"]
        if c["neuron_model"] == "Leaky" and c["encoding"] == "rate":
            done.add((c["beta"], c["num_steps"]))
    return done

def main():
    completed = get_completed()
    print(f"Already completed: {len(completed)} configs")
    
    all_configs = [(b, ns) for b in BETAS for ns in NUM_STEPS_LIST]
    remaining = [(b, ns) for b, ns in all_configs if (b, ns) not in completed]
    print(f"Remaining: {len(remaining)} configs\n")
    
    results = []
    for i, (beta, num_steps) in enumerate(remaining):
        exp_id = f"beta{beta}_steps{num_steps}"
        print(f"[{i+1}/{len(remaining)}] Running: beta={beta}, num_steps={num_steps}")
        
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
        print(f"  → test_acc={result.final_test_acc:.4f}  wall_clock={result.wall_clock_time:.1f}s\n")
    
    # Load ALL results for final summary
    all_results = []
    for f in sorted(glob.glob(os.path.join(RESULTS_DIR, "*.json"))):
        all_results.append(load_result(f))
    
    # Filter to just rate-coded Leaky
    rate_results = [r for r in all_results if r.config.neuron_model == "Leaky" and r.config.encoding == "rate"]
    
    print("\n" + "=" * 80)
    print("PHASE 1.2 — Full Beta Sweep Summary (Rate Coding, MNIST, 1 epoch)")
    print("=" * 80)
    df = compare_results(rate_results)
    df = df.sort_values(["num_steps", "beta"])
    print(df[["experiment_id", "beta", "num_steps",
              "final_train_acc", "final_test_acc",
              "best_test_acc", "wall_clock_s"]].to_string(index=False))
    print("=" * 80)

if __name__ == "__main__":
    main()
