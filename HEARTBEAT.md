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

## Task 1: Git Commits (Both Repos)

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

## Task 2: Telegram Summary to Shael

Send Shael a brief Telegram message summarizing heartbeat activity. Include:
- Which tasks were launched into pipelines (if any)
- Which pipelines finished — include test results (passed/failed, test count)
- Which pipelines are still running
- Any errors or issues found
- Skip this task if nothing changed since last heartbeat (no launches, no completions, no errors)

## Task 3: Agent Conversation Export

1. `python3 scripts/export_agent_conversations.py --since 2`
2. Skip silently if no new conversations

---

## Completed Tasks (Archive)

### ~~Task: Monitor SNN Standard Model Experiments~~
✅ **COMPLETED 2026-03-12 23:58 UTC** — All 26 experiments finished (0 failures). Report synthesis complete.
