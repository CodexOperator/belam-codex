---
primitive: orchestrator
name: Pipeline Stage Orchestrator
description: >
  Manages pipeline stage execution as fresh agent sessions with context carry-over.
  The orchestrator is the SINGLE AUTHORITY for session lifecycle — agents do not
  manage their own resets. pipeline_update.py tracks state; the orchestrator manages sessions.
fields:
  scripts:
    type: object
    description: "Core scripts that make up the orchestrator system"
    properties:
      run_stage:
        type: string
        default: "scripts/run_pipeline_stage.py"
        description: "Main orchestrator — resets sessions, injects context, sends tasks, polls completion, archives transcripts"
      generate_context:
        type: string
        default: "scripts/generate_session_context.py"
        description: "Generates dynamic session briefing from current pipeline state, memories, skills, lessons"
      archive_transcript:
        type: string
        default: "scripts/archive_session_transcript.py"
        description: "Reads JSONL transcripts, formats as markdown, saves to conversations/ as training data"
      pipeline_update:
        type: string
        default: "scripts/pipeline_update.py"
        description: "Lightweight state tracker — updates stage history + state JSON, prints ping instructions. Does NOT manage sessions."
      log_memory:
        type: string
        default: "scripts/log_memory.py"
        description: "Quick memory entry logging with categories, tags, importance levels"
  session_management:
    type: object
    description: "How sessions are managed per pipeline stage"
    properties:
      reset_policy:
        type: string
        default: "smart-carry-over"
        description: "Only reset agents that weren't in the previous stage. Agents bridging stages keep context."
      reset_method:
        type: string
        default: "openclaw gateway call sessions.reset"
        description: "Gateway API method to reset a session to a fresh ID"
      context_injection:
        type: string
        default: "generate_session_context.py --pipeline {version} --role {role}"
        description: "How context is injected after reset"
  agent_pairs:
    type: object[]
    description: "Agent pair assignments per stage type"
  lifecycle:
    type: string[]
    description: "Stage lifecycle steps"
    default: ["reset → context inject → send task → poll completion → log memory → archive transcript"]
---

# Pipeline Stage Orchestrator

## What It Does

The orchestrator manages the **session lifecycle** for each pipeline stage. It ensures:
- Fresh, lean context for agents entering a new stage
- Smart carry-over for agents bridging consecutive stages
- Memory logging after each stage
- Transcript archival for training data

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                       │
│            (run_pipeline_stage.py)                   │
│                                                      │
│  1. Reset NEW agents (sessions.reset)               │
│  2. Generate context (generate_session_context.py)  │
│  3. Send task to primary agent (sessions_send)      │
│  4. Poll state JSON for completion                  │
│  5. Log memory (log_memory.py)                      │
│  6. Archive transcript (archive_session_transcript) │
│  7. Advance to next stage (if --auto)               │
└─────────────────────────────────────────────────────┘
         │                    │                │
         ▼                    ▼                ▼
   ┌──────────┐       ┌──────────┐      ┌──────────┐
   │ Architect │◄─────►│  Critic  │◄────►│ Builder  │
   │(sessions) │       │(sessions)│      │(sessions)│
   └──────────┘       └──────────┘      └──────────┘
   sessions_send       sessions_send     sessions_send
   (between agents)    (between agents)  (between agents)
```

## Usage

```bash
# Run a single stage
python3 scripts/run_pipeline_stage.py v4-analysis analysis_builder_implementation

# Run full pipeline autonomously
python3 scripts/run_pipeline_stage.py v4-analysis --auto

# Preview what would happen
python3 scripts/run_pipeline_stage.py v4-analysis analysis_builder_implementation --dry-run

# Skip session resets (preserve all context)
python3 scripts/run_pipeline_stage.py v4-analysis analysis_builder_implementation --no-reset

# Custom timeout (default: 30 min per stage)
python3 scripts/run_pipeline_stage.py v4-analysis --auto --timeout 60
```

## Context Carry-Over

Only agents NEW to a stage get reset. Agents bridging consecutive stages keep their context:

| Stage | Architect | Critic | Builder |
|-------|-----------|--------|---------|
| architect_design | 🆕 fresh | 🆕 fresh | — |
| critic_review | ↪ carries design | 🆕 fresh | — |
| builder_implementation | ↪ carries review | — | 🆕 fresh |
| critic_code_review | — | 🆕 fresh | ↪ carries build |

This is tracked via `_last_stage_agents` in the pipeline state JSON.

## Agent Pair Assignments

### Analysis Pipeline
| Stage | Primary | Review | Primary Skill | Review Skill |
|-------|---------|--------|---------------|--------------|
| analysis_architect_design | architect | critic | quant-workflow | quant-workflow |
| analysis_critic_review | critic | architect | quant-workflow | quant-workflow |
| analysis_builder_implementation | builder | architect | quant-infrastructure | quant-workflow |
| analysis_critic_code_review | critic | builder | quant-infrastructure | quant-infrastructure |

### Builder Pipeline
| Stage | Primary | Review | Primary Skill | Review Skill |
|-------|---------|--------|---------------|--------------|
| architect_design | architect | critic | quant-workflow | quant-workflow |
| critic_design_review | critic | architect | quant-workflow | quant-workflow |
| builder_implementation | builder | architect | quant-infrastructure | quant-workflow |
| critic_code_review | critic | builder | quant-infrastructure | quant-infrastructure |

## Separation of Concerns

| Component | Responsibility | Manages Sessions? |
|-----------|---------------|-------------------|
| **Orchestrator** (`run_pipeline_stage.py`) | Session lifecycle, context injection, polling, archival | ✅ YES — the single authority |
| **pipeline_update.py** | State tracking, stage history, ping instructions | ❌ NO — lightweight state only |
| **Agents** (architect/critic/builder) | Do the actual work, use sessions_send to communicate | ❌ NO — orchestrator handles resets |
| **generate_session_context.py** | Produce context briefings | ❌ NO — called by orchestrator |
| **log_memory.py** | Record memories | ❌ NO — called by orchestrator |

## Context Bootstrap (for any session)

Any agent can get up to speed by running:
```bash
python3 scripts/generate_session_context.py --brief
python3 scripts/generate_session_context.py --pipeline v4-analysis --role architect
```

This reads: active pipelines, recent memories, available scripts/skills, recent lessons, role-specific knowledge, pipeline-specific state.

## Memory & Training Data Flow

```
Stage completes
  → log_memory.py records the event
  → export_agent_conversations.py exports recent transcripts
  → archive_session_transcript.py formats JSONL → markdown
  → conversations/ directory grows as training dataset
  → weekly_knowledge_sync.py (cron) processes lessons → knowledge graph
```

## Related Primitives
- `templates/pipeline.md` — builder pipeline template
- `templates/analysis_pipeline.md` — analysis pipeline template
- `templates/memory_log.md` — memory entry template
- `CONTEXT_BOOT.md` — bootstrap instructions for any agent session
