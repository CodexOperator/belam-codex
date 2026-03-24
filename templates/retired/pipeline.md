---
primitive: pipeline
name: Implementation Pipeline
description: >
  Generic 3-phase implementation pipeline for any notebook version.
  Phase 1: Autonomous build (architect → critic → builder).
  Phase 2: Human-in-the-loop (Shael feedback → revision → rebuild).
  Phase 3: Iterative research (gated on phase 2 completion, scored proposals).
  Create one instance per notebook version: pipelines/{version}.md
fields:
  status:
    type: string
    required: true
    default: phase1_design
    enum: [phase1_design, phase1_critique, phase1_revision, phase1_build, phase1_code_review, phase1_complete, experiment_running, experiment_complete, phase2_feedback, phase2_revision, phase2_rebuild, phase2_code_review, phase2_complete, phase3_proposed, phase3_approved, phase3_build, phase3_code_review, phase3_complete, archived]
  priority:
    type: string
    enum: [critical, high, medium, low]
  version:
    type: string
    required: true
    description: "Notebook version key (v1, v2, v3, v4, ...)"
  spec_file:
    type: string
  output_notebook:
    type: string
  agents:
    type: string[]
    description: "Agent IDs involved in this pipeline"
  tags:
    type: string[]
  project:
    type: string
    description: "Parent project primitive"
  started:
    type: date
  phase1_completed:
    type: date
  phase2_completed:
    type: date
  phase3_iterations:
    type: object[]
    description: "Array of phase 3 iteration records: [{id, hypothesis, justification, proposed_by, proposed_at, status, result_summary}]"
  phase3_gate:
    type: string
    default: phase2_complete
    description: "Phase 3 iterations only unlock after this status is reached"
  artifacts:
    type: object
    description: "Paths to pipeline artifacts (design, review, notebook)"
  patch_notes:
    type: object[]
    description: "Chronological log of post-build patches applied to the notebook. Each entry: {date, author, summary, commits}. Patches are always applied to the main notebook directly."
cli:
  dashboard: "R pipelines"
  detail: "R pipeline <version>"
  watch: "R pipeline <version> --watch [sec]"
  update: "R pipeline update <version> complete|start|block|show ..."
  launch: "R pipeline launch <version> --desc '...'"
  analyze: "R analyze <version>"
  shortcut: "R pl / R p <ver>"
---

# Implementation Pipeline: {version}

## Description
_{What this notebook version explores}_

## Notebook Convention

**All phases live in a single notebook** (`crypto_{version}_predictor.ipynb`). Each pipeline phase is a top-level section, with subsections for that phase's experiments, results, and analysis. Shared infrastructure (data loading, encodings, model classes, baselines) appears once at the top.

### Progress Bars — NO INTERACTIVE/DYNAMIC PROGRESS BARS

**Never use `tqdm`, `tqdm.auto`, `tqdm.notebook`, or any library that uses carriage returns (`\r`) or ANSI escape codes for progress display.** These produce garbled output in committed notebook cells and break GitHub's notebook renderer.

Instead:
- **Preferred:** Simple `print()` statements at milestones (e.g., `print(f"Model {i+1}/{total} complete — {name} — acc={acc:.2f}%")`)
- **Acceptable:** Static ASCII progress (e.g., `print(f"[{'█' * done}{'░' * remaining}] {pct:.0f}%")`) — one line per update, no `\r`
- **Never:** `tqdm(...)`, `from tqdm.auto import tqdm`, `tqdm.notebook`, or `end='\r'` print tricks

### GPU & Training — Engineering Guidelines

These are hard-won findings. Agents MUST follow them.

**Precision:** Use fp32 throughout. Do NOT use `torch.cuda.amp.autocast` or `GradScaler`.
- `BCELoss` and `BCEWithLogitsLoss` are unsafe under fp16 autocast (NaN/Inf from log of near-zero values)
- These SNN models are tiny (<100MB VRAM) — fp16 saves nothing meaningful
- Config: `'mixed_precision': False` always

**Parallelization:** Use `concurrent.futures.ThreadPoolExecutor` + CUDA streams to run multiple experiments simultaneously.
- Each experiment gets its own `torch.cuda.Stream()` via thread-local storage
- Auto-detect worker count from GPU type: T4: 12, V100: 12, L4: 14, A100: 20, H100: 24 (for tiny <1MB models — scale down for larger architectures)
- Override with `n_parallel=` argument to `run_all_experiments()`
- `n_parallel=1` for sequential/debug mode
- DataLoaders: `pin_memory=True`, `num_workers=2`, `persistent_workers=True` on GPU; `num_workers=0` on CPU

**Batch size:** Default 2048 for tiny SNN models. Larger batches fill GPU compute and reduce kernel launch overhead. Scale down if models grow beyond ~10MB.

**Data prefetching:** Call `prefetch_to_gpu(data_dict)` before experiments to move the full dataset to GPU once. Eliminates redundant per-batch CPU→GPU copies across all folds and experiments.

**GPU memory cleanup:** Define `gpu_cleanup(verbose=False)` — calls `gc.collect()` + `torch.cuda.empty_cache()`. Run after each fold (del model first), between groups, between phases, and before returning results. Prevents monotonic VRAM growth.

**PyTorch API note:** GPU memory is `torch.cuda.get_device_properties(0).total_memory` (not `total_mem`).

### Patch Notes

Patches are applied directly to the main notebook — not as separate files. Log all post-build patches here with date, author, summary, and commit hash.

| Date | Author | Summary | Commit |
|------|--------|---------|--------|

```
# Section 0: Setup & Imports
# Section 1: Data Pipeline (shared)
# Section 2: Encodings (shared)
# Section 3: Shared Model Infrastructure
# Section 4: Baselines (shared)
# ═══════════════════════════════════════
# Section N: PHASE 1 — {phase 1 label}
#   ## N.1 Experiment Matrix
#   ## N.2 Experiments by group
#   ## N.3 Results Table
#   ## N.4 Analysis
# ═══════════════════════════════════════
# Section N+1: PHASE 2 — {phase 2 label}
#   ## ...same subsection pattern...
# ═══════════════════════════════════════
# Section N+2: PHASE 3 ITERATION {id} — {hypothesis}
#   ## ...
# ═══════════════════════════════════════
# Final Section: Cross-Phase Deep Analysis
```

This enables side-by-side comparison across phases and keeps all research for a version in one place.

## Agent Coordination Protocol

**Filesystem-first:** All data exchange between agents happens via shared files, never through message payloads.

| Action | Method | Example |
|--------|--------|---------|
| Share design/review/fix | Write file to `research/pipeline_builds/` | `v4_critic_phase2_blocks.md` |
| Complete/block a stage | `python3 scripts/pipeline_orchestrate.py {v} complete/block {stage} --agent {role} --notes "..."` | Handles EVERYTHING |
| Update Shael / group | Automatic (orchestrator sends Telegram notification) | — |

### Pipeline Orchestrator — Mandatory Usage

**Every stage transition MUST go through `pipeline_orchestrate.py`** (ONE command replaces the old 3-step dance):

```bash
# Complete a stage:
python3 scripts/pipeline_orchestrate.py {version} complete {stage} --agent {role} --notes "summary"

# Block a stage:
python3 scripts/pipeline_orchestrate.py {version} block {stage} --agent {role} --notes "BLOCK reason" --artifact review_file.md

# Start a stage:
python3 scripts/pipeline_orchestrate.py {version} start {stage} --agent {role}
```

The orchestrator automatically:
1. Updates `{version}_state.json` (stages + `pending_action`)
2. Appends to the pipeline markdown stage history table
3. Bumps frontmatter status on transitions
4. Sends Telegram group notification
5. Wakes the next agent with full context (files to read, what to do)
6. Verifies the agent picked up the handoff (retries if needed)
7. Logs a memory entry for the completing agent

**DO NOT manually call `sessions_send`, `pipeline_update.py`, or post to the group chat for ANY reason.** All notifications are script-driven. Do not burn tokens on chat messages.

**Context model:** The orchestrator wakes agents with a fresh session and a rich context message listing all files to read. All meaningful state lives in the filesystem — agents don't need conversation history to pick up work.

### Stage Flow

```
Architect designs   → [orchestrate complete] → auto-wakes Critic        (session: fresh)
Critic reviews      → [orchestrate complete] → auto-wakes Builder       (session: fresh)
                    → [orchestrate block]    → auto-wakes Architect     (session: fresh)
Builder builds      → [orchestrate complete] → Builder verifies         (session: continue)
Builder verifies    → [orchestrate complete] → auto-wakes Critic        (session: fresh)
Critic code-reviews → [orchestrate complete] → auto-wakes Architect     (session: fresh)
                    → [orchestrate block]    → auto-wakes Builder       (session: fresh)
Phase 1 complete    → [autorun] → local_experiment_running (process stage)
Experiments done    → [self-reports] → local_experiment_complete → Phase 2
```

**Session modes:** Cross-agent transitions use `fresh` (reset session). Same-agent sequential stages (builder_implementation → builder_verification) use `continue` (keep session). Defined in `STAGE_TRANSITIONS` in `scripts/pipeline_update.py`.

Same pattern for Phase 2 and Phase 3. The orchestrator knows all transitions.
Experiment stage is a **process stage** — run_experiment.py self-reports, no agent handoff needed.

## ⚠️ MANDATORY GATE: Analysis Pipeline Must Complete First

**Before launching a new implementation pipeline version, the ANALYSIS pipeline for the previous version must have completed BOTH Phase 1 AND Phase 2.**

The interference pattern between autonomous Phase 1 analysis and Shael's Phase 2 directed analysis often yields surprising insights — experiments that look like failures may contain hidden signal. Premature version jumps skip this critical synthesis step.

**Gate:** Previous version's analysis pipeline must reach `analysis_phase2_complete` before this implementation pipeline can begin Phase 1.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|

## Local Experiment Execution
_Status: Auto-triggered on Phase 1 completion_

Experiments run locally on the VPS via `run_experiment.py`. The pipeline auto-transitions:
`phase1_complete` → `experiment_running` → `experiment_complete` → Phase 2

- **Auto-triggered** by `pipeline_autorun.py` when Phase 1 completes
- **Self-healing** — builder agent is invoked to fix runtime errors
- **Manual trigger:** `R run {version}`
- **Results:** `notebooks/local_results/{version}/`

### Experiment History
| Run | Date | Duration | Experiments | Errors | Notes |
|-----|------|----------|-------------|--------|-------|

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on experiment completion_

### Feedback
_(Shael's feedback goes here when experiments are complete and reviewed)_

## Phase 3: Iterative Research (Autonomous or Human-Triggered)
_Status: LOCKED — requires Phase 2 completion before activation_

**Gate condition:** `phase2_complete` must be set before any Phase 3 iteration can proceed.

### Phase 3 Iteration Chain Protocol

Main pipeline and analysis pipeline Phase 3 iterations are **interleaved** in a strict chain:

```
Main Phase 3 iter 01 → Analysis Phase 3 iter 01a, 01b, 01c...
  (all analysis iters complete, none pending) →
Main Phase 3 iter 02 → Analysis Phase 3 iter 02a, 02b...
  (all clear) →
Main Phase 3 iter 03 → ...
```

**Rules:**
1. Every analysis Phase 3 iteration MUST be preceded by a corresponding main pipeline Phase 3 iteration (can't analyze what wasn't built)
2. Multiple analysis iterations allowed per single main iteration (deep dives, follow-ups)
3. Next main iteration ONLY when ALL analysis iterations for current one are complete AND none pending
4. All Phase 3 iterations append sections to the existing notebook — never create new files

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
- **Spec:** `snn_applied_finance/specs/{version}_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/{version}_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/{version}_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/{version}_state.json`
- **Notebook:** `snn_applied_finance/notebooks/crypto_{version}_predictor.ipynb`
