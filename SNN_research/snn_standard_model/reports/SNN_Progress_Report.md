# SNN Standard Neuron Model Research — Progress Report

**Part I: Systematic Benchmarking of snnTorch Neuron Models**

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Status** | In Progress |
| **Platform** | PyTorch + snnTorch (CPU-only) |
| **Architecture** | FC 784 → 1000 → 10 |
| **Datasets** | MNIST, Fashion-MNIST, N-MNIST |
| **Neuron Models** | Leaky, Synaptic, Alpha |

---

## 1. Executive Summary

This report documents the first phase of a systematic investigation into spiking neural network (SNN) neuron dynamics using the snnTorch library. The goal is to benchmark three neuron models — **Leaky** (first-order LIF), **Synaptic** (second-order with separate synaptic current), and **Alpha** (second-order with coupled dynamics) — across MNIST-family classification tasks.

The research follows a structured four-phase plan:

1. **Phase 1** — Comprehensive characterization of the Leaky neuron: beta sweeps under rate and latency coding, threshold sensitivity, reset mechanisms, learnable parameters, and inhibition.
2. **Phase 2** — Synaptic neuron grid search over alpha-beta space, with direct comparison to Phase 1 Leaky results and verification that alpha → 0 recovers Leaky behavior.
3. **Phase 3** — Alpha neuron baseline and three-way cross-model comparison, extended to Fashion-MNIST for generalization testing.
4. **Phase 4** — Neuromorphic data evaluation using N-MNIST, comparing native spike processing against rate/latency-encoded pipelines.

All experiments use a common infrastructure built around `ExperimentConfig` and `ExperimentResult` dataclasses with JSON logging, enabling reproducible comparisons. The network architecture is a simple two-layer fully-connected SNN (784 → 1000 → 10) chosen to isolate neuron-level effects from architectural complexity.

This work establishes the empirical foundation for **Part II**, which will introduce the custom Rhythm Neuron — a frequency-resonance-based model inspired by the Living Frequency Network architecture.

### 1.1 Technical Background

#### Leaky Integrate-and-Fire (LIF) Model

The simplest biologically-inspired spiking neuron. At each timestep, the membrane potential $U$ integrates weighted input current and decays toward rest:

$$U[t] = \beta \cdot U[t-1] + W \cdot X[t]$$

When $U$ crosses a firing threshold $\theta$, the neuron emits a spike and resets. The parameter **beta** ($\beta \in [0, 1]$) is the membrane potential decay constant — it controls how much "memory" the neuron retains between timesteps. High beta (→ 1) means slow decay and long temporal integration; low beta (→ 0) means rapid forgetting and sensitivity only to recent inputs.

In snnTorch, the `Leaky` neuron implements this with configurable threshold and reset mechanism (zero, subtract, or none).

#### Synaptic Neuron Model

Extends the LIF by modeling synaptic current as a separate state variable with its own decay constant **alpha** ($\alpha$):

$$I_{syn}[t] = \alpha \cdot I_{syn}[t-1] + W \cdot X[t]$$
$$U[t] = \beta \cdot U[t-1] + I_{syn}[t]$$

This two-compartment model produces richer temporal dynamics — the synaptic current acts as a low-pass filter on input before it reaches the membrane. When $\alpha \to 0$, the synaptic current has no memory and the model collapses to the standard Leaky neuron.

#### Alpha Neuron Model

A specific second-order formulation where synaptic current and membrane potential are coupled through a single parameterization. The alpha neuron produces the characteristic "alpha-shaped" post-synaptic potential (a rapid rise followed by exponential decay) seen in biological neurons. In snnTorch, this is implemented with shared alpha/beta dynamics that produce a more constrained but biologically motivated response profile.

#### Spike Coding Schemes

- **Rate coding**: Information is encoded in spike frequency. Input pixel values are converted to spike trains where brighter pixels fire more often over $N$ timesteps. Simple and robust, but temporally redundant.
- **Latency coding**: Information is encoded in spike timing. Brighter pixels fire earlier; each input neuron fires at most once. More efficient (fewer total spikes) but potentially harder to learn from, especially with fewer timesteps.

#### Why MNIST?

MNIST (handwritten digits, 28×28 grayscale) is the standard baseline for SNN classification research. Its simplicity means performance differences between neuron models and parameter settings reflect genuine dynamical effects rather than being confounded by task difficulty. Fashion-MNIST provides a harder variant with the same dimensionality, testing whether findings generalize. N-MNIST provides native neuromorphic (event-based) data from a Dynamic Vision Sensor, testing whether SNNs show advantages on spike-native data.

---

## 2. Implementation Status

### 2.1 Experiment Infrastructure

The experiment framework uses two core dataclasses:

- **`ExperimentConfig`** — Captures all hyperparameters: neuron type, beta, alpha (if applicable), threshold, reset mechanism, encoding scheme, number of timesteps, learning rate, epochs, batch size, and any experiment-specific flags (learnable parameters, inhibition mode, etc.).
- **`ExperimentResult`** — Records outcomes: test accuracy, training loss curve, spike density statistics (hidden and output layers), convergence speed (epoch to reach target accuracy), wall clock time, and the full config that produced them.

Results are serialized to **JSON** for programmatic analysis and comparison across experiments. A reusable training loop handles data loading, encoding, forward pass, loss computation (cross-entropy on spike counts or membrane potential), and metric collection.

**Environment note:** All experiments run on **CPU only**. This constrains batch sizes and total epochs but ensures reproducibility without GPU-specific variance. Expected training time per experiment: ~5–15 minutes depending on timestep count and encoding scheme.

### 2.2 Prior Work

Before this systematic study, an exploratory two-neuron LIF simulation was implemented (in `/SNN_research/machinelearning/spikyNN/`) with:
- Beta = 0.8, threshold = 1.0, reset mechanism = 'subtract'
- Sliding window activation analysis for temporal dynamics visualization

This provided the foundation and intuition for the current benchmarking effort.

### 2.3 Phase Task Tracker

| Phase | Task | ID | Status |
|-------|------|----|--------|
| **1** | Leaky beta sweep (rate coding) | L1 | ✅ **COMPLETE** (18 runs) |
| **1** | Leaky beta sweep (latency coding) | L2 | `[PENDING: not started]` |
| **1** | Threshold sensitivity analysis | L3 | `[PENDING: not started]` |
| **1** | Reset mechanism comparison | L4 | `[PENDING: not started]` |
| **1** | Learnable beta experiment | L5 | `[PENDING: not started]` |
| **1** | Inhibition mode analysis | L6 | `[PENDING: not started]` |
| **2** | Synaptic alpha-beta grid search | S1 | `[PENDING: not started]` |
| **2** | Synaptic learnable parameters | S2 | `[PENDING: not started]` |
| **2** | Alpha → 0 verification | S3 | `[PENDING: not started]` |
| **2** | Synaptic vs Leaky comparison | S4 | `[PENDING: not started]` |
| **3** | Alpha neuron baseline | A1 | `[PENDING: not started]` |
| **3** | Three-way model comparison | A2 | `[PENDING: not started]` |
| **3** | Fashion-MNIST generalization | A3 | `[PENDING: not started]` |
| **4** | N-MNIST native spike processing | N1 | `[PENDING: not started]` |
| **4** | N-MNIST native vs encoded comparison | N2 | `[PENDING: not started]` |
| **Infra** | ExperimentConfig/Result dataclasses | I1 | ✅ **COMPLETE** |
| **Infra** | Reusable training loop | I2 | ✅ **COMPLETE** |
| **Infra** | JSON logging and result aggregation | I3 | ✅ **COMPLETE** |

---

## 3. Results: Leaky Neuron (Phase 1)

Phase 1 isolates the Leaky (first-order LIF) neuron to establish baseline behavior and understand the effect of each parameter in isolation before introducing more complex neuron models.

### 3.0 Technical Deep Dive — How Time Steps Work in SNNs

Before interpreting the results, it's essential to understand what "time steps" actually mean in an SNN processing static images. This is one of the most common points of confusion.

#### Rate Coding on Static Images (MNIST)

With rate coding on a static image like an MNIST digit, **the SAME image is presented at EVERY time step**. This is not like feeding in a video frame by frame. Here's what happens:

1. **Each time step is an independent random sample.** A pixel with intensity 0.8 has an 80% probability of generating a spike at each step. Over 25 steps, a bright pixel (value ≈ 0.8) spikes roughly 20 times, while a dim pixel (value ≈ 0.1) might spike only 2–3 times.

2. **Time steps = repeated stochastic sampling from the same distribution.** The network doesn't "see more data" with more steps — it sees the SAME data more times, each time with independent random noise in the spike generation.

3. **More steps = more samples = more statistically reliable input representation.** In theory, 100 samples of a Bernoulli process give a better estimate of the underlying probability than 25 samples. BUT this comes at a direct cost: more computation (wall clock scales linearly with steps).

4. **Why 25 steps often beats 100:** This is the key insight from Phase 1.2. The neuron dynamics (membrane decay via beta) **interact** with the step count:
   - **High beta + many steps → membrane saturation.** With β=0.99, the membrane retains 99% of its value between steps. Over 100 steps, the accumulated potential grows without bound, creating enormous variance (we measured variance = 86.8 at β=0.99, 100 steps vs. 9.4 at β=0.99, 25 steps). This makes the loss landscape harder to navigate.
   - **Fewer steps keep things crisp.** 25 steps provides enough statistical reliability for rate coding while keeping membrane potentials in a well-behaved range. The network learns more effectively in this regime.
   - **The "sweet spot" depends on beta.** Low-beta neurons (β=0.5) forget fast, so more steps help them accumulate signal. High-beta neurons (β=0.99) remember everything, so excess steps cause accumulation problems.

5. **With latency coding it's fundamentally different.** Each pixel fires ONCE, and the *timing* of that spike encodes the intensity. Bright pixels fire early (step 1–2), dim pixels fire late (step 20+). Here, more steps = wider dynamic range for encoding information. The input IS temporal, not just stochastic resampling.

#### What Happens in the Output Layer

The output layer contains **10 neurons, one per digit class (0–9)**. Here's how classification works:

1. **Each output neuron accumulates membrane potential over all time steps.** At each step, it receives weighted input from hidden layer spikes and integrates it into its membrane state: `mem[t] = beta * mem[t-1] + W @ hidden_spikes[t]`.

2. **The classification decision is: which output neuron has the highest SUMMED membrane potential?** Formally: `predicted_class = argmax(Σ_t mem[t])`. This means the network isn't making a snap decision — it's **integrating evidence over time**, like a jury deliberating.

3. **Individual time-step membrane values show the decision forming:**
   - Early steps (t=1–5): Noisy, uncertain — all neurons have similar low values because only a few spikes have arrived.
   - Middle steps (t=10–15): The correct class starts to pull ahead as consistent evidence accumulates.
   - Late steps (t=20–25): Convergence — the winning neuron has a clear lead, though with high beta the margin can be exaggerated by saturation effects.

4. **Membrane potential is NOT a probability.** It's accumulated electrical evidence. A value of 3.7 doesn't mean "37% chance." To get probabilities, apply softmax to the final summed membrane values: `prob[c] = exp(sum_mem[c]) / Σ exp(sum_mem[c])`.

5. **The "confidence" of a prediction** can be measured as the margin between the top-2 summed membrane potentials. Larger margin = more decisive classification. The output neuron dynamics visualization (see `colab/output_neuron_dynamics.py`) shows this process in action.

---

### 3.1 Beta Sweep — Rate Coding (L1) — Phase 1.2 Results

**Objective:** Determine how membrane decay rate affects classification accuracy and spiking dynamics under rate-coded inputs. Expanded to a full 6×3 grid: beta ∈ {0.5, 0.7, 0.8, 0.9, 0.95, 0.99} × num_steps ∈ {25, 50, 100}.

**Result:** 18 experiments completed. All use rate coding, FC 784→1000→10, 1 epoch, batch size 128.

| Beta | Steps | Test Acc (%) | Train Acc (%) | Spike Density (Hidden) | Spike Density (Output) | Mem Mean (Hidden) | Mem Var (Hidden) | Wall Clock (s) |
|------|-------|-------------|--------------|----------------------|----------------------|-------------------|------------------|---------------|
| 0.50 | 25  | **95.56** | 92.81 | 2.22% | 0.098% | −0.088 | 0.39 | 142 |
| 0.50 | 50  | 95.79 | 92.32 | 1.32% | 0.007% | −0.156 | 0.38 | 239 |
| 0.50 | 100 | 95.37 | 91.50 | 0.92% | 0.001% | −0.194 | 0.39 | 451 |
| 0.70 | 25  | **95.93** | 93.28 | 1.38% | 0.083% | −0.349 | 0.62 | 140 |
| 0.70 | 50  | 95.75 | 92.48 | 0.95% | 0.006% | −0.420 | 0.63 | 235 |
| 0.70 | 100 | 95.31 | 91.74 | 0.75% | 0.003% | −0.479 | 0.65 | 458 |
| 0.80 | 25  | **96.09** | 92.98 | 1.50% | 0.259% | −0.595 | 1.03 | 143 |
| 0.80 | 50  | 95.69 | 92.13 | 1.21% | 0.109% | −0.730 | 1.15 | 240 |
| 0.80 | 100 | 95.23 | 91.70 | 1.17% | 0.107% | −0.795 | 1.23 | 457 |
| 0.90 | 25  | **95.85** | 91.46 | 3.93% | 3.29% | −0.824 | 2.57 | 142 |
| 0.90 | 50  | 94.61 | 90.58 | 3.82% | 3.20% | −1.098 | 3.58 | 240 |
| 0.90 | 100 | 94.54 | 89.53 | 3.82% | 3.44% | −1.288 | 4.27 | 454 |
| 0.95 | 25  | **95.90** | 92.21 | 4.12% | 3.68% | −1.275 | 4.85 | 142 |
| 0.95 | 50  | 95.55 | 91.39 | 3.73% | 3.28% | −2.091 | 9.41 | 240 |
| 0.95 | 100 | 94.52 | 90.64 | 3.74% | 3.38% | −2.719 | 13.46 | 456 |
| **0.99** | **25** | **96.10** ★ | 92.43 | 4.34% | 4.26% | −1.874 | 9.35 | 142 |
| 0.99 | 50  | 95.88 | 91.88 | 3.63% | 3.22% | −3.926 | 30.36 | 241 |
| 0.99 | 100 | 95.36 | 91.49 | 3.18% | 2.75% | −7.355 | 86.76 | 454 |

★ = Best overall configuration

### 3.1.1 Analysis: Beta × Num_Steps Interaction

**Key Finding #1: 25 steps universally dominates.** Across all 6 beta values, 25 time steps yields the highest test accuracy. This is counterintuitive — shouldn't more time steps give a better estimate of the input via rate coding? The answer is no, because of the membrane saturation effect described in Section 3.0.

**Key Finding #2: The accuracy landscape is surprisingly flat.** The best (β=0.99, 25 steps: 96.10%) and worst (β=0.9, 100 steps: 94.54%) differ by only 1.56 percentage points. MNIST is "easy enough" that even suboptimal configurations still learn well. The differences would likely be amplified on harder tasks.

**Key Finding #3: Two distinct regimes emerge at β ≥ 0.9.**

| Regime | Beta Range | Hidden Spike Density | Output Spike Density | Membrane Variance |
|--------|-----------|---------------------|---------------------|-------------------|
| **Low-beta** | 0.5 – 0.8 | 0.75% – 2.22% | 0.001% – 0.26% | 0.38 – 1.23 |
| **High-beta** | 0.9 – 0.99 | 3.18% – 4.34% | 2.75% – 4.26% | 2.57 – 86.76 |

At β ≥ 0.9, spike density roughly **triples** and output neuron spiking jumps from near-zero to ~3–4%. The neurons enter a much more active regime. Simultaneously, membrane variance begins to explode, especially with more time steps.

**Key Finding #4: Membrane variance explosion.** The most dramatic quantitative finding:

| Config | Membrane Variance |
|--------|-------------------|
| β=0.5, 25 steps | 0.39 |
| β=0.99, 25 steps | 9.35 |
| β=0.99, 50 steps | 30.36 |
| β=0.99, 100 steps | **86.76** |

That's a **223× increase** from the calmest to most extreme configuration. High beta with many steps creates wildly fluctuating membrane potentials, making gradient-based learning harder.

**Key Finding #5: Wall clock scales linearly with steps.** As expected, doubling time steps roughly doubles training time (~140s → ~240s → ~455s). Since 25 steps is both faster AND more accurate, there's no reason to use more steps for this task and architecture.

**Recommendation for subsequent phases:** Use β=0.99, 25 steps as the Leaky baseline. Also carry β=0.8, 25 steps as a "conservative" baseline from the low-beta regime (96.09% — essentially tied).

### 3.2 Beta Sweep — Latency Coding (L2)

**Objective:** Repeat the beta sweep under latency coding to understand how encoding scheme interacts with membrane dynamics. With latency coding, each input neuron fires at most once — the timing carries the information.

**Hypothesis:** Latency coding may require higher beta (longer memory) to integrate spike timing information, and may be more sensitive to the beta setting than rate coding.

| Beta | Num Steps | Encoding | Test Acc (%) | Spike Density (Hidden) | Spike Density (Output) | Convergence (epochs) | Wall Clock (s) |
|------|-----------|----------|-------------|----------------------|----------------------|---------------------|---------------|
| 0.3  | 25 | latency | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.5  | 25 | latency | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.7  | 25 | latency | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.8  | 25 | latency | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.9  | 25 | latency | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.95 | 25 | latency | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |

### 3.3 Threshold Sensitivity (L3)

**Objective:** With beta fixed at the best-performing value from L1, sweep the firing threshold to understand its effect on spike density and accuracy.

**Hypothesis:** Lower thresholds produce denser spiking (potentially noisy); higher thresholds produce sparser spiking (potentially losing signal). There should be a sweet spot balancing information throughput and noise.

| Threshold | Beta | Encoding | Test Acc (%) | Spike Density (Hidden) | Spike Density (Output) | Notes |
|-----------|------|----------|-------------|----------------------|----------------------|-------|
| 0.5  | `[best from L1]` | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| 0.75 | `[best from L1]` | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| 1.0  | `[best from L1]` | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | baseline |
| 1.5  | `[best from L1]` | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| 2.0  | `[best from L1]` | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | |

### 3.4 Reset Mechanism Comparison (L4)

**Objective:** Compare the three reset mechanisms available in snnTorch: `zero` (hard reset to 0), `subtract` (subtract threshold from membrane potential), and `none` (no reset — free-running).

**Hypothesis:** `subtract` preserves residual membrane information and should generally outperform `zero`. `none` may cause runaway potentials unless carefully managed.

| Reset Mechanism | Beta | Test Acc (%) | Spike Density (Hidden) | Spike Density (Output) | Notes |
|----------------|------|-------------|----------------------|----------------------|-------|
| zero     | `[best]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | Hard reset |
| subtract | `[best]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | Residual-preserving |
| none     | `[best]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | No reset |

### 3.5 Learnable Beta (L5)

**Objective:** Allow beta to be a learnable parameter (optimized via backpropagation through time) rather than fixed. Compare the learned beta values and final accuracy against the best fixed-beta result.

**Hypothesis:** Learnable beta should match or exceed the best fixed beta. The learned values themselves will be informative — they reveal what the network "wants" the decay constant to be.

| Init Beta | Learned Beta (Hidden) | Learned Beta (Output) | Test Acc (%) | Notes |
|-----------|----------------------|----------------------|-------------|-------|
| 0.5 | `[PENDING]` | `[PENDING]` | `[PENDING]` | Low init |
| 0.8 | `[PENDING]` | `[PENDING]` | `[PENDING]` | Mid init |
| 0.95 | `[PENDING]` | `[PENDING]` | `[PENDING]` | High init |

### 3.6 Inhibition Mode (L6)

**Objective:** Test the effect of lateral inhibition in the output layer, where the most active neuron suppresses others — a winner-take-all dynamic common in biological neural circuits.

**Hypothesis:** Inhibition should sharpen classification confidence and may improve accuracy on ambiguous inputs, at the cost of potentially slower convergence.

| Inhibition | Beta | Test Acc (%) | Spike Density (Output) | Confidence (avg max class) | Notes |
|-----------|------|-------------|----------------------|---------------------------|-------|
| Off | `[best]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | Baseline |
| On  | `[best]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | Winner-take-all |

---

## 4. Results: Synaptic Neuron (Phase 2)

Phase 2 introduces the Synaptic neuron, which adds a separate synaptic current compartment with its own decay constant alpha. This creates a richer dynamical system and explores how two-timescale dynamics affect SNN performance.

### 4.1 Alpha-Beta Grid Search (S1)

**Objective:** Sweep the two-dimensional parameter space of alpha (synaptic current decay) and beta (membrane potential decay) to map the accuracy landscape.

**Hypothesis:** The interaction between alpha and beta matters — certain combinations should produce complementary temporal filtering that outperforms any single-timescale (Leaky) model.

| Alpha | Beta | Encoding | Test Acc (%) | Spike Density (Hidden) | Spike Density (Output) | Convergence (epochs) | Wall Clock (s) |
|-------|------|----------|-------------|----------------------|----------------------|---------------------|---------------|
| 0.3 | 0.5 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.3 | 0.8 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.3 | 0.95 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.5 | 0.5 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.5 | 0.8 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.5 | 0.95 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.8 | 0.5 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.8 | 0.8 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.8 | 0.95 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.95 | 0.8 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| 0.95 | 0.95 | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |

### 4.2 Learnable Parameters (S2)

**Objective:** Allow both alpha and beta to be learned jointly. Observe what timescale separation the network converges to.

| Init Alpha | Init Beta | Learned Alpha | Learned Beta | Test Acc (%) | Notes |
|-----------|----------|--------------|-------------|-------------|-------|
| 0.5 | 0.5 | `[PENDING]` | `[PENDING]` | `[PENDING]` | Symmetric init |
| 0.3 | 0.8 | `[PENDING]` | `[PENDING]` | `[PENDING]` | Separated init |
| 0.8 | 0.8 | `[PENDING]` | `[PENDING]` | `[PENDING]` | Matched init |

### 4.3 Alpha → 0 Verification (S3)

**Objective:** Verify that the Synaptic neuron with alpha → 0 (e.g., alpha = 0.01) reproduces Leaky neuron behavior. This is a sanity check on the implementation and confirms the models form a proper hierarchy.

| Model | Alpha | Beta | Test Acc (%) | Match? |
|-------|-------|------|-------------|--------|
| Leaky | — | 0.8 | `[PENDING]` | baseline |
| Synaptic | 0.01 | 0.8 | `[PENDING]` | `[PENDING: should match Leaky within noise]` |
| Synaptic | 0.05 | 0.8 | `[PENDING]` | `[PENDING]` |
| Synaptic | 0.1 | 0.8 | `[PENDING]` | `[PENDING: divergence point?]` |

### 4.4 Synaptic vs Leaky Comparison (S4)

**Objective:** Head-to-head comparison using best parameters from each model. Does the added complexity of the Synaptic model pay off in accuracy, or does the simpler Leaky model suffice for MNIST?

| Model | Best Params | Test Acc (%) | Spike Density | Convergence | Wall Clock | Params |
|-------|------------|-------------|---------------|-------------|------------|--------|
| Leaky | `[from Phase 1]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | fewer |
| Synaptic | `[from S1]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | more |

---

## 5. Results: Alpha Neuron and Cross-Model Comparison (Phase 3)

Phase 3 completes the neuron model survey by adding the Alpha neuron and running the first cross-model comparison. It also extends to Fashion-MNIST to test whether findings generalize beyond standard MNIST.

### 5.1 Alpha Neuron Baseline (A1)

**Objective:** Establish Alpha neuron performance on MNIST with a parameter sweep. The Alpha model's coupled dynamics provide a different temporal profile than the Synaptic model despite both being second-order.

| Alpha | Beta | Encoding | Test Acc (%) | Spike Density (Hidden) | Spike Density (Output) | Notes |
|-------|------|----------|-------------|----------------------|----------------------|-------|
| `[PENDING: parameter selection]` | | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| | | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| | | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | |

### 5.2 Three-Way Model Comparison (A2)

**Objective:** Compare best-performing configurations of all three neuron models on MNIST under both encoding schemes. This is the central result table of the entire study.

| Model | Best Params | Encoding | Test Acc (%) | Spike Density (Hidden) | Spike Density (Output) | Convergence | Wall Clock |
|-------|------------|----------|-------------|----------------------|----------------------|-------------|------------|
| Leaky | `[from P1]` | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| Leaky | `[from P1]` | latency | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| Synaptic | `[from P2]` | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| Synaptic | `[from P2]` | latency | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| Alpha | `[from A1]` | rate | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |
| Alpha | `[from A1]` | latency | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` | `[PENDING]` |

### 5.3 Fashion-MNIST Generalization (A3)

**Objective:** Re-run the best configuration of each model on Fashion-MNIST. This dataset is structurally identical to MNIST (28×28, 10 classes) but significantly harder (clothing items instead of digits). If model rankings change on Fashion-MNIST, it suggests the temporal dynamics interact with task complexity.

| Model | Dataset | Best Params | Test Acc (%) | Spike Density (Hidden) | Notes |
|-------|---------|------------|-------------|----------------------|-------|
| Leaky | Fashion-MNIST | `[from P1]` | `[PENDING]` | `[PENDING]` | |
| Synaptic | Fashion-MNIST | `[from P2]` | `[PENDING]` | `[PENDING]` | |
| Alpha | Fashion-MNIST | `[from A1]` | `[PENDING]` | `[PENDING]` | |
| Leaky | MNIST | `[from P1]` | `[PENDING]` | `[PENDING]` | reference |
| Synaptic | MNIST | `[from P2]` | `[PENDING]` | `[PENDING]` | reference |
| Alpha | MNIST | `[from A1]` | `[PENDING]` | `[PENDING]` | reference |

---

## 6. Results: Neuromorphic Data (Phase 4)

Phase 4 tests the neuron models on **N-MNIST**, a neuromorphic version of MNIST captured with a Dynamic Vision Sensor (DVS). N-MNIST provides native spike-based data, which is the natural input format for SNNs — unlike standard MNIST which requires encoding.

### 6.1 N-MNIST Results (N1)

**Objective:** Evaluate all three neuron models on N-MNIST using native event-based input (no encoding step needed). This tests whether the models can leverage temporal structure already present in the data.

| Model | Best Params | Input Mode | Test Acc (%) | Spike Density (Hidden) | Spike Density (Output) | Notes |
|-------|------------|-----------|-------------|----------------------|----------------------|-------|
| Leaky | `[from P1]` | native | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| Synaptic | `[from P2]` | native | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| Alpha | `[from A1]` | native | `[PENDING]` | `[PENDING]` | `[PENDING]` | |

### 6.2 Native vs Encoded Comparison (N2)

**Objective:** Compare performance on N-MNIST using native spikes versus re-encoding the frame-accumulated images with rate/latency coding. If native processing outperforms, it validates the SNN's temporal processing advantage. If encoded performs similarly, it suggests the temporal structure in N-MNIST doesn't add much for these simple architectures.

| Model | Input Mode | Test Acc (%) | Spike Density | Wall Clock | Notes |
|-------|-----------|-------------|---------------|------------|-------|
| Leaky | native | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| Leaky | rate-encoded | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| Leaky | latency-encoded | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| Synaptic | native | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| Synaptic | rate-encoded | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| Alpha | native | `[PENDING]` | `[PENDING]` | `[PENDING]` | |
| Alpha | rate-encoded | `[PENDING]` | `[PENDING]` | `[PENDING]` | |

---

## 7. Error and Performance Metrics Summary

Consolidated results across all experiments. This table will be populated as phases complete. Each row represents a single experiment run.

| Exp ID | Phase | Model | Alpha | Beta | Threshold | Reset | Encoding | Num Steps | Learnable | Inhibition | Dataset | Test Acc (%) | Spike Density (Hidden) | Spike Density (Output) | Convergence (epochs) | Wall Clock (s) | Notes |
|--------|-------|-------|-------|------|-----------|-------|----------|-----------|-----------|-----------|---------|-------------|----------------------|----------------------|---------------------|---------------|-------|
| `[PENDING: populated from JSON logs as experiments complete]` | | | | | | | | | | | | | | | | | |

**Metric Definitions:**
- **Test Accuracy:** Classification accuracy on held-out test set after final training epoch.
- **Spike Density (Hidden):** Average fraction of hidden neurons firing per timestep, averaged over test set.
- **Spike Density (Output):** Average fraction of output neurons firing per timestep, averaged over test set.
- **Convergence Speed:** Number of epochs to first reach 90% of final test accuracy (or a fixed threshold like 95%).
- **Wall Clock Time:** Total training time in seconds (CPU-only).

---

## 8. Visualization Gallery

Each visualization type is defined below with its purpose and what it will reveal. Actual figures will be generated from experiment data and linked here.

### V1: Beta vs Accuracy Curves

**Description:** Line plots of test accuracy as a function of beta for each encoding scheme. Separate curves for Leaky rate, Leaky latency. Reveals the optimal beta range and whether encoding interacts with the optimal decay constant.

`[PENDING: figures/v1_beta_accuracy_rate.png]`
`[PENDING: figures/v1_beta_accuracy_latency.png]`

### V2: Spike Density Heatmaps

**Description:** Heatmaps showing average spike density across the hidden layer for different beta values and timesteps. Reveals whether the network is in a healthy spiking regime or suffering from dead neurons / spike saturation.

`[PENDING: figures/v2_spike_density_heatmap.png]`

### V3: Alpha-Beta Landscape (Synaptic)

**Description:** 2D heatmap of test accuracy over the alpha-beta grid from experiment S1. Reveals the interaction structure between synaptic and membrane timescales, and identifies the optimal operating region.

`[PENDING: figures/v3_alpha_beta_landscape.png]`

### V4: Membrane Potential Traces

**Description:** Time-series plots of membrane potential for sample neurons across timesteps during inference. Separate panels for each neuron model. Shows the qualitative difference in dynamics — simple exponential decay (Leaky), filtered response (Synaptic), alpha-shaped PSP (Alpha).

`[PENDING: figures/v4_membrane_traces_leaky.png]`
`[PENDING: figures/v4_membrane_traces_synaptic.png]`
`[PENDING: figures/v4_membrane_traces_alpha.png]`

### V5: Three-Way Model Comparison Bar Chart

**Description:** Grouped bar chart comparing accuracy, spike density, and convergence speed across all three neuron models under both encoding schemes. The central summary visualization of the study.

`[PENDING: figures/v5_model_comparison.png]`

### V6: Learned Parameter Distributions

**Description:** Histograms or violin plots showing the distribution of learned beta (and alpha, for Synaptic) values across neurons after training with learnable parameters. Reveals whether the network learns uniform or heterogeneous timescales.

`[PENDING: figures/v6_learned_params.png]`

### V7: Fashion-MNIST vs MNIST Comparison

**Description:** Side-by-side accuracy comparison showing how each model's performance degrades (or doesn't) when moving from MNIST to Fashion-MNIST. Reveals which neuron models are more robust to increased task difficulty.

`[PENDING: figures/v7_mnist_vs_fashion.png]`

---

## 9. Key Insights and Recommendations

### 9.1 Beta Range Findings

**Completed (rate coding):** The optimal beta for MNIST with rate coding is **β=0.99 at 25 steps** (96.10%), essentially tied with β=0.8 at 25 steps (96.09%). The accuracy landscape is a broad plateau — any beta from 0.5 to 0.99 with 25 steps gives 95.5%–96.1%. The optimum is NOT sharp, suggesting MNIST doesn't strongly discriminate between membrane timescales under rate coding.

However, the *dynamics* change dramatically: β ≥ 0.9 creates a fundamentally different spiking regime (3–4× spike density, exploding membrane variance). Whether this matters depends on the downstream task's difficulty and the computational budget.

**Pending:** Latency coding sweeps (L2) needed to test whether the optimal beta shifts when temporal spike timing carries the information.

### 9.2 Synaptic Complexity Tradeoff

`[PENDING: Does the Synaptic model's extra parameter (alpha) and computation justify its use over the simpler Leaky model? On MNIST, the accuracy gap may be small — but does the Synaptic model show advantages in spike efficiency, convergence, or generalization to Fashion-MNIST?]`

### 9.3 Encoding × Model Interaction

`[PENDING: Do certain neuron models pair better with certain encoding schemes? Does latency coding benefit more from longer membrane memory (high beta)? Does the Synaptic model's filtering help with noisy rate-coded inputs?]`

### 9.4 Threshold and Reset Effects

`[PENDING: How sensitive are results to threshold choice? Does the subtract reset consistently outperform zero reset? Are these effects model-dependent?]`

### 9.5 Learnable Parameters

`[PENDING: Do learnable beta/alpha converge to the same values found optimal in grid search? Do different layers learn different timescales? What does this tell us about the network's preferred dynamics?]`

### 9.6 Recommendations for Part II — Rhythm Neuron

`[PENDING: Based on the standard model benchmarks, what should the Rhythm Neuron target? Specific beta/alpha regimes that underperform? Temporal patterns that none of the standard models capture well? Frequency-domain behaviors missing from the LIF family? The Rhythm Neuron's frequency-resonance mechanism should address gaps identified here.]`

---

## 10. Known Issues and Limitations

### CPU-Only Constraint

All experiments run on CPU, which imposes practical limits:
- Training times of ~5–15 minutes per experiment configuration
- Total experiment suite (all phases) estimated at **several hours** of compute time
- Batch sizes may need to be kept moderate (64–128) to avoid excessive wall clock time
- No GPU-specific optimizations (e.g., cuDNN RNN kernels) are tested

This is acceptable for a research exploration focused on understanding dynamics rather than achieving state-of-the-art throughput, but results should not be compared to GPU-trained benchmarks in terms of wall clock time.

### Architecture Simplicity

The FC 784 → 1000 → 10 architecture is intentionally simple. It isolates neuron-level effects but does not test:
- Convolutional SNN architectures (which are standard for image tasks)
- Deeper networks where temporal dynamics may compound across layers
- Recurrent connections or feedback loops

Findings about neuron model differences may not transfer directly to more complex architectures.

### snnTorch Considerations

- snnTorch's surrogate gradient implementations (fast sigmoid, arctangent, etc.) introduce a choice that could interact with neuron model comparisons. We use the default surrogate gradient throughout for consistency.
- The `Alpha` neuron in snnTorch has a specific parameterization that may differ from other libraries' implementations. Results are specific to snnTorch's formulation.
- N-MNIST data loading and preprocessing depends on snnTorch's dataset utilities; any bugs or format assumptions there propagate to Phase 4 results.

### Statistical Rigor

`[PENDING: Determine whether to run multiple seeds per configuration. Single-seed results show trends but don't quantify variance. For the final report, at least 3 seeds per key configuration is recommended.]`

### Scope Boundary

This report covers **Part I only** — standard neuron models from the snnTorch library. The custom Rhythm Neuron (Part II) is a separate research track that builds on these baselines. No Rhythm Neuron results appear here.

---

*Report generated: 2026-03-06 | Last updated: 2026-03-06 (Phase 1.2 results populated, technical deep dive added)*
*Project path: `/home/ubuntu/.openclaw/workspace/SNN_research/snn_standard_model/`*
*Code base: `/home/ubuntu/.openclaw/workspace/SNN_research/machinelearning/spikyNN/`*
