---
name: orchestration
description: >
  Pipeline orchestration infrastructure — the scripts and systems that move work between agents.
  Covers pipeline_orchestrate.py (handoffs, memory, checkpoint-and-resume), pipeline_autorun.py
  (gate checking, stall detection, stale lock recovery), and the three-tier recovery system.
  Use when: debugging agent handoff failures, understanding why a pipeline is stuck, checking
  orchestration health, modifying handoff behavior, or adding new recovery mechanisms.
  NOT for: checking pipeline status (use pipelines skill), launching new pipelines (use
  launch-pipeline skill), or pipeline lifecycle concepts (use pipelines skill).
---

# Orchestration

The orchestration layer moves work between agents (architect → critic → builder) and ensures pipelines don't get stuck. Two scripts handle everything:

1. **`pipeline_orchestrate.py`** — the handoff engine (agent-facing)
2. **`pipeline_autorun.py`** — the automation layer (heartbeat-facing)

## Scripts

### pipeline_orchestrate.py

The central handoff script. Every agent stage transition goes through it.

```bash
# Agent completes a stage → orchestrator wakes next agent
python3 scripts/pipeline_orchestrate.py <version> complete <stage> \
  --agent <role> --notes "summary" --learnings "insights"

# Agent blocks a stage → orchestrator sends back to previous agent
python3 scripts/pipeline_orchestrate.py <version> block <stage> \
  --agent <role> --notes "BLOCK-1: reason" --artifact review.md

# Mark a stage as started
python3 scripts/pipeline_orchestrate.py <version> start <stage> --agent <role>

# Check for stuck handoffs
python3 scripts/pipeline_orchestrate.py --check-pending

# Verify and retry failed handoffs for a specific pipeline
python3 scripts/pipeline_orchestrate.py <version> verify
```

**What it does on every handoff:**
1. Saves agent memory (`--notes` + `--learnings` → agent's `memory/YYYY-MM-DD.md`)
2. Updates pipeline state (JSON + markdown + frontmatter)
3. Posts to Telegram group
4. Resets next agent's sessions (main + group) for fresh context
5. Wakes next agent via `openclaw agent` with full context message
6. Writes handoff record to `pipelines/handoffs/`
7. On timeout: checkpoint-and-resume (up to 5 cycles)

**Key functions:**
- `reset_agent_session(agent)` — resets both `agent:{name}:main` and `agent:{name}:telegram:group:{id}`
- `consolidate_agent_memory(agent, version, stage, notes)` — writes to agent memory files
- `checkpoint_and_resume(agent, version, stage)` — on timeout, saves partial work + re-wakes

### pipeline_autorun.py

Event-driven automation. Called by heartbeat, no LLM judgment needed.

```bash
# Run all checks (locks → gates → revisions → stalls)
python3 scripts/pipeline_autorun.py

# Individual checks
python3 scripts/pipeline_autorun.py --check-locks      # Stale lock detection only
python3 scripts/pipeline_autorun.py --check-gates      # Gate checking only
python3 scripts/pipeline_autorun.py --check-revisions  # Pending revision requests only
python3 scripts/pipeline_autorun.py --check-stalled    # Stall detection only

# Dry run (report only)
python3 scripts/pipeline_autorun.py --dry-run

# Kick a specific pipeline regardless of gates
python3 scripts/pipeline_autorun.py --one <version>
```

**Check order (every heartbeat cycle):**
1. **Stale locks** (5min) — dead/hung PIDs blocking session dispatch
2. **Gates** — analysis phase2 complete → kick eligible downstream pipelines
3. **Revisions** — pending revision request files → kick `orchestrate_revise()`
4. **Stalls** (120min) — agent went silent, re-kick with recovery context

### Revision Queue

Any process can queue a revision by dropping a file:
```
pipeline_builds/{version}_revision_request.md
```

Format:
```yaml
---
version: build-equilibrium-snn
context_file: research/v4_deep_analysis_findings.md
section: "## For BUILD-EQUILIBRIUM-SNN"
priority: critical
created: 2026-03-19T03:15:00Z
---
Optional extra context body text.
```

CLI shortcut: `R queue-revision <ver> --context-file <path> --section "## Header" --priority high`

Autorun picks up the highest-priority request, loads context from the referenced file (with optional section extraction), calls `orchestrate_revise()`, then deletes the request file. One revision at a time.

**One-pipeline-at-a-time:** Only one pipeline may have active agent work. Autorun enforces this — won't kick a second pipeline while one is being worked on.

## Three-Tier Recovery System

| Tier | Threshold | Script | What it catches |
|------|-----------|--------|-----------------|
| **Lock staleness** | 5 min | `pipeline_autorun.py --check-locks` | Dead/zombied agent processes holding session lock files |
| **Agent timeout** | 10 min | `pipeline_orchestrate.py` (built-in) | Agent taking too long on a stage — checkpoint partial work, resume |
| **Pipeline stall** | 120 min | `pipeline_autorun.py --check-stalled` | Handoff failed silently, agent never woke — full re-kick |

### Tier 1: Stale Lock Detection (5 min)

Session lock files live in `~/.openclaw/agents/{agent}/sessions/*.jsonl.lock`. Format:
```json
{"pid": 12345, "createdAt": "2026-03-18T18:26:13.614Z", "starttime": 180085415}
```

Detection logic:
- **PID dead** → clear lock immediately
- **PID alive but lock >5min** → SIGTERM → wait 2s → SIGKILL if needed → clear lock
- **Corrupt lock file** → clear immediately
- After clearing: reset agent sessions for clean re-dispatch

### Tier 2: Checkpoint-and-Resume (10 min)

Built into `pipeline_orchestrate.py`. When an agent times out:
1. Scan `pipeline_builds/` for files modified in last 12 min (partial work)
2. Write checkpoint to agent's `memory/YYYY-MM-DD.md`
3. Generate fresh UUID4 session
4. Wake agent with resume context pointing to memory checkpoint
5. Up to 5 cycles (60 min total) before alerting human

### Tier 3: Pipeline Stall Recovery (120 min)

Built into `pipeline_autorun.py --check-stalled`. When no activity for 2h:
1. Reset agent session
2. Wake agent with recovery message including pipeline state + files to check
3. One pipeline at a time — won't re-kick multiple simultaneously

## Agent Session Model

- **Fresh UUID4 session per handoff** — prevents stale context accumulation
- **Memory files as continuity** — agents read `memory/YYYY-MM-DD.md` at session start
- **Auto memory consolidation** — orchestrator writes `--learnings` before session ends
- **Both session keys reset** — `agent:{name}:main` (CLI) and `agent:{name}:telegram:group:{id}` (group)

## Transition Map

The orchestrator uses a hardcoded transition map to determine next agent:

| Current Stage | Next Stage | Next Agent |
|---------------|------------|------------|
| `pipeline_created` | `architect_design` | architect |
| `architect_design` | `critic_design_review` | critic |
| `critic_design_review` | `builder_implementation` | builder |
| `builder_implementation` | `critic_code_review` | critic |
| `critic_code_review` | `phase1_complete` | (human gate) |
| `critic_design_review_blocked` | `architect_design_revision` | architect |
| `critic_code_review_blocked` | `builder_apply_blocks` | builder |

### Phase 1 Revisions (coordinator-triggered)

Optional revision loop from `phase1_complete`. Triggered by coordinator, not agents.

```bash
# Via R CLI
R revise <version> --context "revision directions..."

# Via orchestrator directly
python3 scripts/pipeline_orchestrate.py <version> revise --context "..."
```

| From | To | Agent |
|------|----|-------|
| `phase1_complete` | `phase1_revision_architect` | architect (coordinator triggers) |
| `phase1_revision_architect` | `phase1_revision_critic_review` | critic |
| `phase1_revision_critic_review` | `phase1_revision_builder` | builder |
| `phase1_revision_builder` | `phase1_revision_code_review` | critic |
| `phase1_revision_code_review` | `phase1_complete` | (loops back) |

Revision numbers auto-increment. Direction file written to `pipeline_builds/{v}_phase1_revision_{nn}_direction.md`. Multiple revision cycles supported.

## Debugging

```bash
# Check what's pending
python3 scripts/pipeline_orchestrate.py --check-pending

# See handoff records
ls pipelines/handoffs/

# Check agent sessions
openclaw gateway call sessions.list --json | python3 -c "
import json, sys
for s in json.load(sys.stdin).get('sessions', []):
    if any(a in s.get('key','') for a in ['architect','critic','builder']):
        print(s['key'], s['sessionId'][:12])
"

# Check for lock files
ls ~/.openclaw/agents/*/sessions/*.lock 2>/dev/null

# Force stale lock check
python3 scripts/pipeline_autorun.py --check-locks

# Agent memory (most recent)
cat ~/.openclaw/workspace-{architect,critic,builder}/memory/$(date -u +%Y-%m-%d).md
```

## Related Primitives

- `decisions/agent-session-isolation.md` — why fresh sessions + memory continuity
- `decisions/orchestration-architecture.md` — architectural rationale for the orchestration stack
- `lessons/checkpoint-and-resume-pattern.md` — tier 2 pattern details
- `lessons/session-reset-targets-main-not-group.md` — critical bug: must reset both session keys
