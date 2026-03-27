# Ticket Context: LOCAL-1 — ML Workbench (Reasoning Comparison + Token Tax Calculator)

**Issue:** local (no tracker)
**Status:** implemented
**Last Updated:** 2026-03-26
**Last Agent:** claude-code
**Last Phase:** Token Tax v2 Phase 4 complete

---

## Summary
A Gradio app hosted on HuggingFace Spaces with three tabs:
1. **Token Tax Calculator** (primary) — multilingual tokenization cost analysis across 8 models
2. **Tokenizer Inspector** — tokenization visualization
3. **Model Comparison** — side-by-side reasoning model comparison (DeepSeek-R1 vs Llama)

## Current State

### Completed

**Original App (pre-v2):**
- Reasoning model comparison (app.py) — all 4 phases
- Tokenizer Inspector (tokenizer.py) — GH-2 through GH-8
- Deployed to https://huggingface.co/spaces/nad707/workbench

**Token Tax Calculator v2 (this session):**
- [x] Phase 1 — Foundation (Issues 1-4): commit `29c8fee`
  - 8 tokenizers (o200k_base, cl100k_base, Llama-3, Mistral, Qwen-2.5, Phi-2, BLOOM, GPT-2)
  - TiktokenAdapter bridging tiktoken ↔ HuggingFace interface
  - OpenRouter live pricing with TTL cache + static fallback
  - model_registry.py decoupling model IDs from tokenizer keys
  - Token fertility wired into analysis
- [x] Phase 2 — Visualization (Issues 5-8): commit `a217bd6`
  - charts.py extracted (bubble, context bars, heatmap, waterfall)
  - benchmark_all() for cross-language×model analysis
- [x] Phase 3 — Intelligence (Issues 9-10): commit `bb371ae`
  - run_benchmark() for zero-input 20-language analysis
  - Structured recommendation engine with mitigations by RTC band
- [x] Phase 4 — Polish (Issues 12-14): commit `26a8137`
  - CSV/JSON export
  - Tabbed dashboard layout (Cost Table, Charts, Benchmark, Traffic Analysis)
  - Token Tax Calculator promoted to first tab
- [x] Fix gated tokenizers: commits `a567196`, `ecae109`
  - Replaced gated Gemma-2 → Phi-2, Command-R → BLOOM

**Stats:** 363 tests passing, 97% coverage

### In Progress
None — all phases complete

### Not Done (deferred to v3)
- Issue 11 — Auto-translate (low priority)
- Stakeholder-specific views, orthographic scoring, monolingual model recs
- Import tokka-bench 100+ language sentences

## Key Files (Token Tax v2)

| File | Purpose |
|------|---------|
| `workbench/token_tax.py` | Core computation: analyze, benchmark, recommend, export |
| `workbench/token_tax_ui.py` | Gradio UI handlers and layout |
| `workbench/charts.py` | Plotly chart builders (4 types) |
| `workbench/pricing.py` | Static MODEL_PRICING + OpenRouter cache |
| `workbench/model_registry.py` | Model ID ↔ tokenizer key mapping |
| `workbench/openrouter.py` | OpenRouter API client (chat + model discovery) |
| `workbench/tokenizer.py` | Tokenizer registry, TiktokenAdapter, metrics |

## Files to Read Before Starting
- `workbench/token_tax.py` — all computation logic
- `workbench/token_tax_ui.py` — UI layout and handlers
- `workbench/charts.py` — chart builders
- `.claude/plans/groovy-mapping-sketch.md` — full 14-issue plan with research

## Implementation Notes
- **Gated repos:** Google Gemma and Cohere Command-R require HF license acceptance. Use non-gated alternatives (Phi-2, BLOOM).
- **Platform:** HF Spaces free tier (16GB RAM) is the only viable free option for 8 tokenizers. Streamlit Cloud (~1GB) and Render (512MB) are too constrained.
- **Architecture:** All computation in UI-free modules (token_tax.py, pricing.py, charts.py). UI layer (token_tax_ui.py) is thin Gradio glue. Extraction-ready for future FastAPI+React.
- **generate_recommendations()** returns structured dict (not string) — UI formats via _format_recommendations().
- **Pricing cache:** _pricing_cache + _last_refreshed in pricing.py. Static MODEL_PRICING takes precedence over cached entries for tokenizer keys.

## Handoff Instructions
Continue from: **Branch not yet merged or pushed.** Next actions:
1. Push branch to remote: `git push -u origin feature/LOCAL-1-reasoning-model-comparison`
2. Test on HF Spaces — verify all 8 tokenizers load, benchmark runs, charts render
3. If ready, merge to main and deploy
4. For v3 scope, start with Issue 11 (auto-translate) or tokka-bench language import
