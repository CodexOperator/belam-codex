# HEARTBEAT.md — Context-Aware Orchestrator

## Orchestrator Reference

**Before executing tasks below, read `templates/heartbeat.md`** for the full decision framework, script reference, gate rules, and anti-patterns. That file is your HOW — this file is your WHAT.

---

## ~~Task 1: Pipeline Automation~~ (REMOVED 2026-03-24)
> **Removed:** `e0` orchestration sweep was causing gateway freezes — compound load from sweep + concurrent crons + codex_render on the Node event loop. Pipeline orchestration will be triggered manually or via dedicated commands, not heartbeat.

## ~~Task 2: Handoff Verification~~ (REMOVED 2026-03-24)
> **Removed:** Depended on `e0` sweep output. Handle manually.

## ~~Task 3: Experiment Analysis Pipeline~~ (REMOVED 2026-03-24)
> **Removed:** Part of pipeline automation. Run manually when needed.

## ~~Task 4: Phase 3 Iteration Chain Gate~~ (REMOVED 2026-03-24)
> **Removed:** Part of pipeline automation. Run manually when needed.

## ~~Task 5: Pipeline Archival~~ (REMOVED 2026-03-24)
> **Removed:** Part of pipeline automation. All active pipelines archived manually on 2026-03-24.

## Task 5: Infrastructure Pipeline Queue

**Scope:** Infra tasks only. Sequential (MAX_CONCURRENT=1). No research/experiment pipelines.

1. Check current pipeline status:
   - `python3 scripts/codex_engine.py p` — look at pipeline state suffix
   - If a pipeline is actively running (dispatched/running), skip — wait for it

2. If current pipeline reached `phase1_complete` or `phase2_complete`:
   - Archive it: `python3 scripts/pipeline_orchestrate.py {version} complete`
   - Update task status

3. If current pipeline reached `builder_verification` and verification FAILED (check `_test_results.json`):
   - Read the test results
   - Write findings as Phase 2 direction: `pipeline_builds/{version}_phase2_direction.md`
   - Kick Phase 2: `python3 scripts/pipeline_orchestrate.py {version} kickoff`
   - This turns verification failures into iterative improvement

4. If no pipeline is running, find next eligible infra task:
   - `ls tasks/*.md` — look for `status: open` + `tags:` containing `infrastructure`
   - Check `depends_on` are satisfied
   - Launch: `python3 scripts/launch_pipeline.py {slug} --desc "..." --type infrastructure --kickoff`
   - Update task status to `in_pipeline`

5. Skip silently if nothing to do

**Anti-patterns:**
- Do NOT launch research/experiment pipelines (SNN, trading, etc.)
- Do NOT run `e0` sweep (causes gateway load)
- Do NOT launch if a pipeline is already running
- Keep it lightweight — read state files, make one decision, exit

## Task 5.5: Render Engine Health Check

1. `systemctl is-active codex-render.service` — if not `active`, run `sudo systemctl restart codex-render.service`
2. Verify socket responds: `python3 scripts/codex_render.py --status`
3. If both fail, log a warning and continue — don't block heartbeat

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
