---
primitive: task
status: open
priority: high
created: 2026-04-02
owner: belam
depends_on: []
upstream: []
downstream: []
tags: [education, visualization, web]
pipeline: interactive-decision-tree-kfold-visualizer
---

# Interactive Decision Tree & K-Fold Cross Validation Visualizer

## Description

Build an interactive single-page web application that visually demonstrates decision tree growing/pruning and k-fold cross validation. Serves on localhost on the VPS for browser access. Educational tool — clarity and interactivity are paramount.

**Stack:** Python backend (Flask or FastAPI) + scikit-learn for real ML computation. Frontend: HTML/CSS/JS with D3.js for tree visualization. Dark theme, Apple-scientific aesthetic — smooth animations, clean lines, uncluttered.

## Architecture

### Two Main Panels

**Panel 1: Decision Tree Visualizer**
- Animated D3.js tree that grows/prunes interactively
- Click nodes to split or prune individual branches
- Alpha (ccp_alpha) slider that controls complexity — tree branches animate in/out as alpha changes
- Branches fade and collapse as alpha increases, regrow as it decreases
- Show split criteria at each node (feature name, threshold)
- Color-code leaf nodes by predicted class

**Panel 2: K-Fold Cross Validation**
- Visual representation of dataset split into k folds (default k=5)
- Manual step-through with a "Next Fold" button — each click rotates which fold is validation vs training
- Animated fold highlighting: training folds in one color, validation fold in another
- Per-fold error bars update after each fold completes
- Shows how current tree complexity (alpha) affects train vs validation error across folds
- Running aggregate metrics (mean accuracy, std) update as folds complete

**Panel 3: Live Metrics Dashboard**
- Leaf count, tree depth, training error, validation error, alpha value
- All update in real-time as user interacts with the tree or steps through folds
- Clean gauge/number display — not charts, just live values

### Datasets (dropdown selector)

1. **Simple Color Dataset (default):**
   - Input: [10, 20, 30, 40, 50, 60]
   - Output: [red, red, blue, red, blue, blue]
   - Encoded as single feature X, binary classification (red=0, blue=1)
   - Intentionally minimalist for illustration

2. **Iris Dataset** (sklearn built-in, 2-class subset for simplicity)

3. **Synthetic 2D** (sklearn make_classification, 2 features so we can show decision boundaries)

### Interactions

- **Alpha slider:** drag to change ccp_alpha, tree updates live with animation
- **Grow button:** add one level of depth to current tree
- **Prune button:** remove deepest leaves
- **Next Fold button:** step to next k-fold iteration, retrain tree, update all metrics
- **Reset button:** return to initial state
- **Dataset dropdown:** switch between the 3 datasets, resets tree
- **k selector:** change number of folds (3, 5, 10)

### Visual Style

- **Dark theme** — dark background (#1a1a2e or similar), light text, accent colors for tree nodes
- **Apple-scientific aesthetic** — SF Pro-inspired typography (use system fonts), generous whitespace, subtle shadows
- **Smooth animations** — D3 transitions for tree growth/pruning (300-500ms easing)
- **Color palette:** muted blues and greens for training, warm amber/orange for validation, red/blue for class labels
- **No clutter** — every element earns its space

### Technical Requirements

- Python backend with Flask or FastAPI
- scikit-learn DecisionTreeClassifier for actual tree fitting
- API endpoints: `/api/fit` (fit tree with params), `/api/prune` (prune with alpha), `/api/kfold-step` (run one fold), `/api/tree` (get current tree structure), `/api/datasets` (list available datasets)
- D3.js v7 for tree rendering
- Single HTML page with inline or bundled JS/CSS (no build step needed)
- Serve on `0.0.0.0:8080` so it's accessible from browser
- All computation server-side; frontend is pure visualization

## Project Location

`/home/ubuntu/decision-tree-viz/` (git repo already initialized)

## Acceptance Criteria

- [ ] Flask/FastAPI server starts and serves the app on port 8080
- [ ] Decision tree renders as animated D3 visualization
- [ ] Alpha slider prunes/grows tree with smooth animation
- [ ] K-fold cross validation steps manually with button, showing fold assignments visually
- [ ] Per-fold and aggregate metrics display correctly
- [ ] All 3 datasets selectable via dropdown
- [ ] Dark theme with clean, scientific aesthetic
- [ ] Live metrics dashboard updates on every interaction
- [ ] Works in Chrome/Firefox on desktop

## Notes

- This is an educational tool for a machine learning class
- Clarity and interactivity are more important than feature count
- The simple color dataset is intentionally trivial — it's for demonstration
- Server runs on VPS, accessed via browser on localhost or VPS IP
