---
primitive: task
status: open
priority: low
created: 2026-03-24
owner: belam
depends_on: []
upstream: [limit-soul-read-write]
downstream: []
tags: [infrastructure, codex-engine, persona, render]
project: codex-engine
---

# Persona-Filtered Supermap Views

## Description

Render engine supports filtered views of the supermap based on persona role. Each persona sees a weighted view emphasizing the namespaces most relevant to their work.

## Scope

1. `--as architect` → decisions, knowledge, specs weighted higher
2. `--as builder` → tasks, code references, experiments weighted higher  
3. `--as critic` → lessons, test results, validation data weighted higher
4. Filtering is additive (everything still visible, just reordered/emphasized)
5. Persona skill templates can request their filtered view on load

## Success Criteria

- [ ] Three persona views render correctly
- [ ] Filtering reduces context size for focused work
- [ ] Persona skills auto-request their view
- [ ] Coordinator still sees full unfiltered supermap
