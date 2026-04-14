# TODO: align Hermes conversation extraction/consolidation with legacy OpenClaw behavior

Timestamp: 2026-04-14 UTC
Controller: Belam (Hermes)

## User goal
Check whether Hermes gateway still performs the old OpenClaw-style conversation consolidation on each new session:
- extract relevant lessons and decisions from the previous session
- produce a cleaned conversation artifact suitable for fine-tuning / training
- compare `.openclaw` vs `.hermes` directory and script behavior
- investigate discrepancies and bring them into alignment

## Initial answer from investigation
Probably not fully aligned yet.

The Hermes-side scripts were partially ported for flat `~/.hermes/sessions/*.jsonl`, but several pieces still look legacy-oriented or semantically mismatched.

## Directory/layout observations

### Legacy OpenClaw
- Session trees live under `~/.openclaw/agents/<agent>/sessions/`
- Agents include `architect`, `builder`, `critic`, `main`, `sage`, etc.

### Hermes
- Sessions live flat under `~/.hermes/sessions/*.jsonl`
- No per-agent directory split by default

This is the core structural change the extraction pipeline must account for.

## Script comparison findings

### 1) `parse_session_transcript.py`
Status: partially migrated, looks good.
- Hermes version adds `_extract_row()` to support both:
  - OpenClaw wrapper rows: `{type:"message", message:{...}}`
  - Hermes flat rows: `{role, content, timestamp}`
- Falls back to file stem as session id when Hermes rows lack a session header row

Implication:
- transcript parsing itself is mostly on the right path

### 2) `archive_session_transcript.py`
Status: partially migrated, but needs semantics review.
- Hermes version now points at `~/.hermes/sessions`
- It can list all flat session files when in Hermes mode
- But its agent/session model may still be shaped by old per-agent assumptions

Implication:
- likely usable, but should be reviewed end-to-end for Hermes session provenance and agent identity inference

### 3) `export_agent_conversations.py`
Status: suspicious / likely wrong in Hermes mode.
- In Hermes mode it loops over every `.jsonl` session file
- Then loops over every requested `agent_id`
- Then exports each session once per agent label

That means the same Hermes session can be duplicated and relabeled as architect/critic/builder even if it was not actually that agent.

Implication:
- cleaned conversation export for fine-tuning is likely misattributing or duplicating sessions under Hermes
- this is a major discrepancy

### 4) `extract_session_memory.sh`
Status: partially migrated, but still too coarse in Hermes mode.
- Hermes version prefers `~/.hermes/sessions/*.jsonl`
- `find_latest_session()` simply picks the newest Hermes session globally
- it does not appear to disambiguate by actual agent / instance in flat Hermes mode

Implication:
- extracting memories for `architect` / `builder` / `critic` may accidentally process the wrong session file
- main-session extraction may also race against unrelated Hermes sessions

### 5) `run_memory_extraction.py`
Status: only lightly migrated.
- Default workspace path changed to Hermes repo
- But the spawn path still says:
  - `openclaw agent --agent code-tutor ...`
- Docstring still references spawning via openclaw agent

Implication:
- orchestration-side extraction dispatch is not fully Hermes-native
- likely still relying on stale OpenClaw execution assumptions

### 6) `agent_memory_update.py`
Status: still legacy-oriented.
- `AGENT_WORKSPACES` are hardcoded to:
  - `~/.openclaw/workspace`
  - `~/.openclaw/workspace-architect`
  - `~/.openclaw/workspace-critic`
  - `~/.openclaw/workspace-builder`

Implication:
- per-agent memory logging is not aligned with Hermes workspace/session structure
- likely another discrepancy in end-to-end consolidation

### 7) `setup_memory_crons.py`
Status: functionally same, naming still legacy.
- cron ids/log paths still say `openclaw-*`
- not necessarily a blocker, but indicates migration incompleteness

## Architectural notes from project docs
- `MEMORY.md` says memory extraction is automatic on `/new` and `/reset`
- `decisions/auto-memory-extraction-architecture.md` describes a hook-based design:
  1. save session context
  2. resolve previous session file
  3. run extraction
  4. spawn sage in background
- `lessons/auto-memory-extraction-on-bootstrap.md` documents the intended behavior

So the intended architecture exists.
The question is whether the actual Hermes execution path still matches that design after flat-session migration.

## Most likely high-value discrepancies to fix
1. Hermes session selection must not be "latest global file wins"
2. Fine-tuning conversation export must not duplicate/mislabel flat Hermes sessions across multiple agent names
3. Extraction dispatch should be Hermes-native instead of `openclaw agent ...`
4. Agent memory update pathing should stop assuming `~/.openclaw/workspace-*`
5. Hook / bootstrap path should be validated end-to-end on actual Hermes new-session/reset events

## Suggested investigation steps for Codex
1. Read the scripts listed above and compare OpenClaw vs Hermes behavior directly
2. Trace how Hermes gateway/session reset currently exposes previous session metadata
3. Find where the hook or startup path resolves the previous session for extraction
4. Determine how agent identity should be inferred in flat Hermes sessions
5. Propose the minimal compatibility-preserving fix set
6. Ask Belam any needed clarifying questions before editing
7. If editing symbols, follow AGENTS.md and run GitNexus impact first

## Questions Codex should ask if unclear
1. In Hermes flat-session mode, should extraction target only the immediately previous session for the same chat/session thread, or should it infer specific sub-agent sessions too?
2. For fine-tuning export, should Hermes sessions be exported once per actual session only, or still grouped into pseudo-agent buckets when provenance exists in-message?
3. Should `run_memory_extraction.py` be migrated fully to Hermes-native agent/subagent invocation now, or only fixed up to produce correct prompts/files while preserving current spawn behavior?

## Files to inspect first
- `scripts/parse_session_transcript.py`
- `scripts/archive_session_transcript.py`
- `scripts/export_agent_conversations.py`
- `scripts/extract_session_memory.sh`
- `scripts/run_memory_extraction.py`
- `scripts/agent_memory_update.py`
- any memory-extraction hook under `hooks/`
- Hermes gateway/session handling if needed for previous-session resolution
