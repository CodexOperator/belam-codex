#!/usr/bin/env python3
"""Worker-question relay for orchestration slice 1.

Workers drop question packet files under
``<build_dir>/questions/`` and the orchestrator polls for new packets.
Relay destinations supported: ``main_session``, ``telegram``, ``both``.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from dispatch_adapters import _build_dir  # type: ignore


VALID_RELAYS = {"main_session", "telegram", "both"}


def questions_dir(version: str) -> Path:
    d = _build_dir(version) / "questions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_question(
    *,
    version: str,
    stage: str,
    agent: str,
    cli: str,
    question: str,
    relay: str = "main_session",
    context: dict | None = None,
) -> Path:
    if relay not in VALID_RELAYS:
        raise ValueError(f"invalid relay '{relay}'; expected one of {sorted(VALID_RELAYS)}")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    qid = f"{ts}_{uuid.uuid4().hex[:8]}"
    path = questions_dir(version) / f"{qid}.json"
    payload = {
        "schema_version": 1,
        "id": qid,
        "pipeline": version,
        "stage": stage,
        "agent": agent,
        "cli": cli,
        "question": question,
        "relay": relay,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "context": context or {},
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path


def list_open_questions(version: str) -> list[dict]:
    d = questions_dir(version)
    out: list[dict] = []
    for p in sorted(d.glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        if data.get("status", "open") == "open":
            data["_path"] = str(p)
            out.append(data)
    return out


def answer_question(version: str, qid: str, answer: str) -> Path:
    d = questions_dir(version)
    candidates = list(d.glob(f"{qid}*.json"))
    if not candidates:
        raise FileNotFoundError(f"no question {qid!r} under {d}")
    path = candidates[0]
    data = json.loads(path.read_text())
    data["status"] = "answered"
    data["answer"] = answer
    data["answered_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, indent=2, sort_keys=True))
    return path


def poll_relay_inbox(versions: Iterable[str]) -> list[dict]:
    """Aggregate open questions across multiple pipelines for the orchestrator."""
    buckets: list[dict] = []
    for v in versions:
        buckets.extend(list_open_questions(v))
    return buckets


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--ask", nargs=3, metavar=("STAGE", "AGENT", "TEXT"))
    ap.add_argument("--cli", default="claude")
    ap.add_argument("--relay", default="main_session")
    args = ap.parse_args()
    if args.list:
        print(json.dumps(list_open_questions(args.version), indent=2))
    elif args.ask:
        stage, agent, text = args.ask
        path = write_question(
            version=args.version,
            stage=stage,
            agent=agent,
            cli=args.cli,
            question=text,
            relay=args.relay,
        )
        print(str(path))
