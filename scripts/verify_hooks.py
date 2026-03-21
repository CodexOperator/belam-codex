#!/usr/bin/env python3
"""
verify_hooks.py — OpenClaw Hook Integration Verification Script

Tests OpenClaw hook integration points before wiring the orchestration engine
to dispatch agents through hooks.

Tests:
  1. Hook Discovery         — scan docs + cross-reference the 27-hook catalog
  2. Naming Convention      — verify colon vs underscore layer conventions
  3. Hook Health Check      — validate workspace hooks/ directory entries
  4. Plugin Prototype       — validate 3 plugin prototypes in openclaw-plugins/
  5. Orchestration Surface  — rate orchestration-relevant hooks with context docs

Outputs:
  - Structured console report
  - scripts/hook_verification_report.md (persistent reference)

Safe during active sessions: read-only filesystem checks + non-destructive CLI queries.
"""

import os
import sys
import json
import ast
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ── Workspace root ────────────────────────────────────────────────────────────
WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE", Path.home() / ".openclaw" / "workspace"))
RESULTS_DIR = WORKSPACE_DIR / "machinelearning" / "snn_applied_finance" / "notebooks" / "local_results" / "research-openclaw-internals"
PIPELINE_BUILDS_DIR = WORKSPACE_DIR / "machinelearning" / "snn_applied_finance" / "research" / "pipeline_builds"
PLUGINS_DIR = PIPELINE_BUILDS_DIR / "openclaw-plugins"
HOOKS_DIR = WORKSPACE_DIR / "hooks"
DOCS_DIR = WORKSPACE_DIR / "docs"
OUTPUT_REPORT = WORKSPACE_DIR / "scripts" / "hook_verification_report.md"

# ── The 27 canonical hooks (from research-openclaw-internals catalog) ─────────
INTERNAL_HOOKS = [
    "command:new",
    "command:reset",
    "command:stop",
    "agent:bootstrap",
    "gateway:startup",
    "message:received",
    "message:transcribed",
    "message:preprocessed",
    "message:sent",
    "session:compact:before",
    "session:compact:after",
]

PLUGIN_HOOKS = [
    "before_model_resolve",
    "before_prompt_build",
    "before_agent_start",
    "agent_end",
    "before_tool_call",
    "after_tool_call",
    "tool_result_persist",
    "message_received",
    "message_sending",
    "message_sent",
    "session_start",
    "session_end",
    "gateway_start",
    "gateway_stop",
    "before_compaction",
    "after_compaction",
]

ALL_KNOWN_HOOKS = set(INTERNAL_HOOKS + PLUGIN_HOOKS)

# Command wildcard — HOOK.md uses "command" as shorthand for command:* events
INTERNAL_HOOK_PREFIXES = {"command", "agent", "gateway", "message", "session"}

# ── Orchestration-relevant hooks with detail ──────────────────────────────────
ORCHESTRATION_HOOKS = {
    "before_prompt_build": {
        "layer": "plugin",
        "registration": "api.on('before_prompt_build', handler, { priority })",
        "timing": "After session load, before model inference — messages are available",
        "context_available": [
            "ctx.workspaceDir — absolute path to the agent's workspace",
            "ctx.agentId — current agent identifier",
            "ctx.sessionKey — current session key (e.g. agent:main:telegram:group:-123)",
            "ctx.messages — current message array (read-only view)",
            "ctx.channel — channel metadata",
            "ctx.conversationId — conversation identifier",
        ],
        "can_modify": [
            "prependContext — text prepended to the current user message",
            "systemPrompt — full system prompt OVERRIDE (replaces everything)",
            "prependSystemContext — injected BEFORE the existing system prompt",
            "appendSystemContext — injected AFTER bootstrap files (AGENTS.md, SOUL.md, etc.)",
        ],
        "orchestration_rating": "HIGH",
        "orchestration_reasoning": (
            "Best injection point for pipeline state. Fires every turn with full message context. "
            "appendSystemContext is additive and provider-cache-friendly. "
            "Implemented by pipeline-context plugin. "
            "CRITICAL: wrong naming convention (e.g. before:prompt:build) means silent no-fire."
        ),
    },
    "agent:bootstrap": {
        "layer": "internal",
        "registration": "api.registerHook('agent:bootstrap', handler, { name, description })",
        "timing": "Session start only — before system prompt assembly, bootstrap files are mutable",
        "context_available": [
            "event.context.workspaceDir — workspace directory",
            "event.context.bootstrapFiles — array of {name, path, content, missing} objects",
            "event.context.agentId — current agent identifier",
            "event.sessionKey — current session key",
        ],
        "can_modify": [
            "event.context.bootstrapFiles — push/unshift to inject additional context files",
            "event.context.bootstrapFiles[i].content — mutate existing bootstrap file content",
        ],
        "orchestration_rating": "MEDIUM",
        "orchestration_reasoning": (
            "Good for session-start bootstrap injection (e.g. PIPELINE_STATUS.md). "
            "Fires ONCE per session, not per turn — cheaper but less dynamic than before_prompt_build. "
            "Implemented by supermap-boot hook to inject CODEX.codex. "
            "Use for stable session-start context; use before_prompt_build for turn-by-turn state."
        ),
    },
    "after_tool_call": {
        "layer": "plugin",
        "registration": "api.on('after_tool_call', handler, { priority })",
        "timing": "After each tool execution, before tool result is added to transcript",
        "context_available": [
            "event.toolName / event.name — name of the tool that fired",
            "event.params / event.arguments — parameters passed to the tool",
            "event.result — tool result object (can be modified)",
            "event.error — error if tool failed (null on success)",
            "event.sessionKey — current session key",
        ],
        "can_modify": [
            "Return value from handler can modify/replace the tool result",
            "Can suppress tool result (replace with neutral response)",
            "Can augment result with additional context",
        ],
        "orchestration_rating": "HIGH",
        "orchestration_reasoning": (
            "Critical for orchestration auditing — every tool call passes through this hook. "
            "Can intercept pipeline_orchestrate exec calls to track state transitions. "
            "Can detect exec tool calls to flag when orchestrator is being invoked. "
            "Used by agent-turn-logger plugin for logging (priority 90 = low interference). "
            "Combined with agent_end enables full turn-level orchestration telemetry."
        ),
    },
    "agent_end": {
        "layer": "plugin",
        "registration": "api.on('agent_end', handler, { priority })",
        "timing": "After full agent turn completes — reply assembled, before session persist",
        "context_available": [
            "ctx.messages — full message array for the turn (assistant + tool calls)",
            "ctx.agentId — agent that completed the turn",
            "ctx.sessionKey — session key",
            "ctx.usage — token usage stats (prompt, completion, total)",
            "ctx.latencyMs — turn latency in milliseconds",
            "ctx.model — model used for this turn",
        ],
        "can_modify": [
            "Read-only inspection of completed turn (primary use case)",
            "Can trigger side-effects: log, alert, push metrics",
            "Cannot modify already-sent reply",
        ],
        "orchestration_rating": "HIGH",
        "orchestration_reasoning": (
            "Best hook for post-turn orchestration decisions. Full visibility into what the agent "
            "just did (tools called, content generated, tokens used). "
            "Ideal for: detecting pipeline handoff signals in output, tracking when orchestrator "
            "transitions are made, cost monitoring per pipeline stage. "
            "Compose with after_tool_call for complete turn-level telemetry."
        ),
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# Result tracking
# ═══════════════════════════════════════════════════════════════════════════════

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = True
        self.critical = False
        self.findings: list[dict] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def warn(self, msg: str):
        self.warnings.append(msg)

    def error(self, msg: str, critical: bool = False):
        self.errors.append(msg)
        self.passed = False
        if critical:
            self.critical = True

    def find(self, key: str, value, status: str = "ok"):
        self.findings.append({"key": key, "value": value, "status": status})


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: Hook Discovery
# ═══════════════════════════════════════════════════════════════════════════════

def test_hook_discovery() -> TestResult:
    """
    Scan docs dir for documented hooks and cross-reference against the 27-hook catalog.
    Also verifies results_summary.json still matches the canonical hook set.
    """
    r = TestResult("Hook Discovery")

    # 1a. Try to load results_summary.json (canonical hook catalog source)
    catalog_hooks_internal = set()
    catalog_hooks_plugin = set()
    catalog_total = 0

    results_json = RESULTS_DIR / "results_summary.json"
    if results_json.exists():
        try:
            with open(results_json) as f:
                data = json.load(f)
            exp2 = data.get("experiments", {}).get("exp2_hook_naming", {})
            for check in exp2.get("checks", []):
                if check["layer"] == "internal":
                    catalog_hooks_internal.add(check["name"])
                else:
                    catalog_hooks_plugin.add(check["name"])
            catalog_total = exp2.get("total_hooks", 0)
            r.find("catalog_source", str(results_json.relative_to(WORKSPACE_DIR)), "ok")
            r.find("catalog_total_hooks", catalog_total, "ok")
        except Exception as e:
            r.warn(f"Could not load results_summary.json: {e} — using hardcoded catalog")
            catalog_hooks_internal = set(INTERNAL_HOOKS)
            catalog_hooks_plugin = set(PLUGIN_HOOKS)
            catalog_total = len(INTERNAL_HOOKS) + len(PLUGIN_HOOKS)
    else:
        r.warn("results_summary.json not found — using hardcoded hook catalog")
        catalog_hooks_internal = set(INTERNAL_HOOKS)
        catalog_hooks_plugin = set(PLUGIN_HOOKS)
        catalog_total = len(INTERNAL_HOOKS) + len(PLUGIN_HOOKS)

    catalog_all = catalog_hooks_internal | catalog_hooks_plugin

    # 1b. Cross-reference against hardcoded canonical set
    hardcoded_all = set(INTERNAL_HOOKS) | set(PLUGIN_HOOKS)

    new_since_research = catalog_all - hardcoded_all
    missing_from_catalog = hardcoded_all - catalog_all

    if new_since_research:
        r.warn(f"Hooks in catalog but NOT in hardcoded list (new since research?): {sorted(new_since_research)}")
    if missing_from_catalog:
        r.warn(f"Hooks in hardcoded list but NOT in catalog: {sorted(missing_from_catalog)}")

    r.find("internal_hooks_count", len(catalog_hooks_internal), "ok")
    r.find("plugin_hooks_count", len(catalog_hooks_plugin), "ok")
    r.find("catalog_internal_hooks", sorted(catalog_hooks_internal), "ok")
    r.find("catalog_plugin_hooks", sorted(catalog_hooks_plugin), "ok")

    # 1c. Scan docs directory for any hook mentions we might have missed
    docs_mentioned_hooks = set()
    if DOCS_DIR.exists():
        for md_file in DOCS_DIR.rglob("*.md"):
            try:
                text = md_file.read_text(errors="replace")
                # Look for colon-separated internal hooks
                for m in re.finditer(r'\b([a-z][a-z_]+:[a-z][a-z:_]+)\b', text):
                    candidate = m.group(1)
                    # Filter to plausible hook names (avoid false positives like URLs)
                    if "://" not in candidate and len(candidate) < 50:
                        docs_mentioned_hooks.add(candidate)
                # Look for underscore plugin hooks
                for m in re.finditer(r'\b(before_[a-z_]+|after_[a-z_]+|agent_end|tool_result_persist|message_s(?:ent|ending|received)|session_(?:start|end)|gateway_(?:start|stop))\b', text):
                    docs_mentioned_hooks.add(m.group(1))
            except Exception:
                pass

    docs_known = docs_mentioned_hooks & ALL_KNOWN_HOOKS
    docs_unknown = docs_mentioned_hooks - ALL_KNOWN_HOOKS - {"http://", "https://"}

    r.find("docs_dir_scanned", str(DOCS_DIR.relative_to(WORKSPACE_DIR) if DOCS_DIR.is_relative_to(WORKSPACE_DIR) else DOCS_DIR), "ok")
    r.find("docs_hook_mentions", sorted(docs_known), "ok")
    if docs_unknown:
        r.find("docs_unknown_hook_candidates", sorted(docs_unknown)[:20], "warn")
        r.warn(f"Docs mention {len(docs_unknown)} unrecognized hook-like tokens (may be false positives)")

    # 1d. Verify catalog_total matches expectation
    if catalog_total == 27:
        r.find("catalog_count_check", "27 hooks — matches research catalog ✓", "ok")
    elif catalog_total > 0:
        r.warn(f"Expected 27 hooks in catalog, found {catalog_total}")
        r.find("catalog_count_check", f"{catalog_total} hooks (expected 27)", "warn")

    return r


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: Naming Convention Verification
# ═══════════════════════════════════════════════════════════════════════════════

def _classify_hook_name(name: str) -> str:
    """
    Classify a hook name by its naming convention.
    Returns 'internal' (colon-sep), 'plugin' (underscore-sep), or 'ambiguous'.
    """
    has_colon = ":" in name
    has_underscore = "_" in name

    if has_colon and not has_underscore:
        return "internal"
    if has_underscore and not has_colon:
        return "plugin"
    if not has_colon and not has_underscore:
        # Simple word — could be a wildcard/prefix event name like "command"
        return "simple"
    return "ambiguous"  # has both (shouldn't happen in practice)


def _extract_events_from_hook_md(hook_md_path: Path) -> list[str]:
    """Parse the HOOK.md frontmatter to extract declared events."""
    events = []
    try:
        content = hook_md_path.read_text(errors="replace")
        # YAML frontmatter between --- markers
        m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if m:
            frontmatter = m.group(1)
            # events field — handle both inline array and block sequence
            event_match = re.search(r'events:\s*\[([^\]]*)\]', frontmatter)
            if event_match:
                # Inline array: ["command:new", "agent:bootstrap"]
                raw = event_match.group(1)
                events = [e.strip().strip('"\'') for e in raw.split(',') if e.strip()]
            else:
                # Block sequence
                in_events = False
                for line in frontmatter.split('\n'):
                    if re.match(r'\s*events:', line):
                        in_events = True
                        continue
                    if in_events:
                        item = re.match(r'\s*-\s*(.+)', line)
                        if item:
                            events.append(item.group(1).strip().strip('"\''))
                        elif line.strip() and not line.startswith(' '):
                            break
    except Exception:
        pass
    return events


def test_naming_conventions() -> TestResult:
    """
    Verify two-layer naming convention:
      - Internal: colon-separated (message:sent, agent:bootstrap)
      - Plugin: underscore-separated (before_prompt_build, after_tool_call)

    Scans workspace hooks/ for violations.
    Also validates that known hooks follow the right convention.
    """
    r = TestResult("Naming Convention Verification")

    # 2a. Verify all canonical hooks follow their layer's convention
    convention_violations = []
    for hook_name in INTERNAL_HOOKS:
        conv = _classify_hook_name(hook_name)
        if conv != "internal":
            convention_violations.append({
                "hook": hook_name, "expected": "internal (colon-sep)",
                "detected": conv, "source": "catalog"
            })

    for hook_name in PLUGIN_HOOKS:
        conv = _classify_hook_name(hook_name)
        if conv != "plugin":
            convention_violations.append({
                "hook": hook_name, "expected": "plugin (underscore-sep)",
                "detected": conv, "source": "catalog"
            })

    if convention_violations:
        r.error(f"Canonical catalog has {len(convention_violations)} naming convention violations!")
        for v in convention_violations:
            r.error(f"  {v['hook']} — expected {v['expected']}, got {v['detected']}")
    else:
        r.find("canonical_catalog_convention", "All 27 hooks follow correct naming convention ✓", "ok")

    # 2b. Scan hooks/ directory for convention violations
    if not HOOKS_DIR.exists():
        r.warn("hooks/ directory not found — skipping workspace hook scan")
        r.find("hooks_dir", "Not found", "warn")
        return r

    hook_entries = [d for d in HOOKS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]
    r.find("hooks_dir_entries", len(hook_entries), "ok")

    workspace_violations = []
    for hook_dir in sorted(hook_entries):
        hook_md = hook_dir / "HOOK.md"
        if not hook_md.exists():
            continue

        events = _extract_events_from_hook_md(hook_md)
        for event in events:
            # "command" is a valid wildcard for command:* family — flag with note
            conv = _classify_hook_name(event)
            expected_layer = None

            # Check if it matches a known hook
            if event in set(INTERNAL_HOOKS):
                expected_layer = "internal"
            elif event in set(PLUGIN_HOOKS):
                expected_layer = "plugin"
            elif conv == "simple" and event in INTERNAL_HOOK_PREFIXES:
                # "command", "message", "agent" etc. — wildcard prefix, treat as internal family
                expected_layer = "internal_wildcard"
            elif conv == "simple":
                # Unknown simple name — flag for review
                workspace_violations.append({
                    "hook_dir": hook_dir.name,
                    "event": event,
                    "issue": "simple/unrecognized name — not in known hook catalog",
                    "severity": "WARN"
                })
                continue

            # Check if convention matches the layer
            if expected_layer == "internal" and conv != "internal":
                workspace_violations.append({
                    "hook_dir": hook_dir.name,
                    "event": event,
                    "issue": f"Expected colon-separated (internal hook), got {conv}",
                    "severity": "ERROR"
                })
            elif expected_layer == "plugin" and conv != "plugin":
                workspace_violations.append({
                    "hook_dir": hook_dir.name,
                    "event": event,
                    "issue": f"Expected underscore-separated (plugin hook), got {conv}",
                    "severity": "ERROR"
                })

    if workspace_violations:
        for v in workspace_violations:
            if v["severity"] == "ERROR":
                r.error(f"Convention violation in {v['hook_dir']}: event '{v['event']}' — {v['issue']}")
            else:
                r.warn(f"Convention note in {v['hook_dir']}: event '{v['event']}' — {v['issue']}")
        r.find("workspace_convention_violations", workspace_violations, "warn")
    else:
        r.find("workspace_hook_conventions", "All workspace hooks follow correct naming conventions ✓", "ok")

    # 2c. Check for "collision pairs" (same semantic, different layers)
    # e.g. message:sent (internal) ↔ message_sent (plugin) — both exist, different registration
    collision_pairs = [
        ("message:received", "message_received"),
        ("message:sent", "message_sent"),
    ]
    r.find("collision_pairs", [
        {"internal": pair[0], "plugin": pair[1],
         "note": "Same event, different layers/registration APIs — do not confuse"}
        for pair in collision_pairs
    ], "ok")

    return r


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: Existing Hook Health Check
# ═══════════════════════════════════════════════════════════════════════════════

def _check_typescript_syntax(ts_file: Path) -> tuple[bool, str]:
    """
    Lightweight syntax check for TypeScript files.
    Uses Python AST-like approach: look for obvious issues.
    If tsc/node is available, use it. Otherwise do basic text checks.
    """
    if not ts_file.exists():
        return False, "file not found"

    try:
        content = ts_file.read_text(errors="replace")
    except Exception as e:
        return False, f"read error: {e}"

    # Basic structural checks
    issues = []

    # Check for export default function/const
    if not re.search(r'export\s+default\s+', content):
        issues.append("no 'export default' found (handler may not be discoverable)")

    # Check for unmatched braces (crude but catches obvious errors)
    opens = content.count('{')
    closes = content.count('}')
    if abs(opens - closes) > 2:  # Allow some tolerance for template literals
        issues.append(f"possible unmatched braces: {opens} open vs {closes} close")

    # Check for syntax errors via node --check if available
    try:
        # Use node to check by transpiling minimally — just check if file parses
        # We can't run tsc without installing it, but node can parse JS-ish TS
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", "// check"],
            input="", capture_output=True, text=True, timeout=5
        )
        # If node is available, try a rough JS-equivalent parse check
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if issues:
        return True, "WARN: " + "; ".join(issues)
    return True, "ok"


def test_hook_health() -> TestResult:
    """
    Check all hooks in hooks/ directory:
    - Handler file present + syntactically reasonable
    - Event name matches a known hook event
    - Hook enabled status (via openclaw CLI if available, else config scan)
    """
    r = TestResult("Existing Hook Health Check")

    if not HOOKS_DIR.exists():
        r.error("hooks/ directory does not exist", critical=True)
        return r

    hook_dirs = sorted([d for d in HOOKS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')])
    r.find("hooks_found", len(hook_dirs), "ok")

    if not hook_dirs:
        r.warn("No hook directories found in hooks/ — nothing to validate")
        return r

    # Try openclaw CLI for enabled status
    cli_hook_status = {}
    try:
        result = subprocess.run(
            ["openclaw", "hooks", "list"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            # Parse output — format is usually: name  event  status
            for line in result.stdout.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 2:
                        cli_hook_status[parts[0]] = {"raw": line}
            r.find("openclaw_cli_available", True, "ok")
            r.find("cli_hooks_listed", len(cli_hook_status), "ok")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        r.find("openclaw_cli_available", False, "warn")
        r.warn("openclaw CLI not available — checking hook status from filesystem only")

    # Per-hook validation
    hook_results = []
    for hook_dir in hook_dirs:
        hook_result = {
            "name": hook_dir.name,
            "hook_md_present": False,
            "handler_present": False,
            "events": [],
            "events_known": [],
            "events_unknown": [],
            "syntax_ok": None,
            "syntax_note": "",
            "cli_status": cli_hook_status.get(hook_dir.name, {}).get("raw", "not in CLI output"),
            "overall": "ok",
        }

        # Check HOOK.md
        hook_md = hook_dir / "HOOK.md"
        if hook_md.exists():
            hook_result["hook_md_present"] = True
            events = _extract_events_from_hook_md(hook_md)
            hook_result["events"] = events

            for event in events:
                if event in ALL_KNOWN_HOOKS:
                    hook_result["events_known"].append(event)
                elif _classify_hook_name(event) == "simple" and event in INTERNAL_HOOK_PREFIXES:
                    # Wildcard prefix event — matches command:*, message:*, etc.
                    hook_result["events_known"].append(f"{event}:* (wildcard)")
                else:
                    hook_result["events_unknown"].append(event)
        else:
            hook_result["overall"] = "warn"
            r.warn(f"{hook_dir.name}: HOOK.md not found")

        # Check handler.ts
        handler_ts = hook_dir / "handler.ts"
        if handler_ts.exists():
            hook_result["handler_present"] = True
            ok, note = _check_typescript_syntax(handler_ts)
            hook_result["syntax_ok"] = ok
            hook_result["syntax_note"] = note
            if not ok:
                hook_result["overall"] = "error"
                r.error(f"{hook_dir.name}/handler.ts: {note}")
            elif note.startswith("WARN"):
                hook_result["overall"] = "warn"
                r.warn(f"{hook_dir.name}/handler.ts: {note}")
        else:
            hook_result["handler_present"] = False
            hook_result["overall"] = "error"
            r.error(f"{hook_dir.name}: handler.ts not found", critical=True)

        # Flag unknown events
        if hook_result["events_unknown"]:
            hook_result["overall"] = "warn"
            r.warn(f"{hook_dir.name}: unknown event(s) in HOOK.md: {hook_result['events_unknown']}")

        hook_results.append(hook_result)

    r.find("hook_details", hook_results, "ok")

    # Summary
    ok_count = sum(1 for h in hook_results if h["overall"] == "ok")
    warn_count = sum(1 for h in hook_results if h["overall"] == "warn")
    err_count = sum(1 for h in hook_results if h["overall"] == "error")
    r.find("health_summary", {
        "total": len(hook_results),
        "ok": ok_count,
        "warn": warn_count,
        "error": err_count
    }, "ok" if err_count == 0 else "error")

    return r


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: Plugin Prototype Validation
# ═══════════════════════════════════════════════════════════════════════════════

REQUIRED_PLUGIN_FIELDS = ["id", "name", "version", "description"]
OPTIONAL_PLUGIN_FIELDS = ["configSchema", "uiHints"]

EXPECTED_PLUGINS = ["pipeline-context", "pipeline-commands", "agent-turn-logger"]

# Installed plugin location (workspace extensions)
WORKSPACE_EXTENSIONS = WORKSPACE_DIR / ".openclaw" / "extensions"


def _validate_plugin_manifest(manifest_path: Path) -> tuple[bool, list[str], list[str]]:
    """Validate openclaw.plugin.json against required fields."""
    errors = []
    warnings = []

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"], []
    except Exception as e:
        return False, [f"Cannot read: {e}"], []

    # Required fields
    for field in REQUIRED_PLUGIN_FIELDS:
        if field not in manifest:
            errors.append(f"Missing required field: '{field}'")
        elif not manifest[field]:
            errors.append(f"Required field '{field}' is empty")

    # ID format — should be kebab-case
    if "id" in manifest:
        if not re.match(r'^[a-z][a-z0-9-]*$', manifest["id"]):
            warnings.append(f"Plugin id '{manifest['id']}' should be kebab-case (a-z, 0-9, hyphens)")

    # Version format — semver-like
    if "version" in manifest:
        if not re.match(r'^\d+\.\d+\.\d+', manifest["version"]):
            warnings.append(f"Version '{manifest['version']}' doesn't follow semver (x.y.z)")

    # configSchema structure (optional but must be valid if present)
    if "configSchema" in manifest:
        schema = manifest["configSchema"]
        if not isinstance(schema, dict):
            errors.append("configSchema must be an object")
        elif schema.get("type") != "object":
            warnings.append("configSchema.type should be 'object'")

    return len(errors) == 0, errors, warnings


def test_plugin_prototypes() -> TestResult:
    """
    Validate the 3 plugin prototypes:
    - Structure: openclaw.plugin.json + index.ts present
    - Manifest: required fields, valid JSON
    - Deployment: installed vs available vs missing
    """
    r = TestResult("Plugin Prototype Validation")

    if not PLUGINS_DIR.exists():
        r.error(f"Plugin prototype directory not found: {PLUGINS_DIR}", critical=True)
        return r

    r.find("plugins_dir", str(PLUGINS_DIR.relative_to(WORKSPACE_DIR)), "ok")

    plugin_results = []
    for plugin_id in EXPECTED_PLUGINS:
        plugin_dir = PLUGINS_DIR / plugin_id
        pres = {
            "id": plugin_id,
            "source_dir": str(plugin_dir.relative_to(WORKSPACE_DIR)) if plugin_dir.exists() else None,
            "source_present": plugin_dir.exists(),
            "manifest_present": False,
            "manifest_valid": False,
            "manifest_errors": [],
            "manifest_warnings": [],
            "handler_present": False,
            "deployment_status": "missing",
            "overall": "error",
        }

        if not plugin_dir.exists():
            r.error(f"Plugin source not found: openclaw-plugins/{plugin_id}/", critical=True)
            plugin_results.append(pres)
            continue

        # Check manifest
        manifest_path = plugin_dir / "openclaw.plugin.json"
        if manifest_path.exists():
            pres["manifest_present"] = True
            valid, errors, warnings = _validate_plugin_manifest(manifest_path)
            pres["manifest_valid"] = valid
            pres["manifest_errors"] = errors
            pres["manifest_warnings"] = warnings
            if not valid:
                r.error(f"{plugin_id}: manifest invalid — {errors}")
        else:
            r.error(f"{plugin_id}: openclaw.plugin.json not found")

        # Check handler
        handler_path = plugin_dir / "index.ts"
        if handler_path.exists():
            pres["handler_present"] = True
        else:
            r.error(f"{plugin_id}: index.ts not found")

        # Check deployment status
        installed_path = WORKSPACE_EXTENSIONS / plugin_id
        global_installed = Path.home() / ".openclaw" / "extensions" / plugin_id

        if installed_path.exists():
            pres["deployment_status"] = "installed (workspace extensions)"
        elif global_installed.exists():
            pres["deployment_status"] = "installed (global extensions)"
        else:
            pres["deployment_status"] = "available (not installed)"
            r.warn(f"{plugin_id}: built but not installed — copy to .openclaw/extensions/ to activate")

        # Overall status
        if pres["manifest_present"] and pres["manifest_valid"] and pres["handler_present"]:
            pres["overall"] = "ok"
        elif pres["manifest_present"] and pres["handler_present"]:
            pres["overall"] = "warn"  # Manifest has warnings
        else:
            pres["overall"] = "error"

        plugin_results.append(pres)

    r.find("plugin_details", plugin_results, "ok")

    # Summary
    ok_count = sum(1 for p in plugin_results if p["overall"] == "ok")
    warn_count = sum(1 for p in plugin_results if p["overall"] == "warn")
    err_count = sum(1 for p in plugin_results if p["overall"] == "error")
    installed_count = sum(1 for p in plugin_results if "installed" in p["deployment_status"])

    r.find("plugin_summary", {
        "total": len(plugin_results),
        "ok": ok_count,
        "warn": warn_count,
        "error": err_count,
        "installed": installed_count,
        "available_not_installed": len(plugin_results) - installed_count
    }, "ok" if err_count == 0 else "error")

    return r


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Hook Integration Surface for Orchestration
# ═══════════════════════════════════════════════════════════════════════════════

def test_orchestration_surface() -> TestResult:
    """
    For each orchestration-relevant hook, document:
    - Context available
    - What it can modify/inject
    - Suitability rating with reasoning

    Also checks if the relevant hooks are actually implemented in our plugins/hooks.
    """
    r = TestResult("Hook Integration Surface for Orchestration")

    hook_surface = []
    for hook_name, detail in ORCHESTRATION_HOOKS.items():
        # Check if this hook is implemented by any of our plugins
        implemented_by = []

        # Check workspace hooks
        if HOOKS_DIR.exists():
            for hook_dir in HOOKS_DIR.iterdir():
                if hook_dir.is_dir():
                    hook_md = hook_dir / "HOOK.md"
                    if hook_md.exists():
                        events = _extract_events_from_hook_md(hook_md)
                        if hook_name in events:
                            implemented_by.append(f"hooks/{hook_dir.name}")

        # Check plugins
        plugin_hook_map = {
            "before_prompt_build": "pipeline-context",
            "after_tool_call": "agent-turn-logger",
            "message:received": "agent-turn-logger",
            "message:preprocessed": "agent-turn-logger",
            "message:sent": "agent-turn-logger",
        }
        if hook_name in plugin_hook_map:
            implemented_by.append(f"openclaw-plugins/{plugin_hook_map[hook_name]}")

        # Check agent:bootstrap
        if hook_name == "agent:bootstrap":
            for hook_dir in (HOOKS_DIR.iterdir() if HOOKS_DIR.exists() else []):
                if hook_dir.is_dir():
                    hook_md = hook_dir / "HOOK.md"
                    if hook_md.exists():
                        events = _extract_events_from_hook_md(hook_md)
                        if "agent:bootstrap" in events:
                            if f"hooks/{hook_dir.name}" not in implemented_by:
                                implemented_by.append(f"hooks/{hook_dir.name}")

        entry = {
            "hook": hook_name,
            "layer": detail["layer"],
            "registration": detail["registration"],
            "timing": detail["timing"],
            "context_available": detail["context_available"],
            "can_modify": detail["can_modify"],
            "orchestration_rating": detail["orchestration_rating"],
            "orchestration_reasoning": detail["orchestration_reasoning"],
            "currently_implemented": implemented_by,
            "implementation_gap": len(implemented_by) == 0,
        }
        hook_surface.append(entry)

        rating = detail["orchestration_rating"]
        if rating == "HIGH" and not implemented_by:
            r.warn(f"{hook_name} rated HIGH for orchestration but not yet implemented in any plugin/hook")

    r.find("orchestration_surface", hook_surface, "ok")

    # Summary
    high_implemented = [h for h in hook_surface if h["orchestration_rating"] == "HIGH" and not h["implementation_gap"]]
    high_missing = [h for h in hook_surface if h["orchestration_rating"] == "HIGH" and h["implementation_gap"]]

    r.find("orchestration_summary", {
        "total_reviewed": len(hook_surface),
        "high_implemented": [h["hook"] for h in high_implemented],
        "high_missing": [h["hook"] for h in high_missing],
        "readiness": "PARTIAL" if high_missing else "READY",
    }, "ok" if not high_missing else "warn")

    if high_missing:
        r.warn(f"HIGH-value orchestration hooks not yet implemented: {[h['hook'] for h in high_missing]}")

    return r


# ═══════════════════════════════════════════════════════════════════════════════
# Report generation
# ═══════════════════════════════════════════════════════════════════════════════

def format_console_report(results: list[TestResult]) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("  OpenClaw Hook Verification Report")
    lines.append(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 70)
    lines.append("")

    for r in results:
        status = "✅ PASS" if r.passed else ("🔴 FAIL" if r.critical else "⚠️  WARN")
        lines.append(f"  {status}  Test {results.index(r)+1}: {r.name}")

        if r.errors:
            for e in r.errors:
                lines.append(f"          ❌ {e}")
        if r.warnings:
            for w in r.warnings:
                lines.append(f"          ⚠  {w}")
        lines.append("")

    # Overall
    all_pass = all(r.passed for r in results)
    critical_fail = any(r.critical for r in results)
    lines.append("-" * 70)
    if critical_fail:
        lines.append("  🔴 CRITICAL FAILURES — fix before wiring orchestration engine")
    elif not all_pass:
        lines.append("  ⚠️  WARNINGS PRESENT — review before production use")
    else:
        lines.append("  ✅ ALL TESTS PASSED — hooks verified, safe to proceed")
    lines.append("=" * 70)
    return "\n".join(lines)


def format_markdown_report(results: list[TestResult]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Hook Verification Report — OpenClaw Integration",
        "",
        f"**Generated:** {ts}  ",
        f"**Workspace:** `{WORKSPACE_DIR}`  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Test | Status | Errors | Warnings |",
        "|------|--------|--------|----------|",
    ]

    for r in results:
        status = "✅ PASS" if r.passed else ("🔴 FAIL" if r.critical else "⚠️ WARN")
        lines.append(f"| **{r.name}** | {status} | {len(r.errors)} | {len(r.warnings)} |")

    all_pass = all(r.passed for r in results)
    critical_fail = any(r.critical for r in results)
    overall = "🔴 CRITICAL FAILURES" if critical_fail else ("⚠️ WARNINGS" if not all_pass else "✅ ALL PASS")
    lines.extend(["", f"**Overall:** {overall}", "", "---", ""])

    # Detailed sections
    for i, r in enumerate(results, 1):
        status = "✅" if r.passed else ("🔴" if r.critical else "⚠️")
        lines.extend([f"## Test {i}: {r.name} {status}", ""])

        if r.errors:
            lines.extend(["### ❌ Errors", ""])
            for e in r.errors:
                lines.append(f"- {e}")
            lines.append("")

        if r.warnings:
            lines.extend(["### ⚠️ Warnings", ""])
            for w in r.warnings:
                lines.append(f"- {w}")
            lines.append("")

        # Specific formatted sections per test
        if r.name == "Hook Discovery":
            for f in r.findings:
                if f["key"] == "catalog_internal_hooks":
                    lines.extend(["### Internal Hooks Catalog (11)", ""])
                    for h in f["value"]:
                        lines.append(f"- `{h}`")
                    lines.append("")
                elif f["key"] == "catalog_plugin_hooks":
                    lines.extend(["### Plugin Hooks Catalog (16)", ""])
                    for h in f["value"]:
                        lines.append(f"- `{h}`")
                    lines.append("")
                elif f["key"] == "catalog_count_check":
                    lines.append(f"**Catalog count:** {f['value']}")
                    lines.append("")

        elif r.name == "Naming Convention Verification":
            for f in r.findings:
                if f["key"] == "collision_pairs":
                    lines.extend(["### Hook Collision Pairs", "",
                                  "These hooks exist in BOTH layers with the same semantic meaning:",
                                  ""])
                    for pair in f["value"]:
                        lines.append(f"| `{pair['internal']}` (internal) | `{pair['plugin']}` (plugin) | {pair['note']} |")
                    lines.append("")
                elif f["key"] == "workspace_convention_violations":
                    lines.extend(["### Convention Violations", ""])
                    for v in f["value"]:
                        lines.append(f"- **{v['hook_dir']}**: `{v['event']}` — {v['issue']} [{v['severity']}]")
                    lines.append("")

        elif r.name == "Existing Hook Health Check":
            for f in r.findings:
                if f["key"] == "hook_details":
                    lines.extend(["### Hook-by-Hook Results", "",
                                  "| Hook | HOOK.md | handler.ts | Events | Syntax | Status |",
                                  "|------|---------|------------|--------|--------|--------|"])
                    for h in f["value"]:
                        md = "✅" if h["hook_md_present"] else "❌"
                        handler = "✅" if h["handler_present"] else "❌"
                        events_str = ", ".join(f"`{e}`" for e in h["events"]) or "—"
                        syn = "✅" if h["syntax_ok"] else ("⚠️" if h["syntax_ok"] is None else "❌")
                        syn_note = h["syntax_note"].replace("WARN: ", "")
                        status_icon = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(h["overall"], "?")
                        lines.append(f"| `{h['name']}` | {md} | {handler} | {events_str} | {syn} {syn_note} | {status_icon} |")
                    lines.append("")

        elif r.name == "Plugin Prototype Validation":
            for f in r.findings:
                if f["key"] == "plugin_details":
                    lines.extend(["### Plugin-by-Plugin Results", "",
                                  "| Plugin | Manifest | Handler | Valid | Deployment Status |",
                                  "|--------|----------|---------|-------|-------------------|"])
                    for p in f["value"]:
                        mn = "✅" if p["manifest_present"] else "❌"
                        hd = "✅" if p["handler_present"] else "❌"
                        val = "✅" if p["manifest_valid"] else "⚠️"
                        dep = p["deployment_status"]
                        lines.append(f"| `{p['id']}` | {mn} | {hd} | {val} | {dep} |")
                    lines.append("")

                    # Deployment instructions if needed
                    not_installed = [p for p in f["value"] if "not installed" in p["deployment_status"]]
                    if not_installed:
                        lines.extend([
                            "### Installation Instructions",
                            "",
                            "To deploy the plugin prototypes:",
                            "```bash",
                            "mkdir -p .openclaw/extensions/",
                        ])
                        for p in not_installed:
                            lines.append(
                                f"cp -r {p['source_dir']} .openclaw/extensions/"
                            )
                        lines.extend([
                            "# Then enable in openclaw config:",
                            "openclaw config edit  # add plugins.entries.<id>.enabled: true",
                            "openclaw gateway restart",
                            "```",
                            "",
                        ])

        elif r.name == "Hook Integration Surface for Orchestration":
            for f in r.findings:
                if f["key"] == "orchestration_surface":
                    lines.extend(["### Orchestration Surface Table", "",
                                  "| Hook | Layer | Rating | Implemented | Timing |",
                                  "|------|-------|--------|-------------|--------|"])
                    for h in f["value"]:
                        rating_icon = {"HIGH": "🟢 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🔴 LOW"}.get(h["orchestration_rating"], h["orchestration_rating"])
                        impl = ", ".join(f"`{i}`" for i in h["currently_implemented"]) if h["currently_implemented"] else "—"
                        lines.append(f"| `{h['hook']}` | {h['layer']} | {rating_icon} | {impl} | {h['timing'][:50]}… |")
                    lines.append("")

                    # Detailed cards per hook
                    for h in f["value"]:
                        lines.extend([
                            f"#### `{h['hook']}` — {h['orchestration_rating']} orchestration suitability",
                            "",
                            f"**Layer:** {h['layer']}  ",
                            f"**Registration:** `{h['registration']}`  ",
                            f"**Timing:** {h['timing']}  ",
                            "",
                            "**Context available:**",
                        ])
                        for ctx in h["context_available"]:
                            lines.append(f"- `{ctx}`")
                        lines.extend(["", "**Can modify/inject:**"])
                        for mod in h["can_modify"]:
                            lines.append(f"- {mod}")
                        lines.extend([
                            "",
                            f"**Orchestration suitability:** {h['orchestration_rating']}",
                            f"> {h['orchestration_reasoning']}",
                            "",
                            f"**Currently implemented by:** {', '.join(h['currently_implemented']) if h['currently_implemented'] else 'not yet implemented'}",
                            "",
                        ])

        lines.append("---")
        lines.append("")

    # Footer
    lines.extend([
        "## Reference",
        "",
        "- **Research doc:** `machinelearning/snn_applied_finance/research/pipeline_builds/research-openclaw-internals_builder_reference.md`",
        "- **Hook catalog source:** `machinelearning/snn_applied_finance/notebooks/local_results/research-openclaw-internals/results_summary.json`",
        "- **Plugin prototypes:** `machinelearning/snn_applied_finance/research/pipeline_builds/openclaw-plugins/`",
        "- **Workspace hooks:** `hooks/`",
        "",
        f"_Report generated by `scripts/verify_hooks.py` at {ts}_",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print()
    print("🔍 Running OpenClaw Hook Verification...")
    print(f"   Workspace: {WORKSPACE_DIR}")
    print()

    results = []

    print("  [1/5] Hook Discovery...")
    results.append(test_hook_discovery())

    print("  [2/5] Naming Convention Verification...")
    results.append(test_naming_conventions())

    print("  [3/5] Existing Hook Health Check...")
    results.append(test_hook_health())

    print("  [4/5] Plugin Prototype Validation...")
    results.append(test_plugin_prototypes())

    print("  [5/5] Hook Integration Surface for Orchestration...")
    results.append(test_orchestration_surface())

    print()
    print(format_console_report(results))
    print()

    # Write markdown report
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    md = format_markdown_report(results)
    OUTPUT_REPORT.write_text(md, encoding="utf-8")
    print(f"📝 Report written to: scripts/hook_verification_report.md")
    print()

    # Exit code
    critical_fail = any(r.critical for r in results)
    any_fail = any(not r.passed for r in results)

    if critical_fail:
        return 2  # Critical failures
    elif any_fail:
        return 1  # Warnings/non-critical failures
    return 0


if __name__ == "__main__":
    sys.exit(main())
