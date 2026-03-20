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

WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"
AGENTS_DIR="${AGENTS_DIR:-$HOME/.openclaw/agents}"
SCRIPTS_DIR="$WORKSPACE/scripts"

# --- Defaults ---
INSTANCE="main"
SESSION_FILE=""
PERSONA=""
DRY_RUN=false

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --instance NAME    Agent instance (default: main)
  --session-file F   Specific JSONL to process (default: auto-detect latest)
  --persona NAME     Optional persona tag (architect/critic/builder/etc)
  --dry-run          Parse transcript only, don't build extraction prompt
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
    -h|--help)     usage ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# --- Find latest completed session ---
find_latest_session() {
  local sessions_dir="$AGENTS_DIR/$INSTANCE/sessions"
  [[ -d "$sessions_dir" ]] || { echo "ERROR: No sessions dir for '$INSTANCE'" >&2; return 1; }
  
  local latest
  latest=$(ls -t "$sessions_dir"/*.jsonl.reset.* "$sessions_dir"/*.jsonl.deleted.* 2>/dev/null | head -1)
  [[ -n "$latest" ]] || { echo "ERROR: No completed sessions for '$INSTANCE'" >&2; return 1; }
  echo "$latest"
}

# --- Create tracking primitive ---
create_tracker() {
  local status="$1"
  local now
  now=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
  mkdir -p "$WORKSPACE/memory"
  cat > "$WORKSPACE/memory/pending_extraction.json" <<JSON
{
  "instance": "$INSTANCE",
  "session": "$SESSION_ID",
  "promptFile": "$PROMPT_FILE",
  "transcriptFile": "$TRANSCRIPT_FILE",
  "exchangeCount": $EXCHANGE_COUNT,
  "status": "$status",
  "createdAt": "$now"
}
JSON
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
TRANSCRIPT_FILE="/tmp/session_transcript_${INSTANCE}_${SESSION_ID}.md"
python3 "$SCRIPTS_DIR/parse_session_transcript.py" \
  "$SESSION_FILE" "$TRANSCRIPT_FILE" \
  --instance "$INSTANCE" \
  --persona "${PERSONA:-}"

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

cat > "$PROMPT_FILE" <<PROMPT
You are a memory extraction agent. Read the session transcript below and create structured primitives.

## Context
- **Instance:** $INSTANCE
- **Persona:** ${PERSONA:-none}
- **Date:** $TODAY

## Instructions

1. Read the transcript and identify:
   - **Memories** (events, context, what happened) → use \`python3 scripts/log_memory.py\`
   - **Lessons** (reusable knowledge, gotchas, patterns) → use \`python3 scripts/create_primitive.py lesson <slug>\`
   - **Decisions** (architectural choices with rationale) → use \`python3 scripts/create_primitive.py decision <slug>\`

2. For each primitive:
   - Assess importance (1-5 stars via --importance flag)
   - Add tags: \`instance:$INSTANCE\` on everything
$PERSONA_TAG
   - Add upstream/downstream edges if relationships to existing primitives are obvious

3. For trivial sessions (quick checks, no real work), create ONE memory with importance 1

4. Append a summary to the daily memory log:
   - File: \`memory/$TODAY.md\`
   - If it exists, append. If not, create with \`# Memory Log — $TODAY\` header

5. After all primitives are created:
   \`\`\`bash
   cd $WORKSPACE && git add -A && git diff --cached --stat
   # If changes exist:
   git commit -m "Auto-extract: $INSTANCE session memories [$TODAY]" && git push origin
   \`\`\`

6. Update the tracker: write \`complete\` status to \`memory/pending_extraction.json\`

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
