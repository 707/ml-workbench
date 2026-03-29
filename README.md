---
title: ML Workbench
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# ML Workbench

Three tools in one Space:

| Tab | What it does |
|-----|-------------|
| **Token Tax Workbench** | Benchmark tokenizer families across languages, inspect deployable model mappings, run scenario tradeoff analyses, and audit formulas/sources |
| **Model Comparison** | Compare any two free models via OpenRouter side-by-side — reasoning trace, token counts, per-model inference parameters |
| **Tokenizer Inspector** | Paste text, see colour-coded token splits, token IDs, fragmentation ratios, OOV flags, and language efficiency scores |

---

## Token Tax Workbench

The workbench is designed as a four-step analysis flow:

1. **Benchmark**: Compare tokenizer families on a strict verified multilingual corpus
2. **Catalog**: Inspect deployable models, current pricing, context windows, and tokenizer mappings
3. **Scenario Lab**: Turn tokenizer differences into cost, scale, and context tradeoff views under your assumptions
4. **Audit**: Inspect formulas, data dictionary, sources, provenance, and exclusions

### What to do first

- Start in **Benchmark** to see which tokenizer families inflate tokens for your target languages
- Move to **Catalog** to see which real models sit on top of those families
- Use **Scenario Lab** to test your traffic assumptions
- Use **Audit** when you need to verify where a number came from

### Data policy

- Strict verified data is shown by default
- Proxy tokenizer mappings stay hidden until explicitly enabled
- Latency and throughput are only shown when surfaced metadata exists
- The app separates measured benchmark evidence from scenario-derived estimates

### Why it matters

The same semantic content can use very different token counts across languages and tokenizer families. That changes:

- API cost
- effective context window
- scaling behavior under traffic

This workbench helps you inspect those tradeoffs directly instead of assuming one model behaves equally across all languages.

---

## Model Comparison

Compare how reasoning and standard models respond to the same question. Pick two models from the dropdown, adjust temperature / max-tokens if you want, and click **Compare →**.

The left panel shows the model's reasoning trace (if it has one) plus its final answer and token counts. The right panel shows the second model's response.

### Models available

All comparison-tab models are explicit [OpenRouter](https://openrouter.ai) free-tier IDs so the hosted app can stay on a free-only runtime path.

| Label | Model ID |
|-------|----------|
| Qwen 2.5 7B Instruct (Free) | `qwen/qwen-2.5-7b-instruct:free` |
| Llama 3.2 3B Instruct (Free) | `meta-llama/llama-3.2-3b-instruct:free` |
| Mistral 7B Instruct (Free) | `mistralai/mistral-7b-instruct:free` |

### Preset questions

Chosen to expose the "overthinking" failure mode of reasoning models:

| Question | Why interesting |
|----------|----------------|
| How many r's in "strawberry"? | Tokenization trap — letter-counting spiral |
| Bat and ball cost $1.10... | CRT problem — intuitive wrong answer is $0.10, correct is $0.05 |
| Is 9677 a prime number? | Forces real arithmetic vs pattern recall |
| Monty Hall problem | Famous model-confuser — counterintuitive correct answer |
| Fold paper 42 times | Exponential growth — tests step-by-step reasoning vs approximation |

---

## Tokenizer Inspector

Paste any text and see exactly how a tokenizer splits it.

### Single mode
- Choose a tokenizer (GPT-2, Llama-3, or Mistral)
- Set the OOV threshold (tokens per word that counts as suspicious — default 3)
- Click **Tokenize**

Output: colour-coded token spans (red = OOV-flagged words), token count, fragmentation ratio, detected language.

### Compare mode
- Same input text, two tokenizers side by side
- Shows token count per tokenizer and the ratio between them

### Tokenizers

| Label | Model |
|-------|-------|
| gpt2 | `gpt2` |
| llama-3 | `NousResearch/Meta-Llama-3-8B` |
| mistral | `mistralai/Mistral-7B-v0.1` |

### Language efficiency score

When the input is not English, the app translates it via OpenRouter and compares token counts:

```
score = english_token_count / input_token_count
```

Score > 1.0: the source language is more compact than English for this tokenizer.
Score < 1.0: the source language uses more tokens.
Score = 1.0: English input (no translation needed).

---

## Run locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies (creates .venv)
make install

# Run the app
make run
```

Open the local Gradio URL printed in your terminal. Set your own OpenRouter API key in the UI if you are running locally without a hosted server key.

To run with a pre-set server key (skips the key input field and uses the host's quota for comparisons):

```bash
OPENROUTER_API_KEY=sk-or-... make run
```

### Run tests

```bash
make test
```

Runs the workbench test suite with coverage.

### Capture review screenshots

Use the screenshot review harness to capture consistent visual states across the workbench tabs:

```bash
uv run playwright install chromium
make review-screenshots REVIEW_BASE_URL=http://127.0.0.1:7860
```

Artifacts are written to `artifacts/review/<date>/<time>Z/` with a `manifest.json` describing the captured scenarios.
To include runtime tabs such as Model Comparison, run:

```bash
uv run python scripts/capture_review_bundle.py --base-url https://ml-workbench.onrender.com --include-runtime-tabs
```

If Chromium is flaky in your environment, the harness also supports `--browser firefox` or `--browser webkit`.

---

## Deploy to Render

Render is the primary hosted target for this repo.

```bash
# Push to GitHub (Render auto-deploys from the connected repo)
make deploy
```

In Render:
- Create a new Blueprint or Web Service from `707/ml-workbench`
- Branch: `main`
- Runtime: `Docker`
- Plan: `Free`

### Set your OpenRouter API key

In Render environment variables, add:
```
Name:  OPENROUTER_API_KEY
Value: sk-or-...
```

This lets the comparison tab run without users entering their own key. The UI discloses when the hosted server-side key is being used.

### Hugging Face fallback

```bash
HF_SPACE=your-username/your-space-name make deploy-hf
```

Use this only if you explicitly want to keep a HF Space in sync.

---

## Notes

- API keys are never stored; used only for the duration of each request.
- The tokenizer tab downloads model tokenizer configs on first use (~seconds). Subsequent calls use a local cache.
- The Docker image starts via `bootstrap.py`.
- The image is intentionally minimal: Python, `requirements.txt`, and the runtime modules only.
