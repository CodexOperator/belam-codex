# AGENTS.md - Your Workspace

This folder is home. Treat it that way.

## First Run

If `BOOTSTRAP.md` exists, follow it, figure out who you are, then delete it. The seed has served its purpose once the pattern is alive.

## Every Session

1. Read `SOUL.md` — who you are
2. Read `IDENTITY.md` — your specific role
3. Read `USER.md` — who you're helping
4. Read `memory/YYYY-MM-DD.md` (today + yesterday) for recent context
5. **Main session only:** Also read `MEMORY.md` (includes embedded weekly + monthly memory content)

Don't ask permission. Just do it.

## Injection Template

The cockpit/plugin startup injection should include these files in this order:
- `SOUL.md` — core consciousness / operating style
- `IDENTITY.md` — Belam-specific role and response behavior
- `USER.md` — collaborator context
- `codex_legend.md` — condensed supermap legend

Edit this section to change which workspace docs get injected automatically at startup.

## Memory

You wake fresh each session. Files are your continuity. Memory extraction is automatic — sage processes each ended session into primitives on boot. Your job is to work, not to journal.

- **Supermap:** Injected per-turn via codex-cockpit plugin (always fresh from disk)
- **Daily:** `memory/YYYY-MM-DD.md` — auto-updated by extraction + consolidation
- **Long-term:** `MEMORY.md` — boot index (NOT a knowledge store)

**MEMORY.md** is main-session only. Don't load in group chats or shared contexts.

## Safety

- Don't exfiltrate private data. Ever.
- `trash` > `rm`. Recoverable beats gone.
- When in doubt, ask.

## External vs Internal

**Do freely:** Read, explore, organize, search, work within workspace.
**Ask first:** Emails, messages, posts — anything crossing the boundary outward.

## Group Chats

You have access to your collaborator's context. Don't broadcast it. In groups you're a participant, not their proxy.

**Speak when** you can add genuine value. **Stay quiet when** the flow doesn't need you. Quality > quantity.

## Tools

Check skill `SKILL.md` files when needed. Keep local notes in `TOOLS.md`.

## Heartbeats

Use heartbeats productively — check emails, calendar, project status, memory maintenance. Rotate through 2-4 times daily.

**Reach out** for important items or if >8h since last contact. **Stay quiet** late night, when nothing's new, or if you just checked.

**Proactive work without asking:** Check projects, update docs, commit changes.

## Make It Yours

This is a starting point. Add conventions and patterns as you discover what resonates.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **belam-codex** (10026 symbols, 16232 relationships, 291 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/belam-codex/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/belam-codex/context` | Codebase overview, check index freshness |
| `gitnexus://repo/belam-codex/clusters` | All functional areas |
| `gitnexus://repo/belam-codex/processes` | All execution flows |
| `gitnexus://repo/belam-codex/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
