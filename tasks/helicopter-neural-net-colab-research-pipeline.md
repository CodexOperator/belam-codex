---
primitive: task
status: open
priority: high
created: 2026-04-27
owner: belam
project: machinelearning-school
depends_on: []
upstream: []
downstream: []
tags: [machinelearning, school, colab, neural-nets, helicopter, research]
pipeline_template: research
launch_mode: queued
---

# helicopter neural net colab research pipeline

## Description

Build a Colab-ready research notebook for the helicopter dataset in `machinelearning/school/helicopter_nn/`.

Main objectives:
- fit one neural net for `spun` classification
- fit one neural net for `fall_time` regression
- document architecture choices and training methodology clearly
- compare tiny MLP architectures against simple baselines
- generate interpretable conclusions with honest discussion of small-data limits

Existing repo artifacts already prepared:
- `machinelearning/school/helicopter_nn/helicopter_nn_brainstorm_starter.ipynb`
- `machinelearning/school/helicopter_nn/data/helicopterData-page1.csv.zip`
- `machinelearning/school/helicopter_nn/docs/design_doc.md`

## Acceptance Criteria

- [ ] notebook runs in Google Colab from GitHub
- [ ] notebook supports zipped CSV input from repo or upload fallback
- [ ] baseline models included before neural nets
- [ ] neural net search compares small architectures only
- [ ] activation comparison includes ReLU vs tanh
- [ ] methodology section explains layers, widths, activations, training, regularization, CV, and metrics
- [ ] results section compares classification and regression performance clearly
- [ ] interpretation section discusses what is and is not learnable from this sparse dataset
- [ ] notebook and docs remain committed in `machinelearning/school/helicopter_nn/`

## Notes

Desired research posture:
- rigor over complexity
- repeated cross-validation, not one lucky split
- avoid giant networks
- if simple baselines match MLPs, say so explicitly

Current concern:
OpenClaw cockpit research pipeline scripts appear partially hardcoded to `machinelearning/snn_applied_finance/`, so generic multi-agent kickoff for this `school/helicopter_nn` path may require adaptation before safe orchestrated launch.
