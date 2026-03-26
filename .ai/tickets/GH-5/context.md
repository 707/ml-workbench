# Ticket Context: GH-5 — feat: Token Tax Dashboard tab

**Issue:** https://github.com/707/ml-workbench/issues/5
**Status:** planning-complete
**Last Updated:** 2026-03-25
**Last Agent:** claude-code
**Last Phase:** plan

---

## Summary
New Gradio tab combining text input with multi-model cost analysis, bar charts, context window visualization, and actionable recommendations. The centerpiece feature of the Token Tax Calculator.

## Confirmed Plan

### Step 1: Write failing tests for `analyze_text_across_models`
**File:** `workbench/test_token_tax.py` (NEW)
- `TestAnalyzeTextAcrossModels`:
  - Returns list of dicts, one per model
  - Each dict has keys: model, token_count, rtc, byte_premium, context_usage, risk_level, cost_per_million, monthly_cost
  - Mock `get_tokenizer` and `tokenize_text` — no network calls
  - English text input: RTC = 1.0 for all models
  - Non-English with english_text provided: RTC > 1.0

### Step 2: Implement `analyze_text_across_models` in `token_tax.py`
**File:** `workbench/token_tax.py` (NEW)
```python
def analyze_text_across_models(
    text: str,
    english_text: str | None,
    model_names: list[str],
) -> list[dict]:
```
- For each model: load tokenizer, tokenize both texts, compute all metrics using GH-3 functions + GH-4 pricing
- Import from tokenizer.py: `get_tokenizer`, `tokenize_text`, `detect_language`, `relative_tokenization_cost`, `byte_premium`, `context_window_usage`, `quality_risk_level`
- Import from pricing.py: `get_pricing`

### Step 3: Write failing tests for `cost_projection`
- `TestCostProjection`:
  - Known inputs → expected monthly_cost, annual_cost
  - Zero requests → zero cost
  - Returns dict with monthly_cost and annual_cost keys

### Step 4: Implement `cost_projection`
```python
def cost_projection(
    token_count: int,
    price_per_million: float,
    monthly_requests: int,
    avg_tokens_per_request: int,
) -> dict:
```

### Step 5: Write failing tests for `generate_recommendations`
- `TestGenerateRecommendations`:
  - Returns non-empty string
  - Mentions the lowest-cost model name
  - Mentions risk level when any model is "high" or "severe"

### Step 6: Implement `generate_recommendations`
```python
def generate_recommendations(analysis_results: list[dict], language: str) -> str:
```
- Find cheapest model, flag high-risk models, suggest alternatives

### Step 7: Write failing smoke tests for UI
**File:** `workbench/test_token_tax_ui.py` (NEW)
- `TestBuildTokenTaxUI`: `build_token_tax_ui()` returns `gr.Blocks` without raising
- `TestDashboardHandler`: mock tokenizers + pricing, verify handler returns expected component count

### Step 8: Implement `build_token_tax_ui` in `token_tax_ui.py`
**File:** `workbench/token_tax_ui.py` (NEW)
- UI layout:
  1. `gr.Textbox` — input text
  2. `gr.Markdown` — auto-detected language badge
  3. `gr.Textbox` — English equivalent (auto-fills via `translate_to_english` when API key present, or manual paste)
  4. `gr.CheckboxGroup` — model multi-select (default: all)
  5. `gr.Textbox` — API key (collapsed accordion, same pattern as app.py)
  6. `gr.Button` — "Analyze"
  7. `gr.DataFrame` — cost table
  8. `gr.BarPlot` — token counts by model
  9. `gr.Markdown` — context window summary
  10. `gr.Markdown` — recommendations
  11. `gr.Accordion("Traffic Projections")` — monthly requests slider (100-1M), avg chars slider → projected costs

### Step 9: Wire into app.py
- Update `build_ui()` to import `build_token_tax_ui` and add as third tab
- `gr.TabbedInterface([comparison, tokenizer, token_tax], ["Model Comparison", "Tokenizer Inspector", "Token Tax Dashboard"])`
- Update `test_app.py`: `test_build_ui_returns_gradio_blocks` accepts 3-tab interface

## Files to Read Before Starting
- `workbench/tokenizer.py` — reuse `get_tokenizer`, `tokenize_text`, `detect_language`, `translate_to_english`, and GH-3 metric functions
- `workbench/pricing.py` — reuse `get_pricing`, `available_models` (created in GH-4)
- `workbench/app.py` — understand `build_ui()` tab composition pattern (lines 395-404)
- `workbench/openrouter.py` — `call_openrouter` used by `translate_to_english`
- `workbench/test_tokenizer.py` — follow test patterns, especially mock strategies for `AutoTokenizer.from_pretrained`

## Current State

### Completed
(none)

### In Progress
(none)

### Blocked By
- GH-3 (token tax metrics must exist in tokenizer.py)
- GH-4 (pricing.py must exist)

## Implementation Notes
- **Critical**: `build_ui()` in app.py currently returns `gr.TabbedInterface` with 2 tabs — adding a 3rd is straightforward but test assertions may need updating
- English baseline: UI should work WITHOUT an API key (manual English paste). Auto-translation is a convenience, not a requirement.
- Translation uses `translate_to_english(text, api_key)` from tokenizer.py which calls `call_openrouter` with `meta-llama/llama-3.1-8b-instruct`
- All tokenizer calls must be mocked in tests — `patch("token_tax.get_tokenizer")` and `patch("token_tax.tokenize_text")`
- `gr.BarPlot` accepts a dict or pandas DataFrame — use a simple dict structure
- Keep `token_tax.py` as pure computation (no Gradio imports), `token_tax_ui.py` as UI only
