#!/usr/bin/env python3
"""Pipeline Stall Recovery — detect and re-dispatch stuck pipeline agents.

Usage:
    python3 scripts/pipeline_stall_recovery.py [--threshold 30] [--dry-run]

Scans non-archived pipelines for stalls (stage unchanged for >threshold minutes,
agent process dead). Re-dispatches the agent to the same session with escalating
timeouts. Max 3 retries per stage.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PIPELINES_DIR = WORKSPACE / "pipelines"
STATE_DIRS = [
    WORKSPACE / "pipeline_builds",
    WORKSPACE / "machinelearning" / "snn_applied_finance" / "research" / "pipeline_builds",
]

DEFAULT_THRESHOLD_MINUTES = 30
MAX_RECOVERY_ATTEMPTS = 3
TIMEOUT_ESCALATION = 1.5
BASE_TIMEOUT_SECONDS = 600

ACTIVE_STAGES = {
    "p1_architect_design", "p1_critic_design_review", "p1_builder_implement",
    "p1_bugfix", "p1_builder_bugfix", "p1_critic_review", "p1_critic_code_review",
    "p2_architect_design", "p2_critic_design_review", "p2_builder_implement",
    "p2_bugfix", "p2_builder_bugfix", "p2_critic_review", "p2_critic_code_review",
    "phase1_design", "phase1_implement",
}

STAGE_TO_AGENT = {
    "architect": ["architect_design", "architect"],
    "critic": ["critic_design_review", "critic_review", "critic_code_review", "critic"],
    "builder": ["builder_implement", "bugfix", "builder_bugfix", "builder"],
}


def get_agent_for_stage(stage: str) -> str:
    """Determine which agent is responsible for a given stage."""
    stage_lower = stage.lower()
    for agent, keywords in STAGE_TO_AGENT.items():
        for kw in keywords:
            if kw in stage_lower:
                return agent
    return "builder"  # default fallback


def find_state_file(version: str) -> Path | None:
    """Find the state JSON for a pipeline version."""
    for d in STATE_DIRS:
        candidate = d / f"{version}_state.json"
        if candidate.exists():
            return candidate
    return None


def is_pid_alive(pid: int) -> bool:
    """Check if a process is still running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False


def get_non_archived_pipelines() -> list[dict]:
    """Get all non-archived pipeline metadata."""
    results = []
    if not PIPELINES_DIR.exists():
        return results

    for f in PIPELINES_DIR.glob("*.md"):
        content = f.read_text()
        status = None
        version = None
        for line in content.split("\n"):
            if line.startswith("status:"):
                status = line.split(":", 1)[1].strip()
            if line.startswith("version:"):
                version = line.split(":", 1)[1].strip()
        if status and status != "archived" and version:
            results.append({"file": f, "status": status, "version": version})

    return results


def detect_stall(state: dict, threshold_minutes: int) -> dict | None:
    """Check if a pipeline is stalled. Returns stall info or None."""
    status = state.get("status", "")

    # Only check active stages
    is_active = any(s in status.lower() for s in [
        "architect", "critic", "builder", "implement", "bugfix", "design", "review"
    ])
    if not is_active:
        return None

    # Check age
    status_updated = state.get("status_updated", "")
    if not status_updated:
        return None

    try:
        # Handle various date formats
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"]:
            try:
                updated_dt = datetime.strptime(status_updated, fmt)
                if updated_dt.tzinfo is None:
                    updated_dt = updated_dt.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        else:
            return None
    except Exception:
        return None

    now = datetime.now(timezone.utc)
    age_minutes = (now - updated_dt).total_seconds() / 60

    if age_minutes < threshold_minutes:
        return None

    # Check if PID is alive
    last_dispatched_str = state.get("last_dispatched", "")
    # Try to extract PID from dispatch info — not always available
    # Check process list for agent processes instead
    pid = state.get("dispatch_pid", 0)
    if pid and is_pid_alive(pid):
        return None  # Agent is still running, not stalled

    return {
        "status": status,
        "age_minutes": round(age_minutes, 1),
        "status_updated": status_updated,
        "pid_alive": False,
    }


def get_recovery_attempts(state: dict, stage: str) -> int:
    """Get number of recovery attempts for a stage."""
    attempts = state.get("recovery_attempts", {})
    return attempts.get(stage, 0)


def calculate_timeout(attempt: int) -> int:
    """Calculate timeout with escalation."""
    return int(BASE_TIMEOUT_SECONDS * (TIMEOUT_ESCALATION ** attempt))


def recover_pipeline(version: str, state: dict, state_file: Path, dry_run: bool = False) -> bool:
    """Attempt to recover a stalled pipeline. Returns True if recovery was initiated."""
    status = state.get("status", "")
    attempts = get_recovery_attempts(state, status)

    if attempts >= MAX_RECOVERY_ATTEMPTS:
        print(f"  ⛔ Max recovery attempts ({MAX_RECOVERY_ATTEMPTS}) reached for {version} stage {status}")
        return False

    agent = get_agent_for_stage(status)
    timeout = calculate_timeout(attempts)

    print(f"  🔄 Recovery attempt {attempts + 1}/{MAX_RECOVERY_ATTEMPTS} for {version}")
    print(f"     Stage: {status} | Agent: {agent} | Timeout: {timeout}s")

    if dry_run:
        print(f"     [DRY RUN] Would re-dispatch {agent} for {version}")
        return True

    # Update state with recovery tracking
    if "recovery_attempts" not in state:
        state["recovery_attempts"] = {}
    state["recovery_attempts"][status] = attempts + 1

    if "recovery_log" not in state:
        state["recovery_log"] = []
    state["recovery_log"].append({
        "time": datetime.now(timezone.utc).isoformat(),
        "stage": status,
        "attempt": attempts + 1,
        "timeout": timeout,
        "agent": agent,
    })

    # Update last_dispatched
    state["last_dispatched"] = datetime.now(timezone.utc).isoformat()
    state["status_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    # Write updated state
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    # Re-dispatch via pipeline_orchestrate.py
    # Use the "kickoff" approach — re-dispatch same stage with session continue
    try:
        orchestrate_script = WORKSPACE / "scripts" / "pipeline_orchestrate.py"
        cmd = [
            sys.executable, str(orchestrate_script),
            version, "redispatch",
            "--agent", agent,
            "--timeout", str(timeout),
        ]

        # If pipeline_orchestrate.py doesn't support redispatch, fall back to
        # direct OpenClaw session send
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            # Fallback: use openclaw CLI to send message to agent
            print(f"     ⚠️  orchestrate redispatch failed, using direct session dispatch")
            fallback_cmd = [
                "openclaw", "session", "send",
                f"agent:{agent}:main",
                f"Resume pipeline {version} stage {status}. "
                f"This is recovery attempt {attempts + 1}. "
                f"Check the pipeline state and continue where you left off. "
                f"When done, run: python3 scripts/pipeline_orchestrate.py {version} complete {status}"
            ]
            subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=30)

        print(f"  ✅ Recovery dispatched for {version}")
        return True

    except Exception as e:
        print(f"  ❌ Recovery failed for {version}: {e}")
        return False


def scan_and_recover(threshold_minutes: int = DEFAULT_THRESHOLD_MINUTES, dry_run: bool = False) -> dict:
    """Main entry point. Scan all pipelines and recover stalled ones."""
    results = {
        "scanned": 0,
        "stalled": 0,
        "recovered": 0,
        "max_retries_reached": 0,
        "errors": 0,
    }

    pipelines = get_non_archived_pipelines()
    results["scanned"] = len(pipelines)

    if not pipelines:
        print("📋 No active pipelines found.")
        return results

    print(f"📋 Scanning {len(pipelines)} active pipeline(s) (threshold: {threshold_minutes}min)")

    for p in pipelines:
        version = p["version"]
        state_file = find_state_file(version)

        if not state_file:
            continue

        try:
            with open(state_file) as f:
                state = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  ⚠️  Could not read state for {version}: {e}")
            results["errors"] += 1
            continue

        stall_info = detect_stall(state, threshold_minutes)
        if not stall_info:
            continue

        results["stalled"] += 1
        print(f"\n🚨 STALL DETECTED: {version}")
        print(f"   Stage: {stall_info['status']} | Stale for: {stall_info['age_minutes']}min | PID alive: {stall_info['pid_alive']}")

        attempts = get_recovery_attempts(state, stall_info["status"])
        if attempts >= MAX_RECOVERY_ATTEMPTS:
            results["max_retries_reached"] += 1
            print(f"   ⛔ Max retries ({MAX_RECOVERY_ATTEMPTS}) reached — needs manual intervention")
            continue

        if recover_pipeline(version, state, state_file, dry_run=dry_run):
            results["recovered"] += 1

    # Summary
    print(f"\n{'─' * 50}")
    print(f"📊 Stall Recovery Summary:")
    print(f"   Scanned:    {results['scanned']}")
    print(f"   Stalled:    {results['stalled']}")
    print(f"   Recovered:  {results['recovered']}")
    if results["max_retries_reached"]:
        print(f"   ⛔ Max retries: {results['max_retries_reached']}")
    if results["errors"]:
        print(f"   ❌ Errors:    {results['errors']}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Pipeline stall recovery")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD_MINUTES,
                        help=f"Minutes before a stage is considered stalled (default: {DEFAULT_THRESHOLD_MINUTES})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Detect and report only, don't recover")
    args = parser.parse_args()

    scan_and_recover(threshold_minutes=args.threshold, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
