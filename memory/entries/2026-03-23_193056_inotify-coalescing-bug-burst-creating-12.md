---
primitive: memory_log
timestamp: "2026-03-23T19:30:56Z"
category: technical
importance: 4
tags: [instance:main, render-engine, inotify, debugging, codex-engine-v4]
source: "session"
content: "Inotify coalescing bug: burst-creating 12 test primitives triggered _reindex_single_new 12 times — only 1 DiffEntry returned. Root causes: (1) filepath_to_coord lookup failed due to relative vs absolute path mismatch in live engine, (2) repeated reindexes fought each other. Fix: make _reindex_single_new return all new files in one pass; track already-diffed files to skip redundant reindexes; update apply_disk_change return type from DiffEntry|None to list[DiffEntry]."
status: consolidated
---

# Memory Entry

**2026-03-23T19:30:56Z** · `technical` · importance 4/5

Inotify coalescing bug: burst-creating 12 test primitives triggered _reindex_single_new 12 times — only 1 DiffEntry returned. Root causes: (1) filepath_to_coord lookup failed due to relative vs absolute path mismatch in live engine, (2) repeated reindexes fought each other. Fix: make _reindex_single_new return all new files in one pass; track already-diffed files to skip redundant reindexes; update apply_disk_change return type from DiffEntry|None to list[DiffEntry].

---
*Source: session*
*Tags: instance:main, render-engine, inotify, debugging, codex-engine-v4*
