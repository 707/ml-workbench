---
title: Reasoning Model Comparison
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "6.8.0"
app_file: app.py
pinned: false
license: mit
hf_oauth: true
---

# Reasoning Model Comparison

Compare how **Step 3.5 Flash** (reasoning model) and **Llama-3.1-8B** (standard model) respond to the same question side-by-side. The reasoning model's full thinking trace is shown alongside its final answer so you can see how much reasoning it actually does — and whether that reasoning helps.

## How to use

1. Enter your [OpenRouter](https://openrouter.ai) API key (both models have free-tier access).
2. Pick a preset question or type your own.
3. Click **Compare**.

The left panel shows R1's reasoning trace and final answer with token counts. The right panel shows Llama's response.

## Preset questions

These are chosen to expose the "overthinking" failure mode of reasoning models:

| Question | Why interesting |
|----------|----------------|
| How many r's are in "strawberry"? | Tokenization trap — letter-counting spiral |
| Bat and ball cost $1.10... | CRT problem — intuitive wrong answer is $0.10, correct is $0.05 |
| Is 9677 a prime number? | Forces real arithmetic vs pattern recall |
| Monty Hall problem | Famous model-confuser — counterintuitive correct answer |
| Fold paper 42 times | Exponential growth — tests step-by-step reasoning vs approximation |

## Models

- **Step 3.5 Flash** (`stepfun/step-3.5-flash`) — reasoning model with visible thinking trace
- **Llama-3.1-8B Instruct** (`meta-llama/llama-3.1-8b-instruct`) — standard instruction-tuned model

Both are free-tier on OpenRouter.

## Run locally

From the `workbench/` directory:

```bash
make install
make run
```

Then open the local Gradio URL shown in your terminal.

## Deploy to Hugging Face Space

1. Authenticate once:

```bash
hf login
```

2. Deploy from `workbench/`:

```bash
HF_SPACE=nad707/workbench make deploy
```

This uploads app files from `workbench/` to your Space while excluding local cache/venv artifacts.

## Notes

- Rename this file to `README.md` when deploying to HuggingFace Spaces (the YAML frontmatter must be in `README.md`).
- API key is not stored; it is used only for the duration of the request.
