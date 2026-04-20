#!/usr/bin/env python3
"""Runtime resolution for orchestration slice 1.

Combines three override layers into a single resolved runtime dict for a
given (phase, stage, role) triple:

  1. task overrides   (task frontmatter `pipeline_runtime` block)
  2. template runtime (template `runtime` / `defaults` / per-stage fields)
  3. registry defaults (state/cli_registry.yaml)

Deep merge policy (per the implementation brief):
  * scalars -> override
  * arrays  -> replace by default
  * maps    -> deep merge
"""
from __future__ import annotations

import copy
from typing import Any, Iterable

from cli_registry import (
    RegistryError,
    load_registry,
    resolve_cli_spec,
    role_context,
)


def deep_merge(base: Any, overlay: Any) -> Any:
    """Deep-merge ``overlay`` into ``base`` using the documented policy."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        out = dict(base)
        for k, v in overlay.items():
            if k in out:
                out[k] = deep_merge(out[k], v)
            else:
                out[k] = copy.deepcopy(v)
        return out
    # Arrays replace by default. Scalars replace. None lets base stand.
    if overlay is None:
        return copy.deepcopy(base)
    return copy.deepcopy(overlay)


def _layer_defaults(source: dict | None) -> dict:
    """Pull the ``defaults`` sub-dict from a runtime layer, tolerating shape drift."""
    if not isinstance(source, dict):
        return {}
    d = source.get("defaults")
    return dict(d) if isinstance(d, dict) else {}


def _stage_layer(source: dict | None, stage_key: str) -> dict:
    if not isinstance(source, dict):
        return {}
    overrides = source.get("stage_overrides") or {}
    return dict(overrides.get(stage_key) or {})


def _phase_layer(source: dict | None, phase_key: str) -> dict:
    if not isinstance(source, dict):
        return {}
    overrides = source.get("phase_overrides") or {}
    return dict(overrides.get(phase_key) or {})


def _alias_map(source: dict | None) -> dict:
    if not isinstance(source, dict):
        return {}
    aliases = source.get("cli_aliases")
    return dict(aliases) if isinstance(aliases, dict) else {}


def resolve_stage_runtime(
    *,
    stage_key: str,
    role: str,
    action: str | None = None,
    phase_key: str | None = None,
    stage_def: dict | None = None,
    template_runtime: dict | None = None,
    task_runtime: dict | None = None,
    registry: dict | None = None,
    message: str | None = None,
    extra_args: Iterable[str] | None = None,
) -> dict:
    """Return the fully-resolved runtime spec for one stage dispatch.

    Resolution order (low -> high precedence, applied via deep_merge):
      1. registry-level defaults
      2. template `runtime` block + template stage def (``cli`` / ``context``)
      3. task ``pipeline_runtime.defaults``
      4. task ``pipeline_runtime.phase_overrides[phase_key]``
      5. task ``pipeline_runtime.stage_overrides[stage_key]``
    """
    reg = registry if registry is not None else load_registry()

    # ── 1) registry defaults ──────────────────────────────────────────────
    merged: dict[str, Any] = {
        "launcher": (reg.get("defaults") or {}).get("launcher", "popen"),
        "cockpit_mode": (reg.get("defaults") or {}).get("cockpit_mode", "shared"),
        "question_strategy": (reg.get("defaults") or {}).get(
            "question_strategy", "packet_and_relay"
        ),
        "task_entry": (reg.get("defaults") or {}).get("task_entry", "file"),
        "args": [],
        "context": role_context(role, reg),
        "ask_on_question": "main_session",
    }

    # ── 2) template layer ─────────────────────────────────────────────────
    tmpl = template_runtime or {}
    merged = deep_merge(merged, _layer_defaults(tmpl))
    if phase_key is not None:
        merged = deep_merge(merged, _phase_layer(tmpl, phase_key))
    merged = deep_merge(merged, _stage_layer(tmpl, stage_key))
    # Template may name a symbolic CLI on stage_def.
    symbolic_cli: str | None = None
    if stage_def:
        if "cli" in stage_def:
            symbolic_cli = stage_def.get("cli")
        if "context" in stage_def and stage_def["context"] is not None:
            merged["context"] = list(stage_def["context"])
        for k in ("args", "launcher", "ask_on_question", "cockpit_mode"):
            if k in stage_def and stage_def[k] is not None:
                merged = deep_merge(merged, {k: stage_def[k]})

    # ── 3) task defaults ──────────────────────────────────────────────────
    task = task_runtime or {}
    merged = deep_merge(merged, _layer_defaults(task))

    # ── 4) phase overrides ────────────────────────────────────────────────
    if phase_key is not None:
        merged = deep_merge(merged, _phase_layer(task, phase_key))

    # ── 5) stage overrides ────────────────────────────────────────────────
    merged = deep_merge(merged, _stage_layer(task, stage_key))

    # ── CLI resolution ────────────────────────────────────────────────────
    # Priority: stage override `cli` → phase override `cli` → template stage cli
    #        → role alias `<role>_default` → registry alias table
    cli_name = merged.get("cli") or symbolic_cli
    alias_map = {}
    alias_map.update(reg.get("aliases") or {})
    alias_map.update(_alias_map(tmpl))
    alias_map.update(_alias_map(task))
    if not cli_name:
        cli_name = alias_map.get(f"{role}_default") or f"{role}_default"

    # Re-apply the merged alias table so task-level alias rewrites win.
    reg_with_aliases = dict(reg)
    reg_with_aliases["aliases"] = alias_map

    try:
        spec = resolve_cli_spec(cli_name, reg_with_aliases)
    except RegistryError as e:
        raise RegistryError(
            f"Failed to resolve CLI for stage '{stage_key}' (role={role}): {e}"
        ) from e

    merged["cli"] = spec["name"]
    merged["program"] = spec["program"]
    merged["supports_tmux"] = spec.get("supports_tmux", False)
    merged["supports_resume"] = spec.get("supports_resume", False)
    merged["task_entry"] = merged.get("task_entry") or spec.get("task_entry")
    merged["question_strategy"] = (
        merged.get("question_strategy") or spec.get("question_strategy")
    )

    # Arg composition: registry defaults + merged.args + extra_args.
    arg_list: list[str] = []
    arg_list.extend(spec.get("default_args") or [])
    for a in merged.get("args") or []:
        if a not in arg_list:
            arg_list.append(a)
    if extra_args:
        for a in extra_args:
            if a not in arg_list:
                arg_list.append(a)
    merged["args"] = arg_list

    merged["stage_key"] = stage_key
    merged["role"] = role
    if action is not None:
        merged["action"] = action
    if phase_key is not None:
        merged["phase_key"] = phase_key
    if message:
        merged["message"] = message

    return merged


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys

    role = sys.argv[1] if len(sys.argv) > 1 else "builder"
    stage = sys.argv[2] if len(sys.argv) > 2 else "p1_builder_implement"
    out = resolve_stage_runtime(
        stage_key=stage, role=role, phase_key=stage.split("_", 1)[0]
    )
    print(json.dumps(out, indent=2, sort_keys=True))
