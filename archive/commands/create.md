---
primitive: command
command: "R create <type>"
aliases: []
description: "Create a new primitive (lesson/decision/task/project/skill) with frontmatter scaffolding"
category: primitives
tags: [create, primitives, scaffolding]
status: superseded
superseded_by: decision/codex-engine-v1-architecture
---

# R create

Creates a new primitive file with proper YAML frontmatter scaffolding. Supports lesson, decision, task, project, and skill types. Use instead of manually creating files to ensure consistent structure.

## Usage
```bash
R create lesson
R create decision
R create task
R create project
R create skill
```

## Related
- `decisions/skill-primitive-pairing.md`
- `commands/edit.md`
