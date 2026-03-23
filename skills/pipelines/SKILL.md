---
name: pipelines
description: >
  List, create, check, and archive Implementation Pipelines — the 3-phase research lifecycle
  (autonomous build → human-in-the-loop → iterative research) for SNN notebook versions.
  Use when: user says "pipelines", "pipeline list", "launch pipeline", "archive pipeline",
  "pipeline status", or asks about active/completed notebook versions.
  Also use when an agent needs to check pipeline state, verify phase gates, or find its
  current build stage.
---

# Pipelines

Implementation Pipelines track notebook versions through 3 phases:
1. **Phase 1:** Autonomous build (architect → critic → builder)
2. **Phase 2:** Human-in-the-loop (feedback → revision → rebuild)
3. **Phase 3:** Iterative research (gated on phase 2 completion, scored proposals)

All phases live in a **single notebook** as top-level sections.

## CLI Commands (`belam`)

The `belam` CLI (at `~/.local/bin/belam`, on PATH) wraps all pipeline and primitive scripts. **Prefer `belam` commands** — they work from any directory.

### Pipelines
```bash
R pipelines                    # Dashboard: all pipelines with status
R pipeline <ver>               # Detail view with full stage history
R pipeline <ver> --watch [sec] # Live auto-refresh (default 10s)
R pipeline update <ver> <cmd>  # Update stage (complete/start/block/status/show)
R pipeline launch <ver> --desc "..."  # Create new pipeline
R pipeline analyze <ver>       # Launch analysis pipeline
R kickoff <ver>                # Kick off a created pipeline (wake architect via orchestrator)
R orchestrate <ver> <action>   # Orchestrated stage transition (auto-handoff)
R handoffs                     # Check for stuck/pending handoffs
```

### Experiment Analysis
```bash
R analyze <ver>                # Run analysis (auto-finds analysis pipeline)
R analyze --detect             # Auto-detect new experiment results
R analyze --check-gate <ver>   # Check Phase 3 gate
```

### Primitives
```bash
R tasks                        # List tasks (with status + tags)
R task <name>                  # Show one task (fuzzy match)
R lessons                      # List lessons
R projects                     # List projects
R decisions                    # List decisions
```

### Memory & Status
```bash
R status                       # Full overview: pipelines + tasks + memory + git
R log "message"                # Quick memory entry
R log -t tag "message"         # Tagged memory entry
R consolidate                  # Run memory consolidation
```

### Shortcuts
`R pl` = pipelines, `R p` = pipeline, `R t` = tasks, `R l` = lessons,
`R d` = decisions, `R pj` = projects, `R s` = status, `R a` = analyze

## Direct Script Commands (equivalent)

Scripts are in the workspace `scripts/` directory. The `belam` CLI calls these under the hood.

| R command | Script equivalent |
|---------------|-------------------|
| `R pipelines` | `python3 scripts/pipeline_dashboard.py` |
| `R pipeline <ver>` | `python3 scripts/pipeline_dashboard.py <ver>` |
| `R pipeline update <ver> ...` | `python3 scripts/pipeline_update.py <ver> ...` |
| `R pipeline launch <ver> ...` | `python3 scripts/launch_pipeline.py <ver> ...` |
| `R pipeline analyze <ver>` | `python3 scripts/launch_analysis_pipeline.py <ver>` |
| `R analyze <ver>` | `python3 scripts/analyze_experiment.py --notebook <ver>` |
| `R analyze --check-gate <ver>` | `python3 scripts/analyze_experiment.py --check-gate <ver>` |
| `R log "msg"` | `python3 scripts/log_memory.py "msg"` |

### Generate phase 3 proposal (autonomous)
```bash
python3 scripts/analyze_experiment.py --propose-auto '{"version":"<ver>","id":"<id>","hypothesis":"...","justification":"...","score":<1-10>,"proposed_by":"<role>"}'
```
Score ≥ 7 = auto-approved, 4-6 = flagged for review, < 4 = rejected.

## Pipeline files

- **Templates:** `templates/pipeline.md`, `templates/analysis_pipeline.md`, `templates/launch-pipeline.md`, `templates/orchestrator.md`
- **Instances:** `pipelines/<version>.md` (one per notebook version)
- **Build artifacts:** `machinelearning/snn_applied_finance/research/pipeline_builds/<version>_*`
- **State JSON:** `pipeline_builds/<version>_state.json`
- **Handoff records:** `pipelines/handoffs/<timestamp>_<version>_<agent>.json`
- **Launch skill:** `skills/launch-pipeline/SKILL.md` — full decision flow for gate checking + kickoff

## Agent Session Model

Each agent (architect, critic, builder) runs as a **persistent OpenClaw instance on Opus** with its own workspace and memory files. Key properties:

- **Fresh session per interaction** — every handoff spawns a new session (UUID4). No session reuse.
- **Memory files are the ONLY continuity** — agents must read their `memory/` directory at session start.
- **10-minute session window** — agents have 600s per session to complete their work.
- **Checkpoint-and-resume on timeout** — if an agent times out, the orchestrator:
  1. Scans for partial artifacts the agent created
  2. Writes a checkpoint to the agent's memory files
  3. Wakes the agent again with a fresh session + resume context
  4. Up to 5 resume cycles (60 min total) before alerting
- **Auto memory consolidation** — the `--learnings` flag on orchestrator calls writes directly to the agent's memory files. Agents don't need to manually save.

## For agents — MANDATORY orchestrator protocol

**All stage transitions go through the centralized orchestrator.** ONE command handles everything:

### When you COMPLETE work:
```bash
python3 scripts/pipeline_orchestrate.py <version> complete <stage> \
  --agent <your_role> \
  --notes "summary of what you did" \
  --learnings "key decisions, patterns, insights worth keeping across sessions"
```

### When you BLOCK work:
```bash
python3 scripts/pipeline_orchestrate.py <version> block <stage> \
  --agent <your_role> \
  --notes "BLOCK-1: reason" \
  --artifact your_review_file.md \
  --learnings "what I found, why it's blocked, what the fix should look like"
```

### When you START work:
```bash
python3 scripts/pipeline_orchestrate.py <version> start <stage> --agent <your_role>
```

The orchestrator automatically:
1. **Saves your memory** — `--notes` and `--learnings` written to your `memory/YYYY-MM-DD.md`
2. **Updates pipeline state** — JSON + markdown + frontmatter status bumps
3. **Notifies Telegram group** — human-visible progress update
4. **Wakes the next agent** — fresh session with full context (files to read, what to do)
5. **Handles timeouts** — checkpoint-and-resume if the next agent needs more time
6. **Logs handoff records** — for verification and debugging

**DO NOT manually call `sessions_send`, `pipeline_update.py`, or post to the group chat for stage transitions.** The orchestrator handles all of it.

### The `--learnings` flag

This is your continuity mechanism. Be specific about what you'd want to know if you woke up with no memory:
- Design decisions and WHY
- Patterns discovered
- What worked, what didn't
- Architectural insights
- Blockers encountered and how they were resolved

### Manual Group Chat Posts
Post to group chat (`message` tool, target `-5243763228`) ONLY for:
- Significant findings or insights during your work
- Questions for Shael or other agents
- Non-stage updates

## Read before starting:
Read `pipelines/<version>.md` for current phase, stage history, feedback, and iteration log.
