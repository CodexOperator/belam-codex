#!/usr/bin/env python3
"""Install the local openclaw_hooks bridge plugin into ~/.hermes/plugins."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PLUGIN = REPO_ROOT / "local_plugins" / "openclaw_hooks" / "plugin.py"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()
TARGET_DIR = HERMES_HOME / "plugins" / "openclaw_hooks"

PLUGIN_YAML = """name: openclaw_hooks
version: 0.3.0
description: Hermes bridge for OpenClaw supermap/bootstrap prompt context injection.
author: belam-codex
provides_hooks:
  - on_session_start
  - on_session_finalize
  - on_session_reset
  - pre_llm_call
"""


def install() -> Path:
    if not SOURCE_PLUGIN.exists():
        raise FileNotFoundError(f"Missing source plugin: {SOURCE_PLUGIN}")

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_PLUGIN, TARGET_DIR / "__init__.py")
    (TARGET_DIR / "plugin.py").write_text((TARGET_DIR / "__init__.py").read_text(encoding="utf-8"), encoding="utf-8")
    (TARGET_DIR / "plugin.yaml").write_text(PLUGIN_YAML, encoding="utf-8")
    return TARGET_DIR


if __name__ == "__main__":
    target = install()
    print(target)
