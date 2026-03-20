#!/usr/bin/env python3
"""Incremental Relationship Mapper — pairwise primitive comparison via Opus.

Deterministic orchestrator that:
1. Loads all primitives, reads frontmatter + content
2. Pre-filters the comparison matrix (tag overlap, temporal proximity, type compatibility)
3. Tracks progress in relationship_progress.json (resumable)
4. Spawns fresh Opus subagent per batch of N pairs
5. Applies discovered relationships via belam link backend (direct Python)
6. Runs incrementally — designed for ~15min cron/heartbeat invocations

Usage:
    python3 scripts/map_relationships.py                # run one batch
    python3 scripts/map_relationships.py --dry-run      # show what would be compared, no writes
    python3 scripts/map_relationships.py --status        # show progress stats
    python3 scripts/map_relationships.py --batch-size 5  # pairs per invocation (default: 4)
    python3 scripts/map_relationships.py --reset         # clear progress, start fresh
    python3 scripts/map_relationships.py --filter-only   # show filtered pair count, exit
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────

WORKSPACE = os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace"))
PROGRESS_FILE = os.path.join(WORKSPACE, "canvas", "relationship_progress.json")

# Primitive types eligible for relationship mapping
ELIGIBLE_TYPES = ["lessons", "decisions", "tasks", "projects", "knowledge"]

# Type pairs that are worth comparing (high-value combinations)
# Format: frozenset({typeA, typeB}) — order doesn't matter
COMPARABLE_TYPE_PAIRS = {
    frozenset({"lessons", "decisions"}),      # lessons inform decisions
    frozenset({"lessons", "lessons"}),         # lessons reinforce/contradict each other
    frozenset({"decisions", "decisions"}),     # decisions depend on each other
    frozenset({"decisions", "tasks"}),         # decisions spawn tasks
    frozenset({"decisions", "knowledge"}),     # decisions shape knowledge domains
    frozenset({"tasks", "tasks"}),             # task dependencies
    frozenset({"tasks", "projects"}),          # tasks belong to projects
    frozenset({"lessons", "tasks"}),           # lessons block/enable tasks
    frozenset({"lessons", "knowledge"}),       # lessons refine knowledge
    frozenset({"projects", "knowledge"}),      # projects use knowledge domains
    frozenset({"projects", "projects"}),       # project dependencies
    frozenset({"decisions", "projects"}),      # decisions shape projects
}

# Minimum tag overlap to consider a pair (0 = compare all eligible type pairs)
MIN_TAG_OVERLAP = 0

# Temporal proximity window (days) — primitives created within this window
# get a boost in priority. Set to 0 to disable temporal filtering.
TEMPORAL_PROXIMITY_DAYS = 14


# ── Primitive Loading ──────────────────────────────────────────────────────

def parse_frontmatter(filepath):
    """Parse YAML frontmatter from a markdown file.
    
    Returns dict with keys: primitive, status, tags, date, upstream, downstream, 
    and any other frontmatter fields. Plus '_content' with the body text.
    """
    meta = {}
    content_lines = []
    try:
        text = Path(filepath).read_text(errors="replace")
    except Exception:
        return meta

    in_fm = False
    fm_done = False
    for line in text.split("\n"):
        if line.strip() == "---":
            if not in_fm and not fm_done:
                in_fm = True
                continue
            elif in_fm:
                in_fm = False
                fm_done = True
                continue
        if in_fm:
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                # Parse YAML lists
                if val.startswith("[") and val.endswith("]"):
                    inner = val[1:-1]
                    meta[key] = [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
                else:
                    meta[key] = val.strip('"').strip("'")
        elif fm_done:
            content_lines.append(line)

    meta["_content"] = "\n".join(content_lines).strip()
    return meta


def load_all_primitives():
    """Load all primitives from eligible type directories.
    
    Returns dict: { 'type/slug': { frontmatter + _content + _type + _slug + _path } }
    """
    primitives = {}
    for ptype in ELIGIBLE_TYPES:
        pdir = Path(WORKSPACE) / ptype
        if not pdir.is_dir():
            continue
        for f in sorted(pdir.glob("*.md")):
            meta = parse_frontmatter(f)
            # Skip superseded/archived
            status = meta.get("status", "")
            if status in ("superseded", "archived"):
                continue
            meta["_type"] = ptype
            meta["_slug"] = f.stem
            meta["_path"] = str(f)
            key = f"{ptype}/{f.stem}"
            primitives[key] = meta
    return primitives


# ── Pre-filtering ──────────────────────────────────────────────────────────

def get_tags(meta):
    """Extract tags as a set from primitive metadata."""
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return set(tags)


def get_date(meta):
    """Extract date from primitive metadata, return datetime or None."""
    raw = meta.get("date", "") or meta.get("created", "")
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def get_existing_links(meta):
    """Return set of existing upstream + downstream refs."""
    links = set()
    for field in ("upstream", "downstream"):
        vals = meta.get(field, [])
        if isinstance(vals, str):
            vals = [v.strip() for v in vals.split(",")]
        for v in vals:
            # Normalize: 'decision/slug' or 'decisions/slug' → 'decisions/slug'
            links.add(v.strip())
    return links


def is_type_pair_eligible(type_a, type_b):
    """Check if this type combination is worth comparing."""
    return frozenset({type_a, type_b}) in COMPARABLE_TYPE_PAIRS


def compute_pair_priority(meta_a, meta_b):
    """Compute a priority score for comparing this pair.
    
    Higher = more likely to have a meaningful relationship.
    Returns (score, reasons) or (0, []) if pair should be skipped.
    """
    score = 0
    reasons = []

    # Tag overlap
    tags_a = get_tags(meta_a)
    tags_b = get_tags(meta_b)
    overlap = tags_a & tags_b
    if overlap:
        score += len(overlap) * 2
        reasons.append(f"tags:{','.join(sorted(overlap))}")

    # Temporal proximity
    date_a = get_date(meta_a)
    date_b = get_date(meta_b)
    if date_a and date_b and TEMPORAL_PROXIMITY_DAYS > 0:
        delta = abs((date_a - date_b).days)
        if delta <= TEMPORAL_PROXIMITY_DAYS:
            proximity_score = max(1, TEMPORAL_PROXIMITY_DAYS - delta)
            score += proximity_score
            reasons.append(f"temporal:{delta}d")

    # Shared project references (in tags or explicit fields)
    projects_a = {t for t in tags_a if t in ("snn", "infrastructure", "agents")}
    projects_b = {t for t in tags_b if t in ("snn", "infrastructure", "agents")}
    shared_projects = projects_a & projects_b
    if shared_projects:
        score += len(shared_projects) * 3
        reasons.append(f"domain:{','.join(sorted(shared_projects))}")

    # If no signals at all, give a baseline score of 1 (still eligible, just low priority)
    if score == 0:
        score = 1
        reasons.append("baseline")

    return score, reasons


def already_linked(meta_a, meta_b, key_a, key_b):
    """Check if two primitives are already linked in either direction."""
    links_a = get_existing_links(meta_a)
    links_b = get_existing_links(meta_b)

    # Check various reference formats
    type_a, slug_a = key_a.split("/", 1)
    type_b, slug_b = key_b.split("/", 1)

    # Common ref formats: 'type/slug', 'decision/slug', 'decisions/slug'
    refs_a = {key_a, f"{type_a.rstrip('s')}/{slug_a}", slug_a}
    refs_b = {key_b, f"{type_b.rstrip('s')}/{slug_b}", slug_b}

    if links_a & refs_b:
        return True
    if links_b & refs_a:
        return True
    return False


def generate_candidate_pairs(primitives):
    """Generate all candidate pairs with priority scores.
    
    Returns list of (score, key_a, key_b, reasons) sorted by score descending.
    Filters out:
    - Ineligible type pairs
    - Already-linked pairs
    - Self-comparisons
    """
    keys = sorted(primitives.keys())
    candidates = []

    for i, key_a in enumerate(keys):
        meta_a = primitives[key_a]
        type_a = meta_a["_type"]

        for key_b in keys[i + 1:]:
            meta_b = primitives[key_b]
            type_b = meta_b["_type"]

            # Type pair eligibility
            if not is_type_pair_eligible(type_a, type_b):
                continue

            # Already linked
            if already_linked(meta_a, meta_b, key_a, key_b):
                continue

            # Compute priority
            score, reasons = compute_pair_priority(meta_a, meta_b)

            candidates.append((score, key_a, key_b, reasons))

    # Sort by score descending (highest priority first)
    candidates.sort(key=lambda x: -x[0])
    return candidates


# ── Progress Tracking ──────────────────────────────────────────────────────

def load_progress():
    """Load progress from JSON file. Returns dict with 'completed_pairs' set and stats."""
    if not os.path.exists(PROGRESS_FILE):
        return {
            "completed_pairs": set(),
            "links_created": 0,
            "pairs_evaluated": 0,
            "no_relationship_count": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_run": None,
        }
    try:
        with open(PROGRESS_FILE) as f:
            data = json.load(f)
        data["completed_pairs"] = set(data.get("completed_pairs", []))
        return data
    except (json.JSONDecodeError, KeyError):
        return {
            "completed_pairs": set(),
            "links_created": 0,
            "pairs_evaluated": 0,
            "no_relationship_count": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_run": None,
        }


def save_progress(progress):
    """Save progress to JSON file."""
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    data = dict(progress)
    data["completed_pairs"] = sorted(data["completed_pairs"])
    data["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def pair_key(key_a, key_b):
    """Create a canonical key for a pair (order-independent)."""
    return "|".join(sorted([key_a, key_b]))


# ── LLM Judgment ───────────────────────────────────────────────────────────

def format_primitive_for_prompt(key, meta):
    """Format a primitive's content for inclusion in the comparison prompt."""
    ptype = meta["_type"]
    slug = meta["_slug"]
    tags = ", ".join(get_tags(meta)) if get_tags(meta) else "none"
    date = meta.get("date", meta.get("created", "unknown"))
    status = meta.get("status", "unknown")
    
    # Truncate content to keep prompt focused
    content = meta.get("_content", "")
    if len(content) > 1500:
        content = content[:1500] + "\n[... truncated]"

    return f"""## {ptype}/{slug}
Type: {ptype} | Status: {status} | Date: {date} | Tags: [{tags}]

{content}"""


def build_comparison_prompt(pairs_with_meta):
    """Build the prompt for the Opus subagent to judge relationships.
    
    Args:
        pairs_with_meta: list of (key_a, meta_a, key_b, meta_b)
    
    Returns: prompt string
    """
    primitives_text = []
    pair_labels = []

    for idx, (key_a, meta_a, key_b, meta_b) in enumerate(pairs_with_meta, 1):
        primitives_text.append(f"### Pair {idx}: {key_a} ↔ {key_b}\n")
        primitives_text.append(format_primitive_for_prompt(key_a, meta_a))
        primitives_text.append("---")
        primitives_text.append(format_primitive_for_prompt(key_b, meta_b))
        primitives_text.append("")
        pair_labels.append(f"Pair {idx}: {key_a} ↔ {key_b}")

    prompt = f"""You are analyzing relationships between workspace primitives (lessons, decisions, tasks, projects, knowledge files).

For each pair below, determine if a meaningful upstream/downstream relationship exists.

**Upstream** means: A informs, enables, or is a prerequisite for B.
**Downstream** means: B was created because of, builds upon, or extends A.

Only identify relationships that are **genuinely meaningful** — not just topically related. 
A shared tag or domain is NOT sufficient. Look for causal, dependency, or evolutionary relationships.

For each pair, respond with ONE of:
- `LINK: A > B` — A is upstream of B (A informs/enables B)
- `LINK: B > A` — B is upstream of A
- `LINK: A <> B` — bidirectional (rare — mutual dependency)
- `NONE` — no meaningful relationship

Use the exact `type/slug` identifiers. One judgment per pair, on its own line.

---

{chr(10).join(primitives_text)}

---

Respond with exactly {len(pairs_with_meta)} lines, one per pair, in order:
{chr(10).join(pair_labels)}
"""
    return prompt


def call_opus_judgment(prompt, dry_run=False):
    """Spawn a fresh Opus subagent to judge relationships.
    
    Returns list of raw response lines.
    
    TODO: Wire to sessions_spawn or direct API call.
    Currently a stub that returns empty results.
    """
    if dry_run:
        return []

    # ── STUB: Replace with actual Opus subagent spawn ──
    # Options:
    #   1. sessions_spawn(task=prompt, model="anthropic/claude-opus-4-6", mode="run")
    #   2. Direct Anthropic API call via requests
    #   3. openclaw agent CLI invocation
    #
    # The subagent should return structured lines matching the prompt format.
    # Parse its response with parse_judgment_response().
    
    print("  ⚠ LLM judgment not yet wired — skeleton mode")
    return []


def parse_judgment_response(lines, pairs_with_meta):
    """Parse the LLM's response into actionable link operations.
    
    Returns list of dicts:
        { 'action': 'link'|'none', 'upstream': 'type/slug', 'downstream': 'type/slug' }
    """
    results = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or i >= len(pairs_with_meta):
            continue
            
        key_a, _, key_b, _ = pairs_with_meta[i]
        
        if line.startswith("NONE"):
            results.append({"action": "none", "pair": (key_a, key_b)})
            continue
        
        m = re.match(r'LINK:\s*(.+?)\s*(<>|>)\s*(.+)', line)
        if m:
            left = m.group(1).strip()
            direction = m.group(2)
            right = m.group(3).strip()
            
            if direction == "<>":
                # Bidirectional — create both directions
                results.append({"action": "link", "upstream": left, "downstream": right})
                results.append({"action": "link", "upstream": right, "downstream": left})
            else:
                results.append({"action": "link", "upstream": left, "downstream": right})
        else:
            results.append({"action": "none", "pair": (key_a, key_b)})
    
    return results


# ── Link Application ──────────────────────────────────────────────────────

def apply_link(upstream_ref, downstream_ref, dry_run=False):
    """Apply a single upstream/downstream link between two primitives.
    
    Uses the same backend as belam link (direct frontmatter manipulation).
    Returns True if link was created, False if already existed or failed.
    """
    # Resolve refs to file paths
    up_parts = upstream_ref.split("/", 1)
    dn_parts = downstream_ref.split("/", 1)
    
    if len(up_parts) != 2 or len(dn_parts) != 2:
        print(f"  ✗ Invalid ref format: {upstream_ref} or {downstream_ref}")
        return False
    
    up_type, up_slug = up_parts
    dn_type, dn_slug = dn_parts
    
    up_path = Path(WORKSPACE) / up_type / f"{up_slug}.md"
    dn_path = Path(WORKSPACE) / dn_type / f"{dn_slug}.md"
    
    if not up_path.exists():
        print(f"  ✗ Not found: {up_path}")
        return False
    if not dn_path.exists():
        print(f"  ✗ Not found: {dn_path}")
        return False
    
    if dry_run:
        print(f"  [dry-run] Would link: {upstream_ref} → {downstream_ref}")
        return True
    
    # Import the link helpers from belam_index
    # We add to downstream list on upstream file, and upstream list on downstream file
    sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
    from belam_index import _add_to_frontmatter_list
    
    # Canonical ref format: type/slug (singular type for frontmatter)
    up_ref_canonical = f"{up_type.rstrip('s')}/{up_slug}" if up_type.endswith("s") else f"{up_type}/{up_slug}"
    dn_ref_canonical = f"{dn_type.rstrip('s')}/{dn_slug}" if dn_type.endswith("s") else f"{dn_type}/{dn_slug}"
    
    changed_any = False
    
    # Add downstream ref to upstream file
    content = up_path.read_text(errors="replace")
    new_content, changed = _add_to_frontmatter_list(content, "downstream", dn_ref_canonical)
    if changed:
        up_path.write_text(new_content)
        changed_any = True
    
    # Add upstream ref to downstream file
    content = dn_path.read_text(errors="replace")
    new_content, changed = _add_to_frontmatter_list(content, "upstream", up_ref_canonical)
    if changed:
        dn_path.write_text(new_content)
        changed_any = True
    
    if changed_any:
        print(f"  ✓ Linked: {upstream_ref} → {downstream_ref}")
    else:
        print(f"  · Already linked: {upstream_ref} → {downstream_ref}")
    
    return changed_any


# ── Main Orchestration ─────────────────────────────────────────────────────

def show_status(primitives, candidates, progress):
    """Display progress statistics."""
    total_primitives = len(primitives)
    total_candidates = len(candidates)
    completed = len(progress["completed_pairs"])
    remaining = total_candidates - completed
    
    print(f"\n  🔮 RELATIONSHIP MAPPER STATUS")
    print(f"  {'─' * 45}")
    print(f"  Primitives loaded:    {total_primitives}")
    print(f"  Candidate pairs:      {total_candidates}")
    print(f"  Completed:            {completed}")
    print(f"  Remaining:            {remaining}")
    print(f"  Links created:        {progress.get('links_created', 0)}")
    print(f"  No-relationship:      {progress.get('no_relationship_count', 0)}")
    print(f"  Started:              {progress.get('started_at', 'never')}")
    print(f"  Last run:             {progress.get('last_run', 'never')}")
    
    if remaining > 0 and total_candidates > 0:
        pct = (completed / total_candidates) * 100
        print(f"  Progress:             {pct:.1f}%")
    elif total_candidates > 0:
        print(f"  Progress:             100% ✓")
    print()


def run_batch(batch_size=4, dry_run=False):
    """Run one batch of relationship comparisons.
    
    Returns (pairs_evaluated, links_created).
    """
    # 1. Load primitives
    primitives = load_all_primitives()
    print(f"  Loaded {len(primitives)} primitives")

    # 2. Generate candidates (already sorted by priority)
    candidates = generate_candidate_pairs(primitives)
    print(f"  {len(candidates)} candidate pairs after filtering")

    # 3. Load progress
    progress = load_progress()
    
    # 4. Filter out already-completed pairs
    remaining = [
        (score, ka, kb, reasons) 
        for score, ka, kb, reasons in candidates
        if pair_key(ka, kb) not in progress["completed_pairs"]
    ]
    print(f"  {len(remaining)} remaining after progress filter")

    if not remaining:
        print("  ✓ All candidate pairs have been evaluated!")
        return 0, 0

    # 5. Take the next batch (highest priority first)
    batch = remaining[:batch_size]
    print(f"\n  Processing batch of {len(batch)} pairs:")
    for score, ka, kb, reasons in batch:
        print(f"    [{score:3d}] {ka} ↔ {kb}  ({', '.join(reasons)})")
    print()

    # 6. Prepare pairs with full metadata for the prompt
    pairs_with_meta = [
        (ka, primitives[ka], kb, primitives[kb])
        for _, ka, kb, _ in batch
    ]

    # 7. Build prompt and call LLM
    prompt = build_comparison_prompt(pairs_with_meta)
    
    if dry_run:
        print("  [dry-run] Would send prompt to Opus subagent")
        print(f"  [dry-run] Prompt length: {len(prompt)} chars")
        return len(batch), 0

    response_lines = call_opus_judgment(prompt, dry_run=dry_run)

    # 8. Parse response and apply links
    links_created = 0
    if response_lines:
        results = parse_judgment_response(response_lines, pairs_with_meta)
        for result in results:
            if result["action"] == "link":
                created = apply_link(result["upstream"], result["downstream"], dry_run=dry_run)
                if created:
                    links_created += 1
                    progress["links_created"] = progress.get("links_created", 0) + 1
            else:
                progress["no_relationship_count"] = progress.get("no_relationship_count", 0) + 1

    # 9. Mark pairs as completed
    for _, ka, kb, _ in batch:
        progress["completed_pairs"].add(pair_key(ka, kb))
    progress["pairs_evaluated"] = progress.get("pairs_evaluated", 0) + len(batch)

    # 10. Save progress
    save_progress(progress)

    # 11. Rebuild indexes if any links were created
    if links_created > 0:
        print(f"\n  Rebuilding primitive indexes...")
        embed_script = Path(WORKSPACE) / "scripts" / "embed_primitives.py"
        if embed_script.exists():
            import subprocess
            subprocess.run(
                [sys.executable, str(embed_script)],
                capture_output=True, cwd=str(WORKSPACE)
            )

    return len(batch), links_created


def main():
    parser = argparse.ArgumentParser(description="Incremental Relationship Mapper")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be compared, no writes")
    parser.add_argument("--status", action="store_true", help="Show progress statistics")
    parser.add_argument("--batch-size", type=int, default=4, help="Pairs per invocation (default: 4)")
    parser.add_argument("--reset", action="store_true", help="Clear progress, start fresh")
    parser.add_argument("--filter-only", action="store_true", help="Show filtered pair count, exit")
    args = parser.parse_args()

    if args.reset:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            print("  ✓ Progress reset")
        else:
            print("  · No progress file to reset")
        return

    primitives = load_all_primitives()
    candidates = generate_candidate_pairs(primitives)
    progress = load_progress()

    if args.status:
        show_status(primitives, candidates, progress)
        return

    if args.filter_only:
        print(f"\n  Primitives: {len(primitives)}")
        print(f"  Candidate pairs: {len(candidates)}")
        print(f"  Top 10 by priority:")
        for score, ka, kb, reasons in candidates[:10]:
            print(f"    [{score:3d}] {ka} ↔ {kb}  ({', '.join(reasons)})")
        print()
        return

    pairs_evaluated, links_created = run_batch(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    print(f"\n  Done: {pairs_evaluated} pairs evaluated, {links_created} links created")


if __name__ == "__main__":
    main()
