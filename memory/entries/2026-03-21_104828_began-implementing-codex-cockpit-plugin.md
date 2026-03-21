---
primitive: memory_log
timestamp: "2026-03-21T10:48:28Z"
category: technical
importance: 4
tags: [instance:main, codex-cockpit, before_prompt_build, openclaw-plugin, supermap]
source: "session"
content: "Began implementing codex-cockpit plugin (before_prompt_build hook) to inject supermap on every agent turn. Prior supermap-boot hook only fires on agent:bootstrap, leaving the agent blind to state changes mid-session. New plugin scaffolded at /home/ubuntu/.openclaw/extensions/codex-cockpit/ with openclaw.plugin.json + index.ts. First load attempt failed: TypeError: (0, _core.definePluginEntry) is not a function. Investigation of stock plugin imports revealed correct SDK import path pattern. Session transcript truncated — work likely continued past this point."
status: active
---

# Memory Entry

**2026-03-21T10:48:28Z** · `technical` · importance 4/5

Began implementing codex-cockpit plugin (before_prompt_build hook) to inject supermap on every agent turn. Prior supermap-boot hook only fires on agent:bootstrap, leaving the agent blind to state changes mid-session. New plugin scaffolded at /home/ubuntu/.openclaw/extensions/codex-cockpit/ with openclaw.plugin.json + index.ts. First load attempt failed: TypeError: (0, _core.definePluginEntry) is not a function. Investigation of stock plugin imports revealed correct SDK import path pattern. Session transcript truncated — work likely continued past this point.

---
*Source: session*
*Tags: instance:main, codex-cockpit, before_prompt_build, openclaw-plugin, supermap*
