---
primitive: task
status: open
priority: high
created: 2026-03-23
owner: belam
depends_on: [codex-engine-v3-legendary-map]
upstream: []
downstream: []
tags: [codex-engine, legendary-map, lm, infrastructure]
---

# LM v2: Coordinate-Native Pipeline Launch and Workflow Enrichment

## Description

The LM (Legendary Map) v1 established the self-describing namespace on the supermap. V2 enriches it so agents instinctively reach for coordinates over raw scripts — closing the gap where agents still bypass the coordinate system for common operations.

## Improvements

### 1. Coordinate-native pipeline launch (`e0 t{n}`)
- `e0 t1` should mean "launch pipeline for task 1" — detect eligible task, create pipeline, dispatch architect
- Currently requires falling through to `python3 scripts/launch_pipeline.py` — no coordinate shorthand exists
- Goal: single coordinate invocation replaces the 3-step e0.l1 workflow

### 2. Workflow step concreteness
- e0.l1 and e0.l2 workflows reference shell commands, not coordinates
- Each workflow step should itself be a coordinate or show the coordinate equivalent
- Example: e0.l1 step 3 says `R pipelines` — should say `p` (the coordinate)

### 3. Pipeline lifecycle coordinates
- `e0 archive {ver}` or `e0a {ver}` — archive a pipeline by coordinate
- `e0 status` — show all pipeline states without falling to R command
- Pipeline phase transitions expressible as field edits: `e1p{n} status archived`

### 4. Task-pipeline linking
- When a task has `status: in_pipeline`, its coordinate should show the linked pipeline
- `t1` view should render pipeline stage inline (e.g. "in_pipeline → p3 phase1/architect_design")

### 5. Richer LM entry descriptions
- Every LM entry should include at least one concrete example showing actual workspace coordinates
- Descriptions should be compelling enough to displace raw script invocations from agent habits
- Per lesson: lm-entries-must-be-compelling-to-displace-raw-scripts


### 6. Coordinate Mode scaffold on boot
- Cockpit plugin injects a compact "Coordinate Mode Active" block via `before_prompt_build`
- Lists available coordinate grammar (e0, t{n}, p{n}, d{n}, e1, e2, e3) with behavioral framing
- Agents see coordinates as the **expected interface**, not optional shortcuts
- Gentle nudge when raw commands (grep/cat/echo) would have a coordinate equivalent
- Enables coordinate navigation natively even without the full codex layer (t1) — perfect fallback
- LM entries become immediately actionable since the scaffold primes the agent to use them
- Degrades gracefully: if render engine is down, scaffold still works from static LM data
