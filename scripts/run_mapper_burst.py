#!/usr/bin/env python3
"""Process mapper queue tasks via the map_relationships.py --apply-result interface.
Reads tasks from canvas/mapper_queue.json, processes them by reading both primitive files
and making a judgment, then applies the result."""

import json, subprocess, sys, os

WORKSPACE = "/home/ubuntu/.openclaw/workspace"
QUEUE_FILE = os.path.join(WORKSPACE, "canvas/mapper_queue.json")

def read_file_summary(path, max_lines=30):
    """Read first N lines of a file."""
    try:
        with open(path) as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line)
            return ''.join(lines)
    except Exception as e:
        return f"[Error reading: {e}]"

def main():
    with open(QUEUE_FILE) as f:
        tasks = json.load(f)
    
    print(f"Loaded {len(tasks)} tasks from queue")
    
    # Just output the task details for subagent consumption
    for i, task in enumerate(tasks):
        key_a = task['key_a']
        key_b = task['key_b']
        path_a = os.path.join(WORKSPACE, key_a + '.md')
        path_b = os.path.join(WORKSPACE, key_b + '.md')
        
        print(f"\n--- Task {i+1}/{len(tasks)} ---")
        print(f"A: {key_a}")
        print(f"B: {key_b}")
        print(f"Score: {task['score']}")

if __name__ == '__main__':
    main()
