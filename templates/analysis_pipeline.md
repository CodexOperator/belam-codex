---
primitive: analysis_pipeline
name: Analysis Pipeline
description: >
  2-phase analysis pipeline for existing SNN experiment results (pkl files).
  Phase 1: Autonomous analysis (architect designs → critic reviews → builder implements).
  Phase 2: Human-in-the-loop (Shael provides questions/direction → architect extends notebook).
  Both phases live in a SINGLE notebook — sections appended, never a new file.
  No new training — this pipeline loads pkl result files and extracts research insights.
fields:
  status:
    type: string
    required: true
    default: analysis_phase1_design
    enum:
      - analysis_phase1_design
      - analysis_phase1_critique
      - analysis_phase1_build
      - analysis_phase1_code_review
      - analysis_phase1_complete
      - analysis_phase2_design
      - analysis_phase2_critique
      - analysis_phase2_build
      - analysis_phase2_code_review
      - analysis_phase2_complete
      - analysis_phase3_proposed
      - analysis_phase3_design
      - analysis_phase3_critique
      - analysis_phase3_build
      - analysis_phase3_code_review
      - analysis_phase3_complete
      - archived
  priority:
    type: string
    enum: [critical, high, medium, low]
  version:
    type: string
    required: true
    description: "Analysis version key (e.g. v4-analysis)"
  source_version:
    type: string
    required: true
    description: "The experiment version whose pkl files are being analyzed (e.g. v4)"
  source_pkl_dir:
    type: string
    description: "Path to the directory containing pkl result files"
  output_notebook:
    type: string
    description: "Path to the analysis notebook output"
  agents:
    type: string[]
    description: "Agent IDs involved in this pipeline"
  tags:
    type: string[]
  project:
    type: string
  started:
    type: date
  phase1_completed:
    type: date
  phase2_completed:
    type: date
  artifacts:
    type: object
    description: "Paths to pipeline artifacts (design brief, review, notebook)"
cli:
  dashboard: "belam pipelines"
  detail: "belam pipeline <version>"
  watch: "belam pipeline <version> --watch [sec]"
  update: "belam pipeline update <version> complete|start|block|show ..."
  analyze: "belam analyze <source_version>"
  launch: "belam pipeline analyze <version>"
  shortcut: "belam pl / belam p <ver> / belam a <ver>"
---

# Analysis Pipeline: {version}

## Description
_{What experiment results are being analyzed, and the primary research questions}_

## Source Data
- **Source Version:** `{source_version}`
- **Pkl Files:** `{source_pkl_dir}`
- **Upload Method:** Individual pkl files OR single zip — notebook handles both

## Analysis Notebook Convention

**Both analysis phases live in a single notebook** (`crypto_{source_version}_analysis.ipynb`). Phase 1 sections are autonomous; Phase 2 sections are appended after Shael's direction. The notebook never splits into separate files.

### Notebook Structure

```
# Section 0: Setup & Colab Upload
  ## 0.1 Imports (pandas, numpy, scipy, matplotlib, seaborn, pickle, zipfile)
  ## 0.2 Colab Upload Cell (handles both zip and individual pkl files)
  ## 0.3 Data Loader (auto-detect zip vs individual, extract into results dict)

# ═══════════════════════════════════════════════════
# PHASE 1: Autonomous Statistical Analysis
#   Agents analyze data independently — no Shael input needed
# ═══════════════════════════════════════════════════

# Section 1: Data Inventory & Sanity Checks
  ## 1.1 Pkl File Inventory (experiment count, fields, groups)
  ## 1.2 Data Shape Validation (expected vs actual)
  ## 1.3 Missing Value / NaN Audit
  ## 1.4 Results Summary Table (all experiments, all metrics)

# Section 2: Statistical Analysis
  ## 2.1 Descriptive Statistics (mean, std, min, max per metric)
  ## 2.2 Distribution Analysis (histograms, KDE plots)
  ## 2.3 Hypothesis Tests (McNemar, Wilcoxon signed-rank, Bonferroni-corrected)
  ## 2.4 Correlation Analysis (metric cross-correlations)

# Section 3: Visualizations
  ## 3.1 Performance Heatmaps (experiment × metric)
  ## 3.2 Scale Analysis Plots (performance vs architecture scale)
  ## 3.3 Encoding Comparison Plots
  ## 3.4 Group-by-Group Bar Charts
  ## 3.5 Fold Variance Analysis (performance stability across walk-forward folds)

# Section 4: Pattern Discovery
  ## 4.1 Top-N Experiments (by each metric)
  ## 4.2 Bottom-N Experiments (failure mode analysis)
  ## 4.3 Interaction Effects (encoding × scale × output scheme)
  ## 4.4 Anomaly Detection (outlier experiments)

# Section 5: Phase 1 Research Summary
  ## 5.1 Key Findings (ranked by insight value)
  ## 5.2 Open Questions (flagged for Phase 2)
  ## 5.3 Recommendations for Future Experiments

# ═══════════════════════════════════════════════════
# PHASE 2: Directed Analysis (Shael's Questions)
#   Shael provides direction → Architect designs → Builder implements
#   Sections appended below — same notebook
# ═══════════════════════════════════════════════════

# Section 6+: [Shael-directed analysis sections — appended in Phase 2]
#   Each directed question becomes its own section with:
#   ## N.1 Question & Methodology
#   ## N.2 Analysis Implementation
#   ## N.3 Results & Interpretation
#   ## N.4 Implications for Future Experiments

# Final Section: Cross-Phase Synthesis
  ## Unified insight table
  ## Research trajectory recommendations
  ## Open experiments to run next
```

### Colab Upload Cell (MANDATORY — must be first executable cell)

```python
# ── Section 0.2: Upload pkl files ──────────────────────────────────────────────
# Upload EITHER: all pkl files individually, OR a single zip containing them all.
# This cell handles both cases automatically.

from google.colab import files
import pickle, zipfile, io, os

print("Upload pkl files now (individual OR single zip):")
uploaded = files.upload()

results = {}
pkl_files_found = []

for fname, fbytes in uploaded.items():
    if fname.endswith('.zip'):
        print(f"  📦 Detected zip: {fname} — extracting...")
        with zipfile.ZipFile(io.BytesIO(fbytes)) as zf:
            for zname in zf.namelist():
                if zname.endswith('.pkl'):
                    with zf.open(zname) as pf:
                        key = os.path.splitext(os.path.basename(zname))[0]
                        results[key] = pickle.load(pf)
                        pkl_files_found.append(zname)
                        print(f"    ✅ Loaded: {zname} → key='{key}'")
    elif fname.endswith('.pkl'):
        key = os.path.splitext(fname)[0]
        results[key] = pickle.load(io.BytesIO(fbytes))
        pkl_files_found.append(fname)
        print(f"  ✅ Loaded: {fname} → key='{key}'")

print(f"\n📊 Total pkl files loaded: {len(results)}")
print(f"   Keys: {list(results.keys())}")
```

### Visualization Standards

**Never use interactive/dynamic widgets** in analysis notebooks:
- No `ipywidgets`, no `plotly` interactive traces (static `.png`-compatible output only)
- Use `matplotlib` + `seaborn` throughout
- Always call `plt.tight_layout()` before `plt.show()`
- Set figure size explicitly: `fig, ax = plt.subplots(figsize=(12, 6))`
- Use `seaborn.set_theme(style='whitegrid')` at the top of Section 0

### Statistical Test Standards

- **McNemar test:** `scipy.stats.contingency.mcnemar` or manual via `scipy.stats.chi2`
- **Wilcoxon signed-rank:** `scipy.stats.wilcoxon`
- **Bonferroni correction:** `statsmodels.stats.multitest.multipletests` or manual (`α / n_tests`)
- Always state H0 explicitly before each test
- Report p-values AND effect sizes (Cohen's d or rank-biserial correlation)
- Pre-register primary metric and threshold before running tests

## Agent Coordination Protocol

**Filesystem-first:** All data exchange between agents happens via shared files, never through message payloads.

| Action | Method | Example |
|--------|--------|---------|
| Share design/review/fix | Write file to `research/pipeline_builds/` | `{version}_architect_analysis_design.md` |
| Complete/block a stage | `python3 scripts/pipeline_orchestrate.py {v} complete/block {stage} --agent {role} --notes "..."` | Handles EVERYTHING |
| Update Shael / group | Automatic (orchestrator sends Telegram notification) | — |

### Pipeline Orchestrator — Mandatory Usage

**Every stage transition MUST go through `pipeline_orchestrate.py`** (ONE command replaces the old 3-step dance):

```bash
# Complete a stage:
python3 scripts/pipeline_orchestrate.py {version} complete {stage} --agent {role} --notes "summary"

# Block a stage:
python3 scripts/pipeline_orchestrate.py {version} block {stage} --agent {role} --notes "BLOCK reason" --artifact review_file.md
```

The orchestrator automatically:
1. Updates pipeline state (JSON + markdown + frontmatter status bumps)
2. Sends Telegram group notification
3. Wakes the next agent with full context (files to read, what to do)
4. Verifies the agent picked up the handoff (retries if needed)
5. Logs a memory entry for the completing agent

**DO NOT manually call `sessions_send`, `pipeline_update.py`, or post to the group chat for stage transitions.** The orchestrator handles all of it.

### Stage Flow

```
Phase 1:
Architect designs analysis → [orchestrate complete] → auto-wakes Critic
Critic reviews methodology → [orchestrate complete] → auto-wakes Builder
                           → [orchestrate block]    → auto-wakes Architect
Builder implements notebook → [orchestrate complete] → auto-wakes Critic
Critic code-reviews         → [orchestrate complete] → auto-wakes next / pipeline complete
                            → [orchestrate block]    → auto-wakes Builder

Phase 2 (after Shael provides direction):
Same flow with analysis_phase2_ prefix stages.
```

## Phase 1: Autonomous Analysis
_Architect designs analysis methodology → Critic reviews statistical rigor → Builder implements_

### Architect Tasks (Phase 1)
1. Read `research/ANALYSIS_AGENT_ROLES.md` and skill at `~/.openclaw/workspace/skills/quant-workflow/SKILL.md`
2. Read the design brief at `research/pipeline_builds/{version}_design_brief.md`
3. Design the full analysis notebook structure:
   - Specify exactly which statistical tests to run and why
   - Define visualizations needed to answer the research questions
   - Identify expected patterns to look for
   - Write design to `research/pipeline_builds/{version}_architect_analysis_design.md`
4. Run: `python3 scripts/pipeline_orchestrate.py {version} complete analysis_architect_design --agent architect --notes "Design summary"`

### Critic Tasks (Phase 1 — Design Review)
1. Read `research/ANALYSIS_AGENT_ROLES.md` and skill at `~/.openclaw/workspace/skills/quant-workflow/SKILL.md`
2. Review architect's design at `research/pipeline_builds/{version}_architect_analysis_design.md`
3. Check for: statistical validity, methodology gaps, missing visualizations, appropriate corrections
4. If approved: `python3 scripts/pipeline_orchestrate.py {version} complete analysis_critic_review --agent critic --notes "Approved: ..."`
5. If blocked: write blocks to file, then: `python3 scripts/pipeline_orchestrate.py {version} block analysis_critic_review --agent critic --notes "BLOCK-1: ..." --artifact {version}_critic_analysis_blocks.md`

### Builder Tasks (Phase 1)
1. Read `research/ANALYSIS_AGENT_ROLES.md` and skill at `~/.openclaw/workspace/skills/quant-infrastructure/SKILL.md`
2. Read approved design at `research/pipeline_builds/{version}_architect_analysis_design.md`
3. Implement the analysis notebook: `notebooks/crypto_{source_version}_analysis.ipynb`
4. Notebook must include the mandatory Colab upload cell (Section 0.2 above)
5. Run: `python3 scripts/pipeline_orchestrate.py {version} complete analysis_builder_implementation --agent builder --notes "Notebook complete: N cells"`

### Critic Tasks (Phase 1 — Code Review)
1. Read skill at `~/.openclaw/workspace/skills/quant-infrastructure/SKILL.md`
2. Review notebook implementation quality, visualization clarity, statistical correctness
3. Check upload cell handles both zip and individual pkl correctly
4. If approved: `python3 scripts/pipeline_orchestrate.py {version} complete analysis_critic_code_review --agent critic --notes "Approved: ..."`
5. If blocked: write blocks to `research/pipeline_builds/{version}_critic_code_blocks.md`, then: `python3 scripts/pipeline_orchestrate.py {version} block analysis_critic_code_review --agent critic --notes "BLOCK-1: ..." --artifact {version}_critic_code_blocks.md`

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|

## ⚠️ MANDATORY GATE: No New Notebook Versions Until Analysis Complete

**Never start a fresh notebook version (v5, v6, etc.) until the analysis pipeline completes BOTH phases minimum.**

Phase 1 autonomous analysis surfaces patterns. Phase 2 human-directed analysis applies Shael's perspective. The interference pattern between Phase 1 findings and Shael's Phase 2 input often yields surprising results — what looks like a failure in Phase 1 may reveal hidden signal once human intuition is applied. Premature conclusions from Phase 1 alone miss this.

**Gate:** `analysis_phase2_complete` must be reached before any new implementation pipeline can be launched for the next version.

## Phase 2: Directed Analysis (Human-in-the-Loop)
_Status: Queued — triggers after Phase 1 completion and Shael's input_

### How Phase 2 Works
1. Phase 1 completes → Belam notifies Shael with key findings summary
2. Shael reviews Phase 1 notebook (on Colab) and formulates questions/directions
3. Shael relays questions to Architect directly (DM or group chat)
4. Architect designs Phase 2 sections — new analysis cells appended to existing notebook
5. Critic reviews methodology additions, Builder extends the notebook
6. Process mirrors Phase 1 stages (prefixed `analysis_phase2_`)

### `#phase2` Tag Convention
Shael provides feedback tagged with `#phase2 {version}` in DM or group chat. Belam (coordinator) captures all tagged messages chronologically into `research/pipeline_builds/{version}_phase2_shael_direction.md`. When Shael says "kick off phase 2" or all feedback is collected, Belam triggers the Architect.

### Shael's Direction
_(Populated from `research/pipeline_builds/{version}_phase2_shael_direction.md` after Phase 1 completion)_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|

## Phase 3: Iterative Analysis (Autonomous or Human-Triggered)
_Status: LOCKED — requires Phase 2 completion before activation_

**Gate condition:** `analysis_phase2_complete` must be set before any Phase 3 iteration can proceed.

### Phase 3 Iteration Chain Protocol

Analysis Phase 3 iterations are **interleaved** with main pipeline Phase 3 iterations in a strict chain:

```
Main Pipeline Phase 3 iter 01 → Analysis Phase 3 iter 01a, 01b, 01c...
  (all analysis iters complete, none pending) →
Main Pipeline Phase 3 iter 02 → Analysis Phase 3 iter 02a, 02b...
  (all clear) →
Main Pipeline Phase 3 iter 03 → ...
```

**Rules:**
1. Every analysis Phase 3 iteration MUST be preceded by a corresponding MAIN pipeline Phase 3 iteration (can't analyze what wasn't built/run)
2. Multiple analysis iterations allowed per single main iteration (deep dives, follow-ups)
3. The next MAIN pipeline iteration is ONLY allowed when ALL analysis iterations for the current one are complete AND none are pending
4. All Phase 3 iterations append sections to the existing analysis notebook — never create new files

### How Analysis Phase 3 Works

1. **Auto-triggered:** Main pipeline Phase 3 iteration completes and produces new pkl results → analysis Phase 3 iteration kicks off automatically
2. **Human-triggered:** Shael says "analyze X deeper" → iteration created
3. **Agent-triggered:** During analysis, agent identifies a follow-up analysis question → proposal generated:
   - Score ≥ 7: auto-approved (but MUST have a preceding main iteration)
   - Score 4-6: flagged for Shael's review
   - Score < 4: rejected, logged only

### Iteration Log

| ID | Source Main Iter | Hypothesis | Proposed By | Status | Result |
|----|-----------------|-----------|-------------|--------|--------|

## Artifacts
- **Design Brief:** `snn_applied_finance/research/pipeline_builds/{version}_design_brief.md`
- **Architect Analysis Design:** `snn_applied_finance/research/pipeline_builds/{version}_architect_analysis_design.md`
- **Critic Design Review:** `snn_applied_finance/research/pipeline_builds/{version}_critic_analysis_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/{version}_state.json`
- **Notebook:** `snn_applied_finance/notebooks/crypto_{source_version}_analysis.ipynb`
