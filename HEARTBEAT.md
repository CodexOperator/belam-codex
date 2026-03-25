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
**Frequency:** Every 12 hours (not every heartbeat). Check `/tmp/openclaw_last_pipeline_check.ts` — if it exists and is less than 12 hours old, skip this entire task silently. Update the timestamp file after completing a check (whether or not a pipeline was launched).

1. Check current pipeline status:
   - `grep "^status:" pipelines/*.md | grep -vE "archived"` — look at active pipeline states
   - If a pipeline is actively running (dispatched/in_progress/architect_design/critic_*/builder_*), skip — wait for it

2. If current pipeline reached `phase1_complete`:
   - Check test results: `pipeline_builds/{version}_test_results.md` or `machinelearning/.../pipeline_builds/{version}_test_results.md`
   - If tests **PASSED (GREEN)**: mark pipeline as archived, update task status to `done`
   - If tests **FAILED**: write findings as Phase 2 direction (`pipeline_builds/{version}_phase2_direction.md`), then kick Phase 2: `python3 scripts/pipeline_orchestrate.py {version} kickoff`
   - **Do NOT auto-kick Phase 2 on passed pipelines** — Phase 2 is only for fixing failures

3. If no pipeline is running, find next eligible infra task:
   - `ls tasks/*.md` — look for `status: open` + `tags:` containing `infrastructure`
   - **Sort by priority:** high → medium → low. Within same priority, prefer tasks with no unmet `depends_on`
   - Check `depends_on` AND `upstream` are satisfied (upstream tasks must be `done` or `archived`)
   - Launch: `python3 scripts/launch_pipeline.py {slug} --desc "..." --type infrastructure --kickoff`
   - Update task status to `in_pipeline`

4. Skip silently if nothing to do

**Anti-patterns:**
- Do NOT launch research/experiment pipelines (SNN, trading, etc.)
- Do NOT run `e0` sweep (causes gateway load)
- Do NOT launch if a pipeline is already running
- Do NOT auto-kick Phase 2 when Phase 1 tests passed — this causes dispatch loops
- Keep it lightweight — read state files, make one decision, exit

## ~~Task 5.5: Render Engine Health Check~~ (REMOVED 2026-03-25)
> **Removed:** Render daemon retired. Supermap is now rendered on-demand by `scripts/render_supermap.py` (called directly by cockpit plugin V10). No daemon to health-check.

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

## Task 8: Telegram Summary to Shael

Send Shael a brief Telegram message summarizing heartbeat activity. Include:
- Which tasks were launched into pipelines (if any)
- Which pipelines finished — include test results (passed/failed, test count)
- Which pipelines are still running
- Any errors or issues found
- Skip this task if nothing changed since last heartbeat (no launches, no completions, no errors)

## Task 9: Agent Conversation Export

1. `python3 scripts/export_agent_conversations.py --since 2`
2. Skip silently if no new conversations

---

## Completed Tasks (Archive)

### ~~Task: Monitor SNN Standard Model Experiments~~
✅ **COMPLETED 2026-03-12 23:58 UTC** — All 26 experiments finished (0 failures). Report synthesis complete.
