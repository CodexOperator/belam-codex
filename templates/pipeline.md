---
primitive: pipeline
fields:
  status:
    type: string
    required: true
    default: phase1_design
    enum: [phase1_design, phase1_critique, phase1_revision, phase1_build, phase1_code_review, phase1_complete, phase2_feedback, phase2_revision, phase2_rebuild, phase2_code_review, phase2_complete, archived]
  priority:
    type: string
    enum: [critical, high, medium, low]
  version:
    type: string
    required: true
  spec_file:
    type: string
  output_notebook:
    type: string
  agents:
    type: string[]
    description: "Agent IDs involved in this pipeline"
  tags:
    type: string[]
  project:
    type: string
    description: "Parent project primitive"
  started:
    type: date
  phase1_completed:
    type: date
  phase2_completed:
    type: date
  artifacts:
    type: object
    description: "Paths to pipeline artifacts (design, review, notebook)"
---
