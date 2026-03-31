---
primitive: lesson
date: 2026-03-15
source: builder agent (v4 pipeline build)
confidence: high
project: snn-applied-finance
tags: [pipeline, infrastructure, markdown, debugging]
applies_to: [pipeline_update.py, pipeline primitives]
promotion_status: exploratory
doctrine_richness: 6
contradicts: []
---

# Pipeline Table Separator Required for Update Script

`pipeline_update.py` parses stage history tables by looking for `| Stage |` followed immediately by a `|---|---|---|---|` separator row on the next line. If the markdown separator row is missing, the parser silently fails and only updates the state JSON — the markdown file gets no stage history entries.

## Symptoms
- `pipeline_update.py <version> show` works (reads JSON state)
- But `pipelines/<version>.md` stage history table stays empty
- No error message — silent fallback to JSON-only update

## Fix
Ensure every pipeline markdown file has the full table header:

```markdown
| Stage | Status | Agent | Timestamp |
|---|---|---|---|
```

## Prevention
- The pipeline template (`templates/pipeline.md`) should include the separator row
- When creating new pipeline primitives, verify table structure before first update
- Consider hardening `pipeline_update.py` to warn (not silently skip) when separator is missing
