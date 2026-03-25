# Research Pipeline Template

## Flow

```
Phase 1: Architect (design) → Critic (design review) → Builder (implement) → Builder (verify) → Critic (code review) → phase1_complete → Local Experiment → Local Analysis → [local_analysis_complete — human gate]
Phase 1 Revisions: Architect (revise) → Critic (review) → Builder (implement) → Critic (code review) → [phase1_complete]
Local Experiment: system (run) → system (complete) → Architect (analysis) → Critic (review) → Builder (scripts) → Critic (code review) → system (report build) → [local_analysis_complete — human gate]
Phase 2: Architect (design) → Critic (design review) → Builder (implement) → Builder (verify) → Critic (code review) → [phase2_complete — human gate]
Phase 3: Architect (design) → Critic (review) → Builder (implement) → Critic (code review) → [phase3_complete — human gate]
Analysis Phase 1: Architect (design) → Critic (review) → Builder (implement) → Critic (code review) → [analysis_phase1_complete]
Analysis Phase 2: Architect (design) → Critic (review) → Builder (implement) → Critic (code review) → [analysis_phase2_complete]
```

## When to Use
- SNN notebook research pipelines (systematic benchmarking)
- Multi-phase research with local experiments and analysis
- Full architect → critic → builder lifecycle with human gates between phases

## Stage Definitions

### Phase 1 — Design & Build

#### `architect_design`
- Receives: pipeline spec from `pipelines/{v}.md`
- Produces: notebook architecture design at `pipeline_builds/{v}_architect_design.md`
- Handoff: design doc → critic for review

#### `critic_design_review`
- Receives: architect design doc
- Produces: review (approve or request revisions)
- Handoff: approved design → builder | revision request → architect

#### `builder_implementation`
- Receives: approved design doc
- Produces: working notebook, committed to repo
- Handoff: implementation → builder verification

#### `builder_verification`
- Receives: implementation + verification script
- Produces: verification results from `pipeline_verify.py`
- Handoff: verified notebook → critic code review

#### `critic_code_review`
- Receives: verified implementation + design spec
- Produces: code review (pass/fail, issues)
- Handoff: pass → phase1_complete → auto-triggers local experiment | blocks → builder

### Phase 1 Revisions (coordinator-triggered)

#### `phase1_revision_architect`
- Receives: revision request from coordinator
- Produces: revision design at `pipeline_builds/{v}_phase1_revision_architect.md`

#### `phase1_revision_critic_review` / `phase1_revision_builder` / `phase1_revision_code_review`
- Standard architect → critic → builder → critic loop
- Loops back to `phase1_complete` on completion

### Local Experiment & Analysis

#### `local_experiment_running` / `local_experiment_complete`
- System-managed experiment execution
- Results at `notebooks/local_results/{v}/`

#### `local_analysis_architect`
- Receives: experiment results
- Produces: preliminary analysis report + script recommendations

#### `local_analysis_critic_review` / `local_analysis_builder` / `local_analysis_code_review`
- Full architect → critic → builder → critic loop for analysis scripts
- Ends at `local_analysis_complete` (human gate — Shael approves via `R kickoff <ver> --phase2`)

### Phase 2

Same architect → critic → builder → verify → critic flow as Phase 1.
Design docs at `pipeline_builds/{v}_phase2_architect_design.md`.
Ends at `phase2_complete` (human gate).

### Phase 3

Simplified architect → critic → builder → critic flow.
Ends at `phase3_complete` (human gate).

### Analysis Pipeline — Phase 1 & Phase 2

Separate autonomous analysis pipeline with its own architect → critic → builder → critic loop.
Phase 2 analysis is Shael-directed with specific questions.

## Subtask Convention
Research pipelines use version-based naming:
```
{neuron-model}_v{N}   — main notebook version
{neuron-model}_v{N}_analysis — analysis notebook
```

## Stage Transitions
<!-- machine-readable: parsed by orchestration_engine.py -->
<!-- gate: human → stops auto-dispatch, waits for manual kick -->
```yaml
first_agent: architect
pipeline_fields:
  type: research
  stages: [architect_design, critic_design_review, builder_implementation, builder_verification, critic_code_review, phase1_complete, phase2_architect_design, phase2_critic_design_review, phase2_builder_implementation, phase2_builder_verification, phase2_critic_code_review, phase2_complete, phase3_architect_design, phase3_critic_review, phase3_builder_implementation, phase3_critic_code_review, phase3_complete]

transitions:
  # session: fresh = reset agent session (cross-agent or after gate)
  # session: continue = keep same session (same-agent sequential stages)

  # ── Kickoff ──────────────────────────────────────────────────────
  pipeline_created:                      [architect_design,                    architect, "New pipeline created. Design the notebook architecture per pipelines/{v}.md", session: fresh]

  # ── Phase 1 — Design → Build → Review ───────────────────────────
  architect_design:                      [critic_design_review,                critic,    "Design ready for review at pipeline_builds/{v}_architect_design.md", session: fresh]
  critic_design_review:                  [builder_implementation,              builder,   "Design approved. Build spec at pipeline_builds/{v}_architect_design.md", session: fresh]
  architect_design_revision:             [critic_design_review,                critic,    "Design revised, re-review at pipeline_builds/{v}_architect_design.md", session: fresh]
  builder_implementation:                [builder_verification,                builder,   "Implementation done. Run verification: python3 scripts/pipeline_verify.py {v}", session: continue]
  builder_verification:                  [critic_code_review,                  critic,    "Verification passed. Review the notebook.", session: fresh]
  critic_code_review:                    [phase1_complete,                     architect, "Phase 1 code review passed. Triggering local experiment.", session: fresh]
  phase1_complete:                       [local_experiment_running,            system,    "Phase 1 complete. Starting local experiment run.", session: fresh]
  # Phase 1 blocks
  builder_apply_blocks:                  [critic_code_review,                  critic,    "Blocks fixed. Re-review the notebook.", session: fresh]

  # ── Phase 1 Revisions (coordinator-triggered) ───────────────────
  phase1_revision_architect:             [phase1_revision_critic_review,       critic,    "Revision design ready at pipeline_builds/{v}_phase1_revision_architect.md", session: fresh]
  phase1_revision_critic_review:         [phase1_revision_builder,             builder,   "Revision design approved. Build per pipeline_builds/{v}_phase1_revision_architect.md", session: fresh]
  phase1_revision_builder:               [phase1_revision_code_review,         critic,    "Revision implementation done. Review the notebook.", session: fresh]
  phase1_revision_code_review:           [phase1_complete,                     architect, "Phase 1 revision code review passed. Back to phase1_complete.", session: fresh]
  # Phase 1 revision blocks
  phase1_revision_architect_fix:         [phase1_revision_critic_review,       critic,    "Revision design revised, re-review at pipeline_builds/{v}_phase1_revision_architect.md", session: fresh]
  phase1_revision_builder_fix:           [phase1_revision_code_review,         critic,    "Revision blocks fixed. Re-review the notebook.", session: fresh]

  # ── Local Experiment Execution ───────────────────────────────────
  local_experiment_running:              [local_experiment_complete,           system,    "Local experiment run completed. Results at notebooks/local_results/{v}/", session: fresh]
  local_experiment_complete:             [local_analysis_architect,            architect, "Experiments complete. Analyze results at notebooks/local_results/{v}/. Read the analysis MD and write a comprehensive preliminary report with any additional analysis scripts needed.", session: fresh]

  # ── Local Analysis (architect → critic → builder loop) ──────────
  local_analysis_architect:              [local_analysis_critic_review,        critic,    "Preliminary analysis report ready at notebooks/local_results/{v}/{v}_analysis_report.md. Review the analysis and script recommendations.", session: fresh]
  local_analysis_critic_review:          [local_analysis_builder,              builder,   "Analysis design approved. Implement additional scripts, run them, incorporate results into the report at notebooks/local_results/{v}/", session: fresh]
  local_analysis_architect_revision:     [local_analysis_critic_review,        critic,    "Analysis revised. Re-review at notebooks/local_results/{v}/{v}_analysis_report.md", session: fresh]
  local_analysis_builder:                [local_analysis_code_review,          critic,    "Analysis scripts implemented and run. Review the updated report and code at notebooks/local_results/{v}/", session: fresh]
  local_analysis_builder_fix:            [local_analysis_code_review,          critic,    "Analysis blocks fixed. Re-review at notebooks/local_results/{v}/", session: fresh]
  local_analysis_code_review:            [local_analysis_report_build,         system,    "Analysis code review passed. Building LaTeX report.", session: fresh]
  local_analysis_report_build:           [local_analysis_complete,             system,    "LaTeX report built. PDF at notebooks/local_results/{v}/{v}_report.pdf", gate: human, session: fresh]
  # Phase 2 entry (fires only on manual phase2 kickoff — gate: human prevents auto-dispatch)
  local_analysis_complete:               [phase2_architect_design,             architect, "Phase 2 approved. Design phase 2 per direction doc.", session: fresh]

  # ── Phase 2 — Design → Build → Review ───────────────────────────
  phase2_architect_design:               [phase2_critic_design_review,         critic,    "Phase 2 design ready at pipeline_builds/{v}_phase2_architect_design.md", session: fresh]
  phase2_critic_design_review:           [phase2_builder_implementation,       builder,   "Phase 2 design approved. Build spec at pipeline_builds/{v}_phase2_architect_design.md", session: fresh]
  phase2_architect_revision:             [phase2_critic_design_review,         critic,    "Phase 2 design revised, re-review at pipeline_builds/{v}_phase2_architect_design.md", session: fresh]
  phase2_builder_implementation:         [phase2_builder_verification,         builder,   "Phase 2 implementation done. Run verification: python3 scripts/pipeline_verify.py {v}", session: continue]
  phase2_builder_verification:           [phase2_critic_code_review,           critic,    "Phase 2 verification passed. Review the notebook.", session: fresh]
  builder_phase2_implemented:            [phase2_critic_code_review,           critic,    "Phase 2 implementation done. Review the notebook.", session: fresh]
  phase2_critic_code_review:             [phase2_complete,                     architect, "Phase 2 code review passed. Pipeline complete (or ready for Phase 3).", gate: human, session: fresh]
  # Phase 2 blocks
  builder_apply_phase2_blocks:           [phase2_critic_code_review,           critic,    "Phase 2 analysis blocks fixed. Re-review the notebook.", session: fresh]
  critic_block_fixes:                    [phase2_critic_code_review,           critic,    "Blocks fixed. Re-review the notebook.", session: fresh]

  # ── Phase 3 ─────────────────────────────────────────────────────
  phase3_architect_design:               [phase3_critic_review,                critic,    "Phase 3 iteration design ready for review.", session: fresh]
  phase3_critic_review:                  [phase3_builder_implementation,       builder,   "Phase 3 design approved. Build it.", session: fresh]
  phase3_builder_implementation:         [phase3_critic_code_review,           critic,    "Phase 3 implementation done. Review the notebook.", session: fresh]
  phase3_critic_code_review:             [phase3_complete,                     architect, "Phase 3 iteration complete.", gate: human, session: fresh]

  # ── Analysis Pipeline — Phase 1 (autonomous statistical analysis) ──
  analysis_architect_design:             [analysis_critic_review,              critic,    "Analysis design ready at pipeline_builds/{v}_architect_analysis_design.md"]
  analysis_critic_review:                [analysis_builder_implementation,     builder,   "Analysis design approved. Implement notebook per pipeline_builds/{v}_architect_analysis_design.md"]
  analysis_architect_design_revision:    [analysis_critic_review,              critic,    "Analysis design revised, re-review at pipeline_builds/{v}_architect_analysis_design.md"]
  analysis_builder_implementation:       [analysis_critic_code_review,         critic,    "Analysis notebook complete. Review implementation at notebooks/crypto_{v}_analysis.ipynb"]
  analysis_critic_code_review:           [analysis_phase1_complete,            architect, "Phase 1 analysis code review passed. Notify Shael — phase 1 complete, ready for directed questions."]
  # Analysis Phase 1 block fixes
  analysis_builder_apply_blocks:         [analysis_critic_code_review,         critic,    "Analysis blocks fixed. Re-review the notebook."]

  # ── Analysis Pipeline — Phase 2 (Shael-directed analysis) ──────
  analysis_phase2_architect:             [analysis_phase2_critic_review,       critic,    "Phase 2 analysis design ready at pipeline_builds/{v}_phase2_architect_design.md"]
  analysis_phase2_architect_design:      [analysis_phase2_critic_review,       critic,    "Phase 2 analysis design ready at pipeline_builds/{v}_phase2_architect_analysis_design.md"]
  analysis_phase2_critic_review:         [analysis_phase2_builder_implementation, builder, "Phase 2 analysis design approved. Extend notebook per pipeline_builds/{v}_phase2_architect_analysis_design.md"]
  analysis_phase2_architect_revision:    [analysis_phase2_critic_review,       critic,    "Phase 2 analysis design revised, re-review."]
  analysis_phase2_builder_implementation: [analysis_phase2_critic_code_review, critic,    "Phase 2 analysis notebook extended. Review additions."]
  analysis_phase2_critic_code_review:    [analysis_phase2_complete,            architect, "Phase 2 analysis code review passed. Pipeline complete."]
  # Analysis Phase 2 block fixes
  analysis_phase2_builder_apply_blocks:  [analysis_phase2_critic_code_review,  critic,    "Phase 2 analysis blocks fixed. Re-review the notebook."]

status_bumps:
  # ── Kickoff ──────────────────────────────────────────────────────
  architect_design:                          phase1_design

  # ── Builder Pipeline — Phase 1 ───────────────────────────────────
  critic_design_review:                      phase1_review
  builder_implementation:                    phase1_build
  critic_code_review:                        phase1_code_review
  phase1_complete:                           phase1_complete

  # Phase 1 revisions
  phase1_revision_critic_review:             phase1_revision
  phase1_revision_builder:                   phase1_revision
  phase1_revision_code_review:               phase1_revision

  # ── Local Experiment Execution ────────────────────────────────────
  local_experiment_running:                  experiment_running
  local_experiment_complete:                 experiment_complete

  # ── Local Analysis (post-experiment) ──────────────────────────────
  local_analysis_critic_review:              local_analysis_in_progress
  local_analysis_builder:                    local_analysis_in_progress
  local_analysis_code_review:                local_analysis_in_progress
  local_analysis_report_build:               local_analysis_report
  local_analysis_complete:                   local_analysis_complete

  # ── Builder Pipeline — Phase 2 ───────────────────────────────────
  phase2_critic_design_review:               phase2_review
  phase2_builder_implementation:             phase2_build
  phase2_critic_code_review:                 phase2_code_review
  phase2_complete:                           phase2_complete

  # ── Builder Pipeline — Phase 3 ───────────────────────────────────
  phase3_critic_review:                      phase3_active
  phase3_builder_implementation:             phase3_active
  phase3_critic_code_review:                 phase3_active
  phase3_complete:                           phase3_complete

  # ── Analysis Pipeline — Phase 1 ──────────────────────────────────
  analysis_critic_review:                    analysis_phase1_review
  analysis_builder_implementation:           analysis_phase1_build
  analysis_critic_code_review:               analysis_phase1_code_review
  analysis_phase1_complete:                  phase1_complete

  # ── Analysis Pipeline — Phase 2 ──────────────────────────────────
  analysis_phase2_critic_review:             phase2_in_progress
  analysis_phase2_builder_implementation:    phase2_in_progress
  analysis_phase2_critic_code_review:        phase2_in_progress
  analysis_phase2_complete:                  phase2_complete

start_status_bumps:
  # Local analysis starts
  local_analysis_architect:                  local_analysis_in_progress
  local_analysis_critic_review:              local_analysis_in_progress
  local_analysis_builder:                    local_analysis_in_progress
  local_analysis_code_review:                local_analysis_in_progress
  local_analysis_report_build:               local_analysis_report

  # Analysis Phase 2 starts
  analysis_phase2_architect:                 phase2_in_progress
  analysis_phase2_architect_design:          phase2_in_progress
  analysis_phase2_critic_review:             phase2_in_progress
  analysis_phase2_builder_implementation:    phase2_in_progress
  analysis_phase2_critic_code_review:        phase2_in_progress

  # Phase 1 revision starts
  phase1_revision_architect:                 phase1_revision
  phase1_revision_critic_review:             phase1_revision
  phase1_revision_builder:                   phase1_revision
  phase1_revision_code_review:               phase1_revision

  # Local experiment starts
  local_experiment_running:                  experiment_running

  # Builder Phase 2 starts
  phase2_architect_design:                   phase2_in_progress
  phase2_critic_design_review:               phase2_in_progress
  phase2_builder_implementation:             phase2_in_progress
  phase2_critic_code_review:                 phase2_in_progress

  # Phase 3 starts
  phase3_architect_design:                   phase3_active
  phase3_critic_review:                      phase3_active
  phase3_builder_implementation:             phase3_active
  phase3_critic_code_review:                 phase3_active
```
