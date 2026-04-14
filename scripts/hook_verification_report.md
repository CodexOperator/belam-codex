# Hook Verification Report — OpenClaw Integration

**Generated:** 2026-04-13 17:22 UTC  
**Workspace:** `/home/ubuntu/.openclaw/workspace`  

---

## Summary

| Test | Status | Errors | Warnings |
|------|--------|--------|----------|
| **Hook Discovery** | ✅ PASS | 0 | 2 |
| **Naming Convention Verification** | ✅ PASS | 0 | 0 |
| **Existing Hook Health Check** | ✅ PASS | 0 | 1 |
| **Plugin Prototype Validation** | 🔴 FAIL | 1 | 0 |
| **Hook Integration Surface for Orchestration** | ✅ PASS | 0 | 2 |

**Overall:** 🔴 CRITICAL FAILURES

---

## Test 1: Hook Discovery ✅

### ⚠️ Warnings

- results_summary.json not found — using hardcoded hook catalog
- Docs mention 1 unrecognized hook-like tokens (may be false positives)

### Internal Hooks Catalog (11)

- `agent:bootstrap`
- `command:new`
- `command:reset`
- `command:stop`
- `gateway:startup`
- `message:preprocessed`
- `message:received`
- `message:sent`
- `message:transcribed`
- `session:compact:after`
- `session:compact:before`

### Plugin Hooks Catalog (16)

- `after_compaction`
- `after_tool_call`
- `agent_end`
- `before_agent_start`
- `before_compaction`
- `before_model_resolve`
- `before_prompt_build`
- `before_tool_call`
- `gateway_start`
- `gateway_stop`
- `message_received`
- `message_sending`
- `message_sent`
- `session_end`
- `session_start`
- `tool_result_persist`

**Catalog count:** 27 hooks — matches research catalog ✓

---

## Test 2: Naming Convention Verification ✅

### Hook Collision Pairs

These hooks exist in BOTH layers with the same semantic meaning:

| `message:received` (internal) | `message_received` (plugin) | Same event, different layers/registration APIs — do not confuse |
| `message:sent` (internal) | `message_sent` (plugin) | Same event, different layers/registration APIs — do not confuse |

---

## Test 3: Existing Hook Health Check ✅

### ⚠️ Warnings

- pipeline-dispatch: unknown event(s) in HOOK.md: ['agent:end']

### Hook-by-Hook Results

| Hook | HOOK.md | handler.ts | Events | Syntax | Status |
|------|---------|------------|--------|--------|--------|
| `memory-extract` | ✅ | ✅ | `command` | ✅ ok | ✅ |
| `pipeline-dispatch` | ✅ | ✅ | `agent:end` | ✅ ok | ⚠️ |
| `supermap-boot` | ✅ | ✅ | `agent:bootstrap` | ✅ ok | ✅ |

---

## Test 4: Plugin Prototype Validation 🔴

### ❌ Errors

- Plugin prototype directory not found: /home/ubuntu/.openclaw/workspace/pipeline_builds/openclaw-plugins

---

## Test 5: Hook Integration Surface for Orchestration ✅

### ⚠️ Warnings

- agent_end rated HIGH for orchestration but not yet implemented in any plugin/hook
- HIGH-value orchestration hooks not yet implemented: ['agent_end']

### Orchestration Surface Table

| Hook | Layer | Rating | Implemented | Timing |
|------|-------|--------|-------------|--------|
| `before_prompt_build` | plugin | 🟢 HIGH | `openclaw-plugins/pipeline-context` | After session load, before model inference — messa… |
| `agent:bootstrap` | internal | 🟡 MEDIUM | `hooks/supermap-boot` | Session start only — before system prompt assembly… |
| `after_tool_call` | plugin | 🟢 HIGH | `openclaw-plugins/agent-turn-logger` | After each tool execution, before tool result is a… |
| `agent_end` | plugin | 🟢 HIGH | — | After full agent turn completes — reply assembled,… |

#### `before_prompt_build` — HIGH orchestration suitability

**Layer:** plugin  
**Registration:** `api.on('before_prompt_build', handler, { priority })`  
**Timing:** After session load, before model inference — messages are available  

**Context available:**
- `ctx.workspaceDir — absolute path to the agent's workspace`
- `ctx.agentId — current agent identifier`
- `ctx.sessionKey — current session key (e.g. agent:main:telegram:group:-123)`
- `ctx.messages — current message array (read-only view)`
- `ctx.channel — channel metadata`
- `ctx.conversationId — conversation identifier`

**Can modify/inject:**
- prependContext — text prepended to the current user message
- systemPrompt — full system prompt OVERRIDE (replaces everything)
- prependSystemContext — injected BEFORE the existing system prompt
- appendSystemContext — injected AFTER bootstrap files (AGENTS.md, SOUL.md, etc.)

**Orchestration suitability:** HIGH
> Best injection point for pipeline state. Fires every turn with full message context. appendSystemContext is additive and provider-cache-friendly. Implemented by pipeline-context plugin. CRITICAL: wrong naming convention (e.g. before:prompt:build) means silent no-fire.

**Currently implemented by:** openclaw-plugins/pipeline-context

#### `agent:bootstrap` — MEDIUM orchestration suitability

**Layer:** internal  
**Registration:** `api.registerHook('agent:bootstrap', handler, { name, description })`  
**Timing:** Session start only — before system prompt assembly, bootstrap files are mutable  

**Context available:**
- `event.context.workspaceDir — workspace directory`
- `event.context.bootstrapFiles — array of {name, path, content, missing} objects`
- `event.context.agentId — current agent identifier`
- `event.sessionKey — current session key`

**Can modify/inject:**
- event.context.bootstrapFiles — push/unshift to inject additional context files
- event.context.bootstrapFiles[i].content — mutate existing bootstrap file content

**Orchestration suitability:** MEDIUM
> Good for session-start bootstrap injection (e.g. PIPELINE_STATUS.md). Fires ONCE per session, not per turn — cheaper but less dynamic than before_prompt_build. Implemented by supermap-boot hook to inject CODEX.codex. Use for stable session-start context; use before_prompt_build for turn-by-turn state.

**Currently implemented by:** hooks/supermap-boot

#### `after_tool_call` — HIGH orchestration suitability

**Layer:** plugin  
**Registration:** `api.on('after_tool_call', handler, { priority })`  
**Timing:** After each tool execution, before tool result is added to transcript  

**Context available:**
- `event.toolName / event.name — name of the tool that fired`
- `event.params / event.arguments — parameters passed to the tool`
- `event.result — tool result object (can be modified)`
- `event.error — error if tool failed (null on success)`
- `event.sessionKey — current session key`

**Can modify/inject:**
- Return value from handler can modify/replace the tool result
- Can suppress tool result (replace with neutral response)
- Can augment result with additional context

**Orchestration suitability:** HIGH
> Critical for orchestration auditing — every tool call passes through this hook. Can intercept pipeline_orchestrate exec calls to track state transitions. Can detect exec tool calls to flag when orchestrator is being invoked. Used by agent-turn-logger plugin for logging (priority 90 = low interference). Combined with agent_end enables full turn-level orchestration telemetry.

**Currently implemented by:** openclaw-plugins/agent-turn-logger

#### `agent_end` — HIGH orchestration suitability

**Layer:** plugin  
**Registration:** `api.on('agent_end', handler, { priority })`  
**Timing:** After full agent turn completes — reply assembled, before session persist  

**Context available:**
- `ctx.messages — full message array for the turn (assistant + tool calls)`
- `ctx.agentId — agent that completed the turn`
- `ctx.sessionKey — session key`
- `ctx.usage — token usage stats (prompt, completion, total)`
- `ctx.latencyMs — turn latency in milliseconds`
- `ctx.model — model used for this turn`

**Can modify/inject:**
- Read-only inspection of completed turn (primary use case)
- Can trigger side-effects: log, alert, push metrics
- Cannot modify already-sent reply

**Orchestration suitability:** HIGH
> Best hook for post-turn orchestration decisions. Full visibility into what the agent just did (tools called, content generated, tokens used). Ideal for: detecting pipeline handoff signals in output, tracking when orchestrator transitions are made, cost monitoring per pipeline stage. Compose with after_tool_call for complete turn-level telemetry.

**Currently implemented by:** not yet implemented

---

## Reference

- **Research doc:** `machinelearning/snn_applied_finance/research/pipeline_builds/research-openclaw-internals_builder_reference.md`
- **Hook catalog source:** `machinelearning/snn_applied_finance/notebooks/local_results/research-openclaw-internals/results_summary.json`
- **Plugin prototypes:** `machinelearning/snn_applied_finance/research/pipeline_builds/openclaw-plugins/`
- **Workspace hooks:** `hooks/`

_Report generated by `scripts/verify_hooks.py` at 2026-04-13 17:22 UTC_