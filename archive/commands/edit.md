---
primitive: command
command: "R edit <primitive>"
aliases: []
description: "Fuzzy-match and edit primitives, --set key=value for frontmatter updates"
category: primitives
tags: [edit, primitives, fuzzy-match, frontmatter]
status: superseded
superseded_by: decision/codex-engine-v1-architecture
---

# R edit

Fuzzy-matches a primitive by name and opens it for editing. Supports `--set key=value` for quick frontmatter updates without opening the full file.

## Usage
```bash
R edit equilibrium              # fuzzy match and edit
R edit equilibrium --set status=complete
R edit equilibrium --set priority=critical
```

## Related
- `commands/create.md`
- `commands/embed-primitives.md`
