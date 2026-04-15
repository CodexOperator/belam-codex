#!/usr/bin/env bash
# extract_session_memory.sh — Parse a completed session and prepare memory extraction
#
# Entry points:
#   1. Bootstrap hook (agent:bootstrap) — processes the just-ended session
#   2. Orchestrator handoff — processes sub-agent session at handoff time
#   3. Manual: bash scripts/extract_session_memory.sh [--instance main]
#
# Flow:
#   1. Find latest completed session JSONL for the instance
#   2. Parse it into readable transcript (bash+python — clock cycles, zero tokens)
#   3. Build extraction prompt for subagent
#   4. Output file paths for the caller to use
#
# Design principle: clock cycles > tokens. All deterministic work here.

set -euo pipefail

WORKSPACE="${WORKSPACE:-$HOME/.hermes/belam-codex}"
AGENTS_DIR="${AGENTS_DIR:-$HOME/.openclaw/agents}"
HERMES_SESSIONS_DIR="${HERMES_SESSIONS_DIR:-$HOME/.hermes/sessions}"
SCRIPTS_DIR="$WORKSPACE/scripts"

# --- Defaults ---
INSTANCE="main"
SESSION_FILE=""
PERSONA=""
DRY_RUN=false
TEST_MODE=false

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --instance NAME    Agent instance (default: main)
  --session-file F   Specific JSONL to process (default: auto-detect latest)
  --persona NAME     Optional persona tag (architect/critic/builder/etc)
  --dry-run          Parse transcript only, don't build extraction prompt
  --test             Test mode: write all output to memory/test-extract/ (no duplicates)
  -h, --help         Show this help
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --instance)    INSTANCE="$2"; shift 2 ;;
    --session-file) SESSION_FILE="$2"; shift 2 ;;
    --persona)     PERSONA="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=true; shift ;;
    --test)        TEST_MODE=true; shift ;;
    -h|--help)     usage ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# --- Find latest completed session ---
find_latest_session() {
  local sessions_dir="$AGENTS_DIR/$INSTANCE/sessions"

  # Preferred path for Hermes: ~/.hermes/sessions/*.jsonl
  if [[ -d "$HERMES_SESSIONS_DIR" ]]; then
    local latest_hermes
    latest_hermes=$(ls -t "$HERMES_SESSIONS_DIR"/*.jsonl 2>/dev/null | head -1 || true)
    if [[ -n "$latest_hermes" ]]; then
      echo "$latest_hermes"
      return 0
    fi
  fi

  # Legacy OpenClaw path fallback
  [[ -d "$sessions_dir" ]] || { echo "ERROR: No sessions dir for '$INSTANCE'" >&2; return 1; }

  local latest
  latest=$(ls -t "$sessions_dir"/*.jsonl.reset.* "$sessions_dir"/*.jsonl.deleted.* "$sessions_dir"/*.jsonl 2>/dev/null | head -1)
  [[ -n "$latest" ]] || { echo "ERROR: No completed sessions for '$INSTANCE'" >&2; return 1; }
  echo "$latest"
}

# ============================================================
# MAIN
# ============================================================

# Step 1: Find the session file
if [[ -z "$SESSION_FILE" ]]; then
  SESSION_FILE=$(find_latest_session) || exit 1
fi
[[ -f "$SESSION_FILE" ]] || { echo "ERROR: File not found: $SESSION_FILE" >&2; exit 1; }

SESSION_ID=$(basename "$SESSION_FILE" | sed 's/\.jsonl.*//')
echo "📋 Processing session: $SESSION_ID (instance: $INSTANCE)"

# Step 2: Parse to readable transcript
if [[ "$TEST_MODE" == "true" ]]; then
  mkdir -p "$WORKSPACE/memory/test-extract"
  TRANSCRIPT_FILE="$WORKSPACE/memory/test-extract/transcript.md"
  TEST_FLAG="--test"
else
  TRANSCRIPT_FILE="/tmp/session_transcript_${INSTANCE}_${SESSION_ID}.md"
  TEST_FLAG=""
fi
python3 "$SCRIPTS_DIR/parse_session_transcript.py" \
  "$SESSION_FILE" "$TRANSCRIPT_FILE" \
  --instance "$INSTANCE" \
  --persona "${PERSONA:-}" \
  ${TEST_FLAG:+"$TEST_FLAG"}

# Step 3: Count exchanges
EXCHANGE_COUNT=$(grep -c '### 🧑 User' "$TRANSCRIPT_FILE" 2>/dev/null || echo "0")
echo "   Exchanges: $EXCHANGE_COUNT"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "DRY RUN — transcript at: $TRANSCRIPT_FILE"
  head -50 "$TRANSCRIPT_FILE"
  exit 0
fi

# Step 4: Build extraction prompt
TODAY=$(date -u +%Y-%m-%d)
PROMPT_FILE="/tmp/session_extract_prompt_${INSTANCE}_${SESSION_ID}.md"

PERSONA_TAG=""
[[ -n "${PERSONA:-}" ]] && PERSONA_TAG="   - \`persona:$PERSONA\` on every primitive"

# Test mode overrides output directories to avoid duplicates
TEST_MODE_BLOCK=""
if [[ "$TEST_MODE" == "true" ]]; then
  TEST_MODE_BLOCK="
## ⚠️ TEST MODE
Write all memories to \`memory/test-extract/\` instead of normal directories. Create the directory if needed.
Do NOT write to \`memory/$TODAY.md\` or any normal primitive directories.
"
fi

# Step 4b: Gather existing entries for dedup context
EXISTING_ENTRIES=""
EXISTING_COUNT=0
if ls "$WORKSPACE/memory/entries/${TODAY}"_*.md >/dev/null 2>&1; then
  EXISTING_COUNT=$(ls "$WORKSPACE/memory/entries/${TODAY}"_*.md 2>/dev/null | wc -l)
  EXISTING_ENTRIES=$(for f in "$WORKSPACE/memory/entries/${TODAY}"_*.md; do
    slug=$(basename "$f" .md | sed "s/^${TODAY}_[0-9]*_//")
    firstline=$(grep -m1 "^[^-#]" "$f" 2>/dev/null | head -c 120 || true)
    echo "  - [memory] $slug: $firstline"
  done)
fi

# Also gather existing lessons and decisions (these don't have date prefixes)
EXISTING_LESSONS=""
LESSON_COUNT=0
if ls "$WORKSPACE/lessons/"*.md >/dev/null 2>&1; then
  LESSON_COUNT=$(ls "$WORKSPACE/lessons/"*.md 2>/dev/null | wc -l)
  EXISTING_LESSONS=$(for f in "$WORKSPACE/lessons/"*.md; do
    slug=$(basename "$f" .md)
    echo "  - [lesson] $slug"
  done)
fi

EXISTING_DECISIONS=""
DECISION_COUNT=0
if ls "$WORKSPACE/decisions/"*.md >/dev/null 2>&1; then
  DECISION_COUNT=$(ls "$WORKSPACE/decisions/"*.md 2>/dev/null | wc -l)
  EXISTING_DECISIONS=$(for f in "$WORKSPACE/decisions/"*.md; do
    slug=$(basename "$f" .md)
    echo "  - [decision] $slug"
  done)
fi

TOTAL_EXISTING=$((EXISTING_COUNT + LESSON_COUNT + DECISION_COUNT))
echo "   Existing today: $EXISTING_COUNT memories, $LESSON_COUNT lessons, $DECISION_COUNT decisions"

DEDUP_BLOCK=""
if [[ $TOTAL_EXISTING -gt 0 ]]; then
  DEDUP_BLOCK="
## Already Logged ($TOTAL_EXISTING primitives)
The following memories/lessons/decisions already exist. **Do NOT create duplicates.**
If the session covers the same topic as an existing entry, skip it or only add genuinely new information.

$EXISTING_ENTRIES
$EXISTING_LESSONS
$EXISTING_DECISIONS
"
fi

cat > "$PROMPT_FILE" <<PROMPT
You are a memory extraction agent. Read the session transcript below and create structured primitives.
${TEST_MODE_BLOCK}
${DEDUP_BLOCK}
## Context
- **Instance:** $INSTANCE
- **Persona:** ${PERSONA:-none}
- **Date:** $TODAY

## Instructions

1. Read the transcript and extract ONLY:
   - **Lessons** (reusable knowledge, gotchas, patterns) → use \`python3 scripts/create_primitive.py lesson <slug>\`
   - **Decisions** (architectural choices with rationale) → use \`python3 scripts/create_primitive.py decision <slug>\`

2. **DO NOT create memory entries.** No events, no context logs, no "what happened" entries.
   Specifically DO NOT log:
   - Pipeline or task state transitions (stage changes, dispatches, completions, archives)
   - Routine operations (git commits, memory consolidation, heartbeat runs)
   - Session summaries or cross-agent status reports
   - Live project status or progress snapshots (e.g. "3 of 5 components done", "script at 291 lines")
   - Implementation details mid-build (file lists, line counts, function names written)
   - Anything that is already captured in pipeline/task files on disk

3. Only create a primitive when there is a genuinely reusable lesson or a meaningful architectural decision.
   If the session contains no lessons or decisions, create nothing — that's fine.

4. For each primitive:
   - Assess importance (1-5 stars via --importance flag)
   - Add tags: \`instance:$INSTANCE\` on everything
$PERSONA_TAG
   - Add upstream/downstream edges if relationships to existing primitives are obvious
   - **Check the "Already Logged Today" section above** — skip entries that duplicate existing ones

5. For trivial sessions (quick checks, no real work), create NOTHING

6. Append a ONE-LINE summary to the daily memory log (only if you created any primitives):
   - File: \`memory/$TODAY.md\`
   - If it exists, append. If not, create with \`# Memory Log — $TODAY\` header
   - Format: \`## Session $INSTANCE — $TODAY\` followed by a single line listing which lessons/decisions were created
   - Do NOT write full session summaries, cross-agent reports, stage-by-stage narratives, or project status updates
   - The daily log is a PRIMITIVE INDEX, not a journal — just list what was created, nothing more

7. After all primitives are created:
   \`\`\`bash
   cd $WORKSPACE && git add -A && git diff --cached --stat
   # If changes exist:
   git commit -m "Auto-extract: $INSTANCE session lessons/decisions [$TODAY]" && git push origin
   \`\`\`

8. Finalize extraction bookkeeping with the hardcoded script below. Do NOT edit
   \`memory/pending_extraction.json\` manually.
   - Success with primitives:
     \`python3 scripts/finalize_memory_extraction.py --session-id "$SESSION_ID" --status complete --primitive "<path-or-slug-1>" --primitive "<path-or-slug-2>"\`
   - Success with no primitives:
     \`python3 scripts/finalize_memory_extraction.py --session-id "$SESSION_ID" --status complete\`
     This must result in \`primitives: []\`.
   - Actual extraction failure:
     \`python3 scripts/finalize_memory_extraction.py --session-id "$SESSION_ID" --status error --details "<short reason>"\`
   - Run exactly one finalizer command before exiting.

## Star Ratings
- ★☆☆☆☆ = trivial/routine (status check, greeting)
- ★★☆☆☆ = minor context
- ★★★☆☆ = significant work completed
- ★★★★☆ = important insight or decision
- ★★★★★ = architectural or paradigm shift

## Transcript

$(cat "$TRANSCRIPT_FILE")
PROMPT

PROMPT_SIZE=$(wc -c < "$PROMPT_FILE")
echo "   Prompt: ${PROMPT_SIZE} bytes"

# Step 5: Output results for caller
echo "PROMPT_FILE=$PROMPT_FILE"
echo "TRANSCRIPT_FILE=$TRANSCRIPT_FILE"
echo "SESSION_ID=$SESSION_ID"
echo "EXCHANGE_COUNT=$EXCHANGE_COUNT"
