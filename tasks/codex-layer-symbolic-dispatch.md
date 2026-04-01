---
primitive: task
status: superseded
superseded_by: build-codex-layer-v1
priority: high
created: 2026-03-22
owner: belam
depends_on: [codex-layer-output-codec]
upstream: [codex-layer-output-codec]
downstream: []
tags: [codex-layer, symbolic-dispatch, infrastructure]
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# Codex Layer Symbolic Dispatch

## Description

Wire symbolic command dispatch through the render engine so the LLM and human can interact with the entire workspace using minimal-token symbolic grammar instead of verbose shell commands or tool calls.

### Grammar

```
Bare coordinates → codex engine
  e0        orchestration sweep
  t5        navigate to task  
  p1        pipeline status
  e1t5      edit task 5

Prefix . → render engine verbs (codex layer meta)
  .d        diff since anchor
  .a        anchor reset
  .s        status
  .c        context
  .m        supermap (map)

Prefix ! → shell passthrough
  !"git status"     raw shell
  !git status       simple commands without quotes

Pipe → output routing
  e0 > t5    output of e0, feed to t5 context
  !cmd > .d  run cmd, diff against last
```

### What to build

1. Dispatch parser in render engine — route by prefix (bare/./!)
2. UDS dispatch command — send command, get codex-formatted response
3. Pipe semantics — result register feeding into next command
4. Integration with output codec (D4) — all responses come back codex-formatted

## Acceptance Criteria

- [ ] Bare coordinates dispatch through codex engine
- [ ] `.` prefix dispatches render engine verbs
- [ ] `!` prefix passes through to shell
- [ ] Pipe `>` chains output to next command's context
- [ ] All outputs go through output codec before returning
- [ ] Works from both LLM exec calls and human CLI

## Notes

Depends on output codec being live. This is the final piece that makes the codex layer the single interaction surface.
