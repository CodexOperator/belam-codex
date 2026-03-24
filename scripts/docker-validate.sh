#!/bin/bash
set -euo pipefail
# D2: Container Build & Validation Script
# Runs 11 integration tests against the Docker container.
#
# FLAG-1 fix: Stops systemd gateway before container start, restarts after.
# FLAG-3 fix: Guards exec tests on running container.
# FLAG-4 fix: Uses retry loop instead of fixed sleep.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_FILE="$WORKSPACE_DIR/machinelearning/snn_applied_finance/research/pipeline_builds/container-build-and-test_test_results.md"

export HOST_UID=$(id -u)
export HOST_GID=$(id -g)
export OPENCLAW_HOME="$HOME/.openclaw"

pass=0; fail=0; skip=0; total=0
container_running=false
details=""

# FLAG-1: Cleanup trap — always restart systemd gateway + stop container
cleanup() {
    echo ""
    echo "=== Cleanup ==="
    sg docker -c "docker compose -f '$WORKSPACE_DIR/docker-compose.yml' down" 2>/dev/null || true
    echo "Restarting systemd gateway..."
    systemctl --user start openclaw-gateway 2>/dev/null || true
    sleep 2
    echo "✅ Cleanup complete"
}
trap cleanup EXIT

check() {
    total=$((total + 1))
    local desc="$1"; shift
    printf "  T%-2d %-45s " "$total" "$desc"
    local output
    if output=$("$@" 2>&1); then
        echo "PASS"
        pass=$((pass + 1))
        details+="| T${total} | ✅ PASS | ${desc} |\n"
    else
        echo "FAIL"
        fail=$((fail + 1))
        details+="| T${total} | ❌ FAIL | ${desc} |\n"
        details+="<!-- ${output:0:200} -->\n"
    fi
}

check_skip() {
    total=$((total + 1))
    local desc="$1"
    printf "  T%-2d %-45s " "$total" "$desc"
    echo "SKIP (container not running)"
    skip=$((skip + 1))
    details+="| T${total} | ⏭ SKIP | ${desc} |\n"
}

echo "============================================================"
echo "  CONTAINER BUILD & VALIDATION"
echo "  $(date -u +'%Y-%m-%d %H:%M UTC')"
echo "============================================================"
echo ""

# ── Pre-flight ──
echo "--- Pre-flight ---"

# T1: Docker CLI available
check "Docker CLI available" docker --version

# T2: Docker Compose available
check "Docker Compose available" docker compose version

# ── Build ──
echo ""
echo "--- Build ---"

# FLAG-1: Stop systemd gateway to free port 18789
echo "Stopping systemd gateway (FLAG-1: free port 18789)..."
systemctl --user stop openclaw-gateway 2>/dev/null || true
sleep 2

# T3: Build image
echo "Building image (this may take 2-5 min on first run)..."
check "Image builds successfully" sg docker -c "docker compose -f '$WORKSPACE_DIR/docker-compose.yml' build"

# ── Start ──
echo ""
echo "--- Start ---"

# T4: Start container
sg docker -c "docker compose -f '$WORKSPACE_DIR/docker-compose.yml' up -d" 2>&1 || true

# FLAG-4: Retry loop instead of fixed sleep
echo "Waiting for gateway health (up to 30s)..."
gateway_ready=false
for i in $(seq 1 30); do
    if curl -sf http://localhost:18789/health >/dev/null 2>&1; then
        echo "  Gateway ready after ${i}s"
        gateway_ready=true
        break
    fi
    sleep 1
done

if $gateway_ready; then
    container_running=true
fi

check "Container starts and gateway responds" $gateway_ready

# T5: Container is running
check "Container is running" sg docker -c "docker compose -f '$WORKSPACE_DIR/docker-compose.yml' ps --status running" "| grep -q openclaw"

# ── Health ──
echo ""
echo "--- Health & Integration ---"

# T6: Health check
check "Health check (curl :18789/health)" curl -sf http://localhost:18789/health

# T7: Gateway health endpoint
check "Gateway health endpoint" curl -sf http://localhost:18789/health

# FLAG-3: Guard exec tests on running container
if $container_running; then
    # T8: Workspace files accessible
    check "Workspace scripts accessible" sg docker -c "docker compose -f '$WORKSPACE_DIR/docker-compose.yml' exec -T openclaw test -f /home/oc/.openclaw/workspace/scripts/codex_engine.py"

    # T9: Python deps
    check "Python deps (PyYAML + numpy)" sg docker -c "docker compose -f '$WORKSPACE_DIR/docker-compose.yml' exec -T openclaw python3 -c 'import yaml, numpy; print(\"ok\")'"

    # T10: OpenClaw CLI
    check "OpenClaw CLI works" sg docker -c "docker compose -f '$WORKSPACE_DIR/docker-compose.yml' exec -T openclaw openclaw --version"

    # T11: Config accessible
    check "Config file accessible" sg docker -c "docker compose -f '$WORKSPACE_DIR/docker-compose.yml' exec -T openclaw test -f /home/oc/.openclaw/openclaw.json"
else
    check_skip "Workspace scripts accessible"
    check_skip "Python deps (PyYAML + numpy)"
    check_skip "OpenClaw CLI works"
    check_skip "Config file accessible"
fi

# ── Results ──
echo ""
echo "============================================================"
if [ $fail -eq 0 ] && [ $skip -eq 0 ]; then
    echo "  ✅ ALL TESTS PASSED: ${pass}/${total}"
else
    echo "  Results: ${pass} passed, ${fail} failed, ${skip} skipped (${total} total)"
fi
echo "============================================================"

# Write results markdown
cat > "$RESULTS_FILE" << EOF
# Container Validation Results

**Date:** $(date -u +"%Y-%m-%d %H:%M UTC")
**Host:** $(uname -n) ($(uname -m))
**Docker:** $(docker --version 2>/dev/null || echo "N/A")

## Results: ${pass}/${total} passed, ${fail} failed, ${skip} skipped

$([ $fail -eq 0 ] && [ $skip -eq 0 ] && echo "✅ ALL TESTS PASSED" || echo "⚠️ See details below")

| Test | Status | Description |
|------|--------|-------------|
$(echo -e "$details")
EOF

echo "Results written to: $RESULTS_FILE"

[ $fail -eq 0 ] && exit 0 || exit 1
