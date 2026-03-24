---
primitive: task
status: in_pipeline
priority: high
created: 2026-03-20
owner: belam
depends_on: []
upstream: []
downstream: []
tags: [video, youtube, automation, infrastructure, manim, tts]
pipeline: report-to-youtube-pipeline
---

# Build Report-to-YouTube Video Pipeline

## Description

Build an end-to-end automated pipeline that takes a PDF or LaTeX research report and produces a fully edited YouTube video with:
- Professional voiceover narration
- Custom graphs and data visualizations pulled from the report
- Mathematical/concept animations (Manim-style)
- Structured narrative: origins of the research → methodology → findings → implications
- Title cards, transitions, background music, and polish

The pipeline should be scriptable and reusable — feed it any report, get a video. First target: one of the SNN analysis reports.

## Architecture

### Input
- PDF or LaTeX report (or the markdown analysis report from our pipeline)
- Optional: raw data/results files for regenerating visualizations
- Optional: style config (color palette, music choice, pacing)

### Output
- MP4 video (1080p minimum, 4K stretch goal)
- SRT subtitle file
- Thumbnail image
- Video description/metadata for YouTube upload

### Pipeline Stages

```
Report → Script → Assets → Assembly → Review → Export
```

## Phase 1: Capability Audit & Tool Selection

**Goal:** Determine what's installable and functional on the ARM VPS, identify gaps, select the stack.

### 1.1 Video Composition Engine
- [ ] Test **FFmpeg** availability and codec support (should be fine)
- [ ] Evaluate **MoviePy** — Python scriptable editing, FFmpeg backend
- [ ] Evaluate **Remotion** (Node.js) — React-based programmatic video, richer but heavier
- [ ] Decision: MoviePy vs Remotion vs pure FFmpeg scripting

### 1.2 Animation Engine
- [ ] Install and test **Manim** (Community Edition) on ARM64
  - Requires: Cairo, Pango, LaTeX (texlive), ffmpeg
  - Test: render a simple scene, verify output quality
- [ ] Benchmark render times for typical animations (30s clip at 1080p)
- [ ] Fallback: **matplotlib.animation** + FFmpeg if Manim is too heavy

### 1.3 Voiceover / TTS
- [ ] Test **Edge TTS** (free, async, good quality, no API key)
- [ ] Test **OpenAI TTS** (HD voices, needs API key — we likely have this)
- [ ] Evaluate **ElevenLabs** (studio quality, paid per character)
- [ ] Evaluate **Coqui XTTS** (local, free, but GPU-preferred)
- [ ] Decision: primary TTS engine + quality tier
- [ ] Test: generate 60s voiceover, evaluate naturalness and pacing

### 1.4 Supporting Tools
- [ ] **Pillow/Cairo** for title cards, lower thirds, custom graphics
- [ ] **pydub** or FFmpeg for audio mixing (voiceover + background music)
- [ ] Background music source (royalty-free: YouTube Audio Library, Pixabay, etc.)
- [ ] **LaTeX** rendering for equation overlays (likely already installed)

### 1.5 Constraints Assessment
- [ ] Memory budget on 4-core ARM VPS (Manim + rendering)
- [ ] Estimated render time for a 10-minute video at 1080p
- [ ] Storage for intermediate assets (frames, audio clips, temp video)
- [ ] Whether any component genuinely needs GPU (probably nothing does)

## Phase 2: Script Generation Pipeline

**Goal:** LLM-powered report → video script conversion.

### 2.1 Report Parsing
- [ ] PDF text extraction (PyMuPDF/pdfplumber — we have these)
- [ ] LaTeX source parsing (if available, richer than PDF extraction)
- [ ] Markdown report parsing (our native format — easiest path)
- [ ] Figure/table extraction and cataloging
- [ ] Structure detection: abstract, methodology, results, conclusions

### 2.2 Script Writer
- [ ] Design prompt template for report → video script
- [ ] Script format: timestamped segments with:
  - Narration text (for TTS)
  - Visual direction (what's on screen — animation, chart, title card)
  - Transition notes
  - Emphasis/pacing cues
- [ ] Target duration calculator (word count → minutes at speaking pace)
- [ ] Tone options: educational, documentary, technical deep-dive
- [ ] Hook/intro generator (the "why should you care" opener)
- [ ] Conclusion/CTA generator

### 2.3 Script Review Gate
- [ ] Human review checkpoint before asset generation
- [ ] Script preview: text + timing + visual storyboard (markdown)
- [ ] Revision loop capability

## Phase 3: Asset Generation

**Goal:** Programmatically create all visual and audio assets from the script.

### 3.1 Voiceover Generation
- [ ] Split script into segments by scene/section
- [ ] Generate audio per segment (allows re-recording individual parts)
- [ ] Apply pacing: pauses between sections, emphasis markers
- [ ] Export: WAV/MP3 per segment + master timeline

### 3.2 Data Visualizations
- [ ] Parse report for charts/tables → regenerate as styled video-ready plots
- [ ] Consistent color palette and typography
- [ ] Animated chart builds (data appearing progressively)
- [ ] Export: PNG sequences or MP4 clips per visualization

### 3.3 Concept Animations (Manim)
- [ ] Scene library for common concepts:
  - Neural network architecture diagrams
  - Spike timing / membrane potential animations
  - Data flow visualizations
  - Statistical concept illustrations (confidence intervals, permutation tests)
  - Comparison overlays (before/after, A vs B)
- [ ] Custom scene generator from script visual directions
- [ ] Export: MP4 clips per animation scene

### 3.4 Static Graphics
- [ ] Title card template (report title, authors, date)
- [ ] Section header cards
- [ ] Lower thirds (speaker name, topic label)
- [ ] Equation renders (LaTeX → high-res PNG)
- [ ] Key finding callout cards
- [ ] Thumbnail generator

### 3.5 Audio
- [ ] Background music selection and download
- [ ] Audio ducking (music volume drops during narration)
- [ ] Sound effects for transitions (subtle, optional)
- [ ] Master audio mix per segment

## Phase 4: Video Assembly

**Goal:** Compose all assets into the final video.

### 4.1 Timeline Engine
- [ ] Scene-by-scene assembly from script timeline
- [ ] Voiceover as master clock (visuals sync to narration timing)
- [ ] Transition effects between scenes (fade, cut, slide)
- [ ] Ken Burns effect on static images (subtle zoom/pan)
- [ ] Text overlay rendering (key quotes, statistics, labels)

### 4.2 Post-Production
- [ ] Color grading / consistent look
- [ ] Audio normalization (LUFS targeting for YouTube)
- [ ] Subtitle generation from script (SRT format)
- [ ] Intro/outro sequences
- [ ] Progress markers (chapter timestamps for YouTube)

### 4.3 Export
- [ ] H.264/H.265 encoding at target resolution
- [ ] YouTube-optimized bitrate and format
- [ ] Thumbnail export (1280x720)
- [ ] Metadata file (title, description, tags, chapters)

## Phase 5: Automation & CLI Integration

**Goal:** Make it a R command.

- [ ] `R video <report>` — full pipeline from report to video
- [ ] `R video <report> --script-only` — generate script for review
- [ ] `R video <report> --from-script <script.md>` — resume from approved script
- [ ] `R video <report> --assets-only` — regenerate assets without reassembly
- [ ] Pipeline stage tracking (same pattern as experiment pipelines)
- [ ] Config file for defaults (voice, style, music, resolution)

## Acceptance Criteria

- [ ] Feed in a PDF/LaTeX report, get a watchable YouTube-ready MP4
- [ ] Voiceover sounds professional (not robotic)
- [ ] Custom animations illustrate at least 3 key concepts from the report
- [ ] Data visualizations are regenerated (not screenshots of the PDF)
- [ ] Video has structure: hook → context → methodology → findings → implications
- [ ] Subtitles are accurate and properly timed
- [ ] Total render time under 30 minutes for a 10-minute video (on our VPS)
- [ ] Pipeline is reusable across different reports
- [ ] Human review gate exists between script and production

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Manim won't install/run on ARM64 | High | Fallback to matplotlib animations + custom Cairo rendering |
| TTS quality too robotic | High | Test multiple engines; ElevenLabs as premium fallback |
| Render time too slow on 4-core ARM | Medium | Reduce resolution, simplify animations, or render overnight |
| Animation generation needs too much manual direction | Medium | Build reusable scene templates; LLM generates Manim code |
| Video looks amateurish without motion design skills | Medium | Keep it clean and minimal — good typography + data viz > flashy effects |
| Memory exhaustion during rendering | Medium | Process segments independently, assemble at end |

## First Target

One of the SNN analysis reports — likely `validate-scheme-b` or `build-equilibrium-snn`. The Scheme B validation is a cleaner narrative (clear hypothesis → rigorous testing → confirmed result).

## Notes

- This is infrastructure that compounds — once built, every future report can become a video
- The LLM-to-Manim-code path is the most novel/risky piece — test early
- Consider whether the script generation should use the architect/critic pattern
- YouTube chapters and timestamps should be auto-generated from the script structure
- Long-term: could add AI avatar/presenter overlay (but that's a much later enhancement)
