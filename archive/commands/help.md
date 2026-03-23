---
primitive: command
command: "R help"
aliases: []
description: "Show the engine's action word registry and usage reference"
category: infrastructure
tags: [help, usage, reference, action-words]
---

# R help

Prints the full list of action words registered in the Codex Engine's ACTION_REGISTRY, grouped by category (Memory, Pipelines, Experiments, Primitives, Notebooks, Sessions, Other). Each entry shows the command name, description, and any shortcut aliases.

## Usage
```bash
R help
```

## What It Shows
- All registered action words with descriptions
- Shortcut aliases for each command
- Grouped by functional category

## Related
- `decisions/codex-engine-v1-architecture.md`
