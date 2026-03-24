---
primitive: task
status: in_pipeline
priority: high
created: 2026-03-24
owner: belam
project: multi-agent-infrastructure
depends_on: []
upstream: [containerize-openclaw-workspace]
downstream: []
tags: [docker, infrastructure, disaster-recovery, testing]
pipeline: container-build-and-test
---

# Container Build & Test: Disaster Recovery Validation

## Description

The containerize-openclaw-workspace pipeline produced Dockerfile, docker-compose.yml, .dockerignore, and requirements files. This task validates they actually work by building the image, running it, and verifying core functionality.

## Scope

1. `docker build` the workspace image — fix any build errors
2. `docker compose up` — verify gateway starts and responds on port 18789
3. Verify agent dispatch works inside the container (mock dispatch test)
4. Verify workspace volume mounts are correct (primitives, scripts, config accessible)
5. Write a disaster recovery runbook: `docs/disaster-recovery.md`
   - Steps to restore from GitHub repos + Docker image
   - Estimated recovery time
   - What's preserved (code, primitives, memory) vs what's lost (active sessions, PID state)
6. Document how to update containers with new features (rebuild flow)

## Success Criteria

- Image builds without errors
- Gateway starts and accepts connections
- Agent dispatch completes at least one mock task
- Recovery runbook exists and is tested
- Container update workflow documented

## Notes

- Do NOT replace current local setup — this is parallel/backup
- ARM64 (Oracle aarch64) — verify image works on this architecture
