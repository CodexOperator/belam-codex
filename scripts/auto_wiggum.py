#!/usr/bin/env python3
"""
auto_wiggum.py — Standalone Auto-Wiggum Runner

Resets an agent session, sends a task, waits, steers at threshold, then exits.
Runs as a fire-and-forget process (cron, nohup, background) with no dependency
on Belam's main session or gateway state.

Usage:
    python3 scripts/auto_wiggum.py --agent builder --timeout 600 --task "Do X"
    python3 scripts/auto_wiggum.py --agent sage --timeout 300 --steer-ratio 0.7 --task-file specs/task.md
    python3 scripts/auto_wiggum.py --agent builder --timeout 600 --pipeline my-pipe --stage p1_builder_implement --complete-on-exit
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Auto-Wiggum: fire-and-forget agent task runner with steer timer.",
    )
    p.add_argument("--agent", required=True, help="Agent name (e.g. builder, sage, architect)")
    p.add_argument("--timeout", type=int, required=True, help="Hard timeout in seconds")
    p.add_argument("--steer-ratio", type=float, default=0.8,
                   help="Fraction of timeout at which to send the steer message (default: 0.8)")

    task_group = p.add_mutually_exclusive_group(required=True)
    task_group.add_argument("--task", help="Inline task text")
    task_group.add_argument("--task-file", help="Path to file containing task text")

    p.add_argument("--pipeline", help="Pipeline version/name (optional context)")
    p.add_argument("--stage", help="Pipeline stage (optional context)")
    p.add_argument("--no-reset", action="store_true",
                   help="Skip session reset (use for continue-mode or recovery into existing session)")
    p.add_argument("--complete-on-exit", action="store_true",
                   help="After timeout, call pipeline_orchestrate.py to complete the stage")
    return p


# ---------------------------------------------------------------------------
# Session control (all via subprocess — no internal imports)
# ---------------------------------------------------------------------------

def session_key(agent: str) -> str:
    return f"agent:{agent}:main"


def reset_session(agent: str) -> bool:
    """Reset agent session for a fresh context via gateway RPC. Returns True on success."""
    import json as _json
    key = session_key(agent)
    log(f"Resetting session {key} …")
    result = subprocess.run(
        ["openclaw", "gateway", "call", "sessions.reset",
         "--json", "--params", _json.dumps({"key": key})],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        log(f"ERROR: session reset failed (exit {result.returncode}): {result.stderr.strip()}")
        return False
    try:
        data = _json.loads(result.stdout)
        if data.get("ok"):
            sid = data.get("entry", {}).get("sessionId", "")
            log(f"Session reset OK: {sid[:8]}...")
            return True
        else:
            log(f"ERROR: session reset returned ok=false: {result.stdout.strip()}")
            return False
    except _json.JSONDecodeError:
        log(f"ERROR: session reset returned non-JSON: {result.stdout.strip()}")
        return False


def send_message(agent: str, message: str, background: bool = False) -> bool:
    """Send a message to agent session via openclaw agent CLI.
    
    If background=True, launches via Popen (fire-and-forget) and returns immediately.
    If background=False, uses gateway call sessions.send (non-blocking inject).
    Returns True on success.
    """
    import json as _json
    if background:
        # Fire-and-forget: launch openclaw agent as detached subprocess
        log(f"Dispatching {agent} via openclaw agent (Popen) …")
        try:
            subprocess.Popen(
                ["openclaw", "agent", "--agent", agent, "--message", message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True
        except Exception as e:
            log(f"ERROR: Popen dispatch failed: {e}")
            return False
    else:
        # Inject message into existing session via gateway RPC
        key = session_key(agent)
        log(f"Injecting message to {agent} via gateway sessions.send …")
        result = subprocess.run(
            ["openclaw", "gateway", "call", "sessions.send",
             "--json", "--params", _json.dumps({"key": key, "message": message})],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            log(f"ERROR: session send failed (exit {result.returncode}): {result.stderr.strip()[:200]}")
            return False
        return True


def send_message_with_retry(agent: str, message: str, retries: int = 1, background: bool = False) -> bool:
    """Send with one retry on failure."""
    if send_message(agent, message, background=background):
        return True
    for attempt in range(1, retries + 1):
        log(f"Retrying send (attempt {attempt}/{retries}) …")
        time.sleep(2)
        if send_message(agent, message, background=background):
            return True
    return False


# ---------------------------------------------------------------------------
# Steer message
# ---------------------------------------------------------------------------

def build_steer_message(remaining_seconds: int, pipeline: str | None, stage: str | None) -> str:
    pipeline_line = ""
    if pipeline and stage:
        pipeline_line = (
            f"\n3. If working on a pipeline, run: "
            f"python3 scripts/pipeline_orchestrate.py {pipeline} complete {stage}"
        )
    return (
        f"⏰ WRAP UP — You have {remaining_seconds}s left before hard timeout.\n"
        f"Finish what you're doing NOW:\n"
        f"1. Write any remaining files\n"
        f"2. Run tests if applicable{pipeline_line}\n"
        f"4. Summarize what you completed and what remains\n\n"
        f"Do NOT start new work. Wrap up cleanly."
    )


# ---------------------------------------------------------------------------
# Pipeline stage completion
# ---------------------------------------------------------------------------

def complete_pipeline_stage(pipeline: str, stage: str) -> bool:
    """Call pipeline_orchestrate.py to mark stage complete. Returns True on success."""
    workspace = Path(__file__).parent.parent
    script = workspace / "scripts" / "pipeline_orchestrate.py"
    log(f"Completing pipeline stage: {pipeline} {stage} …")
    result = subprocess.run(
        ["python3", str(script), pipeline, "complete", stage,
         "--notes", "auto_wiggum: hard timeout reached, marking complete"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log(f"WARNING: pipeline complete failed (exit {result.returncode}): {result.stderr.strip()}")
        return False
    log(f"Pipeline stage marked complete.")
    return True


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    # ── Resolve task text ──────────────────────────────────────────────────
    if args.task:
        task_text = args.task
    else:
        task_path = Path(args.task_file)
        if not task_path.exists():
            log(f"ERROR: task-file not found: {task_path}")
            return 1
        task_text = task_path.read_text()

    # ── Prepend pipeline context if provided ──────────────────────────────
    if args.pipeline and args.stage:
        prefix = (
            f"[Pipeline: {args.pipeline} | Stage: {args.stage}]\n\n"
        )
        task_text = prefix + task_text

    timeout: int = args.timeout
    steer_ratio: float = args.steer_ratio
    steer_delay = int(timeout * steer_ratio)
    remaining_at_steer = timeout - steer_delay

    log(f"Auto-Wiggum starting: agent={args.agent} timeout={timeout}s "
        f"steer_ratio={steer_ratio} steer_at={steer_delay}s")

    # ── 1. Reset session (unless --no-reset for continue mode / recovery) ─
    if getattr(args, 'no_reset', False):
        log(f"Skipping session reset (--no-reset)")
    elif not reset_session(args.agent):
        return 1

    # ── 2. Send task (fire-and-forget via Popen — agent runs in background) ─
    log(f"Dispatching task to {args.agent} …")
    if not send_message_with_retry(args.agent, task_text, background=True):
        log("ERROR: could not dispatch task after retry. Exiting.")
        return 1
    log("Task dispatched.")

    start_time = time.monotonic()

    # ── 3. Sleep until steer threshold ────────────────────────────────────
    log(f"Sleeping {steer_delay}s until steer threshold …")
    time.sleep(steer_delay)

    # ── 4. Send steer message ──────────────────────────────────────────────
    steer_msg = build_steer_message(remaining_at_steer, args.pipeline, args.stage)
    log(f"Sending steer message ({remaining_at_steer}s remaining) …")
    if not send_message_with_retry(args.agent, steer_msg):
        log("WARNING: steer message send failed — agent will not receive wrap-up signal.")
    else:
        log("Steer message sent.")

    # ── 5. Sleep until hard timeout ───────────────────────────────────────
    elapsed = time.monotonic() - start_time
    remaining = max(0.0, timeout - elapsed)
    log(f"Sleeping {remaining:.0f}s until hard timeout …")
    time.sleep(remaining)

    # ── 6. Finalize ───────────────────────────────────────────────────────
    log(f"Hard timeout reached for agent={args.agent}.")

    if args.complete_on_exit and args.pipeline and args.stage:
        complete_pipeline_stage(args.pipeline, args.stage)

    log("Auto-Wiggum done. Exit 0.")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
