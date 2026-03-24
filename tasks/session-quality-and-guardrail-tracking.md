---
primitive: task
status: open
priority: high
created: 2026-03-24
owner: belam
depends_on: []  # lm-v3 done 2026-03-24
tags: [lm, metacognition, quality, guardrails, observability, infrastructure]
project: codex-engine
---

# Session Quality & Guardrail Tracking

## Scope

Two observability systems integrated into the coordinate/session flow:

### 1. Satisfaction Survey (every 10 min or 10 turns)

Bidirectional quality checkpoint:

**Agent self-assessment:**
- Flow quality (1-5): Am I in coordinate mode or falling back to raw commands?
- Utility (1-5): Am I moving real work forward or churning?
- Token efficiency (1-5): Am I being concise or verbose?
- Brief note on what's working / what's friction

**User prompt (optional, non-blocking):**
- Satisfaction (1-5): Is this session productive?
- Brief note

**Implementation:**
- Turn counter + timestamp tracker in cockpit plugin or render engine
- At threshold: inject survey prompt via `before_prompt_build` or system event
- Results logged as memory entries with `tag: session-quality`
- Aggregatable over time — trend lines on agent effectiveness

### 2. Guardrail Chain Tracking

Programmatic detection and logging of guardrail trigger events:

**What to track:**
- Any LLM response that triggered a guardrail (safety, content policy, tool denial)
- Whether the same guardrail fired repeatedly (chain detection)
- Whether different guardrails fired in sequence (escalation pattern)
- Context: what was the agent trying to do when the guardrail fired

**Dual purpose — debug AND training signal:**
- Debug: alert on chains > 3 (likely stuck in a loop), surface via `r.guardrails`
- Training: structured negative examples for fine-tuning. Each activation captures (context, action, guardrail_type, outcome) — encoding "don't do this" as training pairs
- Surveys are pure training signal; guardrail activations are both
- Format TBD: different fine-tuning approaches handle negative signal differently (DPO pairs, RLHF penalty, instruction-following with "avoid X" framing). Collect richly now, experiment with encoding later.

**Implementation:**
- Hook into agent_end telemetry or tool response parsing
- Detect guardrail signatures: refusal patterns, tool denials, approval-pending states
- Log as structured events: `{timestamp, guardrail_type, chain_length, context, action_attempted, resolution}`
- Alert on chains > 3 (likely stuck in a loop)
- Surfaceable via `r.guardrails` read command (from t7's `r.*` namespace)

### 3. Integration with LM v3

- `r.quality` — read command showing recent satisfaction scores + trends
- `r.guardrails` — read command showing guardrail events + chains
- Survey results feed into session memory — agents learn what works
- Guardrail chains feed into lesson creation — prevent repeat failures

## Open Questions

1. Survey delivery: system event injection vs dedicated UDS command?
2. Guardrail detection: parse response text for patterns vs hook into gateway internals?
3. Should survey results auto-create primitives or just log to a rolling file?
