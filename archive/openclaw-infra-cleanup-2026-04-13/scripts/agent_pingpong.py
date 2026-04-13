#!/usr/bin/env python3
"""
agent_pingpong.py — Inter-agent conversational review via render engine diffs.

Instead of fire-and-forget handoffs, keeps both agents alive and routes
diffs between them. Critic flags → architect fixes → critic re-reviews.

Usage:
  python3 scripts/agent_pingpong.py <pipeline> <stage>
  python3 scripts/agent_pingpong.py limbic-reward-snn critic_code_review

Flow:
  1. Critic reviews, writes flags to pipeline_builds/{ver}_critic_*.md
  2. This script detects the flags via render engine diff
  3. Sends flags to architect via sessions_send
  4. Architect applies fixes, commits
  5. Script detects fix diff, sends to critic
  6. Critic approves or flags again
  7. Max rounds configurable (default 3)
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE = Path(os.environ.get('BELAM_WORKSPACE', Path.home() / '.openclaw' / 'workspace'))
SOCK_PATH = WORKSPACE / '.codex_runtime' / 'render.sock'
MAX_ROUNDS = 3
POLL_INTERVAL = 5  # seconds


def uds_command(cmd: dict) -> dict:
    """Send a JSON-line command to the render engine UDS."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(SOCK_PATH))
        sock.settimeout(5)
        sock.sendall(json.dumps(cmd).encode() + b'\n')
        resp = json.loads(sock.recv(65536).decode())
        sock.close()
        return resp
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def get_diff() -> str:
    """Get current diff from render engine."""
    resp = uds_command({'cmd': 'diff'})
    if resp.get('ok') and resp.get('delta'):
        return resp['delta']
    return ''


def reset_anchor():
    """Reset render engine diff anchor."""
    uds_command({'cmd': 'anchor_reset'})


def sessions_send(session_key: str, message: str) -> bool:
    """Send a message to an agent session via openclaw CLI."""
    try:
        result = subprocess.run(
            ['openclaw', 'session', 'send', '--key', session_key, '--message', message],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def find_agent_session(agent: str) -> str:
    """Find the session key for an agent."""
    return f'agent:{agent}:main'


def run_pingpong(pipeline: str, stage: str, max_rounds: int = MAX_ROUNDS):
    """Run the ping-pong review loop."""
    
    print(f'🏓 Ping-pong review: {pipeline}/{stage}')
    print(f'   Max rounds: {max_rounds}')
    print(f'   Render engine: {SOCK_PATH}')
    print()
    
    # Verify render engine is running
    status = uds_command({'cmd': 'status'})
    if not status.get('ok'):
        print('❌ Render engine not running. Start with: python3 scripts/codex_render.py &')
        sys.exit(1)
    print(f'   Engine: {status.get("tree_size")} nodes, {status.get("sessions")} sessions')
    
    # Determine agents for this stage
    if 'critic' in stage:
        reviewer = 'critic'
        fixer = 'architect' if 'design' in stage else 'builder'
    else:
        reviewer = 'architect'
        fixer = 'builder'
    
    reviewer_key = find_agent_session(reviewer)
    fixer_key = find_agent_session(fixer)
    
    print(f'   Reviewer: {reviewer} ({reviewer_key})')
    print(f'   Fixer: {fixer} ({fixer_key})')
    print()
    
    # Initial: send review request to critic
    review_msg = (
        f'Review pipeline {pipeline} at stage {stage}.\n'
        f'Check pipeline_builds/{pipeline}_*.md for the latest artifacts.\n'
        f'For each issue found, write a FLAG or BLOCK with a clear description.\n'
        f'When done, write your verdict: APPROVED (with any remaining FLAGs) or BLOCKED.\n'
        f'This is a conversational review — the {fixer} will respond to your flags in real-time.'
    )
    
    print(f'📤 Sending review request to {reviewer}...')
    # Use sessions_send tool-style via subprocess to openclaw
    send_ok = _send_via_api(reviewer_key, review_msg)
    if not send_ok:
        print(f'⚠️  Could not send to {reviewer}. Session may need reset.')
        print(f'   Falling back to file-based review.')
        return False
    
    # Reset anchor so we only see new changes
    reset_anchor()
    
    round_num = 0
    last_actor = reviewer  # reviewer goes first
    
    while round_num < max_rounds:
        print(f'\n--- Round {round_num + 1}/{max_rounds} ---')
        print(f'⏳ Waiting for {last_actor} to write...')
        
        # Poll for changes
        max_wait = 300  # 5 minutes per round
        waited = 0
        diff = ''
        
        while waited < max_wait:
            time.sleep(POLL_INTERVAL)
            waited += POLL_INTERVAL
            
            diff = get_diff()
            if diff:
                break
            
            if waited % 30 == 0:
                print(f'   Still waiting... ({waited}s)')
        
        if not diff:
            print(f'⏰ Timeout waiting for {last_actor}. Ending review.')
            break
        
        print(f'📝 {last_actor} wrote:')
        for line in diff.split('\n')[:10]:
            print(f'   {line}')
        if len(diff.split('\n')) > 10:
            print(f'   ... ({len(diff.split(chr(10)))} lines total)')
        
        # Check if review is complete (APPROVED in diff)
        if 'APPROVED' in diff.upper() and last_actor == reviewer:
            print(f'\n✅ {reviewer} APPROVED! Review complete.')
            reset_anchor()
            return True
        
        # Route diff to the other agent
        if last_actor == reviewer:
            # Reviewer flagged something → send to fixer
            next_agent = fixer
            next_key = fixer_key
            msg = (
                f'The {reviewer} flagged issues in {pipeline}. '
                f'Here is the diff showing their feedback:\n\n{diff}\n\n'
                f'Apply fixes and commit. The {reviewer} will re-review.'
            )
        else:
            # Fixer applied changes → send back to reviewer
            next_agent = reviewer
            next_key = reviewer_key
            msg = (
                f'The {fixer} applied fixes to {pipeline}. '
                f'Here is the diff showing their changes:\n\n{diff}\n\n'
                f'Re-review the changes. APPROVE if resolved, or flag remaining issues.'
            )
            round_num += 1
        
        print(f'📤 Routing to {next_agent}...')
        send_ok = _send_via_api(next_key, msg)
        if not send_ok:
            print(f'⚠️  Could not send to {next_agent}. Ending review.')
            break
        
        reset_anchor()
        last_actor = next_agent
    
    print(f'\n🏁 Review ended after {round_num} round(s).')
    return False


def _send_via_api(session_key: str, message: str) -> bool:
    """Send message via the sessions_send mechanism.
    
    Uses openclaw's internal API by writing to a trigger file
    that the gateway picks up.
    """
    # Try direct openclaw CLI first
    try:
        result = subprocess.run(
            ['openclaw', 'send', '--session', session_key, message],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass
    
    # Fallback: write to a handoff file that orchestration picks up
    handoff_dir = WORKSPACE / 'pipelines' / 'handoffs'
    handoff_dir.mkdir(exist_ok=True)
    ts = time.strftime('%Y%m%dT%H%M%S')
    agent = session_key.split(':')[1] if ':' in session_key else 'unknown'
    handoff_file = handoff_dir / f'{ts}_pingpong_{agent}.json'
    handoff_file.write_text(json.dumps({
        'type': 'pingpong_message',
        'session_key': session_key,
        'message': message,
        'timestamp': ts,
    }, indent=2))
    print(f'   (Wrote handoff file: {handoff_file.name})')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Inter-agent ping-pong review')
    parser.add_argument('pipeline', help='Pipeline version')
    parser.add_argument('stage', nargs='?', default='critic_code_review', help='Review stage')
    parser.add_argument('--rounds', type=int, default=MAX_ROUNDS, help='Max review rounds')
    args = parser.parse_args()
    
    success = run_pingpong(args.pipeline, args.stage, args.rounds)
    sys.exit(0 if success else 1)
