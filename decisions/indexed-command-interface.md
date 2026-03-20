---
title: Indexed Command Interface as Default belam UX
status: accepted
date: 2026-03-20
tags: [infrastructure, cli, ux, belam]
---

# Indexed Command Interface as Default belam UX

## Context

Every belam command currently renders flat text output. Navigation requires knowing exact command names and primitive slugs. We want every command to render an **addressable indexed view** by default — coordinates you can reference in follow-up calls.

## Decision

**Every belam command renders indexed, addressable output by default.** Raw/plain output is available via `--raw` flag.

### Design

**Three levels of indexing:**

1. **Root menu** (`belam` with no args) — shows all commands organized by category. Categories get letter prefixes (a-z), commands get numbers within category. `belam a2` runs the second command in category A.

2. **List views** (`belam lessons`, `belam tasks`, `belam pipelines`, etc.) — each item gets a numeric index. `belam lesson 3` or just `belam 3` (if last command was `belam lessons`) shows item #3.

3. **Detail views** (`belam lesson <name>`, `belam pipeline <ver>`) — fields get coordinates for edit addressing. `belam edit --field b3` targets the third field in section B.

**Coordinate system:**
- Root: `{letter}{number}` — e.g., `a1`, `b3`, `c2`
- Lists: `{number}` — e.g., `1`, `5`, `12`
- Detail fields: `{letter}{number}` — same pattern, sections get letters

**State persistence:**
- `~/.belam_last_context` stores the last rendered view type + mapping
- Bare number input (`belam 3`) resolves against last context
- Explicit commands always work regardless of context

**`--raw` flag:**
- Any command + `--raw` renders the old-style unindexed output
- For scripting and piping

### Core components:
- `scripts/belam_index.py` — rendering engine + coordinate resolver
- Modified `belam` bash entrypoint — routes through index engine
- Per-command integration (progressive rollout)

## Consequences

- Every command becomes navigable without knowing slugs
- Sequential workflow: `belam` → `b2` → `3` → drill into anything
- Muscle memory builds around coordinates, not file paths
- `--raw` preserves scriptability
