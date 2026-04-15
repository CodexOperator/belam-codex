#!/usr/bin/env python3
"""Wrapper-owned memory extraction flow."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from finalize_memory_extraction import finalize_status


def _workspace() -> Path:
    candidates = [
        os.environ.get("BELAM_WORKSPACE"),
        os.environ.get("OPENCLAW_WORKSPACE"),
        os.environ.get("WORKSPACE"),
    ]
    for value in candidates:
        if value:
            candidate = Path(value).expanduser()
            if (candidate / "scripts" / "codex_engine.py").is_file():
                return candidate

    cwd = Path.cwd()
    if (cwd / "scripts" / "codex_engine.py").is_file():
        return cwd

    return Path.home() / ".hermes" / "belam-codex"


WORKSPACE = _workspace()
LOG_PATH = WORKSPACE / "logs" / "memory-extract.log"
EXTRACT_SCRIPT = WORKSPACE / "scripts" / "extract_session_memory.sh"
TRACKED_DIRS = ("lessons", "decisions", "memory/entries")


def log(level: str, message: str, data: dict[str, Any] | None = None) -> None:
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    extra = f" {json.dumps(data, sort_keys=True)}" if data else ""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(f"{ts} [{level}] {message}{extra}\n")


def snapshot_primitives(workspace: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for rel_dir in TRACKED_DIRS:
        base = workspace / rel_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            rel = path.relative_to(workspace).as_posix()
            try:
                snapshot[rel] = path.read_text(encoding="utf-8")
            except Exception:
                snapshot[rel] = ""
    return snapshot


def detect_changed_primitives(workspace: Path, before: dict[str, str]) -> list[str]:
    after = snapshot_primitives(workspace)
    changed: list[str] = []
    for rel, content in after.items():
        if before.get(rel) == content:
            continue
        if not rel.endswith(".md"):
            continue
        changed.append(rel[:-3])
    return sorted(changed)


def parse_extract_output(stdout: str) -> dict[str, str]:
    info: dict[str, str] = {}
    for line in (stdout or "").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        info[key.strip()] = value.strip()
    return info


def build_extraction_session_id(session_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    nonce = uuid.uuid4().hex[:8]
    safe_session = session_id or "unknown"
    return f"mem-extract-{safe_session}-{stamp}-{nonce}"


def run_extract_prep(
    *,
    workspace: Path,
    instance: str,
    session_file: str,
    persona: str,
) -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("BELAM_WORKSPACE", str(workspace))
    env.setdefault("OPENCLAW_WORKSPACE", str(workspace))
    env.setdefault("WORKSPACE", str(workspace))

    cmd = ["bash", str(EXTRACT_SCRIPT), "--instance", instance]
    if session_file:
        cmd.extend(["--session-file", session_file])
    if persona:
        cmd.extend(["--persona", persona])

    result = subprocess.run(
        cmd,
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "extract script failed").strip()[:200]
        raise RuntimeError(details)

    info = parse_extract_output(result.stdout)
    if not info.get("PROMPT_FILE"):
        raise RuntimeError("missing PROMPT_FILE")
    if not info.get("SESSION_ID"):
        raise RuntimeError("missing SESSION_ID")
    return info


def run_agent(
    *,
    workspace: Path,
    agent: str,
    extraction_session_id: str,
    prompt: str,
    timeout_sec: int,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.setdefault("BELAM_WORKSPACE", str(workspace))
    env.setdefault("OPENCLAW_WORKSPACE", str(workspace))
    env.setdefault("WORKSPACE", str(workspace))

    return subprocess.run(
        [
            "openclaw",
            "agent",
            "--agent",
            agent,
            "--session-id",
            extraction_session_id,
            "--message",
            prompt,
            "--timeout",
            str(timeout_sec),
        ],
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_sec + 30,
        check=False,
    )


def orchestrate_memory_extraction(
    *,
    workspace: Path,
    instance: str,
    reason: str = "",
    session_file: str = "",
    persona: str = "",
    agent: str = "sage",
    timeout_sec: int = 300,
) -> dict[str, Any]:
    info = run_extract_prep(
        workspace=workspace,
        instance=instance,
        session_file=session_file,
        persona=persona,
    )
    prompt_file = Path(info["PROMPT_FILE"])
    session_id = info["SESSION_ID"]
    prompt = prompt_file.read_text(encoding="utf-8")
    extraction_session_id = build_extraction_session_id(session_id)

    before = snapshot_primitives(workspace)
    finalize_status(
        workspace=workspace,
        session_id=session_id,
        status="running",
        details=reason or instance,
    )
    log(
        "info",
        "Wrapper-owned memory extraction started",
        {
            "session_id": session_id,
            "instance": instance,
            "reason": reason,
            "agent": agent,
            "extraction_session_id": extraction_session_id,
        },
    )

    try:
        result = run_agent(
            workspace=workspace,
            agent=agent,
            extraction_session_id=extraction_session_id,
            prompt=prompt,
            timeout_sec=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        details = f"timeout after {timeout_sec}s"
        finalize_status(
            workspace=workspace,
            session_id=session_id,
            status="error",
            details=details,
        )
        log(
            "error",
            "Memory extraction timed out",
            {"session_id": session_id, "timeout_sec": timeout_sec, "agent": agent},
        )
        return {"status": "error", "session_id": session_id, "details": details}
    except Exception as exc:
        details = str(exc)[:200] or "wrapper failed"
        finalize_status(
            workspace=workspace,
            session_id=session_id,
            status="error",
            details=details,
        )
        log(
            "error",
            "Memory extraction wrapper failed",
            {"session_id": session_id, "error": str(exc)[:400]},
        )
        return {"status": "error", "session_id": session_id, "details": details}

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "agent failed").strip()[:200]
        finalize_status(
            workspace=workspace,
            session_id=session_id,
            status="error",
            details=details,
        )
        log(
            "error",
            "Memory extraction agent failed",
            {
                "session_id": session_id,
                "returncode": result.returncode,
                "stderr": (result.stderr or "")[:400],
            },
        )
        return {"status": "error", "session_id": session_id, "details": details}

    primitives = detect_changed_primitives(workspace, before)
    finalize_status(
        workspace=workspace,
        session_id=session_id,
        status="complete",
        primitives=primitives,
    )
    log(
        "info",
        "Wrapper-owned memory extraction complete",
        {"session_id": session_id, "primitives": primitives, "agent": agent},
    )
    return {
        "status": "complete",
        "session_id": session_id,
        "primitives": primitives,
        "extraction_session_id": extraction_session_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", default="main")
    parser.add_argument("--reason", default="")
    parser.add_argument("--session-file", default="")
    parser.add_argument("--persona", default="")
    parser.add_argument("--agent", default="sage")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    result = orchestrate_memory_extraction(
        workspace=WORKSPACE,
        instance=args.instance,
        reason=args.reason,
        session_file=args.session_file,
        persona=args.persona,
        agent=args.agent,
        timeout_sec=args.timeout,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
