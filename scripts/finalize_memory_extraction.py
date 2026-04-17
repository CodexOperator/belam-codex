#!/usr/bin/env python3
"""Deterministically update memory extraction bookkeeping."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _workspace() -> Path:
    return Path(os.environ.get("WORKSPACE", os.path.expanduser("~/.hermes/belam-codex")))


def _pending_extraction_path(workspace: Path) -> Path:
    return workspace / "memory" / "pending_extraction.json"


def _load_pending_extraction(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def finalize_status(
    *,
    workspace: Path,
    session_id: str,
    status: str,
    details: str = "",
    primitives: list[str] | None = None,
    finalized_at: str = "",
) -> None:
    path = _pending_extraction_path(workspace)
    data = _load_pending_extraction(path)
    entry = data.get(session_id, {}) if isinstance(data.get(session_id), dict) else {}

    entry["status"] = status
    entry["updated_at"] = _utc_now_iso()

    if status == "queued":
        entry["finalized_at"] = finalized_at.strip() or entry.get("finalized_at") or entry["updated_at"]
        entry.pop("details", None)
        entry.pop("primitives", None)
    elif status == "complete":
        entry["primitives"] = primitives or []
        entry.pop("details", None)
    elif status == "error":
        if not details.strip():
            raise ValueError("error status requires --details")
        entry["details"] = details.strip()
        entry.pop("primitives", None)
    else:
        if details.strip():
            entry["details"] = details.strip()
        else:
            entry.pop("details", None)
        entry.pop("primitives", None)

    data[session_id] = entry
    data["status"] = status

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--status", required=True, choices=["queued", "running", "complete", "error"])
    parser.add_argument("--details", default="")
    parser.add_argument("--finalized-at", default="")
    parser.add_argument("--primitive", action="append", default=[])
    args = parser.parse_args()

    try:
        finalize_status(
            workspace=_workspace(),
            session_id=args.session_id,
            status=args.status,
            details=args.details,
            primitives=args.primitive,
            finalized_at=args.finalized_at,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
