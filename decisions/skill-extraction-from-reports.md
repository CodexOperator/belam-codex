---
primitive: decision
status: accepted
date: 2026-03-15
context: How to make domain knowledge available to all agents
alternatives: [inline in AGENT_SOUL.md, separate knowledge files only, OpenClaw skills]
rationale: Skills are the right abstraction — they're discoverable by any agent, loaded on-demand via progressive disclosure, and shareable across OpenClaw instances. Knowledge files give role-specific depth. Skills give cross-cutting domain access. Both are needed.
consequences: [New domain reports → extract into skills + agent knowledge files, Skills symlinked to ~/.openclaw/skills/ for discovery, Reference files for deep detail keep SKILL.md lean]
project: quant-knowledge-skills
tags: [skills, knowledge, workflow]
promotion_status: exploratory
doctrine_richness: 0
contradicts: []
---

# Extract Domain Reports Into Skills + Knowledge Files

When ingesting domain knowledge:
1. **Agent knowledge files** → role-specific extracts (architect/critic/builder perspectives)
2. **Skills** → cross-cutting domain knowledge callable by any agent
3. **Reference files** → deep detail loaded on-demand (calibration patterns, compute specs)

Skills use progressive disclosure: description triggers loading, SKILL.md gives overview, references/ gives depth.
