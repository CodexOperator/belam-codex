#!/usr/bin/env python3
"""Collect mapper subagent results and apply them via map_relationships.py --apply-result.

Usage: python3 collect_mapper_results.py <session_keys_file>
Where session_keys_file has lines: label|session_key|key_a|key_b
"""
import sys, json, subprocess, os

def main():
    if len(sys.argv) < 2:
        print("Usage: collect_mapper_results.py <manifest_file>")
        sys.exit(1)
    
    manifest_file = sys.argv[1]
    with open(manifest_file) as f:
        lines = [l.strip() for l in f if l.strip()]
    
    results = []
    for line in lines:
        label, session_key, key_a, key_b = line.split("|")
        
        # Read the result from the session's last message file
        # Sessions store in ~/.openclaw/state/sessions/
        # But we can also just parse the history from the gateway
        # For now, we'll use the result files we write
        results.append({
            "label": label,
            "session_key": session_key, 
            "key_a": key_a,
            "key_b": key_b
        })
    
    print(f"Loaded {len(results)} entries from manifest")

if __name__ == "__main__":
    main()
