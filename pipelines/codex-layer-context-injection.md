---
primitive: pipeline
status: phase1_build
priority: critical
version: codex-layer-context-injection
spec_file: pipeline_builds/codex-layer-context-injection_spec.md
output_dir: pipeline_builds/
agents: [architect, critic, builder]
tags: [codex-layer, context-optimization, infrastructure]
project: multi-agent-infrastructure
started: 2026-03-22
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
