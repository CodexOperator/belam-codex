---
primitive: decision
status: accepted
date: 2026-03-19
context: Experiment runner failed on 2/3 pipelines due to fragile mechanical execution and broken error recovery
alternatives: [direct notebook execution, reactive builder recovery, manual Colab]
rationale: Proactive supervision catches bugs before they crash, creates knowledge, and self-heals
consequences: [self-healing experiments, automatic primitive creation, builder busy during runs, one-at-a-time enforced]
tags: [infrastructure, experiments, builder, architecture]
promotion_status: candidate
doctrine_richness: 9
contradicts: []
---

# Supervised Builder Agent for Experiment Execution

## Context

`run_experiment.py` originally tried to mechanically execute notebooks via papermill/nbconvert, then reactively spawned a builder agent to fix errors after crashes. This failed for stack-specialists and validate-scheme-b: (1) papermill detection bug (`subprocess.run` doesn't raise on non-zero exit — was setting `papermill_available=True` incorrectly), (2) reactive recovery used wrong CLI syntax (`openclaw gateway sessions send --agent` doesn't exist; correct is `openclaw agent --agent`).

## Options Considered

- **Direct notebook execution** (papermill/nbconvert): Fragile, no error recovery, no learning. Kept as `--direct` fallback.
- **Reactive builder recovery** (original): Builder only sees errors after crash, no context about experiment design, can't proactively validate.
- **Manual Colab execution**: Works but wastes Shael's time on mechanical tasks.
- **Supervised builder** (chosen): Builder owns the full lifecycle proactively.

## Decision

Default experiment execution mode is **supervised builder**: spawn a builder agent that owns the entire experiment lifecycle. The builder reads the notebook, creates a standalone runner script (`run_supervised.py`), executes experiments, fixes bugs inline, creates primitives for findings, and self-reports completion via orchestrator.

## Consequences

- Experiments self-heal: bugs get fixed without human intervention
- Knowledge capture: builder creates lesson/decision primitives from findings
- Slower startup (builder reads notebook first) but faster overall (no crash-retry-crash cycles)
- Builder agent is busy during experiment runs — one pipeline at a time enforced
- `--direct` flag available for simple re-runs where the builder-created `run_supervised.py` already exists
