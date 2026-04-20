"""Tests for scripts/dispatch_adapters.py and agent_questions.py (slice 1)."""
from __future__ import annotations

import gzip
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dispatch_adapters as da  # noqa: E402
import agent_questions as aq  # noqa: E402


@pytest.fixture
def patched_build_dirs(tmp_path, monkeypatch):
    ml = tmp_path / "machinelearning" / "pipeline_builds"
    ml.mkdir(parents=True)
    legacy = tmp_path / "pipeline_builds"
    legacy.mkdir()
    monkeypatch.setattr(da, "ML_BUILDS_DIR", ml)
    monkeypatch.setattr(da, "BUILDS_DIR", legacy)
    return ml, legacy


def test_get_adapter_known_and_unknown():
    assert isinstance(da.get_adapter("codex"), da.CodexAdapter)
    assert isinstance(da.get_adapter("claude"), da.ClaudeAdapter)
    assert isinstance(da.get_adapter("openclaw"), da.OpenClawAdapter)
    with pytest.raises(da.AdapterError):
        da.get_adapter("no-such-cli")


def test_codex_build_command_includes_yolo_and_packet(tmp_path):
    runtime = {
        "cli": "codex", "program": "codex", "args": ["--yolo"],
        "task_entry": "file",
    }
    packet = tmp_path / "packet.json"
    packet.write_text("{}")
    cmd = da.CodexAdapter().build_command(runtime, packet, message="hello")
    assert cmd[0] == "codex"
    assert "--yolo" in cmd
    assert str(packet) in cmd


def test_claude_build_command_skip_permissions(tmp_path):
    runtime = {
        "cli": "claude", "program": "claude",
        "args": ["--dangerously-skip-permissions"], "task_entry": "file",
    }
    packet = tmp_path / "p.json"
    packet.write_text("{}")
    cmd = da.ClaudeAdapter().build_command(runtime, packet, message="hi")
    assert "--dangerously-skip-permissions" in cmd


def test_openclaw_build_command_uses_message():
    runtime = {
        "cli": "openclaw", "program": "openclaw", "args": ["agent"],
        "task_entry": "message", "role": "architect",
    }
    cmd = da.OpenClawAdapter().build_command(runtime, Path("/tmp/irrelevant"),
                                              message="boot")
    assert cmd[0] == "openclaw"
    assert "--agent" in cmd and "architect" in cmd
    assert "--message" in cmd and "boot" in cmd


def test_write_task_packet_prefers_ml_build_dir(patched_build_dirs):
    ml, legacy = patched_build_dirs
    (ml / "v1").mkdir()
    runtime = {"cli": "codex", "program": "codex", "args": ["--yolo"],
               "context": [], "launcher": "popen", "task_entry": "file"}
    path = da.write_task_packet("v1", "p1_builder_implement", "builder",
                                 runtime, message="m")
    assert path.exists()
    assert ml in path.parents
    assert legacy not in path.parents
    data = json.loads(path.read_text())
    assert data["pipeline"] == "v1"
    assert data["stage"] == "p1_builder_implement"
    assert data["schema_version"] == 1


def test_dispatch_unknown_program_returns_error(patched_build_dirs):
    ml, _ = patched_build_dirs
    (ml / "v1").mkdir()
    runtime = {"cli": "codex", "program": "definitely-not-a-real-binary-xyz",
               "args": [], "context": [], "launcher": "popen", "task_entry": "file"}
    result = da.dispatch(version="v1", stage="p1_builder_implement",
                          agent="builder", runtime=runtime, message="m")
    assert result["success"] is False
    assert "not found" in (result.get("error") or "")
    # Packet should still have been written.
    assert Path(result["packet"]).exists()


def test_question_write_list_answer(patched_build_dirs):
    ml, _ = patched_build_dirs
    (ml / "v1").mkdir()
    path = aq.write_question(
        version="v1", stage="p1_builder_implement", agent="builder",
        cli="codex", question="Need key?", relay="main_session",
    )
    assert path.exists()
    open_qs = aq.list_open_questions("v1")
    assert len(open_qs) == 1
    qid = open_qs[0]["id"]
    aq.answer_question("v1", qid, "yes")
    assert aq.list_open_questions("v1") == []


def test_append_appendix_writes_entry_and_index(patched_build_dirs):
    ml, _ = patched_build_dirs
    (ml / "v1").mkdir()
    entry = da.append_appendix(
        "v1", stage="p1_builder_implement", text="deferred tmux backend until slice 4",
        kind="defer", agent="builder",
    )
    assert entry.exists()
    body = entry.read_text()
    assert "kind: defer" in body
    assert "deferred tmux backend" in body
    index = da.task_appendix_dir("v1") / "INDEX.md"
    assert index.exists()
    assert entry.name in index.read_text()


def test_append_appendix_rejects_unknown_kind(patched_build_dirs):
    ml, _ = patched_build_dirs
    (ml / "v1").mkdir()
    with pytest.raises(ValueError):
        da.append_appendix("v1", stage="p1_x", text="x", kind="bogus")


def test_archive_old_logs_moves_and_gzips(patched_build_dirs):
    ml, _ = patched_build_dirs
    (ml / "v1").mkdir()
    logs = da.task_log_dir("v1")
    fresh = logs / "20260420T000000Z_fresh.log"
    fresh.write_text("new")
    old = logs / "20260401T000000Z_old.log"
    old.write_text("old body")
    old_epoch = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    os.utime(old, (old_epoch, old_epoch))

    archived = da.archive_old_logs("v1")
    assert len(archived) == 1
    assert archived[0].suffix == ".gz"
    assert not old.exists()
    assert fresh.exists()
    with gzip.open(archived[0], "rb") as fh:
        assert fh.read() == b"old body"

    # Idempotent: second run is a no-op.
    assert da.archive_old_logs("v1") == []


def test_archive_uses_iso_week_bucket(patched_build_dirs):
    ml, _ = patched_build_dirs
    (ml / "v1").mkdir()
    logs = da.task_log_dir("v1")
    p = logs / "20260101T000000Z_stale.log"
    p.write_text("s")
    # Pin mtime to 2026-01-15 → ISO week 2026-W03.
    target = datetime(2026, 1, 15, tzinfo=timezone.utc).timestamp()
    os.utime(p, (target, target))
    archived = da.archive_old_logs("v1", now=datetime(2026, 4, 20, tzinfo=timezone.utc))
    assert len(archived) == 1
    assert "2026-W03" in str(archived[0])


def test_question_invalid_relay_rejected(patched_build_dirs):
    ml, _ = patched_build_dirs
    (ml / "v1").mkdir()
    with pytest.raises(ValueError):
        aq.write_question(version="v1", stage="p1_x", agent="builder",
                          cli="codex", question="?", relay="smoke-signals")
