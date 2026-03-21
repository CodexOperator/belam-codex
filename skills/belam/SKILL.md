---
name: belam
description: >
  Direct relay to the Belam workspace CLI and Codex Engine. Use when Shael (the user) 
  types commands exactly as Belam would — codex coordinates (t1, d6, p, m, md2), 
  V2 dense grammar (e0p3, e1t12, e2 t "title", e3), codex flags (-g, -e, -n, --depth, --graph),
  pipeline commands (pipelines, pipeline list, pipeline status), task commands (tasks, task detail),
  status checks (status), memory inspection (memory), and any other belam CLI subcommand.
  Routes codex coordinates, V2 mode operations, and flags to `python3 scripts/codex_engine.py`;
  routes named subcommands (pipelines, status, tasks, etc.) to the `belam` CLI.
  No translation — the user's input passes through verbatim (after sanitization).
  Triggers on: bare coordinates like t1/d6/p/m/md2, V2 mode ops like e0/e1/e2/e3,
  dash-flags like -g or --depth, or any belam CLI subcommand typed directly in chat.
---

# Belam Relay Skill

Lets Shael invoke the Codex Engine and Belam CLI directly from chat using the **exact same syntax** Belam uses internally.

## When This Skill Applies

- User types a bare coordinate: `t1`, `d6`, `p`, `m`, `md2`, `e`, etc.
- User types a V2 mode operation: `e0`, `e0p3`, `e1t12`, `e2 t "title"`, `e3`
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
| `e0p3` | `python3 scripts/codex_engine.py e0p3` |
| `e1 t1 2 active` | `python3 scripts/codex_engine.py e1 t1 2 active` |
| `e0 locks` | `python3 scripts/codex_engine.py e0 locks` |
| `e` | `python3 scripts/codex_engine.py e` (list modes) |
| `-g d6 --depth 2` | `python3 scripts/codex_engine.py -g d6 --depth 2` |
| `pipelines` | `belam pipelines` |
| `status` | `belam status` |
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
