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
subtasks: ["{'id': 'A1', 'title': 'Energy-Aware LIF Neuron — Base Implementation', 'status': 'open', 'depends_on': []}", "{'id': 'A2', 'title': 'Frequency Matching Loss Function', 'status': 'open', 'depends_on': ['A1']}", "{'id': 'A3', 'title': 'Frequency Band Quantization', 'status': 'open', 'depends_on': ['A2']}", "{'id': 'A4', 'title': 'Differential Output Under Energy Pressure', 'status': 'open', 'depends_on': ['A1', 'A2']}", "{'id': 'A5', 'title': 'Pull-Only Connection Dynamics', 'status': 'open', 'depends_on': ['A1']}", "{'id': 'B1', 'title': 'Architecture Baseline — Fixed Feedforward SNN', 'status': 'open', 'depends_on': ['A1', 'A2', 'A3']}", "{'id': 'B2', 'title': 'Self-Organizing Processing Cluster — Variant A (output reads processing only)', 'status': 'open', 'depends_on': ['A5', 'B1']}", "{'id': 'B3', 'title': 'Self-Organizing Processing Cluster — Variant B (output reads processing + input)', 'status': 'open', 'depends_on': ['B2']}", "{'id': 'B4', 'title': 'Connection Limits & Scaling — Max K Connections', 'status': 'open', 'depends_on': ['B2']}", "{'id': 'C1', 'title': 'Single-Indicator Micro-Networks — Candles Only', 'status': 'open', 'depends_on': ['B2']}", "{'id': 'C2', 'title': 'Single-Indicator Micro-Networks — Individual Indicators', 'status': 'open', 'depends_on': ['C1']}", "{'id': 'C3', 'title': 'Micro-Network Ensemble — Combine Trained Specialists', 'status': 'open', 'depends_on': ['C1', 'C2']}", "{'id': 'D1', 'title': 'All-Indicators Monolithic Network', 'status': 'open', 'depends_on': ['B2']}", "{'id': 'D2', 'title': 'Ensemble vs Monolithic Comparison', 'status': 'open', 'depends_on': ['C3', 'D1']}", "{'id': 'E1', 'title': 'Multi-Horizon Prediction — 5/10/50 Candle Windows', 'status': 'open', 'depends_on': ['D2']}", "{'id': 'E2', 'title': 'Energy-Optimal Spike Rates Across Horizons', 'status': 'open', 'depends_on': ['E1']}", "{'id': 'F1', 'title': 'Research Synthesis & Architecture Recommendations', 'status': 'open', 'depends_on': ['D2', 'E2']}"]
---

# SNN Energy-Topology Research — Subtask Breakdown

Master task for the energy-aware, self-organizing SNN architecture research.

## Project Reference
`projects/snn-energy-topology-research.md`

---

## Group A: Core Neuron Mechanics (Foundation)

Everything else is gated on this group. If energy-aware frequency matching doesn't produce meaningful behavior on synthetic signals, we retool before using market data.

### A1: Energy-Aware LIF Neuron — Base Implementation
**Depends:** None
**Scope:**
- Pure PyTorch implementation of a leaky integrate-and-fire neuron with energy accounting
- Energy costs: spike emission (high), spike reception (low), connection maintenance (low/ongoing)
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

### A5: Pull-Only Connection Dynamics
**Depends:** A1
**Scope:**
- Implement connection formation/breaking mechanism: per-batch topology updates
- Each neuron decides which inputs to subscribe to (pull-only)
- Connection cost: forming costs energy, maintenance is ongoing drain, breaking is free
- Unused connections (low signal contribution) naturally decay when energy budget is tight
- Per-sample weight adjustment (fine-tune within batch)
- Per-batch structural adjustment (subscribe/unsubscribe)
- Enforce layer rules: processing can't connect to output, input doesn't initiate
- Test on small (5-10 neuron) processing cluster: do stable connection patterns emerge?
**Acceptance:**
- [ ] Connections form and break based on energy economics
- [ ] Layer rules enforced (no illegal connections)
- [ ] Stable topology emerges after training on consistent signal
- [ ] Topology changes when signal characteristics change

---

## Group B: Architecture Variants

Test topology variants on synthetic signal detection before market data.

### B1: Architecture Baseline — Fixed Feedforward SNN
**Depends:** A1, A2, A3
**Scope:**
- Standard feedforward SNN with energy-aware neurons but NO self-organizing topology
- Fixed architecture: Input → Hidden → Output
- Same energy model and frequency matching as custom variants
- This is the control group — how much does self-organization add?
- Test on: synthetic time series with regime changes, simple pattern detection
**Acceptance:**
- [ ] Baseline accuracy and energy metrics established
- [ ] Comparison framework ready (metrics: accuracy, energy efficiency, adaptation speed)

### B2: Self-Organizing Processing Cluster — Variant A
**Depends:** A5, B1
**Scope:**
- Full architecture: Input (broadcast) → Processing cluster (self-organizing) → Output (reads processing only)
- Processing neurons subscribe to input and each other (pull-only)
- Output neurons subscribe to processing neurons only
- All connection rules enforced
- Same synthetic tests as B1 for direct comparison
- Analyze: what topology emerges? Do processing neurons specialize?
**Acceptance:**
- [ ] Network trains and converges
- [ ] Outperforms or matches B1 baseline
- [ ] Topology analysis: connection graph visualization, neuron specialization metrics
- [ ] Energy efficiency comparison vs B1

### B3: Self-Organizing Processing Cluster — Variant B
**Depends:** B2
**Scope:**
- Same as B2 but output neurons can also subscribe to input neurons directly
- Compare: does direct input access help or hurt output quality?
- Hypothesis: might help for simple signals, hurt for complex ones (bypasses processing)
**Acceptance:**
- [ ] Direct comparison with B2 on same test suite
- [ ] Analysis of when/why output neurons choose to read input directly vs through processing

### B4: Connection Limits & Scaling — Max K Connections
**Depends:** B2
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

Now apply to real market data. Each micro-network is tiny (3-10 processing neurons).

### C1: Single-Indicator Micro-Networks — Candles Only
**Depends:** B2
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

### C2: Single-Indicator Micro-Networks — Individual Indicators
**Depends:** C1
**Scope:**
- One micro-network per indicator: RSI, MACD, OBV, Bollinger %B, Volume ROC, ATR, Fear & Greed
- Same architecture, same energy budget, same prediction target as C1
- Which indicators produce the strongest individual signal?
- Do different indicators produce different topology patterns?
**Acceptance:**
- [ ] All indicator networks trained and evaluated
- [ ] Ranking by accuracy and energy efficiency
- [ ] Topology comparison across indicators

### C3: Micro-Network Ensemble — Combine Trained Specialists
**Depends:** C1, C2
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
**Depends:** B2
**Scope:**
- Single larger network takes ALL indicators as input simultaneously
- Same energy and topology rules, just bigger processing cluster
- Larger network (20-50 processing neurons)
- Same prediction targets as C1/C2
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
