#!/usr/bin/env python3
"""
knowledge_quality_gate.py — Auto-promote lessons/decisions through the knowledge pipeline.

Promotion levels (one-directional, never demotes):
  exploratory → candidate → promoted → validated (human-only)

Promotion rules:
  → candidate: body sections are well-populated (≥20 words each, ≥3 sections)
  → promoted:  candidate AND referenced by other primitives (upstream/downstream links)
  validated:   never auto-set, requires explicit human tag

Auto-computes doctrine_richness (0-10):
  +2 per well-populated body section
  +1 per upstream/downstream link (capped at 3)
  +1 if body word count > 200

Usage:
  python3 scripts/knowledge_quality_gate.py            # Run promotions
  python3 scripts/knowledge_quality_gate.py --dry-run   # Preview only
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
LESSONS_DIR = WORKSPACE / "lessons"
DECISIONS_DIR = WORKSPACE / "decisions"

PROMOTION_ORDER = ["exploratory", "candidate", "promoted", "validated"]

# Expected body sections per primitive type
EXPECTED_SECTIONS = {
    "lesson": ["Context", "What Happened", "Lesson", "Application"],
    "decision": ["Context", "Options Considered", "Decision", "Consequences"],
}

# Minimum well-populated sections required for candidate promotion
MIN_SECTIONS_FOR_CANDIDATE = 3


def parse_frontmatter(filepath: Path) -> tuple[dict, str, str]:
    """Parse YAML frontmatter. Returns (fm_dict, body, raw_text)."""
    text = filepath.read_text()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)", text, re.DOTALL)
    if not m:
        return {}, text, text
    fm_raw = m.group(1)
    body = m.group(2)
    fm = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if v.startswith("["):
                raw = v.strip("[]")
                fm[k] = [t.strip().strip('"').strip("'") for t in raw.split(",") if t.strip()]
            else:
                fm[k] = v.strip('"').strip("'")
    return fm, body, text


def update_frontmatter_field(text: str, field: str, value) -> str:
    """Update a single YAML frontmatter field in raw text. Adds before closing --- if missing."""
    if isinstance(value, list):
        yaml_val = "[" + ", ".join(str(v) for v in value) + "]"
    else:
        yaml_val = str(value)

    pattern = rf"^({re.escape(field)}\s*:).*$"
    new_line = f"{field}: {yaml_val}"
    updated, count = re.subn(pattern, new_line, text, count=1, flags=re.MULTILINE)

    if count > 0:
        return updated

    # Field doesn't exist — insert before closing ---
    parts = text.split("---\n", 2)
    if len(parts) >= 3:
        return parts[0] + "---\n" + parts[1] + f"{field}: {yaml_val}\n---\n" + parts[2]
    return text


def extract_sections(body: str) -> dict[str, str]:
    """Extract ## sections from body text. Returns {heading: content}."""
    sections = {}
    current_heading = None
    current_lines = []

    for line in body.splitlines():
        heading_match = re.match(r"^##\s+(.+)", line)
        if heading_match:
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines)
            current_heading = heading_match.group(1).strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines)

    return sections


def is_placeholder(text: str) -> bool:
    """Check if section text is just template placeholder."""
    stripped = text.strip()
    if not stripped:
        return True
    if stripped.startswith("_") and stripped.endswith("_"):
        return True
    if stripped.startswith("(") and stripped.endswith(")"):
        return True
    return False


def word_count(text: str) -> int:
    """Count words, excluding markdown formatting."""
    clean = re.sub(r"[#*_\[\]\(\)`]", " ", text)
    return len(clean.split())


def section_is_populated(content: str) -> bool:
    """A section is populated if non-placeholder and ≥20 words."""
    return not is_placeholder(content) and word_count(content) >= 20


def compute_richness(fm: dict, body: str, sections: dict[str, str]) -> int:
    """Compute doctrine_richness score (0-10)."""
    score = 0

    # +2 per well-populated section
    for content in sections.values():
        if section_is_populated(content):
            score += 2

    # +1 per upstream/downstream link, capped at 3
    upstream = fm.get("upstream", [])
    downstream = fm.get("downstream", [])
    if isinstance(upstream, str):
        upstream = [upstream] if upstream else []
    if isinstance(downstream, str):
        downstream = [downstream] if downstream else []
    score += min(len(upstream) + len(downstream), 3)

    # +1 if body word count > 200
    if word_count(body) > 200:
        score += 1

    return min(score, 10)


def check_candidate_eligibility(fm: dict, body: str, sections: dict[str, str]) -> bool:
    """Check if a primitive qualifies for candidate status."""
    primitive_type = fm.get("primitive", "lesson")
    expected = EXPECTED_SECTIONS.get(primitive_type, [])

    if expected:
        populated = sum(1 for name in expected if section_is_populated(sections.get(name, "")))
    else:
        populated = sum(1 for content in sections.values() if section_is_populated(content))

    return populated >= MIN_SECTIONS_FOR_CANDIDATE


def check_promoted_eligibility(fm: dict, slug: str, all_primitives: dict) -> bool:
    """Check if a candidate qualifies for promoted status.

    True if this file has non-empty upstream/downstream links,
    or another primitive references this slug in its upstream/downstream.
    """
    upstream = fm.get("upstream", [])
    downstream = fm.get("downstream", [])
    if isinstance(upstream, str):
        upstream = [upstream] if upstream else []
    if isinstance(downstream, str):
        downstream = [downstream] if downstream else []
    if upstream or downstream:
        return True

    for other_slug, (other_fm, _, _) in all_primitives.items():
        if other_slug == slug:
            continue
        other_up = other_fm.get("upstream", [])
        other_down = other_fm.get("downstream", [])
        if isinstance(other_up, str):
            other_up = [other_up] if other_up else []
        if isinstance(other_down, str):
            other_down = [other_down] if other_down else []
        for link in other_up + other_down:
            if slug in link:
                return True

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Auto-promote lessons/decisions and compute doctrine richness.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Load all primitives
    all_primitives = {}  # slug → (fm, body, raw_text)
    file_paths = {}      # slug → Path

    for directory in [LESSONS_DIR, DECISIONS_DIR]:
        if not directory.exists():
            continue
        for f in sorted(directory.glob("*.md")):
            slug = f.stem
            fm, body, raw_text = parse_frontmatter(f)
            if fm:
                all_primitives[slug] = (fm, body, raw_text)
                file_paths[slug] = f

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Knowledge Quality Gate")
    print(f"  Loaded {len(all_primitives)} primitives")
    print(f"  Timestamp: {now}\n")

    promotions = []       # (slug, old_status, new_status)
    richness_updates = [] # (slug, old_richness, new_richness)

    for slug, (fm, body, raw_text) in all_primitives.items():
        current_status = fm.get("promotion_status", "exploratory")
        current_richness = int(fm.get("doctrine_richness", "0"))
        sections = extract_sections(body)

        # Compute richness
        new_richness = compute_richness(fm, body, sections)
        if new_richness != current_richness:
            richness_updates.append((slug, current_richness, new_richness))

        # Check promotions (one-directional)
        current_idx = PROMOTION_ORDER.index(current_status) if current_status in PROMOTION_ORDER else 0
        new_status = current_status

        if current_idx < 1:  # exploratory → candidate?
            if check_candidate_eligibility(fm, body, sections):
                new_status = "candidate"

        if current_idx < 2 and (new_status == "candidate" or current_status == "candidate"):
            if check_promoted_eligibility(fm, slug, all_primitives):
                new_status = "promoted"

        if new_status != current_status:
            promotions.append((slug, current_status, new_status))

    # --- Apply changes ---
    files_modified = set()

    if richness_updates:
        print(f"Doctrine Richness Updates ({len(richness_updates)}):")
        for slug, old, new in richness_updates:
            print(f"  {slug}: {old} → {new}")
            if not args.dry_run:
                path = file_paths[slug]
                text = path.read_text()
                text = update_frontmatter_field(text, "doctrine_richness", new)
                path.write_text(text)
                files_modified.add(slug)

    if promotions:
        print(f"\nPromotions ({len(promotions)}):")
        for slug, old, new in promotions:
            print(f"  {slug}: {old} → {new}")
            if not args.dry_run:
                path = file_paths[slug]
                text = path.read_text()
                text = update_frontmatter_field(text, "promotion_status", new)
                path.write_text(text)
                files_modified.add(slug)
    else:
        print("No promotions.")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Richness updates: {len(richness_updates)}")
    print(f"  Promotions: {len(promotions)}")
    print(f"  Files modified: {len(files_modified)}")


if __name__ == "__main__":
    main()
