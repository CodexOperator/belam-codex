---
primitive: lesson
slug: diffentry-content-field-for-f-label-display
title: DiffEntry Content Field Required for F-Label Display
importance: 3
tags: [instance:main, render-engine, diff, implementation]
created: 2026-03-23
promotion_status: exploratory
doctrine_richness: 6
contradicts: []
---

# Lesson: DiffEntry Content Field Required for F-Label Display

## What Happened
Implementing R/F label split required that the render engine store file content at change-time, not just the coordinate/slug. Without the content field in DiffEntry, F-labels can't be produced later when the diff is served.

## The Pattern
`DiffEntry` now has a `content: str` field populated from the tree node at change time (`_on_file_change`). The `get_delta` / `get_delta_since` methods accept `include_content: bool` and format F-label blocks only when true:

```
F[m1]:
| ---
| title: test
| ---
| Body here
```

Content must be captured **at write time** because the tree may be updated or the file may change before the diff is served.

## Why It Matters
- Lazy content loading (reading file at serve time) risks stale or missing content
- Eager capture at change-time is consistent with the RAM-first philosophy
- Adds modest memory overhead per DiffEntry but entries are short-lived

## Related
- upstream: codex-engine-dense-alphanumeric-coordinate-grammar
- upstream: r-f-label-split-by-agent-role
