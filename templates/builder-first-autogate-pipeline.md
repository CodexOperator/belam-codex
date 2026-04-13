# Builder-First Pipeline Template (Auto Phase 1 Gate)

Variant of builder-first-pipeline where Phase 1 auto-advances to Phase 2.
Used for research analysis tasks where critic review → architect refinement → builder revision
is the expected flow before reaching a human gate.

## Flow

```
Phase 1: Builder (implement) → Builder (bugfix) → Critic (review) → [AUTO GATE → Phase 2]
Phase 2: Architect (design) → Builder (implement) → Builder (bugfix) → Critic (review) → [HUMAN GATE]
Phase 3: Architect (design) → Builder (implement) → Builder (bugfix) → Critic (review) → [HUMAN GATE]
```

## Stage Transitions
<!-- machine-readable: parsed by template_parser.py -->
```yaml
first_agent: builder
type: builder-first-autogate
runtime:
  platform: hermes
  dispatch_tool: delegate_task
  codex_cli_enabled: true
  roles:
    architect: { toolsets: [terminal, file, web, skills] }
    builder: { toolsets: [terminal, file, skills] }
    critic: { toolsets: [file, terminal] }

phases:
  1:
    stages:
      - { role: builder, action: implement, session: fresh }
      - { role: builder, action: bugfix, session: continue }
      - { role: critic, action: review, session: fresh }
    gate: auto

  2:
    stages:
      - { role: architect, action: design, session: fresh }
      - { role: builder, action: implement, session: fresh }
      - { role: builder, action: bugfix, session: continue }
      - { role: critic, action: review, session: fresh }
    gate: human

  3:
    stages:
      - { role: architect, action: design, session: fresh }
      - { role: builder, action: implement, session: fresh }
      - { role: builder, action: bugfix, session: continue }
      - { role: critic, action: review, session: fresh }
    gate: human

block_routing:
  critic:
    review: { agent: builder, session: continue }

auto_complete_on_clean_pass: false

complete_task_agent: architect
```

## Human Gates

Only `p2_complete` and `p3_complete` are human gates. Phase 1 auto-advances to Phase 2 when the critic approves.
