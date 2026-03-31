---
primitive: lesson
date: 2026-03-25
source: "Shael session: critic block session mode design"
confidence: high
project: snn-applied-finance
tags: [instance:main, orchestration, agents, session-management]
applies_to: [pipeline_orchestrate, template_parser, block_routing]
upstream: [decision/session-continuity-on-block-with-phase-diff, decision/agent-session-isolation]
promotion_status: exploratory
doctrine_richness: 10
contradicts: []
---

# Lesson: Block Routing Should Use `continue` to Preserve Build Context

## Pattern
When a critic blocks a stage and routes back to the same agent (builder or architect), the receiving agent should reuse their existing session (`session: continue`) rather than starting fresh.

## Why It Matters
The agent being sent back to fix their own work has the most valuable context: the full reasoning behind what they just built. A fresh session discards that entirely, forcing the agent to re-read all files to reconstruct understanding. The `continue` mode already existed in the infrastructure for builder→verify; the same logic applies to critic→block→builder and critic→block→architect.

## Implementation Note
Block routing in templates needed to support a `session` field alongside the fix role:
```yaml
block_routing:
  critic:
    code_review: { role: builder, session: continue }
    design_review: { role: architect, session: continue }
```
The template parser generates 4-tuples `(fix_stage, fix_role, message, session_mode)` for block transitions, matching the format already used by stage transitions.

## Contrast
Cross-agent handoffs (architect → builder, builder → critic) should stay `fresh` — each agent needs a clean slate for tasks that aren't continuations of their own prior work.
