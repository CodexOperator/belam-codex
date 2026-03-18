---
primitive: lesson
date: 2026-03-18
source: "Pipeline debugging — agents processing 3 pipelines in one session despite one-at-a-time gate"
confidence: high
project: snn-applied-finance
tags: [infrastructure, agents, openclaw, debugging]
applies_to: [orchestrator, pipeline-autorun, agent-management]
---

# Lesson: OpenClaw Agent CLI Uses `main` Session, Not Group Session

## Finding
`openclaw agent --agent <name> --message <msg>` delivers to the `agent:{name}:main` session key, NOT the `agent:{name}:telegram:group:{id}` session key.

## Impact
Resetting only the group session left old handoff messages in the main session. The agent woke up, found three pipeline handoffs queued, and processed all three in one session — defeating the one-at-a-time gate.

## Fix
`reset_agent_session()` must reset BOTH:
- `agent:{name}:main` — the CLI session
- `agent:{name}:telegram:group:{id}` — the group chat session

## Pattern
When debugging agent behavior, always check which session key the delivery mechanism actually uses. `openclaw gateway call sessions.list --json` shows all sessions with their keys.

## Verification
```bash
openclaw gateway call sessions.list --json | python3 -c "
import json, sys
for s in json.load(sys.stdin).get('sessions', []):
    if 'architect' in s.get('key', ''):
        print(s['key'], s['sessionId'][:12])
"
```
