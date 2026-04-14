#!/usr/bin/env python3
"""Install Belam Codex interface bootstrap artifacts.

Installs/refreshes:
1) R wrapper -> ~/.local/bin/R
2) Hermes plugin bridge -> ~/.hermes/plugins/openclaw_hooks
3) OpenClaw cockpit plugin -> ~/.openclaw/extensions/codex-cockpit

Goal: keep supermap + legend/cockpit behavior reproducible on fresh machines.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
RETIRED_UNIT_SUFFIX = ".retired"


def resolve_workspace() -> Path:
    """Resolve preferred workspace path with local-first Hermes fallback order."""
    cwd = Path.cwd()
    if (cwd / "scripts" / "codex_engine.py").is_file():
        return cwd

    env_candidates = [
        os.environ.get("BELAM_WORKSPACE"),
        os.environ.get("OPENCLAW_WORKSPACE"),
        os.environ.get("WORKSPACE"),
    ]
    for value in env_candidates:
        if value:
            p = Path(value).expanduser()
            if (p / "scripts" / "codex_engine.py").is_file():
                return p

    preferred = HOME / ".hermes" / "belam-codex"
    legacy = HOME / ".openclaw" / "workspace"

    for candidate in (preferred, legacy):
        if (candidate / "scripts" / "codex_engine.py").is_file():
            return candidate

    return preferred


def install_r_wrapper(local_bin: Path) -> Path:
    source = REPO_ROOT / "bin" / "R"
    if not source.is_file():
        raise FileNotFoundError(f"Missing R wrapper template: {source}")
    local_bin.mkdir(parents=True, exist_ok=True)
    target = local_bin / "R"
    shutil.copy2(source, target)
    target.chmod(0o755)
    return target


def install_hermes_plugin(hermes_home: Path) -> Path:
    source_plugin = REPO_ROOT / "local_plugins" / "openclaw_hooks" / "plugin.py"
    if not source_plugin.is_file():
        raise FileNotFoundError(f"Missing Hermes plugin source: {source_plugin}")

    target_dir = hermes_home / "plugins" / "openclaw_hooks"
    target_dir.mkdir(parents=True, exist_ok=True)

    plugin_body = source_plugin.read_text(encoding="utf-8")
    (target_dir / "__init__.py").write_text(plugin_body, encoding="utf-8")
    (target_dir / "plugin.py").write_text(plugin_body, encoding="utf-8")
    (target_dir / "plugin.yaml").write_text(
        "\n".join(
            [
                "name: openclaw_hooks",
                "version: 0.2.0",
                "description: Hermes bridge for OpenClaw supermap/bootstrap prompt context injection.",
                "author: belam-codex",
                "provides_hooks:",
                "  - on_session_start",
                "  - pre_llm_call",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return target_dir


def install_openclaw_plugin(openclaw_home: Path) -> Path:
    source_dir = REPO_ROOT / "plugins" / "codex-cockpit"
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Missing OpenClaw plugin source: {source_dir}")

    target_dir = openclaw_home / "extensions" / "codex-cockpit"
    target_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("index.ts", "openclaw.plugin.json"):
        src = source_dir / filename
        if not src.is_file():
            raise FileNotFoundError(f"Missing OpenClaw plugin file: {src}")
        shutil.copy2(src, target_dir / filename)

    return target_dir


def systemd_user_dir() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")).expanduser()
    return config_home / "systemd" / "user"


def write_text_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def install_user_systemd_units(systemd_dir: Path, workspace: Path) -> list[Path]:
    systemd_dir.mkdir(parents=True, exist_ok=True)
    log_path = workspace / "logs" / "reactive_daemon.log"
    unit_path = systemd_dir / "openclaw-reactive.service"
    content = "\n".join(
        [
            "[Unit]",
            "Description=OpenClaw Reactive Daemon (Belam Codex bootstrap)",
            "After=openclaw-gateway.service",
            "",
            "[Service]",
            f"ExecStart=/usr/bin/python3 {workspace / 'scripts' / 'reactive_daemon.py'} --loop --interval 30 --queue-spacing 1h",
            "Restart=always",
            "RestartSec=10",
            "TimeoutStopSec=15",
            "Environment=PYTHONUNBUFFERED=1",
            f"Environment=BELAM_WORKSPACE={workspace}",
            f"Environment=OPENCLAW_WORKSPACE={workspace}",
            f"WorkingDirectory={workspace}",
            f"StandardOutput=append:{log_path}",
            f"StandardError=append:{log_path}",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )
    write_text_if_changed(unit_path, content)
    return [unit_path]


def retire_codex_render_unit(systemd_dir: Path) -> Path | None:
    unit_path = systemd_dir / "codex-render.service"
    retired_path = systemd_dir / f"{unit_path.name}{RETIRED_UNIT_SUFFIX}"
    if not unit_path.exists():
        return retired_path if retired_path.exists() else None
    if retired_path.exists():
        archived_path = systemd_dir / f"{retired_path.name}.prev"
        shutil.move(str(retired_path), str(archived_path))
    if not unit_path.exists():
        return None
    shutil.move(str(unit_path), str(retired_path))
    return retired_path


def run_systemctl(*args: str) -> bool:
    result = subprocess.run(
        ["systemctl", "--user", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Belam Codex interface bootstrap artifacts")
    parser.add_argument("--skip-r", action="store_true", help="Skip installing ~/.local/bin/R")
    parser.add_argument("--skip-hermes", action="store_true", help="Skip installing Hermes openclaw_hooks plugin")
    parser.add_argument("--skip-openclaw", action="store_true", help="Skip installing OpenClaw codex-cockpit plugin")
    parser.add_argument("--skip-systemd", action="store_true", help="Skip managing ~/.config/systemd/user units")
    parser.add_argument("--skip-systemctl", action="store_true", help="Write unit files but do not run systemctl --user")
    parser.add_argument("--workspace", default="", help="Optional workspace override for verification output")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser() if args.workspace else resolve_workspace()
    local_bin = Path(os.environ.get("XDG_BIN_HOME", HOME / ".local" / "bin")).expanduser()
    hermes_home = Path(os.environ.get("HERMES_HOME", HOME / ".hermes")).expanduser()
    openclaw_home = Path(os.environ.get("OPENCLAW_HOME", HOME / ".openclaw")).expanduser()
    user_systemd_dir = systemd_user_dir()

    print(f"workspace={workspace}")

    if not args.skip_r:
        target = install_r_wrapper(local_bin)
        print(f"installed R wrapper -> {target}")

    if not args.skip_hermes:
        target = install_hermes_plugin(hermes_home)
        print(f"installed Hermes plugin -> {target}")

    if not args.skip_openclaw:
        target = install_openclaw_plugin(openclaw_home)
        print(f"installed OpenClaw plugin -> {target}")

    if not args.skip_systemd:
        targets = install_user_systemd_units(user_systemd_dir, workspace)
        for target in targets:
            print(f"installed systemd unit -> {target}")

        if not args.skip_systemctl:
            render_disabled = run_systemctl("disable", "--now", "codex-render.service")
            print(f"systemctl disable codex-render.service -> {'ok' if render_disabled else 'failed'}")

        retired = retire_codex_render_unit(user_systemd_dir)
        if retired:
            print(f"retired systemd unit -> {retired}")

        if not args.skip_systemctl:
            daemon_reloaded = run_systemctl("daemon-reload")
            print(f"systemctl daemon-reload -> {'ok' if daemon_reloaded else 'failed'}")

            reactive_enabled = run_systemctl("enable", "--now", "openclaw-reactive.service")
            print(f"systemctl enable openclaw-reactive.service -> {'ok' if reactive_enabled else 'failed'}")

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
