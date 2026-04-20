#!/usr/bin/env python3
"""Dispatch adapters for orchestration slice 1.

Each adapter knows how to:
  * turn a resolved runtime dict + task packet into an argv list
  * launch that command via popen (tmux backend is slice 4)
  * provide a hook for worker question relay (routes through
    ``scripts/agent_questions.py`` packet files)
"""
from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILDS_DIR = REPO_ROOT / "pipeline_builds"
ML_BUILDS_DIR = REPO_ROOT / "machinelearning" / "pipeline_builds"


class AdapterError(RuntimeError):
    pass


def _build_dir(version: str) -> Path:
    """Resolve the per-pipeline build dir.

    Prefer ``machinelearning/pipeline_builds/<version>/`` per the new layout
    (decision 12), fall back to the legacy ``pipeline_builds/<version>/``.
    """
    ml_dir = ML_BUILDS_DIR / version
    if ml_dir.exists():
        return ml_dir
    legacy_dir = BUILDS_DIR / version
    if legacy_dir.exists():
        return legacy_dir
    # New pipelines: bias toward the new layout but only if the machinelearning
    # parent already exists (so we don't create an ML tree inside unrelated repos).
    if ML_BUILDS_DIR.exists():
        ml_dir.mkdir(parents=True, exist_ok=True)
        return ml_dir
    legacy_dir.mkdir(parents=True, exist_ok=True)
    return legacy_dir


def write_task_packet(
    version: str, stage: str, agent: str, runtime: dict, message: str
) -> Path:
    """Materialize the per-stage dispatch packet file.

    Returns the path to the written JSON packet.
    """
    build_dir = _build_dir(version)
    packets_dir = build_dir / "dispatch_packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = packets_dir / f"{ts}_{stage}.json"
    payload = {
        "schema_version": 1,
        "pipeline": version,
        "stage": stage,
        "agent": agent,
        "cli": runtime.get("cli"),
        "program": runtime.get("program"),
        "args": list(runtime.get("args") or []),
        "context": list(runtime.get("context") or []),
        "launcher": runtime.get("launcher", "popen"),
        "task_entry": runtime.get("task_entry"),
        "question_strategy": runtime.get("question_strategy"),
        "ask_on_question": runtime.get("ask_on_question"),
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path


# ─── Adapter interface ───────────────────────────────────────────────────

class DispatchAdapter:
    """Base dispatch adapter. Subclasses customize ``build_command``."""

    name: str = "base"

    def build_command(self, runtime: dict, packet_path: Path, message: str) -> list[str]:
        program = runtime.get("program") or self.name
        cmd: list[str] = [program]
        cmd.extend(runtime.get("args") or [])
        # Default task-entry handling: adapters with ``task_entry == "file"`` get
        # the packet path appended; ``task_entry == "message"`` CLIs get the
        # raw message appended via whatever flag they expect (subclasses override).
        if runtime.get("task_entry") == "file":
            cmd.append(str(packet_path))
        elif message:
            cmd.extend(["--message", message])
        return cmd

    def launch_popen(
        self, cmd: list[str], *, cwd: Path | None = None, log_path: Path | None = None
    ) -> dict:
        if not cmd:
            raise AdapterError("Empty command for dispatch")
        program = cmd[0]
        if shutil.which(program) is None:
            return {
                "success": False,
                "pid": None,
                "error": f"{program!r} not found on PATH",
            }
        stdout_target: Any = subprocess.DEVNULL
        stderr_target: Any = subprocess.DEVNULL
        log_fh = None
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_fh = open(log_path, "ab", buffering=0)
            stdout_target = log_fh
            stderr_target = subprocess.STDOUT
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd) if cwd else None,
                stdout=stdout_target,
                stderr=stderr_target,
                start_new_session=True,
            )
            return {"success": True, "pid": proc.pid, "error": None}
        except Exception as e:  # pragma: no cover — surface launch errors
            return {"success": False, "pid": None, "error": str(e)}
        finally:
            # Popen has already inherited the fd; close our reference so we
            # don't keep an extra descriptor pinned in the parent.
            if log_fh is not None:
                try:
                    log_fh.close()
                except Exception:
                    pass

    def launch_tmux(self, *args, **kwargs) -> dict:  # pragma: no cover — slice 4
        return {"success": False, "pid": None, "error": "tmux backend not yet enabled"}


class CodexAdapter(DispatchAdapter):
    name = "codex"


class ClaudeAdapter(DispatchAdapter):
    name = "claude"


class OpenClawAdapter(DispatchAdapter):
    """Legacy adapter — preserves the `openclaw agent --agent X --message M` shape."""

    name = "openclaw"

    def build_command(self, runtime: dict, packet_path: Path, message: str) -> list[str]:
        program = runtime.get("program") or "openclaw"
        args = list(runtime.get("args") or [])
        if "agent" not in args:
            args.insert(0, "agent")
        role = runtime.get("role") or runtime.get("agent")
        cmd = [program, *args]
        if role:
            cmd.extend(["--agent", role])
        if message:
            cmd.extend(["--message", message])
        return cmd


_ADAPTERS: dict[str, DispatchAdapter] = {
    "codex": CodexAdapter(),
    "claude": ClaudeAdapter(),
    "openclaw": OpenClawAdapter(),
}


def register_adapter(name: str, adapter: DispatchAdapter) -> None:
    _ADAPTERS[name] = adapter


def get_adapter(name: str) -> DispatchAdapter:
    try:
        return _ADAPTERS[name]
    except KeyError as e:
        raise AdapterError(f"No dispatch adapter registered for CLI '{name}'") from e


def known_adapters() -> list[str]:
    return sorted(_ADAPTERS.keys())


# ─── Task-level log / appendix helpers (decision 9) ───────────────────────
#
# Layout under ``<build_dir>/``:
#   logs/                per-stage raw stdout/stderr capture files
#   logs/archive/        gzipped logs older than ARCHIVE_AFTER_DAYS (weekly sweep)
#   appendix/            persistent per-task appendix entries (structured notes)
#   appendix/INDEX.md    human-readable index of appendix entries
#
# ``archive_old_logs`` is the weekly sweep: it gzips any ``*.log`` whose mtime
# is older than the cutoff into ``logs/archive/<YYYY-WW>/`` and removes the
# original. Idempotent — running it twice in the same week is a no-op.

ARCHIVE_AFTER_DAYS = 7
APPENDIX_KINDS = {"note", "decision", "defer", "result", "error"}


def task_log_dir(version: str) -> Path:
    d = _build_dir(version) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def task_log_archive_dir(version: str) -> Path:
    d = task_log_dir(version) / "archive"
    d.mkdir(parents=True, exist_ok=True)
    return d


def task_appendix_dir(version: str) -> Path:
    d = _build_dir(version) / "appendix"
    d.mkdir(parents=True, exist_ok=True)
    return d


def stage_log_path(version: str, stage: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return task_log_dir(version) / f"{ts}_{stage}.log"


def append_appendix(
    version: str,
    *,
    stage: str,
    text: str,
    kind: str = "note",
    agent: str | None = None,
) -> Path:
    """Append a structured entry to the per-task appendix.

    Each call creates a dated markdown file and appends a line to
    ``appendix/INDEX.md``. Entries are immutable once written; kind is one of
    ``APPENDIX_KINDS`` (``defer`` is used for deterministic deferred-work notes).
    """
    if kind not in APPENDIX_KINDS:
        raise ValueError(f"Unknown appendix kind {kind!r}; expected one of {sorted(APPENDIX_KINDS)}")
    dir_ = task_appendix_dir(version)
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    fname = f"{ts}_{kind}_{stage}.md"
    entry_path = dir_ / fname
    header = (
        f"---\nkind: {kind}\nstage: {stage}\n"
        + (f"agent: {agent}\n" if agent else "")
        + f"created_at: {now.isoformat()}\n---\n\n"
    )
    entry_path.write_text(header + text.rstrip() + "\n")
    index = dir_ / "INDEX.md"
    index_line = f"- {now.isoformat()} · **{kind}** · `{stage}` → [{fname}]({fname})\n"
    with index.open("a", encoding="utf-8") as fh:
        fh.write(index_line)
    return entry_path


def _iso_week_key(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso.year:04d}-W{iso.week:02d}"


def archive_old_logs(
    version: str,
    *,
    older_than_days: int = ARCHIVE_AFTER_DAYS,
    now: datetime | None = None,
) -> list[Path]:
    """Gzip & move logs older than ``older_than_days`` into weekly buckets.

    Returns the list of archived destination paths. Safe to call repeatedly
    (weekly cron). Skips files already under ``logs/archive/`` and anything
    ending in ``.gz``.
    """
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=older_than_days)
    src_dir = task_log_dir(version)
    archive_root = task_log_archive_dir(version)
    archived: list[Path] = []
    for path in sorted(src_dir.glob("*.log")):
        if not path.is_file():
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if mtime > cutoff:
            continue
        week_dir = archive_root / _iso_week_key(mtime)
        week_dir.mkdir(parents=True, exist_ok=True)
        dest = week_dir / (path.name + ".gz")
        if dest.exists():
            # Already archived with same name — skip to keep idempotent.
            path.unlink()
            continue
        with path.open("rb") as src, gzip.open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.utime(dest, (path.stat().st_atime, path.stat().st_mtime))
        path.unlink()
        archived.append(dest)
    return archived


# ─── Convenience dispatcher used by orchestration_engine ──────────────────

def dispatch(
    *,
    version: str,
    stage: str,
    agent: str,
    runtime: dict,
    message: str,
    cwd: Path | None = None,
) -> dict:
    """End-to-end popen dispatch for a single stage.

    Writes a task packet, picks the right adapter, launches popen, returns a
    result dict with ``success``, ``pid``, ``packet``, ``cmd``, ``log``.
    """
    cli_name = runtime.get("cli") or agent
    adapter = get_adapter(cli_name)
    packet = write_task_packet(version, stage, agent, runtime, message)
    cmd = adapter.build_command(runtime, packet, message)
    log_path = stage_log_path(version, stage)
    if runtime.get("launcher", "popen") != "popen":
        # slice 1 only implements popen; signal that tmux is pending.
        return {
            "success": False,
            "pid": None,
            "error": f"launcher '{runtime.get('launcher')}' not yet implemented",
            "packet": str(packet),
            "cmd": cmd,
            "log": str(log_path),
        }
    result = adapter.launch_popen(cmd, cwd=cwd, log_path=log_path)
    result.update({"packet": str(packet), "cmd": cmd, "log": str(log_path)})
    return result


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps({"adapters": known_adapters()}, indent=2))
