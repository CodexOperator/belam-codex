#!/usr/bin/env python3
"""
migrate_promotion_fields.py — Add promotion_status, doctrine_richness, and contradicts
to all lessons/decisions.

Adds three new YAML frontmatter fields with defaults:
  - promotion_status: exploratory
  - doctrine_richness: 0
  - contradicts: []

Preserves all existing content. Safe to run multiple times (idempotent).

Usage:
  python3 scripts/migrate_promotion_fields.py            # Migrate all
  python3 scripts/migrate_promotion_fields.py --dry-run   # Preview only
"""

import argparse
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
LESSONS_DIR = WORKSPACE / "lessons"
DECISIONS_DIR = WORKSPACE / "decisions"

# Fields to add and their default YAML representations
DEFAULTS = [
    ("promotion_status", "exploratory"),
    ("doctrine_richness", "0"),
    ("contradicts", "[]"),
]


def parse_frontmatter_raw(text: str) -> tuple[str | None, str | None, str | None]:
    """Split file into (opener '---\\n', frontmatter-body, closer '---\\n' + rest).

    Returns (None, None, text) if no frontmatter found.
    """
    m = re.match(r"^(---\n)(.*?\n)(---\n?)(.*)", text, re.DOTALL)
    if not m:
        return None, None, text
    return m.group(1), m.group(2), m.group(3) + m.group(4)


def has_field(fm_body: str, field: str) -> bool:
    """Check if a YAML field exists in frontmatter text."""
    return bool(re.search(rf"^{re.escape(field)}\s*:", fm_body, re.MULTILINE))


def add_fields(filepath: Path, dry_run: bool = False) -> dict:
    """Add missing promotion fields to a file. Returns dict of changes made."""
    text = filepath.read_text()
    opener, fm_body, rest = parse_frontmatter_raw(text)

    if opener is None or fm_body is None:
        return {"skipped": True, "reason": "no frontmatter"}

    changes = {}
    new_fm_body = fm_body

    for field, default in DEFAULTS:
        if not has_field(fm_body, field):
            new_fm_body += f"{field}: {default}\n"
            changes[field] = default

    if not changes:
        return {"skipped": True, "reason": "already migrated"}

    if not dry_run:
        new_text = opener + new_fm_body + rest
        filepath.write_text(new_text)

    return {"added": changes}


def main():
    parser = argparse.ArgumentParser(
        description="Add promotion_status, doctrine_richness, and contradicts to all lessons/decisions.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    dirs = []
    if LESSONS_DIR.exists():
        dirs.append(("lessons", LESSONS_DIR))
    if DECISIONS_DIR.exists():
        dirs.append(("decisions", DECISIONS_DIR))

    if not dirs:
        print("No lessons/ or decisions/ directories found.")
        sys.exit(1)

    total_migrated = 0
    total_skipped = 0
    total_already = 0

    for label, directory in dirs:
        files = sorted(directory.glob("*.md"))
        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Processing {label}/ ({len(files)} files)")

        for f in files:
            result = add_fields(f, dry_run=args.dry_run)
            rel = f.relative_to(WORKSPACE)

            if result.get("skipped"):
                reason = result["reason"]
                if reason == "already migrated":
                    total_already += 1
                else:
                    total_skipped += 1
                    print(f"  SKIP {rel}: {reason}")
            else:
                added = result["added"]
                fields_str = ", ".join(f"{k}={v}" for k, v in added.items())
                print(f"  {'WOULD ADD' if args.dry_run else 'ADDED'} {rel}: {fields_str}")
                total_migrated += 1

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Migrated: {total_migrated}")
    print(f"  Already done: {total_already}")
    print(f"  Skipped (no frontmatter): {total_skipped}")


if __name__ == "__main__":
    main()
