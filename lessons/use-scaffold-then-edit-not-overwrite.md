---
primitive: lesson
date: 2026-03-20
source: session
confidence: high
tags: [infrastructure, primitives, conventions, clock-cycles]
upstream: [memory/2026-03-19_204801_design-principle-from-shael-clock-cycles]
promotion_status: promoted
doctrine_richness: 9
contradicts: []
---

# use-scaffold-then-edit-not-overwrite

## Context

Creating two new decision primitives (phase2-human-gate, clock-cycles-over-tokens). Used `R create decision` to scaffold, then tried `Edit` tool to replace body content — but guessed the template markers wrong (assumed `<!-- comment -->` instead of actual `_italic prompts_`). Fell back to `Write` which overwrote the entire file, bypassing the scaffold pattern.

## What Happened

`Write` (full overwrite) wastes the scaffold and violates clock-cycles-over-tokens — the scaffold already did the structural work, overwriting it re-does that work with tokens. The `Edit` tool failed because I didn't read the scaffold output first to learn the exact placeholder text.

## Lesson

Always work WITH the scaffold: `R create` → `R edit --set` for frontmatter → `Read` the file → `Edit` body sections using exact placeholder text. Never `Write`-overwrite a scaffolded file.

## Application

Every time a new primitive is created. The workflow is:
1. `R create <type> "name" --desc --tags` — scaffold (clock cycles)
2. `R edit "name" --set key=value` — frontmatter updates (clock cycles)
3. `Read` the file — learn exact placeholder text (one tool call)
4. `Edit` with exact `oldText` matches — surgical body replacement (minimal tokens)

No `Write` overwrites. The scaffold is the structure; edits fill it in.
