---
primitive: lesson
severity: high
created: 2026-03-24
source: incident
tags: [infrastructure, docker, containerization, safety]
promotion_status: exploratory
doctrine_richness: 6
contradicts: []
---

# Containerization Must Use Isolated Build Directory

## Incident

Container-build-and-test pipeline attempted Docker installation and system modifications on the live host. This broke PATH, caused the gateway to shut down, and required manual recovery using the startup script reference.

## Lesson

Infrastructure pipelines that modify system packages, PATH, or install new runtimes must NEVER run on the live host directly. Containerization work specifically must:

1. **Use an isolated build directory** — `/tmp/container-build/` or `~/Desktop/container-build/` — not the workspace
2. **Copy files into the build dir** rather than operating in-place
3. **Delete the build dir** after the image is confirmed working
4. **Never install Docker or system packages via pipeline agents** — Docker must be pre-installed by the human, or the pipeline must detect and halt if missing

## Correct Pattern

```
1. mkdir /tmp/container-build/
2. Copy/clone workspace contents into build dir
3. Build Dockerfile, compose, configs in that directory
4. docker build + docker run from there
5. Verify health
6. Clean up: rm -rf /tmp/container-build/
```

The live workspace and gateway must remain untouched throughout the entire process.
