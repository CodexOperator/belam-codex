import importlib.util
import json
import os
import subprocess
from pathlib import Path


PLUGIN_PATH = Path(__file__).resolve().parents[1] / "local_plugins" / "openclaw_hooks" / "plugin.py"
EXTRACT_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "extract_session_memory.sh"
FINALIZER_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "finalize_memory_extraction.py"
PARSE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "parse_session_transcript.py"
SPEC = importlib.util.spec_from_file_location("test_openclaw_hooks_plugin_module", PLUGIN_PATH)
plugin = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(plugin)


def _session_file(sessions_dir: Path, session_id: str) -> Path:
    path = sessions_dir / f"{session_id}.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    return path


def test_find_session_to_extract_skips_current_and_completed(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    sessions_dir = tmp_path / "sessions"
    memory_dir = workspace / "memory"
    memory_dir.mkdir(parents=True)
    sessions_dir.mkdir(parents=True)

    current = "20260415_100000_current"
    completed = "20260414_090000_done"
    eligible = "20260413_080000_todo"

    _session_file(sessions_dir, current)
    _session_file(sessions_dir, completed)
    eligible_path = _session_file(sessions_dir, eligible)

    (memory_dir / "pending_extraction.json").write_text(
        json.dumps(
            {
                "status": "complete",
                completed: {"status": "complete", "primitives": ["lesson/example"]},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(plugin, "_workspace", lambda: workspace)
    monkeypatch.setattr(plugin, "_sessions_dir", lambda: sessions_dir)
    plugin._EXTRACTION_DISPATCHED.clear()

    selected = plugin._find_session_to_extract(current_session_id=current)

    assert selected == eligible_path



def test_on_session_reset_dispatches_finalized_session(monkeypatch):
    dispatched = []
    plugin._EXTRACTION_DISPATCHED.clear()
    plugin._LAST_FINALIZED_SESSION_ID = None

    monkeypatch.setattr(plugin, "_dispatch_extraction", lambda session_path, reason: dispatched.append((session_path, reason)))
    monkeypatch.setattr(plugin, "_session_file_for", lambda session_id: Path(f"/tmp/{session_id}.jsonl"))

    plugin._on_session_finalize(session_id="old-session")
    plugin._on_session_reset(session_id="new-session")

    assert dispatched == [(Path("/tmp/old-session.jsonl"), "session_reset")]
    assert plugin._LAST_FINALIZED_SESSION_ID is None



def test_on_session_start_catches_up_previous_unextracted_session(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    sessions_dir = tmp_path / "sessions"
    (workspace / "memory").mkdir(parents=True)
    sessions_dir.mkdir(parents=True)

    previous = _session_file(sessions_dir, "20260414_090000_prev")
    _session_file(sessions_dir, "20260415_100000_current")

    dispatched = []
    plugin._EXTRACTION_DISPATCHED.clear()
    plugin._LAST_FINALIZED_SESSION_ID = None
    monkeypatch.setattr(plugin, "_workspace", lambda: workspace)
    monkeypatch.setattr(plugin, "_sessions_dir", lambda: sessions_dir)
    monkeypatch.setattr(plugin, "_dispatch_extraction", lambda session_path, reason: dispatched.append((session_path, reason)))

    plugin._on_session_start(session_id="20260415_100000_current")

    assert dispatched == [(previous, "session_start_catchup")]


def test_recover_pending_extractions_marks_stale_running_entries(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    memory_dir = workspace / "memory"
    memory_dir.mkdir(parents=True)

    stale_session = "20260414_090000_stale"
    active_session = "20260415_100000_active"
    (memory_dir / "pending_extraction.json").write_text(
        json.dumps(
            {
                "status": "running",
                stale_session: {
                    "status": "running",
                    "details": "session_start_catchup",
                    "updated_at": "2026-04-15T09:00:00Z",
                },
                active_session: {
                    "status": "running",
                    "details": "session_reset",
                    "updated_at": "2026-04-15T11:59:40Z",
                },
            }
        ),
        encoding="utf-8",
    )

    plugin._EXTRACTION_DISPATCHED.clear()
    plugin._EXTRACTION_DISPATCHED.update({stale_session, active_session})
    monkeypatch.setattr(plugin, "_workspace", lambda: workspace)
    monkeypatch.setattr(plugin, "_EXTRACTION_STALE_AFTER_SECONDS", 60)
    monkeypatch.setattr(
        plugin,
        "datetime",
        type(
            "FrozenDateTime",
            (),
            {
                "now": staticmethod(lambda tz=None: plugin._parse_pending_timestamp("2026-04-15T12:00:00Z")),
                "fromisoformat": staticmethod(plugin.datetime.fromisoformat),
            },
        ),
    )

    plugin._recover_pending_extractions()

    pending = json.loads((memory_dir / "pending_extraction.json").read_text(encoding="utf-8"))
    assert pending["status"] == "error"
    assert pending[stale_session]["status"] == "error"
    assert pending[stale_session]["details"] == "stale"
    assert pending[active_session]["status"] == "running"
    assert stale_session not in plugin._EXTRACTION_DISPATCHED
    assert active_session in plugin._EXTRACTION_DISPATCHED


def test_dispatch_extraction_recovers_stale_entries_for_reset_runs(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    sessions_dir = tmp_path / "sessions"
    memory_dir = workspace / "memory"
    memory_dir.mkdir(parents=True)
    sessions_dir.mkdir(parents=True)

    stale_session = "20260414_090000_stale"
    new_session = "20260415_100000_new"
    session_path = _session_file(sessions_dir, new_session)
    (memory_dir / "pending_extraction.json").write_text(
        json.dumps(
            {
                "status": "running",
                stale_session: {"status": "running", "updated_at": "2026-04-15T09:00:00Z"},
            }
        ),
        encoding="utf-8",
    )

    plugin._EXTRACTION_DISPATCHED.clear()
    plugin._EXTRACTION_DISPATCHED.add(stale_session)
    monkeypatch.setattr(plugin, "_workspace", lambda: workspace)
    monkeypatch.setattr(plugin, "_sessions_dir", lambda: sessions_dir)
    monkeypatch.setattr(plugin, "_EXTRACTION_STALE_AFTER_SECONDS", 60)
    monkeypatch.setattr(
        plugin,
        "_write_extraction_status_via_script",
        lambda session_id, status, details="", primitives=None: plugin._mark_extraction_status(
            session_id, status, details
        ),
    )
    monkeypatch.setattr(
        plugin,
        "datetime",
        type(
            "FrozenDateTime",
            (),
            {
                "now": staticmethod(lambda tz=None: plugin._parse_pending_timestamp("2026-04-15T12:00:00Z")),
                "fromisoformat": staticmethod(plugin.datetime.fromisoformat),
            },
        ),
    )

    monkeypatch.setattr(
        plugin.subprocess,
        "run",
        lambda *args, **kwargs: type(
            "RunResult",
            (),
            {"returncode": 0, "stdout": "PROMPT_FILE=/tmp/extract.md\n", "stderr": ""},
        )(),
    )
    popen_calls = []
    monkeypatch.setattr(
        plugin.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)) or object(),
    )

    plugin._dispatch_extraction(session_path, reason="session_reset")

    pending = json.loads((memory_dir / "pending_extraction.json").read_text(encoding="utf-8"))
    assert pending[stale_session]["status"] == "error"
    assert pending[stale_session]["details"] == "stale"
    assert pending[new_session]["status"] == "running"
    assert pending[new_session]["details"] == "session_reset"
    assert new_session in plugin._EXTRACTION_DISPATCHED
    assert len(popen_calls) == 1


def test_finalize_memory_extraction_complete_defaults_to_empty_primitives(tmp_path):
    workspace = tmp_path / "workspace"
    memory_dir = workspace / "memory"
    memory_dir.mkdir(parents=True)

    subprocess.run(
        [
            "python3",
            str(FINALIZER_SCRIPT),
            "--session-id",
            "session-123",
            "--status",
            "complete",
        ],
        cwd=str(workspace),
        env={**os.environ, "WORKSPACE": str(workspace)},
        capture_output=True,
        text=True,
        check=True,
    )

    pending = json.loads((memory_dir / "pending_extraction.json").read_text(encoding="utf-8"))
    assert pending["status"] == "complete"
    assert pending["session-123"]["status"] == "complete"
    assert pending["session-123"]["primitives"] == []


def test_finalize_memory_extraction_error_requires_details(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)

    result = subprocess.run(
        [
            "python3",
            str(FINALIZER_SCRIPT),
            "--session-id",
            "session-456",
            "--status",
            "error",
        ],
        cwd=str(workspace),
        env={**os.environ, "WORKSPACE": str(workspace)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "requires --details" in result.stderr


def test_extract_session_memory_prompt_requires_empty_primitives_completion(tmp_path):
    workspace = tmp_path / "workspace"
    scripts_dir = workspace / "scripts"
    memory_dir = workspace / "memory"
    sessions_dir = tmp_path / "sessions"
    scripts_dir.mkdir(parents=True)
    memory_dir.mkdir(parents=True)
    sessions_dir.mkdir(parents=True)

    (scripts_dir / "parse_session_transcript.py").write_text(
        PARSE_SCRIPT.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    session_file = sessions_dir / "session.jsonl"
    session_file.write_text(
        json.dumps(
            {
                "role": "user",
                "content": "Short session with no reusable lessons",
                "timestamp": "2026-04-15T12:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(EXTRACT_SCRIPT), "--instance", "main", "--session-file", str(session_file)],
        cwd=str(workspace),
        env={**os.environ, "WORKSPACE": str(workspace), "HERMES_SESSIONS_DIR": str(sessions_dir)},
        capture_output=True,
        text=True,
        check=True,
    )

    prompt_file = next(
        line.split("=", 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith("PROMPT_FILE=")
    )
    prompt = Path(prompt_file).read_text(encoding="utf-8")

    assert 'python3 scripts/finalize_memory_extraction.py --session-id "session" --status complete' in prompt
    assert "This must result in `primitives: []`." in prompt
    assert '--status error --details "<short reason>"' in prompt
