"""Hermes-native OpenClaw hooks bridge.

Implements a lightweight context-injection plugin that ports the OpenClaw
supermap/bootstrap behavior to Hermes plugin hooks.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

_SESSION_CACHE: dict[str, dict[str, str]] = {}

REFRESH_COMMANDS = {
    "r0",
    "/supermap",
    "/refresh-supermap",
    "refresh supermap",
    "force-render supermap",
    "force render supermap",
}


def _looks_like_workspace(path: Path) -> bool:
    return (path / "scripts" / "codex_engine.py").is_file()


def _workspace() -> Path:
    cwd = Path.cwd()
    if _looks_like_workspace(cwd):
        return cwd

    env_candidates = [
        os.environ.get("BELAM_WORKSPACE"),
        os.environ.get("OPENCLAW_WORKSPACE"),
        os.environ.get("WORKSPACE"),
    ]
    for value in env_candidates:
        if value:
            candidate = Path(value).expanduser()
            if _looks_like_workspace(candidate):
                return candidate

    preferred = Path.home() / ".hermes" / "belam-codex"
    legacy = Path.home() / ".openclaw" / "workspace"

    for candidate in (preferred, legacy):
        if _looks_like_workspace(candidate):
            return candidate

    return preferred


def _should_inject(user_message: str, is_first_turn: bool) -> bool:
    if is_first_turn:
        return True
    normalized = (user_message or "").strip().lower()
    return normalized in REFRESH_COMMANDS


def _run(script_args: list[str], cwd: Path) -> str:
    env = dict(os.environ)
    env.setdefault("BELAM_WORKSPACE", str(cwd))
    env.setdefault("OPENCLAW_WORKSPACE", str(cwd))
    try:
        result = subprocess.run(
            script_args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            env=env,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return (result.stdout or "").strip()


def _build_startup_context(session_id: str, is_first_turn: bool) -> str:
    ws = _workspace()
    cached = _SESSION_CACHE.get(session_id)

    if not cached or is_first_turn:
        supermap = _run(["python3", "scripts/render_supermap.py"], ws)
        memory_idx = _run(["python3", "scripts/codex_engine.py", "--memory-boot-index"], ws)
        cached = {
            "supermap": supermap,
            "memory": memory_idx,
            "built_at": datetime.now(timezone.utc).isoformat(),
        }
        _SESSION_CACHE[session_id] = cached

    legend = ""
    legend_file = ws / "codex_legend.md"
    if legend_file.exists():
        try:
            legend = legend_file.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            legend = ""

    blocks = ["# Codex Layer Active (Hermes Plugin)"]
    if cached.get("supermap"):
        blocks += ["## Supermap", "```", cached["supermap"], "```"]
    if legend:
        blocks += ["## Legend", legend]
    if cached.get("memory"):
        blocks += ["## Memory Boot Index", cached["memory"]]

    return "\n\n".join(blocks).strip()


def _on_session_start(**kwargs: Any) -> None:
    sid = str(kwargs.get("session_id") or "")
    if sid:
        _SESSION_CACHE.pop(sid, None)


def _pre_llm_call(**kwargs: Any) -> Dict[str, str] | None:
    sid = str(kwargs.get("session_id") or "")
    if not sid:
        return None
    is_first_turn = bool(kwargs.get("is_first_turn"))
    user_message = str(kwargs.get("user_message") or "")
    if not _should_inject(user_message, is_first_turn):
        return None
    context = _build_startup_context(sid, is_first_turn)
    if not context:
        return None
    return {"context": context}


def register(ctx) -> None:
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_llm_call", _pre_llm_call)
