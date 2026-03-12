# SNN Phase 1 — Colab Visualization Files

## Quick Start

1. **Open Google Colab** → New Notebook → Runtime → Change runtime type → **GPU** (recommended for `output_neuron_dynamics.py`)

2. **Upload files**: Upload `phase1_results.csv` and the Python scripts to `/content/`

3. **Install dependencies** (run in a cell):
   ```python
   !pip install snntorch torch torchvision matplotlib seaborn pandas numpy
   ```

4. **Run the scripts**:
   ```python
   # Phase 1 results visualization (no GPU needed, runs in seconds)
   %run visualize_results.py

   # Output neuron dynamics (trains 1 epoch, ~2.5 min on GPU, ~15 min on CPU)
   %run output_neuron_dynamics.py
   ```

## Files

| File | Description | GPU? | Time |
|------|-------------|------|------|
| `phase1_results.csv` | Raw experiment data: 18 configs (6 betas × 3 step counts) | — | — |
| `visualize_results.py` | Heatmaps + line plots of beta × steps × accuracy/spike density | No | ~5s |
| `output_neuron_dynamics.py` | **Key visualization**: trains SNN, shows evidence accumulation in output neurons | Recommended | ~2.5 min (GPU) |

## Expected Outputs

### From `visualize_results.py`:
- `heatmap_test_accuracy.png` — Beta × steps accuracy heatmap
- `heatmap_spike_density.png` — Beta × steps spike density heatmap
- `line_accuracy_vs_beta.png` — Accuracy curves by step count
- `line_spike_density_vs_beta.png` — Spike density curves by step count
- `line_membrane_variance.png` — Membrane variance explosion (log scale)

### From `output_neuron_dynamics.py`:
- `output_neuron_dynamics.png` — 6-panel visualization showing input, membrane traces, spikes, confidence
- `output_dynamics_animated.gif` — Animated evidence accumulation (if Pillow is available)
- `output_dynamics_example.csv` — Per-step membrane data for all 10 output neurons

## Key Findings (Phase 1.2)

- **Best config**: β=0.99, 25 steps → **96.10% test accuracy**
- **25 steps beats 50 and 100** across ALL beta values
- **Spike density jumps** from ~1-2% to ~3-4% at β ≥ 0.9
- **Membrane variance explodes** with high β + many steps (β=0.99, 100 steps → variance = 86.8!)
- Wall clock scales linearly: ~140s (25 steps), ~240s (50), ~455s (100)
