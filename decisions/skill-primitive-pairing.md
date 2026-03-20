---
primitive: decision
status: accepted
date: 2026-03-18
context: "Skills document HOW to use tools/knowledge, but not WHY they exist or what architectural choices they encode. Without a primitive, the rationale behind a skill is lost when context rotates."
alternatives:
  - "Skills are self-documenting (they're not — SKILL.md is usage-focused)"
  - "Rationale lives only in memory (decays, not discoverable by other agents)"
  - "Every skill gets a decision primitive with skill: cross-reference (chosen)"
rationale: "Skills and primitives serve complementary roles. SKILL.md is the HOW — commands, patterns, usage. The primitive is the WHY — architectural rationale, alternatives rejected, consequences accepted. Pairing them ensures agents can both USE a skill and UNDERSTAND it."
consequences:
  - "Every new skill MUST have a corresponding decision primitive created alongside it"
  - "Primitive frontmatter includes skill: field for cross-referencing"
  - "Naming: {skill-name}-skill.md for dedicated primitives, or reuse existing decisions that naturally map"
  - "Existing skills without primitives should be backfilled"
project: workspace-conventions
tags: [skills, primitives, conventions, knowledge-management]
downstream: [memory/2026-03-18_192651_convention-established-every-workspace-s]
---

# Decision: Every Skill Gets a Primitive

## Convention

| File | Purpose | Audience |
|------|---------|----------|
| `skills/{name}/SKILL.md` | HOW — commands, patterns, usage reference | Agents doing the work |
| `decisions/{name}-skill.md` | WHY — rationale, alternatives, consequences | Agents making architectural choices |

## Cross-Reference

Primitive frontmatter includes `skill: {name}` so `grep -rl "skill: {name}" decisions/` finds the rationale for any skill.

## When Creating a New Skill

1. Create `skills/{name}/SKILL.md` with usage content
2. Create `decisions/{name}-skill.md` (or identify existing decision that maps)
3. Add `skill: {name}` to the primitive's frontmatter
4. Verify: `grep "skill: {name}" decisions/*.md` returns a hit

## Current Mapping

Maintained via: `for s in skills/*/; do n=$(basename "$s"); grep -rl "skill: $n" decisions/*.md; done`
