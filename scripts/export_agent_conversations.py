#!/usr/bin/env python3
"""
Export agent conversation transcripts to readable text logs.
Reads JSONL session files from ~/.openclaw/agents/*/sessions/
Outputs readable markdown logs to the conversations directory.

Usage:
    python3 export_agent_conversations.py [--output-dir DIR] [--agents AGENT1,AGENT2,...] [--since HOURS]
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta


def parse_args():
    parser = argparse.ArgumentParser(description="Export agent conversation transcripts")
    parser.add_argument(
        "--output-dir",
        default=os.path.expanduser("~/.openclaw/workspace/SNN_research/machinelearning/snn_applied_finance/conversations"),
        help="Output directory for conversation logs"
    )
    parser.add_argument(
        "--agents",
        default="architect,critic,builder",
        help="Comma-separated list of agent IDs to export"
    )
    parser.add_argument(
        "--since",
        type=float,
        default=0,
        help="Only export sessions modified within the last N hours (0 = all)"
    )
    parser.add_argument(
        "--state-dir",
        default=os.path.expanduser("~/.openclaw/agents"),
        help="OpenClaw agents state directory"
    )
    return parser.parse_args()


def extract_text_content(content):
    """Extract readable text from message content (string or structured)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                item_type = item.get("type", "")
                if item_type == "text":
                    parts.append(item.get("text", ""))
                elif item_type == "thinking":
                    # Include thinking but marked
                    thinking = item.get("thinking", "")
                    if thinking:
                        preview = thinking[:300]
                        if len(thinking) > 300:
                            preview += "..."
                        parts.append(f"*[thinking: {preview}]*")
                elif item_type == "toolCall":
                    name = item.get("name", "unknown")
                    args = item.get("arguments", {})
                    if name == "sessions_send":
                        target = args.get("sessionKey", args.get("label", "?"))
                        msg = args.get("message", "")
                        parts.append(f"**→ sessions_send to `{target}`:**\n\n{msg}")
                    elif name in ("read", "Read"):
                        path = args.get("file_path", args.get("path", "?"))
                        parts.append(f"*[📖 read {path}]*")
                    elif name in ("write", "Write"):
                        path = args.get("file_path", args.get("path", "?"))
                        parts.append(f"*[✏️ write {path}]*")
                    elif name == "exec":
                        cmd = (args.get("command", ""))[:150]
                        parts.append(f"*[⚡ exec: `{cmd}`]*")
                    elif name == "message":
                        msg = args.get("message", "")[:300]
                        parts.append(f"**→ message to group:**\n\n{msg}")
                    else:
                        parts.append(f"*[🔧 {name}]*")
                elif item_type == "toolResult":
                    # Skip verbose tool results
                    pass
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(p for p in parts if p)
    return str(content)


def format_timestamp(ts_ms):
    """Format millisecond timestamp to readable datetime."""
    if not ts_ms:
        return "unknown time"
    try:
        if isinstance(ts_ms, str):
            # Try ISO format
            return ts_ms[:19].replace("T", " ") + " UTC"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, OSError, TypeError):
        return str(ts_ms)


def process_session(jsonl_path, agent_id):
    """Read a JSONL session file and return structured messages."""
    messages = []
    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    
                    # Handle wrapped message format (type: "message")
                    if entry.get("type") == "message":
                        msg = entry.get("message", {})
                        timestamp = entry.get("timestamp", msg.get("timestamp"))
                    elif entry.get("role"):
                        # Direct message format
                        msg = entry
                        timestamp = entry.get("timestamp")
                    else:
                        continue
                    
                    role = msg.get("role", "unknown")
                    content = extract_text_content(msg.get("content", ""))
                    
                    # Skip empty content and pure tool results
                    if not content or not content.strip():
                        continue
                    if role == "toolResult":
                        continue
                    if role == "system":
                        continue
                    
                    # Determine speaker
                    if role == "user":
                        prov = msg.get("provenance", {})
                        if prov.get("kind") == "inter_session":
                            source = prov.get("sourceAgentId", prov.get("sourceAgent", "agent"))
                            speaker = f"📨 From {source}"
                        else:
                            speaker = "👤 Shael"
                    elif role == "assistant":
                        speaker = f"🤖 {agent_id.capitalize()}"
                    else:
                        speaker = role
                    
                    messages.append({
                        "speaker": speaker,
                        "content": content,
                        "timestamp": timestamp,
                        "time_str": format_timestamp(timestamp),
                    })
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return messages


def export_session(messages, agent_id, session_id, output_dir):
    """Write messages to a readable markdown file."""
    if not messages:
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine date range
    timestamps = [m["timestamp"] for m in messages if m.get("timestamp")]
    if timestamps:
        start = format_timestamp(min(timestamps))
        end = format_timestamp(max(timestamps))
        first_ts = min(timestamps)
        try:
            if isinstance(first_ts, str):
                date_str = first_ts[:10]
            else:
                date_str = datetime.fromtimestamp(first_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        start = end = "unknown"
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    filename = f"{date_str}_{agent_id}_{session_id[:8]}.md"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w") as f:
        f.write(f"# Conversation Log: {agent_id.capitalize()}\n\n")
        f.write(f"- **Agent:** {agent_id}\n")
        f.write(f"- **Session:** `{session_id}`\n")
        f.write(f"- **Period:** {start} → {end}\n")
        f.write(f"- **Messages:** {len(messages)}\n\n")
        f.write(f"---\n\n")
        
        for msg in messages:
            f.write(f"### {msg['speaker']} — {msg['time_str']}\n\n")
            f.write(f"{msg['content']}\n\n")
            f.write(f"---\n\n")
    
    return filepath


def main():
    args = parse_args()
    agents = [a.strip() for a in args.agents.split(",")]
    cutoff = None
    if args.since > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.since)
    
    exported = []
    print(f"📋 Exporting conversations for: {', '.join(agents)}")
    
    for agent_id in agents:
        sessions_dir = Path(args.state_dir) / agent_id / "sessions"
        if not sessions_dir.exists():
            print(f"  ⏭️  No sessions dir for {agent_id}")
            continue
        
        for jsonl_file in sorted(sessions_dir.glob("*.jsonl")):
            # Check modification time if --since is set
            if cutoff:
                mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    continue
            
            session_id = jsonl_file.stem
            messages = process_session(jsonl_file, agent_id)
            
            if messages:
                filepath = export_session(messages, agent_id, session_id, args.output_dir)
                if filepath:
                    exported.append(filepath)
                    print(f"  ✅ {agent_id}/{session_id[:8]}: {len(messages)} messages → {os.path.basename(filepath)}")
            else:
                print(f"  ⏭️  {agent_id}/{session_id[:8]}: no exportable messages")
    
    if exported:
        print(f"\n📁 Exported {len(exported)} conversation(s) to {args.output_dir}/")
    else:
        print("\n⚠️  No conversations to export.")


if __name__ == "__main__":
    main()
