"""Tests for scripts/runtime_resolution.py (slice 1)."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import runtime_resolution as rr  # noqa: E402
from runtime_resolution import deep_merge, resolve_stage_runtime  # noqa: E402


def test_deep_merge_scalars_override():
    assert deep_merge({"a": 1}, {"a": 2}) == {"a": 2}


def test_deep_merge_arrays_replace():
    assert deep_merge({"a": [1, 2]}, {"a": [3]}) == {"a": [3]}


def test_deep_merge_maps_merge():
    result = deep_merge({"a": {"x": 1}}, {"a": {"y": 2}})
    assert result == {"a": {"x": 1, "y": 2}}


def test_deep_merge_none_keeps_base():
    assert deep_merge({"a": 1}, None) == {"a": 1}


def test_resolve_defaults_role_alias():
    rt = resolve_stage_runtime(stage_key="p1_architect_design", role="architect")
    assert rt["cli"] == "claude"
    assert "--dangerously-skip-permissions" in rt["args"]
    assert rt["launcher"] == "popen"
    assert "persona-architect" in rt["context"]


def test_stage_override_wins_over_template():
    template_runtime = {"defaults": {"cli": "openclaw"}}
    task_runtime = {
        "stage_overrides": {
            "p2_builder_analysis_scripts": {"cli": "codex", "args": ["--yolo", "--extra"]}
        }
    }
    rt = resolve_stage_runtime(
        stage_key="p2_builder_analysis_scripts",
        role="builder",
        phase_key="p2",
        template_runtime=template_runtime,
        task_runtime=task_runtime,
    )
    assert rt["cli"] == "codex"
    assert rt["args"].count("--yolo") == 1
    assert "--extra" in rt["args"]


def test_phase_override_precedence():
    task_runtime = {
        "defaults": {"cli": "claude"},
        "phase_overrides": {"p2": {"cli": "codex"}},
    }
    rt = resolve_stage_runtime(
        stage_key="p2_critic_review", role="critic", phase_key="p2",
        task_runtime=task_runtime,
    )
    assert rt["cli"] == "codex"


def test_task_alias_remap():
    task_runtime = {"cli_aliases": {"architect_default": "codex"}}
    rt = resolve_stage_runtime(
        stage_key="p1_architect_design", role="architect", phase_key="p1",
        task_runtime=task_runtime,
    )
    assert rt["cli"] == "codex"


def test_template_stage_def_cli_is_used():
    rt = resolve_stage_runtime(
        stage_key="p1_builder_implement", role="builder", phase_key="p1",
        stage_def={"role": "builder", "action": "implement", "cli": "codex"},
    )
    assert rt["cli"] == "codex"


def test_context_replaced_by_stage_def():
    rt = resolve_stage_runtime(
        stage_key="p1_builder_implement", role="builder", phase_key="p1",
        stage_def={"role": "builder", "action": "implement",
                   "context": ["supermap"]},
    )
    assert rt["context"] == ["supermap"]


def test_template_runtime_stage_overrides_are_applied():
    template_runtime = {
        "defaults": {"launcher": "popen"},
        "stage_overrides": {
            "p1_builder_implement": {
                "cli": "codex",
                "context": ["persona-builder", "supermap", "cockpit", "cavekit"],
            }
        },
    }
    rt = resolve_stage_runtime(
        stage_key="p1_builder_implement",
        role="builder",
        phase_key="p1",
        template_runtime=template_runtime,
    )
    assert rt["cli"] == "codex"
    assert rt["context"] == ["persona-builder", "supermap", "cockpit", "cavekit"]
