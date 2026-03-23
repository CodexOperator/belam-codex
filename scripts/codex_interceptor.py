"""Codex Interceptor — catches raw commands and suggests coordinate equivalents.

Phase C of the Codex Layer. Provides:
  - 10 static interception rules for common raw→coordinate mappings
  - LM auto-rules stubbed for v1 (FLAG-4: speculative, design in v2)
  - Graduated enforcement: advisory → redirect → block
  - Workspace-prefix check to avoid false positives (Q3)
  - Advisory mode only for Phase 1

Pipeline: build-codex-layer-v1
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from codex_output_codec import CodexResult


# ── Data model ──────────────────────────────────────────────────────────────

@dataclass
class InterceptionRule:
    """Maps a raw command pattern to its coordinate equivalent."""
    pattern: re.Pattern       # regex matching raw command
    coordinate_template: str  # coordinate equivalent (human-readable suggestion)
    description: str          # explanation shown to agent
    source: str               # 'static' | 'lm'


# ── Static Rules (top 10 raw→coordinate mappings) ──────────────────────────

# Q3 fix: patterns include workspace-relative paths to avoid false positives

STATIC_RULES: List[InterceptionRule] = [
    InterceptionRule(
        pattern=re.compile(r'\bcat\s+(?:\./)?(?:tasks|decisions|lessons|pipelines|commands|modes|knowledge)/(\S+)\.md\b'),
        coordinate_template='{ns}{n} — navigate via coordinate',
        description='Navigate via coordinate instead of cat',
        source='static',
    ),
    InterceptionRule(
        pattern=re.compile(r'\bgrep\b.*\s+(?:\./)?(?:tasks|decisions|lessons|pipelines)/'),
        coordinate_template='--tag {pattern} or --since {d} — use engine filters',
        description='Use engine filter instead of grep',
        source='static',
    ),
    InterceptionRule(
        pattern=re.compile(r'\becho\s+"[^"]*"\s*>>\s*(?:\./)?(?:tasks|decisions|lessons|pipelines)/(\S+)\.md\b'),
        coordinate_template='e1{coord} B+ "{text}" — append via edit mode',
        description='Append via edit mode instead of echo >>',
        source='static',
    ),
    InterceptionRule(
        pattern=re.compile(r'\bpython3\s+scripts/codex_engine\.py\s+--supermap\b'),
        coordinate_template='e0 — orchestration sweep includes supermap',
        description='Use e0 for full orchestration sweep',
        source='static',
    ),
    InterceptionRule(
        pattern=re.compile(r'\bpython3\s+scripts/pipeline_update\.py\s+(\S+)\s+show\b'),
        coordinate_template='p{n} — navigate to pipeline coordinate',
        description='Navigate to pipeline coordinate',
        source='static',
    ),
    InterceptionRule(
        pattern=re.compile(r'\bpython3\s+scripts/pipeline_update\.py\s+(\S+)\s+complete\b'),
        coordinate_template='e0p{n} — use orchestrate mode for transitions',
        description='Use orchestrate mode for pipeline transitions',
        source='static',
    ),
    InterceptionRule(
        pattern=re.compile(r'\bRead\b.*(?:tasks|decisions|lessons|pipelines|commands|modes)/'),
        coordinate_template='{coord} — use coordinate navigation instead of Read',
        description='Use coordinate navigation instead of Read tool',
        source='static',
    ),
    InterceptionRule(
        pattern=re.compile(r'\bls\s+(?:\./)?(?:tasks|decisions|lessons|pipelines|commands|modes)/'),
        coordinate_template='{ns} — use namespace coordinate for listing',
        description='Use namespace coordinate for listing',
        source='static',
    ),
    InterceptionRule(
        pattern=re.compile(r'\bsed\b.*\s+(?:\./)?(?:tasks|decisions|lessons|pipelines)/(\S+)\.md\b'),
        coordinate_template='e1{coord} {field} {value} — use edit mode instead of sed',
        description='Use edit mode instead of sed',
        source='static',
    ),
    InterceptionRule(
        pattern=re.compile(r'\bpython3\s+scripts/log_memory\.py\b'),
        coordinate_template='e2 m "entry" — use create mode for memory entries',
        description='Use create mode for memory entries',
        source='static',
    ),
]


# ── Interceptor ─────────────────────────────────────────────────────────────

class CodexInterceptor:
    """Catches raw commands and suggests/redirects to coordinates.

    Modes:
      advisory (Phase 1): suggest coordinate, let command through
      redirect (Phase 2): execute coordinate equivalent instead
      block (Phase 2+):   block raw command, require coordinate or ! override
    """

    def __init__(self, workspace: Path, mode: str = 'advisory'):
        self.workspace = workspace
        self.mode = mode  # 'advisory' | 'redirect' | 'block'
        self.rules: List[InterceptionRule] = []
        self._build_rules()

    def _build_rules(self):
        """Build interception rules from static patterns + LM namespace."""
        self.rules.extend(STATIC_RULES)

        # FLAG-4: LM auto-rules stubbed for v1.
        # LMEntry has no replaces_pattern field — auto-generation requires
        # schema extension. Static rules cover the top-10 patterns.
        # Uncomment when LM schema has reverse-pattern support:
        #
        # try:
        #     from codex_lm_renderer import build_lm_tree
        #     entries = build_lm_tree(self.workspace)
        #     for entry in entries:
        #         rule = self._lm_entry_to_rule(entry)
        #         if rule:
        #             self.rules.append(rule)
        # except ImportError:
        #     pass

    def _lm_entry_to_rule(self, entry) -> Optional[InterceptionRule]:
        """Stub: convert LM entry to interception rule.

        v2 will add replaces_pattern to LMEntry for proper reverse-mapping.
        """
        return None  # FLAG-4: stubbed for v1

    def check(self, command: str) -> Optional[CodexResult]:
        """Check command against interception rules.

        Returns CodexResult with suggestion/redirect/block, or None for passthrough.
        """
        # Q3: Only intercept commands that reference workspace-relative paths
        # (patterns already scoped to workspace dirs in STATIC_RULES)
        for rule in self.rules:
            m = rule.pattern.search(command)
            if m:
                suggestion = rule.coordinate_template
                return self._apply_mode(command, suggestion, rule)
        return None

    def _apply_mode(self, command: str, suggestion: str, rule: InterceptionRule) -> CodexResult:
        """Apply enforcement mode to a matched rule."""
        if self.mode == 'advisory':
            # Let command through, append suggestion as hint
            return CodexResult(
                coord='_hint',
                source='interceptor',
                content_type='text',
                fields={'suggestion': suggestion, 'original': command},
                raw=command,
                rendered=f'💡 Coordinate equivalent: {suggestion}',
            )

        elif self.mode == 'redirect':
            # Would redirect to coordinate equivalent — not active in v1
            return CodexResult(
                coord='_redirect',
                source='interceptor',
                content_type='text',
                fields={'suggestion': suggestion, 'original': command},
                raw=command,
                rendered=f'↪ Redirecting to: {suggestion}',
            )

        elif self.mode == 'block':
            # Block with instruction — not active in v1
            return CodexResult(
                coord='_blocked',
                source='interceptor',
                content_type='text',
                fields={'suggestion': suggestion, 'original': command},
                raw=command,
                rendered=f'⛔ Raw command blocked. Use: {suggestion}\n   Override with: !{command}',
            )

        return None


# ── CLI test entry point ────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    workspace = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / '.openclaw' / 'workspace'
    interceptor = CodexInterceptor(workspace)

    if len(sys.argv) > 2:
        command = ' '.join(sys.argv[2:])
        result = interceptor.check(command)
        if result:
            print(result.rendered)
        else:
            print(f'No interception for: {command}')
    else:
        print(f'Loaded {len(interceptor.rules)} rules ({sum(1 for r in interceptor.rules if r.source == "static")} static)')
        for r in interceptor.rules:
            print(f'  [{r.source}] {r.description}')
