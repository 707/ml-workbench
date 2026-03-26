# Ticket Context: GH-6 — feat: Traffic Analysis tab with CSV upload

**Issue:** https://github.com/707/ml-workbench/issues/6
**Status:** planning-complete
**Last Updated:** 2026-03-25
**Last Agent:** claude-code
**Last Phase:** plan

---

## Summary
New tab for portfolio-level token tax analysis. Users upload a CSV with language/traffic data and see aggregate cost exposure, spend share vs traffic share, and worst-case languages.

## Confirmed Plan

### Step 1: Write failing tests for `SAMPLE_PHRASES`
**File:** `workbench/test_token_tax.py`
- `TestSamplePhrases`:
  - `SAMPLE_PHRASES` has at least 15 languages
  - All values are non-empty strings
  - Includes: en, zh, ar, hi, ja, ko, fr, de, es, pt, ru, th, vi, bn, ta

### Step 2: Add `SAMPLE_PHRASES` to `token_tax.py`
- Dict of ~20 language codes → representative sentence in that language
- Sentences should be real text (not transliterations), ~10-20 words each

### Step 3: Write failing tests for `parse_traffic_csv`
- `TestParseTrafficCsv`:
  - Valid CSV with columns language,request_count,avg_chars → list of dicts
  - Missing column raises ValueError with descriptive message
  - Empty CSV returns empty list
  - Non-numeric request_count raises ValueError
  - Extra columns are ignored (only required 3 are used)

### Step 4: Implement `parse_traffic_csv`
```python
def parse_traffic_csv(file_path: str) -> list[dict]:
    """Parse CSV. Required columns: language, request_count, avg_chars.
    Returns list of {"language": str, "request_count": int, "avg_chars": int}."""
```
- Use `csv.DictReader` (no pandas dependency needed)
- Validate required columns exist
- Coerce numeric fields, raise ValueError on bad data

### Step 5: Write failing tests for `portfolio_analysis`
- `TestPortfolioAnalysis`:
  - Returns dict with keys: total_monthly_cost, languages (list), token_tax_exposure (weighted avg RTC)
  - Each language entry has: language, traffic_share, token_count, rtc, cost_share, tax_ratio
  - Traffic shares sum to ~1.0
  - Cost shares sum to ~1.0
  - Mock `get_tokenizer` and `tokenize_text`

### Step 6: Implement `portfolio_analysis`
```python
def portfolio_analysis(
    traffic_data: list[dict],
    model_name: str,
    english_tokenizer_name: str = "gpt2",
) -> dict:
```
- For each language row: use `SAMPLE_PHRASES[language]` (or fall back to English phrase if language not in dict)
- Tokenize sample phrase with selected model + tokenize English phrase
- Compute RTC, cost per request, aggregate
- Return portfolio-level summary

### Step 7: Write failing smoke tests for Traffic Analysis UI
**File:** `workbench/test_token_tax_ui.py`
- `TestBuildTrafficAnalysisUI`: returns `gr.Blocks` without raising
- `TestTrafficHandler`: mock CSV parse + portfolio analysis, verify returns expected outputs

### Step 8: Implement Traffic Analysis tab in `token_tax_ui.py`
- Add `build_traffic_analysis_ui() -> gr.Blocks` or add as sub-tab within token_tax_ui
- UI layout:
  1. `gr.File(file_types=[".csv"])` — CSV upload
  2. `gr.Markdown` — example CSV format shown as code block
  3. `gr.Dropdown` — model selector (from `available_models()`)
  4. `gr.Button` — "Analyze Portfolio"
  5. `gr.DataFrame` — results table: Language, Traffic Share %, Token Count, RTC, Cost Share %, Tax Ratio
  6. `gr.Markdown` — summary: total token tax exposure, worst-case language, recommendation

### Step 9: Wire into app.py
- Option A: Add as 4th tab in `build_ui()` → `["Model Comparison", "Tokenizer Inspector", "Token Tax Dashboard", "Traffic Analysis"]`
- Option B: Nest inside Token Tax Dashboard as a sub-tab (like Single/Compare in Tokenizer Inspector)
- **Recommended: Option B** — keeps top-level tab count at 3, groups related functionality

## Files to Read Before Starting
- `workbench/token_tax.py` — extend with CSV/portfolio functions (created in GH-5)
- `workbench/token_tax_ui.py` — extend with Traffic Analysis tab (created in GH-5)
- `workbench/pricing.py` — `get_pricing` for cost calculations
- `workbench/tokenizer.py` — `get_tokenizer`, `tokenize_text`, GH-3 metric functions

## Current State

### Completed
(none)

### In Progress
(none)

### Blocked By
- GH-3 (metrics)
- GH-4 (pricing)
- GH-5 (token_tax.py and token_tax_ui.py must exist)

## Implementation Notes
- `csv` module from stdlib is sufficient — no need for pandas
- Sample phrases should be actual text in each language, not lorem ipsum
- Portfolio analysis uses sample phrases as approximation — document this limitation in UI: "Estimates based on representative sample text per language. For exact analysis, use the Dashboard tab with your actual content."
- File uploads on HF Spaces are ephemeral — that's fine, results are computed immediately
- Fall back gracefully if a language isn't in SAMPLE_PHRASES — use English phrase and note "no sample available for [lang]"
- Mock all tokenizer calls in tests: `patch("token_tax.get_tokenizer")`
