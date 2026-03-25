"""
Unit tests for scripts/auto_wiggum.py

All subprocess.run calls are mocked — openclaw is never actually invoked.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import auto_wiggum


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok() -> MagicMock:
    """A mock subprocess.CompletedProcess with returncode=0."""
    m = MagicMock()
    m.returncode = 0
    m.stderr = ""
    return m


def _fail(msg: str = "error") -> MagicMock:
    """A mock subprocess.CompletedProcess with returncode=1."""
    m = MagicMock()
    m.returncode = 1
    m.stderr = msg
    return m


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

class TestArgParsing:
    def _parse(self, args):
        parser = auto_wiggum.build_parser()
        return parser.parse_args(args)

    def test_required_agent_and_timeout_and_task(self):
        args = self._parse(["--agent", "builder", "--timeout", "600", "--task", "Do X"])
        assert args.agent == "builder"
        assert args.timeout == 600
        assert args.task == "Do X"

    def test_default_steer_ratio(self):
        args = self._parse(["--agent", "sage", "--timeout", "300", "--task", "t"])
        assert args.steer_ratio == 0.8

    def test_custom_steer_ratio(self):
        args = self._parse(["--agent", "sage", "--timeout", "300", "--steer-ratio", "0.7", "--task", "t"])
        assert args.steer_ratio == 0.7

    def test_task_file(self):
        args = self._parse(["--agent", "builder", "--timeout", "60", "--task-file", "specs/task.md"])
        assert args.task_file == "specs/task.md"
        assert args.task is None

    def test_task_and_task_file_mutually_exclusive(self):
        parser = auto_wiggum.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--agent", "b", "--timeout", "60", "--task", "t", "--task-file", "f.md"])

    def test_pipeline_and_stage(self):
        args = self._parse(["--agent", "builder", "--timeout", "600", "--task", "t",
                            "--pipeline", "my-pipe", "--stage", "p1_builder_implement"])
        assert args.pipeline == "my-pipe"
        assert args.stage == "p1_builder_implement"

    def test_complete_on_exit_flag(self):
        args = self._parse(["--agent", "builder", "--timeout", "600", "--task", "t",
                            "--complete-on-exit"])
        assert args.complete_on_exit is True

    def test_complete_on_exit_defaults_false(self):
        args = self._parse(["--agent", "builder", "--timeout", "600", "--task", "t"])
        assert args.complete_on_exit is False

    def test_missing_agent_exits(self):
        parser = auto_wiggum.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--timeout", "60", "--task", "t"])

    def test_missing_timeout_exits(self):
        parser = auto_wiggum.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--agent", "b", "--task", "t"])

    def test_missing_task_exits(self):
        parser = auto_wiggum.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--agent", "b", "--timeout", "60"])


# ---------------------------------------------------------------------------
# Steer timing calculation
# ---------------------------------------------------------------------------

class TestSteerTiming:
    def test_default_80_percent(self):
        timeout = 600
        ratio = 0.8
        steer_delay = int(timeout * ratio)
        assert steer_delay == 480
        assert timeout - steer_delay == 120

    def test_custom_70_percent(self):
        timeout = 300
        ratio = 0.7
        steer_delay = int(timeout * ratio)
        assert steer_delay == 210
        assert timeout - steer_delay == 90

    def test_90_percent(self):
        timeout = 1000
        ratio = 0.9
        steer_delay = int(timeout * ratio)
        assert steer_delay == 900
        assert timeout - steer_delay == 100


# ---------------------------------------------------------------------------
# Steer message formatting
# ---------------------------------------------------------------------------

class TestSteerMessage:
    def test_contains_remaining_time(self):
        msg = auto_wiggum.build_steer_message(120, None, None)
        assert "120s" in msg

    def test_wrap_up_header(self):
        msg = auto_wiggum.build_steer_message(60, None, None)
        assert "WRAP UP" in msg

    def test_no_pipeline_context_by_default(self):
        msg = auto_wiggum.build_steer_message(60, None, None)
        assert "pipeline_orchestrate" not in msg

    def test_pipeline_context_included(self):
        msg = auto_wiggum.build_steer_message(120, "my-pipe", "p1_builder_implement")
        assert "my-pipe" in msg
        assert "p1_builder_implement" in msg
        assert "pipeline_orchestrate.py" in msg

    def test_no_new_work_instruction(self):
        msg = auto_wiggum.build_steer_message(30, None, None)
        assert "Do NOT start new work" in msg

    def test_pipeline_none_stage_provided_no_pipeline_line(self):
        # Only stage, no pipeline — should not include pipeline orchestrate line
        msg = auto_wiggum.build_steer_message(60, None, "p1_stage")
        assert "pipeline_orchestrate" not in msg


# ---------------------------------------------------------------------------
# Session key construction
# ---------------------------------------------------------------------------

class TestSessionKey:
    def test_builder(self):
        assert auto_wiggum.session_key("builder") == "agent:builder:main"

    def test_sage(self):
        assert auto_wiggum.session_key("sage") == "agent:sage:main"

    def test_architect(self):
        assert auto_wiggum.session_key("architect") == "agent:architect:main"


# ---------------------------------------------------------------------------
# Session reset command construction
# ---------------------------------------------------------------------------

class TestResetSession:
    def test_calls_correct_command(self):
        with patch("subprocess.run", return_value=_ok()) as mock_run:
            result = auto_wiggum.reset_session("builder")
        assert result is True
        mock_run.assert_called_once_with(
            ["openclaw", "session", "reset", "agent:builder:main"],
            capture_output=True,
            text=True,
        )

    def test_returns_false_on_failure(self):
        with patch("subprocess.run", return_value=_fail("gateway down")):
            result = auto_wiggum.reset_session("builder")
        assert result is False


# ---------------------------------------------------------------------------
# Session send command construction
# ---------------------------------------------------------------------------

class TestSendMessage:
    def test_calls_correct_command(self):
        with patch("subprocess.run", return_value=_ok()) as mock_run:
            result = auto_wiggum.send_message("sage", "Hello task")
        assert result is True
        mock_run.assert_called_once_with(
            ["openclaw", "session", "send", "agent:sage:main", "Hello task"],
            capture_output=True,
            text=True,
        )

    def test_returns_false_on_failure(self):
        with patch("subprocess.run", return_value=_fail("not found")):
            result = auto_wiggum.send_message("sage", "Hello task")
        assert result is False


# ---------------------------------------------------------------------------
# Send with retry
# ---------------------------------------------------------------------------

class TestSendMessageWithRetry:
    def test_succeeds_first_try(self):
        with patch("subprocess.run", return_value=_ok()) as mock_run:
            result = auto_wiggum.send_message_with_retry("builder", "task")
        assert result is True
        assert mock_run.call_count == 1

    def test_retries_on_first_failure(self):
        side_effects = [_fail(), _ok()]
        with patch("subprocess.run", side_effect=side_effects) as mock_run:
            with patch("time.sleep"):  # don't actually sleep
                result = auto_wiggum.send_message_with_retry("builder", "task", retries=1)
        assert result is True
        assert mock_run.call_count == 2

    def test_fails_after_all_retries(self):
        with patch("subprocess.run", return_value=_fail()) as mock_run:
            with patch("time.sleep"):
                result = auto_wiggum.send_message_with_retry("builder", "task", retries=1)
        assert result is False
        assert mock_run.call_count == 2


# ---------------------------------------------------------------------------
# Error handling in run()
# ---------------------------------------------------------------------------

class TestRunErrorHandling:
    def _make_args(self, **kwargs):
        defaults = dict(
            agent="builder",
            timeout=10,
            steer_ratio=0.8,
            task="Do something",
            task_file=None,
            pipeline=None,
            stage=None,
            complete_on_exit=False,
        )
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def _make_args_simple(self):
        import argparse
        return argparse.Namespace(
            agent="builder",
            timeout=10,
            steer_ratio=0.8,
            task="Do something",
            task_file=None,
            pipeline=None,
            stage=None,
            complete_on_exit=False,
        )

    def test_exit_1_if_reset_fails(self):
        args = self._make_args_simple()
        with patch("subprocess.run", return_value=_fail("reset error")):
            result = auto_wiggum.run(args)
        assert result == 1

    def test_exit_1_if_send_fails_after_retry(self):
        import argparse
        args = argparse.Namespace(
            agent="builder",
            timeout=10,
            steer_ratio=0.8,
            task="Do something",
            task_file=None,
            pipeline=None,
            stage=None,
            complete_on_exit=False,
        )
        # reset succeeds, all sends fail
        with patch("subprocess.run", side_effect=[_ok(), _fail(), _fail()]):
            with patch("time.sleep"):
                result = auto_wiggum.run(args)
        assert result == 1

    def test_exit_0_on_success(self):
        import argparse
        args = argparse.Namespace(
            agent="builder",
            timeout=10,
            steer_ratio=0.8,
            task="Do something",
            task_file=None,
            pipeline=None,
            stage=None,
            complete_on_exit=False,
        )
        with patch("subprocess.run", return_value=_ok()):
            with patch("time.sleep"):
                result = auto_wiggum.run(args)
        assert result == 0

    def test_exit_1_if_task_file_missing(self):
        import argparse
        args = argparse.Namespace(
            agent="builder",
            timeout=10,
            steer_ratio=0.8,
            task=None,
            task_file="/nonexistent/path/task.md",
            pipeline=None,
            stage=None,
            complete_on_exit=False,
        )
        with patch("subprocess.run", return_value=_ok()):
            result = auto_wiggum.run(args)
        assert result == 1


# ---------------------------------------------------------------------------
# --task-file reads file content correctly
# ---------------------------------------------------------------------------

class TestTaskFile:
    def test_reads_file_content(self):
        import argparse
        task_content = "# My Task\n\nDo all the things.\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(task_content)
            f.flush()
            tmp_path = f.name

        sent_messages = []

        def fake_run(cmd, **kwargs):
            # cmd = ["openclaw", "session", "send", "<session-key>", "<message>"]
            if len(cmd) >= 5 and cmd[2] == "send":
                sent_messages.append(cmd[4])
            return _ok()

        args = argparse.Namespace(
            agent="sage",
            timeout=10,
            steer_ratio=0.8,
            task=None,
            task_file=tmp_path,
            pipeline=None,
            stage=None,
            complete_on_exit=False,
        )
        with patch("subprocess.run", side_effect=fake_run):
            with patch("time.sleep"):
                result = auto_wiggum.run(args)

        assert result == 0
        # The first send should contain the file content
        assert task_content in sent_messages[0]

        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Pipeline context in task
# ---------------------------------------------------------------------------

class TestPipelineContext:
    def test_pipeline_context_prepended_to_task(self):
        import argparse
        sent_messages = []

        def fake_run(cmd, **kwargs):
            # cmd = ["openclaw", "session", "send", "<session-key>", "<message>"]
            if len(cmd) >= 5 and cmd[2] == "send":
                sent_messages.append(cmd[4])
            return _ok()

        args = argparse.Namespace(
            agent="builder",
            timeout=10,
            steer_ratio=0.8,
            task="Do the work",
            task_file=None,
            pipeline="my-pipe",
            stage="p1_implement",
            complete_on_exit=False,
        )
        with patch("subprocess.run", side_effect=fake_run):
            with patch("time.sleep"):
                auto_wiggum.run(args)

        assert sent_messages, "No messages were sent"
        first_msg = sent_messages[0]
        assert "my-pipe" in first_msg
        assert "p1_implement" in first_msg
        assert "Do the work" in first_msg

    def test_complete_on_exit_calls_orchestrate(self):
        import argparse
        run_calls = []

        def fake_run(cmd, **kwargs):
            run_calls.append(cmd)
            return _ok()

        args = argparse.Namespace(
            agent="builder",
            timeout=10,
            steer_ratio=0.8,
            task="Do something",
            task_file=None,
            pipeline="my-pipe",
            stage="p1_stage",
            complete_on_exit=True,
        )
        with patch("subprocess.run", side_effect=fake_run):
            with patch("time.sleep"):
                result = auto_wiggum.run(args)

        assert result == 0
        # One call should be to pipeline_orchestrate.py directly (not via session send)
        orchestrate_calls = [c for c in run_calls
                             if len(c) > 1 and "pipeline_orchestrate.py" in str(c[1])]
        assert len(orchestrate_calls) == 1
        assert "my-pipe" in orchestrate_calls[0]
        assert "complete" in orchestrate_calls[0]
        assert "p1_stage" in orchestrate_calls[0]


# Need this for Namespace usage in older test patterns
import argparse
