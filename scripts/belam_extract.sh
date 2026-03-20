#!/usr/bin/env bash
# belam_extract.sh — Wrapper for manual memory extraction
# Usage: bash scripts/belam_extract.sh [instance]
#
# Steps:
#   1. Run extract_session_memory.sh to prepare the prompt file
#   2. Read the PROMPT_FILE from its output
#   3. Spawn the sage agent with that prompt in an isolated session

set -euo pipefail

WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
SCRIPTS="$WORKSPACE/scripts"

INSTANCE="${1:-main}"
EXTRACT_SCRIPT="$SCRIPTS/extract_session_memory.sh"

echo "🧠 belam extract — instance: $INSTANCE"

# Check that the extraction script exists
if [ ! -f "$EXTRACT_SCRIPT" ]; then
    echo "⚠️  extract_session_memory.sh not found at $EXTRACT_SCRIPT"
    echo "   Memory extraction script is not yet installed."
    exit 1
fi

# Run the extraction prep script; it should export or echo PROMPT_FILE path
EXTRACT_OUTPUT=$(bash "$EXTRACT_SCRIPT" --instance "$INSTANCE" 2>&1) || {
    exit_code=$?
    echo "⚠️  extract_session_memory.sh exited with code $exit_code"
    echo "$EXTRACT_OUTPUT"
    # Graceful: no session found is not fatal
    if echo "$EXTRACT_OUTPUT" | grep -qi "no session\|not found\|no messages"; then
        echo "   No session found for instance '$INSTANCE'. Nothing to extract."
        exit 0
    fi
    exit "$exit_code"
}

echo "$EXTRACT_OUTPUT"

# Parse PROMPT_FILE from script output (expected line: PROMPT_FILE=/path/to/file)
PROMPT_FILE=$(echo "$EXTRACT_OUTPUT" | grep -E '^PROMPT_FILE=' | tail -1 | cut -d= -f2- | tr -d '"' || true)

if [ -z "$PROMPT_FILE" ]; then
    # Fallback: look for a temp file pattern the script may have created
    PROMPT_FILE=$(echo "$EXTRACT_OUTPUT" | grep -oE '/tmp/[^ ]+\.txt' | tail -1 || true)
fi

if [ -z "$PROMPT_FILE" ] || [ ! -f "$PROMPT_FILE" ]; then
    echo "⚠️  Could not find PROMPT_FILE from extraction script output."
    echo "   Check that extract_session_memory.sh emits: PROMPT_FILE=/path/to/prompt"
    exit 1
fi

echo "📄 Prompt file: $PROMPT_FILE"

# Build a unique session id for the sage agent
SESSION_ID="mem-extract-$(date +%s)"
PROMPT_CONTENT=$(cat "$PROMPT_FILE")

echo "🤖 Spawning sage agent (session: $SESSION_ID)..."

openclaw agent \
    --agent sage \
    --session-id "$SESSION_ID" \
    --message "$PROMPT_CONTENT"

echo "✅ Memory extraction dispatched to sage agent (session: $SESSION_ID)"
