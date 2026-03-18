#!/usr/bin/env python3
"""
create_primitive.py — Unified primitive creator for the workspace.

Creates new primitives (lessons, decisions, tasks, projects, skills)
with proper frontmatter templates and triggers embed_primitives.py.

Usage:
  python3 scripts/create_primitive.py lesson "Title here" --tags tag1,tag2 --confidence high --project snn-applied-finance
  python3 scripts/create_primitive.py decision "Title here" --tags tag1,tag2 --status accepted --skill skill-name --project proj
  python3 scripts/create_primitive.py task "Title here" --tags tag1,tag2 --priority critical --depends task1,task2 --project proj
  python3 scripts/create_primitive.py project "Title here" --tags tag1,tag2 --status active
  python3 scripts/create_primitive.py skill "skill-name" --tags tag1,tag2 --desc "Short description"
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", Path.home() / ".openclaw" / "workspace"))
SKILLS_DIR = WORKSPACE / "skills"

PRIMITIVE_DIRS = {
    "lesson": WORKSPACE / "lessons",
    "decision": WORKSPACE / "decisions",
    "task": WORKSPACE / "tasks",
    "project": WORKSPACE / "projects",
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


CREATORS = {
    "lesson": create_lesson,
    "decision": create_decision,
    "task": create_task,
    "project": create_project,
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

    # Skill options
    parser.add_argument("--desc", default="", help="Short description (used for skill and decision).")

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

    # Trigger embed index update
    try:
        sys.path.insert(0, str(WORKSPACE / "scripts"))
        import trigger_embed
        trigger_embed.trigger(background=True)
    except Exception:
        pass  # Non-fatal — embed will run on next heartbeat


if __name__ == "__main__":
    main()
