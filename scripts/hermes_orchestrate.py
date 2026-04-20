#!/usr/bin/env python3
"""Hermes orchestration entry point (slice 1).

Replaces the implicit "invoke orchestration_engine.py directly" pattern with
a named entry point that routes subcommands into the engine and the slice-1
adapter pipeline. The old entry point stays functional as a thin wrapper
during the transition.

Subcommands:
  dispatch VERSION STAGE AGENT [--message TEXT]
      Run the CLI-agnostic adapter dispatch path.
  resolve STAGE ROLE [--phase PKEY]
      Print the resolved runtime dict for the requested stage (JSON).
  registry [CLI]
      Dump the registry or a single resolved CLI spec.
  questions VERSION [--list|--ask STAGE AGENT TEXT]
      Worker-question relay helper.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make sibling modules importable regardless of cwd.
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import agent_questions  # noqa: E402
import cli_registry  # noqa: E402
import dispatch_adapters  # noqa: E402
import runtime_resolution  # noqa: E402


def cmd_dispatch(args: argparse.Namespace) -> int:
    runtime = runtime_resolution.resolve_stage_runtime(
        stage_key=args.stage,
        role=args.agent,
        phase_key=args.phase,
    )
    result = dispatch_adapters.dispatch(
        version=args.version,
        stage=args.stage,
        agent=args.agent,
        runtime=runtime,
        message=args.message or "",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("success") else 1


def cmd_resolve(args: argparse.Namespace) -> int:
    runtime = runtime_resolution.resolve_stage_runtime(
        stage_key=args.stage,
        role=args.role,
        phase_key=args.phase,
    )
    print(json.dumps(runtime, indent=2, sort_keys=True))
    return 0


def cmd_registry(args: argparse.Namespace) -> int:
    reg = cli_registry.load_registry()
    if args.cli:
        print(json.dumps(cli_registry.resolve_cli_spec(args.cli, reg), indent=2, sort_keys=True))
    else:
        print(json.dumps({
            "schema_version": reg.get("schema_version"),
            "clis": cli_registry.list_clis(reg),
            "aliases": reg.get("aliases"),
            "defaults": reg.get("defaults"),
        }, indent=2, sort_keys=True))
    return 0


def cmd_questions(args: argparse.Namespace) -> int:
    if args.list:
        print(json.dumps(agent_questions.list_open_questions(args.version), indent=2))
        return 0
    if args.ask:
        stage, agent, text = args.ask
        path = agent_questions.write_question(
            version=args.version, stage=stage, agent=agent,
            cli=args.cli, question=text, relay=args.relay,
        )
        print(str(path))
        return 0
    print(json.dumps(agent_questions.list_open_questions(args.version), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="hermes_orchestrate")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("dispatch", help="Adapter-based dispatch for one stage")
    sp.add_argument("version")
    sp.add_argument("stage")
    sp.add_argument("agent")
    sp.add_argument("--message", default="")
    sp.add_argument("--phase", default=None)
    sp.set_defaults(func=cmd_dispatch)

    sp = sub.add_parser("resolve", help="Show resolved runtime for a stage")
    sp.add_argument("stage")
    sp.add_argument("role")
    sp.add_argument("--phase", default=None)
    sp.set_defaults(func=cmd_resolve)

    sp = sub.add_parser("registry", help="Inspect the CLI registry")
    sp.add_argument("cli", nargs="?", default=None)
    sp.set_defaults(func=cmd_registry)

    sp = sub.add_parser("questions", help="Worker question relay")
    sp.add_argument("version")
    sp.add_argument("--list", action="store_true")
    sp.add_argument("--ask", nargs=3, metavar=("STAGE", "AGENT", "TEXT"))
    sp.add_argument("--cli", default="claude")
    sp.add_argument("--relay", default="main_session")
    sp.set_defaults(func=cmd_questions)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
