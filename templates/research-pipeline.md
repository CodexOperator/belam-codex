# Research Pipeline Template

## Flow

```
Phase 1: Architect (design) → Critic (design review) → Builder (implement) → Builder (verify) → Critic (code review) → [AUTO GATE → Phase 2]
Phase 2: System (experiment run) → System (experiment complete) → Architect (analysis) → Critic (analysis review) → Builder (analysis scripts) → Critic (analysis code review) → System (report build) → [HUMAN GATE]
Phase 3: Architect (design) → Critic (design review) → Builder (implement) → Builder (verify) → Critic (code review) → [HUMAN GATE]
Phase 4: Architect (design) → Critic (review) → Builder (implement) → Critic (code review) → [HUMAN GATE]
```

## When to Use
- SNN notebook research pipelines (systematic benchmarking)
- Multi-phase research with local experiments and analysis
- Full architect → critic → builder lifecycle with human gates between phases

## Stage Definitions

### Phase 1 — Design & Build

#### `p1_architect_design`
- Receives: pipeline spec from `pipelines/{v}.md`
- Produces: notebook architecture design at `pipeline_builds/{v}_architect_design.md`
- Handoff: design doc → critic for review

#### `p1_critic_design_review`
- Receives: architect design doc
- Produces: review (approve or request revisions)
- Handoff: approved design → builder | revision request → architect

#### `p1_builder_implement`
- Receives: approved design doc
- Produces: working notebook, committed to repo
- Handoff: implementation → builder verification

#### `p1_builder_verify`
- Receives: implementation + verification script
- Produces: verification results from `pipeline_verify.py`
- Handoff: verified notebook → critic code review

#### `p1_critic_code_review`
- Receives: verified implementation + design spec
- Produces: code review (pass/fail, issues)
- Handoff: pass → p1_complete → auto-triggers Phase 2

### Phase 2 — Local Experiment & Analysis

#### `p2_system_experiment_run` / `p2_system_experiment_complete`
- System-managed experiment execution
- Results at `notebooks/local_results/{v}/`

#### `p2_architect_analysis`
- Receives: experiment results
- Produces: preliminary analysis report + script recommendations

#### `p2_critic_analysis_review` / `p2_builder_analysis_scripts` / `p2_critic_analysis_code_review`
- Full architect → critic → builder → critic loop for analysis scripts
- Ends at `p2_system_report_build` → `p2_complete` (human gate)

### Phase 3 — Refinement

Same architect → critic → builder → verify → critic flow as Phase 1.
Design docs at `pipeline_builds/{v}_phase2_architect_design.md`.
Ends at `p3_complete` (human gate).

### Phase 4 — Iteration

Simplified architect → critic → builder → critic flow.
Ends at `p4_complete` (human gate).

## Subtask Convention
Research pipelines use version-based naming:
```
{neuron-model}_v{N}   — main notebook version
{neuron-model}_v{N}_analysis — analysis notebook
```

## Stage Transitions
<!-- machine-readable: parsed by template_parser.py -->
<!-- Phase-based format: phases define stage sequences, gates, and block routing -->
```yaml
first_agent: architect
type: research

phases:
  1:
    stages:
      - { role: architect, action: design, session: fresh }
      - { role: critic, action: design_review, session: fresh }
      - { role: builder, action: implement, session: fresh }
      - { role: builder, action: verify, session: continue }
      - { role: critic, action: code_review, session: fresh }
    gate: auto

  2:
    stages:
      - { role: system, action: experiment_run, session: fresh }
      - { role: system, action: experiment_complete, session: fresh }
      - { role: architect, action: analysis, session: fresh }
      - { role: critic, action: analysis_review, session: fresh }
      - { role: builder, action: analysis_scripts, session: fresh }
      - { role: critic, action: analysis_code_review, session: fresh }
      - { role: system, action: report_build, session: fresh }
    gate: human

  3:
    stages:
      - { role: architect, action: design, session: fresh }
      - { role: critic, action: design_review, session: fresh }
      - { role: builder, action: implement, session: fresh }
      - { role: builder, action: verify, session: continue }
      - { role: critic, action: code_review, session: fresh }
    gate: human

  4:
    stages:
      - { role: architect, action: design, session: fresh }
      - { role: critic, action: review, session: fresh }
      - { role: builder, action: implement, session: fresh }
      - { role: critic, action: code_review, session: fresh }
    gate: human

block_routing:
  critic:
    design_review: architect
    code_review: builder
    analysis_review: architect
    analysis_code_review: builder
    review: architect

complete_task_agent: architect
```

## Human Gates

`p2_complete`, `p3_complete`, and `p4_complete` are **human gates**. Phase 1 (`p1_complete`) uses an auto gate that transitions directly to Phase 2.

### Actions at a Human Gate

| Action | Command | Effect |
|--------|---------|--------|
| Kick next phase | `pipeline_orchestrate.py <ver> kickoff --phase N` | Starts Phase N flow |
| Complete task | `pipeline_orchestrate.py <ver> complete-task --agent architect --notes "reason"` | Archives pipeline + marks task done |
| Manual transition | `pipeline_orchestrate.py <ver> complete <gate_stage> --agent <role> --notes "..."` | Advance to specific next stage |
