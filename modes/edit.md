---
primitive: mode
status: active
coordinate: e1
function: edit
applicable_namespaces: [p, t, d, l, w, k, s, m, md, mw, c]
tags: [engine, mode, v2]
description: Edit primitive fields and body content with F-label tracking
---

## e1 — Edit Mode

Edits frontmatter fields or body content of any primitive.
All changes are tracked with F-labels and are undoable via e-z (or -z).

### Usage
  e1 <coord> <field_num> <value>  — set a frontmatter field
  e1 <coord> B  <text>            — replace entire body
  e1 <coord> B+ <text>            — append to body
  e1 <coord> B5 <text>            — replace body line 5
  e1 <coord> B5-10 <text>         — replace body lines 5-10
  e1 <coord> B.Section <text>     — replace ## Section content
  e1                              — show this help

### Dense Form
  e1t1 2 active                   — edit task 1, field 2 = active
  e1p3 B+ "new content"           — append to pipeline 3 body

### Routing
Maps to execute_edit() — all V1 -e flag behaviour applies.
