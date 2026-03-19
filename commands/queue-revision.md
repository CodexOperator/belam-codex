---
primitive: command
command: "belam queue-revision <ver> [opts]"
aliases: ["belam qr"]
description: "Queue a revision request for autorun pickup"
category: pipeline
tags: [revision, queue, autorun, pipeline]
---

# belam queue-revision

Creates a revision request file that `belam autorun` picks up on the next cycle. Supports fuzzy version matching.

## Usage
```bash
belam queue-revision <version> [--context-file <path>] [--section "## Header"] [--priority critical|high|normal|low] [--body "extra context"]
```

## Examples
```bash
# Queue with findings doc + specific section
belam queue-revision build-eq --context-file research/v4_deep_analysis_findings.md --section '## For BUILD-EQUILIBRIUM-SNN' --priority critical

# Queue with inline body text
belam queue-revision stack-sp --priority high --body 'Revise stacking to add specialist aliveness checks'

# Minimal — just queue it
belam queue-revision validate-scheme-b --priority high
```

## How It Works
1. Creates `pipeline_builds/{version}_revision_request.md` with YAML frontmatter
2. Next `belam autorun` (or heartbeat) picks it up
3. Autorun loads context from the referenced file/section
4. Calls `orchestrate_revise()` to run the full architect→critic→builder→complete loop
5. Deletes the request file after kicking

## Related
- `commands/autorun.md`
- `commands/revise.md`
- `skills/orchestration/SKILL.md`
