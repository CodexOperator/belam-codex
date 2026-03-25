---
primitive: decision
status: accepted
date: 2026-03-25
context: "Critic blocks reset the agent session, forcing re-ingestion of all files despite the agent having full context of what they just built/designed. With well-scoped subtasks this is pure waste — the agent's own reasoning is the most valuable context for fixing their own work."
alternatives:
  - "Option A: Always fresh sessions on block (current system) — simple but wasteful, loses agent reasoning context"
  - "Option B: Continue sessions on same-agent blocks, fresh on cross-agent handoffs, verbose git diff on cross-phase transitions (chosen)"
  - "Option C: Continue sessions everywhere (too risky — cross-agent context pollution)"
rationale: "Same-agent block returns are the most contextually coherent handoff possible. The agent just produced the work, has full reasoning context, and only needs the critic's feedback delta. Cross-agent handoffs still benefit from fresh sessions (different reading frames). Cross-phase transitions need explicit diffs because significant work happened between the agent's last turn and their next one."
consequences:
  - "block_routing in templates gains a session field (continue for same-agent blocks)"
  - "Per-agent HEAD tracking added to pipeline state — snapshot on successful turn completion"
  - "Cross-phase handoffs include verbose git diff from agent's last HEAD to current state"
  - "HEAD not updated on blocked turns (still mid-work)"
  - "Faster block resolution cycles — no file re-ingestion overhead"
  - "Lower token cost per block-fix cycle on Opus"
upstream:
  - decision/agent-session-isolation
  - lesson/checkpoint-and-resume-pattern
downstream: []
tags: [infrastructure, orchestration, agents, session-management]
---

# Decision: Session Continuity on Block + Phase-Level Git Diff

## Summary

Three session modes based on handoff type:

| Handoff Type | Session Mode | Context Mechanism |
|---|---|---|
| Critic block → fixing agent | `continue` | Agent keeps full session context + critic feedback injected |
| Fix complete → critic re-review | `continue` | Critic keeps context from initial review + diff of fixes |
| Normal cross-agent handoff | `fresh` | File list + handoff message (existing behavior) |
| Cross-phase same-agent | `fresh` | File list + verbose git diff from agent's last HEAD |

## Git HEAD Tracking

Each agent gets a per-pipeline HEAD reference tracking when they last completed a turn:

1. **Set HEAD:** When agent completes a turn without being blocked (critic approves or passes forward)
2. **Don't update HEAD:** On blocked turns — the work is incomplete, HEAD stays at last clean completion
3. **Use HEAD:** On cross-phase transitions, generate `git diff <agent_HEAD>..<current>` for the relevant file paths
4. **Reset cycle:** HEAD updates only on successful turn completion, so it always points to the agent's last known-good contribution

### Example Flow (Research Pipeline)

```
P1: architect designs → HEAD_architect = abc123
P1: critic reviews design → approves
P1: builder implements → HEAD_builder = def456  
P1: critic blocks code review → builder continues (same session)
P1: builder fixes → critic re-reviews (same session, continue)
P1: critic approves → HEAD_critic set, HEAD_builder = ghi789
P1: architect gets completion handoff

P2: architect designs (fresh + diff abc123..current = sees builder's implementation)
P2: builder implements (fresh + diff ghi789..current = sees architect's P2 design)
```

## Implementation

### 1. Template block_routing gains session field

```yaml
block_routing:
  critic:
    design_review: { agent: architect, session: continue }
    code_review: { agent: builder, session: continue }
    analysis_review: { agent: architect, session: continue }
    analysis_code_review: { agent: builder, session: continue }
    review: { agent: builder, session: continue }  # builder-first template
```

### 2. Pipeline state tracks per-agent HEAD

```json
{
  "agent_heads": {
    "architect": { "ref": "abc123", "phase": "p1", "stage": "architect_design", "timestamp": "..." },
    "builder": { "ref": "def456", "phase": "p1", "stage": "builder_implementation", "timestamp": "..." }
  }
}
```

### 3. Orchestrator changes

- `cmd_block()` reads session mode from block_routing and passes to orchestrator
- `advance_pipeline()` snapshots agent HEAD on successful (non-blocked) completion
- Cross-phase handoffs call `git diff <head_ref>..HEAD -- <relevant_files>` and include in handoff message
- Within-phase blocks skip HEAD update and use `continue` session mode

## Boundary Conditions

- **First-ever turn for an agent in a pipeline:** No HEAD exists → full file list, no diff (existing behavior)
- **Agent HEAD ref is garbage-collected/unreachable:** Fall back to full file list, no diff
- **Multiple blocks in sequence:** Session continues accumulating, HEAD stays at last clean turn — this is correct because the agent is still working on the same logical task
