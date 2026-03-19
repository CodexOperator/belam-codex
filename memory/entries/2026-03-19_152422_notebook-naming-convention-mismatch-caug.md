---
primitive: memory_log
timestamp: "2026-03-19T15:24:22Z"
category: technical
importance: 3
tags: [infrastructure, lesson, naming]
source: "session"
content: "Notebook naming convention mismatch caught: pipeline template used snn_crypto_predictor_{version}.ipynb but actual notebooks are crypto_{version}_predictor.ipynb. Fixed template, all 3 active pipeline frontmatter (output_notebook field), and inline markdown references. The run_experiment.py auto-launcher failed silently on build-equilibrium-snn because of this — always verify output_notebook paths resolve to actual files. Convention going forward: crypto_{version}_predictor.ipynb"
status: consolidated
---

# Memory Entry

**2026-03-19T15:24:22Z** · `technical` · importance 3/5

Notebook naming convention mismatch caught: pipeline template used snn_crypto_predictor_{version}.ipynb but actual notebooks are crypto_{version}_predictor.ipynb. Fixed template, all 3 active pipeline frontmatter (output_notebook field), and inline markdown references. The run_experiment.py auto-launcher failed silently on build-equilibrium-snn because of this — always verify output_notebook paths resolve to actual files. Convention going forward: crypto_{version}_predictor.ipynb

---
*Source: session*
*Tags: infrastructure, lesson, naming*
