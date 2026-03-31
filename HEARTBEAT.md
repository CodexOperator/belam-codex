# HEARTBEAT.md — Context-Aware Orchestrator

## Orchestrator Reference

**Before executing tasks below, read `templates/heartbeat.md`** for the full decision framework, script reference, gate rules, and anti-patterns. That file is your HOW — this file is your WHAT.

---

## Task 1: SNN Deep Analysis Pipeline Queue

**Run one pipeline at a time, sequentially.** Check which is next, kick it if idle, leave it alone if running.

### Pipeline Queue (in order)

| # | Pipeline | Status |
|---|----------|--------|
| 1 | `snn-deep-analysis-foundational-v1-v2` | ✅ p1_complete |
| 2 | `snn-deep-analysis-advanced-v3-v4` | ✅ p1_complete |
| 3 | `snn-deep-analysis-bioinspired-specialized` | ✅ p1_complete |
| 4 | `snn-deep-analysis-standard-leaky` | ✅ p1_complete |
| 5 | `snn-deep-analysis-standard-synaptic-alpha` | ✅ p1_complete |

**All Phase 1 pipelines complete!** Queue now awaiting Phase 2 human gates or new pipeline definitions.

### Decision Logic

1. Check current pipeline status: `python3 scripts/pipeline_dashboard.py <current-pipeline> 2>&1 | grep -E "p[0-9]_"`
2. **If stage is `p1_builder_implement` with no agent running** → kick with auto_wiggum:
   ```bash
   python3 scripts/auto_wiggum.py --agent builder --timeout 900 --pipeline <ver> --stage p1_builder_implement --restart-on-exit --task-file /tmp/heartbeat_builder_task.txt
   ```
   Write the task file first with pipeline-specific instructions (read the pipeline's Builder Instructions section).
3. **If stage is `p1_builder_bugfix`** → same as above but with bugfix task (run scripts, fix errors)
4. **If stage is `p1_critic_review`** → kick critic:
   ```bash
   python3 scripts/auto_wiggum.py --agent critic --timeout 600 --pipeline <ver> --stage p1_critic_review --restart-on-exit --task "Review pipeline <ver>. Read pipelines/<ver>.md and the output in the analysis directory. Check scripts run, PNGs generated, REPORT.md quality. Run: python3 scripts/pipeline_orchestrate.py <ver> complete p1_critic_review --agent critic --notes 'review summary' --learnings 'findings'"
   ```
5. **If at `p1_complete` (human gate)** → mark current pipeline status as ✅ in this table, move to next
6. **If at `p2_*` stages** → kick appropriate agent (architect for design, builder for implement/bugfix, critic for review)
7. **If a Wiggum process is already running for this pipeline** → do nothing, let it finish
8. **Only kick the NEXT pipeline after the current one reaches its human gate**

### Anti-Patterns
- ❌ Do NOT poll pipeline status repeatedly — one check per heartbeat
- ❌ Do NOT read output files to "check progress" — causes gateway load
- ❌ Do NOT run multiple pipelines concurrently
- ❌ Do NOT restart a builder that's already running (check `/tmp/wiggum_*.log` timestamps)

### How to Check If Agent Is Running
```bash
ps aux | grep -E "auto_wiggum|wiggum" | grep -v grep | head -3
cat /tmp/wiggum_<pipeline-slug>.log 2>/dev/null | tail -3
```
If Wiggum is sleeping (steer timer), the agent is active. Leave it.

## Task 2: Git Commits (Both Repos)

**Lesson:** `lessons/always-back-up-workspace-to-github.md` — if it's not pushed, it doesn't exist.

1. **Workspace (belam-codex):**
   - `git status --short` (from workspace root)
   - If uncommitted changes: `git add -A && git commit -m "Auto-commit: workspace updates [$(date -u +'%Y-%m-%d %H:%M UTC')]" && git push origin`
2. **Research (machinelearning):**
   - `cd machinelearning && git status --short`
   - If uncommitted changes: `git add -A && git commit -m "Auto-commit: research updates [$(date -u +'%Y-%m-%d %H:%M UTC')]" && git push origin`
3. Skip silently if both clean

## Task 3: Telegram Summary to Shael

Send Shael a brief Telegram message summarizing heartbeat activity. Include:
- Which pipeline is currently running and its stage
- Which pipelines completed since last heartbeat
- Any errors or stuck agents
- Skip this task if nothing changed since last heartbeat

## Task 4: Agent Conversation Export

1. `python3 scripts/export_agent_conversations.py --since 2`
2. Skip silently if no new conversations

---

## Completed Tasks (Archive)

### ~~Task: Monitor SNN Standard Model Experiments~~
✅ **COMPLETED 2026-03-12 23:58 UTC** — All 26 experiments finished (0 failures). Report synthesis complete.
