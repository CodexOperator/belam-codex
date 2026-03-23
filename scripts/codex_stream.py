#!/usr/bin/env python3
"""
codex_stream.py — Live UDS diff stream from the render engine.

Connects to the render engine's Unix Domain Socket and prints diffs as they
arrive in real-time. Can filter by pipeline or agent name.

Usage:
  python3 codex_stream.py                          # all diffs
  python3 codex_stream.py --agent architect         # diffs from architect only
  python3 codex_stream.py --pipeline validate-scheme-b  # diffs related to pipeline
  python3 codex_stream.py --content                 # include file content (F-labels)

For tmux multi-pane monitoring, see: R monitor <pipeline>
"""

import argparse
import json
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SOCKET_PATH = Path.home() / '.openclaw' / 'workspace' / '.codex_runtime' / 'render.sock'


def uds_send(sock: socket.socket, msg: dict) -> dict:
    """Send a JSON-line command and read the response."""
    sock.sendall((json.dumps(msg) + '\n').encode('utf-8'))
    buf = b''
    while b'\n' not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("Render engine closed connection")
        buf += chunk
    line, remainder = buf.split(b'\n', 1)
    return json.loads(line), remainder


def format_diff(diff: dict, include_content: bool = False) -> str:
    """Format a single diff entry for terminal display."""
    ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
    action = diff.get('action', '?')
    coord = diff.get('coord', '?')
    label = diff.get('label', '?')
    slug = diff.get('slug', '')

    # Color codes
    colors = {
        'CREATE': '\033[32m+\033[0m',  # green
        'MODIFY': '\033[33m~\033[0m',  # yellow
        'DELETE': '\033[31m-\033[0m',  # red
    }
    icon = colors.get(action, ' ')

    line = f"  {ts} {icon} [{label}] {coord} {slug}"

    if include_content and 'content' in diff:
        content = diff['content']
        if content:
            # Indent content preview (first 3 lines, max 120 chars each)
            preview_lines = content.strip().split('\n')[:3]
            for pl in preview_lines:
                line += f"\n         │ {pl[:120]}"
            if len(content.strip().split('\n')) > 3:
                line += "\n         │ ..."

    return line


def main():
    parser = argparse.ArgumentParser(description='Live UDS diff stream from render engine')
    parser.add_argument('--agent', '-a', help='Filter diffs by agent name')
    parser.add_argument('--pipeline', '-p', help='Filter diffs by pipeline name (matches coord prefixes)')
    parser.add_argument('--content', '-c', action='store_true', help='Include file content (F-labels)')
    parser.add_argument('--name', '-n', default='monitor', help='Session name for attach (default: monitor)')
    args = parser.parse_args()

    if not SOCKET_PATH.exists():
        print(f"❌ Render engine not running (no socket at {SOCKET_PATH})")
        print("   Start with: R up")
        sys.exit(1)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(str(SOCKET_PATH))
    except ConnectionRefusedError:
        print("❌ Render engine socket exists but connection refused")
        sys.exit(1)

    # Attach as observer
    resp, remainder = uds_send(sock, {
        'command': 'attach',
        'agent': f'monitor-{args.name}',
        'pipeline': args.pipeline or '',
        'stage': 'observe',
        'role': 'observer',
    })

    if not resp.get('ok'):
        print(f"❌ Attach failed: {resp}")
        sys.exit(1)

    tree_size = resp.get('tree_size', 0)
    session_id = resp.get('session_id', '?')
    print(f"🔮 Connected to render engine (session: {session_id}, tree: {tree_size} nodes)")
    if args.pipeline:
        print(f"   Filtering: pipeline={args.pipeline}")
    if args.agent:
        print(f"   Filtering: agent={args.agent}")
    print(f"   Content: {'on' if args.content else 'off'}")
    print(f"   Press Ctrl+C to stop\n")
    print(f"{'─' * 72}")

    # Process push notifications as they arrive
    buf = remainder  # may have leftover from attach response
    try:
        while True:
            try:
                sock.settimeout(1.0)
                chunk = sock.recv(8192)
                if not chunk:
                    print("\n⚠️  Render engine disconnected")
                    break
                buf += chunk
            except socket.timeout:
                continue

            # Process all complete JSON lines in buffer
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Handle different notification types
                notify_type = msg.get('type', msg.get('command', ''))

                if notify_type == 'diff_update':
                    diffs = msg.get('diffs', [])
                    for d in diffs:
                        # Agent filter
                        if args.agent:
                            agent = d.get('agent', d.get('source', ''))
                            if args.agent.lower() not in str(agent).lower():
                                continue
                        # Pipeline filter (match on coord prefix or slug)
                        if args.pipeline:
                            coord = d.get('coord', '')
                            slug = d.get('slug', '')
                            if args.pipeline.lower() not in f"{coord} {slug}".lower():
                                continue
                        print(format_diff(d, include_content=args.content))

                elif notify_type == 'session_joined':
                    agent = msg.get('agent', '?')
                    print(f"  {'─' * 40}")
                    print(f"  👤 Agent joined: {agent}")
                    print(f"  {'─' * 40}")

                elif notify_type == 'session_left':
                    agent = msg.get('agent', '?')
                    print(f"  {'─' * 40}")
                    print(f"  👋 Agent left: {agent}")
                    print(f"  {'─' * 40}")

                elif notify_type == 'heartbeat':
                    # Silent keepalive
                    pass

                else:
                    # Unknown message — show raw for debugging
                    ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
                    print(f"  {ts} ? {json.dumps(msg)[:100]}")

    except KeyboardInterrupt:
        print(f"\n{'─' * 72}")
        print("🔮 Stream ended")
    finally:
        try:
            sock.sendall((json.dumps({'command': 'detach'}) + '\n').encode('utf-8'))
        except Exception:
            pass
        sock.close()


if __name__ == '__main__':
    main()
