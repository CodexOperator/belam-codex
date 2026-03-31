---
primitive: lesson
date: 2026-03-24
source: main session 36029da4
confidence: confirmed
upstream: []
downstream: []
tags: [instance:main, openclaw, install, path, gateway]
importance: 3
promotion_status: candidate
doctrine_richness: 8
contradicts: []
---

# openclaw-dual-install-path-conflict

## Context

Shael reported gateway freezing and Telegram unreachability. After investigation, OpenClaw was found to be on a stale version (2026.3.12) despite the user running the installer (which installed 2026.3.23-1).

## What Happened

The installer placed the new version in `~/.npm-global/lib/node_modules/openclaw` but `/usr/bin/openclaw` was a symlink to the old global install at `/usr/lib/node_modules/openclaw`. The old version won in PATH, so `openclaw --version` still showed 2026.3.12. `sudo npm rm -g openclaw` failed with ENOTEMPTY. Fix was `sudo rm -rf /usr/lib/node_modules/openclaw && sudo rm -f /usr/bin/openclaw`, then adding `~/.npm-global/bin` to PATH via `.bashrc`.

## Lesson

When the OpenClaw installer installs to `~/.npm-global` but a system-level install exists at `/usr/lib/node_modules/openclaw`, the old system install will shadow the new one. `npm rm -g` may fail; manual `sudo rm -rf` of the old path is the reliable fix.

## Application

If `openclaw --version` doesn't match the installer output after an update, check for a dual install: `which -a openclaw`. If `/usr/bin/openclaw` exists alongside `~/.npm-global/bin/openclaw`, remove the system one manually and ensure `~/.npm-global/bin` is in PATH.
