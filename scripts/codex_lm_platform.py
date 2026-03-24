#!/usr/bin/env python3
"""
LM v3 Platform & System Namespace — oc.*, sys.*, r.*, sc.* commands.

Entries ARE invocations: typing `oc.gw` executes `openclaw gateway status`.

Registration: scan_platform_entries() returns LMEntry list for the renderer.
Execution: execute_platform(prefix, sub, args) routes to the correct handler.
"""

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
MAIN_WORKSPACE = Path(os.path.expanduser('~/.openclaw/workspace'))
TIMEOUT = 30


# ─── Entry dataclass (matches codex_lm_renderer convention) ────────────────

@dataclass
class LMEntry:
    verb: str
    syntax: str
    description: str
    source: str = 'platform'


# ═══════════════════════════════════════════════════════════════════════════
# D1: oc.* — OpenClaw Platform Commands
# ═══════════════════════════════════════════════════════════════════════════

OC_ENTRIES = [
    LMEntry('oc.status',   'oc.status',               'openclaw status (overall health)'),
    LMEntry('oc.gw',       'oc.gw [cmd]',             'gateway status|start|stop|restart|health'),
    LMEntry('oc.cron',     'oc.cron [cmd]',           'cron list|add|rm|run|status'),
    LMEntry('oc.sessions', 'oc.sessions',             'list active agent sessions'),
    LMEntry('oc.logs',     'oc.logs [n]',             'gateway log tail (last n lines)'),
    LMEntry('oc.doctor',   'oc.doctor',               'health checks + auto-fixes'),
    LMEntry('oc.cost',     'oc.cost',                 'token usage + cost summary'),
    LMEntry('oc.update',   'oc.update',               'check for / run openclaw update'),
]

OC_COMMANDS = {
    'status':   ['openclaw', 'status'],
    'gw':       ['openclaw', 'gateway'],
    'cron':     ['openclaw', 'cron'],
    'sessions': ['openclaw', 'sessions', 'list'],
    'logs':     ['openclaw', 'logs'],
    'doctor':   ['openclaw', 'doctor'],
    'cost':     ['openclaw', 'gateway', 'health'],
    'update':   ['openclaw', 'gateway', 'update.run'],
}


def execute_oc(sub: str, args: list[str]) -> str:
    """Execute an oc.* command. Returns output string."""
    base = OC_COMMANDS.get(sub)
    if not base:
        available = ', '.join(sorted(OC_COMMANDS.keys()))
        return f"Unknown: oc.{sub}. Available: {available}"
    cmd = base + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        output = result.stdout
        if result.stderr:
            output += f"\n⚠️ {result.stderr[:500]}"
        return output or '(no output)'
    except subprocess.TimeoutExpired:
        return f"⏰ oc.{sub} timed out after {TIMEOUT}s"
    except FileNotFoundError:
        return f"⚠️ 'openclaw' not found in PATH"


# ═══════════════════════════════════════════════════════════════════════════
# D2: sys.* — System Tools (FLAG-2 fix: shlex.quote on all args)
# ═══════════════════════════════════════════════════════════════════════════

SYS_ENTRIES = [
    LMEntry('sys.ps',    'sys.ps [pattern]',         'process listing (ps aux | grep)'),
    LMEntry('sys.kill',  'sys.kill {pid}',           'kill process by PID'),
    LMEntry('sys.svc',   'sys.svc {name} [cmd]',    'systemd --user start|stop|restart|status'),
    LMEntry('sys.grep',  'sys.grep {pat} [path]',   'pattern search in workspace'),
    LMEntry('sys.find',  'sys.find {name}',          'file discovery in workspace'),
    LMEntry('sys.tail',  'sys.tail {file} [n]',      'last N lines of file'),
    LMEntry('sys.disk',  'sys.disk [path]',          'disk usage (df -h, du -sh)'),
    LMEntry('sys.curl',  'sys.curl {url}',           'HTTP GET (health checks)'),
    LMEntry('sys.net',   'sys.net [port]',           'port/connection check (ss)'),
    LMEntry('sys.top',   'sys.top',                  'resource snapshot (CPU/mem/disk)'),
    LMEntry('sys.git',   'sys.git {cmd}',            'git operations in main workspace'),
]

# Commands that need shell (pipes) — use shlex.quote on args (FLAG-2 fix)
def _sys_cmd(sub: str, args: list[str]) -> tuple[str, bool]:
    """Return (command_string, needs_shell). Uses shlex.quote for safety."""
    q = shlex.quote  # shorthand

    if sub == 'ps':
        return (f'ps aux | grep -i {q(args[0])}' if args
                else 'ps aux --sort=-%mem | head -20'), True
    elif sub == 'kill':
        if not args:
            return 'echo "Usage: sys.kill <pid>"', True
        # Only allow numeric PIDs for kill
        if args[0].isdigit():
            return f'kill {args[0]}', True
        return f'echo "sys.kill: expected numeric PID, got {q(args[0])}"', True
    elif sub == 'svc':
        if not args:
            return 'systemctl --user list-units --type=service', True
        svc_name = q(args[0])
        action = q(args[1]) if len(args) > 1 else 'status'
        return f'systemctl --user {action} {svc_name}', True
    elif sub == 'grep':
        if not args:
            return 'echo "Usage: sys.grep <pattern> [path]"', True
        pat = q(args[0])
        path = q(args[1]) if len(args) > 1 else 'scripts/'
        return f'grep -rn {pat} {path}', True
    elif sub == 'find':
        if not args:
            return 'echo "Usage: sys.find <name>"', True
        return f'find . -name {q("*" + args[0] + "*")} -not -path "*/.git/*"', True
    elif sub == 'tail':
        if not args:
            return 'echo "Usage: sys.tail <file> [n]"', True
        n = args[1] if len(args) > 1 and args[1].isdigit() else '20'
        return f'tail -n {n} {q(args[0])}', True
    elif sub == 'disk':
        return (f'du -sh {q(args[0])}' if args else 'df -h'), True
    elif sub == 'curl':
        if not args:
            return 'echo "Usage: sys.curl <url>"', True
        return f'curl -sf {q(args[0])}', True
    elif sub == 'net':
        return (f'ss -tlnp | grep {q(args[0])}' if args else 'ss -tlnp'), True
    elif sub == 'top':
        return ('echo "=== CPU ===" && uptime && echo "=== MEM ===" && free -h '
                '&& echo "=== DISK ===" && df -h /'), True
    elif sub == 'git':
        # Run in main workspace (FLAG-5 fix: agent workspaces aren't git repos)
        return (f'git {" ".join(q(a) for a in args)}' if args else 'git status'), True
    else:
        return '', False


def execute_sys(sub: str, args: list[str]) -> str:
    """Execute a sys.* command via shell."""
    cmd_str, needs_shell = _sys_cmd(sub, args)
    if not cmd_str:
        available = ', '.join(sorted(e.verb.split('.')[1] for e in SYS_ENTRIES))
        return f"Unknown: sys.{sub}. Available: {available}"
    try:
        # Use main workspace for git commands (FLAG-5 fix)
        cwd = str(MAIN_WORKSPACE) if sub == 'git' else str(WORKSPACE)
        result = subprocess.run(
            cmd_str, shell=needs_shell, capture_output=True, text=True,
            timeout=TIMEOUT, cwd=cwd
        )
        output = result.stdout[:4000]
        if result.stderr:
            output += f"\n⚠️ {result.stderr[:500]}"
        return output or '(no output)'
    except subprocess.TimeoutExpired:
        return f"⏰ sys.{sub} timed out after {TIMEOUT}s"


# ═══════════════════════════════════════════════════════════════════════════
# D3: sc.* — Scaffolded Writes (renamed from e2.* per FLAG-3 to avoid
#     collision with e2 create mode)
# ═══════════════════════════════════════════════════════════════════════════

SC_ENTRIES = [
    LMEntry('sc.script',   'sc.script {name}',        'new script with argparse + logging'),
    LMEntry('sc.cron',     'sc.cron {name} {sched}',  'cron job: script + crontab entry'),
    LMEntry('sc.skill',    'sc.skill {name}',         'skill directory: SKILL.md + scripts/'),
    LMEntry('sc.pipeline', 'sc.pipeline {name}',      'pipeline with state + frontmatter'),
]


def scaffold_script(name: str, workspace: Path) -> str:
    """Create scripts/{name}.py with standard boilerplate."""
    path = workspace / 'scripts' / f'{name}.py'
    if path.exists():
        return f"⚠️ {path.relative_to(workspace)} already exists"

    path.write_text(f'''#!/usr/bin/env python3
"""{name} — [description]

Usage: python3 scripts/{name}.py [args]
"""

import argparse
import logging
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='{name}')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    logger.info(f'Running {name}...')
    # TODO: implement


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    main()
''', encoding='utf-8')
    path.chmod(0o755)
    return f"✅ Created {path.relative_to(workspace)}"


def scaffold_skill(name: str, workspace: Path) -> str:
    """Create skill directory with SKILL.md template."""
    skill_dir = workspace / 'skills' / name
    if skill_dir.exists():
        return f"⚠️ skills/{name}/ already exists"

    skill_dir.mkdir(parents=True)
    (skill_dir / 'scripts').mkdir()
    (skill_dir / 'references').mkdir()
    (skill_dir / 'SKILL.md').write_text(f'''# {name}

## Description
[What does this skill do?]

## When to Use
[Trigger conditions]

## Steps
1. [Step 1]
2. [Step 2]

## References
See `references/` directory.
''', encoding='utf-8')
    return f"✅ Created skills/{name}/ (SKILL.md + scripts/ + references/)"


def scaffold_pipeline(name: str, workspace: Path) -> str:
    """Create pipeline via existing launch_pipeline.py script."""
    try:
        result = subprocess.run(
            [sys.executable, str(workspace / 'scripts' / 'launch_pipeline.py'),
             name, '--desc', name.replace('-', ' '), '--priority', 'high'],
            capture_output=True, text=True, timeout=30, cwd=str(workspace)
        )
        if result.returncode == 0:
            return f"✅ Pipeline {name} created\n{result.stdout[:500]}"
        return f"⚠️ {result.stderr[:500]}"
    except Exception as e:
        return f"⚠️ Failed: {e}"


def scaffold_cron(name: str, args: list[str], workspace: Path) -> str:
    """Create a script + placeholder cron schedule."""
    # First scaffold the script
    script_result = scaffold_script(name, workspace)
    schedule = args[0] if args else '0 * * * *'
    return (f"{script_result}\n"
            f"📅 Schedule: {schedule}\n"
            f"Add via: oc.cron add --name {name} --schedule '{schedule}' "
            f"--cmd 'python3 scripts/{name}.py'")


def execute_scaffold(sub: str, args: list[str], workspace: Path = None) -> str:
    """Execute a sc.* scaffold command."""
    ws = workspace or WORKSPACE
    if not args:
        return f"Usage: sc.{sub} <name>"

    name = args[0]
    remaining = args[1:]

    if sub == 'script':
        return scaffold_script(name, ws)
    elif sub == 'skill':
        return scaffold_skill(name, ws)
    elif sub == 'pipeline':
        return scaffold_pipeline(name, ws)
    elif sub == 'cron':
        return scaffold_cron(name, remaining, ws)
    else:
        available = ', '.join(e.verb.split('.')[1] for e in SC_ENTRIES)
        return f"Unknown: sc.{sub}. Available: {available}"


# ═══════════════════════════════════════════════════════════════════════════
# D4: r.* — Formatted Read Commands
# ═══════════════════════════════════════════════════════════════════════════

R_ENTRIES = [
    LMEntry('r.health',  'r.health',          'gateway + render engine + experiment status'),
    LMEntry('r.cost',    'r.cost',            'token usage + cost across sessions'),
    LMEntry('r.recent',  'r.recent [n]',      'last N changes across all namespaces'),
]


def execute_read(sub: str, args: list[str]) -> str:
    """Execute an r.* read command."""
    if sub == 'health':
        parts = []
        # Gateway health
        try:
            gw = subprocess.run(['openclaw', 'gateway', 'health'],
                                capture_output=True, text=True, timeout=10)
            parts.append(f"## Gateway\n{gw.stdout[:500] or 'No response'}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            parts.append("## Gateway\n⏰ Timed out")
        # Render engine
        sock = WORKSPACE / '.codex_runtime' / 'render.sock'
        parts.append(f"## Render Engine\n{'✅ Running' if sock.exists() else '❌ Not running'}")
        # Experiments
        builds_dir = WORKSPACE / 'pipeline_builds'
        if builds_dir.exists():
            pids = list(builds_dir.glob('*_experiment.pid'))
            parts.append(f"## Experiments\n{len(pids)} running")
        return '\n\n'.join(parts)

    elif sub == 'cost':
        try:
            cost = subprocess.run(['openclaw', 'gateway', 'health'],
                                  capture_output=True, text=True, timeout=10)
            return cost.stdout or '(no cost data)'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return '⏰ Cost query timed out'

    elif sub == 'recent':
        n = int(args[0]) if args and args[0].isdigit() else 10
        # Use main workspace which IS a git repo (FLAG-5 fix)
        try:
            log = subprocess.run(
                ['git', 'log', '--oneline', f'-{n}', '--',
                 'tasks/', 'pipelines/', 'decisions/', 'lessons/'],
                capture_output=True, text=True, timeout=10,
                cwd=str(MAIN_WORKSPACE)
            )
            return log.stdout or '(no recent changes)'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return '⚠️ git not available or not in a repo'

    else:
        available = ', '.join(e.verb.split('.')[1] for e in R_ENTRIES)
        return f"Unknown: r.{sub}. Available: {available}"


# ═══════════════════════════════════════════════════════════════════════════
# D5: Unified Dispatch + D7: Registration
# ═══════════════════════════════════════════════════════════════════════════

PLATFORM_PREFIXES = {'oc', 'sys', 'r', 'sc'}


def execute_platform(prefix: str, sub: str, args: list[str]) -> str:
    """Unified dispatch for all platform namespaces."""
    if prefix == 'oc':
        return execute_oc(sub, args)
    elif prefix == 'sys':
        return execute_sys(sub, args)
    elif prefix == 'sc':
        return execute_scaffold(sub, args)
    elif prefix == 'r':
        return execute_read(sub, args)
    else:
        return f"Unknown prefix: {prefix}. Available: {', '.join(sorted(PLATFORM_PREFIXES))}"


def scan_platform_entries(workspace: Path = None) -> list[LMEntry]:
    """Return all platform entries for LM renderer registration."""
    return OC_ENTRIES + SYS_ENTRIES + SC_ENTRIES + R_ENTRIES


def is_platform_command(text: str) -> bool:
    """Check if text starts with a platform prefix (oc.*, sys.*, sc.*, r.*)."""
    if '.' not in text:
        return False
    prefix = text.split('.', 1)[0].lower()
    return prefix in PLATFORM_PREFIXES
