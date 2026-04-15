import importlib.util
import json
from pathlib import Path


PLUGIN_PATH = Path(__file__).resolve().parents[1] / "local_plugins" / "openclaw_hooks" / "plugin.py"
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
