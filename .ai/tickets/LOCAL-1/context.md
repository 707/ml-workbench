# Ticket Context: LOCAL-1 — ML Workbench

**Issue:** local (no tracker)
**Status:** active
**Last Updated:** 2026-03-30
**Last Agent:** codex
**Last Phase:** architecture review + stabilization follow-up

---

## Summary
The current project is a Gradio-based ML workbench deployed primarily on Render. The app now has four main work areas:
1. **Token Tax Workbench** — tokenizer-first multilingual benchmarking with dual benchmark lanes:
   - `Strict Evidence` for reproducible FLORES-backed claims
   - `Streaming Exploration` for live exploratory benchmarking
2. **Tokenizer Inspector** — tokenizer visualization and inspection
3. **Model Comparison** — hosted OpenRouter free-model comparison
4. **Catalog / Scenario Lab** — tokenizer-family economics and deployable-model comparisons

The current priority is stabilization after expanding the exact tokenizer family registry and free OpenRouter model list.

## Current State

### Shipping state
- Render is the primary host.
- The app is stateless at runtime.
- `Strict Evidence` is the only deploy-grade basis for Scenario Lab cost/context projections.
- `Streaming Exploration` remains benchmark-only exploratory analysis.
- The free OpenRouter model list was recently expanded with additional exact, text-only families.

### Recent implementation milestones
- Local FLORES strict snapshot added and made the default benchmark source.
- Dual-lane benchmark flow shipped (`Strict Evidence` + `Streaming Exploration`).
- Tokenizer-first catalog and scenario views shipped.
- Artificial Analysis snapshot support added for benchmark-only speed metadata.
- Benchmark/scenario visual defaults and diagnostics were improved.
- Tokenizer warmup and bounded tokenizer caching were added to reduce Render cold-start and memory issues.

### Important runtime/deploy learnings
- Render free tier is sensitive to tokenizer memory usage; unbounded tokenizer retention and overly broad default selections caused instability.
- Default benchmark/scenario selections were intentionally reduced to keep the app responsive.
- Benchmark/chart bugs have often come from architecture drift rather than pure UI issues.

## Architecture Findings To Preserve

### 1. Tokenizer-family metadata drift is the main regression source
Adding a new tokenizer family currently requires aligned updates in several places:
- tokenizer loader registry
- tokenizer-family/model registry
- continuation heuristic logic
- chart color configuration

This drift already caused real bugs after the latest family expansion.

**Recommendation:** make tokenizer family metadata a single source of truth and derive the other registries from it.

### 2. Continuation heuristics are incomplete for new exact families
The benchmark’s `continued_word_rate` metric only had explicit handling for legacy families. New exact families were falling through to the unknown-family default, so coverage-style metrics were unreliable.

**Recommendation:** store `continuation_style` on each tokenizer family and drive `_is_continued_token()` from registry metadata rather than ad hoc family sets.

### 3. Docker tokenizer warmup needs runtime-safe permissions
The image currently warms tokenizers during build to reduce cold starts, but this is a deploy-sensitive path. Cache ownership must remain safe for the non-root runtime user.

**Recommendation:** ensure warmup runs under the runtime user or the warmed cache is explicitly ownership-corrected afterward.

### 4. Dark/light theming is only partially shipped
The shell theme can toggle, but Plotly charts were still using hardcoded white templates and not following the active theme.

**Recommendation:** centralize chart theme selection and make chart builders theme-aware.

### 5. Model Comparison has drifted from the shared free-model registry
The runtime comparison tab still uses a separate hardcoded model list instead of deriving its options from the same free exact registry used elsewhere in the app.

**Recommendation:** derive Model Comparison choices from the tokenizer/model registry so product surfaces stay aligned.

## Recommended Next Implementation Steps
1. Add failing tests that codify the registry contract:
   - every exact tokenizer family has continuation metadata
   - every exact tokenizer family has a chart color
   - Model Comparison choices derive from the free exact runtime registry
   - chart builders expose active theme in their layouts
2. Refactor tokenizer family metadata into a shared registry and derive:
   - tokenizer loading map
   - model family metadata
   - continuation logic
   - chart colors
3. Fix Docker warmup ownership/runtime safety.
4. Make Plotly charts follow the active app theme.
5. Re-run focused regression suites first, then the broader safety suite.

## Files To Read Before Continuing
- [/Users/nad/Documents/Tests/workbench-core/tokenizer_registry.py](/Users/nad/Documents/Tests/workbench-core/tokenizer_registry.py)
- [/Users/nad/Documents/Tests/workbench-core/tokenizer.py](/Users/nad/Documents/Tests/workbench-core/tokenizer.py)
- [/Users/nad/Documents/Tests/workbench-core/model_registry.py](/Users/nad/Documents/Tests/workbench-core/model_registry.py)
- [/Users/nad/Documents/Tests/workbench-core/token_tax.py](/Users/nad/Documents/Tests/workbench-core/token_tax.py)
- [/Users/nad/Documents/Tests/workbench-core/charts.py](/Users/nad/Documents/Tests/workbench-core/charts.py)
- [/Users/nad/Documents/Tests/workbench-core/app.py](/Users/nad/Documents/Tests/workbench-core/app.py)
- [/Users/nad/Documents/Tests/workbench-core/Dockerfile](/Users/nad/Documents/Tests/workbench-core/Dockerfile)

## Verification Baseline
- Full pytest suite last green before this follow-up: `510 passed`
- Latest shipped Render-facing stabilization commit before this follow-up: `27c0089`

## Handoff Instructions
Continue with a TDD-first stabilization pass:
1. lock in registry/theme/runtime expectations in tests
2. refactor to a single shared tokenizer-family source of truth
3. fix deploy/runtime and theme consistency issues
4. rerun focused + broader regression suites
