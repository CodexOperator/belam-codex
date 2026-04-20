#!/usr/bin/env python3
"""CLI registry loader for orchestration slice 1.

Loads ``state/cli_registry.yaml`` and exposes helpers for resolving
symbolic CLI references into concrete launch specs.

Authoring format is YAML (see decision 1 in the implementation brief).
A compiled JSON cache path is left as a future-extension point.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError as e:  # pragma: no cover — PyYAML is required for slice 1
    raise RuntimeError("PyYAML required for cli_registry") from e


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = REPO_ROOT / "state" / "cli_registry.yaml"

SUPPORTED_SCHEMA_VERSIONS = {1}


class RegistryError(RuntimeError):
    """Raised for registry loading / resolution errors."""


_cache: dict[str, dict[str, Any]] = {}


def _resolve_path(path: str | os.PathLike | None) -> Path:
    if path is None:
        return DEFAULT_REGISTRY_PATH
    return Path(path)


def load_registry(path: str | os.PathLike | None = None, *, use_cache: bool = True) -> dict:
    """Load the CLI registry YAML file and return its parsed dict."""
    p = _resolve_path(path)
    key = str(p.resolve()) if p.exists() else str(p)
    if use_cache and key in _cache:
        return _cache[key]
    if not p.exists():
        raise RegistryError(f"CLI registry not found: {p}")
    try:
        data = yaml.safe_load(p.read_text()) or {}
    except yaml.YAMLError as e:
        raise RegistryError(f"Invalid YAML in registry {p}: {e}") from e
    if not isinstance(data, dict):
        raise RegistryError(f"Registry root must be a mapping ({p})")
    schema = data.get("schema_version", 1)
    if schema not in SUPPORTED_SCHEMA_VERSIONS:
        raise RegistryError(
            f"Unsupported registry schema_version={schema}; expected one of "
            f"{sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    data.setdefault("clis", {})
    data.setdefault("aliases", {})
    data.setdefault("defaults", {})
    data.setdefault("role_contexts", {})
    _cache[key] = data
    return data


def clear_cache() -> None:
    _cache.clear()


def list_clis(registry: dict | None = None) -> list[str]:
    reg = registry or load_registry()
    return sorted(reg.get("clis", {}).keys())


def resolve_alias(name: str, registry: dict | None = None) -> str:
    """If ``name`` is a known alias, return its target CLI key; else return ``name``."""
    reg = registry or load_registry()
    aliases = reg.get("aliases", {}) or {}
    seen: set[str] = set()
    cur = name
    # Follow up to 8 alias hops to defeat accidental cycles.
    for _ in range(8):
        if cur in seen:
            raise RegistryError(f"CLI alias cycle detected starting at '{name}'")
        seen.add(cur)
        target = aliases.get(cur)
        if target is None:
            return cur
        cur = target
    raise RegistryError(f"CLI alias resolution exceeded depth for '{name}'")


def resolve_cli_spec(name: str, registry: dict | None = None) -> dict:
    """Resolve ``name`` (CLI key or alias) to a concrete spec dict.

    Returned dict is a shallow copy of the registry entry merged with
    registry-level defaults for ``launcher``, ``question_strategy``,
    and ``task_entry`` when the entry does not set them.
    """
    reg = registry or load_registry()
    cli_key = resolve_alias(name, reg)
    clis = reg.get("clis", {}) or {}
    if cli_key not in clis:
        raise RegistryError(
            f"Unknown CLI '{name}' (resolved to '{cli_key}'); "
            f"known: {sorted(clis.keys())}"
        )
    entry = dict(clis[cli_key])
    entry["name"] = cli_key
    defaults = reg.get("defaults", {}) or {}
    for key in ("launcher", "question_strategy", "task_entry", "cockpit_mode"):
        entry.setdefault(key, defaults.get(key))
    # Ensure list fields are lists (never None).
    entry["default_args"] = list(entry.get("default_args") or [])
    return entry


def role_context(role: str, registry: dict | None = None) -> list[str]:
    reg = registry or load_registry()
    return list((reg.get("role_contexts") or {}).get(role, []))


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys

    reg = load_registry()
    if len(sys.argv) > 1:
        spec = resolve_cli_spec(sys.argv[1], reg)
        print(json.dumps(spec, indent=2, sort_keys=True))
    else:
        print(json.dumps({
            "schema_version": reg.get("schema_version"),
            "clis": list_clis(reg),
            "aliases": reg.get("aliases"),
            "defaults": reg.get("defaults"),
        }, indent=2, sort_keys=True))
