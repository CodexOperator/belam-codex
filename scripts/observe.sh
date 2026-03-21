#!/usr/bin/env bash
# Quick attach to observation session (read-only)
# Usage: ./observe.sh  OR  ssh user@host -t "bash ~/.openclaw/workspace/scripts/observe.sh"

SESSION="belam-observe"

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "No observation session running. Starting one..."
    bash ~/.openclaw/workspace/scripts/observe_setup.sh
fi

tmux attach -t "$SESSION" -r
