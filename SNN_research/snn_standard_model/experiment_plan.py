"""
Master experiment plan for all phases.
Returns a list of ExperimentConfig objects for everything that needs to run.
Checks existing results to skip completed experiments.
"""

import os
import sys
import glob
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment_infrastructure import ExperimentConfig

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments")


def get_completed_ids():
    """Return set of experiment_ids already completed."""
    done = set()
    for f in glob.glob(os.path.join(RESULTS_DIR, "*.json")):
        try:
            with open(f) as fh:
                d = json.load(fh)
            done.add(d["config"]["experiment_id"])
        except Exception:
            pass
    return done


def phase2_configs():
    """Phase 2: Synaptic neuron — alpha-beta grid search + extras."""
    configs = []

    # S1: Alpha-Beta grid search (rate coding, 25 steps)
    alphas = [0.3, 0.5, 0.8, 0.95]
    betas = [0.5, 0.8, 0.95, 0.99]
    for alpha in alphas:
        for beta in betas:
            configs.append(ExperimentConfig(
                experiment_id=f"syn_a{alpha}_b{beta}_steps25",
                neuron_model="Synaptic",
                dataset="MNIST",
                encoding="rate",
                beta=beta,
                alpha=alpha,
                num_steps=25,
                threshold=1.0,
                reset_mechanism="subtract",
                batch_size=128,
                lr=5e-4,
                num_epochs=1,
                hidden_size=1000,
                seed=42,
            ))

    # S2: Learnable alpha and beta
    for init_alpha, init_beta in [(0.5, 0.5), (0.3, 0.8), (0.8, 0.8)]:
        configs.append(ExperimentConfig(
            experiment_id=f"syn_learn_a{init_alpha}_b{init_beta}",
            neuron_model="Synaptic",
            dataset="MNIST",
            encoding="rate",
            beta=init_beta,
            alpha=init_alpha,
            num_steps=25,
            threshold=1.0,
            reset_mechanism="subtract",
            learn_beta=True,
            learn_alpha=True,
            batch_size=128,
            lr=5e-4,
            num_epochs=5,
            hidden_size=1000,
            seed=42,
        ))

    # S3: Alpha -> 0 verification
    for alpha in [0.01, 0.05, 0.1]:
        configs.append(ExperimentConfig(
            experiment_id=f"syn_alpha_zero_a{alpha}_b0.8",
            neuron_model="Synaptic",
            dataset="MNIST",
            encoding="rate",
            beta=0.8,
            alpha=alpha,
            num_steps=25,
            threshold=1.0,
            reset_mechanism="subtract",
            batch_size=128,
            lr=5e-4,
            num_epochs=1,
            hidden_size=1000,
            seed=42,
        ))

    return configs


def phase3_configs():
    """Phase 3: Alpha neuron baseline + cross-model + Fashion-MNIST."""
    configs = []

    # A1: Alpha neuron parameter sweep
    # snnTorch constraint: alpha MUST be > beta for Alpha neuron
    alpha_beta_pairs = [
        (0.8, 0.5), (0.8, 0.7),
        (0.9, 0.5), (0.9, 0.7), (0.9, 0.8),
        (0.95, 0.5), (0.95, 0.7), (0.95, 0.8), (0.95, 0.9),
        (0.99, 0.5), (0.99, 0.8), (0.99, 0.9), (0.99, 0.95),
    ]
    for alpha, beta in alpha_beta_pairs:
        configs.append(ExperimentConfig(
            experiment_id=f"alpha_a{alpha}_b{beta}_steps25",
            neuron_model="Alpha",
            dataset="MNIST",
            encoding="rate",
            beta=beta,
            alpha=alpha,
            num_steps=25,
            threshold=1.0,
            reset_mechanism="subtract",
            batch_size=128,
            lr=5e-4,
            num_epochs=1,
            hidden_size=1000,
            seed=42,
        ))

    # A3: Fashion-MNIST with best configs from each model type
    # Leaky best: beta=0.99, steps=25
    configs.append(ExperimentConfig(
        experiment_id="fashion_leaky_b0.99_steps25",
        neuron_model="Leaky",
        dataset="FashionMNIST",
        encoding="rate",
        beta=0.99,
        num_steps=25,
        threshold=1.0,
        reset_mechanism="subtract",
        batch_size=128,
        lr=5e-4,
        num_epochs=1,
        hidden_size=1000,
        seed=42,
    ))
    configs.append(ExperimentConfig(
        experiment_id="fashion_leaky_b0.8_steps25",
        neuron_model="Leaky",
        dataset="FashionMNIST",
        encoding="rate",
        beta=0.8,
        num_steps=25,
        threshold=1.0,
        reset_mechanism="subtract",
        batch_size=128,
        lr=5e-4,
        num_epochs=1,
        hidden_size=1000,
        seed=42,
    ))

    # Synaptic on Fashion-MNIST (placeholder — will use best from Phase 2)
    for alpha, beta in [(0.5, 0.95), (0.8, 0.99), (0.3, 0.8)]:
        configs.append(ExperimentConfig(
            experiment_id=f"fashion_syn_a{alpha}_b{beta}",
            neuron_model="Synaptic",
            dataset="FashionMNIST",
            encoding="rate",
            beta=beta,
            alpha=alpha,
            num_steps=25,
            threshold=1.0,
            reset_mechanism="subtract",
            batch_size=128,
            lr=5e-4,
            num_epochs=1,
            hidden_size=1000,
            seed=42,
        ))

    # Alpha on Fashion-MNIST (alpha must be > beta)
    for alpha, beta in [(0.95, 0.8), (0.99, 0.8), (0.99, 0.9)]:
        configs.append(ExperimentConfig(
            experiment_id=f"fashion_alpha_a{alpha}_b{beta}",
            neuron_model="Alpha",
            dataset="FashionMNIST",
            encoding="rate",
            beta=beta,
            alpha=alpha,
            num_steps=25,
            threshold=1.0,
            reset_mechanism="subtract",
            batch_size=128,
            lr=5e-4,
            num_epochs=1,
            hidden_size=1000,
            seed=42,
        ))

    return configs


def get_all_remaining():
    """Return list of (phase_name, config) for all incomplete experiments."""
    completed = get_completed_ids()

    remaining = []
    for phase_name, configs in [("Phase 2", phase2_configs()), ("Phase 3", phase3_configs())]:
        for cfg in configs:
            if cfg.experiment_id not in completed:
                remaining.append((phase_name, cfg))

    return remaining


def get_status():
    """Return a summary dict of what's done and what's pending."""
    completed = get_completed_ids()
    p2 = phase2_configs()
    p3 = phase3_configs()

    p2_done = sum(1 for c in p2 if c.experiment_id in completed)
    p3_done = sum(1 for c in p3 if c.experiment_id in completed)

    return {
        "phase1": {"total": 49, "done": 49, "status": "COMPLETE"},
        "phase2": {"total": len(p2), "done": p2_done, "status": "COMPLETE" if p2_done == len(p2) else "IN_PROGRESS" if p2_done > 0 else "PENDING"},
        "phase3": {"total": len(p3), "done": p3_done, "status": "COMPLETE" if p3_done == len(p3) else "IN_PROGRESS" if p3_done > 0 else "PENDING"},
    }


if __name__ == "__main__":
    status = get_status()
    print("=== Experiment Status ===")
    for phase, info in status.items():
        print(f"  {phase}: {info['done']}/{info['total']} ({info['status']})")

    remaining = get_all_remaining()
    print(f"\nTotal remaining: {remaining.__len__()} experiments")
    if remaining:
        print("\nNext 5:")
        for phase, cfg in remaining[:5]:
            print(f"  [{phase}] {cfg.experiment_id} — {cfg.neuron_model} alpha={cfg.alpha} beta={cfg.beta}")
