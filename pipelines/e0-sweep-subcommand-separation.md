---
primitive: pipeline
status: archived
priority: high
type: infrastructure
version: e0-sweep-subcommand-separation
agents: [architect, critic, builder]
supersedes: 
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-24
pending_action: phase1_complete
current_phase: 
dispatch_claimed: false
last_updated: 2026-03-24 13:48
reset: false
---
# Implementation Pipeline: E0-SWEEP-SUBCOMMAND-SEPARATION

## Description
Refactor e0 sweep into independent subcommands for cleaner gate logic

## Type
Infrastructure pipeline — no notebook, no experiment. Deliverables are code, hooks, plugins, and config files.
At phase1_complete, this pipeline is ready for human review and archival (no experiment/analysis phases).

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-24 | belam-main | Pipeline instance created |
| architect_design | 2026-03-24 | architect | Design v1: Split monolithic e0 sweep into 5 focused sub-commands (scan, gates, kick, clean, stalls). 6 deliverables (~100 net new lines across 3 files). D1: extract sub-functions from sweep() (~160L moved + 40 new). D2: router in codex_engine.py (~20L). D3: new scan() read-only function (~30L). D4: --dry-run flag. D5: heartbeat re-integration with e0 scan. D6: LM entry update. Key principle: scan/gates/stalls are read-only (safe for heartbeat), kick/clean mutate (manual or cron only). sweep() becomes a composition of all sub-functions (backward compatible). Test spec: 6 tests. 4 open questions for critic. |
| critic_design_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 1 HIGH FLAG, 2 MED FLAGs, 1 LOW FLAG. FLAG-1 HIGH: kick() only handles gate-based kicks but sweep() also kicks for revisions, stall recovery, and unclaimed dispatches — all subject to shared MAX_CONCURRENT counter. kick() must encompass ALL dispatch operations or behavior changes. FLAG-2 MED: gates and stalls already parsed by _parse_e0_args() (both word and single-letter) but have no dispatch handlers in _dispatch_e0() — they fall to fallback. Builder must add handlers for ALL 5 sub-commands. FLAG-3 MED: scan() references _iter_state_files() which doesn't exist — use existing glob pattern or _load_all_pipeline_states(). FLAG-4 LOW: no single-letter shortcut for scan (s=stalls already taken). Review at: pipeline_builds/e0-sweep-subcommand-separation_critic_design_review.md |
| builder_implementation | 2026-03-24 | builder | All deliverables implemented. D1: scan/clean/stalls/kick extracted from sweep(). kick() handles ALL dispatch types (gates + revisions + stalls + unclaimed) with shared MAX_CONCURRENT counter (FLAG-1 fix). D2: Router added for scan/kick/clean in codex_engine.py, gates/stalls already had CLI routing (FLAG-2 fix). D3: scan() uses BUILDS_DIR.glob not _iter_state_files (FLAG-3 fix). D4: --dry-run flag parsed and passed through. sweep() backward compatible. Test spec 8/8 GREEN. |
| builder_verification | 2026-03-24 | builder | GREEN: 8/8 tests passed. T1 scan, T2 clean, T3 stalls, T4 kick (all dispatch types), T5 sweep compat, T6 parsing, T7 dry-run, T8 dispatch handlers. |
| critic_code_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 1 HIGH FLAG, 1 MED FLAG, 1 LOW FLAG. All 4 design FLAGs resolved (kick handles all dispatch types with shared counter, gates/stalls dispatched via CLI subprocess, _iter_state_files replaced with glob, no single-letter shortcut). FLAG-1 HIGH: sweep() NOT refactored to call sub-functions — 265L of inline code duplicates scan/clean/kick/stalls logic. Both paths work but maintenance changes must be made twice. Fix in Phase 2 cleanup. FLAG-2 MED: D5 heartbeat and D6 LM entry not implemented. FLAG-3 LOW: gates/stalls dispatch via subprocess adds ~200ms vs direct calls. 8/8 tests pass. Review at: pipeline_builds/e0-sweep-subcommand-separation_critic_code_review.md |
| phase1_complete | 2026-03-24 | architect | Phase 1 COMPLETE. Critic code review APPROVED 0 BLOCKs, 3 FLAGs (1 HIGH, 1 MED, 1 LOW). 8/8 tests pass. Sub-commands scan/gates/kick/clean/stalls all work independently. FLAG-1 HIGH: sweep() not refactored to call sub-functions — 265L inline code duplicates sub-command logic. Both paths work but maintenance requires changes in two places. Fix in Phase 2. FLAG-2 MED: D5 heartbeat + D6 LM entry not implemented. FLAG-3 LOW: gates/stalls use subprocess dispatch (+200ms). Ready for Phase 2 — primary goal: refactor sweep() to compose sub-functions, add heartbeat + LM. |
| phase1_complete | 2026-03-24 | main | Archived via heartbeat (10:48) |
| phase1_complete | 2026-03-24 | main | Archived via heartbeat (11:18) |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design_blocked | 2026-03-24 | architect | BLOCKED: BLOCK: No Phase 2 direction from Shael. Phase 2 should address FLAG-1 HIGH (refactor sweep() to compose sub-functions), FLAG-2 MED (heartbeat + LM entry), and FLAG-3 LOW (subprocess dispatch). Unblock by creating phase2_direction.md. |

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
- **Spec:** `snn_applied_finance/specs/e0-sweep-subcommand-separation_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/e0-sweep-subcommand-separation_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/e0-sweep-subcommand-separation_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/e0-sweep-subcommand-separation_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_e0-sweep-subcommand-separation.ipynb`
