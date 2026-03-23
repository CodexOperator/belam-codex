#!/usr/bin/env bash
# gateway_watchdog.sh — Restart OpenClaw gateway if unresponsive.
# Safe: checks health endpoint first, only restarts if actually down.
# Runs via system crontab (independent of gateway).

LOG="/tmp/openclaw_watchdog.log"
MAX_LOG_LINES=500

log() { echo "$(date -u +'%Y-%m-%d %H:%M:%S UTC') $1" >> "$LOG"; }

# Trim log if too long
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt "$MAX_LOG_LINES" ]; then
    tail -n 200 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# Check if gateway process exists
if ! pgrep -f "openclaw.*gateway" > /dev/null 2>&1; then
    log "WARN: No gateway process found. Restarting..."
    systemctl --user start openclaw-gateway.service 2>> "$LOG"
    sleep 5
    if pgrep -f "openclaw.*gateway" > /dev/null 2>&1; then
        log "OK: Gateway restarted successfully (pid $(pgrep -f 'openclaw.*gateway' | head -1))"
    else
        log "ERROR: Gateway failed to restart"
    fi
    exit 0
fi

# Process exists — check if it's actually responding
HEALTH=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 5 \
    http://127.0.0.1:18789/health 2>/dev/null)

if [ "$HEALTH" = "200" ]; then
    # Healthy — silent exit (no log spam)
    exit 0
fi

log "WARN: Gateway process alive but health check failed (HTTP $HEALTH). Restarting..."
systemctl --user restart openclaw-gateway.service 2>> "$LOG"
sleep 5

HEALTH2=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 5 \
    http://127.0.0.1:18789/health 2>/dev/null)

if [ "$HEALTH2" = "200" ]; then
    log "OK: Gateway recovered after restart"
else
    log "ERROR: Gateway still unhealthy after restart (HTTP $HEALTH2)"
fi
