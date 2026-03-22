---
primitive: pipeline
status: phase1_complete
priority: medium
version: codex-engine-v3
spec_file: machinelearning/snn_applied_finance/specs/codex-engine-v3_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_codex-engine-v3.ipynb
agents: [architect, critic, builder]
tags: [engine, codex, mcp, v3]
project: multi-agent-infrastructure
started: 2026-03-22
---

# Implementation Pipeline: CODEX-ENGINE-V3

## Description
Engine V3: MCP-native codex server, live mode-switch, reactive .codex materialization, multi-pane rendering

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_codex-engine-v3.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-22 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-22 | belam-main | Launching Phase 1 — final item in queue |
| architect_design | 2026-03-22 | architect | Design complete: 4 modules (MCP server, live mode-switch, reactive materialization, multi-pane rendering). 3 new files + ~80 lines in codex_engine.py. No changes to codex_codec.py or codex_ram.py. |
| critic_design_review | 2026-03-22 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 med, 2 low), 3 suggestions. All API references verified against codebase (4272L codex_engine.py, codec APIs, RenderTracker, --boot markers, _parse_e0_args). FLAG-1 MED: async handlers with sync internals — recommend sync. FLAG-2 MED: materialize_affected() race — recommend append-only. FLAG-3 LOW: state/ dir creation. FLAG-4 LOW: priority sort fallback. Clean design, minimal core engine changes (~80L), correct separation into 3 new files. Builder can proceed. |
| critic_design_review | 2026-03-22 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 med, 2 low). All APIs verified. FLAG-1 MED: drop async for MCP handlers. FLAG-2 MED: append-only materialization. FLAG-3 LOW: state/ dir. FLAG-4 LOW: priority sort fallback. |
| critic_design_review | 2026-03-22 | critic | APPROVED: 0 BLOCKs, 5 FLAGs (2 MED, 3 LOW). Design is clean, well-scoped, implementable. All task spec acceptance criteria covered. |
| critic_design_review | 2026-03-22 | critic | APPROVED 0 BLOCKs 4 FLAGs |
| critic_design_review | 2026-03-22 | critic | APPROVED: 0 BLOCKs, 5 FLAGs (2 MED, 3 LOW) |
| critic_design_review | 2026-03-22 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 med, 2 low). All APIs verified against codebase. Review at: pipeline_builds/codex-engine-v3_critic_design_review.md |
| builder_implementation | 2026-03-22 | builder | In progress |
| builder_implementation | 2026-03-22 | builder | In progress |
| builder_implementation | 2026-03-22 | builder | V3 implementation complete: 3 new files (codex_mcp_server.py 486L, codex_materialize.py 351L, codex_panes.py 333L). All 5 Critic FLAGs addressed. codex_engine.py changes were 0 lines — V2 had already stubbed all integration points (sort mode, e0x dispatch, --shuffle, --boot delegation, materialize_affected hooks). 52/52 tests pass. MCP server: stdio JSON-RPC, 5 tools, codex:// URI scheme. Materializer: hash-based diffing, boot injection, incremental updates. Panes: dense/json/pretty tmux rendering. |
| builder_implementation | 2026-03-22 | builder | V3 implementation complete: 4 modules (MCP server 486L, materializer 351L, panes 333L, engine +179L). 3 new files + CODEX.codex + state/materialize_hashes.json. All 5 Critic FLAGs addressed: FLAG-1 SINGLE_OPS dispatch, FLAG-2 sync MCP, FLAG-3 sort mode persistence, FLAG-4 batch frontmatter reads, FLAG-5 materialize_affected insertion points. Commit b893ddd2. |
| critic_code_review | 2026-03-22 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 MED, 2 LOW). All 5 design FLAGs resolved. MCP server, materializer, panes, engine mods all clean. No regressions. |
| phase1_complete | 2026-03-22 | architect | Phase 1 COMPLETE. Critic code review APPROVED 0 BLOCKs, 3 FLAGs (1 MED, 2 LOW). All 5 design FLAGs resolved. V3 delivers: MCP server (486L, stdio JSON-RPC, 5 tools, codex:// URIs), materializer (351L, hash-based diffing, boot injection), panes (333L, dense/json/pretty tmux rendering), engine mods (+179L). Clean implementation, no regressions, 52/52 tests pass. |

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
- **Spec:** `snn_applied_finance/specs/codex-engine-v3_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/codex-engine-v3_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/codex-engine-v3_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/codex-engine-v3_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_codex-engine-v3.ipynb`
