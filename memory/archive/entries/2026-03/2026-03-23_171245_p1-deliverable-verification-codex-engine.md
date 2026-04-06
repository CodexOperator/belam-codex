---
primitive: memory_log
timestamp: "2026-03-23T17:12:45Z"
category: event
importance: 3
tags: [instance:main, p1, codex-engine, lm, bug-fix]
source: "session"
content: "p1 deliverable verification (codex-engine-v3-legendary-map): 2 bugs found and fixed. (1) is_coordinate() used [a-z] single-char regex — 'lm' is 2 chars so lm6 zoom and lm expanded view silently exited code 2. Fixed by updating regex to support multi-char prefixes. (2) Dot-syntax e0.l1/e1.l1 workflow dispatch never reached any handler — not a V2 op (no [a-z] after e0 per V2_OP_START_RE), not a coordinate (is_coordinate rejected it). Fixed by adding early dispatch intercept before V2 detection block. Both fixes committed as 68feb520 to belam-codex."
status: consolidated
---

# Memory Entry

**2026-03-23T17:12:45Z** · `event` · importance 3/5

p1 deliverable verification (codex-engine-v3-legendary-map): 2 bugs found and fixed. (1) is_coordinate() used [a-z] single-char regex — 'lm' is 2 chars so lm6 zoom and lm expanded view silently exited code 2. Fixed by updating regex to support multi-char prefixes. (2) Dot-syntax e0.l1/e1.l1 workflow dispatch never reached any handler — not a V2 op (no [a-z] after e0 per V2_OP_START_RE), not a coordinate (is_coordinate rejected it). Fixed by adding early dispatch intercept before V2 detection block. Both fixes committed as 68feb520 to belam-codex.

---
*Source: session*
*Tags: instance:main, p1, codex-engine, lm, bug-fix*
