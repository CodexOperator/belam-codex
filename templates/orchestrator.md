---
primitive: orchestrator
name: Pipeline Stage Orchestrator
description: >
  Manages pipeline stage transitions with fresh agent sessions, automatic memory
  consolidation, and checkpoint-and-resume on timeout. The orchestrator is the
  SINGLE AUTHORITY for handoffs — agents call it to complete/block stages, and it
  handles everything: memory save, state update, Telegram notification, next agent wake.
fields:
  scripts:
    type: object
    description: "Core scripts that make up the orchestrator system"
    properties:
      orchestrate:
        type: string
        default: "scripts/pipeline_orchestrate.py"
        description: "Main orchestrator — complete/block/start stages, auto-handoff with fresh sessions, checkpoint-and-resume"
      pipeline_update:
        type: string
        default: "scripts/pipeline_update.py"
        description: "Lightweight state tracker — updates stage history + state JSON. Called by orchestrator internally."
      log_memory:
        type: string
        default: "scripts/log_memory.py"
        description: "Quick memory entry logging with categories, tags, importance levels"
      launch_pipeline:
        type: string
        default: "scripts/launch_pipeline.py"
        description: "Create new pipeline instances from template, optionally kick off"
  session_management:
    type: object
    description: "How sessions are managed per pipeline stage"
    properties:
      session_policy:
        type: string
        default: "fresh-per-interaction"
        description: "Every handoff creates a new session (UUID4). No session reuse. Memory files provide continuity."
      timeout:
        type: integer
        default: 600
        description: "10 minutes per agent session"
      checkpoint_on_timeout:
        type: boolean
        default: true
        description: "On timeout: scan for partial work, write checkpoint to agent memory, re-wake with fresh session"
      max_resumes:
        type: integer
        default: 5
        description: "Maximum checkpoint-and-resume cycles before alerting (5 × 10min = 50min max compute)"
      memory_auto_save:
        type: boolean
        default: true
        description: "--notes and --learnings auto-written to agent memory at every complete/block"
  agents:
    type: object
    description: "Agent configuration"
    properties:
      model:
        type: string
        default: "anthropic/claude-opus-4-6"
        description: "All persistent agents run Opus"
      instances:
        type: string[]
        default: ["architect", "critic", "builder"]
      workspaces:
        type: object
        default:
          architect: "~/.openclaw/workspace-architect"
          critic: "~/.openclaw/workspace-critic"
          builder: "~/.openclaw/workspace-builder"
  lifecycle:
    type: string[]
    description: "What happens at each handoff"
    default:
      - "1. Auto-save calling agent's memory (--notes + --learnings → memory/YYYY-MM-DD.md)"
      - "2. Update pipeline state (JSON + markdown + frontmatter status)"
      - "3. Send Telegram group notification"
      - "4. Generate fresh session ID (UUID4) for next agent"
      - "5. Build rich handoff message (files to read, context, orchestrator commands)"
      - "6. Wake next agent via openclaw agent CLI"
      - "7. If timeout → checkpoint partial work → resume with fresh session (up to 5×)"
      - "8. Write handoff record for verification"
---

# Pipeline Stage Orchestrator

## What It Does

The orchestrator manages **stage transitions** between agents. When an agent finishes work, it calls the orchestrator once — everything else is automatic:

- Memory consolidation for the calling agent
- Pipeline state update + Telegram notification
- Fresh session creation for the next agent
- Handoff with full context
- Checkpoint-and-resume if the next agent times out

## Architecture

```
Agent completes work
  │
  ▼
┌─────────────────────────────────────────────────────┐
│            ORCHESTRATOR                              │
│       (pipeline_orchestrate.py)                      │
│                                                      │
│  1. 💾 Save calling agent's memory (--learnings)    │
│  2. 📋 Update pipeline state (pipeline_update.py)   │
│  3. 📱 Telegram group notification                   │
│  4. 🔄 Generate fresh session (UUID4)               │
│  5. 📨 Build handoff message with full context      │
│  6. 🔔 Wake next agent (openclaw agent CLI)         │
│  7. ⏱️ If timeout → checkpoint → resume (up to 5×)  │
│  8. 📝 Write handoff record                         │
└─────────────────────────────────────────────────────┘
         │                    │                │
         ▼                    ▼                ▼
   ┌──────────┐       ┌──────────┐      ┌──────────┐
   │ Architect │       │  Critic  │      │ Builder  │
   │  (Opus)   │       │  (Opus)  │      │  (Opus)  │
   │ fresh ses │       │ fresh ses│      │ fresh ses│
   │ reads mem │       │ reads mem│      │ reads mem│
   └──────────┘       └──────────┘      └──────────┘
```

## Agent Session Model

### Fresh sessions, memory-based continuity
- **Every interaction = fresh session** — no context carries over in-session
- **Memory files = sole continuity** — agents read `memory/YYYY-MM-DD.md` at session start
- **Auto memory save** — orchestrator writes to agent memory at every boundary (complete, block, timeout)
- **10-minute session window** — enough for Opus to do substantial work per pass
- **Checkpoint-and-resume** — timeout doesn't mean failure, it means "save and continue"

### Checkpoint-and-resume flow
```
Session 1 (10 min) → timeout
  💾 Checkpoint: scan partial files, write summary to agent memory
  ↓
Session 2 (fresh, 10 min) → reads memory + partial artifacts → continues
  💾 Checkpoint if needed
  ↓
Session 3...up to 6 total (initial + 5 resumes = 60 min max)
  ↓ (if all timeout)
  📱 Alert Shael via Telegram — manual intervention needed
```

## Usage

### Agents call the orchestrator to transition stages:

```bash
# Complete a stage (auto-saves memory, auto-wakes next agent):
python3 scripts/pipeline_orchestrate.py <version> complete <stage> \
  --agent <role> \
  --notes "summary of what was done" \
  --learnings "key decisions, patterns, insights for future sessions"

# Block a stage (auto-saves memory, auto-wakes fixing agent):
python3 scripts/pipeline_orchestrate.py <version> block <stage> \
  --agent <role> \
  --notes "BLOCK-1: reason" \
  --artifact review_file.md \
  --learnings "what I found, why it's blocked"

# Start a stage (mark as in-progress):
python3 scripts/pipeline_orchestrate.py <version> start <stage> --agent <role>

# Show pipeline state:
python3 scripts/pipeline_orchestrate.py <version> show

# Check all pipelines for stuck handoffs:
python3 scripts/pipeline_orchestrate.py --check-pending

# Retry failed handoffs for a specific pipeline:
python3 scripts/pipeline_orchestrate.py <version> verify
```

### The --learnings flag

This is the agent's continuity mechanism. Written directly to the agent's `memory/YYYY-MM-DD.md` before the handoff. Be specific:
- Design decisions and WHY
- Patterns discovered
- What worked, what didn't
- Anything worth knowing next time you wake up fresh

## Stage Transition Maps

### Builder Pipeline (complete transitions)
| Completed Stage | Next Stage | Next Agent |
|----------------|------------|------------|
| pipeline_created | architect_design | architect |
| architect_design | critic_design_review | critic |
| critic_design_review | builder_implementation | builder |
| builder_implementation | critic_code_review | critic |
| critic_code_review | → phase complete | — |

### Builder Pipeline (block transitions)
| Blocked Stage | Fix Stage | Fix Agent |
|--------------|-----------|-----------|
| critic_design_review | architect_design_revision | architect |
| critic_code_review | critic_block_fixes | builder |

### Analysis Pipeline (complete transitions)
| Completed Stage | Next Stage | Next Agent |
|----------------|------------|------------|
| pipeline_created | analysis_architect_design | architect |
| analysis_architect_design | analysis_critic_review | critic |
| analysis_critic_review | analysis_builder_implementation | builder |
| analysis_builder_implementation | analysis_critic_code_review | critic |

## Separation of Concerns

| Component | Responsibility | Manages Sessions? |
|-----------|---------------|-------------------|
| **Orchestrator** (`pipeline_orchestrate.py`) | Memory save, state update, handoffs, timeouts | ✅ YES — single authority |
| **pipeline_update.py** | State tracking, stage history | ❌ Called by orchestrator |
| **Agents** | Do the actual work, write artifacts | ❌ Call orchestrator when done |
| **log_memory.py** | Record indexed memory entries | ❌ Called by orchestrator |
| **launch_pipeline.py** | Create pipeline instances | ❌ Calls orchestrator for kickoff |

## Related
- `skills/pipelines/SKILL.md` — full pipeline skill reference
- `skills/launch-pipeline/SKILL.md` — pipeline creation and kickoff
- `templates/pipeline.md` — builder pipeline template
- `templates/analysis_pipeline.md` — analysis pipeline template
