# Ticket Context: GH-1 — feat: user-selectable free models with per-model inference parameters

**Issue:** https://github.com/707/ml-workbench/issues/1
**Status:** complete
**Last Updated:** 2026-03-25
**Last Agent:** claude-code
**Last Phase:** implementation

---

## Summary
Replaces the two hard-coded model constants (MODEL_R1, MODEL_LLAMA) with user-facing dropdowns and per-model inference parameter controls (temperature, max_tokens). The `compare()` return shape and all 46 existing tests remain unchanged — model selection is wired one layer up in `_compare_and_render`.

## Confirmed Plan

### Phase 1: Data Layer — Model Registry and call_openrouter params

1. **Add FREE_MODELS registry** — `workbench/app.py`
   - Action: Define `FREE_MODELS: list[tuple[str, str]]` — a list of (display_label, openrouter_model_id) pairs. Keep MODEL_R1 / MODEL_LLAMA constants as defaults pointing into the list.
   - Status: pending

2. **Extend `call_openrouter` with optional inference params** — `workbench/app.py`
   - Action: Add `temperature: float | None = None` and `max_tokens: int | None = None` kwargs. Include in payload only when not None.
   - Status: pending

### Phase 2: Call Layer — Generic _call_model

3. **Replace `_call_r1` and `_call_llama` with `_call_model`** — `workbench/app.py`
   - Action: Delete both helpers. Add `_call_model(api_key, model_id, prompt, temperature=None, max_tokens=None) -> dict`. Reasoning detection (prefer `message.reasoning`, fall back to `parse_think_block`) applies to all models.
   - Status: pending

4. **Update `run_comparison` signature** — `workbench/app.py`
   - Action: `run_comparison(api_key, question, model_a, model_b, params_a=None, params_b=None)`. Return shape `(result_a, result_b)` unchanged.
   - Status: pending

### Phase 3: Gradio UI — Dropdowns and Inference Controls

5. **Add model dropdowns** — `workbench/app.py`
   - Action: Two `gr.Dropdown` components above the question row, populated from FREE_MODELS. Defaults: stepfun and llama IDs.
   - Status: pending

6. **Add per-model inference parameter inputs** — `workbench/app.py`
   - Action: Under each dropdown, `gr.Accordion` (collapsed) containing `gr.Slider` for temperature (0.0–2.0, default 1.0) and `gr.Number` for max_tokens (default blank = no limit).
   - Status: pending

### Phase 4: Wiring — _compare_and_render and _build_card

7. **Thread model names and params through `_compare_and_render`** — `workbench/app.py`
   - Action: Add model_a, model_b, temp_a, temp_b, max_tokens_a, max_tokens_b to inputs. Call `run_comparison` directly with model IDs and params. Do NOT modify `compare()`.
   - Status: pending

8. **Update `_build_card` to accept model names** — `workbench/app.py`
   - Action: Add `model_a_label` and `model_b_label` params. Replace hard-coded heading strings.
   - Status: pending

### Phase 5: Tests

9. **Unit tests for FREE_MODELS** — non-empty, 2-tuples of strings, defaults present
10. **Unit tests for extended `call_openrouter`** — params in payload when set, absent when None
11. **Unit tests for `_call_model`** — reasoning detection, params forwarded, error isolation
12. **Unit tests for updated `run_comparison`** — explicit model IDs and params threaded through
13. **Regression** — all 46 existing tests pass unchanged

## Files to Read Before Starting
- `workbench/app.py` — full file; understand `compare()`, `_compare_and_render()`, `run_comparison()`, `_call_r1`, `_call_llama`, `_build_card`, `build_ui()`
- `workbench/test_app.py` — especially TestCompare (frozen contract) and TestRunComparison
- `workbench/pyproject.toml` — dep versions

## Current State

### Completed
(none yet)

### In Progress
(none yet)

### Blocked By
None

## Implementation Notes
- **Critical constraint**: `compare()` has a frozen 5-tuple return `(r1_reasoning, r1_answer, r1_stats, llama_answer, llama_stats)`. Do not touch its signature or return shape.
- `_compare_and_render` calls `run_comparison(effective_key, question, model_a, model_b, params_a, params_b)` directly. `compare()` stays unchanged.
- Reasoning detection from `_call_r1` moves to `_call_model` — applies to all models, not just the R1 slot.
- Inference params: use `if temperature is not None: payload["temperature"] = temperature` — never send defaults.
- Free model candidates: stepfun/step-3.5-flash, meta-llama/llama-3.1-8b-instruct:free, google/gemma-3-27b-it:free, mistralai/mistral-7b-instruct:free, qwen/qwen3-8b:free

## Handoff Instructions
Continue from: Phase 1, Step 1 — add FREE_MODELS registry to app.py. Write the unit test first (TDD), then implement.
