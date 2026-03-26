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

Two tools in one Space:

| Tab | What it does |
|-----|-------------|
| **Model Comparison** | Compare any two free models via OpenRouter side-by-side — reasoning trace, token counts, per-model inference parameters |
| **Tokenizer Inspector** | Paste text, see colour-coded token splits, token IDs, fragmentation ratios, OOV flags, and language efficiency scores |

---

## Model Comparison

Compare how reasoning and standard models respond to the same question. Pick two models from the dropdown, adjust temperature / max-tokens if you want, and click **Compare →**.

The left panel shows the model's reasoning trace (if it has one) plus its final answer and token counts. The right panel shows the second model's response.

### Models available

All free-tier via [OpenRouter](https://openrouter.ai) — no credit card required.

| Label | Model ID |
|-------|----------|
| Step 3.5 Flash (Reasoning) | `stepfun/step-3.5-flash` |
| Llama-3.1-8B | `meta-llama/llama-3.1-8b-instruct` |
| Gemma-3-27B | `google/gemma-3-27b-it:free` |
| Mistral-7B | `mistralai/mistral-7b-instruct:free` |

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
cd workbench/

# Install dependencies (creates .venv)
make install

# Run the app
make run
```

Open the local Gradio URL printed in your terminal. Set your OpenRouter API key in the UI.

To run with a pre-set server key (skips the key input field):

```bash
OPENROUTER_API_KEY=sk-or-... make run
```

### Run tests

```bash
make test
```

Runs all tests across `test_app.py` and `test_tokenizer.py` with coverage report.

---

## Deploy to Hugging Face Spaces

### First-time setup

```bash
# Authenticate with Hugging Face
hf login
```

Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space):
- SDK: **Gradio**
- Visibility: Public or Private

### Set your OpenRouter API key as a Space secret

In your Space settings → **Secrets** → add:
```
Name:  OPENROUTER_API_KEY
Value: sk-or-...
```

This lets the app run without users needing their own key.

### Deploy

```bash
cd workbench/
HF_SPACE=your-username/your-space-name make deploy
```

This uploads all app files (excluding `.venv`, cache, and build artifacts) directly to your Space.

### Update after changes

Same command — `make deploy` uploads the current state of `workbench/` on every run.

---

## Notes

- API keys are never stored; used only for the duration of each request.
- The tokenizer tab downloads model tokenizer configs on first use (~seconds). Subsequent calls use a local cache.
