# Ticket Context: GH-3 — feat: add token tax metrics

**Issue:** https://github.com/707/ml-workbench/issues/3
**Status:** planning-complete
**Last Updated:** 2026-03-25
**Last Agent:** claude-code
**Last Phase:** plan

---

## Summary
Add pure computation functions for token tax analysis to `tokenizer.py`: Relative Tokenization Cost (RTC), byte premium, context window usage, and quality risk level.

## Confirmed Plan

### Step 1: Write failing tests for RTC and byte premium
- `TestRelativeTokenizationCost`: rtc(10, 5) = 2.0, rtc(5, 5) = 1.0, rtc(10, 0) = 1.0 (zero guard)
- `TestBytePremium`: byte_premium("hello", "hello") = 1.0, Arabic vs English > 1.0, zero guard

### Step 2: Implement `relative_tokenization_cost` and `byte_premium`
- Pure math, ~15 lines total
- Zero-guard: return 1.0 when denominator is 0

### Step 3: Write failing tests for context window usage and quality risk
- `TestContextWindowUsage`: usage(1000, 128000) ≈ 0.0078, usage(128000, 128000) = 1.0, usage(0, 128000) = 0.0
- `TestQualityRiskLevel`: rtc 1.0 → "low", 2.0 → "moderate", 3.0 → "high", 5.0 → "severe", boundary values

### Step 4: Implement `context_window_usage` and `quality_risk_level`
- Pure math + threshold mapping, ~20 lines total
- Risk bands: low (<1.5), moderate (1.5-2.5), high (2.5-4.0), severe (>4.0)

## Files to Read Before Starting
- `workbench/tokenizer.py` — understand existing functions, where to add new ones
- `workbench/test_tokenizer.py` — follow existing test patterns

## Current State

### Completed
(none)

### In Progress
(none)

### Blocked By
Nothing

## Implementation Notes
- Add functions below `efficiency_score` in tokenizer.py
- Follow existing test class naming pattern (TestXxx)
- ~80 lines of new code total, keeping tokenizer.py under 540 lines
- All pure functions — no mocks needed in tests
