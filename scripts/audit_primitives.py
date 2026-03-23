#!/usr/bin/env python3
"""
audit_primitives.py — Scan all primitives for consistency issues.

Checks:
  1. Commands without skill references (orphaned commands)
  2. Skills with stale command lists (R commands referenced but no commands/*.md)
  3. Cross-reference integrity (skill: frontmatter field points to real skill)
  4. Decision primitives for every skill (skill: field in decisions/*.md)
  5. Duplicate/similar primitive names

Usage:
  python3 scripts/audit_primitives.py
  python3 scripts/audit_primitives.py --fix
  python3 scripts/audit_primitives.py --check commands   # Run specific check only
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", Path.home() / ".openclaw" / "workspace"))
SKILLS_DIR = WORKSPACE / "skills"
COMMANDS_DIR = WORKSPACE / "commands"
DECISIONS_DIR = WORKSPACE / "decisions"
LESSONS_DIR = WORKSPACE / "lessons"

# ANSI colors
G = "\033[32m"   # green ✅
Y = "\033[33m"   # yellow ⚠️
R = "\033[31m"   # red ❌
D = "\033[2m"    # dim
B = "\033[1m"    # bold
C = "\033[36m"   # cyan
RST = "\033[0m"


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_frontmatter(path: Path) -> dict:
    """Extract YAML-ish frontmatter fields from a markdown file."""
    fields = {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return fields
    if not text.startswith("---"):
        return fields
    end = text.find("\n---", 3)
    if end == -1:
        return fields
    block = text[3:end]
    for line in block.splitlines():
        m = re.match(r'^(\w+):\s*(.*)', line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            # Strip quotes
            val = val.strip('"\'')
            fields[key] = val
    return fields


def get_tags(path: Path) -> list[str]:
    """Extract tags list from frontmatter."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    m = re.search(r'^tags:\s*\[([^\]]*)\]', text, re.MULTILINE)
    if not m:
        return []
    return [t.strip().strip('"\'') for t in m.group(1).split(",") if t.strip()]


def get_full_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9-]', '-', name.lower().strip()).strip('-')


def skill_name_from_dir(skill_dir: Path) -> str:
    return skill_dir.name


def all_skill_dirs() -> list[Path]:
    if not SKILLS_DIR.exists():
        return []
    return [d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]


def all_command_files() -> list[Path]:
    if not COMMANDS_DIR.exists():
        return []
    return sorted(COMMANDS_DIR.glob("*.md"))


def all_decision_files() -> list[Path]:
    if not DECISIONS_DIR.exists():
        return []
    return sorted(DECISIONS_DIR.glob("*.md"))


def all_lesson_files() -> list[Path]:
    if not LESSONS_DIR.exists():
        return []
    return sorted(LESSONS_DIR.glob("*.md"))


# ── Check 1: Commands without skill references ─────────────────────────────────

def check_commands_referenced(fix: bool = False) -> tuple[list[str], list[str], int]:
    """
    For each commands/*.md, check if command name or alias is mentioned in any skill SKILL.md.
    Returns (ok_lines, warn_lines, issue_count).
    """
    ok_lines = []
    warn_lines = []
    issues = 0

    skill_dirs = all_skill_dirs()
    # Build a map of skill_dir → full SKILL.md text (lowercased for matching)
    skill_texts: dict[Path, str] = {}
    for sd in skill_dirs:
        skill_texts[sd] = get_full_text(sd / "SKILL.md").lower()

    for cmd_file in all_command_files():
        cmd_name = cmd_file.stem  # e.g. "autorun"
        fm = parse_frontmatter(cmd_file)
        cmd_str = fm.get("command", f"R {cmd_name}").lower()
        aliases_raw = fm.get("aliases", "")

        # Build all search tokens: command name, command string, aliases
        tokens = {cmd_name, cmd_str}
        # Parse aliases from YAML list string like ["R auto", "R au"]
        for a in re.findall(r'"([^"]+)"', aliases_raw):
            tokens.add(a.lower())
        # Also add the short alias part (e.g. "auto" from "R auto")
        for a in re.findall(r'"R (\S+)"', aliases_raw):
            tokens.add(a.lower())

        found_in = None
        for sd, text in skill_texts.items():
            for tok in tokens:
                if tok in text:
                    found_in = sd
                    break
            if found_in:
                break

        if found_in:
            rel = found_in.relative_to(WORKSPACE)
            ok_lines.append(f"  {G}✅{RST}  {cmd_name}: referenced in {rel}/SKILL.md")
        else:
            warn_lines.append(f"  {Y}⚠️ {RST}  {cmd_name}: not referenced in any skill SKILL.md")
            issues += 1

            if fix:
                # Try to find the best matching skill by tag overlap
                cmd_tags = set(get_tags(cmd_file))
                cmd_category = fm.get("category", "")
                best_skill = None
                best_score = 0
                for sd in skill_dirs:
                    skill_md = sd / "SKILL.md"
                    skill_tags = set(get_tags(skill_md))
                    overlap = len(cmd_tags & skill_tags)
                    # Bonus if category matches skill name
                    if cmd_category and cmd_category.lower() in sd.name.lower():
                        overlap += 2
                    if overlap > best_score:
                        best_score = overlap
                        best_skill = sd

                if best_skill and best_score > 0:
                    skill_md_path = best_skill / "SKILL.md"
                    skill_text = skill_md_path.read_text(encoding="utf-8")
                    ref_line = f"\n- `commands/{cmd_name}.md` — {fm.get('description', cmd_name)}\n"
                    # Find ## Related Commands or ## Related section, else append
                    if "## Related Commands" in skill_text:
                        skill_text = skill_text.replace(
                            "## Related Commands",
                            f"## Related Commands{ref_line}"
                        )
                    elif "## Related" in skill_text:
                        skill_text = skill_text.replace(
                            "## Related",
                            f"## Related{ref_line}"
                        )
                    else:
                        skill_text = skill_text.rstrip() + f"\n\n## Related Commands\n{ref_line}"
                    skill_md_path.write_text(skill_text, encoding="utf-8")
                    warn_lines[-1] += f"\n    {G}→ Auto-fixed: appended reference to {best_skill.name}/SKILL.md{RST}"

    return ok_lines, warn_lines, issues


# ── Check 2: Skills with stale command references ─────────────────────────────

def check_skill_command_refs(fix: bool = False) -> tuple[list[str], list[str], int]:
    """
    For each skill SKILL.md, find all 'R X' references and check that
    commands/X.md exists.
    Returns (ok_lines, warn_lines, issue_count).
    """
    ok_lines = []
    warn_lines = []
    issues = 0

    existing_commands = {f.stem for f in all_command_files()}

    for sd in all_skill_dirs():
        skill_name = sd.name
        skill_md = sd / "SKILL.md"
        text = get_full_text(skill_md)

        # Find all "R <word>" patterns — looking for real command names
        # Match: backtick-quoted `R X` or in code blocks (``` lines starting with R)
        found_refs = re.findall(r'`R\s+([a-z][a-z0-9-]{2,})`', text)
        # Also find R X at start of a code line (indented or in fenced block)
        found_refs += re.findall(r'^\s+R\s+([a-z][a-z0-9-]{3,})(?:\s|$)', text, re.MULTILINE)
        # Deduplicate; ignore very generic/meta words, single-letter aliases, table headers
        ignore = {
            "help", "create", "new", "edit", "status", "log", "command", "version",
            "run", "use", "see", "get", "set", "list", "show", "check",
        }
        # Also ignore 2-char shortcuts like "pj", "pl", "au", etc.
        refs = sorted(set(
            r for r in found_refs
            if r not in ignore and len(r) >= 3 and not re.match(r'^[a-z]{1,2}$', r)
        ))

        if not refs:
            ok_lines.append(f"  {G}✅{RST}  {skill_name}: no R command references found (ok)")
            continue

        skill_ok = True
        for ref in refs:
            # Check if commands/ref.md exists
            if ref in existing_commands:
                ok_lines.append(f"  {G}✅{RST}  {skill_name}: 'R {ref}' → commands/{ref}.md exists")
            else:
                warn_lines.append(
                    f"  {Y}⚠️ {RST}  {skill_name}: references 'R {ref}' but no commands/{ref}.md exists"
                )
                issues += 1
                skill_ok = False

                if fix:
                    # Create a stub command primitive
                    stub_path = COMMANDS_DIR / f"{ref}.md"
                    stub_content = f"""---
primitive: command
command: "R {ref}"
aliases: []
description: "(stub — auto-created by audit --fix)"
category: {skill_name}
tags: [{skill_name}]
---

# R {ref}

_(Stub — fill in description and usage.)_

## Usage

```bash
R {ref} [args]
```

## Related

- `skills/{skill_name}/SKILL.md`
"""
                    stub_path.write_text(stub_content, encoding="utf-8")
                    warn_lines[-1] += f"\n    {G}→ Auto-fixed: created stub commands/{ref}.md{RST}"

    return ok_lines, warn_lines, issues


# ── Check 3: Cross-reference integrity (skill: frontmatter field) ──────────────

def check_cross_refs() -> tuple[list[str], list[str], int]:
    """
    For any primitive with a 'skill:' field in frontmatter, check the referenced
    skill directory exists.
    """
    ok_lines = []
    warn_lines = []
    issues = 0

    all_skill_names = {sd.name for sd in all_skill_dirs()}
    all_knowledge_names = {f.stem for f in (WORKSPACE / "knowledge").glob("*.md")
                           if parse_frontmatter(f).get("primitive") == "knowledge"} if (WORKSPACE / "knowledge").exists() else set()

    # Scan decisions, lessons
    all_files = list(all_decision_files()) + list(all_lesson_files())
    has_any = False
    for f in all_files:
        fm = parse_frontmatter(f)
        skill_ref = fm.get("skill", "")
        knowledge_ref = fm.get("knowledge", "")
        ref = skill_ref or knowledge_ref
        ref_type = "skill" if skill_ref else "knowledge"
        if not ref:
            continue
        has_any = True
        rel = f.relative_to(WORKSPACE)
        if ref in all_skill_names or ref in all_knowledge_names:
            ok_lines.append(f"  {G}✅{RST}  {rel}: {ref_type}: {ref} → exists")
        else:
            warn_lines.append(
                f"  {Y}⚠️ {RST}  {rel}: {ref_type}: {ref} → not found in skills/ or knowledge/"
            )
            issues += 1

    if not has_any:
        ok_lines.append(f"  {G}✅{RST}  All skill: references valid (none found)")

    return ok_lines, warn_lines, issues


# ── Check 4: Every skill has a decision primitive ─────────────────────────────

def check_skill_decisions() -> tuple[list[str], list[str], int]:
    """
    Check that every skill/ directory has a corresponding decision primitive
    with skill: <name> in its frontmatter.
    """
    ok_lines = []
    warn_lines = []
    issues = 0

    # Build map: skill_name → [decision files that reference it]
    skill_to_decisions: dict[str, list[Path]] = {}
    for f in all_decision_files():
        fm = parse_frontmatter(f)
        skill_ref = fm.get("skill", "")
        if skill_ref:
            skill_to_decisions.setdefault(skill_ref, []).append(f)

    for sd in all_skill_dirs():
        skill_name = sd.name
        if skill_name in skill_to_decisions:
            for dec_path in skill_to_decisions[skill_name]:
                rel = dec_path.relative_to(WORKSPACE)
                ok_lines.append(f"  {G}✅{RST}  {skill_name}: has decision primitive {rel}")
        else:
            warn_lines.append(
                f"  {Y}⚠️ {RST}  {skill_name}: no decision primitive found (no decisions/*.md with skill: {skill_name})"
            )
            issues += 1

    return ok_lines, warn_lines, issues


# ── Check 5: Duplicate/similar primitive names ────────────────────────────────

def check_duplicates() -> tuple[list[str], list[str], int]:
    """
    Flag primitives with very similar names that might be duplicates.
    Uses SequenceMatcher ratio > 0.85 threshold.
    """
    ok_lines = []
    warn_lines = []
    issues = 0
    THRESHOLD = 0.80

    all_prim_dirs = {
        "commands": all_command_files(),
        "decisions": all_decision_files(),
        "lessons": all_lesson_files(),
    }

    for category, files in all_prim_dirs.items():
        stems = [(f.stem, f) for f in files]
        flagged_pairs = set()
        for i, (name_a, path_a) in enumerate(stems):
            for name_b, path_b in stems[i+1:]:
                ratio = SequenceMatcher(None, name_a, name_b).ratio()
                if ratio >= THRESHOLD:
                    pair = tuple(sorted([name_a, name_b]))
                    if pair not in flagged_pairs:
                        flagged_pairs.add(pair)
                        warn_lines.append(
                            f"  {Y}⚠️ {RST}  {category}: '{name_a}' and '{name_b}' are very similar "
                            f"(similarity: {ratio:.0%}) — possible duplicate"
                        )
                        issues += 1

    if not warn_lines:
        ok_lines.append(f"  {G}✅{RST}  No suspiciously similar primitive names found")

    return ok_lines, warn_lines, issues


# ── Reporting ──────────────────────────────────────────────────────────────────

def print_section(title: str, ok_lines: list[str], warn_lines: list[str], verbose: bool):
    print(f"\n{B}{title}{RST}")
    if verbose:
        for line in ok_lines:
            print(line)
    for line in warn_lines:
        print(line)
    if not warn_lines and not verbose:
        total = len(ok_lines)
        print(f"  {G}✅{RST}  All {total} check(s) passed")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Audit workspace primitives for consistency issues."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix issues where possible.",
    )
    parser.add_argument(
        "--check",
        choices=["commands", "skills", "cross-refs", "decisions", "duplicates"],
        help="Run only a specific check.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show passing checks too.",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only show summary line.",
    )
    args = parser.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n{B}🔍 Primitive Audit — {today}{RST}")
    if args.fix:
        print(f"  {Y}⚡ Auto-fix mode enabled{RST}")

    total_issues = 0
    total_fixable = 0

    checks = args.check

    if not checks or checks == "commands":
        ok, warn, n = check_commands_referenced(fix=args.fix)
        total_issues += n
        if args.fix:
            total_fixable += sum(1 for w in warn if "Auto-fixed" in w)
        if not args.quiet:
            print_section("Commands:", ok, warn, args.verbose)

    if not checks or checks == "skills":
        ok, warn, n = check_skill_command_refs(fix=args.fix)
        total_issues += n
        if args.fix:
            total_fixable += sum(1 for w in warn if "Auto-fixed" in w)
        if not args.quiet:
            print_section("Skills:", ok, warn, args.verbose)

    if not checks or checks == "cross-refs":
        ok, warn, n = check_cross_refs()
        total_issues += n
        if not args.quiet:
            print_section("Cross-refs:", ok, warn, args.verbose)

    if not checks or checks == "decisions":
        ok, warn, n = check_skill_decisions()
        total_issues += n
        if not args.quiet:
            print_section("Skill → Decision Primitives:", ok, warn, args.verbose)

    if not checks or checks == "duplicates":
        ok, warn, n = check_duplicates()
        total_issues += n
        if not args.quiet:
            print_section("Duplicates:", ok, warn, args.verbose)

    # Summary
    print()
    if total_issues == 0:
        print(f"{G}{B}✅ No issues found.{RST}")
    else:
        fix_note = f", {total_fixable} auto-fixed" if args.fix and total_fixable else (
            f", {total_issues} potentially auto-fixable (run with --fix)" if not args.fix else ""
        )
        color = Y if total_issues < 5 else R
        print(f"{color}{B}Summary: {total_issues} issue(s) found{fix_note}.{RST}")

    print()
    sys.exit(0 if total_issues == 0 else 1)


if __name__ == "__main__":
    main()
