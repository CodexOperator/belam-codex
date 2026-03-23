# Phase 2 Direction: Persistent Agent Sessions via Render Engine

## Context

Phase 1 delivered the RAM-first render runtime: UDS socket, cockpit plugin with per-session diffs, write-through cache, per-node locking. But agents are still spawned as one-shot sessions with full context injection each time. The render engine holds authoritative state in RAM but agents don't live inside it — they get snapshots injected into their prompts.

## Phase 2 Goal

**Agents become persistent UDS sessions attached to the render engine.** They stay attached throughout a pipeline phase (architect → critic → builder → critic) until the phase gate clears (e.g. "code review approved"). The render engine is both shared state and communication channel.

## Deliverables

### D1: Persistent Agent Session Manager
Extend the render engine's SessionManager to support named persistent sessions (not just anonymous cockpit sessions). Each pipeline agent role gets a named session (`architect`, `critic`, `builder`) that persists across orchestrator signals.

- `attach {agent: "architect", pipeline: "v4", persistent: true}` → returns session_id, stays alive
- Session tracks: last anchor, last activity, pipeline context
- Idle sessions are kept alive but cost nothing (no LLM tokens, just a UDS entry)

### D2: Orchestrator Signal Protocol
Replace `fire_and_forget_dispatch()` spawn pattern with signal-based handoffs via UDS:

- `signal {session_id, task: "design", pipeline: "...", context_coord: "t3"}` → wakes the agent
- Agent reads tree state from its session anchor (sees only what changed)
- Agent writes results to tree → sends `done {session_id, result: "approved|flagged|complete"}`
- Orchestrator routes next signal based on result

### D3: Cockpit Plugin Simplification
With agents attached directly to the render engine:
- First turn: attach + full tree render (unchanged)
- Subsequent turns: `my_diff` returns nothing if agent hasn't been signaled (agent is idle)
- Remove per-turn supermap re-injection for persistent sessions — they already have it in conversation history
- Legend scaffold still injected (small, serves as persistent reminder)

### D4: Session Compaction Integration
After each agent handoff within a pipeline phase:
- Trigger OpenClaw conversation compaction for the idle agent
- Render engine retains full state — agent doesn't lose anything from compaction
- Next signal to the agent starts with lean context + diff from tree

### D5: Graceful Degradation
If render engine crashes or restarts:
- Sessions reconnect on next signal (re-attach, get full tree)
- Fall back to one-shot spawn model if persistent session is unreachable
- No pipeline work is lost (write-through ensures disk is always current)

## Phase 1 FLAG to Address
- **FLAG-1 MED** (from critic code review): `codexExec('--register-show')` subprocess takes 158ms per turn. Fix: read `.codex_runtime/register.json` directly in TypeScript (<1ms).

## Key Architectural Shift
- **Before:** Agent lifecycle = spawn → inject → work → exit → parse
- **After:** Agent lifecycle = attach → idle → signal → work → signal → idle → ... → detach
- **Communication:** Render engine RAM tree replaces file-based handoffs
- **Context:** Tree diffs replace full prompt injection
- **Observation:** Critic as persistent observer sees project evolve, not just final diffs

## Open Questions for Architect
1. Should all 3 agent roles share one render engine session or each get their own? (Recommend: each gets own — independent anchors)
2. How does this interact with OpenClaw's `sessions_spawn` / `sessions_send`? Can we use persistent OpenClaw sessions (`mode: "session"`) as the agent process, with UDS as the state channel?
3. Token budget: what's the practical limit for a persistent agent session before compaction is needed? Should compaction be time-based, token-based, or handoff-based?
4. Should the orchestrator itself be a render engine session, or remain external?
