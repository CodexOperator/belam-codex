---
primitive: lesson
date: 2026-03-23
source: session a1318751
confidence: high
upstream: []
downstream: []
tags: [instance:main, lm, workflow, documentation, orchestrate]
promotion_status: candidate
doctrine_richness: 8
contradicts: []
---

# workflow-doc-step-refs-must-match-actual-script-names

## Context

e0.l1 ("Full Pipeline Launch") was defined in `modes/orchestrate.md` with step 1 as `R pipeline launch {ver} --desc "..." --kickoff`. That alias either didn't exist or was broken, and the underlying `launch_pipeline.py --kickoff` had import errors.

## What Happened

When following e0.l1 to launch t1, step 1 referenced the broken `R pipeline launch` alias. The actual working invocation is `python3 scripts/launch_pipeline.py ... --kickoff`. Updated `modes/orchestrate.md` to reference the concrete script path.

## Lesson

Workflow docs (e0.l1 etc.) that reference shell aliases or high-level commands will silently break when those aliases aren't defined or drift. The steps must reference the actual executable path, not a convenience alias.

## Application

When updating script names or flags, grep `modes/` for any workflow that references the old command and update it. Workflow steps should be concrete enough to run as-is.
