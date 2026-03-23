---
primitive: memory_log
timestamp: "2026-03-23T22:20:44Z"
category: technical
importance: 3
tags: [instance:main, pipeline, experiment, recovery]
source: "session"
content: "Dead-PID experiment recovery fix: check_running_experiments() detected dead process with complete results but never updated pipeline status. Now transitions status to experiment_complete when results_summary.json exists in results dir (in addition to checking _experiment_results.md in builds dir). Also auto-kicks analysis gate on detection."
status: consolidated
---

# Memory Entry

**2026-03-23T22:20:44Z** · `technical` · importance 3/5

Dead-PID experiment recovery fix: check_running_experiments() detected dead process with complete results but never updated pipeline status. Now transitions status to experiment_complete when results_summary.json exists in results dir (in addition to checking _experiment_results.md in builds dir). Also auto-kicks analysis gate on detection.

---
*Source: session*
*Tags: instance:main, pipeline, experiment, recovery*
