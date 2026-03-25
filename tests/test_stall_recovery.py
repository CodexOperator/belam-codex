#!/usr/bin/env python3
"""Tests for pipeline_stall_recovery.py"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_stall_recovery import (
    detect_stall,
    get_agent_for_stage,
    get_recovery_attempts,
    calculate_timeout,
    is_pid_alive,
    BASE_TIMEOUT_SECONDS,
    TIMEOUT_ESCALATION,
    MAX_RECOVERY_ATTEMPTS,
)


class TestDetectStall:
    """Test stall detection logic."""

    def _make_state(self, status="p1_builder_implement", minutes_ago=60, pid=99999):
        updated = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M")
        return {
            "status": status,
            "status_updated": updated,
            "last_dispatched": updated,
            "dispatch_pid": pid,
        }

    def test_stale_dead_pid_detected(self):
        """Pipeline with stale timestamp and dead PID should be detected."""
        state = self._make_state(minutes_ago=60, pid=1)  # PID 1 is init, alive but not ours
        # Use a definitely-dead PID
        state["dispatch_pid"] = 999999999
        result = detect_stall(state, threshold_minutes=30)
        assert result is not None
        assert result["age_minutes"] >= 59

    def test_fresh_pipeline_not_stalled(self):
        """Pipeline updated recently should NOT be detected."""
        state = self._make_state(minutes_ago=5)
        result = detect_stall(state, threshold_minutes=30)
        assert result is None

    def test_archived_not_detected(self):
        """Archived pipelines should not be detected."""
        state = self._make_state(status="archived", minutes_ago=120)
        result = detect_stall(state, threshold_minutes=30)
        assert result is None

    def test_completed_not_detected(self):
        """Completed stages should not be detected."""
        state = self._make_state(status="p1_complete", minutes_ago=120)
        result = detect_stall(state, threshold_minutes=30)
        assert result is None

    def test_various_active_stages(self):
        """Various active stage names should be detected when stale."""
        active_stages = [
            "p1_builder_implement",
            "p1_critic_review",
            "p1_architect_design",
            "p2_builder_bugfix",
            "p1_critic_design_review",
        ]
        for stage in active_stages:
            state = self._make_state(status=stage, minutes_ago=60, pid=999999999)
            result = detect_stall(state, threshold_minutes=30)
            assert result is not None, f"Should detect stall for stage: {stage}"

    def test_missing_status_updated(self):
        """Missing status_updated should not crash."""
        state = {"status": "p1_builder_implement"}
        result = detect_stall(state, threshold_minutes=30)
        assert result is None

    def test_iso_format_timestamp(self):
        """ISO format timestamps should be parsed correctly."""
        ts = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        state = {
            "status": "p1_builder_implement",
            "status_updated": ts,
            "dispatch_pid": 999999999,
        }
        result = detect_stall(state, threshold_minutes=30)
        assert result is not None


class TestGetAgentForStage:
    """Test stage-to-agent mapping."""

    def test_builder_stages(self):
        assert get_agent_for_stage("p1_builder_implement") == "builder"
        assert get_agent_for_stage("p1_builder_bugfix") == "builder"
        assert get_agent_for_stage("p2_bugfix") == "builder"

    def test_critic_stages(self):
        assert get_agent_for_stage("p1_critic_review") == "critic"
        assert get_agent_for_stage("p1_critic_design_review") == "critic"
        assert get_agent_for_stage("p2_critic_code_review") == "critic"

    def test_architect_stages(self):
        assert get_agent_for_stage("p1_architect_design") == "architect"
        assert get_agent_for_stage("p2_architect_design") == "architect"

    def test_unknown_defaults_to_builder(self):
        assert get_agent_for_stage("unknown_stage") == "builder"


class TestRecoveryAttempts:
    """Test retry counting."""

    def test_no_attempts(self):
        state = {}
        assert get_recovery_attempts(state, "p1_builder_implement") == 0

    def test_with_attempts(self):
        state = {"recovery_attempts": {"p1_builder_implement": 2}}
        assert get_recovery_attempts(state, "p1_builder_implement") == 2

    def test_different_stage(self):
        state = {"recovery_attempts": {"p1_builder_implement": 2}}
        assert get_recovery_attempts(state, "p1_critic_review") == 0


class TestTimeoutEscalation:
    """Test timeout calculation with escalation."""

    def test_first_attempt(self):
        assert calculate_timeout(0) == BASE_TIMEOUT_SECONDS

    def test_second_attempt(self):
        expected = int(BASE_TIMEOUT_SECONDS * TIMEOUT_ESCALATION)
        assert calculate_timeout(1) == expected

    def test_third_attempt(self):
        expected = int(BASE_TIMEOUT_SECONDS * (TIMEOUT_ESCALATION ** 2))
        assert calculate_timeout(2) == expected

    def test_escalation_increases(self):
        t0 = calculate_timeout(0)
        t1 = calculate_timeout(1)
        t2 = calculate_timeout(2)
        assert t0 < t1 < t2


class TestIsPidAlive:
    """Test PID checking."""

    def test_invalid_pid(self):
        assert is_pid_alive(0) is False
        assert is_pid_alive(-1) is False

    def test_definitely_dead_pid(self):
        assert is_pid_alive(999999999) is False

    def test_own_pid_alive(self):
        assert is_pid_alive(os.getpid()) is True


class TestMaxRetries:
    """Test that max retries are respected."""

    def test_under_max(self):
        state = {"recovery_attempts": {"p1_builder_implement": 1}}
        assert get_recovery_attempts(state, "p1_builder_implement") < MAX_RECOVERY_ATTEMPTS

    def test_at_max(self):
        state = {"recovery_attempts": {"p1_builder_implement": MAX_RECOVERY_ATTEMPTS}}
        assert get_recovery_attempts(state, "p1_builder_implement") >= MAX_RECOVERY_ATTEMPTS
