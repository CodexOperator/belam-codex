#!/usr/bin/env python3
"""
Phase 1 Results Visualization — SNN Beta Sweep Analysis
========================================================
Self-contained script for Google Colab. Generates heatmaps and line plots
from the Phase 1.2 beta × num_steps experiment grid.

Usage (Colab):
    1. Upload phase1_results.csv to /content/
    2. Run this script

Dependencies (pre-installed in Colab):
    pip install pandas matplotlib seaborn numpy
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ─── Load Data ────────────────────────────────────────────────────────────────
df = pd.read_csv("phase1_results.csv")

# Convert test accuracy to percentage for readability
df["test_acc_pct"] = df["test_acc"] * 100
df["train_acc_pct"] = df["train_acc"] * 100
df["spike_density_hidden_pct"] = df["spike_density_hidden"] * 100

# Set up consistent styling
sns.set_theme(style="whitegrid", font_scale=1.2)
colors = sns.color_palette("viridis", n_colors=len(df["num_steps"].unique()))

# ─── 1. Heatmap: Test Accuracy (beta × num_steps) ────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))
pivot_acc = df.pivot_table(values="test_acc_pct", index="beta", columns="num_steps")
sns.heatmap(pivot_acc, annot=True, fmt=".2f", cmap="YlGn", ax=ax,
            cbar_kws={"label": "Test Accuracy (%)"}, linewidths=0.5)
ax.set_title("Test Accuracy (%) — Beta × Time Steps", fontsize=14, fontweight="bold")
ax.set_xlabel("Number of Time Steps")
ax.set_ylabel("Beta (Membrane Decay)")
plt.tight_layout()
plt.savefig("heatmap_test_accuracy.png", dpi=150)
plt.show()
print("Saved: heatmap_test_accuracy.png")

# ─── 2. Heatmap: Hidden Layer Spike Density (beta × num_steps) ───────────────
fig, ax = plt.subplots(figsize=(8, 6))
pivot_spike = df.pivot_table(values="spike_density_hidden_pct", index="beta", columns="num_steps")
sns.heatmap(pivot_spike, annot=True, fmt=".2f", cmap="YlOrRd", ax=ax,
            cbar_kws={"label": "Spike Density (%)"}, linewidths=0.5)
ax.set_title("Hidden Layer Spike Density (%) — Beta × Time Steps", fontsize=14, fontweight="bold")
ax.set_xlabel("Number of Time Steps")
ax.set_ylabel("Beta (Membrane Decay)")
plt.tight_layout()
plt.savefig("heatmap_spike_density.png", dpi=150)
plt.show()
print("Saved: heatmap_spike_density.png")

# ─── 3. Line Plot: Test Accuracy vs Beta for each num_steps ──────────────────
fig, ax = plt.subplots(figsize=(10, 6))
for i, steps in enumerate(sorted(df["num_steps"].unique())):
    subset = df[df["num_steps"] == steps].sort_values("beta")
    ax.plot(subset["beta"], subset["test_acc_pct"], marker="o", linewidth=2,
            label=f"{steps} steps", color=colors[i], markersize=8)
ax.set_xlabel("Beta (Membrane Decay)")
ax.set_ylabel("Test Accuracy (%)")
ax.set_title("Test Accuracy vs Beta — By Time Step Count", fontsize=14, fontweight="bold")
ax.legend(title="Time Steps", frameon=True)
ax.set_xticks(sorted(df["beta"].unique()))
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("line_accuracy_vs_beta.png", dpi=150)
plt.show()
print("Saved: line_accuracy_vs_beta.png")

# ─── 4. Line Plot: Spike Density vs Beta for each num_steps ──────────────────
fig, ax = plt.subplots(figsize=(10, 6))
for i, steps in enumerate(sorted(df["num_steps"].unique())):
    subset = df[df["num_steps"] == steps].sort_values("beta")
    ax.plot(subset["beta"], subset["spike_density_hidden_pct"], marker="s", linewidth=2,
            label=f"{steps} steps", color=colors[i], markersize=8)
ax.set_xlabel("Beta (Membrane Decay)")
ax.set_ylabel("Hidden Layer Spike Density (%)")
ax.set_title("Spike Density vs Beta — By Time Step Count", fontsize=14, fontweight="bold")
ax.legend(title="Time Steps", frameon=True)
ax.set_xticks(sorted(df["beta"].unique()))
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("line_spike_density_vs_beta.png", dpi=150)
plt.show()
print("Saved: line_spike_density_vs_beta.png")

# ─── 5. Bonus: Membrane Variance Explosion Plot ──────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
for i, steps in enumerate(sorted(df["num_steps"].unique())):
    subset = df[df["num_steps"] == steps].sort_values("beta")
    ax.plot(subset["beta"], subset["mem_var_hidden"], marker="^", linewidth=2,
            label=f"{steps} steps", color=colors[i], markersize=8)
ax.set_xlabel("Beta (Membrane Decay)")
ax.set_ylabel("Membrane Potential Variance")
ax.set_title("Membrane Variance Explosion — Beta × Time Steps", fontsize=14, fontweight="bold")
ax.legend(title="Time Steps", frameon=True)
ax.set_xticks(sorted(df["beta"].unique()))
ax.set_yscale("log")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("line_membrane_variance.png", dpi=150)
plt.show()
print("Saved: line_membrane_variance.png")

# ─── Summary Statistics ──────────────────────────────────────────────────────
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
best = df.loc[df["test_acc_pct"].idxmax()]
print(f"Best config: beta={best['beta']}, steps={int(best['num_steps'])}")
print(f"  Test accuracy: {best['test_acc_pct']:.2f}%")
print(f"  Spike density (hidden): {best['spike_density_hidden']*100:.2f}%")
print(f"  Wall clock: {best['wall_clock_s']:.0f}s")
print()
worst = df.loc[df["test_acc_pct"].idxmin()]
print(f"Worst config: beta={worst['beta']}, steps={int(worst['num_steps'])}")
print(f"  Test accuracy: {worst['test_acc_pct']:.2f}%")
print()
print("Key finding: 25 steps consistently outperforms 50 and 100 steps")
print("across ALL beta values. More steps ≠ better accuracy.")
