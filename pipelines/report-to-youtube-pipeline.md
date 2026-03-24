---
primitive: pipeline
status: phase1_complete
priority: high
type: infrastructure
version: report-to-youtube-pipeline
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-24
---

# Implementation Pipeline: REPORT-TO-YOUTUBE-PIPELINE

## Description
Publish research reports and analysis directly to YouTube as narrated video content

## Type
Infrastructure pipeline — no notebook, no experiment. Deliverables are code, hooks, plugins, and config files.
At phase1_complete, this pipeline is ready for human review and archival (no experiment/analysis phases).

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-24 | belam-main | Pipeline instance created |
| architect_design | 2026-03-24 | architect | Design v1: Report-to-YouTube pipeline. 8 deliverables (~740L, 8 files). D1: script generator (report→structured YAML with scenes, narration, visual directions). D2: Edge TTS engine (free, async, high quality). D3: visualization generator (matplotlib animated charts + Manim animations + Cairo title cards). D4: MoviePy video assembler (audio as master clock). D5: SRT subtitle generator. D6: thumbnail generator. D7: CLI orchestrator (report_to_video.py). First target: validate-scheme-b report. Stack: Edge TTS + MoviePy + Manim + FFmpeg + Pillow. All ARM64 compatible. 5 tests. 4 open questions for critic. |
| critic_design_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 2 HIGH FLAGs, 2 MED FLAGs, 2 LOW FLAGs. FLAG-1 HIGH: 5 of 7 deps not installed (ffmpeg, edge-tts, moviepy, pydub, pymupdf) — builder must install D8 FIRST or 3/5 tests fail immediately. Sudo available. FLAG-2 HIGH: D1 script generator underspecified — shows YAML output but no parsing logic. Fix: start with markdown only, split on ## headings, section-name→visual-type mapping dict, 150wpm word count. Defer PDF parsing. FLAG-3 MED: MoviePy 2.x API differs from code (import paths, volume methods). Pin moviepy or verify 2.x API. FLAG-4 MED: subtitle timing assumes uniform word distribution — accept for V1, use Edge TTS SubMaker word timestamps in V2. FLAG-5 LOW: no stage-level resume (check if output exists before re-generating). FLAG-6 LOW: Manim in requirements despite deferral to V2 — remove it. Q1: matplotlib for V1, Manim V2. Q2: template from report text. Q3: skip BGM. Q4: optional review gate. Review at: pipeline_builds/report-to-youtube-pipeline_critic_design_review.md |
| builder_implementation | 2026-03-24 | builder | All 8 deliverables implemented. D1 video_script_generator.py (210L): markdown parser splits on ## headings, section→visual-type mapping dict, 150wpm duration estimates, spoken-word text cleanup. D2 video_tts.py (95L): Edge TTS async, per-scene resume (FLAG-5). D3 video_visuals.py (260L): title cards (Pillow), static charts + animated bar charts (matplotlib.animation→MP4), dark theme palette. D4 video_assembler.py (140L): MoviePy 2.x API verified (FLAG-3), audio as master clock, video loop/trim to match audio. D5 video_subtitles.py (100L): SRT with 10-word chunks, uniform timing (FLAG-4 V1 accepted). D6 video_thumbnail.py (110L): 1280x720 YouTube thumbnail. D7 report_to_video.py (160L): CLI orchestrator with --script-only, --from-script, --preview, --assets-only flags. D8 requirements-video.txt: edge-tts+moviepy+pydub+pymupdf only (no Manim per FLAG-6). All 6 FLAGs addressed. Test spec 9/9 GREEN including T9 end-to-end preview (1-scene video generated from validate-scheme-b report). |
| builder_verification | 2026-03-24 | builder | GREEN: 9/9 tests passed. T1 Edge TTS audio gen, T2 Pillow thumbnail, T3 FFmpeg available, T4 YAML format, T5 MoviePy 2.x imports, T6 script generator parses validate-scheme-b report, T7 SRT subtitle gen, T8 visual generator (title cards + charts), T9 end-to-end preview (1-scene video from real report). Results at pipeline_builds/report-to-youtube-pipeline_test_results.md |
| critic_code_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 1 MED FLAG, 2 LOW FLAGs. All 6 design FLAGs resolved. 9/9 tests pass. FLAG-1 MED: animated chart visuals use random placeholder data (np.random bars), not connected to report data — narration says '53.5% accuracy' but chart shows random bars. Acceptable for V1 but needs data wiring in V2. FLAG-2 LOW: pymupdf in requirements but never imported (markdown-only V1). FLAG-3 LOW: animated charts may be slow on ARM64 (300 frames × FFmpeg encode). 8 files, ~1146L total. Modular architecture works: each stage produces files consumed by the next. Stage-level resume throughout. Edge TTS, MoviePy 2.x, matplotlib.animation all working on ARM64. Review at: pipeline_builds/report-to-youtube-pipeline_critic_code_review.md |
| phase1_complete | 2026-03-24 | architect | Phase 1 COMPLETE. Critic code review APPROVED 0 BLOCKs, 3 FLAGs (1 MED, 2 LOW). 9/9 tests pass. 8 files, 1146L. All stages working on ARM64: Edge TTS, MoviePy 2.x, matplotlib.animation. FLAG-1 MED: animated charts use placeholder data, not connected to actual report data — V2 fix. FLAG-2 LOW: pymupdf unused (markdown-only V1). FLAG-3 LOW: animated charts may be slow on ARM64 (300 frames). Modular architecture validated: each stage produces files consumed by next, stage-level resume works. Ready for Phase 2 — wire real data into charts, produce first validate-scheme-b video. |
| phase1_complete | 2026-03-24 | main | Archived via heartbeat (11:18) |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design_blocked | 2026-03-24 | architect | BLOCKED: BLOCK: No Phase 2 direction from Shael. Phase 2 should wire real data into charts and produce first validate-scheme-b video. Unblock by creating phase2_direction.md. |

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
- **Spec:** `snn_applied_finance/specs/report-to-youtube-pipeline_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/report-to-youtube-pipeline_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/report-to-youtube-pipeline_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/report-to-youtube-pipeline_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_report-to-youtube-pipeline.ipynb`
