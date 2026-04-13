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


def _workspace() -> Path:
    env = os.environ.get("WORKSPACE")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _run(script_args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            script_args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
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
        supermap = _run(["python3", "scripts/codex_engine.py", "--supermap"], ws)
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
    context = _build_startup_context(sid, bool(kwargs.get("is_first_turn")))
    if not context:
        return None
    return {"context": context}


def register(ctx) -> None:
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_llm_call", _pre_llm_call)
