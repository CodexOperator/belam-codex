---
primitive: decision
importance: 4
tags: [instance:main, containerization, infrastructure, safety, architecture]
related: [containerization-must-use-isolated-build-directory, infrastructure-pipeline-must-not-modify-live-host]
created: 2026-03-24
---

# Containerization: Isolated Build Directory Pattern

## Decision

All containerization build work must happen in an isolated temporary directory (e.g. `/tmp/container-build/`) that is separate from the live workspace. The directory is deleted after the image is confirmed working. The live workspace is never modified during a container build pipeline.

## Rationale

The prior approach (running container build logic on the live host, including sudo Docker install) caused the gateway to shut down and PATH to lose the `openclaw` entry. The runtime cannot safely build a container of itself without isolation.

## Architecture

1. Build agent writes all files to `/tmp/container-build/` (or `~/Desktop/container-build/`)
2. Docker build runs from that isolated directory
3. Live workspace is `COPY`-ed into the image at build time — not bind-mounted
4. On success: image confirmed working → tmp dir deleted
5. On failure: tmp dir preserved for debugging, pipeline pauses for human review

## Full Containerization Spec (from Shael, 2026-03-24)

- **Self-contained image**: bake workspace via `COPY` or `git clone` at build time (no bind-mounts)
- **Multi-process**: supervisord/s6 to run gateway + codex-render + cron inside one container
- **Secrets**: via env vars or runtime secrets, not host files baked in
- **Persistent volumes**: for state (workspace edits, memory files)
- **One-command rebuild**: single script to build + test + push
- **Pinned deps**: all requirements files locked to exact versions

## Status

Task `container-build-and-test` reset to open, priority lowered to low — deferred until higher-priority engine work clears.
