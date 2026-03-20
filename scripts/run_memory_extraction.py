#!/usr/bin/env python3
"""
run_memory_extraction.py — Orchestrator-side memory extraction for sub-agent sessions.

Called by pipeline_orchestrate.py at handoff time to extract memories from
sub-agent (architect/critic/builder) sessions.

For main instance: the bootstrap hook + agent-side sessions_spawn handles it.
For sub-agents: this script is called at handoff, reads the agent's latest
session, parses it, and either:
  a) Calls openclaw agent on a non-colliding agent for extraction, or
  b) Outputs the prompt for the orchestrator to pass to sessions_spawn

Usage:
    python3 scripts/run_memory_extraction.py \
        --instance architect \
        --persona architect \
        --prompt-only          # Just output the extraction prompt (for sessions_spawn)
    
    python3 scripts/run_memory_extraction.py \
        --instance builder \
        --session-file /path/to/session.jsonl \
        --spawn                # Spawn via openclaw agent (non-main agent)
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
SCRIPTS = WORKSPACE / 'scripts'


def update_tracker(instance: str, session_id: str, status: str, details: str = ''):
    """Update the extraction tracker primitive."""
    tracker_file = WORKSPACE / 'memory' / 'extraction_tracker.md'
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    content = f"""---
type: tracker
target: memory-extraction
instance: {instance}
session: {session_id}
status: {status}
updated: {now}
---

# Memory Extraction: {instance}

**Status:** {status}
**Session:** {session_id}
**Updated:** {now}
{f'**Details:** {details}' if details else ''}
"""
    tracker_file.write_text(content)


def run_extraction_script(instance, session_file=None, persona=None):
    """Run the bash parser and return parsed info."""
    cmd = ['bash', str(SCRIPTS / 'extract_session_memory.sh'), '--instance', instance]
    if session_file:
        cmd += ['--session-file', session_file]
    if persona:
        cmd += ['--persona', persona]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=str(WORKSPACE))
    
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        return None
    
    # Parse output
    info = {}
    for line in result.stdout.strip().split('\n'):
        if '=' in line:
            key, val = line.split('=', 1)
            info[key] = val
    return info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', default='main')
    parser.add_argument('--session-file', default=None)
    parser.add_argument('--persona', default=None)
    parser.add_argument('--prompt-only', action='store_true',
                       help='Output extraction prompt to stdout (for sessions_spawn)')
    parser.add_argument('--spawn', action='store_true',
                       help='Spawn extraction via openclaw agent (use for non-main agents)')
    args = parser.parse_args()
    
    info = run_extraction_script(args.instance, args.session_file, args.persona)
    if not info or 'PROMPT_FILE' not in info:
        print("No session to extract", file=sys.stderr)
        sys.exit(1)
    
    prompt_file = info['PROMPT_FILE']
    session_id = info.get('SESSION_ID', 'unknown')
    exchange_count = int(info.get('EXCHANGE_COUNT', '0'))
    
    prompt = Path(prompt_file).read_text()
    
    if args.prompt_only:
        # Just output the prompt — caller handles spawning
        print(prompt)
        sys.exit(0)
    
    if args.spawn:
        # Spawn via openclaw agent using code-tutor (least likely to collide)
        update_tracker(args.instance, session_id, 'running')
        
        try:
            result = subprocess.run(
                ['openclaw', 'agent',
                 '--agent', 'code-tutor',
                 '--session-id', f'mem-extract-{session_id[:8]}',
                 '--message', prompt,
                 '--timeout', '300'],
                capture_output=True, text=True, timeout=310,
                cwd=str(WORKSPACE),
            )
            
            if result.returncode == 0:
                update_tracker(args.instance, session_id, 'complete',
                              f'{exchange_count} exchanges processed')
            else:
                update_tracker(args.instance, session_id, 'error',
                              result.stderr[:200])
        except subprocess.TimeoutExpired:
            update_tracker(args.instance, session_id, 'timeout', '5min limit')
        except Exception as e:
            update_tracker(args.instance, session_id, 'error', str(e)[:200])
    else:
        # Default: just print info
        print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
