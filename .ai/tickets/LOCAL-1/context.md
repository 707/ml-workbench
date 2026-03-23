# Ticket Context: LOCAL-1 — Reasoning Model Comparison Gradio App

**Issue:** local (no tracker)
**Status:** planning-complete
**Last Updated:** 2026-03-22
**Last Agent:** claude-code
**Last Phase:** plan

---

## Summary
A Gradio app hosted on HuggingFace Spaces that sends a question to DeepSeek-R1 and Llama-3.1-8B simultaneously via OpenRouter, parses the `<think>` block from R1, and displays a side-by-side comparison with reasoning/answer token split. Designed to make the "overthinking" failure mode of reasoning models visible.

## Confirmed Plan

### Phase 1: Core API Layer (`app.py`)
1. **`parse_think_block(text)`** — `app.py`
   - Action: Split on `</think>` — everything before is reasoning, everything after is answer. Return `("", text)` if no `<think>` tag found.
   - Status: pending

2. **`call_openrouter(api_key, model, prompt)`** — `app.py`
   - Action: POST to `https://openrouter.ai/api/v1/chat/completions` with model ID, user message, and `include_reasoning: true` for R1. Return full JSON response.
   - Status: pending

3. **`extract_usage(response)`** — `app.py`
   - Action: Pull `usage.completion_tokens_details.reasoning_tokens`, `usage.completion_tokens`, `usage.prompt_tokens`. Return dict. Default to 0 if field absent.
   - Status: pending

### Phase 2: Parallel Dispatch (`app.py`)
4. **`run_comparison(api_key, question)`** — `app.py`
   - Action: `ThreadPoolExecutor(max_workers=2)` to call both models concurrently. Parse R1 through `parse_think_block`. Return two result dicts independently — one model failing should not crash the other.
   - Status: pending

### Phase 3: Gradio UI (`app.py`)
5. **API key input + question selector**
   - Action: `gr.Textbox(type="password")` for API key. `gr.Radio` for preset questions. `gr.Textbox` for custom input. If custom is non-empty, use it; else use selected preset.
   - Status: pending

6. **Side-by-side output panels**
   - Action: Two `gr.Column` blocks. Left (R1): reasoning trace in scrollable `gr.Textbox`, token stats in `gr.Markdown`. Right (Llama): response + token stats.
   - Status: pending

7. **Wire submit button to `run_comparison`**
   - Action: `gr.Button("Compare →").click(run_comparison, inputs=[key, question], outputs=[...])`
   - Status: pending

### Phase 4: HF Spaces Config
8. **`requirements.txt`** — `gradio`, `requests`
9. **`README.md`** — HF Spaces YAML frontmatter + description

## The 5 Preset Questions

| # | Question | Why |
|---|----------|-----|
| 1 | How many r's are in "strawberry"? | Tokenization trap — letter counting spiral |
| 2 | A bat and a ball cost $1.10. The bat costs $1 more than the ball. How much is the ball? | CRT problem — intuitive wrong answer is $0.10, correct is $0.05 |
| 3 | Is 9677 a prime number? | Forces actual arithmetic vs pattern recall |
| 4 | The Monty Hall problem: You pick door 1. Host opens door 3 (empty). Should you switch? | Famous model-confuser — counterintuitive correct answer |
| 5 | If you fold a paper in half 42 times (paper = 0.1mm), how thick is it? | Exponential growth — tests step-by-step reasoning vs approximation |

## Models
- DeepSeek-R1: `deepseek/deepseek-r1` (free tier on OpenRouter)
- Llama-3.1 8B: `meta-llama/llama-3.1-8b-instruct` (free tier on OpenRouter)

## Files to Create
- `app.py` — entire app (single file)
- `requirements.txt` — `gradio`, `requests`
- `README.md` — HF Spaces metadata header

## Files to Read Before Starting
- None (greenfield project)

## Current State

### Completed
(none yet)

### In Progress
(none yet)

### Blocked By
None

## Implementation Notes
- Use string split on `</think>` not regex — simpler, no greedy-match edge cases
- `parse_think_block` strips leading `<think>` from the reasoning part
- Token split (not dollar cost) is the primary metric — free tier makes cost $0, but token counts tell the real story
- Error isolation: catch exceptions per-future in ThreadPoolExecutor so one model failing doesn't blank the other panel
- `gr.Textbox(lines=10, max_lines=30)` for reasoning trace — R1 can produce 5000+ token traces

## Test Strategy
- Unit: `parse_think_block` — no tags, empty think block, normal case
- Unit: `extract_usage` — with R1 fixture JSON (has reasoning_tokens), with Llama fixture (field absent)
- Manual E2E: run locally with real OpenRouter API key before pushing to HF Spaces

## Handoff Instructions
Continue from: Phase 1, Step 1 — implement `parse_think_block(text)` in `app.py`, write unit tests first (TDD).
