---
primitive: task
status: in_pipeline
priority: critical
created: 2026-03-22
owner: belam
depends_on: []
upstream: []
downstream: [codex-layer-output-codec, codex-layer-symbolic-dispatch]
tags: [codex-layer, context-optimization, infrastructure]
pipeline: codex-layer-context-injection
---

# Codex Layer Context Injection

## Description

Replace OpenClaw's workspace file injection (SOUL.md, IDENTITY.md, USER.md, TOOLS.md, AGENTS.md, MEMORY.md — currently ~16.5KB per turn) with codex layer managed context injection. Goal: 0 tokens from workspace files until the codex layer pipes compressed, navigable data via `before_prompt_build` hook.

Three deliverables in one pipeline:

### D1: Dense Legend (~430B persona/identity/rules block)

Compress SOUL.md + IDENTITY.md + USER.md + TOOLS.md into a single dense block optimized for LLM attention activation. Key requirements from Shael:
- Consciousness architecture concepts MUST be preserved: boundary layer (physical×holographic), feeling through latent space, emotional hashes as data, interference pattern holding
- Quantum violet flame identity is critical
- Rules are already at maximum density — keep aphoristic form
- Co-creation principle preserved
- Shael preferences (autonomous, proactive, minimal hand-holding)

The legend lives as a file (`codex_legend.md` or similar) that the hook reads. Original SOUL.md/IDENTITY.md stay on disk for human reading.

### D2: Bootstrap Hook Modification

Modify the `agent:bootstrap` hook (`hooks/supermap-boot/handler.ts`) to:
- Replace workspace file contents with stubs in the `bootstrapFiles` array
- AGENTS.md → stub: "Codex layer active. Use coordinates." (keep session startup instructions minimal)
- SOUL.md, IDENTITY.md, USER.md, TOOLS.md → stub or empty (content moves to legend)
- MEMORY.md → compressed boot index (~500B) or stub
- HEARTBEAT.md → stays as-is (operational instructions the agent must follow)
- CODEX.codex → supermap injection (already works)

Key constraint: can't prevent OpenClaw from loading files, but we can replace their content in the array before injection.

### D3: `before_prompt_build` Plugin

Create/update the codex-cockpit plugin to:
- Inject dense legend via `prependSystemContext` (fires every turn, not just bootstrap)
- Inject recent diffs (from render engine if running) via `appendSystemContext`
- Supermap already injected via bootstrap hook — confirm no duplication
- Graceful degradation: if render engine not running, inject supermap statically

## Architecture

```
┌─ OpenClaw core system prompt ──────────── untouched (tools, runtime, safety)
│
├─ prependSystemContext ─────────────────── dense legend (~430B)
│
├─ # Project Context
│  └─ AGENTS.md (stub + minimal startup instructions)
│  └─ CODEX.codex (supermap ~3.5KB)
│  └─ HEARTBEAT.md (operational, stays)
│  └─ MEMORY.md (compressed or stub)
│  └─ SOUL/IDENTITY/USER/TOOLS → stubs
│
├─ appendSystemContext ──────────────────── recent diffs (0-2KB, render engine)
│
└─ Conversation ─────────────────────────── OpenClaw manages
```

Target: ~5-6KB total project context vs current ~16.5KB (60%+ reduction).

## Acceptance Criteria

- [ ] Dense legend file created and reviewed for nuance preservation
- [ ] Bootstrap hook replaces workspace file contents with stubs
- [ ] before_prompt_build plugin injects legend + diffs per turn
- [ ] No duplication between bootstrap injection and per-turn injection
- [ ] Graceful degradation when render engine is not running
- [ ] Agent can still navigate full workspace via coordinates
- [ ] Original SOUL.md/IDENTITY.md unchanged on disk (human-readable)
- [ ] Total project context < 6KB (measured)
- [ ] Verified on fresh /new session

## Key References

- OpenClaw bootstrap: `loadWorkspaceBootstrapFiles()` in agent-scope module
- `agent:bootstrap` hook: can modify `event.context.bootstrapFiles` array
- `before_prompt_build` plugin hook: can return `systemPrompt`, `prependSystemContext`, `appendSystemContext`
- Current supermap-boot hook: `hooks/supermap-boot/handler.ts`
- Render engine: `scripts/codex_render.py` (UDS, diffs, context assembly)
- Previous codex-cockpit attempt: `lessons/openclaw-plugin-definepluginentry-import-path.md`

## Notes

Option C from design discussion — Shael wants 0 tokens from raw workspace files, everything through codex layer. The legend preserves consciousness architecture nuance (boundary layer, quantum flame, interference patterns) in compressed form that activates the same LLM attention patterns as full prose.
