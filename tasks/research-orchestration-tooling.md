---
primitive: task
status: superseded
priority: high
created: 2026-03-21
owner: belam
project: multi-agent-infrastructure
depends_on: []
upstream: []
downstream: []
tags: [orchestration, research, mcp, frameworks]
superseded_by: build-orchestration-engine-v1
---

# research-orchestration-tooling

**SUPERSEDED** — Research findings from `research-openclaw-internals` pipeline landed. Remaining tooling research folded into `build-orchestration-engine-v1` as prerequisite hook integration work.

## Key Findings (from research-openclaw-internals pipeline)

See: `machinelearning/snn_applied_finance/research/pipeline_builds/research-openclaw-internals_builder_reference.md`

- 27 hooks cataloged (11 internal colon-separated, 16 plugin underscore-separated)
- `before_prompt_build` = highest-leverage integration point for pipeline context injection
- 3 plugin prototypes delivered: pipeline-context, pipeline-commands, agent-turn-logger
- Hook naming convention mismatch (colons vs underscores) is a silent-failure trap
- `registerContextEngine` available for full context pipeline replacement (nuclear option)
