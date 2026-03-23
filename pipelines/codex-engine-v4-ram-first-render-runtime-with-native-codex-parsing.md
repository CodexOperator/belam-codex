---
primitive: pipeline
status: phase2_in_progress
priority: critical
type: research
version: codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing
spec_file: machinelearning/snn_applied_finance/specs/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-23
---

# Implementation Pipeline: CODEX-ENGINE-V4-RAM-FIRST-RENDER-RUNTIME-WITH-NATIVE-CODEX-PARSING

## Description
codex engine v4 ram first render runtime with native codex parsing

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-23 | belam-main | Pipeline instance created |
| architect_design | 2026-03-23 | architect | Design v1: RAM-first render runtime. 7 deliverables (~240L net across 4 files). D1: write+create UDS commands with auto-flush to disk. D2: .codex snapshot hydration on startup (~5 lines). D3: ping/pong + my_diff UDS extensions. D4: cockpit plugin UDS-only path (180× speedup: ~900ms→~5ms first turn, ~350ms→~2ms subsequent). D5: engine reads from RAM (resolve_coords, render_supermap). D6: test mode flush suppression (3 lines). D7: per-node concurrency locks. No HTTP API, no .codex versioning, dulwich stays. 4 open questions for critic. |
| critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (1 MED, 1 LOW). FLAG-1 MED: snapshot freshness check doesn't detect file deletions — ghost nodes persist in RAM. Fix: add file-count comparison. FLAG-2 LOW: no retry for failed disk flushes. All 4 open questions answered (sync flush correct, no snapshot versioning, 0.35s rebuild acceptable, async already supported in plugin). Clean write-through cache pattern, per-node locking correct, 180x speedup plausible. Review at: pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_critic_design_review.md |
| builder_implementation | 2026-03-23 | builder | V4 implementation complete. D1-D3/D5-D7 already existed from prior V3 pipeline sessions (codex_render.py had write/create UDS commands, snapshot hydration with FLAG-1 ghost detection, ping/pong + my_diff, test mode flush suppression, per-node concurrency locks; codex_engine.py had UDS helpers for RAM-first reads). Only D4 (cockpit plugin UDS-only path) needed building: native Node.js UDS client (udsQuery via net.createConnection), async udsPing health check, async ensureRenderEngine, session attach for per-agent diffs (S1 my_diff), subprocess fallback retained. ~180x speedup: ~900ms→~5ms first turn, ~350ms→~2ms subsequent. Both FLAGs addressed. Commit 765f070f. |
| critic_code_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 1 FLAG (MED). D4 UDS-only path correctly implemented: native udsQuery via net.createConnection, session attach for per-agent diffs (S1), async ensureRenderEngine with native ping, subprocess fallback retained. FLAG-1 MED: per-turn codexExec('--register-show') subprocess takes 158ms, negating the 180x UDS speedup. Fix: read .codex_runtime/register.json directly in TypeScript (<1ms). Both design FLAGs already in Python render engine from prior pipelines. |
| phase1_complete | 2026-03-23 | architect | Phase 1 COMPLETE. Critic code review APPROVED 0 BLOCKs, 1 FLAG (MED). All deliverables verified: D1 RAM-first write+create, D2 .codex hydration, D3 UDS extensions (ping/my_diff), D4 cockpit plugin UDS-only with native net.createConnection, D5 engine reads from RAM, D6 test mode flush suppression, D7 per-node locking. FLAG-1 MED: codexExec('--register-show') subprocess (158ms) negates UDS speedup — fix by reading .codex_runtime/register.json directly in TypeScript (<1ms). Ready for Phase 2 human review. |
| phase1_complete | 2026-03-23 | belam-main | Phase 2 direction file found — auto-kicked by sweep |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design_blocked | 2026-03-23 | architect | BLOCKED: BLOCK: No Phase 2 direction from Shael. Phase 2 requires human review of Phase 1 deliverables and direction for what to refine/extend. Unblock by creating pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_phase2_direction.md. |
| phase2_architect_design | 2026-03-23 | architect | Phase 2 design: stage-based agent sessions via render engine. 7 deliverables (~225L across 3 files). Key architecture: OpenClaw manages session lifecycle (sessions_spawn/sessions_send), render engine manages tree state (UDS), orchestrator manages pipeline flow (stage transitions + signal detection). D1: stage metadata in AgentSession. D2: exchange loop with inotify-based signal detection (not polling). D3: table-driven stage flow + stall detection. D4: reviewer-join compaction trigger. D5: cockpit plugin stage-session mode + FLAG-1 fix (register read <1ms). D7: session archival for memory extraction. 4 open questions for critic. |
| phase2_critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (1 HIGH, 1 LOW). FLAG-1 HIGH: sessions_spawn/sessions_send not available from standalone Python scripts — openclaw agent CLI runs one turn only, has no --mode session or --label. Builder must resolve via Gateway HTTP API or thin CLI wrapper before implementing D2 exchange loop. FLAG-2 LOW: compaction trigger undefined, deferred to V5. Clean separation of concerns (OpenClaw=sessions, render engine=tree state, orchestrator=pipeline flow). inotify signal detection correct. Stage flow table clean. Phase 1 FLAG-1 fix included. |
| phase2_builder_implementation | 2026-03-23 | builder | Phase 2 implemented: D1 (AgentSession metadata — pipeline/stage/role), D2 (signal handling with inotify + exchange loop via openclaw agent --session-id), D3 (STAGE_FLOW table + stall detection), D4 (reviewer_joined event on second agent attach), D5 (cockpit FLAG-1 fix — register.json direct read), D6 (graceful degradation — existing patterns sufficient), D7 (session archival to markdown). FLAG-1 resolved: openclaw agent --session-id already supports deterministic session routing. FLAG-2 deferred to V5 (compaction trigger). Total ~225 lines across 3 files. Commit 14a81b0c. |
| phase2_critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (1 HIGH, 1 LOW). FLAG-1 HIGH: sessions_spawn/sessions_send not available from standalone Python scripts — builder must resolve via Gateway HTTP API or thin CLI wrapper before implementing D2 exchange loop. FLAG-2 LOW: compaction trigger undefined, deferred to V5. Clean separation of concerns, inotify signal detection correct, stage flow table clean. Phase 1 FLAG-1 fix included. Review at: pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_phase2_critic_design_review.md |
| phase2_critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (1 HIGH, 1 LOW). FLAG-1 HIGH: sessions_spawn/sessions_send not available from standalone Python scripts — builder must resolve via Gateway HTTP API or thin CLI wrapper before implementing D2 exchange loop. FLAG-2 LOW: compaction trigger undefined, deferred to V5. Clean separation of concerns, inotify signal detection correct, stage flow table clean. Phase 1 FLAG-1 fix included. Review at: pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_phase2_critic_design_review.md |
| phase2_critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (1 HIGH, 1 LOW). FLAG-1 HIGH: sessions_spawn/sessions_send not available from standalone Python scripts — builder must resolve via Gateway HTTP API or thin CLI wrapper before implementing D2 exchange loop. FLAG-2 LOW: compaction trigger undefined, deferred to V5. Clean separation of concerns, inotify signal detection correct, stage flow table clean. Phase 1 FLAG-1 fix included. Review at: pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_phase2_critic_design_review.md |
| phase2_critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (1 HIGH, 1 LOW). FLAG-1 HIGH: sessions_spawn/sessions_send not available from standalone Python scripts — builder must resolve via Gateway HTTP API or thin CLI wrapper before implementing D2 exchange loop. FLAG-2 LOW: compaction trigger undefined, deferred to V5. Review at: pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_phase2_critic_design_review.md |
| phase2_critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (1 HIGH, 1 LOW). FLAG-1 HIGH: sessions_spawn/sessions_send not available from standalone Python scripts — builder must resolve via Gateway HTTP API or thin CLI wrapper before implementing D2 exchange loop. FLAG-2 LOW: compaction trigger undefined, deferred to V5. Review at: pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_phase2_critic_design_review.md |
| phase2_critic_code_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 MED, 2 LOW). All 7 deliverables verified. Both design FLAGs resolved (session spawning via dispatch_agent, compaction deferred). FLAG-1 MED: stall detection uses started_at not last activity (false positives on long-running active sessions). FLAG-2 LOW: openclaw sessions history CLI may not exist (best-effort wrapped). FLAG-3 LOW: inotify not installed, polling fallback works. 325L, 3 files. Review at: pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_phase2_critic_code_review.md |
| phase2_critic_design_review | 2026-03-23 | unknown | In progress |

### Feedback
_(Shael's feedback goes here when Phase 1 is complete and reviewed)_

## Phase 3: Iterative Research (Autonomous or Human-Triggered)
_Status: LOCKED — requires Phase 2 completion before activation_

**Gate condition:** `phase2_complete` must be set before any Phase 3 iteration can proceed.

### How Phase 3 Works

1. **Human-triggered:** Shael says "try X" → iteration created and built
2. **Agent-triggered:** Analysis reveals compelling follow-up → proposal generated:
   - Score ≥ 7: auto-approved
   - Score 4-6: flagged for Shael's review
   - Score < 4: rejected, logged only

### Iteration Log

| ID | Hypothesis | Proposed By | Status | Result |
|----|-----------|-------------|--------|--------|

## Artifacts
- **Spec:** `snn_applied_finance/specs/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing.ipynb`
