# Phase 2 Entry Fix — Test Results

**Date:** 2026-03-25
**Task:** Remove hardcoded Phase 2 entry fallback in pipeline_orchestrate.py

## Changes Made

### 1. `scripts/pipeline_orchestrate.py`
Replaced hardcoded fallback in `orchestrate_complete()` with template-aware resolution:
- First queries the template's `stage_trans` (already loaded for the pipeline) for the human gate stage
- Uses the template transition if found (correct agent, stage, and message from template)
- Falls back to hardcoded `phase2_architect_design / architect` only if template has no entry for the gate stage

### 2. `templates/builder-first-pipeline.md`
Added `phase1_complete` → `phase2_architect_design` transition:
```yaml
phase1_complete: [phase2_architect_design, architect, "Phase 2 approved. Design phase 2 changes per direction doc.", session: fresh]
```
Human gate behavior preserved: `critic_review → phase1_complete` still has `gate: human` so no auto-dispatch fires.

### 3. `templates/research-pipeline.md`
Added `local_analysis_complete` → `phase2_architect_design` transition:
```yaml
local_analysis_complete: [phase2_architect_design, architect, "Phase 2 approved. Design phase 2 per direction doc.", session: fresh]
```
Note: `phase1_complete` in research template already maps to `local_experiment_running` (correct — research Phase 1 auto-triggers experiments, no human gate here).

## Test Results

```
builder-first phase1_complete → ('phase2_architect_design', 'architect', 'Phase 2 approved. Design phase 2 changes per direction doc.', 'fresh')
research local_analysis_complete → ('phase2_architect_design', 'architect', 'Phase 2 approved. Design phase 2 per direction doc.', 'fresh')
research phase1_complete → ('local_experiment_running', 'system', 'Phase 1 complete. Starting local experiment run.', 'fresh')
```

All transitions resolve correctly. Template parser correctly picks up the new entries.

## Notes

- The direction_note injection still works: the orchestrate code appends `direction_note` to whatever message the template provides
- Builder-first pipelines will now correctly use the template-defined Phase 2 entry (architect), with the message from the template rather than the hardcoded string
- If a new template type is added without a `phase1_complete` transition, the fallback still applies
