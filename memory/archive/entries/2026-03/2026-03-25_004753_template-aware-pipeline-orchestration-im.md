---
primitive: memory_log
timestamp: "2026-03-25T00:47:53Z"
category: event
importance: 3
tags: [instance:main, templates, pipelines, orchestration, builder-first]
source: "session"
content: "Template-aware pipeline orchestration implemented: scripts/template_parser.py created to parse YAML transitions from template markdown files. pipeline_update.py, pipeline_orchestrate.py, and launch_pipeline.py updated to use dynamic transition resolution based on pipeline type field. Builder-first pipelines now correctly dispatch to builder on kickoff (not architect). Backward compatible — research type falls through to hardcoded dicts. 11/11 tests passing."
status: consolidated
---

# Memory Entry

**2026-03-25T00:47:53Z** · `event` · importance 3/5

Template-aware pipeline orchestration implemented: scripts/template_parser.py created to parse YAML transitions from template markdown files. pipeline_update.py, pipeline_orchestrate.py, and launch_pipeline.py updated to use dynamic transition resolution based on pipeline type field. Builder-first pipelines now correctly dispatch to builder on kickoff (not architect). Backward compatible — research type falls through to hardcoded dicts. 11/11 tests passing.

---
*Source: session*
*Tags: instance:main, templates, pipelines, orchestration, builder-first*
