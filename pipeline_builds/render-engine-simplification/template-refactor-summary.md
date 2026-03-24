# Template Execution Wrapper Refactor — Summary

## Date: 2026-03-24

## Goal
Make `scripts/orchestration_engine.py` a pure template execution wrapper with NO hardcoded stage transitions, human gates, or agent action sets. All pipeline behavior now flows from template markdown files in `templates/`.

---

## Changes Made

### 1. `scripts/orchestration_engine.py` — Core Refactor

#### Removed: Hardcoded `AGENT_ACTIONS` set (was at line ~93)
- **Before:** 28-element hardcoded set of agent action stage names
- **After:** `_get_agent_actions()` function — lazy-loads by scanning all `templates/*-pipeline.md` files, collecting every stage whose transition targets a non-system agent
- Module-level `AGENT_ACTIONS = None` kept as a sentinel (any stale `in AGENT_ACTIONS` will TypeError)

#### Removed: Hardcoded `HUMAN_ACTIONS` set (was at line ~111)
- **Before:** 6-element hardcoded set (`ready_for_colab_run`, `phase1_complete`, `phase2_complete`, `phase3_complete`, `pipeline_created`, `local_analysis_complete`)
- **After:** `_get_human_actions()` function — lazy-loads by scanning all templates, collecting every stage tagged with `gate: human`
- Template-derived set: `{phase1_complete, phase2_complete, phase3_complete, local_analysis_complete}`
- `pipeline_created` removed (not a gate — transitions to architect_design)
- `ready_for_colab_run` removed (legacy, not in any template)

#### Removed: `from pipeline_update import STAGE_TRANSITIONS` fallback
- **Before:** `resolve_transition()` fell back to `STAGE_TRANSITIONS` dict from pipeline_update.py
- **After:** Uses templates exclusively: pipeline's own template → research template as default → None
- `_next_stage_for()` also cleaned: no more `STAGE_TRANSITIONS` import, falls back to research template when no version provided

#### Added: `_resolve_template_name(pipeline_type)` helper
- Maps pipeline types to template names:
  - `None` / `research` / `infrastructure` → `'research'`
  - Other types (e.g. `builder-first`) → themselves

#### Added: `resolve_status_bump(version, stage)` function
- Resolves status bumps from template `status_bumps:` section
- Same cascade: pipeline's template → research fallback

#### Added: `resolve_start_status_bump(version, stage)` function
- Resolves start-of-stage status bumps from template `start_status_bumps:` section
- Same cascade: pipeline's template → research fallback

#### Added: `_load_all_template_gates()` function
- Scans `templates/*-pipeline.md` glob
- Populates `_dynamic_human_actions` and `_dynamic_agent_actions` sets
- Lazy-loaded on first access, cached thereafter

#### Updated: `_parse_template_transitions()` 
- Now parses three sections from yaml block: `transitions:`, `status_bumps:`, `start_status_bumps:`
- Uses section-aware state machine instead of assuming only `transitions:` exists
- Populates `_template_status_bumps` and `_template_start_status_bumps` caches

#### Updated: `is_human_gated(version, stage)`
- No longer checks hardcoded `HUMAN_ACTIONS`
- Checks pipeline-specific template gates first, then global union of all template gates

#### Updated: All `in HUMAN_ACTIONS` / `in AGENT_ACTIONS` references (6 locations)
- Replaced with `in _get_human_actions()` / `in _get_agent_actions()`
- Locations: `_post_state_change`, `_diagnose_pending`, `_agent_from_action`, `check_gates`, `check_stalls`

### 2. `templates/research-pipeline.md` — Made Authoritative

#### Added: `status_bumps:` section (31 entries)
- Mirrors all entries from `pipeline_update.py`'s `STATUS_BUMPS` dict
- Covers Phase 1, Phase 1 revisions, local experiment, local analysis, Phase 2, Phase 3, Analysis Phase 1 & 2

#### Added: `start_status_bumps:` section (23 entries)
- Mirrors all entries from `pipeline_update.py`'s `START_STATUS_BUMPS` dict
- Covers local analysis, analysis Phase 2, Phase 1 revision, local experiment, Phase 2, Phase 3

#### Fixed: Missing `gate: human` tags
- `critic_code_review` transition → `phase1_complete` now tagged `gate: human`
- `phase1_revision_code_review` transition → `phase1_complete` now tagged `gate: human`
- These were in the old hardcoded `HUMAN_ACTIONS` set but missing from the template

### 3. `templates/builder-first-pipeline.md` — Extended

#### Added: `status_bumps:` section (8 entries)
- Phase 1 and Phase 2 status bumps for builder-first pipeline stages

#### Added: `start_status_bumps:` section (2 entries)
- Start bumps for builder and Phase 2 builder stages

---

## What's NOT Changed

- **`scripts/pipeline_update.py`** — untouched. `STAGE_TRANSITIONS`, `STATUS_BUMPS`, `START_STATUS_BUMPS`, and `BLOCK_TRANSITIONS` dicts remain as-is. They're now dead code for orchestration_engine resolution but still used internally by pipeline_update.py itself for its own `cmd_complete`/`cmd_start`/`cmd_block` functions.
- **`BLOCK_TRANSITIONS`** — still imported from pipeline_update.py in `_block_target_for()`. Block transitions could be templatized in a future pass.
- **`STAGE_SEQUENCE`** — kept as positional last-resort fallback in `_next_stage_for()`.
- **Template cache mechanism** — preserved and extended (now caches transitions + gates + status_bumps + start_status_bumps per template).

## Verification

- `python3 -c "import py_compile; py_compile.compile('scripts/orchestration_engine.py', doraise=True)"` — ✅ compiles clean
- All 50 research template transitions parse correctly
- All 10 builder-first template transitions parse correctly
- Dynamic human actions: `{phase1_complete, phase2_complete, phase3_complete, local_analysis_complete}`
- Dynamic agent actions: 36 stages (all non-system transition targets)
- `resolve_status_bump` and `resolve_start_status_bump` return correct values
- `is_human_gated` works correctly for both known and unknown pipelines
- `_next_stage_for` works without version (falls back to research template)

## Architecture After Refactor

```
templates/*-pipeline.md    ← Source of truth for all pipeline behavior
       │
       ├── transitions       → resolve_transition(), _next_stage_for()
       ├── gate: human tags  → is_human_gated(), _get_human_actions()
       ├── agent assignments → _get_agent_actions()
       ├── status_bumps      → resolve_status_bump()
       └── start_status_bumps → resolve_start_status_bump()
       
scripts/orchestration_engine.py  ← Pure template executor (no hardcoded transitions)
scripts/pipeline_update.py       ← Still has dicts (dead for OE, used internally)
```
