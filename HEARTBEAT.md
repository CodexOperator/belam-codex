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

## Task 5: VectorBT/Nautilus Subtask Queue (S2–S6)

**Scope:** ONLY `setup-vectorbt-nautilus-pipeline-s{2..6}` tasks. Sequential (MAX_CONCURRENT=1). Nothing else.
**Type:** builder-first (all these are builder-first pipelines).
**Frequency:** Every heartbeat.
**Stop condition:** When S6 is done, this task is complete. Remove it.

**Completed:** S1 (environment setup) — done, critic approved, 22/22 tests GREEN.

1. Check current pipeline status:
   - `grep "^status:" pipelines/*.md | grep -vE "archived"` — look for active vectorbt pipelines
   - If one is running (any non-archived status), skip — wait for it

2. If current pipeline reached `p1_complete`:
   - If critic approved (0 blocks): mark pipeline archived, update task to `done`
   - If critic blocked: write Phase 2 direction, kick Phase 2
   - Do NOT auto-kick Phase 2 on passed pipelines

3. If no pipeline is running, launch next subtask in sequence:
   - Order: S2 → S3 → S4 → S5 → S6 (strict sequential, each depends on prior)
   - Find first `status: open` subtask in sequence
   - Launch: `python3 scripts/launch_pipeline.py {slug} --desc "..." --type builder-first --kickoff`
   - Update task status to `in_pipeline`

4. Skip silently if nothing to do

**Anti-patterns:**
- Do NOT launch anything except setup-vectorbt-nautilus-pipeline-s{2..6}
- Do NOT run more than 1 pipeline at a time
- Do NOT auto-kick Phase 2 on passed pipelines

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

## ~~Task 7: Memory Maintenance~~ (REMOVED 2026-03-25)
> **Removed:** Memory consolidation retired. Extraction now only creates lessons and decisions (no memory entries). Lessons/decisions link directly to chat transcripts — no roll-up needed.

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
