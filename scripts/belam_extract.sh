#!/usr/bin/env bash
# belam_extract.sh — Manual memory extraction
# Usage:
#   belam extract [instance]              Extract latest session for instance
#   belam extract --file /path/to.jsonl   Extract a specific transcript file
#   belam extract --last                  Extract the most recent completed session
#
# Steps:
#   1. Run extract_session_memory.sh to prepare the prompt file
#   2. Spawn the sage agent with that prompt

set -euo pipefail

WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
SCRIPTS="$WORKSPACE/scripts"
EXTRACT_SCRIPT="$SCRIPTS/extract_session_memory.sh"

INSTANCE="main"
SESSION_FILE=""
BACKGROUND=false

usage() {
  cat <<EOF
Usage: belam extract [options] [instance]

Options:
  --file FILE    Extract from a specific JSONL transcript file
  --last         Extract the most recent completed session (latest .reset.*)
  --bg           Run sage in background (fire-and-forget)
  -h, --help     Show this help

Examples:
  belam extract                     # Latest session for main instance
  belam extract architect           # Latest session for architect
  belam extract --file /path/to/session.jsonl
  belam extract --last --bg         # Background extraction of last session
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file) SESSION_FILE="${2:?'--file requires a path'}"; shift 2 ;;
    --last) shift ;;  # default behavior, explicit flag for clarity
    --bg)   BACKGROUND=true; shift ;;
    -h|--help) usage ;;
    -*) echo "Unknown option: $1" >&2; exit 1 ;;
    *)  INSTANCE="$1"; shift ;;
  esac
done

echo "🧠 belam extract — instance: $INSTANCE"

if [[ ! -f "$EXTRACT_SCRIPT" ]]; then
  echo "⚠️  extract_session_memory.sh not found at $EXTRACT_SCRIPT"
  exit 1
fi

# Build args for the extraction script
EXTRACT_ARGS=(--instance "$INSTANCE")
if [[ -n "$SESSION_FILE" ]]; then
  if [[ ! -f "$SESSION_FILE" ]]; then
    echo "⚠️  File not found: $SESSION_FILE"
    exit 1
  fi
  EXTRACT_ARGS+=(--session-file "$SESSION_FILE")
  echo "📂 Using specific file: $SESSION_FILE"
fi

# Run extraction prep
EXTRACT_OUTPUT=$(bash "$EXTRACT_SCRIPT" "${EXTRACT_ARGS[@]}" 2>&1) || {
  exit_code=$?
  echo "$EXTRACT_OUTPUT"
  if echo "$EXTRACT_OUTPUT" | grep -qi "no session\|not found\|no messages"; then
    echo "   No session found for instance '$INSTANCE'. Nothing to extract."
    exit 0
  fi
  exit "$exit_code"
}

echo "$EXTRACT_OUTPUT"

# Parse PROMPT_FILE
PROMPT_FILE=$(echo "$EXTRACT_OUTPUT" | grep -E '^PROMPT_FILE=' | tail -1 | cut -d= -f2- | tr -d '"' || true)

if [[ -z "$PROMPT_FILE" ]] || [[ ! -f "$PROMPT_FILE" ]]; then
  echo "⚠️  Could not find PROMPT_FILE from extraction output."
  exit 1
fi

echo "📄 Prompt file: $PROMPT_FILE ($(wc -c < "$PROMPT_FILE" | tr -d ' ') bytes)"

SESSION_ID="mem-extract-$(date +%s)"
PROMPT_CONTENT=$(cat "$PROMPT_FILE")

# Capture transcript path from extraction output
TRANSCRIPT_FILE=$(echo "$EXTRACT_OUTPUT" | grep -E '^TRANSCRIPT_FILE=' | tail -1 | cut -d= -f2- | tr -d '"' || true)

# --- Post-processing: stamp new lessons/decisions with source transcript ---
stamp_new_primitives() {
  local transcript_path="$1"
  [[ -z "$transcript_path" ]] && return

  # Find lessons and decisions modified in the last 30 seconds
  for dir in "$WORKSPACE/lessons" "$WORKSPACE/decisions"; do
    [[ -d "$dir" ]] || continue
    find "$dir" -name "*.md" -newermt "30 seconds ago" -type f | while read -r f; do
      # Skip if already has source_transcript
      grep -q "^source_transcript:" "$f" && continue
      # Insert source_transcript after the last frontmatter field (before closing ---)
      sed -i "/^---$/,/^---$/ { /^---$/! { /^---$/! s|^---|source_transcript: $transcript_path\n---|; }; }" "$f" 2>/dev/null
      # Simpler: just append before the closing ---
      python3 -c "
import sys
p = sys.argv[1]
t = sys.argv[2]
text = open(p).read()
# Find second --- (closing frontmatter)
first = text.index('---')
second = text.index('---', first + 3)
patched = text[:second] + 'source_transcript: ' + t + '\n' + text[second:]
open(p, 'w').write(patched)
" "$f" "$transcript_path" 2>/dev/null && echo "   📎 Linked: $(basename "$f") → $(basename "$transcript_path")"
    done
  done
}

if [[ "$BACKGROUND" == true ]]; then
  echo "🤖 Spawning sage in background (session: $SESSION_ID)..."
  # Background: stamp after sage finishes via a wrapper
  (
    openclaw agent \
      --agent sage \
      --session-id "$SESSION_ID" \
      --message "$PROMPT_CONTENT" > /dev/null 2>&1
    stamp_new_primitives "$TRANSCRIPT_FILE"
  ) &
  echo "✅ Sage dispatched (pid: $!, session: $SESSION_ID)"
else
  echo "🤖 Spawning sage agent (session: $SESSION_ID)..."
  openclaw agent \
    --agent sage \
    --session-id "$SESSION_ID" \
    --message "$PROMPT_CONTENT"
  echo "✅ Extraction complete (session: $SESSION_ID)"
  stamp_new_primitives "$TRANSCRIPT_FILE"
fi
