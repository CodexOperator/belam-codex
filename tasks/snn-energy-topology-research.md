---
primitive: task
status: open
priority: high
created: 2026-03-27
owner: belam
depends_on: []
upstream: [snn-standard-model, microcap-swing-signal-extraction]
downstream: []
tags: [snn, research, neuron-architecture, energy-model, topology, frequency-matching]
project: snn-energy-topology-research
subtasks: ["{'id': 'A1', 'title': 'Energy-Aware LIF Neuron — Base Implementation', 'status': 'in_pipeline', 'depends_on': []}", "{'id': 'A2', 'title': 'Frequency Matching Loss Function', 'status': 'open', 'depends_on': ['A1']}", "{'id': 'A3', 'title': 'Frequency Band Quantization', 'status': 'open', 'depends_on': ['A2']}", "{'id': 'A4', 'title': 'Differential Output Under Energy Pressure', 'status': 'open', 'depends_on': ['A1', 'A2']}", "{'id': 'A5a', 'title': 'Pull-Only Connection Mechanics — Subscribe/Unsubscribe', 'status': 'open', 'depends_on': ['A1']}", "{'id': 'A5b', 'title': 'Fold-Based Connection Restructuring & Meta-Learning', 'status': 'open', 'depends_on': ['A5a']}", "{'id': 'A5c', 'title': 'Connection Energy Economics — Formation Cost & Natural Decay', 'status': 'open', 'depends_on': ['A5a']}", "{'id': 'A5d', 'title': 'Layer Rule Enforcement & Small Cluster Integration', 'status': 'open', 'depends_on': ['A5b', 'A5c']}", "{'id': 'B1', 'title': 'Architecture Baseline — Fixed Feedforward SNN on BTC Data', 'status': 'open', 'depends_on': ['A1', 'A2', 'A3']}", "{'id': 'B2a', 'title': 'Full Architecture Assembly — Input/Processing/Output on BTC Data', 'status': 'open', 'depends_on': ['A5d', 'B1']}", "{'id': 'B2b', 'title': 'Topology Analysis — Connection Graphs & Neuron Specialization', 'status': 'open', 'depends_on': ['B2a']}", "{'id': 'B3', 'title': 'Self-Organizing Variant B — Output Reads Processing + Input', 'status': 'open', 'depends_on': ['B2a']}", "{'id': 'B4', 'title': 'Connection Limits & Scaling — Max K Connections', 'status': 'open', 'depends_on': ['B2a']}", "{'id': 'C1', 'title': 'Single-Indicator Micro-Networks — Candles Only', 'status': 'open', 'depends_on': ['B2a']}", "{'id': 'C2a', 'title': 'Single-Indicator Micro-Networks — Indicator Only (Various Formats)', 'status': 'open', 'depends_on': ['C1']}", "{'id': 'C2b', 'title': 'Paired Micro-Networks — Single Indicator + Candle Data (Various Formats)', 'status': 'open', 'depends_on': ['C1']}", "{'id': 'C3', 'title': 'Micro-Network Ensemble — Combine Trained Specialists', 'status': 'open', 'depends_on': ['C1', 'C2a', 'C2b']}", "{'id': 'D1', 'title': 'All-Indicators Monolithic Network', 'status': 'open', 'depends_on': ['B2a']}", "{'id': 'D2', 'title': 'Ensemble vs Monolithic Comparison', 'status': 'open', 'depends_on': ['C3', 'D1']}", "{'id': 'E1', 'title': 'Multi-Horizon Prediction — 5/10/50 Candle Windows', 'status': 'open', 'depends_on': ['D2']}", "{'id': 'E2', 'title': 'Energy-Optimal Spike Rates Across Horizons', 'status': 'open', 'depends_on': ['E1']}", "{'id': 'F1', 'title': 'Research Synthesis & Architecture Recommendations', 'status': 'open', 'depends_on': ['D2', 'E2']}"]
---

# SNN Energy-Topology Research — Subtask Breakdown

Master task for the energy-aware, self-organizing SNN architecture research.
All code lives in `machinelearning/snn_applied_finance/snn_energy_topology/`.
Pipeline template: **research-pipeline** for all subtasks.

## Project Reference
`projects/snn-energy-topology-research.md`

---

## Group A: Core Neuron Mechanics (Foundation)

Everything else is gated on this group. If energy-aware frequency matching doesn't produce meaningful behavior on synthetic signals, we retool before using market data. Group A is the ONLY group that uses synthetic data — all subsequent groups use real market data.

### A1: Energy-Aware LIF Neuron — Base Implementation
**Depends:** None
**Scope:**
- Pure PyTorch implementation of a leaky integrate-and-fire neuron with energy accounting
- Energy costs: spike emission (high), spike reception (low)
- Energy earned: proportional to frequency match accuracy
- Net energy tracked per neuron per batch
- Weight clamping: 0.1–10 range
- Surrogate gradient for backprop through spikes
- Test with synthetic constant-frequency input: does the neuron settle to a stable energy-positive firing rate?
- Test with synthetic varying-frequency input: does the neuron adapt?
**Acceptance:**
- [ ] Neuron fires at stable rate under constant input
- [ ] Energy accounting is correct (costs deducted, earnings credited)
- [ ] Weight clamps enforced
- [ ] Neuron adapts firing rate when input frequency changes

### A2: Frequency Matching Loss Function
**Depends:** A1
**Scope:**
- Design loss function that rewards output frequency matching target
- Train a tiny network (3-5 neurons) to match a target frequency from synthetic input
- Compare: MSE on firing rate vs energy-based loss vs hybrid
- The loss should work with surrogate gradients
- Verify that energy pressure drives toward lower spike rates that still achieve the same differential
**Acceptance:**
- [ ] Network learns to match target frequency on synthetic data
- [ ] Energy-based loss produces sparser firing than pure accuracy loss
- [ ] Differential between output neurons is maintained under energy pressure

### A3: Frequency Band Quantization
**Depends:** A2
**Scope:**
- Define discrete frequency bands (e.g., 5 bands mapping to strong-sell / sell / hold / buy / strong-buy)
- Modify loss to encourage neurons to snap to band centers rather than arbitrary rates
- Implement band assignment: which band is a neuron currently in?
- Test: does quantization improve noise rejection? (small input perturbations shouldn't change band)
- Min/max rate clamping within bands
**Acceptance:**
- [ ] Neurons reliably snap to discrete bands
- [ ] Small input noise doesn't cause band switching
- [ ] Band assignment is interpretable and consistent

### A4: Differential Output Under Energy Pressure
**Depends:** A1, A2
**Scope:**
- Two+ output neurons must maintain meaningful rate *difference*
- Under energy pressure, the network should find the minimum-energy configuration that preserves discrimination
- Test: binary classification on synthetic signal — can two output neurons separate classes via frequency differential while minimizing total energy?
**Acceptance:**
- [ ] Binary classification accuracy >90% on synthetic separable data
- [ ] Total energy consumption measurably lower than unconstrained version
- [ ] Rate differential between classes is clear and consistent

### A5a: Pull-Only Connection Mechanics — Subscribe/Unsubscribe
**Depends:** A1
**Scope:**
- Implement the core pull-only connection mechanism: each neuron decides which inputs to subscribe to
- Per-sample weight adjustment (fine-tuning within batch — small learning rate)
- Per-batch structural adjustment (subscribe/unsubscribe decisions — topology changes)
- **Per-fold connection restructuring:** After each fold, the network reviews how it could have done the fold better, adjusts connections, then re-tests on the same fold with new connections. Repeat 3× per fold before moving on.
- Folds are small (mini-folds)
- Interleave folds from different market regimes (bull/bear/sideways) to force generalization
- Between folds: weights get a randomized offset from their previous state (not reset, nudged) — prevents memorization while preserving meaningful learned structure
- Connection state persists across folds — the network accumulates structural knowledge
- Test: does the network develop stable connection patterns that generalize across regime-interleaved folds?
**Acceptance:**
- [ ] Subscribe/unsubscribe mechanism works (neurons can add/drop inputs)
- [ ] Per-sample fine weight adjustment implemented
- [ ] Per-batch structural adjustment implemented
- [ ] 3× fold replay with connection restructuring shows measurable improvement
- [ ] Randomized weight offset preserves meaningful state between folds
- [ ] Network handles regime-interleaved folds without catastrophic forgetting

### A5b: Fold-Based Connection Restructuring & Meta-Learning
**Depends:** A5a
**Scope:**
- Formalize the fold-replay-restructure loop as a training protocol
- Analyze: what does the network learn from the 3× replay? Does the 3rd pass consistently beat the 1st?
- Track connection churn: how many connections change per replay? Does it stabilize?
- Track weight offset impact: how far do weights drift from their nudged starting point?
- Document the meta-learning dynamics: is the network learning *how to restructure* or just *which connections to keep*?
**Acceptance:**
- [ ] Replay improvement curve documented (1st vs 2nd vs 3rd pass per fold)
- [ ] Connection churn analysis (convergence rate)
- [ ] Weight drift analysis
- [ ] Meta-learning characterization

### A5c: Connection Energy Economics — Formation Cost & Natural Decay
**Depends:** A5a
**Scope:**
- Connection formation costs energy (investment to subscribe)
- Connection maintenance is ongoing energy drain per batch
- Connection breaking is free — just stop spending (natural atrophy from disuse)
- Energy budget constrains total connections: neurons that earn more energy can afford more connections
- Test: does energy pressure create meaningful sparsity? Do useful connections survive and useless ones decay?
**Acceptance:**
- [ ] Formation/maintenance costs correctly deducted
- [ ] Unused connections decay naturally when energy is tight
- [ ] Energy-rich neurons maintain more connections than energy-poor ones
- [ ] Resulting topology is meaningfully sparser than unconstrained version

### A5d: Layer Rule Enforcement & Small Cluster Integration
**Depends:** A5b, A5c
**Scope:**
- Enforce layer rules: processing can subscribe to input + processing only (not output), output subscribes to processing (variant A) or processing + input (variant B), input doesn't initiate connections
- Integration test: 5-10 neuron processing cluster with 3-4 inputs and 2 outputs
- Full stack: energy accounting + pull-only connections + energy economics + layer rules + fold-based training
- Verify everything works together on synthetic data before Group B hits real market data
**Acceptance:**
- [ ] Layer rules enforced (no illegal connections form)
- [ ] Full stack integration works (no component conflicts)
- [ ] Stable topology emerges after training on consistent signal
- [ ] Topology changes when signal characteristics change

---

## Group B: Architecture Variants

Test topology variants on **real market data** (BTC 15-min candles). No synthetic data — synthetic performance doesn't predict market performance and causes integration bugs later.

### B1: Architecture Baseline — Fixed Feedforward SNN on BTC Data
**Depends:** A1, A2, A3
**Scope:**
- Standard feedforward SNN with energy-aware neurons but NO self-organizing topology
- Fixed architecture: Input → Hidden → Output
- Same energy model and frequency matching as custom variants
- This is the control group — how much does self-organization add?
- **Test on:** BTC 15-min candles from `snn_applied_finance/microcap_swing/data/`, next-10-candle direction prediction
- Establish baseline accuracy and energy metrics
**Acceptance:**
- [ ] Baseline accuracy and energy metrics established on real market data
- [ ] Comparison framework ready (metrics: accuracy, energy efficiency, adaptation speed)

### B2a: Full Architecture Assembly — Input/Processing/Output on BTC Data
**Depends:** A5d, B1
**Scope:**
- Assemble the full architecture: Input (broadcast) → Processing cluster (self-organizing) → Output (reads processing only — Variant A)
- Processing neurons subscribe to input and each other (pull-only)
- Output neurons subscribe to processing neurons only
- All connection rules enforced
- **Train on BTC 15-min candles**, same target as B1 for direct comparison
- Focus on: does it converge? Does it match or beat B1?
**Acceptance:**
- [ ] Network trains and converges on real BTC data
- [ ] Accuracy comparison vs B1 baseline documented
- [ ] Energy efficiency comparison vs B1 documented

### B2b: Topology Analysis — Connection Graphs & Neuron Specialization
**Depends:** B2a
**Scope:**
- Analyze the topology that emerged from B2a training
- Connection graph visualization (who subscribes to whom)
- Neuron specialization metrics: do processing neurons develop distinct roles?
- Compare topology across different training runs — is it stable or random?
- Energy distribution: which neurons are energy-rich vs energy-poor?
**Acceptance:**
- [ ] Connection graph visualizations generated
- [ ] Neuron specialization quantified
- [ ] Topology stability across runs assessed
- [ ] Energy distribution analysis

### B3: Self-Organizing Variant B — Output Reads Processing + Input
**Depends:** B2a
**Scope:**
- Same as B2a but output neurons can also subscribe to input neurons directly
- Compare: does direct input access help or hurt output quality?
- Hypothesis: might help for simple signals, hurt for complex ones (bypasses processing)
**Acceptance:**
- [ ] Direct comparison with B2a on same BTC 15-min data
- [ ] Analysis of when/why output neurons choose to read input directly vs through processing

### B4: Connection Limits & Scaling — Max K Connections
**Depends:** B2a
**Scope:**
- Add configurable max connections per neuron (K)
- Test K = 2, 5, 10, unlimited on networks of size 10, 20, 50 processing neurons
- Find the sweet spot: enough connections for information flow, few enough for efficiency
- This is the scaling gate — determines if the architecture works beyond micro-networks
**Acceptance:**
- [ ] Optimal K identified for each network size
- [ ] Scaling behavior documented
- [ ] Energy efficiency vs accuracy tradeoff curve

---

## Group C: Single-Indicator Micro-Networks & Ensemble

Apply to real market data. Each micro-network is tiny (3-10 processing neurons).

### C1: Single-Indicator Micro-Networks — Candles Only
**Depends:** B2a
**Scope:**
- Micro-network (input: OHLCV for one token, output: next N-candle direction)
- Best architecture from Group B
- Start with BTC 15-min candles, then BONK, WIF
- Prediction horizons: 5, 10, 50 candles
- Use data from microcap swing data pipeline (already downloaded)
- Record: accuracy, energy efficiency, topology that emerges, firing patterns
**Acceptance:**
- [ ] Non-random signal detected (significantly above 50% on binary direction)
- [ ] Energy model behaves sensibly on real data
- [ ] Firing patterns documented per token

### C2a: Single-Indicator Micro-Networks — Indicator Only (Various Formats)
**Depends:** C1
**Scope:**
- One micro-network per indicator, taking ONLY the indicator as input (no candle data)
- Indicators: RSI, MACD, OBV, Bollinger %B, Volume ROC, ATR, Fear & Greed
- Test multiple input encoding formats per indicator:
  - Raw value
  - Normalized/z-scored
  - Rate of change
  - Discretized (binned)
- Same architecture, same energy budget, same prediction target as C1
- Which indicators produce signal on their own? Which input format works best?
**Acceptance:**
- [ ] All indicator networks trained and evaluated
- [ ] Ranking by accuracy and energy efficiency
- [ ] Best input format identified per indicator
- [ ] Topology comparison across indicators

### C2b: Paired Micro-Networks — Single Indicator + Candle Data (Various Formats)
**Depends:** C1
**Scope:**
- One micro-network per indicator, taking indicator + corresponding OHLCV candle data together
- Same indicator set as C2a
- Test input format combinations:
  - Raw indicator + raw candles
  - Normalized indicator + normalized candles
  - Indicator ROC + candle ROC
- Key question: does adding candle context improve indicator signal? By how much?
- Compare directly against C2a (indicator-only) and C1 (candle-only)
**Acceptance:**
- [ ] All paired networks trained and evaluated
- [ ] Comparison vs C2a: does adding candles help each indicator?
- [ ] Comparison vs C1: does adding an indicator help candle-only?
- [ ] Best pairing format identified per indicator

### C3: Micro-Network Ensemble — Combine Trained Specialists
**Depends:** C1, C2a, C2b
**Scope:**
- Feed spike outputs from all trained micro-networks into a combiner network
- Compare combination methods:
  - Simple majority vote
  - Learned combination (another SNN layer)
  - Frequency-weighted combination (higher-confidence = higher firing rate = more weight)
  - Energy-weighted (more energy-efficient networks get more say)
- Does ensemble beat every individual?
**Acceptance:**
- [ ] Ensemble accuracy vs best individual documented
- [ ] Best combination method identified
- [ ] Analysis: which indicators agree/disagree and when

---

## Group D: Monolithic Comparison

### D1: All-Indicators Monolithic Network
**Depends:** B2a
**Scope:**
- Single larger network takes ALL indicators as input simultaneously
- Same energy and topology rules, just bigger processing cluster
- Larger network (20-50 processing neurons)
- Same prediction targets as C1/C2a/C2b
**Acceptance:**
- [ ] Network trains and converges
- [ ] Accuracy and energy metrics comparable with ensemble

### D2: Ensemble vs Monolithic Comparison
**Depends:** C3, D1
**Scope:**
- Head-to-head: ensemble of specialists vs monolithic network
- Compare: accuracy, energy efficiency, interpretability, adaptation speed to regime changes
- Key question: does modular beat end-to-end for this architecture?
**Acceptance:**
- [ ] Clear winner identified (or conditions where each wins)
- [ ] Topology analysis: does monolithic rediscover indicator-specific patterns?

---

## Group E: Multi-Horizon

### E1: Multi-Horizon Prediction — 5/10/50 Candle Windows
**Depends:** D2
**Scope:**
- Best config from D2 tested at 5, 10, 50 candle prediction horizons
- 15-min candles (so: 1.25hr, 2.5hr, 12.5hr horizons)
- 1-hour candles (so: 5hr, 10hr, 50hr horizons)
- Does the architecture find stronger signal at longer horizons?
**Acceptance:**
- [ ] Accuracy vs horizon curve
- [ ] Best horizon identified per token

### E2: Energy-Optimal Spike Rates Across Horizons
**Depends:** E1
**Scope:**
- How does energy-optimal firing rate change with prediction horizon?
- Do longer horizons produce different topology?
- Hypothesis: longer horizons → sparser, more selective firing
**Acceptance:**
- [ ] Firing rate vs horizon analysis
- [ ] Topology comparison across horizons

---

## Group F: Synthesis

### F1: Research Synthesis & Architecture Recommendations
**Depends:** D2, E2
**Scope:**
- Full report: what worked, what didn't, recommended architecture for production
- Feature survival analysis (which indicators/topologies survived energy pressure)
- Recommended next steps: production hardening, additional experiments, or pivot
**Acceptance:**
- [ ] Comprehensive report
- [ ] Clear go/no-go recommendation for production architecture
