---
primitive: task
status: open
priority: high
created: 2026-03-22
owner: belam
depends_on: [codex-layer-context-injection]
upstream: [codex-layer-context-injection]
downstream: [codex-layer-symbolic-dispatch]
tags: [codex-layer, output-codec, infrastructure]
---

# Codex Layer Output Codec

## Description

Extend `codex_codec.py` to handle command outputs — translating raw JSON, log lines, and structured text into coordinate-addressed codex format. Every command output gets a transient coordinate so the LLM can reference specific fields or rows in subsequent commands without re-parsing.

### Core concept: Result Register

```
# Command output gets transient coord _
orchestration_engine.py → _ = {p1:phase1_complete, p2:local_analysis_complete, ...}

# Fields addressable:
_.p1.status → "phase1_complete"

# Pipe to next command:
_.p1 > e1    "open p1 in edit mode"

# History:
_1, _2, _3   previous results (stack)
```

### What to build

1. `output_to_codex(command, stdout, stderr, returncode)` — recognize common output patterns:
   - JSON objects/arrays → field-addressed codex
   - Tabular output → row-addressed codex with column names
   - Key-value pairs → field-addressed codex
   - Unstructured text → passthrough with coord wrapper
   - Known scripts (orchestration_engine, launch_pipeline, git status) → specific parsers

2. Result register in render engine — transient coordinates for command outputs
3. Field addressing — dot notation into result fields

## Acceptance Criteria

- [ ] `output_to_codex()` handles JSON, tabular, key-value, and raw text
- [ ] Known script outputs have specific parsers (orchestration, git, pipeline)
- [ ] Transient coordinates assigned to outputs (_ for latest, _N for history)
- [ ] Dot notation field access works (_.field, _.row.field)
- [ ] Token savings measured vs raw output passthrough
- [ ] Round-trip: codex-formatted output can be piped to next command

## Notes

Depends on codex-layer-context-injection being live (legend + hook infrastructure).
