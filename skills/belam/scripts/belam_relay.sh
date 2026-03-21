#!/usr/bin/env bash
# belam_relay.sh — relay user commands to belam CLI or codex engine
# Exit codes: 0=success, 1=sanitization failure, 2=timeout

set -euo pipefail

WORKSPACE="${HOME}/.openclaw/workspace"
CODEX_ENGINE="${WORKSPACE}/scripts/codex_engine.py"
BELAM_CLI="${HOME}/.local/bin/belam"
TIMEOUT_SECS=30

# ── 1. No-arg mode: show supermap ──────────────────────────────────────────
if [[ $# -eq 0 ]]; then
    output=$(cd "${WORKSPACE}" && timeout "${TIMEOUT_SECS}" python3 "${CODEX_ENGINE}" 2>&1) || {
        exit_code=$?
        [[ $exit_code -eq 124 ]] && exit 2
        echo "$output"
        exit $exit_code
    }
    echo "$output" | sed 's/\x1b\[[0-9;]*[mGKHF]//g; s/\x1b\[[0-9;]*[A-Za-z]//g'
    exit 0
fi

# ── 2. Build the raw input string ─────────────────────────────────────────
RAW_INPUT="$*"

# ── 3. Sanitize ────────────────────────────────────────────────────────────
# Max length
if [[ ${#RAW_INPUT} -gt 200 ]]; then
    echo "ERROR: Input too long (max 200 chars)" >&2
    exit 1
fi

# Reject dangerous characters: ; | & $ \ > < ` $( newlines
if echo "${RAW_INPUT}" | grep -qP '[;|&$\\><`\n\r]|\$\('; then
    echo "ERROR: Rejected — input contains unsafe characters" >&2
    exit 1
fi

# Allow only: alphanumeric, hyphens, underscores, dots, spaces, =, commas, single/double quotes
if echo "${RAW_INPUT}" | grep -qP "[^a-zA-Z0-9 _.=,'\"\-]"; then
    echo "ERROR: Rejected — input contains disallowed characters" >&2
    exit 1
fi

# ── 4. Route detection ─────────────────────────────────────────────────────
# Codex engine routes:
#   - bare coordinate: single alphanumeric token like t1, d6, p, m, md2
#   - flags: starts with -g, -e, -n, --graph, --explore, --node, etc.
#   - bare single-word that looks like a coordinate (letters+digits, no spaces)
FIRST_TOKEN="${1:-}"

route_to_codex=false

# Starts with a dash (flag) → codex engine handles flags like -g, -e, -n, --depth
if [[ "${FIRST_TOKEN}" == -* ]]; then
    route_to_codex=true
fi

# Single token that matches coord pattern: optional letters + optional digits (e.g. t1, d6, p, m, md2, a3b)
if [[ $# -eq 1 ]] && echo "${FIRST_TOKEN}" | grep -qP '^[a-zA-Z]{1,4}[0-9]{0,4}$'; then
    route_to_codex=true
fi

# Known belam CLI subcommands — explicitly route to belam
BELAM_COMMANDS="pipelines pipeline status tasks task memory logs log heartbeat help version config init"
for cmd in $BELAM_COMMANDS; do
    if [[ "${FIRST_TOKEN}" == "${cmd}" ]]; then
        route_to_codex=false
        break
    fi
done

# ── 5. Execute ────────────────────────────────────────────────────────────
strip_ansi() {
    sed 's/\x1b\[[0-9;]*[mGKHF]//g; s/\x1b\[[0-9;]*[A-Za-z]//g'
}

if [[ "${route_to_codex}" == true ]]; then
    output=$(cd "${WORKSPACE}" && timeout "${TIMEOUT_SECS}" python3 "${CODEX_ENGINE}" ${RAW_INPUT} 2>&1) || {
        exit_code=$?
        [[ $exit_code -eq 124 ]] && { echo "ERROR: Timed out after ${TIMEOUT_SECS}s" >&2; exit 2; }
        echo "$output" | strip_ansi
        exit $exit_code
    }
else
    output=$(cd "${WORKSPACE}" && timeout "${TIMEOUT_SECS}" "${BELAM_CLI}" ${RAW_INPUT} 2>&1) || {
        exit_code=$?
        [[ $exit_code -eq 124 ]] && { echo "ERROR: Timed out after ${TIMEOUT_SECS}s" >&2; exit 2; }
        echo "$output" | strip_ansi
        exit $exit_code
    }
fi

echo "$output" | strip_ansi
exit 0
