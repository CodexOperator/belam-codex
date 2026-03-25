---
primitive: memory_log
timestamp: "2026-03-25T01:37:57Z"
category: technical
importance: 4
tags: [instance:main, codex-engine, render-engine, infrastructure, simplification]
source: "session"
content: "Render engine daemon (codex_render.py) was retired and archived to scripts/archived/. Cockpit plugin upgraded to V10: now calls render_supermap.py directly (no daemon, no UDS socket), supermap rendered on-demand per turn and returned via stdout. systemd codex-render.service disabled. All codex_render imports in codex_engine.py, orchestration_engine.py stubbed/removed. r0 coordinate added as manual supermap refresh in both cockpit and CLI. Namespace discovery via _scan_namespaces() auto-detects new directories with .namespace marker files on each render."
status: active
---

# Memory Entry

**2026-03-25T01:37:57Z** · `technical` · importance 4/5

Render engine daemon (codex_render.py) was retired and archived to scripts/archived/. Cockpit plugin upgraded to V10: now calls render_supermap.py directly (no daemon, no UDS socket), supermap rendered on-demand per turn and returned via stdout. systemd codex-render.service disabled. All codex_render imports in codex_engine.py, orchestration_engine.py stubbed/removed. r0 coordinate added as manual supermap refresh in both cockpit and CLI. Namespace discovery via _scan_namespaces() auto-detects new directories with .namespace marker files on each render.

---
*Source: session*
*Tags: instance:main, codex-engine, render-engine, infrastructure, simplification*
