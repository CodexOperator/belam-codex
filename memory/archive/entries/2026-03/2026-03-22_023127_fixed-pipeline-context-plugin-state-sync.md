---
primitive: memory_log
timestamp: "2026-03-22T02:31:27Z"
category: technical
importance: 3
tags: [instance:main, pipeline, bug-fix, infrastructure]
source: "session"
content: "Fixed pipeline-context plugin state sync bug: pipeline .md files had status: archived but _state.json files in pipeline_builds/ were never updated by the archive function. The pipeline-context plugin reads _state.json, so archived pipelines (orch-v1, orch-v2, build-equilibrium-snn, stack-specialists, v4, v4-deep-analysis) were still showing as active. Fixed 6 stale state JSONs and patched launch_pipeline.py archive function to sync _state.json on archive."
status: consolidated
---

# Memory Entry

**2026-03-22T02:31:27Z** · `technical` · importance 3/5

Fixed pipeline-context plugin state sync bug: pipeline .md files had status: archived but _state.json files in pipeline_builds/ were never updated by the archive function. The pipeline-context plugin reads _state.json, so archived pipelines (orch-v1, orch-v2, build-equilibrium-snn, stack-specialists, v4, v4-deep-analysis) were still showing as active. Fixed 6 stale state JSONs and patched launch_pipeline.py archive function to sync _state.json on archive.

---
*Source: session*
*Tags: instance:main, pipeline, bug-fix, infrastructure*
