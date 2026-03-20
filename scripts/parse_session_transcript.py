#!/usr/bin/env python3
"""
parse_session_transcript.py — Parse a session JSONL into a concise readable transcript.

Deterministic, zero-token operation. All LLM judgment happens downstream.

Usage:
    python3 scripts/parse_session_transcript.py <jsonl_file> <output_file> [--instance main] [--persona architect]
"""

import json
import sys
from pathlib import Path

MAX_MSG_CHARS = 1500    # Per-message truncation
MAX_TOTAL_CHARS = 40000 # Total transcript cap (~10K tokens)


def extract_text(content):
    """Extract readable text from message content, compacting tool calls."""
    parts = []
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            t = item.get('type', '')
            if t == 'text':
                parts.append(item.get('text', ''))
            elif t == 'tool_use':
                name = item.get('name', '?')
                inp = item.get('input', {})
                if name in ('Read', 'read'):
                    parts.append(f"[Read {inp.get('file_path', inp.get('path', '?'))}]")
                elif name in ('Write', 'write'):
                    parts.append(f"[Write {inp.get('file_path', inp.get('path', '?'))}]")
                elif name in ('Edit', 'edit'):
                    parts.append(f"[Edit {inp.get('file_path', inp.get('path', '?'))}]")
                elif name == 'exec':
                    cmd = inp.get('command', '')[:150]
                    parts.append(f"[exec: {cmd}]")
                elif name == 'sessions_spawn':
                    task = inp.get('task', '')[:150]
                    label = inp.get('label', '')
                    parts.append(f"[spawn {label}: {task}]")
                elif name == 'memory_search':
                    parts.append(f"[memory_search: {inp.get('query', '')}]")
                elif name == 'message':
                    action = inp.get('action', '')
                    msg = inp.get('message', '')[:100]
                    parts.append(f"[message {action}: {msg}]")
                else:
                    parts.append(f"[{name}]")
            # Skip tool_result, thinking, etc — noise for memory extraction
    return '\n'.join(parts).strip()


def parse(jsonl_file: str, output_file: str, instance: str = 'main', persona: str = ''):
    messages = []
    session_id = ''
    session_start = ''
    session_end = ''

    with open(jsonl_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            t = obj.get('type', '')
            if t == 'session':
                session_id = obj.get('id', '')
                session_start = obj.get('timestamp', '')
            elif t == 'message':
                msg = obj.get('message', {})
                role = msg.get('role', 'unknown')
                ts = obj.get('timestamp', '')
                session_end = ts  # Track last timestamp
                
                text = extract_text(msg.get('content', ''))
                
                # Skip noise
                if not text or text in ('NO_REPLY', 'HEARTBEAT_OK'):
                    continue
                # Skip bootstrap/system boilerplate
                if role == 'user' and 'Execute your Session Startup sequence' in text:
                    messages.append({'role': role, 'text': '[Session startup prompt]', 'ts': ts})
                    continue
                
                # Truncate long messages
                if len(text) > MAX_MSG_CHARS:
                    text = text[:MAX_MSG_CHARS] + '\n[...truncated...]'
                
                messages.append({'role': role, 'text': text, 'ts': ts})

    # Enforce total size cap
    total = 0
    kept = []
    for msg in messages:
        total += len(msg['text']) + 50  # overhead per message
        if total > MAX_TOTAL_CHARS:
            kept.append({'role': 'system', 'text': f'[...{len(messages) - len(kept)} more messages trimmed...]', 'ts': ''})
            break
        kept.append(msg)

    # Count user exchanges
    user_count = sum(1 for m in messages if m['role'] == 'user')

    # Write transcript
    with open(output_file, 'w') as f:
        f.write(f"# Session Transcript\n")
        f.write(f"- **Instance:** {instance}\n")
        if persona:
            f.write(f"- **Persona:** {persona}\n")
        f.write(f"- **Session:** {session_id}\n")
        f.write(f"- **Period:** {session_start[:19]} → {session_end[:19]}\n")
        f.write(f"- **Exchanges:** {user_count} user messages, {len(messages)} total\n")
        f.write("---\n\n")

        for msg in kept:
            label = {'user': '🧑 User', 'assistant': '🤖 Assistant'}.get(msg['role'], f"[{msg['role']}]")
            ts = msg['ts'][:19] if msg['ts'] else ''
            f.write(f"### {label} {ts}\n{msg['text']}\n\n")

    print(f"{len(kept)} messages, {user_count} user exchanges, {total} chars")
    return user_count


if __name__ == '__main__':
    import argparse
    import os
    p = argparse.ArgumentParser()
    p.add_argument('jsonl_file')
    p.add_argument('output_file')
    p.add_argument('--instance', default='main')
    p.add_argument('--persona', default='')
    p.add_argument('--test', action='store_true', help='Write transcript to memory/test-extract/ instead of /tmp')
    args = p.parse_args()

    # In test mode, redirect output to memory/test-extract/transcript.md
    output_file = args.output_file
    if args.test:
        workspace = os.environ.get('WORKSPACE', str(Path.home() / '.openclaw' / 'workspace'))
        test_dir = Path(workspace) / 'memory' / 'test-extract'
        test_dir.mkdir(parents=True, exist_ok=True)
        output_file = str(test_dir / 'transcript.md')

    count = parse(args.jsonl_file, output_file, args.instance, args.persona)
    sys.exit(0)
