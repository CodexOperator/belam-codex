---
primitive: decision
status: accepted
date: 2026-03-23
context: research-openclaw-internals (infrastructure pipeline) ran through local_analysis stages; Shael asked why an infra pipeline was doing local analysis
alternatives:
  - "Option 1: Allow infra pipelines to use local_analysis (chosen)"
  - "Option 2: Add type-gate to skip local_analysis for infrastructure pipelines"
rationale: Sometimes additional analysis passes are valuable for infrastructure work too; local_analysis should be general-purpose, not research-only
consequences:
  - infrastructure pipelines can legitimately reach local_analysis_complete status
  - pipeline_autorun.py should not type-gate analysis eligibility
  - no code change needed to filter out infra pipelines from analysis flow
upstream: []
downstream: []
tags: [instance:main, pipeline, infrastructure, local-analysis]
---

# infra-pipelines-use-local-analysis

## Context

`research-openclaw-internals` (an infrastructure pipeline, not a research/SNN pipeline) ran through `local_analysis` stages after its experiments completed. Shael noticed this and asked why — since local_analysis was primarily designed for SNN research pipelines to analyze numerical results.

## Options Considered

- **Option 1:** Allow infrastructure pipelines to use local_analysis stages (keep existing behavior)
- **Option 2:** Add a `type: infrastructure` gate in `check_experiment_eligible` and `check_analysis_eligible` to skip analysis for infra pipelines

## Decision

**Option 1** — infrastructure pipelines are allowed to run local_analysis. The stage is general-purpose. There are valid cases where additional analysis passes add value even for infrastructure work.

## Consequences

- `local_analysis_complete` is a valid terminal status for infrastructure pipelines
- No type-based filtering added to `pipeline_autorun.py` analysis eligibility checks
- Keeps the pipeline framework uniform across pipeline types
