"""Codex Dispatch — unified dispatch grammar for workspace interaction.

Phase B of the Codex Layer. Routes all input through:
  - Bare coords    → codex engine      (t5, e1t5, e0)
  - Prefix .       → render verbs      (.d, .a, .v1)
  - Prefix !       → shell passthrough (!git status)
  - Pipe |>        → output chaining   (e0 |> _.p1)
  - Prefix _       → result register   (_, _1, _.status)
  - No prefix      → interceptor check (Phase C) then shell fallback

FLAG-2 FIX: Uses |> for pipes (not ' > ') to avoid shell redirect collision.
             ! prefix checked BEFORE pipe splitting to prevent misrouting.

Pipeline: build-codex-layer-v1
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

from codex_output_codec import CodexResult, ResultRegister, output_to_codex

# Coordinate grammar regex (matches codex coordinate patterns)
COORD_RE = re.compile(r'^(md|mw|lm|[a-z])\d*$', re.IGNORECASE)

# Extended: match e{n}{coord} compounds (e1t6, e0p3) + bare coords (t5, lm3, d1-d5)
EXTENDED_COORD_RE = re.compile(
    r'^(?:e\d+(?:(?:md|mw|[a-z])\d*)?|(?:md|mw|lm|[a-z])\d*(?:-(?:md|mw|lm|[a-z])?\d+)?)$',
    re.IGNORECASE,
)

# Render verb patterns
RENDER_RE = re.compile(r'^\.[a-z]')

# Pipe operator (FLAG-2: |> not ' > ')
PIPE_OP = '|>'


class CodexDispatcher:
    """Unified dispatch for all workspace interaction."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.register = ResultRegister(workspace)
        self.interceptor = None  # set by Phase C

    def dispatch(self, input_str: str) -> CodexResult:
        """Route input through the dispatch grammar.

        Order (FLAG-2 fix: ! checked before pipes):
        1. Shell passthrough: ! prefix (BEFORE pipe check)
        2. Pipe chains: |> operator
        3. Render verbs: . prefix
        4. Result register: _ prefix
        5. Coordinate resolution: matches coord grammar
        6. Interceptor check (Phase C)
        7. Fallback: execute as shell
        """
        input_str = input_str.strip()
        if not input_str:
            return CodexResult(source='empty', rendered='(empty input)')

        # 1. Shell passthrough — checked FIRST, before pipe splitting
        #    This prevents !git log > file.txt from being misrouted
        if input_str.startswith('!'):
            return self._dispatch_shell(input_str[1:])

        # 2. Pipe chains: split on |> and execute sequentially
        if PIPE_OP in input_str:
            return self._dispatch_pipe(input_str)

        # 3. Render verbs: . prefix
        if RENDER_RE.match(input_str):
            return self._dispatch_render(input_str)

        # 4. Result register: _ prefix
        if input_str.startswith('_'):
            return self._dispatch_register(input_str)

        # 5. Coordinate resolution: matches coord grammar
        first_token = input_str.split()[0]
        if EXTENDED_COORD_RE.match(first_token):
            return self._dispatch_coord(input_str)

        # 6. Interceptor check (Phase C)
        if self.interceptor:
            redirect = self.interceptor.check(input_str)
            if redirect:
                return redirect

        # 7. Fallback: shell execution
        return self._dispatch_shell(input_str)

    def _dispatch_pipe(self, input_str: str) -> CodexResult:
        """Chain commands via |> operator. Previous result available as _."""
        parts = [p.strip() for p in input_str.split(PIPE_OP)]
        result = None
        for part in parts:
            if not part:
                continue
            # Substitute _ references from previous result
            if result:
                part = self._substitute_register_refs(part, result)
            result = self.dispatch(part)
            self.register.push(result)
        return result or CodexResult(source='pipe', rendered='(empty pipe)')

    def _dispatch_shell(self, command: str) -> CodexResult:
        """Execute shell command and run output through codec."""
        command = command.strip()
        try:
            proc = subprocess.run(
                command, shell=True,
                capture_output=True, text=True,
                cwd=str(self.workspace),
                timeout=30,
            )
            result = output_to_codex(command, proc.stdout, proc.stderr, proc.returncode)
            if proc.returncode != 0 and proc.stderr:
                result.rendered += f'\n[exit {proc.returncode}] {proc.stderr[:200]}'
            self.register.push(result)
            return result
        except subprocess.TimeoutExpired:
            return CodexResult(
                source=command, content_type='text',
                rendered=f'[timeout after 30s] {command}',
            )
        except Exception as e:
            return CodexResult(
                source=command, content_type='text',
                rendered=f'[error] {e}',
            )

    def _dispatch_render(self, input_str: str) -> CodexResult:
        """Route render verb to codex engine."""
        return self._dispatch_coord(input_str)

    def _dispatch_register(self, input_str: str) -> CodexResult:
        """Resolve result register reference."""
        # Field access: _.status, _2.p1
        if '.' in input_str:
            val = self.register.resolve_field(input_str)
            if val is not None:
                return CodexResult(
                    coord=input_str, source='register',
                    content_type='text', fields={'value': val},
                    rendered=val,
                )
        # Bare register: _, _1
        result = self.register.resolve(input_str)
        if result:
            return result
        return CodexResult(
            source='register', content_type='text',
            rendered=f'Register {input_str} is empty',
        )

    def _dispatch_coord(self, input_str: str) -> CodexResult:
        """Route coordinate to codex_engine."""
        try:
            proc = subprocess.run(
                ['python3', 'scripts/codex_engine.py'] + input_str.split(),
                capture_output=True, text=True,
                cwd=str(self.workspace),
                timeout=10,
            )
            result = output_to_codex(
                f'codex_engine.py {input_str}',
                proc.stdout, proc.stderr, proc.returncode,
            )
            self.register.push(result)
            return result
        except Exception as e:
            return CodexResult(
                source=input_str, content_type='text',
                rendered=f'[coord error] {e}',
            )

    def _substitute_register_refs(self, text: str, prev: CodexResult) -> str:
        """Replace _ references in text with values from previous result."""
        # _.field references
        def replace_field(m):
            field_name = m.group(1)
            val = prev.fields.get(field_name, m.group(0))
            return str(val)

        text = re.sub(r'_\.(\w+)', replace_field, text)
        # Bare _ → previous rendered output (first line)
        # Only substitute standalone _ (not inside identifiers like _my_var)
        if '_' in text and not re.search(r'_\.\w', text):
            first_line = prev.rendered.split('\n')[0] if prev.rendered else ''
            text = re.sub(r'(?<!\w)_(?!\w)', first_line, text)
        return text


# ── CLI entry point ─────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    workspace = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / '.openclaw' / 'workspace'
    dispatcher = CodexDispatcher(workspace)

    if len(sys.argv) > 2:
        result = dispatcher.dispatch(' '.join(sys.argv[2:]))
        print(result.rendered)
    else:
        print('Usage: codex_dispatch.py <workspace> <command>')
        print('  e.g.: codex_dispatch.py /path/to/workspace "t5"')
        print('  e.g.: codex_dispatch.py /path/to/workspace "!git status"')
        print('  e.g.: codex_dispatch.py /path/to/workspace "e0 |> _.p1"')
