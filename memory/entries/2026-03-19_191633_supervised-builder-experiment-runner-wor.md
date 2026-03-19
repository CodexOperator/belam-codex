---
primitive: memory_log
timestamp: "2026-03-19T19:16:33Z"
category: technical
importance: 4
tags: [infrastructure, experiments, builder, supervised-runner]
source: "session"
content: "Supervised builder experiment runner works. Key changes: (1) run_experiment.py rewritten — default mode spawns builder agent to own entire experiment lifecycle (read notebook, create standalone runner, execute, fix bugs, create primitives, report completion). --direct flag for unsupervised fallback. (2) Root cause of stack-specialists and validate-scheme-b failures: papermill detection bug (subprocess.run doesn't raise on non-zero exit, was setting papermill_available=True incorrectly) + builder recovery used wrong CLI syntax (openclaw gateway sessions send --agent doesn't exist, correct is openclaw agent --agent). (3) Fixed RESULTS_BASE missing from pipeline_autorun.py, added all local analysis stages to agent_actions sets, added failed experiment retry detection. (4) Convention: experiments always run through supervised builder by default — builder creates run_supervised.py, executes, fixes bugs inline, creates primitives for findings."
status: consolidated
---

# Memory Entry

**2026-03-19T19:16:33Z** · `technical` · importance 4/5

Supervised builder experiment runner works. Key changes: (1) run_experiment.py rewritten — default mode spawns builder agent to own entire experiment lifecycle (read notebook, create standalone runner, execute, fix bugs, create primitives, report completion). --direct flag for unsupervised fallback. (2) Root cause of stack-specialists and validate-scheme-b failures: papermill detection bug (subprocess.run doesn't raise on non-zero exit, was setting papermill_available=True incorrectly) + builder recovery used wrong CLI syntax (openclaw gateway sessions send --agent doesn't exist, correct is openclaw agent --agent). (3) Fixed RESULTS_BASE missing from pipeline_autorun.py, added all local analysis stages to agent_actions sets, added failed experiment retry detection. (4) Convention: experiments always run through supervised builder by default — builder creates run_supervised.py, executes, fixes bugs inline, creates primitives for findings.

---
*Source: session*
*Tags: infrastructure, experiments, builder, supervised-runner*
