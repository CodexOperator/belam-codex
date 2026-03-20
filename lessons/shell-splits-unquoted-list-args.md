---
primitive: lesson
date: 2026-03-20
source: session — belam edit --set with list values broke on spaces
confidence: high
upstream: [decision/indexed-command-interface]
downstream: []
tags: [infrastructure, cli, debugging, belam, argparse]
---

# Shell Splits Unquoted List Arguments

## Context

`belam edit` uses `--set key=value` for frontmatter updates. List fields like `downstream=[lesson/foo, memory/bar]` contain spaces inside brackets.

## What Happened

`belam edit primitive --set downstream=[a, b]` failed with argparse seeing `b]` as an unrecognized positional argument. The shell splits on the space between `a,` and `b]`, turning one argument into two. The error was opaque — argparse complained about extra arguments, not about malformed lists.

## Lesson

**Any CLI that accepts structured values (lists, JSON, YAML) as arguments must defend against shell word-splitting.** Don't rely on users quoting correctly — pre-process argv to rejoin split tokens.

## Application

- Fixed in `edit_primitive.py` with `_rejoin_list_args()` — detects unclosed `[` and consumes tokens until `]`
- Any future CLI that accepts list/structured `--set` values should use the same pattern
- Same class of bug applies to JSON values, paths with spaces, or any value containing shell metacharacters
- Test CLI tools with unquoted complex values, not just simple ones
