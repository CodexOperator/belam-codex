---
title: Indexed Command Interface as Default belam UX
status: accepted
date: 2026-03-20
upstream: [decisions/clock-cycles-over-tokens]
downstream: [decisions/primitive-relationship-graph]
tags: [infrastructure, cli, ux, belam]
---

# Indexed Command Interface as Default belam UX

## Context

Every belam command previously rendered flat text output. Navigation required knowing exact command names and primitive slugs. We wanted every command to render an **addressable indexed view** by default — coordinates you can reference in follow-up calls.

## Decision

**Every belam command renders indexed, addressable output by default.** Raw/plain output is available via `--raw` flag.

## Implementation

**Engine:** `scripts/belam_index.py` (883 lines) — intercepts all belam commands before bash dispatch.

**Three levels of indexing:**

1. **Root menu** (`belam` with no args) — all commands organized by category. Categories: a=PIPELINES, b=PRIMITIVES, c=CREATE/EDIT, d=EXPERIMENTS, e=MEMORY, f=NOTEBOOKS, g=OTHER. Example: `belam a1` → `belam pipelines`.

2. **List views** (`belam lessons`, `belam tasks`, `belam pipelines`, `belam notebooks`, `belam status`) — each item gets a numeric index. Example: `belam lesson 4` shows the 4th lesson. Bare numbers work too: `belam 4` resolves against the last list.

3. **Create scaffolds** (`belam create lesson`, `belam create task`, etc.) — field-level coordinates showing what's required/optional with type hints. Falls through to normal creation when title is provided.

**Coordinate system:**
- Root: `{letter}{number}` — e.g., `a1`, `b3`, `c2` (sticky — always work)
- Lists: `{number}` — e.g., `1`, `5`, `12` (context-dependent)
- Status: `p{number}` for pipelines, `t{number}` for tasks

**State persistence:**
- `~/.belam_last_context` — last rendered view (list type + index mapping)
- `~/.belam_root_context` — root menu mapping (persists across list views)
- Bare number input resolves against last context
- Letter+number coords fall back to root context if not in current context

**Indexed commands:** `belam`, `status`, `tasks`, `lessons`, `decisions`, `projects`, `pipelines`, `notebooks`, `create` (scaffold mode). All singular show commands (`lesson`, `task`, `decision`, `project`, `pipeline`, `notebook`) accept numeric indices.

**Bash integration:** Index engine runs first, exit code 0 = handled, exit code 2 = fall through to normal bash dispatch. `set -e` handled via `|| _idx_rc=$?` pattern.

## `--raw` flag

Any command + `--raw` or `--plain` bypasses the index engine entirely, rendering the old-style unindexed output. For scripting and piping.

## Consequences

- Every command is navigable without knowing slugs or file paths
- Sequential workflow: `belam` → `b2` → `3` → drill into anything
- Muscle memory builds around coordinates, not names
- `--raw` preserves scriptability
- Sub-agents built the 4 major extensions in parallel (~2 min)
- All existing commands continue to work unchanged
