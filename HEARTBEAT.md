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

## ~~Task 5: VectorBT/Nautilus Subtask Queue (S2–S6)~~ (COMPLETED 2026-03-25)

> **Completed:** All 6 subtasks done (S1–S6), all critic approved.
> - S1 (environment setup): 22/22 tests GREEN
> - S2 (data pipeline): APPROVED
> - S3 (strategy adapter): APPROVED  
> - S4 (walk-forward validation): Phase 2 DSR fix → APPROVED
> - S5 (transaction costs): APPROVED
> - S6 (statistical validation): 54/54 tests GREEN, Phase 2 bugfix → APPROVED
> 
> VectorBT/Nautilus infrastructure complete. Ready for S7 (experiments) when needed.

## ~~Task 5.5: Render Engine Health Check~~ (REMOVED 2026-03-25)
> **Removed:** Render daemon retired. Supermap is now rendered on-demand by `scripts/render_supermap.py` (called directly by cockpit plugin V10). No daemon to health-check.

## Task 5: Microcap Swing Subtask Queue (S1–S12)

**Scope:** Sequential pipeline queue for `microcap-swing-signal-extraction` subtasks.
**Template:** builder-first (builder → bugfix → critic → human gate)
**MAX_CONCURRENT:** 1

### Subtask Order & Dependencies

| # | Subtask | Depends On | Pipeline Slug |
|---|---------|------------|---------------|
| S1 | Data Pipeline (CEX + DEX + F&G) | — | microcap-swing-s1-data-pipeline-v4 |
| S2 | Feature Engineering | S1 | microcap-swing-s2-feature-engineering |
| S3A | Label Construction & LightGBM — 15-min | S2 | microcap-swing-s3a-lightgbm-15min |
| S3B | Label Construction & LightGBM — 1-hour | S2 | microcap-swing-s3b-lightgbm-1hour |
| S4 | BTC Control Analysis | S3A, S3B | microcap-swing-s4-btc-control |
| S5 | Confidence Calibration | S3A, S3B | microcap-swing-s5-calibration |
| S6 | Risk Management Overlay | S5 | microcap-swing-s6-risk-management |
| S7 | LSTM Secondary Model | S3A, S3B | microcap-swing-s7-lstm |
| S8 | Ensemble & Meta-Learning | S5, S7 | microcap-swing-s8-ensemble |
| S9 | Cross-Token Momentum | S4 | microcap-swing-s9-cross-token |
| S10 | Regime Detection Pre-Filter | S4, S5 | microcap-swing-s10-regime-detection |
| S11 | Experiment Synthesis Report | S8, S9, S10 | microcap-swing-s11-synthesis |
| S12 | Paper Trading Infrastructure | S8, S6 | microcap-swing-s12-paper-trading |

### Execution Logic (Fully Autonomous)

1. Check current pipeline status:
   - `python3 scripts/codex_engine.py e0 l` — look at active pipelines with `microcap-swing` prefix
   - If a microcap-swing pipeline is actively running (builder/critic dispatched), **skip — wait for it**

2. If current pipeline reached `p1_complete` (critic approved Phase 1):
   - **AUTO-ADVANCE:** Archive pipeline, mark subtask `done`, launch next eligible
   - No human gate — critic approval = done (the usual outcome)

3. If current pipeline reached `p1_review` and critic BLOCKED:
   - **AUTO-KICK Phase 2:** Read critic's block notes from `pipeline_builds/{version}_critic_code_review.md`
   - Write Phase 2 direction based on critic feedback
   - Kick Phase 2: `python3 scripts/pipeline_orchestrate.py {version} kickoff --phase 2`
   - Wait for Phase 2 to complete (will reach `p2_complete`)

4. If current pipeline reached `p2_complete`:
   - Archive pipeline, mark subtask `done`, launch next eligible
   - If Phase 2 critic also blocks → mark subtask `blocked`, alert Shael, stop queue

5. If no microcap-swing pipeline is running, find next eligible subtask:
   - Read `tasks/microcap-swing-signal-extraction.md` subtask list
   - Find first subtask with `status: open` whose `depends_on` are all `status: done`
   - **Critical:** Each subtask's builder must reference prior subtask outputs. Include in desc:
     - Which files/modules from prior subtasks to import/extend
     - Path to prior subtask's code: `machinelearning/microcap_swing/src/`
     - Path to prior subtask's tests: `machinelearning/microcap_swing/tests/`
   - Launch:
     ```bash
     python3 scripts/launch_pipeline.py {slug} \
       --template builder-first \
       --desc "{subtask desc + reference to prior outputs}" \
       --priority critical \
       --tags quant,crypto,microcap \
       --project microcap-swing-signal-extraction \
       --kickoff --wiggum
     ```
   - Update subtask status to `in_pipeline`

6. After archiving + launching next: git commit both repos

7. Skip silently if nothing to do

### Builder Context Chain
Each subtask builds on prior work. When launching S(N+1), include in the pipeline description:
- "Builds on S(N) output at `machinelearning/microcap_swing/src/{module}.py`"
- "Import from prior modules — do not reimplement data loading/features/etc."
- "Run existing tests to verify no regressions: `pytest machinelearning/microcap_swing/tests/`"

### Auto-Advance Rules
- Critic PASS at Phase 1 → archive + next subtask (no human gate)
- Critic BLOCK at Phase 1 → auto-kick Phase 2 with critic's feedback as direction
- Critic PASS at Phase 2 → archive + next subtask
- Critic BLOCK at Phase 2 → **STOP** — alert Shael, something needs manual attention
- Pipeline marked `complete` by orchestrator → same as critic PASS, archive + next

### Anti-patterns
- Do NOT launch if a microcap-swing pipeline is already running
- Do NOT launch S3A and S3B concurrently (sequential only, MAX_CONCURRENT=1)
- Do NOT let Phase 2 blocks auto-retry — that's the escalation point for Shael

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
- Microcap swing queue progress: current subtask, next eligible, how many done
- Any errors or issues found
- Skip this task if nothing changed since last heartbeat (no launches, no completions, no errors)

## Task 9: Agent Conversation Export

1. `python3 scripts/export_agent_conversations.py --since 2`
2. Skip silently if no new conversations

---

## Completed Tasks (Archive)

### ~~Task: Monitor SNN Standard Model Experiments~~
✅ **COMPLETED 2026-03-12 23:58 UTC** — All 26 experiments finished (0 failures). Report synthesis complete.
