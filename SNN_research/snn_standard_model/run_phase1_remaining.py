"""
Tasks 1.3–1.7: Latency coding, threshold sweep, reset mechanisms, learnable beta, inhibition.
Uses best beta from Phase 1.2 (beta=0.99, num_steps=25) as baseline.
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment_infrastructure import (
    ExperimentConfig, train_and_evaluate, save_result, load_result, compare_results,
)

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments")
os.makedirs(RESULTS_DIR, exist_ok=True)

BEST_BETA = 0.99
BEST_STEPS = 25

def already_done(exp_id):
    for f in glob.glob(os.path.join(RESULTS_DIR, f"{exp_id}_*.json")):
        return True
    return False

def run_config(config):
    if already_done(config.experiment_id):
        print(f"  SKIP (already done): {config.experiment_id}")
        return None
    result = train_and_evaluate(config)
    path = save_result(result, directory=RESULTS_DIR)
    print(f"  → test_acc={result.final_test_acc:.4f}  time={result.wall_clock_time:.1f}s")
    return result

all_results = []

# ========== Task 1.3: Latency Coding Sweep ==========
print("\n" + "="*60)
print("TASK 1.3: Latency Coding Sweep")
print("="*60)

for beta in [0.95, 0.99]:
    for tau in [1, 2, 5, 10, 20]:
        for linear in [False, True]:
            enc_label = "latency_linear" if linear else "latency_exp"
            exp_id = f"lat_beta{beta}_tau{tau}_{enc_label}_steps{BEST_STEPS}"
            print(f"\n[Task 1.3] beta={beta}, tau={tau}, linear={linear}")
            
            config = ExperimentConfig(
                experiment_id=exp_id,
                neuron_model="Leaky",
                dataset="MNIST",
                encoding="latency",
                beta=beta,
                num_steps=BEST_STEPS,
                threshold=1.0,
                reset_mechanism="subtract",
                batch_size=128,
                lr=5e-4,
                num_epochs=1,
                hidden_size=1000,
                seed=42,
                tau=tau,
                latency_linear=linear,
            )
            r = run_config(config)
            if r: all_results.append(r)

# ========== Task 1.4: Threshold Sensitivity ==========
print("\n" + "="*60)
print("TASK 1.4: Threshold Sensitivity Sweep")
print("="*60)

for thr in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
    exp_id = f"thr{thr}_beta{BEST_BETA}_steps{BEST_STEPS}"
    print(f"\n[Task 1.4] threshold={thr}")
    
    config = ExperimentConfig(
        experiment_id=exp_id,
        neuron_model="Leaky",
        dataset="MNIST",
        encoding="rate",
        beta=BEST_BETA,
        num_steps=BEST_STEPS,
        threshold=thr,
        reset_mechanism="subtract",
        batch_size=128,
        lr=5e-4,
        num_epochs=1,
        hidden_size=1000,
        seed=42,
    )
    r = run_config(config)
    if r: all_results.append(r)

# ========== Task 1.5: Reset Mechanism Comparison ==========
print("\n" + "="*60)
print("TASK 1.5: Reset Mechanism Comparison")
print("="*60)

for reset in ["subtract", "zero", "none"]:
    exp_id = f"reset_{reset}_beta{BEST_BETA}_steps{BEST_STEPS}"
    print(f"\n[Task 1.5] reset_mechanism={reset}")
    
    config = ExperimentConfig(
        experiment_id=exp_id,
        neuron_model="Leaky",
        dataset="MNIST",
        encoding="rate",
        beta=BEST_BETA,
        num_steps=BEST_STEPS,
        threshold=1.0,
        reset_mechanism=reset,
        batch_size=128,
        lr=5e-4,
        num_epochs=1,
        hidden_size=1000,
        seed=42,
    )
    r = run_config(config)
    if r: all_results.append(r)

# ========== Task 1.6: Learnable Beta ==========
print("\n" + "="*60)
print("TASK 1.6: Learnable Beta (3 epochs to track evolution)")
print("="*60)

exp_id = f"learn_beta_steps{BEST_STEPS}"
print(f"\n[Task 1.6] learn_beta=True, 3 epochs")

config = ExperimentConfig(
    experiment_id=exp_id,
    neuron_model="Leaky",
    dataset="MNIST",
    encoding="rate",
    beta=BEST_BETA,
    num_steps=BEST_STEPS,
    threshold=1.0,
    reset_mechanism="subtract",
    learn_beta=True,
    batch_size=128,
    lr=5e-4,
    num_epochs=3,
    hidden_size=1000,
    seed=42,
)
r = run_config(config)
if r: all_results.append(r)

# ========== Task 1.7: Inhibition Mode ==========
print("\n" + "="*60)
print("TASK 1.7: Inhibition Mode")
print("="*60)

exp_id = f"inhibition_beta{BEST_BETA}_steps{BEST_STEPS}"
print(f"\n[Task 1.7] inhibition=True")

config = ExperimentConfig(
    experiment_id=exp_id,
    neuron_model="Leaky",
    dataset="MNIST",
    encoding="rate",
    beta=BEST_BETA,
    num_steps=BEST_STEPS,
    threshold=1.0,
    reset_mechanism="subtract",
    inhibition=True,
    batch_size=128,
    lr=5e-4,
    num_epochs=1,
    hidden_size=1000,
    seed=42,
)
r = run_config(config)
if r: all_results.append(r)

# ========== Summary ==========
print("\n" + "="*70)
print("PHASE 1 REMAINING TASKS — SUMMARY")
print("="*70)
for r in all_results:
    c = r.config
    print(f"  {c.experiment_id:45s}  test_acc={r.final_test_acc:.4f}  time={r.wall_clock_time:.1f}s")
print("="*70)
print(f"Total experiments completed this run: {len(all_results)}")
