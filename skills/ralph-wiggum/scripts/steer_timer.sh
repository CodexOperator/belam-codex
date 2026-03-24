#!/usr/bin/env bash
# steer_timer.sh — Background timer that sends a wrap-up steer to a subagent
# Usage: steer_timer.sh <session-key> <steer-delay-seconds> [hard-timeout-seconds]
#
# Sleeps for steer-delay, then sends a structured wrap-up message via openclaw CLI.
# If hard-timeout is provided, logs a warning when the agent will be killed.

set -euo pipefail

SESSION_KEY="${1:?Usage: steer_timer.sh <session-key> <steer-delay-sec> [hard-timeout-sec]}"
STEER_DELAY="${2:?Missing steer delay seconds}"
HARD_TIMEOUT="${3:-}"

STEER_MSG="⏰ WRAP-UP TIME. You are approaching your timeout. Stop what you're doing and write a summary NOW.

Structure your final output as:

## Status
One line: completed | partial | blocked

## Problems Found
- What issues did you discover?

## What Worked
- What actions succeeded?

## What Didn't Work  
- What failed or was abandoned?

## Changes Made
- List files modified with one-line descriptions

## Remaining Work
- What still needs to be done if status is not completed?

Write this summary to your designated output file, then stop."

echo "[ralph-wiggum] Timer started: steer in ${STEER_DELAY}s for session ${SESSION_KEY}"

sleep "${STEER_DELAY}"

echo "[ralph-wiggum] Sending wrap-up steer to ${SESSION_KEY}"
openclaw agent send --session "${SESSION_KEY}" --message "${STEER_MSG}" 2>&1 || true

if [ -n "${HARD_TIMEOUT}" ]; then
    REMAINING=$((HARD_TIMEOUT - STEER_DELAY))
    echo "[ralph-wiggum] Hard timeout in ${REMAINING}s"
fi
