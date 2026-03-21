---
primitive: command
command: "belam edit <primitive>"
aliases: []
description: "Fuzzy-match and edit primitives, --set key=value for frontmatter updates"
category: primitives
tags: [edit, primitives, fuzzy-match, frontmatter]
status: superseded
superseded_by: decision/codex-engine-v1-architecture
---

# belam edit

Fuzzy-matches a primitive by name and opens it for editing. Supports `--set key=value` for quick frontmatter updates without opening the full file.

## Usage
```bash
belam edit equilibrium              # fuzzy match and edit
belam edit equilibrium --set status=complete
belam edit equilibrium --set priority=critical
```

## Related
- `commands/create.md`
- `commands/embed-primitives.md`
