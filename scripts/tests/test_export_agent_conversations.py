#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from export_agent_conversations import process_session


def test_process_session_hermes_defaults_to_belam(tmp_path):
    session_file = tmp_path / "session.jsonl"
    rows = [
        {"role": "session_meta", "content": "metadata", "timestamp": "2026-04-13T10:00:00Z"},
        {"role": "user", "content": "hello", "timestamp": "2026-04-13T10:00:01Z"},
        {"role": "assistant", "content": "hi", "timestamp": "2026-04-13T10:00:02Z"},
    ]
    session_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    messages = process_session(session_file, "belam-main", hermes_mode=True)

    assert [m["speaker"] for m in messages] == ["👤 User", "🔮 Belam"]


def test_process_session_preserves_explicit_provenance(tmp_path):
    session_file = tmp_path / "session.jsonl"
    rows = [
        {
            "role": "user",
            "content": "please review",
            "timestamp": "2026-04-13T10:00:01Z",
            "provenance": {"kind": "inter_session", "sourceAgentId": "critic"},
        }
    ]
    session_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    messages = process_session(session_file, "belam-main", hermes_mode=True)

    assert len(messages) == 1
    assert messages[0]["speaker"] == "📨 From critic"


def test_hermes_export_writes_each_session_once(tmp_path):
    state_dir = tmp_path / "sessions"
    output_dir = tmp_path / "out"
    state_dir.mkdir()

    for idx in range(2):
        session_file = state_dir / f"20260413_10000{idx}_abc{idx}.jsonl"
        rows = [
            {"role": "user", "content": f"hello {idx}", "timestamp": "2026-04-13T10:00:01Z"},
            {"role": "assistant", "content": f"hi {idx}", "timestamp": "2026-04-13T10:00:02Z"},
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    script = Path(__file__).parent.parent / "export_agent_conversations.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--state-dir",
            str(state_dir),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    exported = sorted(output_dir.glob("*.md"))
    assert len(exported) == 2
    assert all("belam-main" in path.name for path in exported)
