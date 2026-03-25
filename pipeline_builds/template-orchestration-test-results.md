# Template-Aware Pipeline Orchestration — Test Results

**Date:** 2026-03-24
**Task:** builder-first-pipeline-template-coordinate
**Status:** ✅ All tests passed

## Files Modified/Created

| File | Action | Status |
|------|--------|--------|
| `scripts/template_parser.py` | **CREATED** | ✅ Parses both templates correctly |
| `scripts/pipeline_update.py` | **MODIFIED** | ✅ `get_transitions_for_pipeline()` added; `cmd_complete`, `cmd_start`, `cmd_block` use dynamic transitions |
| `scripts/pipeline_orchestrate.py` | **MODIFIED** | ✅ `orchestrate_complete()` and `orchestrate_block()` use dynamic transitions |
| `scripts/launch_pipeline.py` | **MODIFIED** | ✅ `--template` flag sets `type:` from template's `pipeline_fields` |

## Test Results

### 1. Template Parser (`template_parser.py`)

| Test | Result |
|------|--------|
| builder-first: 10 transitions, first_agent=builder, 2 human gates | ✅ |
| research: 50 transitions, first_agent=architect, 3 human gates | ✅ |
| Nonexistent template returns None | ✅ |
| Session modes (fresh/continue) correctly parsed | ✅ |
| YAML list parsing handles quoted strings with commas | ✅ |
| `__main__` dumps both templates cleanly | ✅ |

### 2. Dynamic Transition Resolution (`get_transitions_for_pipeline`)

| Test | Result |
|------|--------|
| Nonexistent pipeline → hardcoded STAGE_TRANSITIONS fallback | ✅ |
| builder-first pipeline → template transitions (builder first) | ✅ |
| research type → hardcoded transitions (backward compatible) | ✅ |
| No type field → hardcoded transitions (backward compatible) | ✅ |
| Status bumps from builder-first template | ✅ |
| Start status bumps from builder-first template | ✅ |

### 3. Existing Pipeline Compatibility

| Test | Result |
|------|--------|
| render-engine-simplification (type: builder-first) uses template transitions | ✅ |
| Research pipelines continue using hardcoded transitions | ✅ |
| Hardcoded dicts remain untouched as fallback | ✅ |

### 4. Pipeline Creation (`launch_pipeline.py`)

| Test | Result |
|------|--------|
| `--template builder-first` sets `type: builder-first` in frontmatter | ✅ |
| `--template research` (default) sets `type: research` | ✅ |
| Template's `pipeline_fields.type` used for frontmatter | ✅ |

## Architecture Summary

```
Pipeline frontmatter: type: builder-first
                          ↓
get_transitions_for_pipeline(version)
  ├── Reads type: field from pipelines/{version}.md
  ├── If type in (research, infrastructure, None) → return hardcoded dicts
  └── Else → template_parser.parse_template(type)
              ├── Reads templates/{type}-pipeline.md
              ├── Extracts YAML from ## Stage Transitions
              ├── Returns (transitions, block_transitions, status_bumps, start_status_bumps)
              └── Fallback to hardcoded if parse fails

Callers updated:
  - pipeline_update.py: cmd_complete(), cmd_start(), cmd_block()
  - pipeline_orchestrate.py: orchestrate_complete(), orchestrate_block()
```

## Key Design Decisions

1. **Hardcoded dicts stay as-is** — they're the fallback for research/infrastructure/unknown types
2. **Template parsing uses PyYAML when available**, falls back to regex-based manual parser
3. **`type:` frontmatter field** is the dispatch key — no magic inference needed
4. **Block transitions** fall back to hardcoded `BLOCK_TRANSITIONS` when not defined in template (builder-first template doesn't define block_transitions)
5. **Session mode** is preserved as the 4th tuple element, matching existing `STAGE_TRANSITIONS` shape
6. **Cache** in `template_parser.py` prevents re-parsing on every call
