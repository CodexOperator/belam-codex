---
name: belam
description: >
  Direct relay to the Belam workspace CLI and Codex Engine. Use when Shael (the user) 
  types commands exactly as Belam would — codex coordinates (t1, d6, p, m, md2), 
  codex flags (-g, -e, -n, --depth, --graph), pipeline commands (pipelines, pipeline list, 
  pipeline status), task commands (tasks, task detail), status checks (status), 
  memory inspection (memory), and any other belam CLI subcommand. 
  Routes codex coordinates and flags to `python3 scripts/codex_engine.py`; 
  routes named subcommands (pipelines, status, tasks, etc.) to the `belam` CLI. 
  No translation — the user's input passes through verbatim (after sanitization). 
  Triggers on: bare coordinates like t1/d6/p/m/md2, dash-flags like -g or --depth, 
  or any belam CLI subcommand typed directly in chat.
---

# Belam Relay Skill

Lets Shael invoke the Codex Engine and Belam CLI directly from chat using the **exact same syntax** Belam uses internally.

## When This Skill Applies

- User types a bare coordinate: `t1`, `d6`, `p`, `m`, `md2`, `a3`, etc.
- User types a flag-style command: `-g d6`, `-g d6 --depth 2`, `-e t1`, `-n m`
- User types a belam subcommand: `pipelines`, `status`, `tasks`, `memory`, `logs`
- User types a pipeline subcommand: `pipeline list`, `pipeline status`, `pipelines`
- No args / empty: show the supermap

## How to Execute

Run the relay script with the user's input as arguments:

```bash
cd ~/.openclaw/workspace
bash skills/belam/scripts/belam_relay.sh <user_input>
```

### Examples

| User types | Command run |
|---|---|
| `t1` | `python3 scripts/codex_engine.py t1` |
| `-g d6 --depth 2` | `python3 scripts/codex_engine.py -g d6 --depth 2` |
| `-e p` | `python3 scripts/codex_engine.py -e p` |
| `pipelines` | `belam pipelines` |
| `status` | `belam status` |
| `tasks` | `belam tasks` |
| *(no args)* | `python3 scripts/codex_engine.py` (supermap) |

## Routing Logic

The relay script auto-detects the route:
- **Codex Engine** (`python3 scripts/codex_engine.py`): input starts with `-` (flag), OR is a single token matching `[a-zA-Z]{1-4}[0-9]{0-4}` (coordinate)
- **Belam CLI** (`~/.local/bin/belam`): known subcommands — `pipelines`, `pipeline`, `status`, `tasks`, `task`, `memory`, `logs`, `log`, `heartbeat`, `help`, `version`, `config`

## Safety

Input is sanitized before execution:
- Max 200 characters
- Rejects: `;`, `|`, `&`, `$`, `\`, `>`, `<`, `` ` ``, `$(`, newlines
- Allows: alphanumeric, `-`, `_`, `.`, spaces, `=`, `,`, `'`, `"`

On rejection, the script exits with code 1 and prints an error.

## Output

Return the script's stdout directly to the user. It's already ANSI-stripped clean text.

## Script Location

`~/.openclaw/workspace/skills/belam/scripts/belam_relay.sh`
