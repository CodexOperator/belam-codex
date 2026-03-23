---
primitive: command
command: "R audit"
aliases: ["R au"]
description: "Scan all primitives for consistency issues (orphaned commands, stale refs, missing decisions, duplicates)"
category: primitives
tags: [audit, primitives, consistency, maintenance]
---

# R audit

Scans all workspace primitives for consistency issues. Keeps the primitive system coherent as it grows.

## Usage

```bash
R audit                    # Run all checks, report issues
R audit --fix              # Auto-fix where possible
R audit --verbose          # Show passing checks too
R audit --quiet            # Summary line only
R audit --check commands   # Run specific check only
R audit --check skills
R audit --check cross-refs
R audit --check decisions
R audit --check duplicates
```

## Checks Performed

1. **Commands without skill references** — each `commands/*.md` should be mentioned in at least one `skills/*/SKILL.md`
2. **Skills with stale command lists** — `R X` references in SKILL.md files that have no matching `commands/X.md`
3. **Cross-reference integrity** — `skill:` frontmatter fields pointing to non-existent skills
4. **Decision primitives for every skill** — every `skills/*/` should have a `decisions/*.md` with `skill: <name>`
5. **Duplicate descriptions** — similar primitive names that might be accidental duplicates

## Auto-fix Mode (`--fix`)

- **Orphaned commands** → appends a reference to the best-matching skill's SKILL.md (matched by tag overlap)
- **Missing command stubs** → creates a stub `commands/*.md` for commands referenced in skills but not yet created

## Exit Codes

- `0` — no issues found
- `1` — one or more issues found

## Related

- `commands/create.md` — creates new primitives (with auto-linking)
- `commands/embed-primitives.md` — regenerates the primitive index
- `scripts/audit_primitives.py` — underlying script
