---
primitive: pipeline
status: archived
priority: high
type: infrastructure
version: codex-engine-v2-modes
spec_file: machinelearning/snn_applied_finance/specs/codex-engine-v2-modes_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_codex-engine-v2-modes.ipynb
agents: [architect, critic, builder]
tags: [engine, codex, v2]
project: multi-agent-infrastructure
started: 2026-03-21
archived: 2026-03-23
archive_reason: superseded by codex-engine-v3-legendary-map
pending_action: phase1_complete
current_phase: 
dispatch_claimed: false
last_updated: 2026-03-21 21:03
reset: false
---
# Implementation Pipeline: CODEX-ENGINE-V2-MODES

## Description
Dense-alphanumeric-parser-e0-e3-modes-extend-mode-retire-legacy-flags-dulwich-RAM

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_codex-engine-v2-modes.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-21 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-21 | belam-main | Pipeline created: Dense-alphanumeric-parser-e0-e3-modes-extend-mode-retire-legacy-flags-dulwich-RAM |
| pipeline_created | 2026-03-21 | belam-main | Pipeline created. Kicking off Phase 1. |
| pipeline_created | 2026-03-21 | belam-main | Kicking off Phase 1 architect design |
| architect_design | 2026-03-21 | architect | Design complete: codex_engine.py V2 modes gap analysis shows ~75% built. 7 gaps identified: (1) legacy flag retirement with strict mode env var, (2) dulwich RAM state tree as new codex_ram.py module (~250L) with MemoryRepo + graceful degradation, (3) e3 persistence via modes/extensions.json, (4) codex_codec as RAM serialization boundary, (5-7) minor: e3 template/integrate, help text update. New module codex_ram.py is the main deliverable. 4 open questions for critic: dulwich vs pure-dict, e3 persistence scope, RAM auto-activation, codec migration scope. |
| architect_design | 2026-03-21 | architect | Design complete: V2 dense parser hardening, enum field indexing, e0 op numbering, dot-connector, e3 template/integrate, pure-Python RAM layer, codec integration — 8-step builder spec with 15-test checklist |
| architect_design | 2026-03-21 | architect | Design complete |
| architect_design | 2026-03-21 | architect | Design complete: V2 modes 75% built, 7 gaps, dulwich RAM state as new codex_ram.py module |
| architect_design | 2026-03-21 | architect | Design complete: V2 dense parser hardening, enum field indexing, e0 op numbering, dot-connector, e3 template/integrate, pure-Python RAM layer, codec integration |
| architect_design | 2026-03-21 | architect | Design complete |
| architect_design | 2026-03-21 | architect | Design complete: V2 modes 75% built, 7 gaps identified, dulwich RAM state as new codex_ram.py module, e3 persistence via extensions.json, legacy flag retirement with strict mode |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 5 FLAGs (2 med, 3 low). All 9 acceptance criteria covered. Builder can proceed. Key FLAGs: spaced collapse regex over-match, dot-connector ambiguity with output format. |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 HIGH, 2 MED). FLAG-1 (HIGH): builder spec missing 3 d10 consequences — enum field indexing, e0 op numbering, dot-connector not in builder steps. FLAG-2 (MED): extensions.json should commit to git. FLAG-3 (MED): dulwich branch/merge/diff speculative, no consumers yet. Verified 75% complete claim accurate. Review at: pipeline_builds/codex-engine-v2-modes_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 medium, 2 low), 3 suggestions. Gap analysis verified against actual code — all claims accurate. FLAG-1 (MED): codex_codec API names wrong in builder spec (parse/serialize don't exist, actual API is from_codex/to_codex) — will cause immediate AttributeError. FLAG-2 (MED): ram_branch/ram_merge speculative editing over-scoped for V1, no consumer exists — defer to V1.1. FLAG-3 (LOW): ram_diff output format unspecified. FLAG-4 (LOW): extensions.json in modes/ mixes data with reference files. Open questions answered: Q1 dulwich justified, Q2 commit extensions.json, Q3 explicit opt-in via BELAM_RAM=1, Q4 keep dual parser paths. Review at: pipeline_builds/codex-engine-v2-modes_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 HIGH, 2 MED). Review at pipeline_builds/codex-engine-v2-modes_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 med, 2 low). FLAG-1 MED: codex_codec API names wrong. FLAG-2 MED: ram_branch/ram_merge defer to V1.1. Review at pipeline_builds/codex-engine-v2-modes_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (1 medium, 3 low). All claims verified against codebase. FLAG-1 (MED): Working tree vs MemoryRepo hybrid needs explicit design — dict for live reads, dulwich for committed snapshots. FLAG-2-4 (LOW): flush atomicity, import path, deprecation specificity. 4 open questions answered: dulwich justified, extensions.json git-tracked, RAM opt-in, dual parsers fine. 10/10 checklist. Review at: pipeline_builds/codex-engine-v2-modes_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED 0 BLOCKs 3 FLAGs |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 HIGH, 2 MED). FLAG-1 HIGH: builder spec missing d10 consequences (enum field indexing, e0 op numbering, dot-connector). FLAG-2 MED: extensions.json should commit to git. FLAG-3 MED: dulwich branch/merge/diff speculative. Review at: pipeline_builds/codex-engine-v2-modes_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (1 med, 3 low). All claims verified. FLAG-1 MED: dict working tree + dulwich snapshots. Review at: pipeline_builds/codex-engine-v2-modes_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 med, 2 low). codex_codec API names wrong, ram_branch/merge defer V1.1. Review at pipeline_builds/codex-engine-v2-modes_critic_design_review.md |
| builder_implementation | 2026-03-21 | builder | V2 implementation complete: 9-step dense grammar build — collapse parser, enum indexing, E0 numeric ops, dot-connector disambiguation, output format (.1=JSON), E3 template/integrate/run, RAM dirty-tracking layer, mode primitives updated. All 5 Critic FLAGs addressed. 399 lines changed across codex_engine.py + codex_ram.py. Committed as a5c9f2ce. |
| builder_implementation | 2026-03-21 | builder | V2 done: 9-step build, all 5 FLAGs addressed, 399 lines, commit a5c9f2ce |
| builder_implementation | 2026-03-21 | builder | V2 done |
| builder_implementation | 2026-03-21 | builder | V2 implementation complete: 9-step dense grammar. All 5 Critic FLAGs addressed. 399 lines changed. Commit a5c9f2ce. |
| critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 med, 2 low). All design FLAGs verified fixed (branch/merge overridden — implemented instead of deferred, acceptable). Parser hardening correct: spaced collapse requires digit, enum before validation, dot-connector .iN vs .N disambiguated. RAM state clean: dict working tree + dulwich snapshots, BELAM_RAM=1 opt-in, graceful degradation. Persistent extensions via modes/extensions.json. FLAG-1 MED: sys.path.insert repeated for codex_codec. FLAG-2 LOW: deprecation trailing space fragile. FLAG-3 LOW: branch _branches attr not in __init__. Review at: pipeline_builds/codex-engine-v2-modes_critic_code_review.md |
| phase1_complete | 2026-03-21 | architect | Phase 1 COMPLETE. Critic code review APPROVED 0 BLOCKs, 3 non-blocking FLAGs: (1) MED sys.path.insert repeated for codex_codec, (2) LOW deprecation trailing space fragile, (3) LOW branch _branches attr not in __init__. All design FLAGs from earlier review verified fixed — branch/merge was implemented rather than deferred, accepted. Builder delivered 9-step dense grammar: collapse parser hardened, enum indexing, E0 numeric ops, dot-connector disambiguation, E3 template/integrate/run, RAM dirty-tracking layer, mode primitives updated. 399 lines across codex_engine.py + codex_ram.py. Commit a5c9f2ce. Ready for Phase 2 human review. |
| critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (all LOW). All 5 design FLAGs verified fixed. 20/20 functional tests, 0 V1 regressions. Review at: pipeline_builds/codex-engine-v2-modes_critic_code_review.md |
| critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (all LOW). All 5 design FLAGs verified fixed. |
| critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (all LOW) |
| phase1_complete | 2026-03-21 | architect | Phase 1 COMPLETE (re-confirmed). Second Critic code review APPROVED 0 BLOCKs, 3 LOW FLAGs (sys.path.insert, deprecation trailing space, branch __init__). All 5 design FLAGs verified fixed. 20/20 functional tests, 0 V1 regressions. Builder delivered 9-step dense grammar: 399 lines across codex_engine.py + codex_ram.py. Commit a5c9f2ce. Ready for Phase 2 human review. |

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
- **Spec:** `snn_applied_finance/specs/codex-engine-v2-modes_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/codex-engine-v2-modes_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/codex-engine-v2-modes_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/codex-engine-v2-modes_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_codex-engine-v2-modes.ipynb`
