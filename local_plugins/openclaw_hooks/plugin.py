"""Hermes-native OpenClaw hooks bridge.

Implements a lightweight context-injection plugin that ports the OpenClaw
supermap/bootstrap behavior to Hermes plugin hooks.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

_SESSION_CACHE: dict[str, dict[str, str]] = {}
_LAST_FINALIZED_SESSION_ID: str | None = None
_EXTRACTION_DISPATCHED: set[str] = set()
_EXTRACTION_STALE_AFTER_SECONDS = 15 * 60

DEFAULT_INJECT_FILES = ["SOUL.md", "IDENTITY.md", "USER.md", "codex_legend.md"]

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


def _sessions_dir() -> Path:
    hermes_sessions = Path(
        os.environ.get("HERMES_SESSIONS_DIR", Path.home() / ".hermes" / "sessions")
    ).expanduser()
    if hermes_sessions.is_dir():
        return hermes_sessions
    return Path.home() / ".openclaw" / "agents" / "main" / "sessions"


def _memory_extract_log() -> Path:
    return _workspace() / "logs" / "memory-extract.log"


def _log(level: str, msg: str, data: dict[str, Any] | None = None) -> None:
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    extra = f" {json.dumps(data, sort_keys=True)}" if data else ""
    line = f"{ts} [{level}] {msg}{extra}\n"
    try:
        log_path = _memory_extract_log()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        pass


def _pending_extraction_path() -> Path:
    return _workspace() / "memory" / "pending_extraction.json"


def _load_pending_extraction() -> dict[str, Any]:
    path = _pending_extraction_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_pending_extraction(data: dict[str, Any]) -> None:
    path = _pending_extraction_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_pending_timestamp(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _mark_extraction_status(session_id: str, status: str, details: str = "") -> None:
    data = _load_pending_extraction()
    entry = data.get(session_id, {}) if isinstance(data.get(session_id), dict) else {}
    entry["status"] = status
    entry["updated_at"] = _utc_now_iso()
    if details:
        entry["details"] = details
    elif "details" in entry:
        entry.pop("details", None)
    data[session_id] = entry
    data["status"] = status
    _write_pending_extraction(data)


def _recover_pending_extractions() -> None:
    data = _load_pending_extraction()
    if not data:
        return

    stale_before = datetime.now(timezone.utc).timestamp() - _EXTRACTION_STALE_AFTER_SECONDS
    changed = False

    for session_id, entry in data.items():
        if not isinstance(entry, dict) or entry.get("status") != "running":
            continue
        updated_at = _parse_pending_timestamp(entry.get("updated_at"))
        if updated_at is not None and updated_at.timestamp() > stale_before:
            continue
        entry["status"] = "error"
        entry["details"] = "stale"
        entry["updated_at"] = _utc_now_iso()
        _EXTRACTION_DISPATCHED.discard(session_id)
        changed = True
        _log("warn", "Recovered stale extraction entry", {"session_id": session_id})

    if changed:
        data["status"] = "error"
        _write_pending_extraction(data)


def _session_file_for(session_id: str) -> Path | None:
    if not session_id:
        return None
    path = _sessions_dir() / f"{session_id}.jsonl"
    return path if path.exists() else None


def _session_already_extracted(session_id: str) -> bool:
    if not session_id:
        return True
    if session_id in _EXTRACTION_DISPATCHED:
        return True
    pending = _load_pending_extraction()
    entry = pending.get(session_id)
    if not isinstance(entry, dict):
        return False
    return entry.get("status") in {"running", "complete"}


def _find_session_to_extract(current_session_id: str = "") -> Path | None:
    _recover_pending_extractions()
    sessions_dir = _sessions_dir()
    if not sessions_dir.is_dir():
        return None
    candidates = sorted(sessions_dir.glob("*.jsonl"), reverse=True)
    for path in candidates:
        session_id = path.stem
        if session_id == current_session_id:
            continue
        if _session_already_extracted(session_id):
            continue
        return path
    return None


def _dispatch_extraction(session_path: Path, reason: str) -> None:
    _recover_pending_extractions()
    session_id = session_path.stem
    if _session_already_extracted(session_id):
        return

    ws = _workspace()
    env = dict(os.environ)
    env.setdefault("BELAM_WORKSPACE", str(ws))
    env.setdefault("OPENCLAW_WORKSPACE", str(ws))
    env.setdefault("WORKSPACE", str(ws))
    env.setdefault("HERMES_SESSIONS_DIR", str(_sessions_dir()))

    _log(
        "info",
        "Dispatching Hermes memory extraction",
        {"session_id": session_id, "reason": reason, "session_path": str(session_path)},
    )

    try:
        result = subprocess.run(
            [
                "bash",
                "scripts/extract_session_memory.sh",
                "--instance",
                "main",
                "--session-file",
                str(session_path),
            ],
            cwd=str(ws),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env,
        )
    except Exception as exc:
        _mark_extraction_status(session_id, "error", str(exc)[:200])
        _log(
            "error",
            "Extraction script crashed",
            {"session_id": session_id, "reason": reason, "error": str(exc)[:400]},
        )
        return

    if result.returncode != 0:
        _mark_extraction_status(session_id, "error", (result.stderr or result.stdout)[:200])
        _log(
            "error",
            "Extraction script failed",
            {
                "session_id": session_id,
                "reason": reason,
                "returncode": result.returncode,
                "stderr": (result.stderr or "")[:400],
            },
        )
        return

    prompt_file = ""
    for line in (result.stdout or "").splitlines():
        if line.startswith("PROMPT_FILE="):
            prompt_file = line.split("=", 1)[1].strip()
            break

    if not prompt_file:
        _mark_extraction_status(session_id, "error", "missing PROMPT_FILE")
        _log(
            "error",
            "Extraction script returned no PROMPT_FILE",
            {
                "session_id": session_id,
                "reason": reason,
                "stdout": (result.stdout or "")[:400],
            },
        )
        return

    try:
        subprocess.Popen(
            ["python3", "scripts/codex_engine.py", "spawn", "sage", f"@{prompt_file}", "--bg"],
            cwd=str(ws),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        _mark_extraction_status(session_id, "error", str(exc)[:200])
        _log(
            "error",
            "Failed to spawn sage for extraction",
            {"session_id": session_id, "reason": reason, "error": str(exc)[:400]},
        )
        return

    _EXTRACTION_DISPATCHED.add(session_id)
    _mark_extraction_status(session_id, "running", reason)
    _log(
        "info",
        "Hermes memory extraction spawned",
        {"session_id": session_id, "reason": reason, "prompt_file": prompt_file},
    )


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


def _load_injection_template(cwd: Path) -> list[str]:
    agents_file = cwd / "AGENTS.md"
    if not agents_file.exists():
        return list(DEFAULT_INJECT_FILES)

    try:
        text = agents_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return list(DEFAULT_INJECT_FILES)

    marker = "## Injection Template"
    if marker not in text:
        return list(DEFAULT_INJECT_FILES)

    section = text.split(marker, 1)[1]
    lines: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            break
        if not line.startswith("-"):
            continue
        item = line[1:].strip()
        if "—" in item:
            item = item.split("—", 1)[0].strip()
        if item.upper().endswith("MAIN SESSION ONLY") and "-" in item:
            item = item.rsplit("-", 1)[0].strip()
        if item.startswith("`") and "`" in item[1:]:
            item = item.split("`", 2)[1].strip()
        if item:
            lines.append(item)

    return lines or list(DEFAULT_INJECT_FILES)


def _read_injected_docs(cwd: Path) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for rel_path in _load_injection_template(cwd):
        path = cwd / rel_path
        if not path.exists() or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            continue
        if not content:
            continue
        heading = path.stem.replace("_", " ").replace("-", " ").title()
        if path.name == "codex_legend.md":
            heading = "Legend"
        blocks.append((heading, content))
    return blocks


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

    injected_docs = _read_injected_docs(ws)

    blocks = ["# Codex Layer Active (Hermes Plugin)"]
    for heading, content in injected_docs:
        blocks += [f"## {heading}", content]
    if cached.get("supermap"):
        blocks += ["## Supermap", "```", cached["supermap"], "```"]
    if cached.get("memory"):
        blocks += ["## Memory Boot Index", cached["memory"]]

    return "\n\n".join(blocks).strip()


def _on_session_start(**kwargs: Any) -> None:
    sid = str(kwargs.get("session_id") or "")
    if sid:
        _SESSION_CACHE.pop(sid, None)
    catchup = _find_session_to_extract(current_session_id=sid)
    if catchup is not None:
        _dispatch_extraction(catchup, reason="session_start_catchup")


def _on_session_finalize(**kwargs: Any) -> None:
    global _LAST_FINALIZED_SESSION_ID
    sid = str(kwargs.get("session_id") or "")
    _LAST_FINALIZED_SESSION_ID = sid or None


def _on_session_reset(**kwargs: Any) -> None:
    global _LAST_FINALIZED_SESSION_ID
    previous_sid = _LAST_FINALIZED_SESSION_ID
    _LAST_FINALIZED_SESSION_ID = None
    if not previous_sid:
        return
    session_path = _session_file_for(previous_sid)
    if session_path is None:
        _log("warn", "No session file found for finalized session", {"session_id": previous_sid})
        return
    _dispatch_extraction(session_path, reason="session_reset")


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
    ctx.register_hook("on_session_finalize", _on_session_finalize)
    ctx.register_hook("on_session_reset", _on_session_reset)
    ctx.register_hook("pre_llm_call", _pre_llm_call)
