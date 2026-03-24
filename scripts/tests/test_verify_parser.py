#!/usr/bin/env python3
"""Test that pipeline_verify.parse_test_spec handles the standard format."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline_verify import parse_test_spec

# Write a minimal test spec with the expected format
spec = (
    "# Test Spec\n\n"
    "### T1: Example pass test\n"
    "**Type:** automated\n"
    "**Command:**\n"
    "```bash\n"
    "echo hello\n"
    "```\n"
    '**Pass criteria:** Exit code 0 AND contains "hello"\n'
    "**Covers:** D1\n\n"
    "### T2: File check test\n"
    "**Type:** file-check\n"
    "**Command:**\n"
    "```bash\n"
    "test -f /etc/hostname\n"
    "```\n"
    "**Pass criteria:** Exit code 0\n"
    "**Covers:** D2\n"
)

Path("/tmp/test_spec_parse.md").write_text(spec)
tests = parse_test_spec(Path("/tmp/test_spec_parse.md"))
assert len(tests) == 2, f"Expected 2 tests, got {len(tests)}"
assert tests[0]["id"] == "T1"
assert tests[0]["type"] == "automated"
assert "echo hello" in tests[0]["command"]
assert tests[1]["id"] == "T2"
assert tests[1]["type"] == "file-check"
print("PASS: parser works")
