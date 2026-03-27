# Ticket Context: GH-7 — feat: enrich existing Tokenizer Inspector with token tax indicators

**Issue:** https://github.com/707/ml-workbench/issues/7
**Status:** complete
**Last Updated:** 2026-03-25
**Last Agent:** claude-code
**Last Phase:** implementation

---

## Summary
Add RTC, context usage percentage, and quality risk badges to the existing Single and Compare sub-tabs in the Tokenizer Inspector. Backward-compatible enhancement.

## Confirmed Plan

### Step 1: Write failing tests for enriched Single tab stats
**File:** `workbench/test_tokenizer.py`
- Update or add to existing `_run_single` tests:
  - When English text (detected language = "en"): stats include "RTC vs English: 1.0x", "Quality risk: low"
  - When non-English text with API key: stats include RTC > 1.0, appropriate risk level
  - When non-English text WITHOUT API key: stats include "RTC: (provide English text for comparison)"
  - Context usage always shown: "Context usage (128k): X.XX%"

### Step 2: Modify `_run_single` in tokenizer.py
- After existing stats computation, add:
  - `context_window_usage(len(tokens), 128_000)` → always shown
  - If text is English: RTC = 1.0, risk = "low"
  - If text is non-English AND api_key available: translate, tokenize English, compute RTC + risk
  - If text is non-English AND no api_key: show placeholder message
- Append to existing stats markdown (don't replace)

### Step 3: Write failing tests for enriched Compare tab stats
- Update or add to existing `_run_compare` tests:
  - Comparison markdown includes RTC for each tokenizer
  - Shows which tokenizer has lower RTC (better for this language)

### Step 4: Modify `_run_compare` in tokenizer.py
- After existing comparison stats, add RTC per tokenizer when English baseline available
- Add note: "Tokenizer A is X% more efficient than Tokenizer B for this language"

## Files to Read Before Starting
- `workbench/tokenizer.py` — full file, especially `_run_single` (~line 350+) and `_run_compare` (~line 380+)
- `workbench/test_tokenizer.py` — existing tests for `_run_single` and `_run_compare` to understand current assertions
- Check exact function signatures and return values before modifying

## Current State

### Completed
- Step 1: Failing tests for enriched Single tab stats (context usage, RTC, quality risk) ✓
- Step 2: Enriched `_handle_single` with context usage, RTC, risk badge ✓
- Step 3: Failing tests for enriched Compare tab stats (RTC per tokenizer, efficiency note) ✓
- Step 4: Enriched `_handle_compare` with RTC and efficiency comparison ✓
- UI wiring: English Equivalent textbox added to both Single and Compare tabs ✓
- Backward compat verified: all 187 existing tests pass, 100% coverage on tokenizer.py

### In Progress
(none)

### Blocked By
(none — GH-3 metrics already exist)

## Implementation Notes
- **Critical constraint**: This modifies existing functions — must be backward compatible. All existing tests must still pass.
- The `_run_single` function currently returns `(html_output, stats_markdown)` — do NOT change the return signature
- The `_run_compare` function returns a tuple — do NOT change the return signature
- RTC computation for non-English requires translation → API call. This must be optional (no API key = graceful degradation)
- Import the GH-3 functions: `relative_tokenization_cost`, `context_window_usage`, `quality_risk_level` — they're in the same file so no import needed
- The `_run_single` function already has access to `api_key` via the UI inputs — check the Gradio callback wiring
- Mock `translate_to_english` in tests that exercise the RTC path
- Run full test suite after changes: `uv run pytest workbench/test_tokenizer.py workbench/test_app.py -q` to verify no regressions
