# Phase-Based Orchestration Refactor — Implementation Summary

## Date: 2025-03-25

## What Changed

### Core Architecture
Replaced hardcoded stage transition dicts with a **phase-based template format**. Pipelines are now defined as numbered phase containers in YAML, with deterministic stage name generation (`p{N}_{role}_{action}`).

### Files Modified

#### 1. `templates/builder-first-pipeline.md`
- Rewrote YAML block to use `phases:` format
- 2 phases: Phase 1 (builder-first implementation), Phase 2 (architect-led refinement)
- Both phases have `gate: human`
- Block routing: critic review → builder fix
- Stage names: `p1_builder_implement`, `p1_builder_bugfix`, `p1_critic_review`, `p1_complete`, `p2_architect_design`, etc.

#### 2. `templates/research-pipeline.md`
- Rewrote YAML block to use `phases:` format
- 4 phases:
  - Phase 1: Design + Build (`gate: auto` → auto-transitions to Phase 2)
  - Phase 2: Local Experiment + Analysis (`gate: human`)
  - Phase 3: Refinement (`gate: human`)
  - Phase 4: Iteration (`gate: human`)
- Block routing: critic design_review → architect, critic code_review → builder, critic analysis_review → architect, critic analysis_code_review → builder, critic review → architect
- Stage names: `p1_architect_design`, `p2_system_experiment_run`, `p3_builder_implement`, `p4_critic_code_review`, etc.

#### 3. `scripts/template_parser.py`
- Added `_parse_phase_based()` — parses the new `phases:` YAML format
- Generates: transitions, block_transitions, status_bumps, start_status_bumps, human_gates
- Stage name generation: `p{N}_{role}_{action}` for stages, `p{N}_complete` for phase ends
- `pipeline_created` → first stage of phase 1
- Auto gates (`gate: auto`): `p{N}_complete` transitions directly to `p{N+1}_first_stage`
- Human gates (`gate: human`): transition exists but pipeline pauses
- Block routing: generates `p{N}_{role}_fix_blocks` stages that route back to the blocking critic
- Added `LEGACY_STAGE_MAP` for backward compatibility with existing pipeline files
- Added `resolve_stage_name()` for bidirectional legacy↔new name resolution
- Preserved legacy format parser (`_parse_legacy_yaml`, `_parse_manually`) — old templates still work

#### 4. `scripts/pipeline_update.py`
- **Removed** 3 giant hardcoded dicts: `STAGE_TRANSITIONS`, `BLOCK_TRANSITIONS`, `STATUS_BUMPS`, `START_STATUS_BUMPS` (replaced with empty dicts for import compat)
- `get_transitions_for_pipeline()` now ALWAYS resolves from template
  - Maps `type: research` → research template, `type: builder-first` → builder-first template
  - Default (no type) → research template
- Updated `detect_phase()` to handle both `p{N}_` prefix (new) and `phase{N}_` prefix (legacy)
- Added `PHASE_SECTION_PATTERNS` for Phase 4
- Kept all function signatures identical — downstream code unchanged

#### 5. `scripts/pipeline_orchestrate.py`
- `kickoff` command now accepts `--phase N` (generic) in addition to `--phase2` (backward compat)
- Phase gate resolution is generic: finds `p{N-1}_complete` or legacy gate names
- Direction file detection supports `phase{N}_direction.md` pattern
- Updated `VERIFICATION_STAGES` to include new `p{N}_builder_verify` names
- Updated `STAGE_FLOW` dict with comments for legacy vs phase-based names
- Phase gate fallback: when a `_complete` stage has no transition, constructs generic `p{N+1}_architect_design` transition
- Legacy stage name resolution via `template_parser.resolve_stage_name()`

### New Files

#### `scripts/tests/test_template_parser.py`
- 17 tests covering: parsing, stage names, transitions, gates, sessions, blocks, chains, legacy resolution
- All passing

## Backward Compatibility

### Existing Pipeline Files
- Pipeline files with old stage names (e.g., `pending_action: architect_design`) still work
- `resolve_stage_name()` maps legacy names to phase-based names bidirectionally
- `detect_phase()` handles both old (`phase2_*`) and new (`p2_*`) name formats
- Empty global dicts (`STAGE_TRANSITIONS`, etc.) kept for import compatibility

### CLI Commands
- `--phase2` still works (maps to `--phase 2`)
- `kickoff` auto-detects phase from pipeline status (unchanged behavior)

## Key Properties

| Property | Details |
|----------|---------|
| Stage naming | `p{N}_{role}_{action}` |
| Phase completion | `p{N}_complete` |
| Auto gate | `gate: auto` → transitions to next phase automatically |
| Human gate | `gate: human` → pauses for manual kick |
| Block routing | `block_routing:` section in template YAML |
| Arbitrary phases | Just add phase N+1 to template |
| Complete-task | Available at any human gate |

## How to Verify

```bash
cd /home/ubuntu/.openclaw/workspace
python3 scripts/template_parser.py          # Dump both templates
python3 -m pytest scripts/tests/ -v         # 17 tests pass
python3 scripts/tests/test_verify_parser.py # Legacy test still passes
```
