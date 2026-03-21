#!/usr/bin/env bash
# Sets up the belam observation tmux session
# Run once; session persists until killed

SESSION="belam-observe"
WS="$HOME/.openclaw/workspace"

# Kill existing if any
tmux kill-session -t "$SESSION" 2>/dev/null

# Create session with a fixed size
tmux new-session -d -s "$SESSION" -x 200 -y 50

# Pane 0: welcome banner + codex watch daemon
tmux send-keys -t "$SESSION" "clear" Enter
tmux send-keys -t "$SESSION" "echo '🔮 Belam Observation Terminal'" Enter
tmux send-keys -t "$SESSION" "echo 'Read-only attach: tmux attach -t belam-observe -r'" Enter
tmux send-keys -t "$SESSION" "echo ''" Enter
tmux send-keys -t "$SESSION" "cd $WS" Enter
tmux send-keys -t "$SESSION" "python3 scripts/codex_engine.py watch 2>&1 || python3 scripts/codex_watch.py --watch 2>&1 || (echo 'Watch daemon unavailable — showing supermap snapshot:'; python3 scripts/codex_engine.py supermap 2>&1; echo ''; echo 'Press Ctrl+C to exit or type commands to explore.')" Enter

# Try to split for a log tail pane (best-effort)
if tmux split-window -t "$SESSION" -v -l 12 2>/dev/null; then
    tmux send-keys -t "$SESSION" "cd $WS && tail -F memory/\$(date +%Y-%m-%d).md 2>/dev/null || (echo 'Watching workspace memory files...' && ls -lt $WS/memory/ | head -10)" Enter
    tmux select-pane -t "$SESSION" -U
fi

echo "Observation session '$SESSION' created."
echo "To attach read-only: tmux attach -t $SESSION -r"
