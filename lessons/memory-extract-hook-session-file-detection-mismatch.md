---
primitive: lesson
date: 2026-04-15
source: session 20260415_075110_a6b97fd9
confidence: high
upstream: [auto-memory-extraction-on-bootstrap, auto-memory-extraction-architecture]
downstream: []
tags: [instance:main, hooks, memory-extract, session-files, openclaw, migration]
promotion_status: candidate
doctrine_richness: 5
contradicts: []
importance: 3
---

# memory-extract-hook-session-file-detection-mismatch

## Context

After migrating from Hermes to OpenClaw, the automatic memory extraction hook stopped firing. Manual extraction (bash script + python wrapper) still worked, but the auto-trigger on new session start was broken.

## What Happened

Traced the full extraction trigger path:
1. `hooks/memory-extract/handler.ts` — OpenClaw plugin hook that fires on session `new` event
2. It reads session files from a sessions directory and spawns sage for extraction
3. Post-migration, the handler's session directory detection and workspace path resolution drifted — `logs/memory-extract.log` showed last successful hook fire was 2026-04-13, with no fires for 2026-04-14 or 2026-04-15 sessions
4. `memory/pending_extraction.json` only had completion records through the 2026-04-13 sessions
5. The handler.ts relied on paths like `HERMES_SESSIONS_DIR` and workspace env vars that weren't consistently set in the OpenClaw runtime

## Lesson

**When migrating between agent runtimes (Hermes → OpenClaw), hook handlers that depend on session directory paths and env vars break silently** — they don't error visibly, they just stop finding session files. Always verify the auto-trigger fires end-to-end after any runtime migration, not just that the extraction logic itself works.

## Application

- After any runtime/platform migration, run a focused end-to-end test of the hook trigger path (not just the extraction script)
- Check `logs/memory-extract.log` timestamps to verify hooks are actually firing
- Ensure env vars (`WORKSPACE`, `BELAM_WORKSPACE`, `OPENCLAW_WORKSPACE`, session dirs) are set correctly in the new runtime's hook execution context
- The handler.ts needs to resolve session directories using the same fallback chain as other scripts: OpenClaw workspace → Hermes workspace → env vars
