# Ticket Context: GH-8 — feat: Plotly bubble chart and visual polish

**Issue:** https://github.com/707/ml-workbench/issues/8
**Status:** planning-complete
**Last Updated:** 2026-03-25
**Last Agent:** claude-code
**Last Phase:** plan

---

## Summary
Add an interactive Plotly bubble chart to the Token Tax Dashboard showing cost vs quality risk vs traffic share. Apply visual refinements across new tabs.

## Confirmed Plan

### Step 1: Add plotly dependency
- Update `workbench/pyproject.toml`: add `"plotly>=5.18"` to dependencies
- Update `workbench/requirements.txt`: add `plotly`

### Step 2: Write failing tests for `build_bubble_chart`
**File:** `workbench/test_token_tax_ui.py`
- `TestBuildBubbleChart`:
  - Returns a `plotly.graph_objects.Figure` instance
  - Figure has data traces (not empty)
  - Trace type is scatter (bubble = scatter with size mapping)
  - Handles empty analysis_results gracefully (returns empty figure with message)
  - Handles single-model results (no crash)

### Step 3: Implement `build_bubble_chart`
**File:** `workbench/token_tax_ui.py`
```python
import plotly.graph_objects as go

def build_bubble_chart(analysis_results: list[dict]) -> go.Figure:
    """Bubble chart: x=RTC, y=monthly_cost, size=token_count, color=risk_level.

    Risk level colors:
    - low: #4CAF50 (green)
    - moderate: #FF9800 (orange)
    - high: #F44336 (red)
    - severe: #9C27B0 (purple)
    """
```
- Use `go.Scatter` with `mode="markers"`, `marker=dict(size=..., color=...)`
- Layout: x-axis "Relative Tokenization Cost (vs English)", y-axis "Estimated Monthly Cost ($)"
- Hover template: model name, token count, RTC, risk level

### Step 4: Wire bubble chart into Dashboard UI
- In `token_tax_ui.py`, add `gr.Plot()` component after the bar chart
- Update the dashboard handler to call `build_bubble_chart(results)` and return figure to the Plot component
- Update smoke tests to verify Plot component receives a figure

### Step 5: Visual polish
- Review all new tabs for consistent styling:
  - Consistent heading hierarchy (## for sections, ### for sub-sections)
  - Consistent spacing in Markdown stats
  - Ensure dark mode readability (same as tokenizer.py's `color:#000` pattern for highlighted elements)
  - Add descriptive tooltips/info text for non-obvious metrics (RTC, byte premium)
- Add `gr.Markdown` explainer at top of Token Tax Dashboard: brief description of what the tool does and why it matters (2-3 sentences, citing the research)

## Files to Read Before Starting
- `workbench/token_tax_ui.py` — the dashboard UI to extend (created in GH-5)
- `workbench/test_token_tax_ui.py` — existing smoke tests to extend
- `workbench/tokenizer.py` lines 200-330 — `render_tokens_html` for styling patterns (alternating colors, dark mode)
- `workbench/pyproject.toml` — current deps to add plotly

## Current State

### Completed
(none)

### In Progress
(none)

### Blocked By
- GH-5 (Token Tax Dashboard must exist)

## Implementation Notes
- `gr.Plot()` in Gradio 6.8.0 accepts a Plotly figure directly — no HTML conversion needed
- Plotly is a heavy dependency (~15MB) but acceptable for the value it provides
- Bubble size should be proportional to token_count (not linear — use sqrt scaling for visual balance)
- Color mapping for risk levels should be colorblind-friendly
- Test with `import plotly.graph_objects as go` — if plotly isn't installed, tests should skip gracefully or the dependency must be added first
- Keep `build_bubble_chart` as a pure function (data in → figure out) for easy testing
- The bubble chart is most useful when 3+ models are compared; for 1-2 models it's less informative — consider showing a note instead
