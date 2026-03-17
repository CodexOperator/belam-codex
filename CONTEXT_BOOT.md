# CONTEXT_BOOT.md

Every session, orient yourself before diving in.

## Quick Start

```bash
# At any session start — get a fast overview:
python3 scripts/generate_session_context.py --brief
```

## Full Briefing

```bash
# Full context with all sections:
python3 scripts/generate_session_context.py
```

## Role-Specific

```bash
# Load role knowledge + current state:
python3 scripts/generate_session_context.py --role architect
python3 scripts/generate_session_context.py --role critic
python3 scripts/generate_session_context.py --role builder
```

## Pipeline Work

```bash
# Deep context for a specific pipeline:
python3 scripts/generate_session_context.py --pipeline v4-analysis

# Combined — best for starting pipeline stage work:
python3 scripts/generate_session_context.py --pipeline v4-analysis --role architect
python3 scripts/generate_session_context.py --pipeline v4-analysis --role critic
python3 scripts/generate_session_context.py --pipeline v4-analysis --role builder
```

## What the Briefing Contains

| Section | Content |
|---------|---------|
| **A. Active Pipelines** | Status, pending action, current stage for all `pipelines/*.md` |
| **B. Recent Memories** | Last 2 days from `memory/YYYY-MM-DD.md` |
| **C. Available Scripts** | All `scripts/*.py` with one-line descriptions |
| **D. Available Skills** | All `skills/*/SKILL.md` with descriptions |
| **E. Recent Lessons** | Last 5 lessons from `lessons/` by modification date |
| **F. Role Context** | Agent definition + knowledge file (if `--role` given) |
| **G. Pipeline Context** | Pipeline definition + state JSON + latest artifacts (if `--pipeline` given) |

## Pipeline Stage Orchestration

To run a pipeline stage (send task to agent, poll for completion, archive transcript):

```bash
# Run a specific stage:
python3 scripts/run_pipeline_stage.py v4-analysis architect_design

# Dry run (see what would happen):
python3 scripts/run_pipeline_stage.py v4-analysis architect_design --dry-run

# Run the full pipeline autonomously:
python3 scripts/run_pipeline_stage.py v4-analysis --auto

# With custom timeout:
python3 scripts/run_pipeline_stage.py v4-analysis builder_implementation --timeout 90
```

## Transcript Archiving

To archive a specific agent's session as training data:

```bash
python3 scripts/archive_session_transcript.py \
    --session-key "agent:architect:telegram:group:-5243763228" \
    --pipeline v4-analysis \
    --stage architect_design \
    --output-dir "machinelearning/snn_applied_finance/conversations/"

# List available sessions for an agent:
python3 scripts/archive_session_transcript.py \
    --session-key "agent:architect:telegram:group:-5243763228" \
    --list-sessions
```

---

_This file is your navigation anchor. The scripts handle the rest._
