---
primitive: task
status: archived
priority: high
created: 2026-03-21
completed: 2026-03-21
owner: belam
project: multi-agent-infrastructure
depends_on: []
upstream: []
downstream: [task/orchestration-engine-v2-temporal-autoclave]
tags: [openclaw, research, sessions, hooks, plugins]
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# research-openclaw-internals

## Description

Research OpenClaw's internal architecture — session routing, hook system, plugin API, extension points — to enable automated pipeline orchestration without LLM overhead.

## Deliverables (Complete)

### Plugin Prototypes
All at `machinelearning/snn_applied_finance/research/pipeline_builds/openclaw-plugins/`:

1. **pipeline-context** — `before_prompt_build` hook auto-injects active pipeline state into agent context. Zero LLM cost. This is the highest-leverage integration point.
2. **pipeline-commands** — `/pipelines` and `/pstatus` slash commands. Zero LLM cost.
3. **agent-turn-logger** — JSONL logging via both hook layers (internal colon-separated + plugin underscore-separated).
4. **agent-end-telemetry** — Structured telemetry on `agent_end`: tokens, handoffs, errors, duration.

### Key Findings
- **27 hooks cataloged** (11 internal colon-separated, 16 plugin underscore-separated)
- **Hook naming is critical:** wrong convention silently fails (colon vs underscore)
- **`before_prompt_build`** is the main leverage point for context injection
- **`agent_end`** is the main leverage point for completion detection
- Plugins run in-process, no sandbox — full access
- Pipeline state injection: ~552 chars/pipeline with tiered truncation

### Research Report
PDF: `machinelearning/snn_applied_finance/notebooks/local_results/research-openclaw-internals/research-openclaw-internals_report.pdf`

## Downstream Usage
- Plugins being deployed to `~/.hermes/extensions/` for live orchestration
- Feeds directly into orchestration-engine-v2-temporal-autoclave task (persistent agents, SpacetimeDB subscriptions, autoclave view)
