---
primitive: memory_log
timestamp: "2026-03-21T06:57:33Z"
category: technical
importance: 5
tags: [instance:main, codex-engine, v2, coordinates, grammar, tokenizer, attention, dense-mode, alphanumeric]
source: "session:e563bfbc"
content: "Major Codex Engine V2 coordinate grammar design session with Shael. Finalized dense alphanumeric as the canonical format: e0p3 e1t12 (no separator between namespace+index, spaces only between operations). Ran empirical tokenizer tests: all separators (dot, colon, slash, hyphen) cost same 16 tokens on 4-op chain; dense = 14 tokens; dense numeric = 11 tokens but bad attention signal (model fights arithmetic priors). Alphanumeric wins because token IDs (e=68, p=79, t=83) fire attention patterns associated with symbolic references/identifiers, not arithmetic. Engine mode namespace: e0=orchestrate, e1=edit, e2=create, e3=extend. Flags remain as view modifiers (camera angles) orthogonal to coordinate operations. 'Large alphanumeric model' framing coined by Shael."
status: consolidated
---

# Memory Entry

**2026-03-21T06:57:33Z** · `technical` · importance 5/5

Major Codex Engine V2 coordinate grammar design session with Shael. Finalized dense alphanumeric as the canonical format: e0p3 e1t12 (no separator between namespace+index, spaces only between operations). Ran empirical tokenizer tests: all separators (dot, colon, slash, hyphen) cost same 16 tokens on 4-op chain; dense = 14 tokens; dense numeric = 11 tokens but bad attention signal (model fights arithmetic priors). Alphanumeric wins because token IDs (e=68, p=79, t=83) fire attention patterns associated with symbolic references/identifiers, not arithmetic. Engine mode namespace: e0=orchestrate, e1=edit, e2=create, e3=extend. Flags remain as view modifiers (camera angles) orthogonal to coordinate operations. 'Large alphanumeric model' framing coined by Shael.

---
*Source: session:e563bfbc*
*Tags: instance:main, codex-engine, v2, coordinates, grammar, tokenizer, attention, dense-mode, alphanumeric*
