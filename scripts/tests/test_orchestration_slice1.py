from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import orchestration_engine as oe
import launch_pipeline as lp


def test_load_task_runtime_from_task_frontmatter(tmp_path, monkeypatch):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    task = tasks_dir / "demo-task.md"
    task.write_text(
        "---\n"
        "primitive: task\n"
        "pipeline: v1\n"
        "pipeline_template_path: templates/builder-first-pipeline.md\n"
        "pipeline_runtime:\n"
        "  defaults:\n"
        "    launcher: popen\n"
        "  stage_overrides:\n"
        "    p1_builder_implement:\n"
        "      cli: claude\n"
        "---\n"
    )
    monkeypatch.setattr(oe, "WORKSPACE", tmp_path)
    runtime = oe._load_task_runtime("v1", {})
    assert runtime is not None
    assert runtime["defaults"]["launcher"] == "popen"
    assert runtime["stage_overrides"]["p1_builder_implement"]["cli"] == "claude"
    assert runtime["pipeline_template_path"] == "templates/builder-first-pipeline.md"


def test_builder_first_template_runtime_preserves_defaults_and_stage_defs():
    oe._template_cache.pop("builder-first", None)
    oe._template_runtime.pop("builder-first", None)
    oe._parse_template_transitions("builder-first")
    runtime = oe._get_template_runtime(template_name="builder-first")
    assert runtime["defaults"]["launcher"] == "popen"
    assert runtime["stage_overrides"]["p1_builder_implement"]["cli"] == "claude"
    assert runtime["stage_overrides"]["p1_critic_review"]["context"] == ["persona-critic", "supermap"]


def test_create_pipeline_materializes_template_runtime(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "builder-first-pipeline.md").write_text(
        "## Stage Transitions\n\n```yaml\n"
        "first_agent: builder\n"
        "type: builder-first\n"
        "runtime:\n"
        "  roles:\n"
        "    builder: { toolsets: [terminal, file] }\n"
        "defaults:\n"
        "  launcher: popen\n"
        "  cockpit_mode: shared\n"
        "phases:\n"
        "  phase1:\n"
        "    humangate: true\n"
        "    stages:\n"
        "      - role: builder\n"
        "        action: implement\n"
        "        session: fresh\n"
        "        cli: claude\n"
        "        context: [persona-builder, supermap, cockpit, cavekit]\n"
        "```\n"
    )

    script = f"""
import json
import sys
from pathlib import Path
sys.path.insert(0, {str(HERE)!r})
import launch_pipeline as lp
import template_parser as tp
root = Path({str(tmp_path)!r})
lp.PIPELINES_DIR = root / 'pipelines'
lp.BUILDS_DIR = root / 'builds'
lp.SPECS_DIR = root / 'specs'
lp.WORKSPACE = root
for d in [lp.PIPELINES_DIR, lp.BUILDS_DIR, lp.SPECS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
tp.TEMPLATES_DIR = root / 'templates'
tp.clear_cache()
lp.create_pipeline('v1', 'demo', pipeline_type='builder-first')
print((lp.BUILDS_DIR / 'v1_state.json').read_text())
"""
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    stdout = proc.stdout
    state_json = stdout[stdout.index('{'):]
    state = json.loads(state_json)
    assert state["template_name"] == "builder-first"
    assert state["template_runtime"]["defaults"]["launcher"] == "popen"
    assert state["template_runtime"]["stage_overrides"]["p1_builder_implement"]["cli"] == "claude"


def test_try_adapter_dispatch_uses_template_stage_runtime(monkeypatch):
    captured = {}

    monkeypatch.setattr(oe, "_HAS_ADAPTERS", True)

    def fake_dispatch(*, version, stage, agent, runtime, message):
        captured.update({
            "version": version,
            "stage": stage,
            "agent": agent,
            "runtime": runtime,
            "message": message,
        })
        return {"success": True, "pid": 123, "error": None}

    monkeypatch.setattr(oe, "_adapter_dispatch", fake_dispatch)
    state = {
        "template_runtime": {
            "defaults": {"launcher": "popen"},
            "stage_overrides": {
                "p1_builder_implement": {
                    "cli": "codex",
                    "context": ["persona-builder", "supermap", "cockpit", "cavekit"],
                }
            },
        }
    }

    result = oe._try_adapter_dispatch("v1", "p1_builder_implement", "builder", "hello", state)
    assert result["success"] is True
    assert captured["runtime"]["cli"] == "codex"
    assert captured["runtime"]["context"] == ["persona-builder", "supermap", "cockpit", "cavekit"]
