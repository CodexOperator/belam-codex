# HEARTBEAT.md — Context-Aware Orchestrator

## Orchestrator Reference

**Before executing tasks below, read `templates/heartbeat.md`** for the full decision framework, script reference, gate rules, and anti-patterns. That file is your HOW — this file is your WHAT.

---

## Task 1: Pipeline Automation (CODE-DRIVEN)

The primary heartbeat responsibility: move work forward via the orchestration sweep.

1. **Run `e0`** — the orchestration sweep:
   ```bash
   e0
   ```
   This automatically: clears stale locks, monitors experiments, checks gates, kicks downstream pipelines, handles revisions, detects stalls (>2h), and re-kicks with checkpoint-and-resume. One pipeline at a time, priority-ordered.

2. **Check open tasks** (still needs judgment):
   - `e0` output shows eligible tasks. For each with met dependencies and no existing pipeline:
   - Create AND kick off: `R pipeline launch {ver} --desc "..." --priority {p} --tags {t} --project {proj} --kickoff`
   - After spawning: `e1{task_coord} status in_pipeline`

3. **If nothing to do:** skip silently

## Task 2: Handoff Verification

1. `e0` already checks pending handoffs in the sweep output
2. If any are stuck, the sweep auto-retries and alerts the group
3. Skip silently if all clear

## Task 3: Experiment Analysis Pipeline

Detect new experiment results and extract lessons:

1. Run `python3 scripts/analyze_experiment.py --detect --quiet`
2. If briefs were generated, spawn a sub-agent with task:
   "Read all pending analysis briefs in machinelearning/snn_applied_finance/research/pipeline_output/ (files with 'status: pending_review'). For each brief:
   1. Read the code changes section — these are Shael's manual tweaks (highest-signal data)
   2. Create lesson primitives in workspace/lessons/ for significant findings
   3. Update research/TECHNIQUES_TRACKER.md with new results
   4. Update the brief's frontmatter to 'status: processed'
   5. If findings change architectural direction, update the relevant *_KNOWLEDGE.md
   6. If analysis reveals a compelling follow-up (score ≥ 7), generate Phase 3 proposal:
      `python3 scripts/analyze_experiment.py --propose-auto '{...}'`
   7. Commit changes to the machinelearning repo"
3. If no briefs, skip silently

## Task 4: Phase 3 Iteration Chain Gate

Manage the interleaved Phase 3 iteration chain between main and analysis pipelines.

1. Check if analysis Phase 2 is complete (gate for all Phase 3 work):
   - `R pipeline v4-deep-analysis` → must show `analysis_phase2_complete`
   - If not complete: skip all Phase 3 work silently
2. If gate is open, check iteration chain state:
   - Find the latest main pipeline Phase 3 iteration ID (from `pipelines/v4.md` iteration log)
   - Check if there are pending/in-progress analysis Phase 3 iterations for that main iteration
   - **If analysis iterations are pending/in-progress:** do NOT spawn new main iterations — wait
   - **If all analysis iterations for current main iter are complete AND none pending:** next main iteration is eligible
3. Check for Phase 3 proposals (`*phase3*proposal*.md`):
   - `status: approved` + chain clear → spawn builder agent
   - `status: pending_review` → alert Shael with hypothesis + score
4. If no proposals or chain is blocked, skip silently

## Task 5: Pipeline Archival

1. `R pipeline --check-supersedes` (auto-archives pipelines superseded by active ones)
2. Check supermap `p` namespace for pipelines at `phase2_complete` or `phase3_complete`
3. For any archivable pipeline: `R pipeline {version} --archive`
4. Skip silently if nothing to archive

## Task 6: Git Commits (Both Repos)

**Lesson:** `lessons/always-back-up-workspace-to-github.md` — if it's not pushed, it doesn't exist.

1. **Workspace (belam-codex):**
   - `git status --short` (from workspace root)
   - If uncommitted changes: `git add -A && git commit -m "Auto-commit: workspace updates [$(date -u +'%Y-%m-%d %H:%M UTC')]" && git push origin`
2. **Research (machinelearning):**
   - `cd machinelearning && git status --short`
   - If uncommitted changes: `git add -A && git commit -m "Auto-commit: research updates [$(date -u +'%Y-%m-%d %H:%M UTC')]" && git push origin`
3. Skip silently if both clean

## Task 7: Memory Maintenance

1. `python3 scripts/consolidate_memories.py --check 2>/dev/null`
2. If entries need consolidation, run `python3 scripts/consolidate_memories.py`
3. Skip silently if nothing to consolidate

_Note: embed_primitives.py is archived — supermap is injected at boot via hook._

## Task 8: Agent Conversation Export

1. `python3 scripts/export_agent_conversations.py --since 2`
2. Skip silently if no new conversations

---

## Completed Tasks (Archive)

### ~~Task: Monitor SNN Standard Model Experiments~~
✅ **COMPLETED 2026-03-12 23:58 UTC** — All 26 experiments finished (0 failures). Report synthesis complete.
