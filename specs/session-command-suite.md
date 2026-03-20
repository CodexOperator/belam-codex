# Spec: Session Command Suite for Codex Engine

## Overview

Add a `session` command group to `scripts/codex_engine.py` that manages agent sessions. All commands accessed via `belam -x session <subcommand>`.

## Commands

### `belam -x session list [agent]`
- Default: list all agents' sessions
- With agent: filter to that agent
- Wraps `openclaw sessions --agent <id> --json` and formats output
- Show: session key, session ID, last updated (human-readable age), token count, file path

### `belam -x session info <agent>`
- Show detailed info for an agent's current session
- Read `~/.openclaw/agents/<agent>/sessions/sessions.json`
- Show: session key, session ID, model, total tokens, last updated, transcript file path, file size

### `belam -x session new <agent>`
- Force-rotate the agent's current session to start fresh
- Steps:
  1. Read `~/.openclaw/agents/<agent>/sessions/sessions.json`
  2. Find the active session entry (the one matching `agent:<agent>:main` key pattern)
  3. Get the `sessionId` from the entry
  4. Find the corresponding JSONL file: `~/.openclaw/agents/<agent>/sessions/<sessionId>.jsonl`
     - Note: the sessionId in sessions.json might be a mapper ID like `mapper-xxx`, not the JSONL filename
     - Also check the transcript path from `openclaw sessions --agent <agent> --json` output
  5. Rename the JSONL: `{file}.jsonl` → `{file}.jsonl.reset.{ISO-timestamp}`
  6. Remove the session entry from `sessions.json` (delete the key, write back)
  7. Print confirmation: which file was rotated, session cleared
- If no active session found, print "No active session for <agent>" and exit 0

### `belam -x session send <agent> "<message>"`
- Send a message to an agent via `openclaw agent --agent <agent> -m "<message>"`
- If message starts with `@` treat it as a file path: read the file content as the message
- Useful for: `belam -x session send sage @/tmp/prompt.md`
- Print the agent's response (or "dispatched" if --bg flag used)

### `belam -x session log <agent> [--tail N]`
- Show the last N messages (default 10) from the agent's active transcript
- Parse the JSONL, extract user/assistant messages, format as readable markdown
- Skip tool calls unless `--verbose` flag

### `belam -x spawn [options] "<task>"`
- Convenience shorthand that maps to `sessions_spawn` tool call
- Options:
  - `--model <alias>` — model override (default: sonnet)
  - `--label <name>` — label for tracking
  - `--timeout <seconds>` — run timeout (default: 300)
  - `--agent <id>` — agent ID for subagent (optional)
- This is an **in-session** command — only works when called by an agent with access to `sessions_spawn`
- Implementation: the codex engine handler prints a structured JSON block that the calling agent interprets as a tool call request
- Format: `{"tool": "sessions_spawn", "params": {"task": "...", "model": "...", "label": "...", "mode": "run"}}`
- The calling agent reads this output and makes the actual `sessions_spawn` call
- This saves tokens by replacing verbose tool-call boilerplate with a short exec command

### Aliases: `sp`

## Registration in Codex Engine

Add to the `COMMANDS` dict in `codex_engine.py`:

```python
'session':  {'handler': 'session', 'description': 'Session management: list, info, new, send, log'},
'sess':     {'alias': 'session'},
```

The handler should parse `remaining_args[0]` as the subcommand (list/info/new/send/log).

## Key Implementation Details

### File Locations
- Sessions store: `~/.openclaw/agents/<agent>/sessions/sessions.json`
- Transcripts: `~/.openclaw/agents/<agent>/sessions/*.jsonl`
- Agent list: parse from `~/.openclaw/openclaw.json` → `agents[]` array

### Session Key Pattern
- Main session key format: `agent:<agent-id>:main`
- But sage's was `agent:code-tutor:main` (legacy) — now `agent:sage:main`
- Always read the actual keys from sessions.json, don't hardcode patterns

### The `@file` Pattern for Send
```python
if message.startswith('@'):
    filepath = message[1:]
    with open(filepath) as f:
        message = f.read()
```

### Error Handling
- All file operations wrapped in try/except with clear error messages
- Missing sessions.json → "No session store found for <agent>"
- Missing agent → "Unknown agent: <agent>. Available: ..." (list from openclaw.json)
- File rotation failure → show the error, don't crash

## Testing
After implementation, verify:
1. `belam -x session list` — shows all agents
2. `belam -x session info sage` — shows sage's current session
3. `belam -x session new sage` — rotates sage's session
4. `belam -x session info sage` — shows "no active session"
5. `belam -x session send sage "hello"` — creates new session automatically
6. `belam -x session log sage --tail 5` — shows the hello exchange

## Hook Integration (Post-Build)
Once working, update `hooks/memory-extract/handler.ts` to call:
```bash
belam -x session new sage
belam -x session send sage @${promptFile}
```
Instead of `openclaw agent --agent sage --session-id ... --message ...`
