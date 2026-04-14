#!/usr/bin/env python3
"""
edit_primitive.py — Edit helper with post-edit trigger.

Takes a path like `lessons/my-lesson.md` or just `my-lesson`
with fuzzy matching across all primitive dirs.
Use --set key=value to update frontmatter fields.

Usage:
  python3 scripts/edit_primitive.py lessons/my-lesson.md
  python3 scripts/edit_primitive.py my-lesson --set status=complete --set confidence=high
  python3 scripts/edit_primitive.py task-name --set priority=critical --set tags=snn,gpu
"""

import argparse
import os
import re
import sys
from pathlib import Path

def _resolve_workspace() -> Path:
    candidates = [
        os.environ.get("BELAM_WORKSPACE"),
        os.environ.get("OPENCLAW_WORKSPACE"),
        os.environ.get("WORKSPACE"),
    ]
    for value in candidates:
        if value:
            candidate = Path(value).expanduser()
            if (candidate / "scripts" / "codex_engine.py").is_file():
                return candidate

    cwd = Path.cwd()
    if (cwd / "scripts" / "codex_engine.py").is_file():
        return cwd

    preferred = Path.home() / ".hermes" / "belam-codex"
    legacy = Path.home() / ".openclaw" / "workspace"
    for candidate in (preferred, legacy):
        if (candidate / "scripts" / "codex_engine.py").is_file():
            return candidate
    return preferred


WORKSPACE = _resolve_workspace()

PRIMITIVE_DIRS = [
    WORKSPACE / "lessons",
    WORKSPACE / "decisions",
    WORKSPACE / "tasks",
    WORKSPACE / "projects",
    WORKSPACE / "commands",
    WORKSPACE / "pipelines",
    WORKSPACE / "knowledge",
]


# ── File resolution ────────────────────────────────────────────────────────────

def resolve_path(name: str) -> Path | None:
    """
    Resolve a primitive path from:
    - Absolute path
    - Relative path like lessons/my-lesson.md
    - Bare name with fuzzy match across all primitive dirs
    """
    # Absolute path
    p = Path(name)
    if p.is_absolute() and p.exists():
        return p

    # Relative to workspace
    wp = WORKSPACE / name
    if wp.exists():
        return wp

    # Try with .md extension
    if not name.endswith(".md"):
        wp_md = WORKSPACE / (name + ".md")
        if wp_md.exists():
            return wp_md

    # Bare name — fuzzy search across primitive dirs
    candidates = []
    bare = Path(name).stem  # strip extension if any

    for d in PRIMITIVE_DIRS:
        if not d.is_dir():
            continue
        for f in d.glob("*.md"):
            # Exact match
            if f.stem == bare:
                return f
            # Substring match
            if bare.lower() in f.stem.lower():
                candidates.append(f)

    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        print(f"  ⚠️  Multiple matches for '{name}':")
        for c in candidates:
            rel = c.relative_to(WORKSPACE)
            print(f"       {rel}")
        print("  Tip: Use the full path to be specific.")
        return None

    return None


# ── Frontmatter parsing / updating ────────────────────────────────────────────

def parse_frontmatter(content: str) -> tuple[dict, str, str]:
    """
    Parse YAML frontmatter from markdown content.
    Returns (frontmatter_lines_list, body, raw_fm_block).
    We keep it line-based to preserve comments and ordering.
    """
    if not content.startswith("---"):
        return {}, content, ""

    end = content.find("\n---", 3)
    if end == -1:
        return {}, content, ""

    fm_block = content[3:end].strip()
    body = content[end + 4:].lstrip("\n")

    # Parse key-value pairs (simple, handles quoted and unquoted values)
    fm_dict: dict[str, str] = {}
    fm_lines: list[str] = fm_block.split("\n")
    for line in fm_lines:
        m = re.match(r'^(\w[\w-]*):\s*(.*)', line)
        if m:
            fm_dict[m.group(1)] = m.group(2)

    return fm_dict, body, fm_block


def update_frontmatter(content: str, updates: dict[str, str]) -> tuple[str, list[str]]:
    """
    Apply key=value updates to frontmatter. Returns (new_content, changes).
    Preserves all existing lines, only modifies matching keys or appends new ones.
    """
    if not content.startswith("---"):
        return content, []

    end = content.find("\n---", 3)
    if end == -1:
        return content, []

    fm_raw = content[3:end]
    body = content[end + 4:]

    fm_lines = fm_raw.split("\n")
    changes: list[str] = []
    updated_keys: set[str] = set()

    new_lines: list[str] = []
    for line in fm_lines:
        m = re.match(r'^(\w[\w-]*):\s*(.*)', line)
        if m:
            key = m.group(1)
            old_val = m.group(2)
            if key in updates:
                new_val = updates[key]
                new_line = f"{key}: {new_val}"
                new_lines.append(new_line)
                changes.append(f"{key}: {old_val!r} → {new_val!r}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # Append any keys not already present
    for key, val in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}: {val}")
            changes.append(f"{key}: (new) → {val!r}")

    new_fm = "\n".join(new_lines)
    new_content = "---" + new_fm + "\n---" + body
    return new_content, changes


# ── Tags special handling ──────────────────────────────────────────────────────

def normalize_tags_value(raw: str) -> str:
    """Convert comma-separated tags to YAML list format if needed."""
    raw = raw.strip()
    if raw.startswith("["):
        return raw  # already yaml list
    tags = [t.strip() for t in raw.split(",") if t.strip()]
    return "[" + ", ".join(tags) + "]"


# Fields that should always be stored as YAML lists
LIST_FIELDS = {"tags", "upstream", "downstream", "depends_on", "alternatives", "consequences"}


def normalize_list_value(raw: str) -> str:
    """Convert comma-separated value to YAML list format for list fields."""
    raw = raw.strip()
    if raw.startswith("["):
        return raw  # already yaml list
    items = [i.strip() for i in raw.split(",") if i.strip()]
    return "[" + ", ".join(items) + "]"


# ── CLI ────────────────────────────────────────────────────────────────────────

def _rejoin_list_args(argv: list[str]) -> list[str]:
    """Rejoin shell-split list values in --set arguments.

    The shell splits `--set downstream=[a, b, c]` into multiple tokens.
    This reassembles them by detecting an unclosed `[` and consuming
    subsequent tokens until the closing `]` is found.
    """
    result = []
    i = 0
    while i < len(argv):
        token = argv[i]
        # Check if this is a --set value with an unclosed bracket
        if "=[" in token and "]" not in token:
            # Accumulate until we find the closing ]
            parts = [token]
            i += 1
            while i < len(argv) and "]" not in parts[-1]:
                parts.append(argv[i])
                i += 1
            result.append(" ".join(parts))
        else:
            result.append(token)
            i += 1
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Edit workspace primitives with post-edit index trigger."
    )
    parser.add_argument("name", help="Primitive path or name (fuzzy matched).")
    parser.add_argument(
        "--set",
        action="append",
        metavar="key=value",
        default=[],
        help="Set a frontmatter field. Can be specified multiple times.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without writing.",
    )
    # Pre-process sys.argv to rejoin shell-split list values
    # e.g. --set downstream=[a, b, c] arrives as ['--set', 'downstream=[a,', 'b,', 'c]']
    # We rejoin them so argparse sees: ['--set', 'downstream=[a, b, c]']
    args_fixed = _rejoin_list_args(sys.argv[1:])
    return parser.parse_args(args_fixed)


def main():
    args = parse_args()

    # Resolve file
    target = resolve_path(args.name)
    if target is None:
        print(f"  ❌ Could not find primitive: {args.name!r}")
        print(f"  Searched in: {', '.join(str(d.relative_to(WORKSPACE)) for d in PRIMITIVE_DIRS)}")
        sys.exit(1)

    rel = target.relative_to(WORKSPACE) if target.is_relative_to(WORKSPACE) else target
    print(f"  📄 Found: {rel}")

    content = target.read_text(encoding="utf-8")

    if not args.set:
        # No --set flags: just open for viewing (print content)
        print()
        print(content)
        return

    # Parse updates
    updates: dict[str, str] = {}
    for item in args.set:
        if "=" not in item:
            print(f"  ⚠️  Ignoring invalid --set value (no '='): {item!r}")
            continue
        key, _, val = item.partition("=")
        key = key.strip()
        val = val.strip()
        # Normalize list fields (tags, upstream, downstream, etc.)
        if key in LIST_FIELDS:
            val = normalize_list_value(val)
        updates[key] = val

    if not updates:
        print("  ⚠️  No valid --set values provided.")
        sys.exit(1)

    new_content, changes = update_frontmatter(content, updates)

    if not changes:
        print("  ℹ️  No changes (keys not found in frontmatter — check spelling).")
        sys.exit(0)

    if args.dry_run:
        print(f"\n  🔮 DRY RUN — would apply {len(changes)} change(s) to {rel}:\n")
        for change in changes:
            print(f"    • {change}")
        print("\n  (No files written — remove --dry-run to apply.)\n")
        return

    target.write_text(new_content, encoding="utf-8")
    print(f"  ✅ Updated {rel}:")
    for change in changes:
        print(f"    • {change}")

    # Trigger embed index update
    try:
        sys.path.insert(0, str(WORKSPACE / "scripts"))
        import trigger_embed
        trigger_embed.trigger(background=True)
        print("  📦 Index update triggered")
    except Exception as e:
        print(f"  ⚠️  Index update failed (non-fatal): {e}")


if __name__ == "__main__":
    main()
