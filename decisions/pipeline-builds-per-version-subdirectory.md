---
primitive: decision
status: accepted
created: 2026-03-23
importance: 4
tags: [pipeline, convention, infrastructure]
promotion_status: exploratory
doctrine_richness: 7
contradicts: []
---

# Pipeline Builds: Per-Version Subdirectories

## Decision

Migrate `pipeline_builds/` from flat prefixed files to per-version subdirectories with standardized filenames.

## Before (flat)
```
pipeline_builds/
  codex-engine-v4-ram-first-..._phase2_direction.md
  codex-engine-v4-ram-first-..._critic_design_review.md
  codex-engine-v4-ram-first-..._state.json
  validate-scheme-b_phase2_direction.md
```

## After (structured)
```
pipeline_builds/
  codex-engine-v4-ram-first-.../
    phase2_direction.md
    critic_design_review.md
    _state.json
  validate-scheme-b/
    phase2_direction.md
```

## Standard Filenames

Within each `pipeline_builds/{version}/` directory:

| File | Purpose |
|------|---------|
| `_state.json` | Pipeline state (stages, timestamps, pending_action) |
| `architect_design.md` | Phase 1 architect design document |
| `critic_design_review.md` | Phase 1 critic design review |
| `critic_code_review.md` | Phase 1 critic code review |
| `phase2_direction.md` | Human direction for Phase 2 (triggers gate) |
| `phase2_architect_design.md` | Phase 2 architect design |
| `phase2_critic_design_review.md` | Phase 2 critic design review |
| `phase2_critic_code_review.md` | Phase 2 critic code review |
| `revision_request.md` | Revision request (triggers revision gate) |
| `agent_context.json` | Agent context backup |
| `experiment_results.md` | Experiment output summary |
| `local_analysis.md` | Local analysis results |

## Naming Rules
- No user names in filenames (drop `_shael_` convention)
- No pipeline version prefix in filenames (directory IS the version)
- Underscore-prefixed files (`_state.json`) are machine-managed
- Phase prefix (`phase2_`, `phase3_iter1_`) only when distinguishing from Phase 1

## Migration
- Add `_find_build_artifact()` helper that checks both old flat path and new directory path
- Migrate scripts to use `BUILDS_DIR / version / filename` pattern
- Move existing files into subdirectories
- Keep backward compatibility during transition
