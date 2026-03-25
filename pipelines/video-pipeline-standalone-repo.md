---
primitive: pipeline
status: p1_complete
priority: high
type: infrastructure
version: video-pipeline-standalone-repo
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-25
---

# Implementation Pipeline: VIDEO-PIPELINE-STANDALONE-REPO

## Description
Standalone video content pipeline repo with CI/CD

## Type
Infrastructure pipeline — no notebook, no experiment. Deliverables are code, hooks, plugins, and config files.
At phase1_complete, this pipeline is ready for human review and archival (no experiment/analysis phases).

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-25 | belam-main | Pipeline instance created |
| p1_architect_design | 2026-03-25 | architect | Design v1: Extract 7-file video pipeline (~1146L) into standalone repo. 21 deliverables (~2000L, 25 files). src/ layout + hatchling + GitHub Actions CI + pytest (9 tests). Minimal mechanical refactoring, no behavioral changes. 4 open questions for critic. Design at: pipeline_builds/video-pipeline-standalone-repo_architect_design.md |
| p1_critic_design_review | 2026-03-25 | critic | APPROVED: 0 BLOCKs, 1 HIGH FLAG, 2 MED FLAGs, 1 LOW FLAG. FLAG-1 HIGH: numpy missing from pyproject.toml dependencies — video_visuals.py imports numpy but it's not declared; pip install into clean venv will fail on chart generation. Fix: add numpy>=1.24. FLAG-2 MED: sys.path.insert(0) hack in report_to_video.py must be explicitly removed during cli.py refactoring, not silently carried over. FLAG-3 MED: COLORS palette copy-pasted between thumbnail.py and visuals.py — accept for V1 but add TODO for extraction. FLAG-4 LOW: integration tests (Edge TTS) need offline graceful skip. All 4 open questions answered (agree on all: ~/repos/, include workflow, MIT, defer Docker). Source files verified: all 7 match claimed line counts, import structure is clean (no cross-module deps except orchestrator). Review at: pipeline_builds/video-pipeline-standalone-repo_critic_design_review.md |
| p1_builder_implement | 2026-03-25 | builder | All 21 deliverables implemented + 2 critic suggestions. D1 README.md with architecture diagram + CLI reference. D2 pyproject.toml: hatchling build, PEP 621, numpy>=1.24 (FLAG-1 fix). D3 Makefile (7 targets). D4 ci.yml: lint+test on push/PR. D5 release.yml: tag→PyPI. D6-D12 source modules: mechanical refactoring with relative imports, sys.path.insert removed (FLAG-2 fix), TODO comments for COLORS extraction (FLAG-3). D13-D19 tests: 42 unit tests + 3 integration tests with offline graceful skip (FLAG-4 fix). D20 sample_report.md (self-contained, ~35 lines). D21 .gitignore. Plus: py.typed marker (PEP 561), project.urls in pyproject.toml. pip install -e . works, report-to-youtube --help works, python3 -m report_to_youtube works. 42/42 unit tests GREEN, ruff check+format clean. |
| p1_builder_verify | 2026-03-25 | builder | GREEN: All 5 success criteria verified. (1) pip install -e . succeeds. (2) report-to-youtube examples/sample_report.md --script-only produces 5 scenes, ~85s. (3) pytest 42/42 unit tests GREEN, 3 integration deselected. (4) ruff check — All checks passed. (5) ruff format --check — 16 files already formatted. FLAG-1 verified: numpy>=1.24 in pyproject.toml. FLAG-2 verified: zero sys.path.insert in src/. FLAG-3 verified: TODO comments in visuals.py and thumbnail.py. FLAG-4 verified: skipif(_network_available) in test_tts.py. |
| p1_builder_verify | 2026-03-25 | builder | GREEN: 13/13 tests passed. T1 pip install, T2 CLI entry point, T3 python -m, T4 script generator YAML, T5 thumbnail 1280x720, T6 title card visual, T7 SRT subtitles, T8 pytest 42/42 unit tests, T9 ruff lint clean, T10 FLAG-1 numpy, T11 FLAG-2 no sys.path, T12 FLAG-3 TODO comments, T13 all 19 files present. Results at pipeline_builds/video-pipeline-standalone-repo_test_results.md |
| p1_critic_code_review | 2026-03-25 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 1 LOW FLAG. All 4 design FLAGs resolved (numpy added, sys.path removed, COLORS TODO added, offline skip implemented). 42/42 pytest GREEN independently. Ruff lint clean. Both entry points work. py.typed and project.urls suggestions picked up. FLAG-1 MED: Makefile build target needs 'build' package in dev deps. FLAG-2 LOW: audio_dir dead variable in assembler.py. Review at: pipeline_builds/video-pipeline-standalone-repo_critic_code_review.md |

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
- **Spec:** `snn_applied_finance/specs/video-pipeline-standalone-repo_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/video-pipeline-standalone-repo_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/video-pipeline-standalone-repo_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/video-pipeline-standalone-repo_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_video-pipeline-standalone-repo.ipynb`
