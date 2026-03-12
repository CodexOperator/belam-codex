"""
Task 1.1 — Experiment Infrastructure for SNN Standard Model Research
Provides ExperimentConfig, ExperimentResult, model building, training, and result management.
"""

import os
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

import snntorch as snn
from snntorch import spikegen, utils as snn_utils


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExperimentConfig:
    experiment_id: str = ""
    neuron_model: str = "Leaky"          # Leaky | Synaptic | Alpha
    dataset: str = "MNIST"               # MNIST | FashionMNIST
    encoding: str = "rate"               # rate | latency
    beta: float = 0.8
    alpha: Optional[float] = None        # only for Synaptic / Alpha
    num_steps: int = 25
    threshold: float = 1.0
    reset_mechanism: str = "subtract"
    learn_beta: bool = False
    learn_alpha: bool = False
    inhibition: bool = False
    batch_size: int = 128
    lr: float = 5e-4
    optimizer_name: str = "Adam"
    num_epochs: int = 1
    hidden_size: int = 1000
    seed: int = 42
    tau: float = 5.0                     # for latency encoding
    latency_linear: bool = False         # linear vs exponential latency

    def __post_init__(self):
        if not self.experiment_id:
            self.experiment_id = uuid.uuid4().hex[:8]


@dataclass
class ExperimentResult:
    config: ExperimentConfig
    final_train_acc: float = 0.0
    final_test_acc: float = 0.0
    best_test_acc: float = 0.0
    best_test_epoch: int = 0
    per_layer_spike_density: Dict[str, float] = field(default_factory=dict)
    per_layer_mem_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    loss_curve: List[float] = field(default_factory=list)
    accuracy_curve: List[float] = field(default_factory=list)
    wall_clock_time: float = 0.0
    avg_epoch_time: float = 0.0
    learned_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _result_to_dict(result: ExperimentResult) -> dict:
    d = asdict(result)
    return d


def save_result(result: ExperimentResult, directory: str = "experiments/") -> str:
    os.makedirs(directory, exist_ok=True)
    c = result.config
    fname = f"{c.experiment_id}_{c.neuron_model}_{c.dataset}_{result.timestamp}.json"
    path = os.path.join(directory, fname)
    with open(path, "w") as f:
        json.dump(_result_to_dict(result), f, indent=2)
    return path


def load_result(filepath: str) -> ExperimentResult:
    with open(filepath) as f:
        d = json.load(f)
    cfg = ExperimentConfig(**d.pop("config"))
    return ExperimentResult(config=cfg, **d)


def compare_results(results: List[ExperimentResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append({
            "experiment_id": r.config.experiment_id,
            "neuron_model": r.config.neuron_model,
            "dataset": r.config.dataset,
            "encoding": r.config.encoding,
            "beta": r.config.beta,
            "num_steps": r.config.num_steps,
            "num_epochs": r.config.num_epochs,
            "hidden_size": r.config.hidden_size,
            "final_train_acc": round(r.final_train_acc, 4),
            "final_test_acc": round(r.final_test_acc, 4),
            "best_test_acc": round(r.best_test_acc, 4),
            "best_test_epoch": r.best_test_epoch,
            "wall_clock_s": round(r.wall_clock_time, 1),
            "avg_epoch_s": round(r.avg_epoch_time, 1),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Model builder
# ---------------------------------------------------------------------------

def build_snn_model(config: ExperimentConfig) -> nn.Sequential:
    """Build a 784 → hidden → 10 SNN with the specified neuron model."""
    neuron_cls = config.neuron_model.lower()

    common_kw = dict(
        beta=config.beta,
        threshold=config.threshold,
        reset_mechanism=config.reset_mechanism,
        init_hidden=True,
    )

    if neuron_cls == "leaky":
        common_kw["learn_beta"] = config.learn_beta
        layers = [
            nn.Flatten(),
            nn.Linear(784, config.hidden_size),
            snn.Leaky(**common_kw),
            nn.Linear(config.hidden_size, 10),
            snn.Leaky(**common_kw, output=True),
        ]
    elif neuron_cls == "synaptic":
        common_kw["alpha"] = config.alpha if config.alpha is not None else 0.5
        common_kw["learn_beta"] = config.learn_beta
        common_kw["learn_alpha"] = config.learn_alpha
        layers = [
            nn.Flatten(),
            nn.Linear(784, config.hidden_size),
            snn.Synaptic(**common_kw),
            nn.Linear(config.hidden_size, 10),
            snn.Synaptic(**common_kw, output=True),
        ]
    elif neuron_cls == "alpha":
        common_kw["alpha"] = config.alpha if config.alpha is not None else 0.5
        common_kw["learn_beta"] = config.learn_beta
        common_kw["learn_alpha"] = config.learn_alpha
        layers = [
            nn.Flatten(),
            nn.Linear(784, config.hidden_size),
            snn.Alpha(**common_kw),
            nn.Linear(config.hidden_size, 10),
            snn.Alpha(**common_kw, output=True),
        ]
    else:
        raise ValueError(f"Unknown neuron model: {config.neuron_model}")

    return nn.Sequential(*layers)


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _get_dataloaders(config: ExperimentConfig):
    transform = transforms.Compose([
        transforms.Resize((28, 28)),
        transforms.Grayscale(),
        transforms.ToTensor(),
        transforms.Normalize((0,), (1,)),
    ])

    ds_cls = datasets.MNIST if config.dataset == "MNIST" else datasets.FashionMNIST
    data_root = os.path.expanduser("~/.cache/torchvision")

    train_ds = ds_cls(data_root, train=True, download=True, transform=transform)
    test_ds = ds_cls(data_root, train=False, download=True, transform=transform)

    train_loader = DataLoader(train_ds, batch_size=config.batch_size, shuffle=True,
                              drop_last=True, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=config.batch_size, shuffle=False,
                             drop_last=True, num_workers=0)
    return train_loader, test_loader


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def _encode_batch(data: torch.Tensor, config: ExperimentConfig) -> torch.Tensor:
    """Returns spike tensor of shape [num_steps, batch, ...]."""
    if config.encoding == "rate":
        return spikegen.rate(data, num_steps=config.num_steps)
    elif config.encoding == "latency":
        return spikegen.latency(data, num_steps=config.num_steps,
                                tau=config.tau, threshold=0.01,
                                linear=config.latency_linear,
                                normalize=True)
    else:
        raise ValueError(f"Unknown encoding: {config.encoding}")


# ---------------------------------------------------------------------------
# Training & evaluation
# ---------------------------------------------------------------------------

def train_and_evaluate(config: ExperimentConfig) -> ExperimentResult:
    """Full training loop. Returns populated ExperimentResult."""

    # Seeds
    torch.manual_seed(config.seed)
    np.random.seed(config.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Data
    train_loader, test_loader = _get_dataloaders(config)

    # Model
    model = build_snn_model(config).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.lr, betas=(0.9, 0.999))
    criterion = nn.CrossEntropyLoss()

    result = ExperimentResult(config=config)
    epoch_times = []

    for epoch in range(config.num_epochs):
        t0 = time.time()

        # ---- TRAIN ----
        model.train()
        train_correct = 0
        train_total = 0
        epoch_loss = 0.0
        num_batches = 0

        # accumulators for spike density / membrane stats (last epoch only)
        spk_counts = {"hidden": 0.0, "output": 0.0}
        spk_elements = {"hidden": 0, "output": 0}
        mem_sums = {"hidden": 0.0, "output": 0.0}
        mem_sq_sums = {"hidden": 0.0, "output": 0.0}
        mem_elements = {"hidden": 0, "output": 0}

        for data, targets in train_loader:
            data, targets = data.to(device), targets.to(device)
            spike_data = _encode_batch(data, config)  # [T, B, 1, 28, 28]

            # Reset hidden states
            snn_utils.reset(model)

            # Forward pass over timesteps — manual layer-by-layer to capture hidden spikes
            # Model layers: [0]=Flatten, [1]=Linear, [2]=Leaky(hidden), [3]=Linear, [4]=Leaky(output)
            mem_out_acc = torch.zeros(config.batch_size, 10, device=device)
            spk_hidden_acc = []
            mem_hidden_acc = []
            spk_out_acc = []
            mem_out_list = []

            for step in range(config.num_steps):
                x = spike_data[step]
                x = model[0](x)              # Flatten
                x = model[1](x)              # Linear(784 -> hidden)
                spk_h = model[2](x)          # hidden (init_hidden=True → returns spk only)
                mem_h = model[2].mem          # access membrane after forward
                x = model[3](spk_h)          # Linear(hidden -> 10)
                out = model[4](x)            # output=True → returns tuple
                # Leaky: (spk, mem), Synaptic: (spk, syn, mem), Alpha: (spk, syn_exc, syn_inh, mem)
                spk_out = out[0]
                mem_out = out[-1]            # mem is always last
                mem_out_acc += mem_out
                spk_hidden_acc.append(spk_h.detach())
                mem_hidden_acc.append(mem_h.detach())
                spk_out_acc.append(spk_out.detach())
                mem_out_list.append(mem_out.detach())

            # Loss on summed membrane potential
            loss = criterion(mem_out_acc, targets)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            # Accuracy
            preds = mem_out_acc.argmax(dim=1)
            train_correct += (preds == targets).sum().item()
            train_total += targets.size(0)
            epoch_loss += loss.item()
            num_batches += 1

            # Spike / membrane stats (accumulate on last epoch to save compute)
            if epoch == config.num_epochs - 1:
                sh = torch.stack(spk_hidden_acc)  # [T, B, hidden]
                so = torch.stack(spk_out_acc)      # [T, B, 10]
                mh = torch.stack(mem_hidden_acc)
                mo = torch.stack(mem_out_list)

                spk_counts["hidden"] += sh.sum().item()
                spk_elements["hidden"] += sh.numel()
                spk_counts["output"] += so.sum().item()
                spk_elements["output"] += so.numel()

                mem_sums["hidden"] += mh.sum().item()
                mem_sq_sums["hidden"] += (mh ** 2).sum().item()
                mem_elements["hidden"] += mh.numel()
                mem_sums["output"] += mo.sum().item()
                mem_sq_sums["output"] += (mo ** 2).sum().item()
                mem_elements["output"] += mo.numel()

        train_acc = train_correct / train_total if train_total > 0 else 0.0
        avg_loss = epoch_loss / max(num_batches, 1)

        # ---- TEST ----
        model.eval()
        test_correct = 0
        test_total = 0
        with torch.no_grad():
            for data, targets in test_loader:
                data, targets = data.to(device), targets.to(device)
                spike_data = _encode_batch(data, config)
                snn_utils.reset(model)
                mem_out_acc = torch.zeros(config.batch_size, 10, device=device)
                for step in range(config.num_steps):
                    out = model(spike_data[step])
                    # Leaky: (spk, mem), Synaptic: (spk, syn, mem), Alpha: (spk, syn_exc, syn_inh, mem)
                    mem_out = out[-1]
                    mem_out_acc += mem_out
                preds = mem_out_acc.argmax(dim=1)
                test_correct += (preds == targets).sum().item()
                test_total += targets.size(0)
        test_acc = test_correct / test_total if test_total > 0 else 0.0

        epoch_time = time.time() - t0
        epoch_times.append(epoch_time)

        result.loss_curve.append(avg_loss)
        result.accuracy_curve.append(test_acc)

        if test_acc > result.best_test_acc:
            result.best_test_acc = test_acc
            result.best_test_epoch = epoch

        # Record learned params
        if config.learn_beta or config.learn_alpha:
            ep_params = {}
            for name, param in model.named_parameters():
                if "beta" in name or "alpha" in name:
                    ep_params[name] = param.item() if param.numel() == 1 else param.tolist()
            result.learned_params[f"epoch_{epoch}"] = ep_params

        print(f"  Epoch {epoch+1}/{config.num_epochs} — "
              f"loss={avg_loss:.4f}  train_acc={train_acc:.4f}  "
              f"test_acc={test_acc:.4f}  time={epoch_time:.1f}s")

    # Finalize result
    result.final_train_acc = train_acc
    result.final_test_acc = test_acc
    result.wall_clock_time = sum(epoch_times)
    result.avg_epoch_time = np.mean(epoch_times) if epoch_times else 0.0

    # Spike density & membrane stats from last epoch
    for layer in ["hidden", "output"]:
        if spk_elements[layer] > 0:
            result.per_layer_spike_density[layer] = spk_counts[layer] / spk_elements[layer]
        n = mem_elements[layer]
        if n > 0:
            mean = mem_sums[layer] / n
            var = mem_sq_sums[layer] / n - mean ** 2
            result.per_layer_mem_stats[layer] = {"mean": mean, "var": max(var, 0.0)}

    return result
