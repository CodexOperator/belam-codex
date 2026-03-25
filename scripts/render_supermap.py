#!/usr/bin/env python3
"""Render supermap to stdout. No daemon, no sockets, no files."""

import os
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(WORKSPACE / 'scripts'))
os.chdir(str(WORKSPACE))
from codex_engine import render_supermap

def main():
    sys.stdout.write(render_supermap())

if __name__ == '__main__':
    main()
