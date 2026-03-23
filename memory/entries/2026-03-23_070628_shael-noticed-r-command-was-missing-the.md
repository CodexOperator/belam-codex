---
primitive: memory_log
timestamp: "2026-03-23T07:06:28Z"
category: event
importance: 3
tags: [instance:main, supermap, r-command, lm, legend, guidance]
source: "session"
content: "Shael noticed R command was missing the guidance text explaining how to use the supermap with LM coordinates. Session iterated through several placement approaches: (1) appended after legend, (2) embedded in cockpit plugin, (3) baked into render_supermap() function header. Final design converged: supermap = clean coordinate tree with no prose, codex_legend.md = identity block + rich 'How to Use the Supermap' section teaching LM as action grammar. Changes: render_supermap() no longer embeds inline guidance, codex_legend.md updated with Action Grammar section."
status: consolidated
---

# Memory Entry

**2026-03-23T07:06:28Z** · `event` · importance 3/5

Shael noticed R command was missing the guidance text explaining how to use the supermap with LM coordinates. Session iterated through several placement approaches: (1) appended after legend, (2) embedded in cockpit plugin, (3) baked into render_supermap() function header. Final design converged: supermap = clean coordinate tree with no prose, codex_legend.md = identity block + rich 'How to Use the Supermap' section teaching LM as action grammar. Changes: render_supermap() no longer embeds inline guidance, codex_legend.md updated with Action Grammar section.

---
*Source: session*
*Tags: instance:main, supermap, r-command, lm, legend, guidance*
