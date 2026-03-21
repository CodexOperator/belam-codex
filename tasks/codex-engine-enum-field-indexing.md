---
primitive: task
status: open
priority: medium
created: 2026-03-21
owner: belam
depends_on: [t1-build-codex-engine]
upstream: [d28-codex-engine-dense-alphanumeric-coordinate-grammar, d8-codex-cockpit-plugin-architecture]
downstream: []
tags: [codex-engine, v2, dense-grammar, enum-indexing, token-efficiency]
---

# codex-engine-enum-field-indexing

## Description

Add numeric index resolution for enum-typed field values in Codex Engine edit mode. Instead of `e1 d8 2 accepted`, allow `e1 d8 2 1` where `1` maps to the first valid option for that field's enum.

This is the next compression step in the dense alphanumeric grammar — every token in the command chain becomes a number or short alpha, eliminating English words entirely from edit operations.

## Enum Mappings (Initial)

**status (decisions):** `1`=proposed, `2`=accepted, `3`=rejected, `4`=superseded
**status (tasks):** `1`=open, `2`=active, `3`=in_pipeline, `4`=complete, `5`=blocked
**priority:** `1`=critical, `2`=high, `3`=medium, `4`=low
**boolean fields:** `0`=false, `1`=true

## Implementation Notes

- Engine already knows primitive type from the coordinate (d→decision, t→task)
- Schema registry maps `(primitive_type, field_name) → enum_values[]`
- Numeric input resolved against the enum list; string input still accepted as fallback
- F-label output should show the resolved value: `F17 Δ d8.2 status proposed→accepted` (not `→1`)
- Schema registry should be extensible — new primitive types or custom enums
- Consider: display enum indices in field listings too (e.g., `╶─ 2   status      accepted [1]`)

## E0 Operation Indexing (Orchestration)

The same enum-index pattern extends to e0 orchestration commands. Operations are numbered, targets reference existing coordinates, `.` means "as":

- `e0p1 1.i1` — dispatch (op 1) as architect (i1)
- `e0p1 2` — status (op 2)
- `e0p1 3` — gates (op 3)
- `e0p1 4.i1.i3` — handoff (op 4) from architect to critic
- `e0p1 5` — locks (op 5)
- `e0p1 6.i1` — complete (op 6) as architect

The `.` connector = "as" — links an operation to its target individual(s). `i1`, `i2`, `i3` are already coordinate-addressable personas in the supermap.

No English in the command chain. `--json` flag replaced by output format index (e.g., trailing `.1` for JSON).

## Acceptance Criteria

- [ ] Numeric values resolve to enum entries for status, priority, boolean fields
- [ ] String values still work as fallback (no breaking change)
- [ ] F-label output shows resolved human-readable value
- [ ] Schema registry is extensible for new primitive types
- [ ] `e1 d8 2 1` sets status to the first enum value for that primitive type
- [ ] E0 operations indexed: dispatch=1, status=2, gates=3, handoff=4, locks=5, complete=6
- [ ] `.` connector wires operations to persona coordinates (i1, i2, i3)
- [ ] Output format indexable (text=default, json=1)
