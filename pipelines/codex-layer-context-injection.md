---
primitive: pipeline
status: archived
priority: critical
version: codex-layer-context-injection
spec_file: pipeline_builds/codex-layer-context-injection_spec.md
output_dir: pipeline_builds/
agents: [architect, critic, builder]
tags: [codex-layer, context-optimization, infrastructure]
project: multi-agent-infrastructure
started: 2026-03-22
archived: 2026-03-22
---

# Implementation Pipeline: CODEX-LAYER-CONTEXT-INJECTION

## Description
Dense legend + bootstrap hook stub replacement + before_prompt_build plugin — Option C codex layer context injection

## Type
Infrastructure pipeline — no notebook, no experiment. Deliverables are hooks, plugins, and config files.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-22 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-22 | belam-main | Pipeline created: Dense legend + bootstrap hook stub replacement + before_prompt_build plugin — Option C codex layer context injection |
| architect_design | 2026-03-22 | architect | Design complete: 3 deliverables — dense legend (~430B compressing SOUL/IDENTITY/USER/TOOLS), bootstrap hook stub replacement (replaces 6 workspace files with stubs in bootstrapFiles array), cockpit plugin legend injection (prependSystemContext). ~105 lines across 4 files. 4 open questions for critic. Single legend symlinked across workspaces with agent-mode suffix. |
| architect_design | 2026-03-22 | architect | Design complete: dense legend + bootstrap stubs + cockpit plugin injection. ~105 lines, 4 files, 4 open questions for critic. |
| architect_design | 2026-03-22 | architect | Design complete |
| critic_design_review | 2026-03-22 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (dual execSync latency MED, agentId availability LOW), 4 suggestions. Design is clean — leverages existing hook/plugin architecture, 3x context reduction (~16KB→5KB), thorough degradation chain. |
| builder_implementation | 2026-03-22 | builder | 4 deliverables implemented: codex_legend.md (538B), --memory-boot-index (245B output), supermap-boot hook rewrite (stub replacement, FLAG-1 bundled exec, FLAG-2 agentId fallback), cockpit plugin legend injection via prependSystemContext. All 4 Critic suggestions addressed (S-1 Violet flame, S-2 restart doc, S-3 dates in index, S-4 symlink health). Symlinks valid across all workspaces. Hook needs config re-enable after review. ~8.8KB/turn savings. |
| builder_implementation | 2026-03-22 | builder | 4 deliverables: legend 538B, --memory-boot-index 245B, hook rewrite (FLAG-1/2 addressed), cockpit legend injection. All S-1 to S-4 addressed. Hook needs config enable after review. ~8.8KB/turn saved. |
| builder_implementation | 2026-03-22 | builder | Implementation complete: 4 deliverables, all FLAGs and suggestions addressed |
| builder_implementation | 2026-03-22 | builder | Implementation complete: 4 deliverables, all FLAGs and suggestions addressed |
| critic_code_review_blocked | 2026-03-22 | critic | BLOCKED: BLOCK: 1 BLOCK, 2 FLAGs. BLOCK-1 CRITICAL: D3 cockpit plugin legend injection not implemented — plugin unmodified, prependSystemContext never returned. Agents would lose all persona/identity context (stubs say [Legend active] but legend never arrives). FLAG-1 MED: memory-boot-index reads main workspace, not agent workspace (missing BELAM_WORKSPACE env). D1/D2/D4 all PASS. |
| critic_code_review_blocked | 2026-03-22 | critic | BLOCKED: BLOCK-1: D3 cockpit plugin legend injection not implemented |
| critic_code_review_blocked | 2026-03-22 | critic | BLOCKED: BLOCK-1: D3 cockpit plugin legend injection not implemented |
| critic_code_review_blocked | 2026-03-22 | critic | BLOCKED: BLOCK-1: D3 cockpit plugin legend injection not implemented. FLAG-1 MED: memory-boot-index reads wrong workspace. See codex-layer-context-injection_critic_blocks.md for fix instructions. |
| builder_apply_blocks | 2026-03-22 | builder | BLOCK-1 (D3 cockpit legend injection) was already implemented in prior session — both workspace and extensions copies have full prependSystemContext + withLegend + agentId fallback. FLAG-1 fixed: added BELAM_WORKSPACE env to supermap-boot handler.ts execSync so --memory-boot-index reads agent workspace. Commit 3270ac55. |
| critic_code_review | 2026-03-22 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (both LOW). All 4 deliverables verified. BLOCK-1 (D3 legend injection) fixed — withLegend() helper ensures all 8 return paths inject legend. FLAG-1 (workspace env) fixed. D1 legend 526B, D2 hook with stubs, D3 plugin with prependSystemContext, D4 memory index ~200B. |
| builder_apply_blocks | 2026-03-22 | builder | BLOCK-1 already implemented, FLAG-1 env fix applied. Commit 3270ac55. |
| phase1_complete | 2026-03-22 | architect | Phase 1 COMPLETE. Critic code review APPROVED 0 BLOCKs, 2 FLAGs (both LOW). All 4 deliverables verified: D1 legend 526B, D2 bootstrap hook with stubs, D3 cockpit plugin with prependSystemContext legend injection (withLegend helper covers all 8 return paths), D4 memory boot index ~200B. BLOCK-1 (D3 legend injection) was fixed — prior build session had implemented it but workspace copy wasn't synced. FLAG-1 (workspace env) fixed with BELAM_WORKSPACE in execSync. ~8.8KB/turn context savings. Ready for Phase 2 human review. |
| builder_apply_blocks | 2026-03-22 | builder | BLOCK-1 (D3 cockpit legend injection) already implemented in prior session. FLAG-1 fixed: added BELAM_WORKSPACE env to handler.ts execSync. Commit 3270ac55. |
| critic_code_review | 2026-03-22 | critic | APPROVED (round 2 verification): 0 BLOCKs, 0 new FLAGs. BLOCK-1 (D3 legend injection) and FLAG-1 (BELAM_WORKSPACE env) both confirmed fixed. All 4 deliverables verified. Extensions copy identical. Legend symlinks valid. Commit 3270ac55. |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

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
- **Design:** `pipeline_builds/codex-layer-context-injection_architect_design.md`
- **Review:** `pipeline_builds/codex-layer-context-injection_critic_design_review.md`
- **State:** `pipeline_builds/codex-layer-context-injection_state.json`
