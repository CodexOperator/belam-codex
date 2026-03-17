#!/usr/bin/env python3
"""
archive_session_transcript.py — Archive agent session transcripts as readable markdown.

Reads JSONL session files from ~/.openclaw/agents/{agentId}/sessions/
Formats them as readable markdown for human review and fine-tuning training data.
Saves to conversations/{version}_{stage}_{date}.md

Usage:
    python3 scripts/archive_session_transcript.py \\
        --session-key "agent:architect:telegram:group:-5243763228" \\
        --pipeline v4-analysis \\
        --stage architect_design \\
        --output-dir "SNN_research/machinelearning/snn_applied_finance/conversations/"

    python3 scripts/archive_session_transcript.py \\
        --session-key "agent:builder:telegram:group:-5243763228" \\
        --pipeline v4 --stage builder_implementation

Options:
    --session-key    Agent session key (agent:{id}:{channel}:{type}:{id})
    --pipeline       Pipeline version (e.g. v4-analysis)
    --stage          Stage name (e.g. architect_design)
    --output-dir     Directory to write transcript (default: conversations/)
    --since          Only include messages from last N hours (0 = all, default: 2)
    --agent-id       Override agent ID derived from session key
    --list-sessions  List available sessions for an agent and exit
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
AGENTS_DIR = Path(os.path.expanduser('~/.openclaw/agents'))
DEFAULT_OUTPUT_DIR = WORKSPACE / 'SNN_research' / 'machinelearning' / 'snn_applied_finance' / 'conversations'


# ---------------------------------------------------------------------------
# Session key parsing
# ---------------------------------------------------------------------------

def parse_session_key(session_key: str) -> str:
    """
    Extract agent ID from a session key.
    Format: agent:{agentId}:{channel}:{type}:{id}
    Examples:
        agent:architect:telegram:group:-5243763228  → architect
        agent:main:main                             → main
    """
    parts = session_key.split(':')
    if len(parts) >= 2 and parts[0] == 'agent':
        return parts[1]
    return session_key  # fallback


def find_agent_dir(agent_id: str) -> Path | None:
    """Find the agent's directory under ~/.openclaw/agents/"""
    # Try exact match first
    candidate = AGENTS_DIR / agent_id
    if candidate.exists():
        return candidate

    # Try case-insensitive / glob match
    for d in AGENTS_DIR.iterdir():
        if d.is_dir() and d.name.lower() == agent_id.lower():
            return d

    return None


def list_sessions(agent_id: str) -> list[Path]:
    """List all session JSONL files for an agent, sorted by modification time (newest first)."""
    agent_dir = find_agent_dir(agent_id)
    if not agent_dir:
        return []

    sessions_dir = agent_dir / 'sessions'
    if not sessions_dir.exists():
        return []

    jsonl_files = list(sessions_dir.glob('*.jsonl'))
    jsonl_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return jsonl_files


def find_recent_session(agent_id: str, since_hours: float) -> Path | None:
    """Find the most recently modified session within the time window."""
    sessions = list_sessions(agent_id)
    if not sessions:
        return None

    if since_hours <= 0:
        return sessions[0]  # Most recent

    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    for session_file in sessions:
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc)
        if mtime >= cutoff:
            return session_file

    return sessions[0]  # Fallback to most recent


# ---------------------------------------------------------------------------
# JSONL parsing
# ---------------------------------------------------------------------------

def parse_message_role(entry: dict) -> str:
    """Extract role from a JSONL entry."""
    # OpenClaw format: type=message, nested message.role
    msg = entry.get('message', {})
    if msg and 'role' in msg:
        return msg['role']
    # Flat format
    role = entry.get('role', '')
    return role or 'unknown'


def extract_content_blocks(content) -> str:
    """Recursively extract text from content (str, list of blocks, or nested)."""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                btype = block.get('type', '')
                if btype == 'text':
                    text = block.get('text', '').strip()
                    if text:
                        parts.append(text)
                elif btype == 'thinking':
                    text = block.get('thinking', '').strip()
                    if text:
                        parts.append(f'_[thinking: {text[:200]}…]_')
                elif btype == 'tool_use':
                    name = block.get('name', 'tool')
                    inp = block.get('input', {})
                    try:
                        inp_str = json.dumps(inp, ensure_ascii=False)[:300]
                    except Exception:
                        inp_str = str(inp)[:300]
                    parts.append(f'`[Tool: {name}({inp_str})]`')
                elif btype == 'tool_result':
                    result_content = block.get('content', '')
                    inner = extract_content_blocks(result_content)
                    if inner:
                        parts.append(f'`[Tool result: {inner[:300]}]`')
        return '\n'.join(parts).strip()

    return ''


def parse_message_content(entry: dict) -> str:
    """Extract human-readable content from a JSONL entry (OpenClaw JSONL format)."""
    # OpenClaw format: type=message, nested message object
    msg = entry.get('message', {})
    if msg:
        content = msg.get('content', '')
        result = extract_content_blocks(content)
        if result:
            return result

    # Flat format fallback
    content = entry.get('content', '')
    result = extract_content_blocks(content)
    return result


def parse_timestamp(entry: dict) -> str | None:
    """Extract ISO timestamp from entry."""
    for key in ('timestamp', 'created_at', 'ts', 'time'):
        val = entry.get(key)
        if val:
            try:
                if isinstance(val, (int, float)):
                    return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
                return str(val)
            except Exception:
                pass
    return None


def load_jsonl(session_file: Path, since_hours: float = 0) -> list[dict]:
    """Load and parse a JSONL session file, optionally filtering by time.

    Only returns entries of type 'message' (skips session metadata, model_change, etc.)
    """
    entries = []
    cutoff = None
    if since_hours > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)

    try:
        with open(session_file, 'r', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Only keep message entries (skip session/model metadata events)
                    entry_type = entry.get('type', '')
                    if entry_type not in ('message', ''):
                        continue
                    # Must have a message or role
                    if 'message' not in entry and 'role' not in entry and 'content' not in entry:
                        continue
                    # Apply time filter if requested
                    if cutoff:
                        ts_str = parse_timestamp(entry)
                        if ts_str:
                            try:
                                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                if ts < cutoff:
                                    continue
                            except Exception:
                                pass
                    entries.append(entry)
                except json.JSONDecodeError:
                    # Skip malformed lines silently (could be partial writes)
                    pass
    except Exception as e:
        print(f"ERROR: Could not read session file: {e}", file=sys.stderr)

    return entries


# ---------------------------------------------------------------------------
# Markdown formatting
# ---------------------------------------------------------------------------

ROLE_LABELS = {
    'user': '👤 **User**',
    'assistant': '🤖 **Assistant**',
    'system': '⚙️ **System**',
    'tool': '🔧 **Tool**',
    'function': '🔧 **Function**',
}


def format_transcript_as_markdown(
    entries: list[dict],
    agent_id: str,
    pipeline: str,
    stage: str,
    session_file: Path,
) -> str:
    """Format JSONL entries as a readable markdown transcript."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    lines = [
        f"# Session Transcript: {agent_id} | {stage}",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Agent | `{agent_id}` |",
        f"| Pipeline | `{pipeline}` |",
        f"| Stage | `{stage}` |",
        f"| Session File | `{session_file.name}` |",
        f"| Session Modified | {mtime} |",
        f"| Exported | {now} |",
        f"| Messages | {len(entries)} |",
        f"",
        f"---",
        f"",
        f"## Transcript",
        f"",
    ]

    for i, entry in enumerate(entries, 1):
        role = parse_message_role(entry)
        content = parse_message_content(entry)
        ts = parse_timestamp(entry)

        role_label = ROLE_LABELS.get(role, f'**{role.title()}**')
        ts_str = f' _{ts}_' if ts else ''

        lines.append(f"### Message {i} — {role_label}{ts_str}")
        lines.append("")

        if content:
            # Indent content to keep it inside the message block
            lines.append(content)
        else:
            lines.append("_(empty)_")

        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(f"_End of transcript — {len(entries)} messages from `{agent_id}` session_")
    lines.append(f"")
    lines.append(f"> **Training data note:** This transcript captures the {agent_id} agent completing the `{stage}` stage")
    lines.append(f"> for pipeline `{pipeline}`. Useful for fine-tuning agent behavior in pipeline coordination tasks.")

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description='Archive agent session transcripts as readable markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--session-key', required=False,
                        help='Agent session key (e.g. agent:architect:telegram:group:-5243763228)')
    parser.add_argument('--pipeline', required=False, help='Pipeline version (e.g. v4-analysis)')
    parser.add_argument('--stage', required=False, help='Stage name (e.g. architect_design)')
    parser.add_argument('--output-dir', default=str(DEFAULT_OUTPUT_DIR),
                        help=f'Output directory (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--since', type=float, default=2.0,
                        help='Only include messages from last N hours (0 = all, default: 2)')
    parser.add_argument('--agent-id', help='Override agent ID (derived from session key by default)')
    parser.add_argument('--list-sessions', action='store_true',
                        help='List available sessions for the agent and exit')
    return parser.parse_args()


def main():
    args = parse_args()

    # Determine agent ID
    agent_id = args.agent_id
    if not agent_id and args.session_key:
        agent_id = parse_session_key(args.session_key)
    if not agent_id:
        print("ERROR: --session-key or --agent-id is required", file=sys.stderr)
        sys.exit(1)

    # List sessions mode
    if args.list_sessions:
        sessions = list_sessions(agent_id)
        if not sessions:
            print(f"No sessions found for agent '{agent_id}'")
            print(f"Looked in: {AGENTS_DIR / agent_id / 'sessions'}")
            sys.exit(0)
        print(f"Sessions for agent '{agent_id}':")
        for s in sessions:
            mtime = datetime.fromtimestamp(s.stat().st_mtime, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            size_kb = s.stat().st_size / 1024
            print(f"  {s.name}  ({size_kb:.1f} KB)  modified: {mtime}")
        sys.exit(0)

    # Find session file
    session_file = find_recent_session(agent_id, args.since)
    if not session_file:
        agent_dir = find_agent_dir(agent_id)
        if not agent_dir:
            print(f"ERROR: Agent directory not found for '{agent_id}'", file=sys.stderr)
            print(f"  Looked in: {AGENTS_DIR}", file=sys.stderr)
            available = [d.name for d in AGENTS_DIR.iterdir() if d.is_dir()] if AGENTS_DIR.exists() else []
            if available:
                print(f"  Available agents: {available}", file=sys.stderr)
        else:
            print(f"ERROR: No session files found for agent '{agent_id}' within {args.since}h", file=sys.stderr)
            print(f"  Sessions dir: {agent_dir / 'sessions'}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading session: {session_file}", file=sys.stderr)

    # Load entries
    entries = load_jsonl(session_file, since_hours=args.since)
    if not entries:
        print(f"WARNING: No entries found in session (since={args.since}h)", file=sys.stderr)
        # Still write an empty transcript
    print(f"Loaded {len(entries)} entries", file=sys.stderr)

    # Format as markdown
    pipeline = args.pipeline or 'unknown'
    stage = args.stage or 'unknown'
    markdown = format_transcript_as_markdown(entries, agent_id, pipeline, stage, session_file)

    # Determine output path
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = WORKSPACE / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')
    filename = f'{pipeline}_{stage}_{agent_id}_{date_str}.md'
    output_path = output_dir / filename

    output_path.write_text(markdown, encoding='utf-8')
    print(f"Transcript archived: {output_path}", file=sys.stderr)
    print(str(output_path))  # stdout: the path (for scripting)


if __name__ == '__main__':
    main()
