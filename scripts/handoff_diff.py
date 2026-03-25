#!/usr/bin/env python3
"""
handoff_diff.py — Git-diff context for pipeline stage handoffs.

Records git HEAD snapshots at handoff boundaries and generates scoped
diffs for agents resuming work on a pipeline.

Two main functions:
  snapshot_handoff_commits(version, stage, agent)
    — Records current HEAD for workspace + machinelearning repos into pipeline state JSON.
    — Called when a stage completes (before the next agent is dispatched).

  build_handoff_diff(version, agent)
    — Looks up the last snapshot for this specific agent on this pipeline.
    — Generates a scoped git diff (stat + hunks if small enough).
    — Returns a formatted markdown string, or '' if no prior snapshot.

Design notes:
  - Diffs are scoped to pipeline-relevant paths only (not the whole repo).
  - Truncation: --stat always included; full hunks only if <3000 chars.
  - .ipynb files are --stat only (diffs are noisy).
  - Graceful fallback on missing repos, first touch, dirty state.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
BUILDS_DIR = WORKSPACE / 'pipeline_builds'
ML_DIR = WORKSPACE / 'machinelearning'

# Maximum chars for full diff hunks before falling back to --stat only
MAX_HUNK_CHARS = 3000


def _get_git_head(repo_path: Path) -> str | None:
    """Get the current git HEAD commit hash for a repo. Returns None on failure."""
    if not repo_path.exists() or not (repo_path / '.git').exists():
        return None
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, timeout=5,
            cwd=str(repo_path),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _load_state(version: str) -> dict:
    """Load pipeline state JSON."""
    # Check subdirectory first, then flat
    for path in (
        BUILDS_DIR / version / '_state.json',
        BUILDS_DIR / f'{version}_state.json',
    ):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def _save_state(version: str, state: dict):
    """Save pipeline state JSON (both flat and subdirectory if exists)."""
    BUILDS_DIR.mkdir(parents=True, exist_ok=True)
    content = json.dumps(state, indent=2, default=str)
    # Always write flat
    flat = BUILDS_DIR / f'{version}_state.json'
    flat.write_text(content, encoding='utf-8')
    # Also write subdirectory if it exists
    sub_dir = BUILDS_DIR / version
    if sub_dir.is_dir():
        (sub_dir / '_state.json').write_text(content, encoding='utf-8')


def _relevant_paths(version: str, repo: str) -> list[str]:
    """Return the pipeline-relevant path globs for a given repo.

    These scope the git diff so we only show changes relevant to this pipeline.
    """
    if repo == 'workspace':
        return [
            f'pipeline_builds/{version}*',
            f'pipeline_builds/{version}/',
            f'tasks/{version}.md',
            f'tasks/{version}/',
            f'pipelines/{version}.md',
            f'pipelines/{version}/',
            f'scripts/handoff_diff.py',
            f'scripts/pipeline_orchestrate.py',
            f'scripts/orchestration_engine.py',
        ]
    elif repo == 'machinelearning':
        return [
            f'snn_applied_finance/research/pipeline_builds/{version}*',
            f'snn_applied_finance/research/pipeline_builds/{version}/',
            f'snn_applied_finance/notebooks/*{version}*',
        ]
    return []


def _run_git_diff(repo_path: Path, old_hash: str, paths: list[str],
                   stat_only: bool = False) -> str:
    """Run git diff between old_hash and HEAD, scoped to paths.

    Returns the diff output string, or '' on failure.
    """
    if not repo_path.exists():
        return ''

    cmd = ['git', 'diff']
    if stat_only:
        cmd.append('--stat')
    cmd.extend([old_hash, 'HEAD', '--'])
    cmd.extend(paths)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            cwd=str(repo_path),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ''


def _run_git_stat(repo_path: Path, old_hash: str, paths: list[str]) -> str:
    """Run git diff --stat between old_hash and HEAD."""
    return _run_git_diff(repo_path, old_hash, paths, stat_only=True)


def _has_ipynb(diff_text: str) -> bool:
    """Check if diff output contains .ipynb changes."""
    return '.ipynb' in diff_text


def snapshot_handoff_commits(version: str, stage: str, agent: str) -> dict:
    """Record current git HEAD for workspace + machinelearning repos.

    Appends a snapshot entry to `handoff_snapshots` in the pipeline state JSON.
    Returns the snapshot dict that was recorded.
    """
    state = _load_state(version)

    workspace_head = _get_git_head(WORKSPACE)
    ml_head = _get_git_head(ML_DIR)

    snapshot = {
        'stage': stage,
        'agent': agent,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'commits': {},
    }

    if workspace_head:
        snapshot['commits']['workspace'] = workspace_head
    if ml_head:
        snapshot['commits']['machinelearning'] = ml_head

    if not snapshot['commits']:
        # No repos available — still record the snapshot for bookkeeping
        snapshot['commits']['_note'] = 'no git repos found'

    snapshots = state.setdefault('handoff_snapshots', [])
    snapshots.append(snapshot)
    state['handoff_snapshots'] = snapshots

    _save_state(version, state)
    return snapshot


def _find_last_snapshot_for_agent(version: str, agent: str) -> dict | None:
    """Find the most recent handoff snapshot for a specific agent.

    Returns the snapshot dict, or None if this agent has no prior snapshots.
    """
    state = _load_state(version)
    snapshots = state.get('handoff_snapshots', [])

    # Walk backwards to find the last snapshot from this agent
    for snap in reversed(snapshots):
        if snap.get('agent') == agent:
            return snap

    return None


def build_handoff_diff(version: str, agent: str) -> str:
    """Generate a scoped git diff section for a handoff message.

    Looks up the last snapshot for this specific agent on this pipeline,
    then runs git diff from that snapshot to current HEAD.

    Returns a formatted markdown string ready to embed in a handoff message,
    or '' if no prior snapshot exists (first touch).
    """
    prior = _find_last_snapshot_for_agent(version, agent)
    if not prior:
        return ''  # First touch — no diff available

    prior_stage = prior.get('stage', '?')
    commits = prior.get('commits', {})

    sections = []

    # Workspace diff
    ws_hash = commits.get('workspace')
    if ws_hash:
        current_ws = _get_git_head(WORKSPACE)
        if current_ws and current_ws != ws_hash:
            paths = _relevant_paths(version, 'workspace')
            stat = _run_git_stat(WORKSPACE, ws_hash, paths)
            if stat:
                section = f'### Workspace\n```\n{stat}\n```'

                # Try full hunks if small enough
                full_diff = _run_git_diff(WORKSPACE, ws_hash, paths)
                if full_diff and len(full_diff) <= MAX_HUNK_CHARS:
                    # Filter out .ipynb hunks (noisy)
                    if not _has_ipynb(full_diff):
                        section = f'### Workspace\n```diff\n{full_diff}\n```'
                    else:
                        section += '\n_(notebook diffs omitted — read the files directly)_'
                elif full_diff and len(full_diff) > MAX_HUNK_CHARS:
                    section += f'\n_(full diff is {len(full_diff)} chars — read the files directly)_'

                sections.append(section)
        elif current_ws and current_ws == ws_hash:
            pass  # No changes in workspace

    # Machinelearning diff
    ml_hash = commits.get('machinelearning')
    if ml_hash:
        current_ml = _get_git_head(ML_DIR)
        if current_ml and current_ml != ml_hash:
            paths = _relevant_paths(version, 'machinelearning')
            stat = _run_git_stat(ML_DIR, ml_hash, paths)
            if stat:
                section = f'### Research\n```\n{stat}\n```'

                full_diff = _run_git_diff(ML_DIR, ml_hash, paths)
                if full_diff and len(full_diff) <= MAX_HUNK_CHARS:
                    if not _has_ipynb(full_diff):
                        section = f'### Research\n```diff\n{full_diff}\n```'
                    else:
                        section += '\n_(notebook diffs omitted — read the files directly)_'
                elif full_diff and len(full_diff) > MAX_HUNK_CHARS:
                    section += f'\n_(full diff is {len(full_diff)} chars — read the files directly)_'

                sections.append(section)

    if not sections:
        return ''  # No relevant changes since last snapshot

    # Assemble the diff block
    header = f'## Changes Since Your Last Session ({prior_stage} → now)\n'
    return header + '\n\n'.join(sections)


# ─── CLI for testing ────────────────────────────────────────────────────────────

def main():
    """CLI for manual testing/debugging."""
    if len(sys.argv) < 3:
        print("Usage:")
        print("  handoff_diff.py snapshot <version> <stage> <agent>")
        print("  handoff_diff.py diff <version> <agent>")
        print("  handoff_diff.py show <version>")
        sys.exit(1)

    cmd = sys.argv[1]
    version = sys.argv[2]

    if cmd == 'snapshot':
        stage = sys.argv[3] if len(sys.argv) > 3 else 'test_stage'
        agent = sys.argv[4] if len(sys.argv) > 4 else 'test_agent'
        snap = snapshot_handoff_commits(version, stage, agent)
        print(f"Snapshot recorded: {json.dumps(snap, indent=2)}")

    elif cmd == 'diff':
        agent = sys.argv[3] if len(sys.argv) > 3 else 'test_agent'
        diff_text = build_handoff_diff(version, agent)
        if diff_text:
            print(diff_text)
        else:
            print("(no diff available — first touch or no changes)")

    elif cmd == 'show':
        state = _load_state(version)
        snapshots = state.get('handoff_snapshots', [])
        print(f"Handoff snapshots for {version}: {len(snapshots)}")
        for s in snapshots:
            print(f"  {s.get('timestamp', '?')} | {s.get('stage', '?')} | {s.get('agent', '?')} | {s.get('commits', {})}")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == '__main__':
    main()
