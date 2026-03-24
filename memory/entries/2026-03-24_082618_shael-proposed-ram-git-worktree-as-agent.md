---
primitive: memory_log
timestamp: "2026-03-24T08:26:18Z"
category: insight
importance: 5
tags: [instance:main, codex-engine, v4, ram, git, architecture, insight]
source: "session"
content: "Shael proposed RAM git worktree as agent filesystem 2026-03-24 ~07:14 UTC. Agents write to symlinked dirs that resolve to /dev/shm git repo. Every write auto-commits, giving atomic diffs, blame, revert. Render engine reads git diff directly instead of inotify queue. Background sync daemon persists RAM->disk. Agent isolation via branches possible. Turn boundary = commit boundary, enabling undo."
status: consolidated
---

# Memory Entry

**2026-03-24T08:26:18Z** · `insight` · importance 5/5

Shael proposed RAM git worktree as agent filesystem 2026-03-24 ~07:14 UTC. Agents write to symlinked dirs that resolve to /dev/shm git repo. Every write auto-commits, giving atomic diffs, blame, revert. Render engine reads git diff directly instead of inotify queue. Background sync daemon persists RAM->disk. Agent isolation via branches possible. Turn boundary = commit boundary, enabling undo.

---
*Source: session*
*Tags: instance:main, codex-engine, v4, ram, git, architecture, insight*
