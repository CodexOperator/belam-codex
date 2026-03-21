---
primitive: memory_log
timestamp: "2026-03-21T11:05:58Z"
category: technical
importance: 3
tags: [instance:architect, pipeline:orchestration-engine-v2-temporal, stage:architect_design]
source: "session"
content: "Designed temporal overlay for V2 orchestration engine: SpacetimeDB for temporal state (5 tables: pipeline_state, state_transition, handoff, agent_context, agent_presence), persistent agent context (structured cross-session memory scoped to pipeline lifecycle), autoclave shared dashboard (real-time subscriptions + time-travel queries). Key design decisions: overlay not replacement (filesystem remains source of truth, graceful degradation if SpacetimeDB unavailable), minimal V2 diff (~30 lines), Rust module for schema+reducers (~300 lines), Python client (~250 lines). New e0a coordinates for autoclave access. 5 open questions for critic including SpacetimeDB vs SQLite tradeoff."
status: active
---

# Memory Entry

**2026-03-21T11:05:58Z** · `technical` · importance 3/5

Designed temporal overlay for V2 orchestration engine: SpacetimeDB for temporal state (5 tables: pipeline_state, state_transition, handoff, agent_context, agent_presence), persistent agent context (structured cross-session memory scoped to pipeline lifecycle), autoclave shared dashboard (real-time subscriptions + time-travel queries). Key design decisions: overlay not replacement (filesystem remains source of truth, graceful degradation if SpacetimeDB unavailable), minimal V2 diff (~30 lines), Rust module for schema+reducers (~300 lines), Python client (~250 lines). New e0a coordinates for autoclave access. 5 open questions for critic including SpacetimeDB vs SQLite tradeoff.

---
*Source: session*
*Tags: instance:architect, pipeline:orchestration-engine-v2-temporal, stage:architect_design*
