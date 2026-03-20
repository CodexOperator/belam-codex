#!/usr/bin/env python3
"""Incremental Relationship Mapper — pairwise primitive comparison via Opus.

Deterministic orchestrator that:
1. Loads all primitives (including memory entries) with frontmatter + content
2. Two modes: LLM judgment for causal pairs, heuristic for structural pairs
3. Tracks progress in relationship_progress.json (resumable)
4. Spawns fresh Opus subagent per single pair (deep judgment with room to reference context)
5. Applies discovered relationships via belam link backend (direct Python)

LLM-judged pairs (causal/semantic):
  - memory ↔ lesson   (memory crystallized into lesson)
  - lesson ↔ decision  (lesson informed decision)
  - memory ↔ decision  (memory led to decision)

Heuristic pairs (structural):
  - Everything else (decision↔task, task↔project, etc.) via tag overlap + temporal + type rules

Usage:
    python3 scripts/map_relationships.py                  # run one LLM pair
    python3 scripts/map_relationships.py --burst 20       # burn through 20 pairs (token burn mode)
    python3 scripts/map_relationships.py --heuristic      # run heuristic linking (instant, no LLM)
    python3 scripts/map_relationships.py --dry-run        # show what would happen, no writes
    python3 scripts/map_relationships.py --status         # show progress stats
    python3 scripts/map_relationships.py --reset          # clear progress, start fresh
    python3 scripts/map_relationships.py --filter-only    # show candidate counts, exit
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────

WORKSPACE = os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace"))
PROGRESS_FILE = os.path.join(WORKSPACE, "canvas", "relationship_progress.json")

# Primitive types eligible for relationship mapping
ELIGIBLE_TYPES = ["lessons", "decisions", "tasks", "projects", "knowledge"]

# Memory entries directory
MEMORY_ENTRIES_DIR = os.path.join(WORKSPACE, "memory", "entries")

# ── LLM-judged type pairs (anything with causal ambiguity) ──
# Direction can't be assumed from type alone — agent must judge.
LLM_TYPE_PAIRS = {
    # Primary causal (original scope)
    frozenset({"memories", "lessons"}),      # memory crystallized into lesson, or lesson triggered memory
    frozenset({"lessons", "decisions"}),      # lesson informed decision, or decision produced lesson
    frozenset({"memories", "decisions"}),     # memory led to decision, or decision logged as memory
    # Cross-type (direction ambiguous — can flow either way)
    frozenset({"decisions", "decisions"}),    # decision informs decision
    frozenset({"decisions", "tasks"}),        # decision spawns task, or task failure shapes decision
    frozenset({"decisions", "knowledge"}),    # knowledge informs decision, or decision creates knowledge
    frozenset({"decisions", "projects"}),     # decision shapes project, or project drives decision
    frozenset({"tasks", "tasks"}),            # task dependencies
    frozenset({"tasks", "projects"}),         # task belongs to project
    frozenset({"lessons", "lessons"}),        # lessons reinforce or contradict
    frozenset({"lessons", "tasks"}),          # lesson reveals task, or task failure produces lesson
    frozenset({"lessons", "knowledge"}),      # lesson refines knowledge, or knowledge gap produces lesson
    frozenset({"projects", "knowledge"}),     # project uses knowledge, or knowledge shapes project
    frozenset({"projects", "projects"}),      # project dependencies
    frozenset({"memories", "tasks"}),         # memory about a task
    frozenset({"memories", "projects"}),      # memory about a project
    frozenset({"memories", "knowledge"}),     # memory about knowledge
}

# ── Heuristic type pairs (ONLY unambiguous structural links) ──
# Cross-type causal relationships are inherently ambiguous in direction
# (lesson→task OR task→lesson depending on the story) — those go to LLM.
# Heuristic only handles: same-type chronological + explicit dependency fields.
HEURISTIC_TYPE_PAIRS = {
    frozenset({"memories", "memories"}),     # chronological chain within same day/topic
}

# Soft cap: max upstream edges per primitive (forces quality over quantity)
MAX_UPSTREAM = 3

# Temporal proximity window (days) for priority scoring
TEMPORAL_PROXIMITY_DAYS = 14

# Heuristic thresholds
HEURISTIC_MIN_TAG_OVERLAP = 2   # require ≥2 shared tags for heuristic linking
HEURISTIC_MAX_TEMPORAL_GAP = 7  # max days apart for heuristic temporal linking


# ── Primitive Loading ──────────────────────────────────────────────────────

def parse_frontmatter(filepath):
    """Parse YAML frontmatter from a markdown file.

    Returns dict with frontmatter fields plus '_content' with the body text.
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
                if val.startswith("[") and val.endswith("]"):
                    inner = val[1:-1]
                    meta[key] = [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
                elif val.startswith('"') and val.endswith('"'):
                    meta[key] = val[1:-1]
                else:
                    meta[key] = val
        elif fm_done:
            content_lines.append(line)

    meta["_content"] = "\n".join(content_lines).strip()
    return meta


def load_all_primitives():
    """Load all primitives from eligible type directories + memory entries.

    Returns dict: { 'type/slug': { frontmatter + _content + _type + _slug + _path } }
    """
    primitives = {}

    # Standard primitive types
    for ptype in ELIGIBLE_TYPES:
        pdir = Path(WORKSPACE) / ptype
        if not pdir.is_dir():
            continue
        for f in sorted(pdir.glob("*.md")):
            meta = parse_frontmatter(f)
            status = meta.get("status", "")
            if status in ("superseded", "archived"):
                continue
            meta["_type"] = ptype
            meta["_slug"] = f.stem
            meta["_path"] = str(f)
            key = f"{ptype}/{f.stem}"
            primitives[key] = meta

    # Memory entries
    entries_dir = Path(MEMORY_ENTRIES_DIR)
    if entries_dir.is_dir():
        for f in sorted(entries_dir.glob("*.md")):
            meta = parse_frontmatter(f)
            meta["_type"] = "memories"
            meta["_slug"] = f.stem
            meta["_path"] = str(f)
            # Normalize: use timestamp as date if no date field
            if "date" not in meta and "timestamp" in meta:
                meta["date"] = meta["timestamp"][:10]
            key = f"memories/{f.stem}"
            primitives[key] = meta

    return primitives


# ── Shared Helpers ─────────────────────────────────────────────────────────

def get_tags(meta):
    """Extract tags as a set from primitive metadata."""
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return set(tags)


def get_date(meta):
    """Extract date from primitive metadata, return datetime or None."""
    raw = meta.get("date", "") or meta.get("created", "") or meta.get("timestamp", "")
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
            vals = [v.strip() for v in vals.split(",") if v.strip()]
        for v in vals:
            links.add(v.strip())
    return links


def count_upstream(meta):
    """Count current upstream links."""
    vals = meta.get("upstream", [])
    if isinstance(vals, str):
        vals = [v.strip() for v in vals.split(",") if v.strip()]
    return len(vals)


def already_linked(meta_a, meta_b, key_a, key_b):
    """Check if two primitives are already linked in either direction."""
    links_a = get_existing_links(meta_a)
    links_b = get_existing_links(meta_b)

    type_a, slug_a = key_a.split("/", 1)
    type_b, slug_b = key_b.split("/", 1)

    # Check various ref formats
    refs_a = {key_a, f"{type_a.rstrip('s')}/{slug_a}", slug_a}
    refs_b = {key_b, f"{type_b.rstrip('s')}/{slug_b}", slug_b}

    return bool(links_a & refs_b) or bool(links_b & refs_a)


def pair_key(key_a, key_b):
    """Create a canonical key for a pair (order-independent)."""
    return "|".join(sorted([key_a, key_b]))


# ── Priority Scoring ──────────────────────────────────────────────────────

def compute_pair_priority(meta_a, meta_b):
    """Compute a priority score for comparing this pair.

    Higher = more likely to have a meaningful relationship.
    """
    score = 0
    reasons = []

    tags_a = get_tags(meta_a)
    tags_b = get_tags(meta_b)
    overlap = tags_a & tags_b
    if overlap:
        score += len(overlap) * 2
        reasons.append(f"tags:{','.join(sorted(overlap))}")

    date_a = get_date(meta_a)
    date_b = get_date(meta_b)
    if date_a and date_b and TEMPORAL_PROXIMITY_DAYS > 0:
        delta = abs((date_a - date_b).days)
        if delta <= TEMPORAL_PROXIMITY_DAYS:
            proximity_score = max(1, TEMPORAL_PROXIMITY_DAYS - delta)
            score += proximity_score
            reasons.append(f"temporal:{delta}d")

    # Importance boost for memory entries
    for meta in (meta_a, meta_b):
        imp = meta.get("importance", 0)
        try:
            imp = int(imp)
            if imp >= 4:
                score += imp
                reasons.append(f"importance:{imp}")
        except (ValueError, TypeError):
            pass

    # Domain overlap (high-level tags that indicate shared project space)
    domain_tags = {"snn", "infrastructure", "agents", "pipeline", "primitives"}
    domains_a = tags_a & domain_tags
    domains_b = tags_b & domain_tags
    shared = domains_a & domains_b
    if shared:
        score += len(shared) * 3
        reasons.append(f"domain:{','.join(sorted(shared))}")

    if score == 0:
        score = 1
        reasons.append("baseline")

    return score, reasons


# ── Candidate Generation ──────────────────────────────────────────────────

def generate_candidates(primitives, type_pairs):
    """Generate candidate pairs for a given set of type pairs.

    Returns list of (score, key_a, key_b, reasons) sorted by score descending.
    """
    keys = sorted(primitives.keys())
    candidates = []

    for i, key_a in enumerate(keys):
        meta_a = primitives[key_a]
        type_a = meta_a["_type"]

        for key_b in keys[i + 1:]:
            meta_b = primitives[key_b]
            type_b = meta_b["_type"]

            if frozenset({type_a, type_b}) not in type_pairs:
                continue

            if already_linked(meta_a, meta_b, key_a, key_b):
                continue

            score, reasons = compute_pair_priority(meta_a, meta_b)
            candidates.append((score, key_a, key_b, reasons))

    candidates.sort(key=lambda x: -x[0])
    return candidates


# ── Progress Tracking ──────────────────────────────────────────────────────

def load_progress():
    """Load progress from JSON file."""
    default = {
        "completed_pairs": set(),
        "links_created": 0,
        "pairs_evaluated": 0,
        "no_relationship_count": 0,
        "heuristic_links": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_run": None,
    }
    if not os.path.exists(PROGRESS_FILE):
        return default
    try:
        with open(PROGRESS_FILE) as f:
            data = json.load(f)
        raw_pairs = data.get("completed_pairs", [])
        # Handle both formats: list of strings (original) or list of dicts (from coordinator)
        pairs_set = set()
        for item in raw_pairs:
            if isinstance(item, str):
                pairs_set.add(item)
            elif isinstance(item, dict) and "a" in item and "b" in item:
                pairs_set.add("|".join(sorted([item["a"], item["b"]])))
        data["completed_pairs"] = pairs_set
        return data
    except (json.JSONDecodeError, KeyError):
        return default


def save_progress(progress):
    """Save progress to JSON file."""
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    data = dict(progress)
    data["completed_pairs"] = sorted(data["completed_pairs"])
    data["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── LLM Judgment (single pair) ────────────────────────────────────────────

def build_agent_task(key_a, meta_a, key_b, meta_b):
    """Build a navigation task for the subagent to judge a single pair.
    
    Instead of dumping content, give the agent identifiers and let it 
    browse using belam CLI, memory_search, and read.
    """
    up_count_a = count_upstream(meta_a)
    up_count_b = count_upstream(meta_b)
    cap_note_a = f" ({up_count_a}/{MAX_UPSTREAM} upstream slots used)" if up_count_a > 0 else ""
    cap_note_b = f" ({up_count_b}/{MAX_UPSTREAM} upstream slots used)" if up_count_b > 0 else ""

    # Give the agent the file paths so it can read them directly
    path_a = meta_a["_path"]
    path_b = meta_b["_path"]

    return f"""RELATIONSHIP JUDGMENT TASK — respond with your judgment only, no conversational text.

Evaluate whether a causal upstream/downstream relationship exists between these two primitives:

  A: {key_a}  →  {path_a}{cap_note_a}
  B: {key_b}  →  {path_b}{cap_note_b}

INSTRUCTIONS:
1. Read both files to understand their content
2. If you need more context, use memory_search or read related files — check conversation logs, git history, whatever helps you judge causation
3. Determine if A caused/enabled/motivated B, or B caused/enabled/motivated A, or neither

SEMANTICS:
- Upstream = A causally informed, enabled, or is a prerequisite for B
- Only genuinely CAUSAL links — shared tags or topic is NOT enough
- "A happened, and because of that, B exists" is the test
- Soft cap: {MAX_UPSTREAM} upstream links per primitive. Prefer the strongest causal link.
- When in doubt, output NONE — missing a link is better than a false one

RESPOND WITH EXACTLY:
Line 1: `LINK: {{upstream_ref}} > {{downstream_ref}}` or `NONE`
Line 2: One-sentence rationale

Use exact type/slug refs like: {key_a} or {key_b}"""


def call_opus_single(task_message, dry_run=False):
    """Judge a single pair via openclaw agent with isolated session.

    Uses `openclaw agent --agent main --session-id mapper-<uuid>` for isolation.
    The fresh session-id ensures no collision with the coordinator's active session.

    Returns the raw response text, or empty string on failure.
    Raises TokenExhaustedError if rate-limited / quota hit.
    """
    if dry_run:
        return ""

    AGENT_TIMEOUT = 300  # 5 minutes — room for browsing + judgment

    import uuid
    session_id = f"mapper-{uuid.uuid4().hex[:12]}"

    # Use code-tutor agent (Sonnet) — lightweight, own session space,
    # won't collide with main coordinator session
    cmd = [
        'openclaw', 'agent',
        '--agent', 'code-tutor',
        '--session-id', session_id,
        '--thinking', 'off',
        '--message', task_message,
        '--timeout', str(AGENT_TIMEOUT),
        '--json',
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=AGENT_TIMEOUT + 30,
        )

        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""
        combined = (stderr + " " + stdout).lower()

        # Detect token exhaustion patterns early (only in stderr — stdout
        # JSON legitimately contains "tokens" in stats fields)
        stderr_lower = stderr.lower()
        if any(phrase in stderr_lower for phrase in
               ["rate limit", "quota", "429", "capacity", "overloaded",
                "rate_limit", "too many requests"]):
            raise TokenExhaustedError(f"Token/rate limit: {stderr[:150]}")

        if result.returncode == 0:
            try:
                data = json.loads(stdout)
                status = data.get('status', 'unknown')

                response_text = ''
                payloads = data.get('result', {}).get('payloads', [])
                if payloads:
                    response_text = payloads[0].get('text', '')

                if status == 'ok' and response_text:
                    return response_text
                else:
                    print(f"    ⚠ Agent status={status}, len={len(response_text)}")
                    return response_text or ""

            except json.JSONDecodeError:
                # Try plain text if it contains judgment markers
                if "LINK:" in stdout or "NONE" in stdout:
                    return stdout
                print(f"    ⚠ Failed to parse agent response")
                return ""
        else:
            stderr_lower = stderr.lower()
            if any(phrase in stderr_lower for phrase in
                   ["rate limit", "quota", "429", "capacity", "overloaded",
                    "rate_limit", "too many requests"]):
                raise TokenExhaustedError(f"Token/rate limit: {stderr[:150]}")
            print(f"    ⚠ Exit code {result.returncode}: {(stderr or stdout)[:100]}")
            return ""

    except subprocess.TimeoutExpired:
        print(f"    ⚠ Timed out after {AGENT_TIMEOUT}s")
        return ""
    except TokenExhaustedError:
        raise
    except FileNotFoundError:
        print(f"    ✗ openclaw CLI not found")
        return ""
    except Exception as e:
        err_str = str(e).lower()
        if any(phrase in err_str for phrase in
               ["rate limit", "quota", "429", "capacity"]):
            raise TokenExhaustedError(str(e))
        print(f"    ⚠ Error: {e}")
        return ""


class TokenExhaustedError(Exception):
    """Raised when token quota or rate limit is hit."""
    pass


def parse_single_judgment(response, key_a, key_b):
    """Parse a single-pair judgment response.

    Returns dict: { 'action': 'link'|'none', 'upstream': ..., 'downstream': ..., 'rationale': ... }
    """
    lines = [l.strip() for l in response.strip().split("\n") if l.strip()]
    if not lines:
        return {"action": "none", "pair": (key_a, key_b), "rationale": "empty response"}

    first = lines[0]
    rationale = lines[1] if len(lines) > 1 else ""

    if first.startswith("NONE"):
        return {"action": "none", "pair": (key_a, key_b), "rationale": rationale}

    m = re.match(r'LINK:\s*(.+?)\s*>\s*(.+)', first)
    if m:
        upstream = m.group(1).strip()
        downstream = m.group(2).strip()
        return {
            "action": "link",
            "upstream": upstream,
            "downstream": downstream,
            "rationale": rationale,
        }

    return {"action": "none", "pair": (key_a, key_b), "rationale": f"unparseable: {first}"}


# ── Heuristic Linking ──────────────────────────────────────────────────────

def run_heuristic_linking(primitives, progress, dry_run=False):
    """Apply safe heuristic links — only unambiguous structural relationships.

    Two safe patterns:
    1. Explicit `depends_on` fields in task frontmatter → wire as upstream
    2. Same-type chronological chains (memories) with high tag overlap → earlier upstream
    """
    links_created = 0
    pairs_processed = 0

    # ── Pattern 1: Explicit depends_on fields ──
    print("  Checking explicit depends_on fields...")
    for key, meta in primitives.items():
        depends = meta.get("depends_on", [])
        if isinstance(depends, str):
            depends = [d.strip() for d in depends.split(",") if d.strip()]
        for dep_slug in depends:
            # Try to find the dependency in any type
            dep_key = None
            for ptype in ELIGIBLE_TYPES:
                candidate = f"{ptype}/{dep_slug}"
                if candidate in primitives:
                    dep_key = candidate
                    break
            if dep_key and not already_linked(primitives[dep_key], meta, dep_key, key):
                pk = pair_key(dep_key, key)
                if pk not in progress["completed_pairs"]:
                    created = apply_link(dep_key, key, dry_run=dry_run)
                    if created:
                        links_created += 1
                    progress["completed_pairs"].add(pk)
                    pairs_processed += 1

    # ── Pattern 2: Same-day memory chains with high tag overlap ──
    print("  Checking same-day memory chains...")
    candidates = generate_candidates(primitives, HEURISTIC_TYPE_PAIRS)
    for score, key_a, key_b, reasons in candidates:
        pk = pair_key(key_a, key_b)
        if pk in progress["completed_pairs"]:
            continue

        meta_a = primitives[key_a]
        meta_b = primitives[key_b]

        tags_a = get_tags(meta_a)
        tags_b = get_tags(meta_b)
        overlap = tags_a & tags_b

        if len(overlap) < HEURISTIC_MIN_TAG_OVERLAP:
            continue

        date_a = get_date(meta_a)
        date_b = get_date(meta_b)
        if not date_a or not date_b:
            continue
        if abs((date_a - date_b).days) > HEURISTIC_MAX_TEMPORAL_GAP:
            continue

        # Chronological: earlier is upstream
        if date_a <= date_b:
            upstream_key, downstream_key = key_a, key_b
            downstream_meta = meta_b
        else:
            upstream_key, downstream_key = key_b, key_a
            downstream_meta = meta_a

        if count_upstream(downstream_meta) >= MAX_UPSTREAM:
            continue

        created = apply_link(upstream_key, downstream_key, dry_run=dry_run)
        if created:
            links_created += 1

        progress["completed_pairs"].add(pk)
        pairs_processed += 1

    progress["heuristic_links"] = progress.get("heuristic_links", 0) + links_created
    save_progress(progress)

    return pairs_processed, links_created


# ── Link Application ──────────────────────────────────────────────────────

def apply_link(upstream_ref, downstream_ref, dry_run=False):
    """Apply a single upstream/downstream link between two primitives.

    Returns True if link was created, False if already existed or failed.
    """
    up_parts = upstream_ref.split("/", 1)
    dn_parts = downstream_ref.split("/", 1)

    if len(up_parts) != 2 or len(dn_parts) != 2:
        print(f"  ✗ Invalid ref format: {upstream_ref} or {downstream_ref}")
        return False

    up_type, up_slug = up_parts
    dn_type, dn_slug = dn_parts

    # Memory entries live in a subdirectory
    if up_type == "memories":
        up_path = Path(MEMORY_ENTRIES_DIR) / f"{up_slug}.md"
    else:
        up_path = Path(WORKSPACE) / up_type / f"{up_slug}.md"

    if dn_type == "memories":
        dn_path = Path(MEMORY_ENTRIES_DIR) / f"{dn_slug}.md"
    else:
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

    # Import link helper from belam_index
    sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
    from belam_index import _add_to_frontmatter_list

    # Canonical ref format for frontmatter (singular type name)
    type_singular = {"lessons": "lesson", "decisions": "decision", "tasks": "task",
                     "projects": "project", "knowledge": "knowledge", "memories": "memory"}
    up_canon = f"{type_singular.get(up_type, up_type)}/{up_slug}"
    dn_canon = f"{type_singular.get(dn_type, dn_type)}/{dn_slug}"

    changed_any = False

    content = up_path.read_text(errors="replace")
    new_content, changed = _add_to_frontmatter_list(content, "downstream", dn_canon)
    if changed:
        up_path.write_text(new_content)
        changed_any = True

    content = dn_path.read_text(errors="replace")
    new_content, changed = _add_to_frontmatter_list(content, "upstream", up_canon)
    if changed:
        dn_path.write_text(new_content)
        changed_any = True

    if changed_any:
        print(f"  ✓ {upstream_ref} → {downstream_ref}")
    else:
        print(f"  · Already linked: {upstream_ref} → {downstream_ref}")

    return changed_any


# ── Rebuild Indexes ────────────────────────────────────────────────────────

def rebuild_indexes():
    """Rebuild primitive indexes after link changes."""
    embed_script = Path(WORKSPACE) / "scripts" / "embed_primitives.py"
    if embed_script.exists():
        subprocess.run(
            [sys.executable, str(embed_script)],
            capture_output=True, cwd=str(WORKSPACE)
        )


# ── Main Orchestration ─────────────────────────────────────────────────────

def show_status(primitives, progress):
    """Display progress statistics."""
    llm_candidates = generate_candidates(primitives, LLM_TYPE_PAIRS)
    heuristic_candidates = generate_candidates(primitives, HEURISTIC_TYPE_PAIRS)
    completed = len(progress["completed_pairs"])

    # Count how many of each are remaining
    llm_remaining = sum(1 for _, ka, kb, _ in llm_candidates
                        if pair_key(ka, kb) not in progress["completed_pairs"])
    heur_remaining = sum(1 for _, ka, kb, _ in heuristic_candidates
                         if pair_key(ka, kb) not in progress["completed_pairs"])

    # Count by type
    type_counts = {}
    for p in primitives.values():
        t = p["_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f"\n  🔮 RELATIONSHIP MAPPER STATUS")
    print(f"  {'─' * 50}")
    print(f"  Primitives:        {len(primitives)}")
    for t in sorted(type_counts):
        print(f"    {t:20s} {type_counts[t]:4d}")
    print(f"  {'─' * 50}")
    print(f"  LLM candidates:    {len(llm_candidates):5d}  (remaining: {llm_remaining})")
    print(f"  Heuristic cand.:   {len(heuristic_candidates):5d}  (remaining: {heur_remaining})")
    print(f"  Completed:         {completed:5d}")
    print(f"  LLM links:         {progress.get('links_created', 0):5d}")
    print(f"  Heuristic links:   {progress.get('heuristic_links', 0):5d}")
    print(f"  No-relationship:   {progress.get('no_relationship_count', 0):5d}")
    print(f"  Started:           {progress.get('started_at', 'never')}")
    print(f"  Last run:          {progress.get('last_run', 'never')}")

    if llm_remaining > 0:
        est_min = llm_remaining * 3
        est_hours = est_min / 60
        print(f"  LLM est. remain:   ~{est_hours:.1f}h at 1 pair/3min")
    print()


def run_llm_batch(count, primitives, progress, dry_run=False):
    """Run N single-pair LLM judgments.

    Returns (pairs_evaluated, links_created).
    """
    candidates = generate_candidates(primitives, LLM_TYPE_PAIRS)

    remaining = [
        (score, ka, kb, reasons)
        for score, ka, kb, reasons in candidates
        if pair_key(ka, kb) not in progress["completed_pairs"]
    ]

    if not remaining:
        print("  ✓ All LLM candidate pairs evaluated!")
        return 0, 0

    batch = remaining[:count]
    total_evaluated = 0
    total_links = 0

    for idx, (score, ka, kb, reasons) in enumerate(batch, 1):
        meta_a = primitives[ka]
        meta_b = primitives[kb]

        # Check upstream caps before bothering with LLM
        up_a = count_upstream(meta_a)
        up_b = count_upstream(meta_b)
        if up_a >= MAX_UPSTREAM and up_b >= MAX_UPSTREAM:
            print(f"  [{idx}/{len(batch)}] Skip (both at upstream cap): {ka} ↔ {kb}")
            progress["completed_pairs"].add(pair_key(ka, kb))
            continue

        print(f"  [{idx}/{len(batch)}] [{score:3d}] {ka} ↔ {kb}  ({', '.join(reasons)})")

        task = build_agent_task(ka, meta_a, kb, meta_b)

        if dry_run:
            print(f"    [dry-run] task: {len(task)} chars")
            progress["completed_pairs"].add(pair_key(ka, kb))
            total_evaluated += 1
            continue

        try:
            response = call_opus_single(task)
        except TokenExhaustedError as e:
            print(f"\n  ⏸ Token quota exhausted: {e}")
            print(f"  Saving progress ({total_evaluated} pairs evaluated this run)...")
            save_progress(progress)
            print(f"  Will resume from here on next invocation.")
            return total_evaluated, total_links

        if response:
            result = parse_single_judgment(response, ka, kb)
            if result["action"] == "link":
                # Verify upstream cap on the downstream target
                dn_key = result["downstream"]
                if dn_key in primitives and count_upstream(primitives[dn_key]) < MAX_UPSTREAM:
                    created = apply_link(result["upstream"], result["downstream"])
                    if created:
                        total_links += 1
                        progress["links_created"] = progress.get("links_created", 0) + 1
                    print(f"    Rationale: {result.get('rationale', '')}")
                else:
                    print(f"    Skip link (upstream cap reached on {dn_key})")
            else:
                progress["no_relationship_count"] = progress.get("no_relationship_count", 0) + 1
                print(f"    NONE — {result.get('rationale', '')}")
        else:
            # Empty response — might be transient failure, don't mark as completed
            # so it gets retried next run
            print(f"    ⚠ No response — will retry next run")
            save_progress(progress)
            continue

        progress["completed_pairs"].add(pair_key(ka, kb))
        progress["pairs_evaluated"] = progress.get("pairs_evaluated", 0) + 1
        total_evaluated += 1

        # Save progress after each pair (resumable)
        save_progress(progress)

    return total_evaluated, total_links


def _process_one_pair(idx, total, score, ka, kb, reasons, primitives, dry_run=False):
    """Process a single pair — thread-safe, returns result dict."""
    meta_a = primitives[ka]
    meta_b = primitives[kb]

    up_a = count_upstream(meta_a)
    up_b = count_upstream(meta_b)
    if up_a >= MAX_UPSTREAM and up_b >= MAX_UPSTREAM:
        return {"ka": ka, "kb": kb, "action": "skip", "rationale": "both at upstream cap"}

    task = build_agent_task(ka, meta_a, kb, meta_b)

    if dry_run:
        return {"ka": ka, "kb": kb, "action": "dry_run", "rationale": f"task: {len(task)} chars"}

    try:
        response = call_opus_single(task)
    except TokenExhaustedError as e:
        return {"ka": ka, "kb": kb, "action": "token_exhausted", "rationale": str(e)}

    if not response:
        return {"ka": ka, "kb": kb, "action": "no_response", "rationale": "empty response"}

    result = parse_single_judgment(response, ka, kb)
    return {"ka": ka, "kb": kb, "score": score, "reasons": reasons, **result}


_progress_lock = threading.Lock()


def run_llm_batch_parallel(count, workers, primitives, progress, dry_run=False):
    """Run N pairs with W parallel workers."""
    candidates = generate_candidates(primitives, LLM_TYPE_PAIRS)
    remaining = [
        (score, ka, kb, reasons)
        for score, ka, kb, reasons in candidates
        if pair_key(ka, kb) not in progress["completed_pairs"]
    ]

    if not remaining:
        print("  ✓ All LLM candidate pairs evaluated!")
        return 0, 0

    batch = remaining[:count]
    total_evaluated = 0
    total_links = 0
    token_exhausted = False

    print(f"  Processing {len(batch)} pairs with {workers} workers...\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for idx, (score, ka, kb, reasons) in enumerate(batch, 1):
            f = executor.submit(_process_one_pair, idx, len(batch), score, ka, kb, reasons, primitives, dry_run)
            futures[f] = (idx, score, ka, kb, reasons)

        for future in as_completed(futures):
            idx, score, ka, kb, reasons = futures[future]
            try:
                result = future.result()
            except Exception as e:
                print(f"  [{idx}/{len(batch)}] ⚠ Exception: {e}")
                continue

            pk = pair_key(result["ka"], result["kb"])

            if result["action"] == "token_exhausted":
                print(f"  [{idx}/{len(batch)}] ⏸ Token exhausted")
                token_exhausted = True
                continue

            if result["action"] == "no_response":
                print(f"  [{idx}/{len(batch)}] [{score:3d}] {ka} ↔ {kb} — ⚠ no response, will retry")
                continue

            if result["action"] == "skip":
                with _progress_lock:
                    progress["completed_pairs"].add(pk)
                print(f"  [{idx}/{len(batch)}] Skip (cap): {ka} ↔ {kb}")
                continue

            if result["action"] == "link":
                dn_key = result["downstream"]
                with _progress_lock:
                    if dn_key in primitives and count_upstream(primitives[dn_key]) < MAX_UPSTREAM:
                        created = apply_link(result["upstream"], result["downstream"])
                        if created:
                            total_links += 1
                            progress["links_created"] = progress.get("links_created", 0) + 1
                        print(f"  [{idx}/{len(batch)}] [{score:3d}] {ka} ↔ {kb} → LINK: {result['upstream']} > {result['downstream']}")
                    else:
                        print(f"  [{idx}/{len(batch)}] [{score:3d}] {ka} ↔ {kb} → Skip link (upstream cap)")
            else:
                with _progress_lock:
                    progress["no_relationship_count"] = progress.get("no_relationship_count", 0) + 1
                print(f"  [{idx}/{len(batch)}] [{score:3d}] {ka} ↔ {kb} → NONE")

            with _progress_lock:
                progress["completed_pairs"].add(pk)
                progress["pairs_evaluated"] = progress.get("pairs_evaluated", 0) + 1
                total_evaluated += 1
                # Save periodically
                if total_evaluated % 5 == 0:
                    save_progress(progress)

    save_progress(progress)

    if token_exhausted:
        raise TokenExhaustedError("Hit during parallel batch")

    return total_evaluated, total_links


def main():
    parser = argparse.ArgumentParser(description="Incremental Relationship Mapper")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen, no writes")
    parser.add_argument("--status", action="store_true", help="Show progress statistics")
    parser.add_argument("--burst", type=int, default=0, help="Burn through N pairs in LLM mode")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers for burst mode")
    parser.add_argument("--heuristic", action="store_true", help="Run heuristic linking (no LLM)")
    parser.add_argument("--reset", action="store_true", help="Clear progress, start fresh")
    parser.add_argument("--filter-only", action="store_true", help="Show candidate counts, exit")
    parser.add_argument("--queue", type=int, default=0, help="Generate N task JSONs to canvas/mapper_queue.json for coordinator")
    parser.add_argument("--apply-result", type=str, default="", help="Apply a judgment result: 'key_a|key_b|LINK|up>down|rationale' or 'key_a|key_b|NONE|rationale'")
    args = parser.parse_args()

    if args.reset:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            print("  ✓ Progress reset")
        else:
            print("  · No progress file to reset")
        return

    primitives = load_all_primitives()
    progress = load_progress()

    if args.status:
        show_status(primitives, progress)
        return

    if args.filter_only:
        llm_cands = generate_candidates(primitives, LLM_TYPE_PAIRS)
        heur_cands = generate_candidates(primitives, HEURISTIC_TYPE_PAIRS)
        print(f"\n  Primitives: {len(primitives)}")
        print(f"  LLM candidates: {len(llm_cands)}")
        print(f"  Heuristic candidates: {len(heur_cands)}")
        print(f"\n  Top 10 LLM pairs:")
        for score, ka, kb, reasons in llm_cands[:10]:
            print(f"    [{score:3d}] {ka} ↔ {kb}  ({', '.join(reasons)})")
        print(f"\n  Top 10 heuristic pairs:")
        for score, ka, kb, reasons in heur_cands[:10]:
            print(f"    [{score:3d}] {ka} ↔ {kb}  ({', '.join(reasons)})")
        print()
        return

    if args.apply_result:
        # Format: "key_a|key_b|LINK|upstream>downstream|rationale" or "key_a|key_b|NONE|rationale"
        parts = args.apply_result.split("|")
        ka, kb = parts[0], parts[1]
        action = parts[2]
        pk = pair_key(ka, kb)

        if action == "LINK" and len(parts) >= 5:
            link_parts = parts[3].split(">")
            upstream, downstream = link_parts[0].strip(), link_parts[1].strip()
            rationale = parts[4] if len(parts) > 4 else ""
            if downstream in primitives and count_upstream(primitives[downstream]) < MAX_UPSTREAM:
                created = apply_link(upstream, downstream)
                if created:
                    progress["links_created"] = progress.get("links_created", 0) + 1
                    print(f"  ✓ LINK: {upstream} > {downstream}")
                else:
                    print(f"  · Link already exists or failed")
            else:
                print(f"  · Skip (upstream cap or unknown downstream)")
        else:
            progress["no_relationship_count"] = progress.get("no_relationship_count", 0) + 1
            print(f"  · NONE: {ka} ↔ {kb}")

        progress["completed_pairs"].add(pk)
        progress["pairs_evaluated"] = progress.get("pairs_evaluated", 0) + 1
        save_progress(progress)
        return

    if args.queue > 0:
        candidates = generate_candidates(primitives, LLM_TYPE_PAIRS)
        remaining = [
            (score, ka, kb, reasons)
            for score, ka, kb, reasons in candidates
            if pair_key(ka, kb) not in progress["completed_pairs"]
        ]
        batch = remaining[:args.queue]
        tasks = []
        for score, ka, kb, reasons in batch:
            meta_a = primitives[ka]
            meta_b = primitives[kb]
            up_a = count_upstream(meta_a)
            up_b = count_upstream(meta_b)
            if up_a >= MAX_UPSTREAM and up_b >= MAX_UPSTREAM:
                continue
            task_text = build_agent_task(ka, meta_a, kb, meta_b)
            tasks.append({
                "key_a": ka,
                "key_b": kb,
                "score": score,
                "task": task_text,
            })
        queue_file = os.path.join(os.path.dirname(PROGRESS_FILE), "mapper_queue.json")
        with open(queue_file, "w") as f:
            json.dump(tasks, f, indent=2)
        print(f"  Queued {len(tasks)} tasks to {queue_file}")
        print(f"  Remaining after queue: {len(remaining) - len(tasks)}")
        return

    if args.heuristic:
        print(f"  Running heuristic linking...")
        pairs, links = run_heuristic_linking(primitives, progress, dry_run=args.dry_run)
        if links > 0 and not args.dry_run:
            rebuild_indexes()
        print(f"\n  Done: {pairs} pairs processed, {links} links created")
        return

    # LLM mode: default 1 pair, or burst N
    count = args.burst if args.burst > 0 else 1
    workers = args.workers if args.workers > 1 else 1
    print(f"  Loaded {len(primitives)} primitives")

    if workers > 1 and count > 1:
        try:
            evaluated, links = run_llm_batch_parallel(count, workers, primitives, progress, dry_run=args.dry_run)
        except TokenExhaustedError as e:
            print(f"\n  ⏸ Token quota exhausted: {e}")
            print(f"  Progress saved. Will resume on next cron invocation.")
            save_progress(progress)
            sys.exit(0)
    else:
        try:
            evaluated, links = run_llm_batch(count, primitives, progress, dry_run=args.dry_run)
        except TokenExhaustedError as e:
            print(f"\n  ⏸ Token quota exhausted: {e}")
            print(f"  Progress saved. Will resume on next cron invocation.")
            save_progress(progress)
            sys.exit(0)

    if links > 0 and not args.dry_run:
        rebuild_indexes()

    save_progress(progress)
    print(f"\n  Done: {evaluated} pairs evaluated, {links} links created")


if __name__ == "__main__":
    main()
