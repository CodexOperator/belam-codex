---
primitive: task
status: open
priority: medium
created: 2026-03-24
owner: belam
depends_on: [persistent-e3-registry]
upstream: [persistent-extend-and-indexed-subops]
downstream: []
tags: [engine, indexed-subops, infrastructure]
project: codex-engine
---

# Indexed Sub-Operations for e0 and e3

## Description

Index all remaining word-based sub-operations across e0 (orchestrate) and e3 (extend) into numeric/coordinate-addressable operations. This is the final step to eliminate English words from the engine command grammar.

## Scope

1. Audit all e0 sub-operations (sweep, status, checkpoint, etc.) — assign numeric indices
2. Audit all e3 sub-operations (register, unregister, list) — assign numeric indices
3. Update engine parser to resolve indexed sub-ops
4. Update LM entries with new indexed forms
5. Backward-compatible: word forms still work, indices are aliases

## Success Criteria

- Every e0/e3 sub-operation has a numeric index
- `e0.1` works the same as `e0 sweep` (etc.)
- LM entries updated with indexed forms
- Word forms remain as aliases for readability
