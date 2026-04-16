---
primitive: decision
status: implemented
date: 2026-04-13
importance: 3
context: Hermes migration — need orchestration engine to configure spawned agents with platform-specific runtime settings (toolsets, personas, dispatch method) defined in pipeline templates
alternatives: [hardcode runtime config per agent in orchestration engine, pass runtime config via env vars at spawn time]
rationale: Templates already define pipeline structure; extending them with runtime blocks keeps all pipeline configuration co-located and declarative
consequences: [dispatch payloads now carry full runtime context, agents can be configured per-role from template YAML, startup_view hints guide agent orientation]
upstream: [decision:template-aware-pipeline-orchestration, lesson:orchestration-dispatch-payload-spawn-relay]
downstream: []
tags: [instance:main, orchestration, dispatch, templates, runtime, hermes-migration]
---

# runtime-aware-dispatch-from-template-metadata

## Context

Pipeline templates define stage transitions and agent roles but had no way to specify *how* agents should be configured at dispatch time — what platform they run on, what toolsets they need, what persona to adopt. During Hermes migration, the orchestration engine needed to propagate this runtime configuration through the dispatch → spawn lifecycle.

## Decision

Pipeline templates now include an optional `runtime:` YAML block specifying platform, dispatch_tool, codex_cli_enabled, and per-role configuration (toolsets, persona). The template parser preserves this block in its output. The orchestration engine caches template runtime metadata and exposes helpers (`_get_template_runtime()`, `_get_runtime_role_config()`). `build_dispatch_payload()` reads role config from `runtime.roles`, injects toolsets/persona into `view_filter`, and adds a `startup_view` instruction to the task prompt.

## Implementation

- **template_parser.py**: `runtime` key preserved in parser output for both phase-based and legacy parse paths. Test coverage added.
- **orchestration_engine.py**: Runtime cache + helpers added. DispatchPayload extended with `runtime` and `startup_view` fields. Payload builder reads role config and injects into context.

## Consequences

- Agents receive role-specific configuration declaratively from templates
- No hardcoded runtime assumptions in orchestration engine
- Templates become the single source of truth for both pipeline structure AND agent configuration
- Enables different platforms (OpenClaw, Hermes) to coexist in the same orchestration layer
