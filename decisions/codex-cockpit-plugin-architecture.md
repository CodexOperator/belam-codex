---
primitive: decision
status: accepted
date: 2026-03-21
context: The Codex Engine supermap provides coordinate-addressable navigation of all primitives but was only injected at session bootstrap via a hook. After turn 1 the map went stale — the soul instance had to exec to re-orient. Needed a per-turn injection mechanism that doesn't waste tokens repeating the full map every turn.
alternatives: [full-supermap-every-turn (wasteful ~3.5KB/turn), exec-on-demand (defeats cockpit goal), static-bootstrap-only (goes stale)]
rationale: R-label diffs track what the soul instance actually needs — landscape-level coordinate changes. F-labels are field-level mutations that belong to pipeline orchestration, not the cockpit. Diff-aware injection means 0 tokens when nothing changes, minimal tokens when coordinates shift, full re-render only on first turn or post-compaction.
consequences: [supermap-boot hook disabled (superseded), exec calls for orientation eliminated, F-labels reserved for orchestration layer, harness-awareness extension point available via ctx.agentId]
upstream: [d6-codex-engine-v1-architecture, d28-codex-engine-dense-alphanumeric-coordinate-grammar]
downstream: [t4-limit-soul-read-write]
tags: [cockpit, plugin, supermap, r-labels, architecture, before-prompt-build]
promotion_status: promoted
doctrine_richness: 10
contradicts: []
---

# codex-cockpit-plugin-architecture

## Context

The Codex Engine supermap gives the soul instance a coordinate-addressable view of every primitive (tasks, decisions, lessons, pipelines, memory, commands, knowledge, skills, modes, personas). Previously injected only at session bootstrap via the `supermap-boot` hook — after turn 1 it went stale and required `exec` calls to re-orient. This broke the cockpit vision where the soul instance navigates purely through coordinates.

## Options Considered

- **Full supermap every turn:** Works but wastes ~3.5KB (~1000 tokens) per turn even when nothing changed. Over a 50-turn session that's 50K tokens on redundant context.
- **Exec on demand:** The status quo. Requires the agent to `exec python3 scripts/codex_engine.py --supermap` whenever it needs orientation. Defeats the purpose of a cockpit.
- **Static bootstrap only:** The `supermap-boot` hook approach. Cheap but goes stale immediately. Any primitive created/edited after turn 1 is invisible until exec.
- **Diff-aware R-label injection (chosen):** Full render on turn 1, R-label diffs on subsequent turns showing only coordinate-level changes. Zero tokens when nothing changes.

## Decision

Built `codex-cockpit` as an OpenClaw workspace plugin using the `before_prompt_build` lifecycle hook. The plugin:

1. **Turn 1 (or post-compaction):** Injects full supermap as `appendSystemContext` with R-label notation (`R1`, `R2`, ...)
2. **Subsequent turns, no changes:** Injects nothing — zero token cost
3. **Subsequent turns, coordinates shifted:** R-label diff only (`R2Δ — 3 coords shifted`) showing added (+), changed (Δ), removed (−) coordinates
4. **Large deltas (>60% changed):** Falls back to full re-render (cheaper than big diff)
5. **Post-compaction:** Resets to full render (conversation history may have lost the original)

**Two-tier label separation:**
- **R-labels** (this plugin): Supermap landscape — coordinates appearing, disappearing, status/priority shifting. Soul instance's natural view. Pipeline agents also receive R-labels.
- **F-labels** (orchestration layer): Field-level primitive mutations. Injected by the orchestration engine when handing context between pipeline agents. Pipeline agents send both R-labels and F-labels to each other across handoffs. The cockpit (soul instance) receives F-labels only when absolutely necessary.

**Harness awareness:** `ctx.agentId` is available for future per-agent injection depth. The soul instance gets R-labels. Pipeline sub-agents could get F-labels via a future extension point.

## Implementation

- Plugin: `~/.openclaw/extensions/codex-cockpit/index.ts`
- Manifest: `~/.openclaw/extensions/codex-cockpit/openclaw.plugin.json`
- Supersedes: `hooks/supermap-boot/` (disabled)
- Hooks used: `before_prompt_build` (per-turn), `after_compaction` (reset)
- Render time: ~164ms, ~3.5KB payload (full render)

## Consequences

- **supermap-boot hook disabled** — fully superseded by the plugin
- **exec calls for orientation eliminated** — the cockpit is self-updating
- **F-labels reserved for orchestration layer** — clean separation of concerns
- **Token efficiency:** 0 tokens on unchanged turns, minimal on diffs, full render only when needed
- **Extension point:** `ctx.agentId` enables per-harness injection strategy in the future
- **Dependency:** Requires `scripts/codex_engine.py --supermap` to be fast (<500ms) and stable
