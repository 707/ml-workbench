# Fix Four Code Review Risks

## Context
Code review of the workbench identified four production risks: a missing HTTP timeout, a crash-on-network-failure path, unguarded tokenizer downloads, and a magic number in the legacy estimator. All four are independent fixes. TDD approach: failing test first, then minimal fix.

---

## Fix 1: `openrouter.py` — Add timeout to POST request

**File:** `workbench/openrouter.py` (line 49)
**Test file:** `workbench/test_openrouter_models.py`

**Problem:** `call_openrouter()` has no `timeout` on `requests.post()`. Can hang indefinitely.

**Test (RED):** Add `TestCallOpenrouterTimeout` — mock `requests.post`, assert `timeout=30` is passed.

**Fix (GREEN):** Add `timeout=30` to line 49. One-line change. (30s because LLM completions are slower than model listing which uses 10s.)

---

## Fix 2: `corpora.py` — Graceful fallback on HF fetch failure

**File:** `workbench/corpora.py` (lines 191-194)
**Test file:** `workbench/test_corpora.py` (new)

**Problem:** `fetch_strict_parallel_samples()` raises `errors[-1]` when all configs fail for a language. This crashes the benchmark tab.

**Test (RED):**
- `test_network_failure_returns_empty_not_raises` — patch `_fetch_first_rows` to raise, verify no exception and language is absent from result
- `test_partial_failure_preserves_successful_languages` — one language fails, one succeeds, successful one is in result

**Fix (GREEN):** Remove `raise errors[-1]` (lines 193-194). When all configs fail, the language is simply omitted from results. Callers already handle missing languages — `token_tax.py` does `samples.get(language, [])` → `if not language_samples: continue`.

---

## Fix 3: `tokenizer.py` — Wrap HF download in try/except

**File:** `workbench/tokenizer.py` (line 100)
**Test file:** `workbench/test_tokenizer.py`

**Problem:** `AutoTokenizer.from_pretrained(repo_id)` at line 100 has no error handling. Network failures produce opaque transformers tracebacks and could pollute the cache.

**Test (RED):**
- `test_from_pretrained_failure_raises_clear_message` — patch `from_pretrained` to raise `OSError`, assert `RuntimeError` with user-friendly message
- `test_from_pretrained_failure_does_not_cache` — after failure, name must not appear in `_tokenizer_cache`

**Fix (GREEN):** Wrap line 100 in try/except, re-raise as `RuntimeError` with actionable message (mentions `TRANSFORMERS_OFFLINE=1`). Assignment to `_tokenizer_cache` only happens on success, so failed downloads can't pollute the cache.

---

## Fix 4: `token_tax.py` — Extract magic number to named constant

**File:** `workbench/token_tax.py` (line 336)
**Test file:** `workbench/test_token_tax.py`

**Problem:** `row["avg_chars"] / 4.0` is undocumented magic number in `portfolio_analysis()`.

**Test (RED):**
- `test_legacy_chars_per_token_constant_exists` — import `LEGACY_CHARS_PER_TOKEN`, assert it's 4.0
- `test_portfolio_analysis_uses_named_constant` — inspect source, assert `LEGACY_CHARS_PER_TOKEN` is referenced and `/ 4.0)` is gone

**Fix (GREEN):**
1. Add `LEGACY_CHARS_PER_TOKEN: float = 4.0` after `SAMPLE_PHRASES` with a comment explaining it's an English-centric BPE heuristic and that `benchmark_corpus()`/`scenario_analysis()` supersede it
2. Replace `/ 4.0` with `/ LEGACY_CHARS_PER_TOKEN` on line 336

---

## Execution Order

1. Fix 1 (openrouter timeout) — simplest, 1 line + 1 test
2. Fix 3 (tokenizer error handling) — small try/except + 2 tests
3. Fix 2 (corpora fallback) — remove raise + new test file + 2 tests
4. Fix 4 (named constant) — constant extraction + 2 tests

## Verification

```bash
cd /Users/nad/Documents/Tests/workbench-core/workbench
python -m pytest test_openrouter_models.py test_tokenizer.py test_corpora.py test_token_tax.py -v --tb=short
python -m pytest --cov=openrouter --cov=tokenizer --cov=corpora --cov=token_tax --cov-report=term-missing
```

Confirm all existing 246+ tests still pass and coverage stays ≥90%.
