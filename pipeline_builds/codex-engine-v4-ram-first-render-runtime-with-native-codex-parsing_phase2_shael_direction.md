# Phase 2 Direction: Stage-Based Agent Sessions via Render Engine

## Context

Phase 1 delivered the RAM-first render runtime: UDS socket, cockpit plugin with per-session diffs, write-through cache, per-node locking. But agents are still spawned as one-shot sessions with full context injection each time — no ping-pong, no iterative review. The render engine holds authoritative state in RAM but agents don't live inside it.

## Phase 2 Goal

**Each pipeline stage gets a shared conversation session, like a chat room.** Agents join and leave based on the stage lifecycle. The render engine provides state continuity between stages; the session provides conversation continuity within a stage. Sessions are terminated and fresh ones spawned at each stage boundary.

## Session Lifecycle Model

### Stage 1: Architect Design → Design Review
```
Session A created by orchestrator
  → architect attaches (solo)
  → architect reads tree, designs, writes design to tree
  → architect signals "ready for review"
  → critic joins Session A (architect keeps context — reasoning is valuable for review)
  → critic gets: full tree state + design artifacts (cold injection)
  → architect ↔ critic ping-pong (revisions, clarifications, FLAG resolution)
  → critic signals APPROVED
  → Session A terminated
```

### Stage 2: Builder Implementation → Code Review
```
Session B created by orchestrator
  → builder attaches (solo)
  → builder reads tree (sees design from Stage 1 — tree persisted)
  → builder implements, writes code to tree
  → builder signals "ready for review"
  → critic joins Session B (builder keeps context — implementation reasoning valuable)
  → critic gets: full tree state + implementation diff since design (cold injection)
  → builder ↔ critic ping-pong (FLAG fixes, revision requests)
  → critic signals APPROVED
  → Session B terminated
  → Phase gate: phase1_complete
```

### Key Properties
- **Option A model:** primary agent (architect/builder) keeps session context; critic always joins cold
- **Easily convertible to Option B** (fresh session for both) if token debt becomes an issue
- **2 agents max per session** (architect+critic OR builder+critic)
- **Critic always joins fresh** — cold context injection (mirrors real code review)
- **Tree is continuity** — design decisions persist in RAM across sessions
- **Session resets between stages** — architect's session dies before builder's starts
- **Orchestrator manages lifecycle** — creates sessions, routes signals, terminates on approval

## Deliverables

### D1: Stage Session Manager (render engine extension)
Extend render engine SessionManager to support orchestrated stage sessions:

- `create_stage_session(pipeline, stage, initial_agent)` → session_id
- `join_session(session_id, agent)` → attaches agent, injects tree state + stage context
- `terminate_session(session_id)` → cleanup, archives conversation
- Max 2 concurrent agents per session (enforced)
- Session tracks: stage, pipeline, participants, message count, creation time

### D2: Agent Ping-Pong Protocol
Within a stage session, agents communicate via the render engine:

- Agent writes work artifacts to tree → signals `ready_for_review`
- Orchestrator adds reviewer to session → reviewer gets tree diff injection
- Reviewer responds (APPROVED / FLAG / BLOCK) → written to tree
- If FLAG: original agent sees diff, addresses it, re-signals
- If APPROVED: orchestrator terminates session, advances pipeline stage
- If BLOCK: orchestrator terminates session, logs block, alerts human

### D3: Orchestrator Integration
Replace `fire_and_forget_dispatch()` with stage session orchestration:

- `advance_pipeline(pipeline)` → determines next stage → creates session → attaches first agent
- Handoff detection: monitor session for `ready_for_review` signal → auto-join critic
- Approval detection: monitor for APPROVED verdict → terminate → advance to next stage
- Stall detection: session active >2h with no new messages → alert

### D4: Context Injection per Stage (Option A)
When an agent joins a session:

- **Primary agent (architect/builder — session creator):** full tree render + pipeline spec at session start. Keeps full conversation context through review phase — their reasoning about "why X over Y" is available when critic asks.
- **Critic (joins existing session):** full tree render + diff since session creation (what primary agent produced) + previous stage verdicts. Always cold injection — mirrors real code review.
- No per-turn re-injection — conversation history carries context forward (like main session)
- Legend scaffold injected once at join
- **Option B fallback:** if token accumulation from solo phase causes issues, switch to fresh session for both at review boundary (primary agent re-reads own artifacts from tree)

### D5: Cockpit Plugin Adaptation
- Persistent sessions use stage session manager (not per-turn supermap injection)
- `before_prompt_build` detects if agent is in a stage session → skips injection (session handles it)
- Fallback: if no stage session active, behave as current (per-turn diff injection)

### D6: Graceful Degradation
- If render engine crashes: fall back to one-shot spawn model (current behavior)
- If session agent crashes: orchestrator detects timeout → respawns agent into same session (with tree state recovery)
- Write-through ensures disk is always current — no data loss on any failure

## Phase 1 FLAG to Address
- **FLAG-1 MED** (from critic code review): `codexExec('--register-show')` subprocess takes 158ms per turn. Fix: read `.codex_runtime/register.json` directly in TypeScript (<1ms).

## Key Architectural Shift
- **Before:** Agent lifecycle = spawn → inject everything → work alone → exit → parse output → spawn next
- **After:** Agent lifecycle = join session → work → ping-pong with reviewer → approved → session ends
- **State continuity:** Render engine RAM tree (persists across sessions)
- **Conversation continuity:** Stage session (disposable, clean per stage)
- **Communication:** Direct agent-to-agent within session, not file-based handoff parsing

## Open Questions for Architect
1. How do stage sessions map to OpenClaw's `sessions_spawn` / `sessions_send`? Use `mode: "session"` with `sessions_send` for ping-pong?
2. Should the orchestrator poll for signals or should the render engine push notifications (e.g. inotify on a signal file)?
3. What's the compaction strategy within a stage session? Compact after every N exchanges, or only when approaching token limit?
4. Should stage session conversations be archived (for memory extraction by sage) or are tree artifacts sufficient?
