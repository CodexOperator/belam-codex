"""Tests for scripts/cli_registry.py (slice 1)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cli_registry  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_cache():
    cli_registry.clear_cache()
    yield
    cli_registry.clear_cache()


def _write_registry(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "cli_registry.yaml"
    p.write_text(body)
    return p


def test_load_registry_defaults_present():
    reg = cli_registry.load_registry()
    assert reg["schema_version"] == 1
    assert "codex" in reg["clis"]
    assert "claude" in reg["clis"]
    assert "openclaw" in reg["clis"]


def test_codex_default_is_yolo():
    spec = cli_registry.resolve_cli_spec("codex")
    assert "--yolo" in spec["default_args"]


def test_claude_default_is_dangerously_skip():
    spec = cli_registry.resolve_cli_spec("claude")
    assert "--dangerously-skip-permissions" in spec["default_args"]


def test_alias_resolution():
    spec = cli_registry.resolve_cli_spec("architect_default")
    assert spec["name"] == "claude"


def test_unknown_cli_raises():
    with pytest.raises(cli_registry.RegistryError):
        cli_registry.resolve_cli_spec("nonexistent-cli-xyz")


def test_unsupported_schema_rejected(tmp_path):
    p = _write_registry(tmp_path, "schema_version: 999\nclis: {}\n")
    with pytest.raises(cli_registry.RegistryError):
        cli_registry.load_registry(p, use_cache=False)


def test_alias_cycle_detected(tmp_path):
    p = _write_registry(
        tmp_path,
        "schema_version: 1\nclis:\n  codex: {program: codex, default_args: []}\n"
        "aliases:\n  a: b\n  b: a\n",
    )
    reg = cli_registry.load_registry(p, use_cache=False)
    with pytest.raises(cli_registry.RegistryError):
        cli_registry.resolve_cli_spec("a", reg)


def test_role_context_lookup():
    ctx = cli_registry.role_context("architect")
    assert "persona-architect" in ctx
