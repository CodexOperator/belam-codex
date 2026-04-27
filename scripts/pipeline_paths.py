from __future__ import annotations

from pathlib import Path


def path_value(value) -> str | None:
    """Normalize user-supplied path value to string, preserving relativity."""
    if value is None:
        return None
    return str(value)


def resolve_workspace_path(workspace: Path, value) -> Path | None:
    """Resolve relative paths under workspace; keep absolute paths absolute."""
    raw = path_value(value)
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else workspace / path


def workspace_relative_path(workspace: Path, value) -> str | None:
    """Prefer workspace-relative string when possible, else absolute."""
    if value is None:
        return None
    path = Path(value)
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def pipeline_builds_frontmatter_value(workspace: Path, override, default_dir: Path) -> str:
    """Frontmatter value for pipeline_builds_dir."""
    if override:
        return path_value(override)
    return workspace_relative_path(workspace, default_dir)


def pipeline_builds_dir_from_meta(workspace: Path, meta: dict, *fallback_dirs: Path) -> Path:
    """Resolve pipeline builds dir from frontmatter, else fallback dirs."""
    raw = meta.get('pipeline_builds_dir') or meta.get('builds_dir')
    if raw:
        resolved = resolve_workspace_path(workspace, raw)
        if resolved is not None:
            return resolved

    for fallback in fallback_dirs:
        if fallback is not None:
            return fallback

    return workspace / 'pipeline_builds'


def state_file_candidates(base_dir: Path, version: str) -> list[Path]:
    """State file candidates in priority order for one builds dir."""
    return [
        base_dir / version / '_state.json',
        base_dir / f'{version}_state.json',
    ]
