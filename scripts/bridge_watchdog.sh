#!/usr/bin/env bash
# bridge_watchdog.sh — Restart live trading bridge if down or stale.
# Runs via crontab every 5 minutes, independent of the bridge process.
# Checks: (1) systemd service status, (2) state file staleness (zombie detection).

LOG="/tmp/bridge_watchdog.log"
MAX_LOG_LINES=500
SERVICE="live-bridge.service"
STATE_FILE="$HOME/.openclaw/workspace/machinelearning/llm-quant-finance/backtesting/live/logs/bridge_state.json"
STALE_SECONDS=1800  # 30 min = 2x cycle duration (15 min)

log_msg() { echo "$(date -u +'%Y-%m-%d %H:%M:%S UTC') $1" >> "$LOG"; }

# Trim log if too long
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt "$MAX_LOG_LINES" ]; then
    tail -n 200 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# --- Check 1: Is the service active? ---
STATUS=$(systemctl --user is-active "$SERVICE" 2>/dev/null)

if [ "$STATUS" != "active" ]; then
    log_msg "WARN: Bridge service not active (status=$STATUS). Restarting..."
    systemctl --user start "$SERVICE" 2>> "$LOG"
    sleep 5
    STATUS2=$(systemctl --user is-active "$SERVICE" 2>/dev/null)
    if [ "$STATUS2" = "active" ]; then
        log_msg "OK: Bridge restarted successfully (pid $(systemctl --user show -p MainPID "$SERVICE" --value 2>/dev/null))"
    else
        log_msg "ERROR: Bridge failed to restart (status=$STATUS2)"
    fi
    exit 0
fi

# --- Check 2: Is the state file stale? (catches zombie processes) ---
if [ -f "$STATE_FILE" ]; then
    FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$STATE_FILE" 2>/dev/null || echo 0) ))
    if [ "$FILE_AGE" -gt "$STALE_SECONDS" ]; then
        log_msg "WARN: Bridge service active but state file stale (${FILE_AGE}s old). Force-restarting..."
        systemctl --user restart "$SERVICE" 2>> "$LOG"
        sleep 5
        STATUS3=$(systemctl --user is-active "$SERVICE" 2>/dev/null)
        if [ "$STATUS3" = "active" ]; then
            log_msg "OK: Bridge recovered after force-restart"
        else
            log_msg "ERROR: Bridge still unhealthy after force-restart (status=$STATUS3)"
        fi
        exit 0
    fi
fi

# Healthy — silent exit (no log spam)
