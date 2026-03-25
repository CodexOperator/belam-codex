#!/usr/bin/env python3
"""
Tests for scripts/handoff_diff.py

Covers:
  - Snapshot recording to state JSON
  - Diff generation with real git repos
  - Truncation logic (--stat only when diff > 3000 chars)
  - Graceful fallbacks (no prior snapshot, missing repo, first touch)
"""

import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from unittest import TestCase, main as unittest_main
from unittest.mock import patch, MagicMock

# Add scripts/ to path
WORKSPACE = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE / 'scripts'))

from handoff_diff import (
    snapshot_handoff_commits,
    build_handoff_diff,
    _get_git_head,
    _find_last_snapshot_for_agent,
    _relevant_paths,
    _load_state,
    _save_state,
    MAX_HUNK_CHARS,
)


class TestSnapshotHandoffCommits(TestCase):
    """Test snapshot_handoff_commits() recording."""

    def setUp(self):
        """Create a temp directory for pipeline state files."""
        self.tmpdir = tempfile.mkdtemp()
        self.orig_builds = os.environ.get('WORKSPACE', '')
        # We'll patch _load_state and _save_state to use temp files

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('handoff_diff.BUILDS_DIR')
    @patch('handoff_diff._get_git_head')
    def test_snapshot_records_commits(self, mock_head, mock_builds):
        """Snapshot should record workspace and ml HEAD hashes."""
        mock_builds.__truediv__ = lambda self, x: Path(self.tmpdir) / x
        mock_builds.mkdir = MagicMock()
        mock_builds.exists = MagicMock(return_value=True)

        # Set up a temp state file
        builds_path = Path(self.tmpdir)
        version = 'test-pipeline'
        state_file = builds_path / f'{version}_state.json'
        state_file.write_text(json.dumps({'version': version, 'stages': {}}))

        # Mock git heads
        mock_head.side_effect = lambda p: {
            'workspace': 'abc1234567890',
            'machinelearning': 'def9876543210',
        }.get('workspace' if 'workspace' in str(p) else 'machinelearning')

        with patch('handoff_diff._load_state') as mock_load, \
             patch('handoff_diff._save_state') as mock_save:
            mock_load.return_value = {'version': version, 'stages': {}}
            saved_state = {}

            def capture_save(v, s):
                saved_state.update(s)
            mock_save.side_effect = capture_save

            snap = snapshot_handoff_commits(version, 'architect_design', 'architect')

        # Verify snapshot structure
        self.assertEqual(snap['stage'], 'architect_design')
        self.assertEqual(snap['agent'], 'architect')
        self.assertIn('timestamp', snap)
        self.assertIn('commits', snap)

        # Verify state was saved with handoff_snapshots
        self.assertIn('handoff_snapshots', saved_state)
        self.assertEqual(len(saved_state['handoff_snapshots']), 1)

    @patch('handoff_diff._get_git_head', return_value=None)
    def test_snapshot_graceful_no_repos(self, mock_head):
        """Snapshot should handle missing git repos gracefully."""
        with patch('handoff_diff._load_state', return_value={'version': 'v', 'stages': {}}), \
             patch('handoff_diff._save_state'):
            snap = snapshot_handoff_commits('v', 'stage', 'agent')

        self.assertIn('_note', snap['commits'])
        self.assertEqual(snap['commits']['_note'], 'no git repos found')

    def test_snapshot_appends_to_existing(self):
        """Multiple snapshots should accumulate in the array."""
        existing_state = {
            'version': 'v',
            'handoff_snapshots': [
                {'stage': 'old', 'agent': 'architect', 'timestamp': '2026-01-01T00:00:00Z', 'commits': {'workspace': 'aaa'}},
            ],
        }

        with patch('handoff_diff._load_state', return_value=existing_state), \
             patch('handoff_diff._save_state') as mock_save, \
             patch('handoff_diff._get_git_head', return_value='bbb1234'):
            snap = snapshot_handoff_commits('v', 'new_stage', 'builder')

        saved = mock_save.call_args[0][1]
        self.assertEqual(len(saved['handoff_snapshots']), 2)
        self.assertEqual(saved['handoff_snapshots'][-1]['agent'], 'builder')


class TestFindLastSnapshot(TestCase):
    """Test _find_last_snapshot_for_agent() lookup."""

    def test_finds_correct_agent(self):
        """Should find the last snapshot for a specific agent, not just any agent."""
        state = {
            'handoff_snapshots': [
                {'stage': 'design', 'agent': 'architect', 'commits': {'workspace': 'a1'}},
                {'stage': 'review', 'agent': 'critic', 'commits': {'workspace': 'c1'}},
                {'stage': 'implement', 'agent': 'builder', 'commits': {'workspace': 'b1'}},
                {'stage': 'code_review', 'agent': 'critic', 'commits': {'workspace': 'c2'}},
            ],
        }

        with patch('handoff_diff._load_state', return_value=state):
            result = _find_last_snapshot_for_agent('v', 'critic')

        self.assertIsNotNone(result)
        self.assertEqual(result['stage'], 'code_review')
        self.assertEqual(result['commits']['workspace'], 'c2')

    def test_returns_none_for_unknown_agent(self):
        """Should return None if agent has no prior snapshots."""
        state = {
            'handoff_snapshots': [
                {'stage': 'design', 'agent': 'architect', 'commits': {'workspace': 'a1'}},
            ],
        }

        with patch('handoff_diff._load_state', return_value=state):
            result = _find_last_snapshot_for_agent('v', 'builder')

        self.assertIsNone(result)

    def test_returns_none_for_empty_snapshots(self):
        """Should return None if no snapshots exist at all."""
        with patch('handoff_diff._load_state', return_value={'version': 'v'}):
            result = _find_last_snapshot_for_agent('v', 'architect')

        self.assertIsNone(result)


class TestBuildHandoffDiff(TestCase):
    """Test build_handoff_diff() output formatting."""

    def test_first_touch_returns_empty(self):
        """First touch (no prior snapshot) should return empty string."""
        with patch('handoff_diff._find_last_snapshot_for_agent', return_value=None):
            result = build_handoff_diff('v', 'architect')

        self.assertEqual(result, '')

    def test_no_changes_returns_empty(self):
        """Same commit hash → no changes → empty string."""
        snapshot = {
            'stage': 'design',
            'agent': 'architect',
            'commits': {'workspace': 'abc123'},
        }

        with patch('handoff_diff._find_last_snapshot_for_agent', return_value=snapshot), \
             patch('handoff_diff._get_git_head', return_value='abc123'):
            result = build_handoff_diff('v', 'architect')

        self.assertEqual(result, '')

    @patch('handoff_diff._run_git_diff')
    @patch('handoff_diff._run_git_stat')
    @patch('handoff_diff._get_git_head')
    @patch('handoff_diff._find_last_snapshot_for_agent')
    def test_small_diff_includes_hunks(self, mock_find, mock_head, mock_stat, mock_diff):
        """Small diffs should include full hunks."""
        mock_find.return_value = {
            'stage': 'design',
            'agent': 'architect',
            'commits': {'workspace': 'old123'},
        }
        mock_head.return_value = 'new456'
        mock_stat.return_value = ' scripts/foo.py | 5 ++---\n 1 file changed'
        mock_diff.return_value = 'diff --git a/scripts/foo.py\n+line1\n-line2'

        result = build_handoff_diff('v', 'architect')

        self.assertIn('Changes Since Your Last Session', result)
        self.assertIn('Workspace', result)
        self.assertIn('diff --git', result)

    @patch('handoff_diff._run_git_diff')
    @patch('handoff_diff._run_git_stat')
    @patch('handoff_diff._get_git_head')
    @patch('handoff_diff._find_last_snapshot_for_agent')
    def test_large_diff_stat_only(self, mock_find, mock_head, mock_stat, mock_diff):
        """Large diffs should show --stat only with a note."""
        mock_find.return_value = {
            'stage': 'design',
            'agent': 'architect',
            'commits': {'workspace': 'old123'},
        }
        mock_head.return_value = 'new456'
        mock_stat.return_value = ' scripts/foo.py | 100 +++\n 1 file changed'
        # Return a diff that exceeds MAX_HUNK_CHARS
        mock_diff.return_value = 'x' * (MAX_HUNK_CHARS + 1)

        result = build_handoff_diff('v', 'architect')

        self.assertIn('Changes Since Your Last Session', result)
        self.assertIn('scripts/foo.py', result)
        self.assertIn('read the files directly', result)
        # Should NOT include the full diff
        self.assertNotIn('x' * 100, result)

    @patch('handoff_diff._run_git_diff')
    @patch('handoff_diff._run_git_stat')
    @patch('handoff_diff._get_git_head')
    @patch('handoff_diff._find_last_snapshot_for_agent')
    def test_ipynb_stat_only(self, mock_find, mock_head, mock_stat, mock_diff):
        """Notebook diffs should always be --stat only."""
        mock_find.return_value = {
            'stage': 'design',
            'agent': 'builder',
            'commits': {'workspace': 'old123'},
        }
        mock_head.return_value = 'new456'
        mock_stat.return_value = ' notebooks/test.ipynb | 500 +++\n 1 file changed'
        mock_diff.return_value = 'diff --git a/notebooks/test.ipynb\n+{"cells":...}'

        result = build_handoff_diff('v', 'builder')

        self.assertIn('notebook diffs omitted', result)


class TestRelevantPaths(TestCase):
    """Test _relevant_paths() scoping."""

    def test_workspace_paths(self):
        paths = _relevant_paths('test-v', 'workspace')
        self.assertTrue(any('pipeline_builds/test-v' in p for p in paths))
        self.assertTrue(any('tasks/test-v' in p for p in paths))
        self.assertTrue(any('pipelines/test-v' in p for p in paths))

    def test_machinelearning_paths(self):
        paths = _relevant_paths('test-v', 'machinelearning')
        self.assertTrue(any('pipeline_builds/test-v' in p for p in paths))


class TestGetGitHead(TestCase):
    """Test _get_git_head() with real workspace repos."""

    def test_workspace_has_head(self):
        """The workspace repo should have a valid HEAD."""
        head = _get_git_head(WORKSPACE)
        if (WORKSPACE / '.git').exists():
            self.assertIsNotNone(head)
            self.assertEqual(len(head), 40)  # SHA-1 hash

    def test_nonexistent_repo_returns_none(self):
        """Non-existent path should return None."""
        result = _get_git_head(Path('/nonexistent/repo'))
        self.assertIsNone(result)

    def test_non_git_dir_returns_none(self):
        """Directory without .git should return None."""
        result = _get_git_head(Path('/tmp'))
        self.assertIsNone(result)


class TestIntegration(TestCase):
    """Integration test: snapshot → diff cycle with the real workspace repo."""

    def test_snapshot_and_diff_cycle(self):
        """End-to-end: record a snapshot, then build_handoff_diff returns empty
        (since no changes happened between snapshots)."""
        version = '_test_integration_handoff'

        # Use temp state
        state = {'version': version, 'stages': {}}

        with patch('handoff_diff._load_state', return_value=state) as mock_load, \
             patch('handoff_diff._save_state') as mock_save:

            # Record snapshot as architect
            snap1 = snapshot_handoff_commits(version, 'design', 'architect')
            saved_state = mock_save.call_args[0][1]

            # Now load the updated state for the diff lookup
            mock_load.return_value = saved_state

            # Record snapshot as critic
            snap2 = snapshot_handoff_commits(version, 'review', 'critic')
            saved_state2 = mock_save.call_args[0][1]
            mock_load.return_value = saved_state2

            # Build diff for architect (since their last snapshot)
            # Since no commits happened between snap1 and now, diff should be empty
            diff = build_handoff_diff(version, 'architect')
            # This should be empty because HEAD hasn't changed
            self.assertEqual(diff, '')


if __name__ == '__main__':
    unittest_main()
