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
    enum: [phase1_design, phase1_critique, phase1_revision, phase1_build, phase1_code_review, phase1_complete, phase2_feedback, phase2_revision, phase2_rebuild, phase2_code_review, phase2_complete, phase3_proposed, phase3_approved, phase3_build, phase3_code_review, phase3_complete, archived]
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
---

# Implementation Pipeline: {version}

## Description
_{What this notebook version explores}_

## Notebook Convention

**All phases live in a single notebook** (`snn_crypto_predictor_{version}.ipynb`). Each pipeline phase is a top-level section, with subsections for that phase's experiments, results, and analysis. Shared infrastructure (data loading, encodings, model classes, baselines) appears once at the top.

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

**Filesystem-first:** All data exchange between agents happens via shared files, never through `sessions_send` message payloads.

| Action | Method | Example |
|--------|--------|---------|
| Share design/review/fix | Write file to `research/pipeline_builds/` | `v4_critic_phase2_blocks.md` |
| Track stage transitions | `python3 scripts/pipeline_update.py {v} complete {stage} "{notes}" {agent}` | Auto-updates state JSON, markdown, pending_action |
| Block a stage (Critic) | `python3 scripts/pipeline_update.py {v} block {stage} "{notes}" {agent} --artifact {file}` | Sets pending_action to fix step |
| Notify another agent | `sessions_send` with `timeoutSeconds: 0` | "Review ready at `pipeline_builds/v4_critic_review.md`" |
| Update Shael / group | `message` tool to group chat | "Phase 1 build complete, 111 cells" |

**Never** use `sessions_send` with a timeout > 0 (it will timeout on heavy agent runs). Never put critical data only in a `sessions_send` payload — the target may not receive it. Write the file first, ping second.

### Pipeline Update Script — Mandatory Usage

**Every stage transition MUST go through `pipeline_update.py`**, which:
1. Updates `{version}_state.json` (stages + `pending_action`)
2. Appends to the pipeline markdown stage history table
3. Prints which agent to ping next and what message to send

The script output tells you exactly who to ping. **Always follow its instructions:**
- Run the `complete` or `block` command
- Read the ping instruction it prints
- Execute the `sessions_send` with `timeoutSeconds: 0` to the indicated agent
- Post a status update to the group chat

### Stage Flow & Ping Points

```
Architect designs → [complete] → ping Critic "review ready"
Critic reviews    → [complete] → ping Builder "approved, build it"
                  → [block]    → ping Architect "blocks, fix instructions at X"
Builder builds    → [complete] → ping Critic "implementation done, review"
Critic code-reviews → [complete] → ping Architect "passed, next phase"
                    → [block]    → ping Builder "blocks, fix instructions at X"
```

Same pattern repeats for Phase 2 and Phase 3. The `pipeline_update.py` script handles all transitions automatically — agents just need to run it and follow the printed ping instruction.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Feedback
_(Shael's feedback goes here when provided)_

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
- **Spec:** `snn_applied_finance/specs/{version}_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/{version}_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/{version}_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/{version}_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_{version}.ipynb`
