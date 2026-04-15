# Memory extraction fresh-session handoff — 2026-04-15

## Goal
Verify that lesson/decision auto-extraction now fires automatically when a new Hermes session starts.

## Root cause found
The old auto-extraction path lived in the OpenClaw command hook:
- `hooks/memory-extract/handler.ts`

After Hermes migration, the active Hermes plugin only registered:
- `on_session_start`
- `pre_llm_call`

So:
- manual extraction still worked
- automatic trigger no longer fired on Hermes session boundaries

## Fix implemented
Updated Hermes plugin:
- `local_plugins/openclaw_hooks/plugin.py`

New behavior:
- register `on_session_finalize`
- register `on_session_reset`
- keep `on_session_start` as catch-up safety path
- prefer Hermes sessions from `~/.hermes/sessions`
- fallback to legacy OpenClaw session path only if needed
- write extraction state to `memory/pending_extraction.json`
- append diagnostics to `logs/memory-extract.log`

## Installer updates
Updated:
- `scripts/install_openclaw_hooks_plugin.py`
- `scripts/install_interface_bootstrap.py`

Installed updated live Hermes plugin to:
- `~/.hermes/plugins/openclaw_hooks`

Installed manifest now exposes 4 hooks:
- `on_session_start`
- `on_session_finalize`
- `on_session_reset`
- `pre_llm_call`

## Tests added
New focused tests:
- `tests/test_openclaw_hooks_plugin.py`

Verified:
- `python -m pytest tests/test_openclaw_hooks_plugin.py -q`
- result: `3 passed`

Also verified plugin discovery manually from hermes-agent:
- plugin loads as `openclaw_hooks`
- hooks registered: 4

## Files changed
- `local_plugins/openclaw_hooks/plugin.py`
- `scripts/install_openclaw_hooks_plugin.py`
- `scripts/install_interface_bootstrap.py`
- `tests/test_openclaw_hooks_plugin.py`

## What to check in the next fresh session
1. Start a brand new session.
2. Send a normal first message.
3. Then inspect:
   - `memory/pending_extraction.json`
   - `logs/memory-extract.log`
   - recent files under `lessons/` and `decisions/`
4. Confirm the just-ended prior session was picked up automatically.

## Expected success signals
- `memory/pending_extraction.json` gets a new entry for the previous session id
- status becomes `running` and later `complete`
- `logs/memory-extract.log` contains lines like:
  - `Dispatching Hermes memory extraction`
  - `Hermes memory extraction spawned`
- if the extractor finds reusable material, new lesson/decision primitives appear

## Important note
The gateway restart had been requested, but at the time of handoff it was still draining because one active agent session remained. If auto-extraction does not fire immediately, first confirm the gateway has actually restarted and reloaded the updated plugin.

## Copy-paste check prompt for next session
Please verify Belam's auto lesson/decision extraction fix.

What changed:
- Hermes plugin now triggers extraction on `on_session_finalize` + `on_session_reset`
- it also has `on_session_start` catch-up logic
- it reads sessions from `~/.hermes/sessions`
- it writes tracker state to `memory/pending_extraction.json`
- it logs to `logs/memory-extract.log`

Please check:
1. whether the current fresh session caused the previous session to be auto-queued for extraction
2. whether `memory/pending_extraction.json` now shows a new entry for the just-ended previous session
3. whether `logs/memory-extract.log` shows the new Hermes-side dispatch lines
4. whether any new lesson/decision primitives were created

Changed files:
- `local_plugins/openclaw_hooks/plugin.py`
- `scripts/install_openclaw_hooks_plugin.py`
- `scripts/install_interface_bootstrap.py`
- `tests/test_openclaw_hooks_plugin.py`

Test status:
- `python -m pytest tests/test_openclaw_hooks_plugin.py -q` → `3 passed`
