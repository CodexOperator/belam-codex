#!/usr/bin/env python3
"""belam indexed command interface — core engine.

Provides:
  - Root menu rendering with category/command coordinates
  - List rendering with numeric indices
  - Coordinate resolution against saved context
  - Context persistence between invocations
"""

import json
import os
import sys
import re
import subprocess
from pathlib import Path

WORKSPACE = os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace"))
CONTEXT_FILE = os.path.expanduser("~/.belam_last_context")
ROOT_CONTEXT_FILE = os.path.expanduser("~/.belam_root_context")

# ── Colors ────────────────────────────────────────────────────────────────────
B = "\033[1m"
D = "\033[2m"
R = "\033[0m"
C = "\033[36m"
G = "\033[32m"
Y = "\033[33m"
M = "\033[35m"
RD = "\033[31m"
BG_DIM = "\033[48;5;236m"

# ── Command Registry ──────────────────────────────────────────────────────────
# Each category is a letter, each command gets a number within category.
# Format: (display_name, belam_command, description)

COMMAND_REGISTRY = [
    ("PIPELINES", [
        ("pipelines",            "pipelines",             "List all pipelines"),
        ("pipeline <ver>",       "pipeline",              "Detail view for a pipeline"),
        ("orchestrate",          "orchestrate",           "Stage transition (auto-handoff)"),
        ("kickoff <ver>",        "kickoff",               "Kick off a pipeline (wake architect)"),
        ("revise <ver>",         "revise",                "Trigger Phase 1 revision cycle"),
        ("queue-revision <ver>", "queue-revision",        "Queue revision for autorun"),
        ("autorun",              "autorun",               "Auto-kick gated/stalled pipelines"),
        ("cleanup",              "cleanup",               "Kill stale agent sessions"),
        ("handoffs",             "handoffs",              "Check for stuck handoffs"),
    ]),
    ("PRIMITIVES", [
        ("tasks",       "tasks",       "List open tasks"),
        ("lessons",     "lessons",     "List lessons"),
        ("decisions",   "decisions",   "List decisions"),
        ("projects",    "projects",    "List projects"),
        ("agents",      "agents",      "Show agent roster"),
    ]),
    ("CREATE / EDIT", [
        ("create <type> <title>", "create",  "Create a new primitive"),
        ("edit <name>",           "edit",    "Edit a primitive (fuzzy match)"),
    ]),
    ("EXPERIMENTS", [
        ("run <ver>",          "run",           "Run experiments locally"),
        ("analyze <ver>",      "analyze",       "Run experiment analysis"),
        ("analyze-local <ver>","analyze-local",  "Orchestrated local analysis"),
        ("report <ver>",       "report",        "Build LaTeX→PDF report"),
    ]),
    ("MEMORY", [
        ("log <message>",  "log",          "Quick memory entry"),
        ("consolidate",    "consolidate",  "Run memory consolidation"),
    ]),
    ("NOTEBOOKS", [
        ("build <ver>",  "build",      "Build a notebook"),
        ("notebooks",    "notebooks",  "List notebooks"),
    ]),
    ("OTHER", [
        ("conversations",   "conversations",   "Export agent conversations"),
        ("knowledge-sync",  "knowledge-sync",  "Run weekly knowledge sync"),
        ("sync",            "sync",            "Sync workspace → knowledge-repo"),
        ("status",          "status",          "Full overview of everything"),
        ("audit",           "audit",           "Audit primitive consistency"),
        ("transcribe <file>", "transcribe",    "Transcribe audio files"),
    ]),
]

# ── Context Persistence ───────────────────────────────────────────────────────

def save_context(context_type, mapping):
    """Save the current view context for follow-up resolution."""
    try:
        with open(CONTEXT_FILE, "w") as f:
            json.dump({"type": context_type, "mapping": mapping}, f)
    except Exception:
        pass  # Non-critical


def load_context():
    """Load the last saved context."""
    try:
        with open(CONTEXT_FILE) as f:
            return json.load(f)
    except Exception:
        return None


# ── Root Menu ─────────────────────────────────────────────────────────────────

def render_root_menu():
    """Render the full command menu with coordinates."""
    mapping = {}
    letter_idx = 0
    
    print()
    print(f"{B}  🔮 belam{R}  {D}— Workspace CLI{R}")
    print(f"  {D}{'─' * 62}{R}")
    
    for cat_name, commands in COMMAND_REGISTRY:
        letter = chr(ord('a') + letter_idx)
        letter_idx += 1
        print()
        print(f"  {B}{cat_name}{R}")
        
        for i, (display, cmd, desc) in enumerate(commands, 1):
            coord = f"{letter}{i}"
            mapping[coord] = cmd
            print(f"    {C}{coord}{R}  {B}{display:<28s}{R} {D}{desc}{R}")
    
    print()
    print(f"  {D}Type a coordinate to run: {C}belam a1{R}  {D}or{R}  {C}belam b2{R}")
    print(f"  {D}Raw output: add {C}--raw{R}  {D}to any command{R}")
    print()
    
    save_context("root", mapping)
    # Also save root mapping separately so it persists across list views
    try:
        with open(ROOT_CONTEXT_FILE, "w") as f:
            json.dump(mapping, f)
    except Exception:
        pass


# ── List Rendering ────────────────────────────────────────────────────────────

def render_primitive_list(ptype, items):
    """Render a list of primitives with numeric indices.
    
    items: list of dicts with keys: name, status, tags, (optional) priority, confidence
    """
    mapping = {}
    type_singular = ptype.rstrip('s')
    
    print()
    print(f"  {B}🔮 {ptype.title()}{R}  {D}({len(items)} total){R}")
    print(f"  {D}{'─' * 62}{R}")
    print(f"  {B}{'#':<5s} {'Name':<38s} {'Status':<14s} {'Tags'}{R}")
    print(f"  {D}{'─' * 62}{R}")
    
    for i, item in enumerate(items, 1):
        name = item.get("name", "?")
        status = item.get("status", "—")
        tags = item.get("tags", "")
        
        # Status coloring
        sc = R
        if any(s in status for s in ["open", "active", "running"]):
            sc = G
        elif "blocked" in status:
            sc = Y
        elif any(s in status for s in ["complete", "done", "closed"]):
            sc = D
        elif any(s in status for s in ["in_pipeline"]):
            sc = C
        
        idx_str = f"{C}{i}{R}"
        mapping[str(i)] = name
        
        # Truncate long names
        display_name = name[:36] + ".." if len(name) > 38 else name
        
        print(f"  {idx_str:<14s} {display_name:<38s} {sc}{status:<14s}{R} {D}{tags}{R}")
    
    print()
    print(f"  {D}View details: {C}belam {type_singular} <#>{R}  {D}e.g.{R} {C}belam {type_singular} 1{R}")
    print()
    
    save_context(f"list:{ptype}", mapping)
    return mapping


def list_primitives_indexed(ptype):
    """Read primitives from workspace directory and render indexed list."""
    pdir = Path(WORKSPACE) / ptype
    if not pdir.is_dir():
        print(f"  No {ptype} directory found.")
        return
    
    items = []
    for f in sorted(pdir.glob("*.md")):
        name = f.stem
        status = "—"
        tags = ""
        
        # Parse frontmatter
        content = f.read_text(errors="replace")
        in_frontmatter = False
        for line in content.split("\n"):
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    break
            if in_frontmatter:
                if line.startswith("status:"):
                    status = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("tags:"):
                    raw = line.split(":", 1)[1].strip()
                    # Handle both [a, b] and a, b formats
                    raw = raw.strip("[]")
                    tags = raw.strip()
                elif line.startswith("archived:") and "true" in line.lower():
                    status = "archived"
        
        # Skip archived by default
        if status == "archived":
            continue
            
        items.append({"name": name, "status": status, "tags": tags})
    
    if not items:
        print(f"  No {ptype} found.")
        return
    
    render_primitive_list(ptype, items)


# ── Coordinate Resolution ────────────────────────────────────────────────────

def resolve_coordinate(coord):
    """Resolve a coordinate against saved context.
    
    Returns: (resolved_command_parts, context_type) or (None, None)
    
    Resolution order:
    1. Current context (last rendered view)
    2. Root context (always available after first `belam` call) — for letter+number coords
    """
    ctx = load_context()
    coord_lower = coord.lower()
    
    # Try current context first
    if ctx:
        mapping = ctx.get("mapping", {})
        ctx_type = ctx.get("type", "")
        
        if coord_lower in mapping:
            target = mapping[coord_lower]
            
            if ctx_type == "root":
                return [target], ctx_type
            elif ctx_type.startswith("list:"):
                ptype = ctx_type.split(":", 1)[1]
                type_singular = ptype.rstrip('s')
                return [type_singular, target], ctx_type
    
    # Fall back to root context for letter+number coordinates
    if re.match(r'^[a-z]\d+$', coord_lower):
        try:
            with open(ROOT_CONTEXT_FILE) as f:
                root_mapping = json.load(f)
            if coord_lower in root_mapping:
                return [root_mapping[coord_lower]], "root"
        except Exception:
            pass
    
    return None, None


# ── Pipeline List (native indexed rendering) ─────────────────────────────────

def _parse_pipeline_frontmatter(filepath):
    """Parse YAML frontmatter from a pipeline markdown file."""
    content = filepath.read_text(errors="replace")
    meta = {}
    in_fm = False
    for line in content.split("\n"):
        if line.strip() == "---":
            if not in_fm:
                in_fm = True
                continue
            else:
                break
        if in_fm:
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == "tags":
                    val = val.strip("[]")
                meta[key] = val
    return meta


def render_pipelines_indexed():
    """Read pipeline files and render an indexed dashboard."""
    pdir = Path(WORKSPACE) / "pipelines"
    archive_dir = pdir / "archive"

    # Gather active pipelines
    active = []
    if pdir.is_dir():
        for f in sorted(pdir.glob("*.md")):
            meta = _parse_pipeline_frontmatter(f)
            version = meta.get("version", f.stem)
            title = meta.get("title", "")
            # If no explicit title, derive from filename
            if not title:
                title = f.stem.replace("-", " ").title()
            active.append({
                "name": version,
                "title": title,
                "status": meta.get("status", "—"),
                "priority": meta.get("priority", "—"),
                "started": meta.get("started", "—"),
                "tags": meta.get("tags", ""),
            })

    # Gather archived pipelines
    archived = []
    if archive_dir.is_dir():
        for f in sorted(archive_dir.glob("*.md")):
            meta = _parse_pipeline_frontmatter(f)
            version = meta.get("version", f.stem)
            title = meta.get("title", "")
            if not title:
                title = f.stem.replace("-", " ").title()
            archived.append({
                "name": version,
                "title": title,
                "status": meta.get("status", "archived"),
                "priority": meta.get("priority", "—"),
                "started": meta.get("started", "—"),
                "tags": meta.get("tags", ""),
            })

    total = len(active) + len(archived)
    if total == 0:
        print(f"  No pipelines found.")
        return

    mapping = {}

    print()
    print(f"  {B}🔮 Pipelines{R}  {D}({total} total, {len(active)} active){R}")
    print(f"  {D}{'─' * 72}{R}")
    print(f"  {B}{'#':<5s} {'Version':<28s} {'Status':<24s} {'Pri':<6s} {'Started'}{R}")
    print(f"  {D}{'─' * 72}{R}")

    idx = 1
    for item in active:
        name = item["name"]
        status = item["status"]
        priority = item["priority"]
        started = item["started"]

        # Status coloring
        sc = R
        if any(s in status for s in ["running", "building", "in_progress"]):
            sc = G
        elif any(s in status for s in ["blocked", "waiting", "stalled"]):
            sc = Y
        elif any(s in status for s in ["complete", "done"]):
            sc = D
        elif any(s in status for s in ["analysis", "review"]):
            sc = C
        elif any(s in status for s in ["revision", "queued"]):
            sc = M

        # Priority coloring
        pc = R
        if priority == "critical":
            pc = RD
        elif priority == "high":
            pc = Y
        elif priority == "medium":
            pc = R
        elif priority == "low":
            pc = D

        idx_str = f"{C}{idx}{R}"
        mapping[str(idx)] = name
        display = name[:26] + ".." if len(name) > 28 else name

        print(f"  {idx_str:<14s} {display:<28s} {sc}{status:<24s}{R} {pc}{priority:<6s}{R} {D}{started}{R}")
        idx += 1

    # Archived section
    if archived:
        print(f"  {D}{'─' * 72}{R}")
        print(f"  {D}  ARCHIVED{R}")
        print(f"  {D}{'─' * 72}{R}")

        for item in archived:
            name = item["name"]
            status = item["status"]
            started = item["started"]

            mapping[str(idx)] = name
            display = name[:26] + ".." if len(name) > 28 else name

            print(f"  {D}{C}{idx}{R}{D}  {display:<28s} {status:<24s} {'—':<6s} {started}{R}")
            idx += 1

    print()
    print(f"  {D}View details: {C}belam pipeline <#>{R}  {D}e.g.{R} {C}belam pipeline 1{R}")
    print()

    save_context("list:pipelines", mapping)


# ── Status (indexed) ──────────────────────────────────────────────────────────

def _parse_frontmatter(path):
    """Parse YAML frontmatter from a markdown file into a dict."""
    meta = {}
    try:
        content = path.read_text(errors="replace")
    except Exception:
        return meta
    in_fm = False
    for line in content.split("\n"):
        if line.strip() == "---":
            if not in_fm:
                in_fm = True
                continue
            else:
                break
        if in_fm:
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip().strip('"').strip("'").strip("[]")
    return meta


def _count_memory_entries(date_str):
    """Count ## headings in today's memory file."""
    mem_file = Path(WORKSPACE) / "memory" / f"{date_str}.md"
    if not mem_file.exists():
        return 0
    count = 0
    try:
        for line in mem_file.read_text(errors="replace").split("\n"):
            if line.startswith("## "):
                count += 1
    except Exception:
        pass
    return count


def _git_dirty_count(repo_path):
    """Return number of uncommitted files in a git repo, or None if not a repo."""
    if not Path(repo_path).is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=str(repo_path), timeout=5
        )
        if result.returncode != 0:
            return None
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        return len(lines)
    except Exception:
        return None


def render_status_indexed():
    """Render a full workspace status view with indexed pipelines and tasks."""
    from datetime import date
    today = date.today().isoformat()
    mapping = {}  # combined context: p1->pipeline, t1->task

    print()
    print(f"  {B}🔮 WORKSPACE STATUS{R}  {D}— {today}{R}")
    print(f"  {D}{'─' * 62}{R}")

    # ── Pipelines ─────────────────────────────────────────────────────
    print()
    print(f"  {B}{M}▸ PIPELINES{R}")
    pdir = Path(WORKSPACE) / "pipelines"
    p_idx = 0
    if pdir.is_dir():
        for f in sorted(pdir.glob("*.md")):
            meta = _parse_frontmatter(f)
            status = meta.get("status", "unknown")
            # Skip archived/complete unless they're interesting
            if status in ("archived",):
                continue
            p_idx += 1
            coord = f"p{p_idx}"
            version = meta.get("version", f.stem)
            mapping[coord] = version
            # Status coloring
            if status in ("complete", "done"):
                sc = D
            elif status in ("running", "active", "building"):
                sc = G
            elif "analysis" in status or "review" in status:
                sc = C
            elif "blocked" in status or "stalled" in status:
                sc = Y
            else:
                sc = R
            priority = meta.get("priority", "")
            pri_str = f" {D}[{priority}]{R}" if priority else ""
            print(f"    {C}{coord}{R}  {B}{version:<30s}{R} {sc}{status:<24s}{R}{pri_str}")
    if p_idx == 0:
        print(f"    {D}No active pipelines{R}")

    # ── Open Tasks ────────────────────────────────────────────────────
    print()
    print(f"  {B}{Y}▸ OPEN TASKS{R}")
    tdir = Path(WORKSPACE) / "tasks"
    t_idx = 0
    if tdir.is_dir():
        for f in sorted(tdir.glob("*.md")):
            meta = _parse_frontmatter(f)
            status = meta.get("status", "unknown")
            if status not in ("open", "blocked", "in_pipeline"):
                continue
            t_idx += 1
            coord = f"t{t_idx}"
            name = f.stem
            mapping[coord] = name
            # Status coloring
            if status == "open":
                sc = G
            elif status == "blocked":
                sc = Y
            elif status == "in_pipeline":
                sc = C
            else:
                sc = R
            priority = meta.get("priority", "")
            dep = meta.get("depends_on", "")
            extras = []
            if priority:
                extras.append(priority)
            if dep:
                extras.append(f"→{dep}")
            extra_str = f" {D}[{', '.join(extras)}]{R}" if extras else ""
            display = name[:36] + ".." if len(name) > 38 else name
            print(f"    {C}{coord}{R}  {B}{display:<38s}{R} {sc}{status:<12s}{R}{extra_str}")
    if t_idx == 0:
        print(f"    {D}No open tasks{R}")

    # ── Memory ────────────────────────────────────────────────────────
    print()
    print(f"  {B}{G}▸ MEMORY{R}")
    mem_count = _count_memory_entries(today)
    print(f"    Today's entries: {B}{mem_count}{R}  {D}(memory/{today}.md){R}")

    # ── Git ────────────────────────────────────────────────────────────
    print()
    print(f"  {B}{C}▸ GIT{R}")
    # Workspace repo
    ws_dirty = _git_dirty_count(WORKSPACE)
    if ws_dirty is not None:
        color = G if ws_dirty == 0 else Y
        label = "clean" if ws_dirty == 0 else f"{ws_dirty} uncommitted"
        print(f"    workspace          {color}{label}{R}")
    else:
        print(f"    workspace          {D}not a git repo{R}")

    # SNN_research/machinelearning repo
    ml_path = Path(WORKSPACE) / "SNN_research" / "machinelearning"
    ml_dirty = _git_dirty_count(ml_path)
    if ml_dirty is not None:
        color = G if ml_dirty == 0 else Y
        label = "clean" if ml_dirty == 0 else f"{ml_dirty} uncommitted"
        print(f"    machinelearning    {color}{label}{R}")
    else:
        print(f"    machinelearning    {D}not found{R}")

    # ── Footer ────────────────────────────────────────────────────────
    print()
    print(f"  {D}{'─' * 62}{R}")
    coords_avail = []
    if p_idx > 0:
        coords_avail.append(f"{C}p1{R}..{C}p{p_idx}{R}")
    if t_idx > 0:
        coords_avail.append(f"{C}t1{R}..{C}t{t_idx}{R}")
    if coords_avail:
        print(f"  {D}Drill in:{R}  {C}belam{R} {' | '.join(coords_avail)}")
    print()

    save_context("status", mapping)


# ── Notebooks List ────────────────────────────────────────────────────────────

def format_size(size_bytes):
    """Format file size human-readable."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} B"


def render_notebooks_indexed():
    """Scan notebooks directory and render indexed list with file info."""
    from datetime import datetime

    nb_dir = Path(WORKSPACE) / "machinelearning" / "snn_applied_finance" / "notebooks"

    if not nb_dir.is_dir():
        print(f"  {RD}✗{R} Notebooks directory not found: {D}{nb_dir}{R}")
        return

    notebooks = sorted(nb_dir.glob("*.ipynb"))
    if not notebooks:
        print(f"  {D}No notebooks found in {nb_dir}{R}")
        return

    mapping = {}

    print()
    print(f"  {B}🔮 Notebooks{R}  {D}({len(notebooks)} total){R}")
    print(f"  {D}{'─' * 72}{R}")
    print(f"  {B}{'#':<5s} {'Notebook':<42s} {'Size':<10s} {'Modified'}{R}")
    print(f"  {D}{'─' * 72}{R}")

    for i, nb in enumerate(notebooks, 1):
        name = nb.name
        try:
            size = os.path.getsize(nb)
            mtime = os.path.getmtime(nb)
            size_str = format_size(size)
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        except OSError:
            size_str = "?"
            date_str = "?"

        mapping[str(i)] = str(nb)
        display_name = name[:40] + ".." if len(name) > 42 else name

        print(f"  {C}{i:<4d}{R} {display_name:<42s} {Y}{size_str:<10s}{R} {D}{date_str}{R}")

    print()
    print(f"  {D}View path: {C}belam notebook <#>{R}  {D}e.g.{R} {C}belam notebook 1{R}")
    print()

    save_context("list:notebooks", mapping)


# ── Create Scaffold ───────────────────────────────────────────────────────────

# Field schemas per primitive type.
# Each field: (name, required, choices_or_None)
CREATE_SCHEMAS = {
    "lesson": [
        ("title",      True,  None),
        ("tags",       False, None),
        ("confidence", False, "high/medium/low/?"),
        ("project",    False, None),
        ("source",     False, None),
    ],
    "decision": [
        ("title",  True,  None),
        ("tags",   False, None),
        ("status", False, "proposed/accepted/superseded"),
        ("skill",  False, None),
        ("project",False, None),
    ],
    "task": [
        ("title",    True,  None),
        ("tags",     False, None),
        ("priority", False, "critical/high/medium/low"),
        ("depends",  False, None),
        ("project",  False, None),
    ],
    "project": [
        ("title",  True,  None),
        ("tags",   False, None),
        ("status", False, "active/complete/paused"),
    ],
    "skill": [
        ("name", True,  None),
        ("tags", False, None),
        ("desc", False, None),
    ],
    "command": [
        ("name",     True,  None),
        ("command",  False, None),
        ("aliases",  False, None),
        ("category", False, None),
        ("desc",     False, None),
    ],
}

def render_create_scaffold(ptype):
    """Show an informational scaffold for creating a primitive of the given type."""
    schema = CREATE_SCHEMAS.get(ptype)
    if not schema:
        print(f"  {RD}✗{R} Unknown type '{ptype}'. Known: {', '.join(sorted(CREATE_SCHEMAS))}")
        return False

    title_field = schema[0][0]  # 'title' or 'name'
    print()
    print(f"  {B}🔮 Create {ptype.title()}{R}")
    print(f"  {D}{'─' * 50}{R}")

    for i, (fname, required, choices) in enumerate(schema, 1):
        coord = f"a{i}"
        req_label = f"{B}(required){R}" if required else f"{D}(optional){R}"
        choices_str = f"  {D}[{choices}]{R}" if choices else ""
        print(f"  {C}{coord}{R}  {fname:<14s} {req_label}  {D}___{R}{choices_str}")

    # Build example fill command
    print()
    example_title = "My Title" if title_field == "title" else "my-name"
    flag_examples = []
    for fname, req, _ in schema[1:]:
        if fname == "tags":
            flag_examples.append("--tags x,y")
        elif fname not in ("desc",):
            flag_examples.append(f"--{fname} …")
        if len(flag_examples) >= 2:
            break
    flags_str = " ".join(flag_examples)
    print(f"  {D}Fill:{R} {C}belam create {ptype} \"{example_title}\"{R}" +
          (f" {C}{flags_str}{R}" if flags_str else ""))
    print()
    return True


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    
    # Strip --raw flag
    raw_mode = "--raw" in args or "--plain" in args
    args = [a for a in args if a not in ("--raw", "--plain")]
    
    if not args:
        # No args: show root menu
        if raw_mode:
            # Delegate to original usage
            sys.exit(2)  # Signal to bash: use old usage()
        render_root_menu()
        sys.exit(0)
    
    cmd = args[0]
    
    # Check if it's a status coordinate (p1, t1, etc.)
    if re.match(r'^[pt]\d+$', cmd):
        ctx = load_context()
        if ctx and ctx.get("type") == "status":
            target = ctx["mapping"].get(cmd)
            if target:
                prefix = "pipeline" if cmd.startswith("p") else "task"
                belam_path = os.path.expanduser("~/.local/bin/belam")
                os.execv(belam_path, ["belam", prefix, target] + args[1:])
            else:
                print(f"  {RD}✗{R} Index '{cmd}' not in last status view.")
                sys.exit(1)

    # Check if it's a coordinate (letter+number or bare number)
    if re.match(r'^[a-z]\d+$', cmd) or (re.match(r'^\d+$', cmd) and len(args) == 1):
        resolved, ctx_type = resolve_coordinate(cmd)
        if resolved:
            # Re-exec belam with resolved command
            belam_path = os.path.expanduser("~/.local/bin/belam")
            os.execv(belam_path, ["belam"] + resolved + args[1:])
        else:
            print(f"  {RD}✗{R} No context for coordinate '{cmd}'. Run a command first.")
            sys.exit(1)
    
    # Handle create scaffold: `belam create <type>` with no title → show scaffold
    if cmd in ("create", "new", "c") and not raw_mode:
        if len(args) >= 2 and args[1] in CREATE_SCHEMAS:
            # Type given — check if title is also provided
            if len(args) >= 3:
                # Title provided → fall through to create_primitive.py
                sys.exit(2)
            else:
                # No title → show scaffold
                render_create_scaffold(args[1])
                sys.exit(0)
        elif len(args) == 1:
            # Bare `belam create` — show all types
            print()
            print(f"  {B}🔮 Create{R}  {D}— choose a type{R}")
            print(f"  {D}{'─' * 50}{R}")
            for i, ptype in enumerate(sorted(CREATE_SCHEMAS), 1):
                print(f"  {C}{i}{R}  {ptype}")
            print()
            print(f"  {D}Usage:{R} {C}belam create <type>{R}  {D}or{R}  {C}belam create <type> \"Title\"{R}")
            print()
            sys.exit(0)
        # Unknown type or flags — fall through
        sys.exit(2)

    # Handle status command
    if cmd in ("status", "s") and not raw_mode:
        render_status_indexed()
        sys.exit(0)

    # Handle indexed list commands
    if cmd in ("tasks", "t") and not raw_mode:
        list_primitives_indexed("tasks")
        sys.exit(0)
    elif cmd in ("lessons", "l") and not raw_mode:
        list_primitives_indexed("lessons")
        sys.exit(0)
    elif cmd in ("decisions", "d") and not raw_mode:
        list_primitives_indexed("decisions")
        sys.exit(0)
    elif cmd in ("projects", "pj") and not raw_mode:
        list_primitives_indexed("projects")
        sys.exit(0)
    elif cmd in ("notebooks", "nb") and not raw_mode:
        render_notebooks_indexed()
        sys.exit(0)
    elif cmd in ("pipelines", "pipes", "pl") and not raw_mode:
        render_pipelines_indexed()
        sys.exit(0)
    
    # Handle pipeline <number> resolution
    if cmd == "pipeline" and len(args) > 1 and args[1].isdigit():
        ctx = load_context()
        if ctx and ctx.get("type") == "list:pipelines":
            name = ctx["mapping"].get(args[1])
            if name:
                belam_path = os.path.expanduser("~/.local/bin/belam")
                os.execv(belam_path, ["belam", "pipeline", name] + args[2:])
            else:
                print(f"  {RD}✗{R} Index {args[1]} not found in last pipelines list.")
                sys.exit(1)
        else:
            print(f"  {RD}✗{R} No pipelines list context. Run {C}belam pipelines{R} first.")
            sys.exit(1)
    
    # Handle notebook <number> resolution
    if cmd in ("notebook",) and len(args) > 1 and args[1].isdigit():
        ctx = load_context()
        if ctx and ctx.get("type") == "list:notebooks":
            nb_path = ctx["mapping"].get(args[1])
            if nb_path:
                print(f"  {G}📓{R} {nb_path}")
                sys.exit(0)
            else:
                print(f"  {RD}✗{R} Index {args[1]} not found in last notebooks list.")
                sys.exit(1)
        else:
            print(f"  {RD}✗{R} No notebooks list context. Run {C}belam notebooks{R} first.")
            sys.exit(1)

    # Handle indexed show commands with numeric arg
    if cmd in ("task", "lesson", "decision", "project") and len(args) > 1 and args[1].isdigit():
        # Resolve number against last list context
        ptype = cmd + "s"  # task → tasks
        ctx = load_context()
        if ctx and ctx.get("type") == f"list:{ptype}":
            name = ctx["mapping"].get(args[1])
            if name:
                # Re-exec with resolved name
                belam_path = os.path.expanduser("~/.local/bin/belam")
                os.execv(belam_path, ["belam", cmd, name] + args[2:])
            else:
                print(f"  {RD}✗{R} Index {args[1]} not found in last {ptype} list.")
                sys.exit(1)
        else:
            print(f"  {RD}✗{R} No {ptype} list context. Run {C}belam {ptype}{R} first.")
            sys.exit(1)
    
    # Not handled by index engine — signal bash to continue normal dispatch
    sys.exit(2)


if __name__ == "__main__":
    main()
