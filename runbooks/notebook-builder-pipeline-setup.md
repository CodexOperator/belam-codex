---
primitive: runbook
status: active
category: pipeline
tags: [snn, notebooks, multi-agent, colab]
last_executed: 2026-03-15
execution_count: 1
automation_script: scripts/setup_pipeline.py
estimated_time: 5-10 minutes
---

# Runbook: Notebook Builder Pipeline Setup

## Purpose
Spin up a complete multi-agent notebook builder pipeline for a new experiment version. Handles workspace configuration, agent access, symlinks, pipeline tracking, and agent kickoff.

## Prerequisites
- OpenClaw gateway running (`openclaw gateway status`)
- Agents configured: `architect`, `critic`, `builder` (check `openclaw status`)
- Agent Telegram bots active in group chat (-5243763228)
- Git repos accessible (machinelearning, workspace)

## Step 1: Create the Spec

Write a YAML spec file defining the experiments:

```bash
# Location: SNN_research/machinelearning/snn_applied_finance/specs/<version>_spec.yaml
# Required fields: version, name, description, experiments[]
# Each experiment: name, architecture, input_modes, encodings, output_scheme
# See specs/v4_spec.yaml as reference
```

Validate: `python3 scripts/build_notebook.py --validate <spec_path>`

## Step 2: Generate Design Brief

```bash
python3 scripts/build_notebook.py --spec <spec_path>
```

This creates:
- `research/pipeline_builds/<version>_design_brief.md`
- `research/pipeline_builds/<version>_state.json`

## Step 3: Ensure Agent Workspace Symlinks

Each agent workspace needs access to shared resources. Required symlinks:

```bash
SHARED_DIRS="skills templates lessons tasks decisions scripts pipelines runbooks"
AGENTS="architect critic builder"

for agent in $AGENTS; do
  ws="$HOME/.openclaw/workspace-$agent"
  for dir in $SHARED_DIRS; do
    src="$HOME/.openclaw/workspace/$dir"
    if [ -d "$src" ] && [ ! -e "$ws/$dir" ]; then
      ln -s "$src" "$ws/$dir"
    fi
  done
  # SNN_research symlink (should already exist)
  if [ ! -e "$ws/SNN_research" ]; then
    ln -s "$HOME/.openclaw/workspace/SNN_research" "$ws/SNN_research"
  fi
done
```

## Step 4: Verify Agent Tool Permissions

Architect and Critic need write/edit access for design docs and reviews:

```python
# In openclaw.json, ensure NO tools.deny for write/edit:
# agents.list[id=architect].tools should NOT contain deny: ["write", "edit"]
# agents.list[id=critic].tools should NOT contain deny: ["write", "edit"]
```

If changed, restart gateway: `openclaw gateway restart`

## Step 5: Update Agent AGENTS.md (if needed)

Each agent's `AGENTS.md` should include:
- Two-phase pipeline documentation
- Communication protocol (sessions_send labels + group chat)
- Skills references (quant-workflow, quant-infrastructure, etc.)
- Knowledge file references (ARCHITECT_KNOWLEDGE.md, etc.)

Templates are in the current agent workspace files — copy pattern from `workspace-architect/AGENTS.md`.

## Step 6: Create Pipeline Tracking Primitive

```bash
# Create pipelines/<version>-<name>.md with:
# - YAML frontmatter: primitive: pipeline, status, version, spec_file, agents, etc.
# - Stage history table
# - Experiment matrix summary
# - Artifact paths
# See pipelines/v4-differential-output.md as reference
```

## Step 7: Verify Global Skills Access

```bash
ls -la ~/.openclaw/skills/
# Should show symlinks to workspace/skills/*
# Skills auto-discovered by all agents across all channels
```

## Step 8: Kick Off the Pipeline

**Option A — Shael initiates in group chat:**
Message the architect bot in the Telegram group. The architect reads the design brief, sends to critic via sessions_send, iterates, then hands to builder.

**Option B — Belam (main) initiates via sessions_send:**
```
sessions_send(label="architect", message="New pipeline: read <design_brief_path> and begin Phase 1...")
```
Note: This sends through OpenClaw internal routing, bypassing Telegram bot-to-bot limitation.

**Option C — Automated via setup script:**
```bash
python3 scripts/setup_pipeline.py --spec <spec_path> --kickoff
```

## Step 9: Monitor Pipeline Progress

- Heartbeat scans `pipelines/` for active stages
- Check state: `python3 scripts/build_notebook.py --status <version>`
- Agent conversations visible in group chat
- Pipeline primitive updated by agents as they progress

## Phase 2 Trigger (After Phase 1 Complete)

When Shael has reviewed the autonomous notebook:

```bash
# Write feedback to a file, then:
python3 scripts/build_notebook.py --revise <version> --feedback <feedback_path>
```

This generates a revision brief and updates pipeline state. Kick off agents again for the rebuild cycle.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Agent can't write files | Check `openclaw.json` → `agents.list[].tools.deny` |
| Agent can't see shared files | Verify symlinks in `~/.openclaw/workspace-<agent>/` |
| Sessions_send fails between agents | Use filesystem artifacts as fallback, Belam-main relays |
| Bot-to-bot messages not visible | Expected — Telegram limitation. Use sessions_send or filesystem |
| Gateway won't restart | Check `openclaw.json` for JSON syntax errors, run `openclaw doctor --fix` |
| Pipeline state stale | Manually update `pipelines/<version>.md` or `pipeline_builds/<version>_state.json` |

## Automation Script

`scripts/setup_pipeline.py` automates Steps 2-7 in a single command:

```bash
# Full setup (validates spec, generates brief, creates symlinks, checks permissions, 
# creates pipeline primitive, verifies skills):
python3 scripts/setup_pipeline.py --spec specs/<version>_spec.yaml

# With automatic kickoff (sends to architect agent after setup):
python3 scripts/setup_pipeline.py --spec specs/<version>_spec.yaml --kickoff

# Verify existing pipeline setup is complete:
python3 scripts/setup_pipeline.py --verify <version>
```

### What `setup_pipeline.py` does:
1. ✅ Checks gateway health (`http://127.0.0.1:18789/health`)
2. ✅ Validates spec YAML (required fields, experiment structure)
3. ✅ Calls `build_notebook.py --spec` to generate design brief + pipeline state
4. ✅ Creates/verifies symlinks for all agent workspaces (shared dirs + SNN_research)
5. ✅ Verifies agent tool permissions in `openclaw.json` (write/edit not denied)
6. ✅ Creates pipeline tracking primitive in `pipelines/`
7. ✅ Verifies global skills in `~/.openclaw/skills/`

### Related scripts:
- `scripts/build_notebook.py` — Pipeline state management (Phase 1 briefs, Phase 2 revisions, status)
- `scripts/analyze_experiment.py` — Post-experiment analysis (notebook diffs, lesson extraction)

### Full setup from scratch:
See the knowledge base README: `knowledge-repo/README.md` for bootstrapping a fresh OpenClaw instance with the complete primitives system, skills, and multi-agent workspace configuration.
