# HEARTBEAT.md — Context-Aware Orchestrator

## Orchestrator Reference

**Before executing tasks below, read `templates/heartbeat.md`** for the full decision framework, script reference, gate rules, and anti-patterns. That file is your HOW — this file is your WHAT.

---

## Task 1: Pipeline Automation (CODE-DRIVEN)

The primary heartbeat responsibility: move work forward. This is now **fully automated via script** — no LLM decision-making needed.

1. **Run the automation script:**
   ```bash
   python3 scripts/pipeline_autorun.py
   ```
   This automatically:
   - Clears stale session locks (dead/hung agent PIDs)
   - Monitors running experiments (progress, dead process recovery)
   - Checks analysis gates → kicks off downstream pipelines when gates open
   - Checks pending revision requests → kicks revisions from `pipeline_builds/*_revision_request.md`
   - Auto-launches experiments for `phase1_complete` pipelines (priority-ordered)
   - Detects stalled pipelines (>2h no activity) → re-kicks them with checkpoint-and-resume
   - One pipeline at a time, priority-ordered — pure event-driven logic

2. **Check open tasks** (still needs judgment):
   ```bash
   grep -l "status: open" tasks/*.md
   ```
   - For each open task, read its `depends_on` field
   - If dependencies are met AND no pipeline already exists → eligible for pipeline spawn
   - **Gate check:** `python3 scripts/pipeline_autorun.py --check-gates --dry-run` shows what's blocked
   - To create AND kick off: `belam pipeline launch {ver} --desc "..." --priority {p} --tags {t} --project {proj} --kickoff`
   - After spawning, update the task's `status: in_pipeline` and add `pipeline: {version}`

3. **If nothing to do:** skip silently

## Task 2: Handoff Verification

1. `python3 scripts/pipeline_orchestrate.py --check-pending`
2. If any handoffs are stuck, the script auto-retries and alerts the group
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
   - `belam pipeline v4-deep-analysis` → must show `analysis_phase2_complete`
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

1. `python3 scripts/launch_pipeline.py --list`
2. For any pipeline at `phase2_complete` or `phase3_complete`:
   - `python3 scripts/launch_pipeline.py <version> --check-archive`
   - If archivable → auto-archive with `--archive`
3. Skip silently if nothing to archive

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
