#!/usr/bin/env python3
"""
Cleanup stale agent sessions — kills sessions inactive for >N hours.

Usage:
  python3 scripts/cleanup_stale_sessions.py              # Dry run (default)
  python3 scripts/cleanup_stale_sessions.py --execute     # Actually kill stale sessions
  python3 scripts/cleanup_stale_sessions.py --hours 12    # Custom staleness threshold
  python3 scripts/cleanup_stale_sessions.py --agent architect  # Only check one agent

Designed for daily cron: kills pipeline sessions that finished or stalled >24h ago.
Skips the main coordinator session and heartbeat session.
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone

DEFAULT_STALE_HOURS = 24
PROTECTED_SESSION_PATTERNS = [
    'agent:main:main',
    'agent:main:telegram:slash',
    'telegram:group:',  # Keep group chat sessions (they get reset on kickoff anyway)
]


def list_sessions(agent_id: str = None) -> list:
    """List all sessions, optionally filtered by agent."""
    params = {'limit': 100}
    if agent_id:
        params['agentId'] = agent_id
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'call', 'sessions.list',
             '--json', '--params', json.dumps(params)],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('sessions', [])
    except Exception as e:
        print(f"❌ Failed to list sessions: {e}")
    return []


def reset_session(key: str) -> bool:
    """Reset (effectively kill) a session by key."""
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'call', 'sessions.reset',
             '--json', '--params', json.dumps({'key': key})],
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False


def is_protected(key: str) -> bool:
    """Check if a session key matches a protected pattern."""
    return any(pattern in key for pattern in PROTECTED_SESSION_PATTERNS)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Cleanup stale agent sessions')
    parser.add_argument('--execute', action='store_true', help='Actually kill sessions (default: dry run)')
    parser.add_argument('--hours', type=int, default=DEFAULT_STALE_HOURS, help=f'Hours of inactivity before considered stale (default: {DEFAULT_STALE_HOURS})')
    parser.add_argument('--agent', type=str, help='Only check sessions for this agent')
    args = parser.parse_args()

    now = time.time()
    cutoff = now - (args.hours * 3600)
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)

    sessions = list_sessions(args.agent)
    if not sessions:
        print("No sessions found.")
        return

    stale = []
    active = []
    protected = []

    for s in sessions:
        key = s.get('key', '')
        updated_at = s.get('updatedAt', 0) / 1000  # ms → seconds
        total_tokens = s.get('totalTokens', 0)

        if is_protected(key):
            protected.append(s)
            continue

        if updated_at < cutoff:
            stale.append(s)
        else:
            active.append(s)

    print(f"\n{'═' * 60}")
    print(f"  Session Cleanup — threshold: {args.hours}h")
    print(f"  Cutoff: {cutoff_dt.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'═' * 60}")
    print(f"\n  Protected: {len(protected)}  Active: {len(active)}  Stale: {len(stale)}")

    if stale:
        print(f"\n  Stale sessions:")
        for s in stale:
            key = s.get('key', '')
            updated = datetime.fromtimestamp(s.get('updatedAt', 0) / 1000, tz=timezone.utc)
            tokens = s.get('totalTokens', 0)
            hours_ago = (now - s.get('updatedAt', 0) / 1000) / 3600
            print(f"    {'🗑️' if args.execute else '⚠️'}  {key}")
            print(f"       Last active: {updated.strftime('%Y-%m-%d %H:%M')} ({hours_ago:.1f}h ago), {tokens} tokens")

            if args.execute:
                if reset_session(key):
                    print(f"       ✅ Reset")
                else:
                    print(f"       ❌ Failed to reset")
    else:
        print(f"\n  ✅ No stale sessions found")

    if not args.execute and stale:
        print(f"\n  Dry run — re-run with --execute to clean up {len(stale)} stale session(s)")

    print()


if __name__ == '__main__':
    main()
