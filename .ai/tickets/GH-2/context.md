# Ticket Context: GH-2 — feat: tokenizer inspector tab

**Issue:** https://github.com/707/ml-workbench/issues/2
**Status:** planning-complete
**Last Updated:** 14:40
**Last Agent:** claude-code
**Last Phase:** plan

---

## Summary
Add a Tokenizer Inspector tab to the existing Gradio workbench Space. Users paste text and see colour-coded token splits, token IDs, counts, a language efficiency score, and OOV word flags. Two sub-tabs: Single (one tokenizer) and Compare (two tokenizers side by side).

Phase 0 first cleans up the existing app: removes HF OAuth, hides the API key in a collapsed accordion, drops the broken Qwen3-8B model.

## Confirmed Plan

### Phase 0: App Cleanup (existing app.py)

1. **Remove Qwen3-8B from FREE_MODELS** — `workbench/app.py`
   - Delete `("Qwen3-8B", "qwen/qwen3-8b:free")` tuple — model returns 404
   - Status: pending

2. **Remove HF OAuth from build_ui()** — `workbench/app.py`
   - Delete `gr.LoginButton()`, `auth_msg`, `_on_load` callback, `demo.load(...)` call
   - Remove `profile` and `oauth_token` from `_compare_and_render` signature and inputs
   - Remove `using_server_key` logic — use SERVER_KEY if set, else fall back to user-entered key
   - Remove rate limiting (`_check_rate_limit`, `_request_log`, `RATE_LIMIT`, `RATE_WINDOW`)
   - Status: pending

3. **Move API key into collapsed Accordion** — `workbench/app.py`
   - Wrap `api_key` Textbox in `gr.Accordion("OpenRouter API Key", open=False)`
   - Pass `visible=False` to accordion when `SERVER_KEY` is set (static check at startup)
   - Status: pending

4. **Update test_app.py for Phase 0** — `workbench/test_app.py`
   - Remove/update tests referencing OAuth profile/token args, auth_msg, Qwen3 model ID
   - Status: pending

### Phase 1: Tokenizer Core (TDD — write tests first)

5. **Write failing tests for tokenizer loading** — `workbench/test_tokenizer.py`
   - `TestTokenizerLoading`: get_tokenizer("gpt2") loads, unknown name raises ValueError, all three names load
   - Mock `AutoTokenizer.from_pretrained` — no network calls in CI
   - Status: pending

6. **Implement tokenizer loading** — `workbench/tokenizer.py`
   - `SUPPORTED_TOKENIZERS = {"gpt2": "gpt2", "llama-3": "NousResearch/Meta-Llama-3-8B", "mistral": "mistralai/Mistral-7B-v0.1"}`
   - `get_tokenizer(name: str)` — lazy-load, module-level cache dict
   - Status: pending

7. **Write failing tests for tokenize_text** — `workbench/test_tokenizer.py`
   - Returns list of dicts with "token" (str) and "id" (int) keys
   - Empty string returns empty list
   - Mock tokenizer with fake encode/convert_ids_to_tokens response
   - Status: pending

8. **Implement tokenize_text** — `workbench/tokenizer.py`
   - `tokenize_text(text: str, tokenizer) -> list[dict]`
   - encode → get IDs, convert_ids_to_tokens → get strings, zip into [{"token": t, "id": i}, ...]
   - Status: pending

9. **Write failing tests for fragmentation_ratio and flag_oov_words** — `workbench/test_tokenizer.py`
   - fragmentation_ratio: per-word counts correct for known input
   - flag_oov_words: above/at/below threshold, empty input
   - Status: pending

10. **Implement fragmentation_ratio and flag_oov_words** — `workbench/tokenizer.py`
    - `fragmentation_ratio(text: str, tokenizer) -> dict[str, float]` — encode each word separately
    - `flag_oov_words(text: str, tokenizer, threshold: int = 3) -> set[str]`
    - Status: pending

11. **Write failing tests for language detection and efficiency score** — `workbench/test_tokenizer.py`
    - TestDetectLanguage: mock langdetect.detect, returns "en" for English, returns "en" on LangDetectException
    - TestEfficiencyScore: 10/10=1.0, 15/10=1.5, 10/0=1.0 (zero guard)
    - TestTranslateToEnglish: mock call_openrouter, verify translation prompt, returns text content
    - Status: pending

12. **Implement detect_language, translate_to_english, efficiency_score** — `workbench/tokenizer.py`
    - `detect_language(text: str) -> str` — wraps langdetect.detect, returns "en" on exception
    - `translate_to_english(text: str, api_key: str) -> str` — calls call_openrouter from openrouter.py
    - `efficiency_score(input_tokens: int, english_tokens: int) -> float`
    - **NOTE**: Must implement Step 17 (extract openrouter.py) before or alongside this step to avoid circular import
    - Status: pending

13. **Write failing tests for render_tokens_html** — `workbench/test_tokenizer.py`
    - Token spans present, OOV highlighting applied, HTML escaping works
    - Status: pending

14. **Implement render_tokens_html** — `workbench/tokenizer.py`
    - `render_tokens_html(tokens: list[dict], oov_words: set[str]) -> str`
    - Alternating background colours for normal tokens; distinct highlight (#ffcccc) for OOV tokens
    - html.escape all token text
    - Status: pending

### Phase 2: Tokenizer UI

15. **Write failing smoke test for build_tokenizer_ui** — `workbench/test_tokenizer.py`
    - Returns gr.Blocks instance without raising
    - Single-tab handler returns non-empty HTML + non-zero count (mocked tokenizer)
    - Compare-tab handler returns two HTML outputs + ratio string
    - Status: pending

16. **Implement build_tokenizer_ui** — `workbench/tokenizer.py`
    - Single tab: Dropdown (gpt2/llama-3/mistral), Textbox, Slider (OOV threshold 1–10 default 3), Button → HTML output + Markdown stats
    - Compare tab: shared Textbox, two Dropdowns, Button → two HTML outputs + Markdown ratio
    - Efficiency score: if text not English and len > 20, call translate_to_english then compute score, else 1.0
    - Translation failure: catch exception, display "N/A"
    - Status: pending

### Phase 3: Integration

17. **Extract call_openrouter to shared module** — `workbench/openrouter.py` (new file)
    - Move `call_openrouter`, `extract_usage`, `OPENROUTER_URL` from app.py to openrouter.py
    - Update app.py: `from openrouter import call_openrouter, extract_usage, OPENROUTER_URL`
    - Update tokenizer.py: `from openrouter import call_openrouter`
    - Update test mocks: patch `app.call_openrouter` still works (re-exported name in app namespace)
    - Status: pending

18. **Compose tabs in app.py** — `workbench/app.py`
    - Import `build_tokenizer_ui` from tokenizer
    - Change `build_ui()` to return `gr.TabbedInterface([existing_blocks, tokenizer_blocks], ["Model Comparison", "Tokenizer Inspector"])`
    - Update `test_build_ui_returns_gradio_blocks` to `isinstance(demo, (gr.Blocks, gr.TabbedInterface))`
    - Status: pending

19. **Add dependencies to pyproject.toml** — `workbench/pyproject.toml`
    - Add `"transformers>=4.40"` and `"langdetect>=1.0.9"`
    - Can be done as early as Phase 1 start
    - Status: pending

### Phase 4: Refactor & Polish

20. **Verify 80% coverage on tokenizer.py**
    - `pytest --cov=tokenizer --cov-report=term-missing workbench/`
    - Add targeted tests for uncovered branches
    - Status: pending

21. **Refactor render_tokens_html if > 30 lines**
    - Extract colour constants and HTML-building loop to helpers
    - Status: pending

## Files to Read Before Starting
- `workbench/app.py` — full file; understand build_ui(), _compare_and_render(), call_openrouter(), FREE_MODELS
- `workbench/test_app.py` — especially TestBuildUi, TestCallOpenrouter, TestFreeModels
- `workbench/pyproject.toml` — current deps

## Current State

### Completed
(none yet)

### In Progress
(none yet)

### Blocked By
None

## Implementation Notes
- **Critical constraint**: `compare()` has a frozen 5-tuple return — do NOT touch its signature
- Step 17 (extract openrouter.py) is logically part of Phase 1 step 12 — do it before implementing translate_to_english
- Lazy-load tokenizers inside `get_tokenizer()` — never at import time
- Mock `AutoTokenizer.from_pretrained` in ALL tests — no network calls in CI
- OOV threshold: configurable via UI slider (1–10, default 3); also accepted as a parameter to flag_oov_words
- Efficiency score = 1.0 when input is English or text length <= 20 chars (no API call)
- Translation failure is non-fatal: display "N/A" for efficiency score

## Handoff Instructions
Continue from: Phase 0, Step 1 — remove Qwen3-8B from FREE_MODELS. Then Steps 2–4 (OAuth removal). Then start TDD from Step 5.

IMPORTANT: This project has BUILDING-SETUP.md but no BUILDING.md yet.
