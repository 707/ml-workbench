# Ticket Context: GH-4 — feat: add model pricing data module

**Issue:** https://github.com/707/ml-workbench/issues/4
**Status:** planning-complete
**Last Updated:** 22:57
**Last Agent:** claude-code
**Last Phase:** plan

---

## Summary
Create `workbench/pricing.py` with a static pricing dict for supported tokenizer/model families and lookup functions.

## Confirmed Plan

### Step 1: Write failing tests for pricing module
- `TestModelPricing`: MODEL_PRICING has all 3 models, each has required keys (input_per_million, output_per_million, context_window, label)
- `TestGetPricing`: known model returns dict, unknown model raises KeyError
- `TestAvailableModels`: returns sorted list of model names matching SUPPORTED_TOKENIZERS keys
- `TestLastUpdated`: LAST_UPDATED is a non-empty string

### Step 2: Implement pricing.py
- `MODEL_PRICING` dict with gpt2, llama-3, mistral entries
- `get_pricing(model_name)` — lookup with KeyError
- `available_models()` — sorted keys
- `LAST_UPDATED = "2026-03-25"`
- ~60 lines total

## Files to Read Before Starting
- `workbench/tokenizer.py` — SUPPORTED_TOKENIZERS dict (keys must match)
- `workbench/test_tokenizer.py` — follow test patterns

## Current State

### Completed
(none)

### In Progress
(none)

### Blocked By
Nothing

## Implementation Notes
- New file: `workbench/pricing.py`
- New test file: `workbench/test_pricing.py`
- Pricing is illustrative/approximate, document this clearly
- Keys in MODEL_PRICING must match keys in SUPPORTED_TOKENIZERS from tokenizer.py
