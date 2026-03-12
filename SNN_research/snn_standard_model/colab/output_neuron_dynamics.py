#!/usr/bin/env python3
"""
Output Neuron Dynamics Visualization — SNN Evidence Accumulation
=================================================================
THE KEY VISUALIZATION: Shows how 10 output neurons accumulate membrane
potential (= evidence) over 25 time steps to make a classification decision.

This script:
  1. Trains a Leaky SNN on MNIST for 1 epoch (best config: beta=0.99, steps=25)
  2. Takes a single test image and runs it step-by-step
  3. Records membrane potential of ALL 10 output neurons at EACH time step
  4. Creates multi-panel visualization + animated version
  5. Exports per-step data as CSV

Dependencies:
    pip install torch torchvision snntorch matplotlib numpy pandas

What membrane potential MEANS (important!):
  - It is NOT a probability. It's accumulated electrical evidence.
  - Higher membrane = more input current pushed this neuron toward firing.
  - Think of it as a "vote counter" — each time step adds votes based on
    how well the input pattern matches this neuron's learned weights.
  - To get something probability-like, apply softmax to the final summed
    membrane potentials across the 10 neurons.
  - Raw values can be negative (net inhibitory input) or positive (net
    excitatory input). The RELATIVE ordering matters, not the absolute scale.
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ─── snnTorch imports ─────────────────────────────────────────────────────────
try:
    import snntorch as snn
    from snntorch import spikegen
    from snntorch import surrogate
except ImportError:
    print("Installing snntorch...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "snntorch"])
    import snntorch as snn
    from snntorch import spikegen
    from snntorch import surrogate

from torchvision import datasets, transforms
from torch.utils.data import DataLoader

# ─── Configuration ────────────────────────────────────────────────────────────
BETA = 0.99          # Membrane decay — best from Phase 1.2
NUM_STEPS = 25       # Time steps — best from Phase 1.2
BATCH_SIZE = 128
LR = 5e-4
EPOCHS = 1
HIDDEN_SIZE = 1000
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}")

# ─── Data Loading ─────────────────────────────────────────────────────────────
transform = transforms.Compose([
    transforms.Resize((28, 28)),
    transforms.Grayscale(),
    transforms.ToTensor(),
    transforms.Normalize((0,), (1,))
])

train_ds = datasets.MNIST(root="./data", train=True, download=True, transform=transform)
test_ds  = datasets.MNIST(root="./data", train=False, download=True, transform=transform)
train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)
test_loader  = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, drop_last=True)

# ─── Model Definition ─────────────────────────────────────────────────────────
class LeakySNN(nn.Module):
    """
    Two-layer fully-connected Leaky Integrate-and-Fire SNN.
    Architecture: 784 → 1000 (hidden, with spikes) → 10 (output, membrane readout)

    The output layer does NOT spike — we read raw membrane potential.
    Classification = argmax of SUMMED membrane potential over all time steps.
    """
    def __init__(self, beta=BETA):
        super().__init__()
        self.fc1 = nn.Linear(784, HIDDEN_SIZE)
        self.lif1 = snn.Leaky(beta=beta, spike_grad=surrogate.fast_sigmoid(slope=25))
        self.fc2 = nn.Linear(HIDDEN_SIZE, 10)
        self.lif2 = snn.Leaky(beta=beta, spike_grad=surrogate.fast_sigmoid(slope=25))

    def forward(self, x):
        """
        x: spike train tensor of shape (num_steps, batch, 784)
        Returns: (spike_recordings, membrane_recordings)
            spike_recordings: list of (num_steps) spike tensors from output layer
            membrane_recordings: list of (num_steps) membrane tensors from output layer
        """
        mem1 = self.lif1.init_leaky()
        mem2 = self.lif2.init_leaky()

        spk2_rec = []
        mem2_rec = []

        for step in range(x.shape[0]):
            cur1 = self.fc1(x[step])
            spk1, mem1 = self.lif1(cur1, mem1)
            cur2 = self.fc2(spk1)
            spk2, mem2 = self.lif2(cur2, mem2)
            spk2_rec.append(spk2)
            mem2_rec.append(mem2)

        return torch.stack(spk2_rec), torch.stack(mem2_rec)

    def forward_detailed(self, x):
        """
        Like forward(), but also records hidden layer activity.
        Used for the single-image analysis.

        Returns dict with per-step recordings of all internal states.
        """
        mem1 = self.lif1.init_leaky()
        mem2 = self.lif2.init_leaky()

        records = {
            "spk_hidden": [], "mem_hidden": [],
            "spk_output": [], "mem_output": [],
            "cur_output": []
        }

        for step in range(x.shape[0]):
            cur1 = self.fc1(x[step])
            spk1, mem1 = self.lif1(cur1, mem1)
            cur2 = self.fc2(spk1)
            spk2, mem2 = self.lif2(cur2, mem2)

            records["spk_hidden"].append(spk1.detach().cpu())
            records["mem_hidden"].append(mem1.detach().cpu())
            records["spk_output"].append(spk2.detach().cpu())
            records["mem_output"].append(mem2.detach().cpu())
            records["cur_output"].append(cur2.detach().cpu())

        return records

# ─── Training ─────────────────────────────────────────────────────────────────
print(f"\nTraining LeakySNN (beta={BETA}, steps={NUM_STEPS}) for {EPOCHS} epoch...")
model = LeakySNN(beta=BETA).to(DEVICE)
optimizer = torch.optim.Adam(model.parameters(), lr=LR, betas=(0.9, 0.999))
loss_fn = nn.CrossEntropyLoss()

model.train()
for epoch in range(EPOCHS):
    total_loss = 0
    correct = 0
    total = 0

    for batch_idx, (data, targets) in enumerate(train_loader):
        data = data.to(DEVICE).view(BATCH_SIZE, -1)  # Flatten: (batch, 784)

        # Rate coding: convert pixel intensities to spike probabilities
        # At each of 25 steps, pixel value 0.8 → 80% chance of spike
        # This is the SAME image shown 25 times with stochastic sampling
        spike_data = spikegen.rate(data, num_steps=NUM_STEPS)  # (25, batch, 784)

        spk_rec, mem_rec = model(spike_data)

        # Sum membrane potential over all time steps for classification
        # This is the "evidence accumulation" — integrating over time
        mem_sum = mem_rec.sum(dim=0)  # (batch, 10)
        loss = loss_fn(mem_sum, targets.to(DEVICE))

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        predicted = mem_sum.argmax(dim=1)
        correct += (predicted == targets.to(DEVICE)).sum().item()
        total += targets.size(0)

        if (batch_idx + 1) % 100 == 0:
            print(f"  Batch {batch_idx+1}/{len(train_loader)}: "
                  f"Loss={loss.item():.4f}, Acc={100*correct/total:.1f}%")

    print(f"Epoch {epoch+1}: Loss={total_loss/len(train_loader):.4f}, "
          f"Train Acc={100*correct/total:.2f}%")

# ─── Single Image Analysis ───────────────────────────────────────────────────
print("\nAnalyzing single test image...")
model.eval()

# Get a test image (find one that's correctly classified for a clean demo)
test_iter = iter(test_loader)
with torch.no_grad():
    for data_batch, target_batch in test_iter:
        data_batch = data_batch.to(DEVICE).view(BATCH_SIZE, -1)
        spike_batch = spikegen.rate(data_batch, num_steps=NUM_STEPS)
        _, mem_batch = model(spike_batch)
        mem_sum_batch = mem_batch.sum(dim=0)
        preds = mem_sum_batch.argmax(dim=1)
        # Find a correctly classified example
        correct_mask = (preds == target_batch.to(DEVICE))
        if correct_mask.any():
            idx = correct_mask.nonzero()[0].item()
            break

# Extract single image
single_image = data_batch[idx:idx+1]  # (1, 784)
true_label = target_batch[idx].item()
original_image = single_image.cpu().view(28, 28).numpy()

# Run through network step-by-step, recording everything
spike_input = spikegen.rate(single_image, num_steps=NUM_STEPS)  # (25, 1, 784)

with torch.no_grad():
    records = model.forward_detailed(spike_input)

# Extract output membrane potentials: shape (25, 10)
mem_output_all = torch.stack(records["mem_output"]).squeeze(1).numpy()  # (25, 10)
spk_output_all = torch.stack(records["spk_output"]).squeeze(1).numpy()  # (25, 10)
spk_hidden_all = torch.stack(records["spk_hidden"]).squeeze(1).numpy()  # (25, 1000)

# ─── Interpretation of Membrane Values ────────────────────────────────────────
# mem_output_all[t, c] = membrane potential of output neuron c at time step t
#
# This value represents ACCUMULATED EVIDENCE for class c at time t.
# It's computed as: mem[t] = beta * mem[t-1] + W @ hidden_spikes[t]
#
# The value is NOT a probability. It can be negative (evidence against)
# or positive (evidence for). What matters is the RELATIVE ranking across
# the 10 classes.
#
# To convert to something probability-like:
#   - Cumulative sum over time: cum_mem[t, c] = sum(mem[0:t+1, c])
#   - Softmax: prob[c] = exp(cum_mem[T, c]) / sum(exp(cum_mem[T, :]))
# We show both below.

# Cumulative membrane potential (summed evidence over time)
cum_mem = np.cumsum(mem_output_all, axis=0)  # (25, 10)

# Final summed membrane → softmax for "confidence" values
final_mem_sum = cum_mem[-1]  # (10,)
exp_vals = np.exp(final_mem_sum - final_mem_sum.max())  # numerically stable
softmax_probs = exp_vals / exp_vals.sum()

predicted_label = final_mem_sum.argmax()
sorted_indices = np.argsort(final_mem_sum)[::-1]
top1 = sorted_indices[0]
top2 = sorted_indices[1]
confidence_margin = final_mem_sum[top1] - final_mem_sum[top2]

# Cumulative spikes per output neuron
cum_spikes = np.cumsum(spk_output_all, axis=0)
final_spike_counts = cum_spikes[-1]

print(f"True label: {true_label}")
print(f"Predicted:  {predicted_label}")
print(f"Confidence margin (top1 - top2): {confidence_margin:.3f}")
print(f"Softmax probabilities: {dict(zip(range(10), [f'{p:.3f}' for p in softmax_probs]))}")

# ─── Export CSV ───────────────────────────────────────────────────────────────
csv_data = {"time_step": list(range(NUM_STEPS))}
for c in range(10):
    csv_data[f"neuron_{c}"] = mem_output_all[:, c].tolist()
csv_data["true_label"] = [true_label] * NUM_STEPS
csv_data["predicted_label"] = [predicted_label] * NUM_STEPS

df_out = pd.DataFrame(csv_data)
df_out.to_csv("output_dynamics_example.csv", index=False)
print("Saved: output_dynamics_example.csv")

# ─── Multi-Panel Visualization ────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 14))
gs = gridspec.GridSpec(3, 2, hspace=0.35, wspace=0.3)

# Color map for digit classes
cmap = plt.cm.tab10
digit_colors = [cmap(i) for i in range(10)]

# Panel 1: Input Image (top left)
ax1 = fig.add_subplot(gs[0, 0])
ax1.imshow(original_image, cmap="gray")
ax1.set_title(f"Input Image (True Label: {true_label})", fontsize=14, fontweight="bold")
ax1.axis("off")

# Panel 2: Membrane Potentials Over Time (top right)
# This is the CORE visualization: watch evidence accumulate step by step
ax2 = fig.add_subplot(gs[0, 1])
time_steps = np.arange(NUM_STEPS)
for c in range(10):
    linewidth = 3.0 if c == true_label else 1.0
    alpha = 1.0 if c == true_label else 0.5
    ax2.plot(time_steps, cum_mem[:, c], color=digit_colors[c],
             linewidth=linewidth, alpha=alpha, label=f"Digit {c}")
ax2.set_xlabel("Time Step")
ax2.set_ylabel("Cumulative Membrane Potential\n(Summed Evidence)")
ax2.set_title("Evidence Accumulation Over Time", fontsize=14, fontweight="bold")
ax2.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, ncol=1)
ax2.grid(True, alpha=0.3)
ax2.axhline(y=0, color="black", linewidth=0.5, linestyle="--")

# Panel 3: Per-Step Membrane (instantaneous, not cumulative) (middle left)
ax3 = fig.add_subplot(gs[1, 0])
for c in range(10):
    linewidth = 2.5 if c == true_label else 0.8
    alpha = 1.0 if c == true_label else 0.4
    ax3.plot(time_steps, mem_output_all[:, c], color=digit_colors[c],
             linewidth=linewidth, alpha=alpha, label=f"Digit {c}")
ax3.set_xlabel("Time Step")
ax3.set_ylabel("Instantaneous Membrane Potential")
ax3.set_title("Per-Step Membrane Potential (Raw)", fontsize=14, fontweight="bold")
ax3.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, ncol=1)
ax3.grid(True, alpha=0.3)
ax3.axhline(y=0, color="black", linewidth=0.5, linestyle="--")

# Panel 4: Output Spike Counts (middle right)
ax4 = fig.add_subplot(gs[1, 1])
bars = ax4.bar(range(10), final_spike_counts, color=digit_colors, edgecolor="black", linewidth=0.5)
# Highlight predicted class
bars[predicted_label].set_edgecolor("red")
bars[predicted_label].set_linewidth(3)
ax4.set_xlabel("Digit Class")
ax4.set_ylabel("Total Spike Count (over 25 steps)")
ax4.set_title("Output Neuron Spike Counts", fontsize=14, fontweight="bold")
ax4.set_xticks(range(10))

# Panel 5: Softmax Confidence (bottom left)
ax5 = fig.add_subplot(gs[2, 0])
bars5 = ax5.bar(range(10), softmax_probs, color=digit_colors, edgecolor="black", linewidth=0.5)
bars5[predicted_label].set_edgecolor("red")
bars5[predicted_label].set_linewidth(3)
ax5.set_xlabel("Digit Class")
ax5.set_ylabel("Softmax Probability")
ax5.set_title("Normalized Confidence (Softmax of Summed Membrane)", fontsize=14, fontweight="bold")
ax5.set_xticks(range(10))
ax5.set_ylim(0, 1)

# Panel 6: Summary Text (bottom right)
ax6 = fig.add_subplot(gs[2, 1])
ax6.axis("off")
summary_text = (
    f"Classification Result\n"
    f"{'='*30}\n\n"
    f"True Label:      {true_label}\n"
    f"Predicted Label: {predicted_label}\n"
    f"{'✓ CORRECT' if true_label == predicted_label else '✗ INCORRECT'}\n\n"
    f"Confidence Margin: {confidence_margin:.3f}\n"
    f"  (gap between top-2 summed membrane potentials)\n\n"
    f"Top-3 Softmax Probabilities:\n"
)
for rank, idx in enumerate(sorted_indices[:3]):
    summary_text += f"  #{rank+1}: Digit {idx} → {softmax_probs[idx]:.3f}\n"

summary_text += (
    f"\nHidden Layer Stats:\n"
    f"  Avg spikes per step: {spk_hidden_all.mean():.4f}\n"
    f"  Total hidden spikes: {spk_hidden_all.sum():.0f} / {HIDDEN_SIZE * NUM_STEPS}\n\n"
    f"What these numbers mean:\n"
    f"  • Membrane values = accumulated evidence\n"
    f"  • NOT probabilities until softmax applied\n"
    f"  • Positive = excitatory input dominated\n"
    f"  • Negative = inhibitory input dominated\n"
    f"  • Decision = argmax(sum over time)"
)
ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes,
         fontsize=10, verticalalignment="top", fontfamily="monospace",
         bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))

plt.suptitle(f"SNN Output Neuron Dynamics — beta={BETA}, {NUM_STEPS} time steps, rate coding",
             fontsize=16, fontweight="bold", y=1.01)
plt.savefig("output_neuron_dynamics.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: output_neuron_dynamics.png")

# ─── Animated Version ─────────────────────────────────────────────────────────
try:
    from matplotlib.animation import FuncAnimation, PillowWriter

    fig_anim, (ax_img, ax_mem) = plt.subplots(1, 2, figsize=(14, 5),
                                                gridspec_kw={"width_ratios": [1, 2.5]})

    ax_img.imshow(original_image, cmap="gray")
    ax_img.set_title(f"Input (True: {true_label})", fontsize=12)
    ax_img.axis("off")

    lines = []
    for c in range(10):
        lw = 3.0 if c == true_label else 1.0
        alpha = 1.0 if c == true_label else 0.5
        line, = ax_mem.plot([], [], color=digit_colors[c], linewidth=lw,
                            alpha=alpha, label=f"Digit {c}")
        lines.append(line)

    ax_mem.set_xlim(0, NUM_STEPS - 1)
    y_min = cum_mem.min() * 1.1
    y_max = cum_mem.max() * 1.1
    ax_mem.set_ylim(y_min, y_max)
    ax_mem.set_xlabel("Time Step")
    ax_mem.set_ylabel("Cumulative Membrane Potential")
    ax_mem.set_title("Evidence Accumulating...", fontsize=12)
    ax_mem.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax_mem.grid(True, alpha=0.3)

    step_text = ax_mem.text(0.02, 0.95, "", transform=ax_mem.transAxes,
                            fontsize=12, fontweight="bold")

    def animate(frame):
        t = frame + 1  # show at least 1 step
        for c in range(10):
            lines[c].set_data(np.arange(t), cum_mem[:t, c])
        current_pred = cum_mem[:t].sum(axis=0).argmax() if t > 0 else -1
        step_text.set_text(f"Step {t}/{NUM_STEPS} | Current prediction: {current_pred}")
        return lines + [step_text]

    anim = FuncAnimation(fig_anim, animate, frames=NUM_STEPS,
                         interval=200, blit=True, repeat_delay=2000)
    plt.tight_layout()
    anim.save("output_dynamics_animated.gif", writer=PillowWriter(fps=5))
    plt.close(fig_anim)
    print("Saved: output_dynamics_animated.gif")

except Exception as e:
    print(f"Animation skipped: {e}")
    print("(This is fine — the static plot has all the information)")

print("\n✅ All visualizations complete!")
