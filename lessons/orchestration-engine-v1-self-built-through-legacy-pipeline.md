---
primitive: lesson
date: 2026-03-21
source: shael-session-2026-03-21
confidence: high
upstream: [d8-codex-cockpit-plugin-architecture, d7-orchestration-architecture]
downstream: []
tags: [orchestration, pipeline, self-reference, infrastructure, meta]
---

# orchestration-engine-v1-self-built-through-legacy-pipeline

## Context

We needed to build the Orchestration Engine V1 — the codex-native replacement for three legacy scripts (pipeline_orchestrate.py, pipeline_autorun.py, launch_pipeline.py). We launched it as a pipeline through the very legacy system it was designed to replace.

## What Happened

Three things ran in parallel:

1. **The legacy pipeline system auto-ran Phase 1** — architect→critic→builder handoffs fired autonomously via `pipeline_orchestrate.py`. The auto-builder produced a working 1208-line `orchestration_engine.py`.
2. **We ran a manual parallel pass** — spawned architect and critic as subagents with enhanced requirements (structured dispatch payloads, R/F label separation, Shael's Phase 2 feedback on dense coordinate grammar).
3. **Phase 2 builder merged both** — took the auto-built working script, overlaid the v2 design enhancements (dispatch payloads, TOCTOU lock fix, F-label output, hook verification), and produced the final engine.

The legacy system's last act was building its own replacement. The `codex-cockpit` plugin (R-label injection via `before_prompt_build`) was also built in the same session, proving the hook architecture the orchestration engine now uses.

## Lesson

**Use the system you're replacing to build its replacement.** The legacy orchestration scripts were good enough to autonomously produce a first draft of the new engine. The manual pass added the architectural vision. The merge produced something better than either alone. Self-referential bootstrapping works when the existing system is functional.

## Application

- When building infrastructure replacements, run the old system one last time to produce the first draft
- Parallel manual + automated passes catch different issues (auto-run found implementation gaps, manual pass found architectural gaps)
- Phase 2 refinement that merges two independent passes is more robust than a single linear pipeline
- The pattern extends: v2 of the orchestration engine should be built THROUGH v1, proving v1 works
