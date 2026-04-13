# Phase 2 Direction: codex-engine-v3-legendary-map

## Objective

Enrich LM entries with richer descriptions that include concrete examples and useful context — similar to the legend explanation block in `codex_legend.md`. The current entries are too terse (e.g., `lm1 navigate {coord}` with description "render primitive") to be immediately useful.

## Target Format

Current (too terse):
```
lm1   navigate     {coord}
```

Phase 2 (rich with examples):
```
lm1   navigate     {coord}  — t1 views task 1, d5 views decision 5, p2 views pipeline 2
```

## Requirements

1. **Enrich description fields** in `codex_lm_renderer.py` with concrete examples for key entries. Each description should show 2-3 real invocation examples that pattern-match immediately for an agent seeing the LM for the first time.

2. **Figure out what's most useful to add** — not every entry needs the same treatment. Some entries (navigate, edit-field, orchestrate) benefit from examples. Others (shell, anchor) may just need a clearer one-liner. Use judgment about which entries need enrichment and how much.

3. **Consider formatting** — if light formatting (em-dashes, parens, slashes) makes entries scan better, use it. But stay within the supermap's monospace tree aesthetic. No markdown links or multi-line descriptions.

4. **Respect the budget** — Phase 1 budget was ≤1KB for ~14-18 entries. Phase 2 can expand modestly (say ≤1.5KB) since the richer descriptions carry more orientation value per byte. But don't bloat — every byte here is injected every turn for every agent.

5. **Keep the abstract coordinate grammar** — use bare coordinates (`t1`, `d5`, `e1t3 status done`) not `R t1`. The LM describes the coordinate language itself; invocation wrappers are an implementation detail that codex-layer-v1 will eliminate.

6. **Workflow sub-entries** (`e0.l1`, `e1.l1` etc.) — these are already decent. If they can benefit from a brief concrete example too, do it; otherwise leave them.

## Files to Modify

- `scripts/codex_lm_renderer.py` — primary: update `_MODE_ENTRIES`, `_RENDER_VERBS`, `_TOOL_PATTERNS` description fields and any rendering logic for longer descriptions
- Verify output with `python3 scripts/codex_engine.py --supermap` after changes

## Success Criteria

An agent seeing the LM namespace for the first time should understand how to use every action from the entry alone, without needing to read the legend block or any other documentation.
