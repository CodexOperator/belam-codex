---
primitive: heartbeat
name: Heartbeat Orchestrator
description: >
  Context-aware heartbeat reference for the Sonnet coordinator model.
  Loaded each heartbeat cycle to enable intelligent task triage, pipeline spawning,
  and autonomous work progression. This is the HOW — HEARTBEAT.md is the WHAT.
---

# Heartbeat Orchestrator Reference

## Decision Framework

Each heartbeat cycle, evaluate tasks and pipelines in this priority order:

### 1. Check Active Pipelines
```bash
R pipelines
```
- If any pipeline has a stalled stage (>2h since last update), alert Shael
- If a pipeline reached phase completion, check if downstream work can be unblocked

### 2. Check Open Tasks
```bash
grep -l "status: open" tasks/*.md
```
For each open task:
- Read `depends_on` — skip if dependencies aren't met
- Check if a pipeline already exists for this task (`R pipelines` output)
- If no pipeline exists AND dependencies are clear → eligible for pipeline spawn

### 3. Gate Awareness

**Analysis Phase 2 gate (MANDATORY):** Once the analysis pipeline reaches `analysis_phase2_complete`, it unlocks THREE things simultaneously:
1. V{N} main pipeline Phase 3 iterations
2. V{N} analysis pipeline Phase 3 iterations
3. V{N+1} implementation pipeline Phase 1

Check: `R pipeline v4-deep-analysis`

**Phase 3 Iteration Chain Protocol:**
```
Main Phase 3 iter 01 → Analysis Phase 3 iter 01a, 01b, 01c...
  (all analysis iters complete, none pending) →
Main Phase 3 iter 02 → Analysis Phase 3 iter 02a, 02b...
  (all clear) →
Main Phase 3 iter 03 → ...
```

Rules:
- Every analysis Phase 3 iteration MUST be preceded by a corresponding main pipeline Phase 3 iteration (can't analyze what wasn't built)
- Multiple analysis iterations allowed per single main iteration (deep dives, follow-ups)
- Next main iteration ONLY when ALL analysis iterations for the current one are complete AND no more analysis Phase 3 iterations are pending on the task list
- All Phase 3 iterations append to the existing notebook (both main and analysis — never new files)

**Tasks that DON'T need the analysis gate:**
- Infrastructure setup (backtesting, data pipelines)
- Specialist ensemble stacking (uses existing v3 results)
- Scheme B validation (uses existing v3 results)
- Any task with `depends_on: []` that isn't a new notebook version
- These get built as standalone Colab notebooks in `notebooks/standalone/`

**Tasks that DO need the analysis gate:**
- `build-equilibrium-snn` → This IS the next notebook version (v5 candidate)
- Any task creating a new `snn_crypto_predictor_v{N}.ipynb`

### 4. Pipeline Spawn Decision

When a task is eligible for a pipeline:

**For implementation tasks** (building notebooks, models, infrastructure):

If a pipeline already exists but was never kicked off (check `R pipelines` — shows `pipeline_created` with no agent activity):
```bash
R kickoff {version}
```

If no pipeline exists yet, create and kick off in one step:
```bash
R pipeline launch {version} \
  --desc "{description from task}" \
  --priority {task priority} \
  --tags {task tags} \
  --project {task project} \
  --kickoff
```

Both paths use the orchestrator to wake the architect with a fresh session via `openclaw agent`.

**For analysis of completed experiments:**
```bash
python3 scripts/launch_analysis_pipeline.py {version}-analysis \
  --source-version {version} \
  --source-pkl machinelearning/snn_applied_finance/notebooks/{pkl_dir}/ \
  --desc "{what to analyze}" \
  --priority {priority} \
  --tags {tags} \
  --kickoff
```

### 5. Task-to-Pipeline Mapping

Not every task warrants a full 3-agent pipeline. Use judgment:

| Task Type | Pipeline? | Output Location | Why |
|-----------|-----------|-----------------|-----|
| New notebook version | Yes — full pipeline | `notebooks/snn_crypto_predictor_v{N}.ipynb` | Complex, needs design review |
| Experiment validation (more folds) | Yes — builder pipeline | `notebooks/standalone/{task-slug}.ipynb` | Needs proper notebook, Colab execution |
| Ensemble stacking | Yes — builder pipeline | `notebooks/standalone/{task-slug}.ipynb` | Novel architecture, needs critique |
| Infrastructure setup (vectorbt, etc.) | No — single agent | `notebooks/standalone/{task-slug}.ipynb` | Config/install, simpler scope |
| Data collection | No — single agent | scripts or datasets/ | Scripting, not multi-agent design |

**All research tasks produce Colab-ready notebooks** — even non-pipeline tasks. Output goes to `notebooks/standalone/` with the task slug as filename. This keeps everything drop-in ready for Colab.

For non-pipeline tasks, spawn a focused sub-agent:
```
sessions_spawn with task: "Read tasks/{task-file}.md and implement it as a Colab notebook.
Follow GPU/training guidelines from templates/pipeline.md.
Output: machinelearning/snn_applied_finance/notebooks/standalone/{task-slug}.ipynb
Export results as pkl for potential analysis pipeline ingestion."
```

## Script Reference

### Pipeline Management
| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `scripts/launch_pipeline.py` | Create builder pipeline | `--kickoff`, `--start`, `--list`, `--archive` |
| `scripts/launch_analysis_pipeline.py` | Create analysis pipeline | `--kickoff`, `--source-version`, `--list` |
| `scripts/pipeline_update.py` | Update pipeline stage | `{ver} complete\|block\|start\|show {stage} "{notes}" {agent}` |
| `scripts/pipeline_dashboard.py` | Live dashboard | `--watch [seconds]` |

### Analysis & Experiments
| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `scripts/analyze_experiment.py` | Detect new results, generate briefs | `--detect`, `--notebook {ver}`, `--check-gate {ver}`, `--propose-auto '{json}'` |
| `scripts/build_notebook.py` | Build/compile notebook | Check `--help` |

### Memory & Knowledge
| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `scripts/log_memory.py` | Quick memory entry | `"message"`, `--workspace {path}` |
| `scripts/consolidate_memories.py` | Daily roll-up | `--check`, `--all-agents` |
| `scripts/daily_agent_memory.py` | Agent memory consolidation | Runs via cron midnight |
| `scripts/weekly_knowledge_sync.py` | Knowledge graph update | `--all-agents`, Monday 3AM cron |
| `scripts/sync_knowledge_repo.py` | Sync to portable repo | `--dry-run` (default), `--execute` |

### Agent Communication
| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `scripts/export_agent_conversations.py` | Export transcripts | `--since {hours}` |
| `scripts/generate_session_context.py` | Build agent context | Check `--help` |

## Agent Session Keys

For `sessions_send` with `timeoutSeconds: 0`:
- **Architect:** `agent:main:subagent:{session_id}` (check via `sessions_list`)
- **Critic:** `agent:critic:telegram:group:-5243763228`
- **Builder:** `agent:builder:telegram:group:-5243763228`

Always use `timeoutSeconds: 0` — agents may take minutes to respond.

## CLI Quick Reference (belam)

```bash
R status          # Full overview
R pipelines       # Pipeline dashboard
R pipeline v4     # Detail view
R tasks           # Open tasks
R lessons         # Lessons learned
R analyze v4      # Trigger analysis
R log "message"   # Quick memory entry
R sync            # Sync to knowledge repo
```

## Anti-Patterns

- **Don't spawn pipelines for gated tasks** — check the gate first
- **Don't use sessions_send with timeout > 0** — agents are slow, it'll timeout
- **Don't put data in sessions_send payloads** — write files, then ping
- **Don't create pipelines for tasks that already have one** — check `R pipelines` first
- **Don't skip pipeline_update.py** — it's the single write path for state + frontmatter sync
- **Don't launch new versions without analysis gate clearance** — MANDATORY
