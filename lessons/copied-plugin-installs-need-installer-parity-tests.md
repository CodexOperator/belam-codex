---
primitive: lesson
date: 2026-04-16
source: session 20260416_181555_298688bb
confidence: confirmed
upstream: []
downstream: []
tags: [instance:main, hermes, plugins, install, testing, drift]
importance: 3
promotion_status: candidate
doctrine_richness: 8
contradicts: []
---

# copied-plugin-installs-need-installer-parity-tests

## Context

The Hermes `openclaw_hooks` plugin was behaving as if it still used an old spawn path even though the repo-local source had already been updated.

## What Happened

The live plugin under `~/.hermes/plugins/openclaw_hooks` was a copied install, not a symlink to `local_plugins/openclaw_hooks`. The repo source changed later, but the installer was not re-run, so the installed copy drifted. Existing tests exercised the repo-local plugin source only, which left the installed runtime copy unverified and let the mismatch stay invisible.

## Lesson

When runtime plugins are installed by copying files out of the repo, test coverage on source files alone is not enough. The installer needs a parity test that installs into a temp target and asserts the installed copy matches the repo source.

## Application

For any copied plugin or extension install path, add a focused installer-parity test and use it as the drift tripwire. When behavior differs between repo source and live runtime, check the installed copy first and re-run the installer before chasing logic bugs.
