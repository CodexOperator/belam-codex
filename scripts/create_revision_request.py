#!/usr/bin/env python3
"""
Create a revision request file for pipeline_autorun.py to pick up.

Usage:
    python3 scripts/create_revision_request.py <version> [options]
    R queue-revision <version> [options]

Options:
    --context-file <path>   Path to findings doc (relative to machinelearning/snn_applied_finance/ or workspace)
    --section "## Header"   Section header to extract from context file
    --priority <level>      critical|high|normal|low (default: high)
    --body "text"           Additional context text for the revision body
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
BUILDS_DIR = WORKSPACE / 'pipeline_builds'
RESEARCH_BUILDS_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
PIPELINES_DIR = WORKSPACE / 'pipelines'


def fuzzy_match_version(partial: str) -> str | None:
    """Match a partial version name to a pipeline file."""
    candidates = [f.stem for f in PIPELINES_DIR.glob('*.md')]
    # Exact match
    if partial in candidates:
        return partial
    # Prefix match
    matches = [c for c in candidates if c.startswith(partial)]
    if len(matches) == 1:
        return matches[0]
    # Substring match
    matches = [c for c in candidates if partial in c]
    if len(matches) == 1:
        return matches[0]
    if matches:
        print(f"Ambiguous match for '{partial}': {', '.join(matches)}")
        return None
    print(f"No pipeline found matching '{partial}'")
    return None


def main():
    parser = argparse.ArgumentParser(description='Create a revision request for autorun pickup')
    parser.add_argument('version', help='Pipeline version (supports fuzzy match)')
    parser.add_argument('--context-file', help='Path to findings/context doc')
    parser.add_argument('--section', help='Section header to extract from context file')
    parser.add_argument('--priority', default='high', choices=['critical', 'high', 'normal', 'low'])
    parser.add_argument('--body', help='Additional context text')
    args = parser.parse_args()

    version = fuzzy_match_version(args.version)
    if not version:
        sys.exit(1)

    # Build frontmatter
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    lines = [
        '---',
        f'version: {version}',
    ]
    if args.context_file:
        lines.append(f'context_file: {args.context_file}')
    if args.section:
        lines.append(f'section: "{args.section}"')
    lines.append(f'priority: {args.priority}')
    lines.append(f'created: {now}')
    lines.append('---')

    if args.body:
        lines.append('')
        lines.append(args.body)

    lines.append('')

    output = BUILDS_DIR / f'{version}_revision_request.md'
    output.write_text('\n'.join(lines))
    print(f"✅ Revision request created: {output.name}")
    print(f"   Version:  {version}")
    print(f"   Priority: {args.priority}")
    if args.context_file:
        print(f"   Context:  {args.context_file}")
        if args.section:
            print(f"   Section:  {args.section}")
    print(f"\n   Will be picked up by next 'R autorun' or heartbeat cycle.")


if __name__ == '__main__':
    main()
