# Hermes Cockpit V1 Handoff — 2026-04-19

## What was done

Implemented Hermes Cockpit V1 behavior in the runtime plugin:
- Plugin path: `/home/ubuntu/.hermes/plugins/openclaw_hooks/plugin.py`

### Cockpit V1 behavior now on disk
- First turn injects full cockpit context.
- Full context ordering is now:
  1. `## Supermap`
  2. `## Legend`
  3. `## Cockpit Status`
  4. remaining injected docs (`SOUL`, `IDENTITY`, `USER`, etc.)
  5. `## Memory Boot Index`
- Later turns are live by default with option B behavior:
  - no relevant workspace change -> no injection
  - relevant workspace change -> inject compact `## Cockpit Delta`
  - explicit refresh -> full inject again
- Explicit refresh commands supported:
  - `r0`
  - `/supermap`
  - `/cockpit`
  - `/refresh-supermap`
- Compact status command supported:
  - `/cockpit-status`
  - `cockpit status`
- Existing memory extraction lifecycle hooks were preserved.

## Specific final tweak after V1

Adjusted full-boot ordering so the legend appears directly after the supermap.

Code area changed:
- `_build_full_cockpit_context(...)`

Implementation detail:
- plugin now reads injected docs once
- pulls out `Legend` (`codex_legend.md`) separately
- renders legend immediately after supermap
- renders all other injected docs afterward

## Verification run

Ran:
- `python3 -m py_compile /home/ubuntu/.hermes/plugins/openclaw_hooks/plugin.py`
- direct import/execution checks against plugin

Verified:
- plugin compiles
- first-turn context generation works
- `## Supermap` appears before `## Legend`
- `## Legend` appears before `## Cockpit Status`
- ordering check returned `True`

## Important deploy note

Hermes gateway service was still active at handoff time:
- `systemctl --user is-active hermes-gateway` -> `active`

That means running gateway process may still have old plugin code loaded until restart.

## Next recommended step

Restart Hermes gateway so new cockpit ordering/behavior applies to fresh sessions.

Suggested check after restart:
1. start fresh session
2. confirm first-turn order is:
   - supermap
   - legend
   - cockpit status
3. send second neutral turn with no workspace changes -> should inject nothing
4. touch relevant workspace state -> next turn should inject `Cockpit Delta`
5. run `/cockpit` -> should force full refresh

## Files changed this session

- `/home/ubuntu/.hermes/plugins/openclaw_hooks/plugin.py`

## Files created this session

- `/home/ubuntu/.hermes/hermes-agent/.hermes/plans/2026-04-19_071629-cockpit-v1-plan.md`
- `/home/ubuntu/.hermes/belam-codex/handoff/2026-04-19-hermes-cockpit-v1-handoff.md`
