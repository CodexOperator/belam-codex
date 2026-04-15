import importlib.util
import json
import subprocess
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "orchestrate_memory_extraction.py"
SPEC = importlib.util.spec_from_file_location("test_orchestrate_memory_extraction_module", SCRIPT_PATH)
wrapper = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(wrapper)


def test_build_extraction_session_id_is_fresh():
    first = wrapper.build_extraction_session_id("session-1")
    second = wrapper.build_extraction_session_id("session-1")

    assert first != second
    assert first.startswith("mem-extract-session-1-")
    assert second.startswith("mem-extract-session-1-")


def test_orchestrate_memory_extraction_finalizes_complete_from_wrapper(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    (workspace / "memory").mkdir(parents=True)
    (workspace / "lessons").mkdir(parents=True)
    prompt_file = workspace / "prompt.md"
    prompt_file.write_text("extract something", encoding="utf-8")

    monkeypatch.setattr(
        wrapper,
        "run_extract_prep",
        lambda **kwargs: {"PROMPT_FILE": str(prompt_file), "SESSION_ID": "session-123"},
    )
    monkeypatch.setattr(wrapper, "build_extraction_session_id", lambda session_id: "fresh-session-1")

    def fake_run_agent(**kwargs):
        lesson = workspace / "lessons" / "wrapper-owned.md"
        lesson.write_text("---\nprimitive: lesson\n---\nBody\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=["openclaw"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(wrapper, "run_agent", fake_run_agent)

    result = wrapper.orchestrate_memory_extraction(
        workspace=workspace,
        instance="main",
        reason="session_reset",
    )

    pending = json.loads((workspace / "memory" / "pending_extraction.json").read_text(encoding="utf-8"))
    assert result["status"] == "complete"
    assert result["extraction_session_id"] == "fresh-session-1"
    assert result["primitives"] == ["lessons/wrapper-owned"]
    assert pending["status"] == "complete"
    assert pending["session-123"]["status"] == "complete"
    assert pending["session-123"]["primitives"] == ["lessons/wrapper-owned"]


def test_orchestrate_memory_extraction_finalizes_error_from_wrapper(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    (workspace / "memory").mkdir(parents=True)
    prompt_file = workspace / "prompt.md"
    prompt_file.write_text("extract something", encoding="utf-8")

    monkeypatch.setattr(
        wrapper,
        "run_extract_prep",
        lambda **kwargs: {"PROMPT_FILE": str(prompt_file), "SESSION_ID": "session-456"},
    )
    monkeypatch.setattr(wrapper, "build_extraction_session_id", lambda session_id: "fresh-session-2")
    monkeypatch.setattr(
        wrapper,
        "run_agent",
        lambda **kwargs: subprocess.CompletedProcess(
            args=["openclaw"], returncode=1, stdout="", stderr="agent failed hard"
        ),
    )

    result = wrapper.orchestrate_memory_extraction(
        workspace=workspace,
        instance="main",
        reason="session_start_catchup",
    )

    pending = json.loads((workspace / "memory" / "pending_extraction.json").read_text(encoding="utf-8"))
    assert result["status"] == "error"
    assert "agent failed hard" in result["details"]
    assert pending["status"] == "error"
    assert pending["session-456"]["status"] == "error"
    assert "agent failed hard" in pending["session-456"]["details"]
