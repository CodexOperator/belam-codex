---
primitive: memory_log
timestamp: "2026-03-24T06:28:23Z"
category: technical
importance: 4
tags: [instance:main, cockpit, supermap, plugin, diagnosis]
source: "session"
content: "Shael asked why supermap/legend weren't injecting into context despite cockpit plugin appearing to load. Coordinate Mode scaffold showed up (baked into system prompt template) but no supermap tree or legend. Diagnosis revealed two issues: (1) session_reset is not a valid plugin hook — OpenClaw logged 'unknown typed hook session_reset ignored'; (2) before_prompt_build is gated behind hooks.allowPromptInjection: true in plugin config entry — without it, the hook fires but its prependSystemContext return is silently dropped. Fix: add allowPromptInjection: true to plugins.entries.codex-cockpit config. Also discovered V7 cockpit plugin was in extensions dir while workspace still had V6."
status: active
---

# Memory Entry

**2026-03-24T06:28:23Z** · `technical` · importance 4/5

Shael asked why supermap/legend weren't injecting into context despite cockpit plugin appearing to load. Coordinate Mode scaffold showed up (baked into system prompt template) but no supermap tree or legend. Diagnosis revealed two issues: (1) session_reset is not a valid plugin hook — OpenClaw logged 'unknown typed hook session_reset ignored'; (2) before_prompt_build is gated behind hooks.allowPromptInjection: true in plugin config entry — without it, the hook fires but its prependSystemContext return is silently dropped. Fix: add allowPromptInjection: true to plugins.entries.codex-cockpit config. Also discovered V7 cockpit plugin was in extensions dir while workspace still had V6.

---
*Source: session*
*Tags: instance:main, cockpit, supermap, plugin, diagnosis*
