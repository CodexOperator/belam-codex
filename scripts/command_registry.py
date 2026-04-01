#!/usr/bin/env python3
"""
Cross-surface command registry.

Commands can be registered to appear on any combination of surfaces:
  - e0, e1, e2, e3: as e-mode operations
  - slash: as slash commands in session chats
  - cli: as belam CLI commands
  - skill: as skill invocations

Commands can also be persona-gated: only accessible to specific personas.

Auto-discovery scans scripts/ for files with COMMAND_META dicts and
skills/ for SKILL.md files.

Usage:
  from command_registry import registry
  cmds = registry.get_for_surface('e0', persona='builder')
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

WORKSPACE = Path(__file__).resolve().parent.parent


@dataclass
class RegisteredCommand:
    """A command registered in the cross-surface registry."""
    name: str
    handler: str               # "module:function" or script path
    surfaces: set[str] = field(default_factory=lambda: {'cli'})
    persona_access: set[str] = field(default_factory=lambda: {'*'})
    description: str = ''
    args_spec: list[str] = field(default_factory=list)
    source: str = 'builtin'    # 'builtin', 'e3-hook', 'script', 'skill'


class CommandRegistry:
    """Cross-surface command registry with auto-discovery."""

    def __init__(self):
        self._commands: dict[str, RegisteredCommand] = {}
        self._discovered = False

    def register(self, cmd: RegisteredCommand):
        """Register a command. Overwrites if name already exists."""
        self._commands[cmd.name] = cmd

    def unregister(self, name: str):
        """Remove a command by name."""
        self._commands.pop(name, None)

    def get(self, name: str) -> Optional[RegisteredCommand]:
        """Get a command by name."""
        self._ensure_discovered()
        return self._commands.get(name)

    def get_for_surface(self, surface: str, persona: str = None) -> list[RegisteredCommand]:
        """Get all commands available on a surface, optionally filtered by persona.

        Args:
            surface: One of 'e0', 'e1', 'e2', 'e3', 'slash', 'cli', 'skill'
            persona: Optional persona role for access filtering
        """
        self._ensure_discovered()
        results = []
        for cmd in self._commands.values():
            if surface not in cmd.surfaces:
                continue
            if persona and '*' not in cmd.persona_access and persona not in cmd.persona_access:
                continue
            results.append(cmd)
        return sorted(results, key=lambda c: c.name)

    def get_for_mode(self, mode_num: int, persona: str = None) -> list[RegisteredCommand]:
        """Get commands for a specific e-mode number."""
        surface = f'e{mode_num}'
        return self.get_for_surface(surface, persona=persona)

    def all_commands(self) -> list[RegisteredCommand]:
        """Get all registered commands."""
        self._ensure_discovered()
        return sorted(self._commands.values(), key=lambda c: c.name)

    def auto_discover(self, force: bool = False):
        """Scan scripts/ and skills/ for auto-registerable commands.

        Looks for:
          - Python files with COMMAND_META dict
          - SKILL.md files with command metadata
        """
        if self._discovered and not force:
            return

        # Scan scripts/ for COMMAND_META
        scripts_dir = WORKSPACE / 'scripts'
        if scripts_dir.is_dir():
            for py_file in scripts_dir.glob('*.py'):
                meta = self._extract_command_meta(py_file)
                if meta:
                    self.register(RegisteredCommand(
                        name=meta.get('name', py_file.stem),
                        handler=str(py_file),
                        surfaces=set(meta.get('surfaces', ['cli'])),
                        persona_access=set(meta.get('persona_access', ['*'])),
                        description=meta.get('description', ''),
                        args_spec=meta.get('args', []),
                        source='script',
                    ))

        # Scan skills/ for SKILL.md
        skills_dir = WORKSPACE / 'skills'
        if skills_dir.is_dir():
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / 'SKILL.md'
                if skill_md.exists():
                    meta = self._extract_skill_meta(skill_md)
                    if meta:
                        self.register(RegisteredCommand(
                            name=meta.get('name', skill_dir.name),
                            handler=f'skill:{skill_dir.name}',
                            surfaces=set(meta.get('surfaces', ['slash', 'skill'])),
                            persona_access=set(meta.get('persona_access', ['*'])),
                            description=meta.get('description', ''),
                            args_spec=meta.get('args', []),
                            source='skill',
                        ))

        self._discovered = True

    def to_index(self) -> dict:
        """Export registry as JSON-serializable dict for cockpit rendering."""
        self._ensure_discovered()
        return {
            name: {
                'handler': cmd.handler,
                'surfaces': sorted(cmd.surfaces),
                'persona_access': sorted(cmd.persona_access),
                'description': cmd.description,
                'args': cmd.args_spec,
                'source': cmd.source,
            }
            for name, cmd in sorted(self._commands.items())
        }

    def save_index(self, path: Path = None):
        """Save command index to JSON file."""
        import json
        if path is None:
            path = WORKSPACE / 'state' / 'command_index.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_index(), indent=2))

    # ───────────────────────────────────────────────────────────
    # Private helpers
    # ───────────────────────────────────────────────────────────

    def _ensure_discovered(self):
        if not self._discovered:
            self.auto_discover()

    def _extract_command_meta(self, py_file: Path) -> dict | None:
        """Extract COMMAND_META dict from a Python file using AST parsing."""
        try:
            source = py_file.read_text()
            tree = ast.parse(source)
        except (SyntaxError, OSError):
            return None

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'COMMAND_META':
                        try:
                            return ast.literal_eval(node.value)
                        except (ValueError, TypeError):
                            return None
        return None

    def _extract_skill_meta(self, skill_md: Path) -> dict | None:
        """Extract command metadata from SKILL.md frontmatter."""
        try:
            text = skill_md.read_text()
        except OSError:
            return None

        m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
        if not m:
            return None

        fm = m.group(1)
        meta = {}

        for line in fm.splitlines():
            kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
            if kv:
                key = kv.group(1)
                value = kv.group(2).strip()
                if value.startswith('[') and value.endswith(']'):
                    meta[key] = [x.strip().strip('"').strip("'")
                                 for x in value[1:-1].split(',') if x.strip()]
                else:
                    meta[key] = value

        return meta if meta.get('name') else None


# Global singleton
registry = CommandRegistry()


# ═══════════════════════════════════════════════════════════════════════
# Script skeleton template for e2-created scripts
# ═══════════════════════════════════════════════════════════════════════

SCRIPT_SKELETON = '''#!/usr/bin/env python3
"""{description}"""

# Command registry metadata - consumed by e3 auto-discovery
COMMAND_META = {{
    "name": "{name}",
    "surfaces": {surfaces},
    "persona_access": {persona_access},
    "description": "{description}",
    "args": {args},
}}


def main({args_signature}) -> int:
    """Entry point called by command registry."""
    # TODO: implement
    print(f"{name} called with: {args_print}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(*sys.argv[1:]))
'''


def generate_script_skeleton(name: str, description: str = '',
                             surfaces: list[str] = None,
                             persona_access: list[str] = None,
                             args: list[str] = None) -> str:
    """Generate a Python script skeleton with COMMAND_META for auto-discovery."""
    if surfaces is None:
        surfaces = ['cli', 'e0']
    if persona_access is None:
        persona_access = ['*']
    if args is None:
        args = []

    args_signature = ', '.join(f'{a}: str = ""' for a in args) if args else ''
    args_print = ', '.join(f'{a}={{{a}}}' for a in args) if args else ''

    return SCRIPT_SKELETON.format(
        name=name,
        description=description or f'{name} command',
        surfaces=surfaces,
        persona_access=persona_access,
        args=args,
        args_signature=args_signature,
        args_print=args_print,
    )


if __name__ == '__main__':
    """Dump command registry for verification."""
    import json

    registry.auto_discover(force=True)

    print(f"Discovered {len(registry.all_commands())} commands:\n")

    for cmd in registry.all_commands():
        surfaces = ', '.join(sorted(cmd.surfaces))
        access = ', '.join(sorted(cmd.persona_access))
        print(f"  {cmd.name:30s} [{surfaces}] ({access}) - {cmd.description[:60]}")

    print(f"\nBy surface:")
    for surface in ('e0', 'e1', 'e2', 'e3', 'slash', 'cli', 'skill'):
        cmds = registry.get_for_surface(surface)
        if cmds:
            print(f"  {surface}: {', '.join(c.name for c in cmds)}")
