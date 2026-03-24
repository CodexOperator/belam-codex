---
primitive: pipeline
status: phase1_build
priority: high
type: infrastructure
version: lm-v3-platform-and-system-namespace
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-24
---

# Implementation Pipeline: LM-V3-PLATFORM-AND-SYSTEM-NAMESPACE

## Description
LM V3: platform and system namespaces for OpenClaw configuration

## Type
Infrastructure pipeline — no notebook, no experiment. Deliverables are code, hooks, plugins, and config files.
At phase1_complete, this pipeline is ready for human review and archival (no experiment/analysis phases).

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-24 | belam-main | Pipeline instance created |
| architect_design | 2026-03-24 | architect | Design v1: 4 new LM sub-namespaces (oc.*, sys.*, e2.*, r.*) in single new file codex_lm_platform.py (~310L). 7 deliverables across 4 files. D1: oc.* (9 OpenClaw platform commands — auto-exec, not render). D2: sys.* (11 system tools — curated shell wrappers). D3: e2.* (5 scaffolded writes — script, cron, hook, skill, pipeline). D4: r.* (3 formatted read views — health, cost, recent). D5: dispatch router for dotted prefixes. D6: namespace folding in LM to manage budget (~2KB). D7: registration into existing renderer. 5 tests. 4 open questions for critic. |
| critic_design_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 2 HIGH FLAGs, 2 MED FLAGs, 1 LOW FLAG. FLAG-1 HIGH: codex_dispatch.py doesn't exist — D5 routing must go through codex_engine.py's existing dispatch chain (main parse loop ~line 5100-5214). Early prefix intercept for oc.*/sys.*/r.* before coord resolution. FLAG-2 HIGH: sys.* lambdas build shell strings with unsanitized args — use shlex.quote() and subprocess.run(list) where possible. Not security (agents have exec) but correctness (metacharacters produce confusing errors). FLAG-3 MED: e2.* prefix collides with existing e2 create mode — parser sees 'e2' as mode 2 before dotted handler can intercept. Use different prefix or add early intercept. FLAG-4 MED: no timeout handling (TimeoutExpired uncaught). FLAG-5 LOW: r.recent depends on git but agent workspaces aren't git repos. Review at: pipeline_builds/lm-v3-platform-and-system-namespace_critic_design_review.md |

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
- **Spec:** `snn_applied_finance/specs/lm-v3-platform-and-system-namespace_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/lm-v3-platform-and-system-namespace_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/lm-v3-platform-and-system-namespace_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/lm-v3-platform-and-system-namespace_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_lm-v3-platform-and-system-namespace.ipynb`
