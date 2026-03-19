#!/usr/bin/env python3
"""
create_primitive.py — Unified primitive creator for the workspace.

Creates new primitives (lessons, decisions, tasks, projects, commands, skills)
with proper frontmatter templates and triggers embed_primitives.py.

Usage:
  python3 scripts/create_primitive.py lesson "Title here" --tags tag1,tag2 --confidence high --project snn-applied-finance
  python3 scripts/create_primitive.py decision "Title here" --tags tag1,tag2 --status accepted --skill skill-name --project proj
  python3 scripts/create_primitive.py task "Title here" --tags tag1,tag2 --priority critical --depends task1,task2 --project proj
  python3 scripts/create_primitive.py project "Title here" --tags tag1,tag2 --status active
  python3 scripts/create_primitive.py skill "skill-name" --tags tag1,tag2 --desc "Short description"

Auto-linking flags:
  --skill <name>    Explicitly link the new primitive to a specific skill (skip auto-detection)
  --no-link         Skip auto-linking entirely
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", Path.home() / ".openclaw" / "workspace"))
SKILLS_DIR = WORKSPACE / "skills"
KNOWLEDGE_DIR = WORKSPACE / "knowledge"

PRIMITIVE_DIRS = {
    "lesson": WORKSPACE / "lessons",
    "decision": WORKSPACE / "decisions",
    "task": WORKSPACE / "tasks",
    "project": WORKSPACE / "projects",
    "command": WORKSPACE / "commands",
}


# ── Slug generation ────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert title to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)   # remove special chars
    text = re.sub(r"[\s_]+", "-", text)     # spaces/underscores → hyphens
    text = re.sub(r"-+", "-", text)         # collapse multiple hyphens
    text = text.strip("-")
    return text


# ── Frontmatter builders ───────────────────────────────────────────────────────

def _tags_yaml(tags_str: str) -> str:
    """Convert comma-separated tags string to YAML list."""
    if not tags_str:
        return "[]"
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    return "[" + ", ".join(tags) + "]"


def build_lesson_frontmatter(title: str, args: argparse.Namespace) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tags = _tags_yaml(args.tags or "")
    lines = [
        "---",
        "primitive: lesson",
        f"date: {today}",
        f"source: (add source)",
        f"confidence: {args.confidence or '?'}",
    ]
    if args.project:
        lines.append(f"project: {args.project}")
    lines.append(f"tags: {tags}")
    lines.append("---")
    return "\n".join(lines)


def build_decision_frontmatter(title: str, args: argparse.Namespace) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tags = _tags_yaml(args.tags or "")
    lines = [
        "---",
        "primitive: decision",
        f"status: {args.status or 'proposed'}",
        f"date: {today}",
        "context: (add context)",
        "alternatives: []",
        "rationale: (add rationale)",
        "consequences: []",
    ]
    if args.project:
        lines.append(f"project: {args.project}")
    if args.skill:
        lines.append(f"skill: {args.skill}")
    lines.append(f"tags: {tags}")
    lines.append("---")
    return "\n".join(lines)


def build_task_frontmatter(title: str, args: argparse.Namespace) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tags = _tags_yaml(args.tags or "")
    lines = [
        "---",
        "primitive: task",
        f"status: open",
        f"priority: {args.priority or 'medium'}",
        f"created: {today}",
        "owner: belam",
    ]
    if args.project:
        lines.append(f"project: {args.project}")
    if args.depends:
        deps = [d.strip() for d in args.depends.split(",") if d.strip()]
        lines.append("depends_on: [" + ", ".join(deps) + "]")
    else:
        lines.append("depends_on: []")
    lines.append(f"tags: {tags}")
    lines.append("---")
    return "\n".join(lines)


def build_project_frontmatter(title: str, args: argparse.Namespace) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tags = _tags_yaml(args.tags or "")
    lines = [
        "---",
        "primitive: project",
        f"status: {args.status or 'active'}",
        f"start_date: {today}",
        "owner: belam",
        f"tags: {tags}",
        "---",
    ]
    return "\n".join(lines)


def build_command_frontmatter(title: str, args: argparse.Namespace) -> str:
    tags = _tags_yaml(args.tags or "")
    cmd = args.command or f"belam {slugify(title)}"
    aliases_list = [a.strip() for a in (args.aliases or "").split(",") if a.strip()]
    aliases = "[" + ", ".join(f'"{a}"' for a in aliases_list) + "]" if aliases_list else "[]"
    desc = args.desc or "(add description)"
    category = args.category or "infrastructure"
    lines = [
        "---",
        "primitive: command",
        f'command: "{cmd}"',
        f"aliases: {aliases}",
        f'description: "{desc}"',
        f"category: {category}",
        f"tags: {tags}",
        "---",
    ]
    return "\n".join(lines)


def build_knowledge_frontmatter(name: str, args: argparse.Namespace) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tags = _tags_yaml(args.tags or "")
    desc = args.desc or "(add description)"
    lines = [
        "---",
        "primitive: knowledge",
        f"name: {name}",
        f'description: "{desc}"',
        f"tags: {tags}",
        f"created: {today}",
        "---",
    ]
    return "\n".join(lines)


def build_skill_decision_frontmatter(skill_name: str, args: argparse.Namespace) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tags_list = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    # Add the skill name as a tag if not already present
    if skill_name not in tags_list:
        tags_list.insert(0, skill_name)
    tags = "[" + ", ".join(tags_list) + "]"
    title = f"{skill_name.replace('-', ' ').title()} Skill"
    lines = [
        "---",
        "primitive: decision",
        f"status: accepted",
        f"date: {today}",
        f"context: Created skill {skill_name}",
        "alternatives: []",
        f"rationale: (describe why this skill was extracted)",
        "consequences: []",
        f"skill: {skill_name}",
        f"tags: {tags}",
        "---",
    ]
    return "\n".join(lines)


# ── Body builders ─────────────────────────────────────────────────────────────

def build_lesson_body(title: str) -> str:
    return f"""
# {title}

## Context

_What was happening? What problem or situation triggered this?_

## What Happened

_Describe the event, experiment, or observation._

## Lesson

_The core insight. Single crisp sentence if possible._

## Application

_When does this lesson apply? What should change going forward?_
""".lstrip()


def build_decision_body(title: str) -> str:
    return f"""
# {title}

## Context

_What problem or situation prompted this decision?_

## Options Considered

- **Option A:** ...
- **Option B:** ...

## Decision

_State the decision clearly._

## Consequences

_What follows from this choice? Trade-offs, risks, next steps._
""".lstrip()


def build_task_body(title: str) -> str:
    return f"""
# {title}

## Description

_What needs to be done and why._

## Acceptance Criteria

- [ ] ...
- [ ] ...

## Notes

_Any relevant context, links, or constraints._
""".lstrip()


def build_project_body(title: str) -> str:
    return f"""
# {title}

## Overview

_What is this project? One-paragraph summary._

## Goals

- ...
- ...

## Status

_Current state. What's done, what's in progress, what's blocked._
""".lstrip()


def build_command_body(title: str, args: argparse.Namespace) -> str:
    cmd = args.command or f"belam {slugify(title)}"
    desc = args.desc or "(describe what this command does)"
    return f"""# {cmd}

{desc}

## Usage

```bash
{cmd} [args]
```

## Related

- (add related decisions, skills, or scripts)
""".lstrip()


def build_knowledge_body(name: str, args: argparse.Namespace) -> str:
    display = name.replace("-", " ").title()
    desc = args.desc or f"(describe what {name} covers)"
    return f"""# {display}

## Overview

{desc}

## Key Concepts

_Core principles, formulas, or reference material._

## Patterns & Code

_Reusable patterns, snippets, or workflows._

```python
# Example
```

## References

_Papers, libraries, and external resources._
""".lstrip()


def build_skill_md_body(skill_name: str, desc: str) -> str:
    display = skill_name.replace("-", " ").title()
    desc_line = desc or f"(describe what {skill_name} is for)"
    return f"""# SKILL.md — {display}

## Description

{desc_line}

## When to Use

_List the scenarios where this skill applies. Be specific about trigger phrases or task types._

- Use when: ...
- Use when: ...
- NOT for: ...

## Commands / Patterns

_Key commands, API calls, code snippets, or workflow steps._

```bash
# Example command
```

## References

_Links, docs, related decisions, and external resources._

- Decision: `decisions/{skill_name}-skill.md`
""".lstrip()


def build_skill_decision_body(skill_name: str, desc: str) -> str:
    display = skill_name.replace("-", " ").title()
    desc_line = desc or f"Extracted skill for {skill_name}."
    return f"""# {display} Skill

{desc_line}

## Why This Skill

_Describe the reasoning behind extracting this as a skill._

## Scope

_What knowledge, patterns, and capabilities live in this skill?_

## Location

`skills/{skill_name}/SKILL.md`
""".lstrip()


# ── Main creation logic ────────────────────────────────────────────────────────

def create_lesson(title: str, args: argparse.Namespace) -> list[tuple[Path, str]]:
    slug = slugify(title)
    path = PRIMITIVE_DIRS["lesson"] / f"{slug}.md"
    frontmatter = build_lesson_frontmatter(title, args)
    body = build_lesson_body(title)
    content = frontmatter + "\n\n" + body
    return [(path, content)]


def create_decision(title: str, args: argparse.Namespace) -> list[tuple[Path, str]]:
    slug = slugify(title)
    path = PRIMITIVE_DIRS["decision"] / f"{slug}.md"
    frontmatter = build_decision_frontmatter(title, args)
    body = build_decision_body(title)
    content = frontmatter + "\n\n" + body
    return [(path, content)]


def create_task(title: str, args: argparse.Namespace) -> list[tuple[Path, str]]:
    slug = slugify(title)
    path = PRIMITIVE_DIRS["task"] / f"{slug}.md"
    frontmatter = build_task_frontmatter(title, args)
    body = build_task_body(title)
    content = frontmatter + "\n\n" + body
    return [(path, content)]


def create_project(title: str, args: argparse.Namespace) -> list[tuple[Path, str]]:
    slug = slugify(title)
    path = PRIMITIVE_DIRS["project"] / f"{slug}.md"
    frontmatter = build_project_frontmatter(title, args)
    body = build_project_body(title)
    content = frontmatter + "\n\n" + body
    return [(path, content)]


def create_command(title: str, args: argparse.Namespace) -> list[tuple[Path, str]]:
    slug = slugify(title)
    path = PRIMITIVE_DIRS["command"] / f"{slug}.md"
    frontmatter = build_command_frontmatter(title, args)
    body = build_command_body(title, args)
    content = frontmatter + "\n\n" + body
    return [(path, content)]


def create_skill(name: str, args: argparse.Namespace) -> list[tuple[Path, str]]:
    """Creates skill directory + SKILL.md + decision primitive."""
    skill_slug = slugify(name)
    desc = args.desc or ""

    skill_dir = SKILLS_DIR / skill_slug
    skill_md_path = skill_dir / "SKILL.md"
    skill_md_content = build_skill_md_body(skill_slug, desc)

    decision_path = PRIMITIVE_DIRS["decision"] / f"{skill_slug}-skill.md"
    decision_frontmatter = build_skill_decision_frontmatter(skill_slug, args)
    decision_body = build_skill_decision_body(skill_slug, desc)
    decision_content = decision_frontmatter + "\n\n" + decision_body

    return [
        (skill_md_path, skill_md_content),
        (decision_path, decision_content),
    ]


# ── Auto-linking helpers ───────────────────────────────────────────────────────

def _get_skill_tags(skill_dir: Path) -> set[str]:
    """Extract tags from a skill's SKILL.md frontmatter."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return set()
    text = skill_md.read_text(encoding="utf-8")
    m = re.search(r'^tags:\s*\[([^\]]*)\]', text, re.MULTILINE)
    if not m:
        return set()
    return {t.strip().strip('"\'') for t in m.group(1).split(",") if t.strip()}


def _get_skill_category(skill_dir: Path) -> str:
    """Try to get a category from the skill's SKILL.md."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return ""
    text = skill_md.read_text(encoding="utf-8")
    m = re.search(r'^category:\s*(.+)', text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _find_section(text: str, section_names: list[str]) -> str | None:
    """Return the first matching section heading found in text."""
    for name in section_names:
        if re.search(rf'^##\s+{re.escape(name)}\s*$', text, re.MULTILINE):
            return name
    return None


def _append_to_section(text: str, section: str, line: str) -> str:
    """
    Append `line` under the first occurrence of `## section` heading.
    Inserts before the next ## heading or at end of section block.
    """
    pattern = re.compile(rf'^(##\s+{re.escape(section)}\s*\n)', re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return text

    insert_pos = m.end()
    # Find end of this section (next ## heading)
    rest = text[insert_pos:]
    next_section = re.search(r'^##\s+', rest, re.MULTILINE)
    if next_section:
        # Insert before the next section
        section_end = insert_pos + next_section.start()
        # Strip trailing blank lines before insert
        block = text[insert_pos:section_end].rstrip()
        return text[:insert_pos] + block + "\n" + line + "\n\n" + text[section_end:]
    else:
        # Append at end of file
        return text.rstrip() + "\n" + line + "\n"


def find_matching_skills(primitive_type: str, tags: set[str], category: str = "", skill_name: str = "") -> list[tuple[Path, int]]:
    """
    Find skills whose tags overlap with the given tags, or whose name/category matches.
    Returns list of (skill_dir, score) sorted by descending score.
    """
    if not SKILLS_DIR.exists():
        return []

    results = []
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
            continue
        if skill_name and skill_dir.name != skill_name:
            continue  # If explicit skill specified, filter to that one

        skill_tags = _get_skill_tags(skill_dir)
        overlap = len(tags & skill_tags)
        score = overlap

        # Bonus for category matching skill name
        if category and (category.lower() in skill_dir.name.lower() or skill_dir.name.lower() in category.lower()):
            score += 2

        if score > 0:
            results.append((skill_dir, score))

    return sorted(results, key=lambda x: -x[1])


def auto_link_command(cmd_name: str, cmd_desc: str, tags: set[str], category: str,
                      explicit_skill: str = "", no_link: bool = False) -> list[str]:
    """
    After creating a command primitive, link it to matching skills.
    Returns list of human-readable messages about what was linked.
    """
    if no_link:
        return []

    linked = []
    matches = find_matching_skills("command", tags, category, explicit_skill)

    for skill_dir, score in matches:
        skill_md_path = skill_dir / "SKILL.md"
        text = skill_md_path.read_text(encoding="utf-8")

        # Skip if already referenced
        if f"commands/{cmd_name}.md" in text or f"`belam {cmd_name}`" in text:
            continue

        ref_line = f"- `commands/{cmd_name}.md` — {cmd_desc}"

        # Try to find appropriate section
        section = _find_section(text, ["CLI Commands", "Related Commands", "Related"])
        if section:
            new_text = _append_to_section(text, section, ref_line)
        else:
            # Append a new Related Commands section
            new_text = text.rstrip() + f"\n\n## Related Commands\n\n{ref_line}\n"

        skill_md_path.write_text(new_text, encoding="utf-8")
        rel = skill_dir.relative_to(WORKSPACE)
        linked.append(f"  🔗 Linked to {rel}/SKILL.md (score: {score})")

    return linked


def auto_link_lesson_or_decision(prim_type: str, prim_path: Path, tags: set[str],
                                  explicit_skill: str = "", no_link: bool = False) -> list[str]:
    """
    After creating a lesson or decision primitive, cross-link to matching skills.
    Returns list of human-readable messages about what was linked.
    """
    if no_link:
        return []

    linked = []
    matches = find_matching_skills(prim_type, tags, "", explicit_skill)
    rel_prim = prim_path.relative_to(WORKSPACE)

    for skill_dir, score in matches:
        skill_md_path = skill_dir / "SKILL.md"
        text = skill_md_path.read_text(encoding="utf-8")

        # Skip if already referenced
        if str(rel_prim) in text or prim_path.stem in text:
            continue

        ref_line = f"- `{rel_prim}`"

        # Try to find appropriate section
        section = _find_section(text, ["Related Primitives", "Related", "References"])
        if section:
            new_text = _append_to_section(text, section, ref_line)
        else:
            new_text = text.rstrip() + f"\n\n## Related Primitives\n\n{ref_line}\n"

        skill_md_path.write_text(new_text, encoding="utf-8")
        rel = skill_dir.relative_to(WORKSPACE)
        linked.append(f"  🔗 Linked to {rel}/SKILL.md (score: {score})")

    return linked


CREATORS = {
    "lesson": create_lesson,
    "decision": create_decision,
    "task": create_task,
    "project": create_project,
    "command": create_command,
    "skill": create_skill,
}


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create workspace primitives with proper frontmatter and scaffolding."
    )
    parser.add_argument(
        "type",
        choices=list(CREATORS.keys()),
        help="Primitive type to create.",
    )
    parser.add_argument("title", help="Title or name for the primitive.")

    # Shared options
    parser.add_argument("--tags", default="", help="Comma-separated tags.")
    parser.add_argument("--project", default="", help="Associated project slug.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created without writing.")

    # Lesson options
    parser.add_argument("--confidence", default="", help="Lesson confidence level (high/medium/low/?).")

    # Decision options
    parser.add_argument("--status", default="", help="Status (e.g. accepted, proposed, rejected).")
    parser.add_argument("--skill", default="", help="Associated skill name.")

    # Task options
    parser.add_argument("--priority", default="", help="Task priority (critical/high/medium/low).")
    parser.add_argument("--depends", default="", help="Comma-separated task dependencies.")

    # Command options
    parser.add_argument("--command", default="", help="Full command string (e.g. 'belam revise <ver>').")
    parser.add_argument("--aliases", default="", help="Comma-separated aliases (e.g. 'belam rev').")
    parser.add_argument("--category", default="", help="Command category (pipeline/memory/primitives/infrastructure/analysis).")

    # Skill options
    parser.add_argument("--desc", default="", help="Short description (used for skill, decision, and command).")

    # Auto-linking options
    parser.add_argument("--no-link", action="store_true", help="Skip auto-linking to skills.")

    return parser.parse_args()


def main():
    args = parse_args()
    primitive_type = args.type
    title = args.title

    creator = CREATORS[primitive_type]
    files = creator(title, args)

    if args.dry_run:
        print(f"\n🔮 DRY RUN — would create {len(files)} file(s):\n")
        for path, content in files:
            print(f"  📄 {path}")
            print("  " + "─" * 60)
            # Show first 20 lines of content
            preview_lines = content.split("\n")[:20]
            for line in preview_lines:
                print(f"  {line}")
            if len(content.split("\n")) > 20:
                print(f"  ... ({len(content.split(chr(10))) - 20} more lines)")
            print()
        print("  (No files written — remove --dry-run to create.)\n")
        return

    created = []
    for path, content in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            print(f"  ⚠️  Already exists: {path}")
            print("     Use 'belam edit' to modify existing primitives.")
            continue
        path.write_text(content, encoding="utf-8")
        created.append(path)

    if not created:
        sys.exit(1)

    for path in created:
        rel = path.relative_to(WORKSPACE) if path.is_relative_to(WORKSPACE) else path
        print(f"  ✅ Created: {rel}")

    # ── Auto-linking ───────────────────────────────────────────────────────────
    no_link = getattr(args, "no_link", False)
    explicit_skill = getattr(args, "skill", "") or ""
    tags_set = {t.strip() for t in (args.tags or "").split(",") if t.strip()}
    linked_messages: list[str] = []

    if not no_link and primitive_type in ("command", "lesson", "decision"):
        for path in created:
            # Only process workspace-relative files (skip SKILL.md inside skills/)
            if not path.is_relative_to(WORKSPACE):
                continue

            if primitive_type == "command":
                fm_category = getattr(args, "category", "") or ""
                fm_desc = getattr(args, "desc", "") or title
                cmd_name = path.stem
                msgs = auto_link_command(
                    cmd_name, fm_desc, tags_set, fm_category,
                    explicit_skill=explicit_skill, no_link=no_link,
                )
                linked_messages.extend(msgs)

            elif primitive_type in ("lesson", "decision"):
                msgs = auto_link_lesson_or_decision(
                    primitive_type, path, tags_set,
                    explicit_skill=explicit_skill, no_link=no_link,
                )
                linked_messages.extend(msgs)

    if linked_messages:
        print()
        print("  Auto-links added:")
        for msg in linked_messages:
            print(msg)

    # Trigger embed index update
    try:
        sys.path.insert(0, str(WORKSPACE / "scripts"))
        import trigger_embed
        trigger_embed.trigger(background=True)
    except Exception:
        pass  # Non-fatal — embed will run on next heartbeat


if __name__ == "__main__":
    main()
