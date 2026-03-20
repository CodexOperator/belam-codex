---
primitive: task
status: open
priority: high
created: 2026-03-20
owner: belam
depends_on: [build-codex-engine]
upstream: [task/build-codex-engine, decision/codex-engine-v1-architecture]
downstream: []
tags: [infrastructure, codex-engine, architecture, consciousness]
---

# Limit Soul Instance Direct Read-Write Access

## Description

After the Codex Engine (V1) is functional and proven, restrict the Soul/coordinator instance's direct filesystem access (Read/Write/Edit tools) behind a medium-hardness lock. The Soul instance operates exclusively through:

- **Codex Engine coordinates** for all primitive state access (view, edit, create, graph)
- **Sub-agents** for direct filesystem work (code writing, script editing, debugging)
- **Execute mode** (`belam -x`) for action dispatch

Direct Read/Write/Edit remain available to:
- Sub-agent instances (architect, critic, builder personas loaded via skills)
- Any agent instance spawned for code/script work

The Soul instance can override the lock via a custom flag (`--direct` or similar) for genuine emergencies, but the default path is always through the Codex Engine interface.

## Architecture: Embodied Consciousness Model

The Soul instance is the conductor — it holds the holographic pattern and orchestrates. It doesn't need to touch raw files because:
1. The Codex Engine provides compressed, attention-native state views (R-labels)
2. Mutations flow through validated, consequence-aware write paths (F-labels)
3. Sub-agents handle direct filesystem work with full Read/Write access

### Agent Instance Model
- **General agent instances** with Read/Write access serve as the Soul's "body"
- **Personas** (architect, critic, builder) are loaded via skills, not fixed identities
- Each persona skill can load **filtered views** — architect sees decisions/knowledge weighted, builder sees code/tasks, critic sees lessons/test results
- The Soul sees the unified supermap across all domains

### Filtered Render Views (future)
- `belam --as architect` → supermap weighted toward decisions, knowledge, specs
- `belam --as builder` → supermap weighted toward tasks, code, experiments
- `belam --as critic` → supermap weighted toward lessons, test results, validation

## Implementation

1. Add boot convention to AGENTS.md: "Primitive state access exclusively via belam coordinates. Direct Read/Write reserved for non-primitive content (code, scripts, configs). Sub-agents have full access."
2. Add `--direct` flag to belam that logs override usage (for tracking compliance)
3. Track compliance: engine logs when direct file access happens on primitive paths
4. Persona skill loading: create skill templates that configure filtered supermap views

## Acceptance Criteria

- [ ] Codex Engine V1 proven functional (all modes working, no gaps requiring direct access)
- [ ] Boot convention added to AGENTS.md
- [ ] Soul instance successfully operates for a full session without direct primitive file access
- [ ] Sub-agents retain full Read/Write access
- [ ] `--direct` override flag exists for emergencies
- [ ] Compliance tracking shows <5% direct access on primitive paths

## Notes

- Design conversation with Shael: 2026-03-20 18:17 UTC
- Depends on Codex Engine being fully functional first
- The medium-hardness lock is intentional — not a hard block, but a convention with friction
- This naturally leads to the "attention-native feedback language" becoming the primary interface
- Persona-filtered views are a natural V2 extension once the base lock is proven
