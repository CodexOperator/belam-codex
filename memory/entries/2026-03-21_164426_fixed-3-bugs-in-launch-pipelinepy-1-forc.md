---
primitive: memory_log
timestamp: "2026-03-21T16:44:26Z"
category: technical
importance: 2
tags: [instance:main, bugfix, infrastructure, launch-pipeline]
source: "session"
content: "Fixed 3 bugs in launch_pipeline.py: (1) --force flag printed in error message but not wired into argparse — now wired + skips gate with warning, (2) phase1_complete not in archivable statuses — added so infrastructure pipelines skipping Phase 2/3 can archive cleanly, (3) operator precedence bug in check_archivable (or not binding to status check). Pushed as commit a25db37."
status: active
---

# Memory Entry

**2026-03-21T16:44:26Z** · `technical` · importance 2/5

Fixed 3 bugs in launch_pipeline.py: (1) --force flag printed in error message but not wired into argparse — now wired + skips gate with warning, (2) phase1_complete not in archivable statuses — added so infrastructure pipelines skipping Phase 2/3 can archive cleanly, (3) operator precedence bug in check_archivable (or not binding to status check). Pushed as commit a25db37.

---
*Source: session*
*Tags: instance:main, bugfix, infrastructure, launch-pipeline*
