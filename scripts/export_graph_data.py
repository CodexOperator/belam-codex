#!/usr/bin/env python3
"""
Export primitive relationship graph data to canvas/graph_data.json.
Scans all primitive directories, parses YAML frontmatter, and extracts
upstream/downstream relationships as edges.
"""

import json
import os
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent

PRIMITIVE_DIRS = {
    "lesson":   "lessons",
    "decision": "decisions",
    "task":     "tasks",
    "project":  "projects",
    "pipeline": "pipelines",
    "command":  "commands",
    "skill":    "skills",
    "knowledge": "knowledge",
}

# Slugs to skip (non-primitive markdown files)
SKIP_SLUGS = {"README", "_index", "_tags"}


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content (simple regex parser)."""
    fm = {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return fm
    
    yaml_block = match.group(1)
    
    # Parse key: value pairs (simple, handles lists and scalars)
    lines = yaml_block.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # Skip empty lines
        if not line.strip():
            i += 1
            continue
        
        # Match key: value
        kv_match = re.match(r"^(\w[\w_-]*):\s*(.*)", line)
        if not kv_match:
            i += 1
            continue
        
        key = kv_match.group(1)
        val = kv_match.group(2).strip()
        
        # Inline list: [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            if inner:
                items = [x.strip().strip('"').strip("'") for x in inner.split(",")]
                fm[key] = [x for x in items if x]
            else:
                fm[key] = []
        # Multi-line list: next lines start with "  - "
        elif not val and i + 1 < len(lines) and re.match(r"^\s+-\s", lines[i + 1]):
            items = []
            i += 1
            while i < len(lines) and re.match(r"^\s+-\s+(.*)", lines[i]):
                item_match = re.match(r"^\s+-\s+(.*)", lines[i])
                items.append(item_match.group(1).strip().strip('"').strip("'"))
                i += 1
            fm[key] = items
            continue
        # Scalar
        else:
            fm[key] = val.strip('"').strip("'")
        
        i += 1
    
    return fm


def get_title(content: str, slug: str) -> str:
    """Extract the first H1 heading from markdown content."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return slug.replace("-", " ").title()


def normalize_ref(ref: str, default_type: str) -> str:
    """Normalize a reference like 'decisions/foo' or just 'foo' to 'type/slug'."""
    ref = ref.strip()
    if "/" in ref:
        # Handle plural type names in refs
        parts = ref.split("/", 1)
        ptype = parts[0].rstrip("s")  # lessons -> lesson, decisions -> decision
        # Map common plurals
        plural_map = {
            "lesson": "lesson",
            "decision": "decision",
            "task": "task",
            "project": "project",
            "pipeline": "pipeline",
            "command": "command",
            "skill": "skill",
            "knowledge": "knowledge",
            "memory": None,  # skip memory refs
        }
        canonical = plural_map.get(ptype, ptype)
        if canonical is None:
            return None
        return f"{canonical}/{parts[1]}"
    return f"{default_type}/{ref}"


def export_graph():
    nodes = []
    edges = []
    node_ids = set()
    
    for ptype, dirname in PRIMITIVE_DIRS.items():
        dirpath = WORKSPACE / dirname
        if not dirpath.exists():
            continue
        
        # For skills, scan subdirectories for SKILL.md
        if ptype == "skill":
            for subdir in sorted(dirpath.iterdir()):
                if subdir.is_dir():
                    skill_md = subdir / "SKILL.md"
                    if skill_md.exists():
                        slug = subdir.name
                        node_id = f"{ptype}/{slug}"
                        content = skill_md.read_text(encoding="utf-8", errors="replace")
                        fm = parse_frontmatter(content)
                        title = get_title(content, slug)
                        
                        node = {
                            "id": node_id,
                            "type": ptype,
                            "title": title,
                            "tags": fm.get("tags", []),
                            "status": fm.get("status", ""),
                            "frontmatter": fm,
                        }
                        nodes.append(node)
                        node_ids.add(node_id)
                        
                        # Collect edges
                        for ref in fm.get("upstream", []):
                            norm = normalize_ref(ref, ptype)
                            if norm:
                                edges.append({"source": norm, "target": node_id, "_raw": ref})
                        for ref in fm.get("downstream", []):
                            norm = normalize_ref(ref, ptype)
                            if norm:
                                edges.append({"source": node_id, "target": norm, "_raw": ref})
            continue
        
        for mdfile in sorted(dirpath.glob("*.md")):
            slug = mdfile.stem
            if slug in SKIP_SLUGS:
                continue
            
            content = mdfile.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(content)
            title = get_title(content, slug)
            
            node_id = f"{ptype}/{slug}"
            
            node = {
                "id": node_id,
                "type": ptype,
                "title": title,
                "tags": fm.get("tags", []),
                "status": fm.get("status", fm.get("confidence", "")),
                "frontmatter": fm,
            }
            nodes.append(node)
            node_ids.add(node_id)
            
            # Collect edges from upstream/downstream
            for ref in fm.get("upstream", []):
                norm = normalize_ref(ref, ptype)
                if norm:
                    edges.append({"source": norm, "target": node_id, "_raw": ref})
            for ref in fm.get("downstream", []):
                norm = normalize_ref(ref, ptype)
                if norm:
                    edges.append({"source": node_id, "target": norm, "_raw": ref})
    
    # Deduplicate edges and filter to only valid node pairs
    # (we keep edges even if target doesn't exist yet — graph will handle gracefully)
    seen_edges = set()
    clean_edges = []
    for e in edges:
        key = (e["source"], e["target"])
        if key not in seen_edges and e["source"] != e["target"]:
            seen_edges.add(key)
            clean_edges.append({"source": e["source"], "target": e["target"]})
    
    output = {
        "nodes": nodes,
        "edges": clean_edges,
    }
    
    out_path = WORKSPACE / "canvas" / "graph_data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    
    print(f"✓ Exported {len(nodes)} nodes, {len(clean_edges)} edges → {out_path}")
    
    # Print summary by type
    from collections import Counter
    type_counts = Counter(n["type"] for n in nodes)
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")


if __name__ == "__main__":
    export_graph()
