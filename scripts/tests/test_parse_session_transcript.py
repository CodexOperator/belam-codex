#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from parse_session_transcript import parse


def test_parse_hermes_flat_jsonl(tmp_path):
    session_file = tmp_path / "hermes.jsonl"
    out_file = tmp_path / "out.md"

    rows = [
        {"role": "user", "content": "hello", "timestamp": "2026-04-13T10:00:00Z"},
        {"role": "assistant", "content": "hi there", "timestamp": "2026-04-13T10:00:01Z"},
    ]
    session_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    count = parse(str(session_file), str(out_file), instance="main")
    content = out_file.read_text(encoding="utf-8")

    assert count == 1
    assert "hermes" in content.lower()
    assert "### 🧑 User" in content
    assert "### 🔮 Belam" in content


def test_parse_openclaw_wrapped_jsonl(tmp_path):
    session_file = tmp_path / "legacy.jsonl"
    out_file = tmp_path / "out.md"

    rows = [
        {"type": "session", "id": "abc123", "timestamp": "2026-04-13T10:00:00Z"},
        {
            "type": "message",
            "timestamp": "2026-04-13T10:00:01Z",
            "message": {"role": "user", "content": [{"type": "text", "text": "legacy hi"}]},
        },
    ]
    session_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    count = parse(str(session_file), str(out_file), instance="architect")
    content = out_file.read_text(encoding="utf-8")

    assert count == 1
    assert "abc123" in content
    assert "legacy hi" in content


def test_parse_hermes_provenance_and_belam_default(tmp_path):
    session_file = tmp_path / "hermes.jsonl"
    out_file = tmp_path / "out.md"

    rows = [
        {"role": "session_meta", "content": "metadata", "timestamp": "2026-04-13T10:00:00Z"},
        {
            "role": "user",
            "content": "forwarded task",
            "timestamp": "2026-04-13T10:00:01Z",
            "provenance": {"kind": "inter_session", "sourceAgentId": "architect"},
        },
        {"role": "assistant", "content": "handled", "timestamp": "2026-04-13T10:00:02Z"},
    ]
    session_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    count = parse(str(session_file), str(out_file), instance="main")
    content = out_file.read_text(encoding="utf-8")

    assert count == 1
    assert "metadata" not in content
    assert "### 📨 From architect" in content
    assert "### 🔮 Belam" in content
