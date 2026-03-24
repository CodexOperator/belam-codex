---
primitive: task
status: open
priority: high
created: 2026-03-24
owner: belam
project: multi-agent-infrastructure
depends_on: []
upstream: [report-to-youtube-pipeline]
downstream: []
tags: [video, youtube, infrastructure, repo-setup]
---

# Video Pipeline: Standalone Repo & Iterative Improvement Loop

## Description

Move the report-to-YouTube video pipeline into its own standalone repository alongside belam-codex and machinelearning. Set up iterative Phase 2/3 improvement via heartbeat-driven Opus subagent loops.

## Phase 1: Repo Setup

1. Create `~/video-pipeline/` directory (same parent as `~/.openclaw/workspace` and `machinelearning`)
2. Initialize git repo, push to `CodexOperator/video-pipeline`
3. Move scripts: `report_to_video.py`, `video_*.py`, `requirements-video.txt`
4. Add test suite: unit tests for each module, integration test that produces a 10-second test video
5. Add `Makefile` or `run.sh` with standard targets: `test`, `generate`, `clean`
6. Update workspace references to point to new location

## Phase 2: Iterative Improvement Heartbeat

Add to HEARTBEAT.md a new task:
- Check if video-pipeline has an open iteration task
- If iteration_complete: spawn Opus subagent (Ralph Wiggum 3x loop) that:
  1. Runs the test suite
  2. Attempts to generate a video from a real report
  3. Identifies failures, attempts bugfixes
  4. Reports findings back to coordinator
- Coordinator reviews findings, scopes next iteration task with improvements
- Loop continues until pipeline produces a real video end-to-end

## Phase 3: Production

- Install ffmpeg and manim dependencies
- Generate first real video from validate-scheme-b report
- Upload to YouTube (manual first, automated later)

## Notes

- Each iteration should be small and testable
- The Ralph loop gives 3 attempts before reporting back
- Coordinator decides whether to fix small bugs inline or scope a new task
