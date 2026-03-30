"""
ML Workbench — Gradio app for tokenizer analysis and free-model comparisons.
"""

import html as _html
import os
import re
from time import perf_counter
import gradio as gr
from concurrent.futures import ThreadPoolExecutor, as_completed

from openrouter import call_openrouter, extract_usage, OPENROUTER_URL  # noqa: F401
from tokenizer import build_tokenizer_ui
from token_tax_ui import build_token_tax_ui

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Set OPENROUTER_API_KEY as a server-side secret to run the comparison tab
# without exposing the key to the browser.
SERVER_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# ---------------------------------------------------------------------------
# Model IDs
# ---------------------------------------------------------------------------

FREE_MODELS: list[tuple[str, str]] = [
    ("Qwen 2.5 7B Instruct (Free)", "qwen/qwen-2.5-7b-instruct:free"),
    ("Llama 3.2 3B Instruct (Free)", "meta-llama/llama-3.2-3b-instruct:free"),
    ("Mistral 7B Instruct (Free)", "mistralai/mistral-7b-instruct:free"),
]

MODEL_R1 = "qwen/qwen-2.5-7b-instruct:free"
MODEL_LLAMA = "meta-llama/llama-3.2-3b-instruct:free"

PRESET_QUESTIONS = [
    'How many r\'s are in "strawberry"?',
    "A bat and a ball cost $1.10. The bat costs $1 more than the ball. How much is the ball?",
    "Is 9677 a prime number?",
    "The Monty Hall problem: You pick door 1. Host opens door 3 (empty). Should you switch?",
    "If you fold a paper in half 42 times (paper = 0.1mm), how thick is it?",
]

APP_CSS = """
body.mlwb-dark {
  --wb-bg: #0f1116;
  --wb-panel: #171b24;
  --wb-panel-soft: #1d2330;
  --wb-border: #2d3748;
  --wb-text: #e5e7eb;
  --wb-muted: #94a3b8;
  --wb-accent: #f97316;
  --wb-accent-soft: rgba(249, 115, 22, 0.16);
}

body.mlwb-light {
  --wb-bg: #f4f6fb;
  --wb-panel: #ffffff;
  --wb-panel-soft: #eef2f9;
  --wb-border: #d7dee9;
  --wb-text: #18212f;
  --wb-muted: #5b6b82;
  --wb-accent: #ea580c;
  --wb-accent-soft: rgba(234, 88, 12, 0.10);
}

body.mlwb-dark,
body.mlwb-light {
  background: var(--wb-bg) !important;
  color: var(--wb-text) !important;
}

body.mlwb-dark .gradio-container,
body.mlwb-light .gradio-container {
  background: var(--wb-bg) !important;
  color: var(--wb-text) !important;
}

body.mlwb-light .gradio-container input,
body.mlwb-light .gradio-container textarea,
body.mlwb-light .gradio-container select,
body.mlwb-light .gradio-container button,
body.mlwb-light .gradio-container .wrap,
body.mlwb-light .gradio-container .block {
  color: var(--wb-text);
}

.app-shell-header,
.filter-panel,
.workbench-box,
.benchmark-summary-box,
.preview-card {
  background: var(--wb-panel);
  border: 1px solid var(--wb-border);
  border-radius: 18px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
}

.app-shell-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  margin-bottom: 1rem;
}

.app-shell-copy h1 {
  margin: 0;
  font-size: 1.1rem;
}

.app-shell-copy p {
  margin: 0.35rem 0 0 0;
  color: var(--wb-muted);
}

#theme-toggle {
  appearance: none;
  border: 1px solid var(--wb-border);
  background: var(--wb-panel-soft);
  color: var(--wb-text);
  border-radius: 999px;
  padding: 0.65rem 1rem;
  font-weight: 600;
  cursor: pointer;
}

.filter-grid {
  align-items: stretch;
}

.filter-panel {
  padding: 1rem;
}

.tooltip-label {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0.2rem 0 0.55rem 0;
  color: var(--wb-text);
  font-weight: 600;
}

.tooltip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.15rem;
  height: 1.15rem;
  border-radius: 999px;
  border: 1px solid var(--wb-border);
  background: var(--wb-panel-soft);
  color: var(--wb-muted);
  font-size: 0.75rem;
  cursor: help;
}

.benchmark-summary-box {
  padding: 1rem 1.1rem;
}

.benchmark-summary-box h3,
.preview-card h3 {
  margin: 0 0 0.4rem 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.85rem;
  margin-top: 0.8rem;
}

.summary-metric {
  background: var(--wb-panel-soft);
  border: 1px solid var(--wb-border);
  border-radius: 14px;
  padding: 0.9rem;
}

.summary-metric-label {
  color: var(--wb-muted);
  font-size: 0.82rem;
  margin-bottom: 0.35rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.summary-metric-value {
  color: var(--wb-text);
  font-size: 0.96rem;
  line-height: 1.4;
}

.preview-card {
  padding: 1rem 1.1rem;
}

.preview-subtitle,
.benchmark-summary-empty,
.preview-empty {
  color: var(--wb-muted);
  margin: 0.2rem 0 0.9rem 0;
}

.preview-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.9rem;
}

.preview-meta {
  background: var(--wb-panel-soft);
  border: 1px solid var(--wb-border);
  border-radius: 12px;
  padding: 0.8rem 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.preview-meta-label {
  font-size: 0.8rem;
  color: var(--wb-muted);
}

.preview-meta-value {
  font-size: 0.98rem;
  color: var(--wb-text);
  font-weight: 600;
}

.preview-text-box,
.preview-token-box {
  border: 1px solid var(--wb-border);
  background: var(--wb-panel-soft);
  border-radius: 14px;
  padding: 0.95rem;
}

.preview-text-box {
  margin-bottom: 0.8rem;
}

.preview-text {
  color: var(--wb-text);
  line-height: 1.7;
}

.preview-token-box {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.preview-token {
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.55rem;
  border-radius: 999px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.92rem;
  border: 1px solid transparent;
}

.preview-tone-0 { background: rgba(59, 130, 246, 0.16); color: #2563eb; border-color: rgba(59, 130, 246, 0.28); }
.preview-tone-1 { background: rgba(16, 185, 129, 0.16); color: #059669; border-color: rgba(16, 185, 129, 0.28); }
.preview-tone-2 { background: rgba(239, 68, 68, 0.16); color: #dc2626; border-color: rgba(239, 68, 68, 0.28); }
.preview-tone-3 { background: rgba(168, 85, 247, 0.16); color: #9333ea; border-color: rgba(168, 85, 247, 0.28); }
.preview-tone-4 { background: rgba(245, 158, 11, 0.16); color: #d97706; border-color: rgba(245, 158, 11, 0.28); }
.preview-tone-5 { background: rgba(14, 165, 233, 0.16); color: #0284c7; border-color: rgba(14, 165, 233, 0.28); }
"""

APP_JS = """
async () => {
  const storageKey = "mlwb-theme";

  const applyTheme = (theme) => {
    const body = document.body;
    body.classList.remove("mlwb-dark", "mlwb-light");
    body.classList.add(theme === "light" ? "mlwb-light" : "mlwb-dark");
    const button = document.getElementById("theme-toggle");
    if (button) {
      button.textContent = theme === "light" ? "Switch to dark mode" : "Switch to light mode";
    }
  };

  const attachToggle = () => {
    const button = document.getElementById("theme-toggle");
    if (!button || button.dataset.bound === "true") {
      return;
    }
    button.dataset.bound = "true";
    button.addEventListener("click", () => {
      const nextTheme = document.body.classList.contains("mlwb-light") ? "dark" : "light";
      localStorage.setItem(storageKey, nextTheme);
      applyTheme(nextTheme);
    });
  };

  applyTheme(localStorage.getItem(storageKey) || "dark");
  attachToggle();
  const observer = new MutationObserver(() => attachToggle());
  observer.observe(document.body, { childList: true, subtree: true });
  setTimeout(() => observer.disconnect(), 8000);
}
"""

APP_HEAD = f"<style>{APP_CSS}</style><script>{APP_JS}</script>"

# ---------------------------------------------------------------------------
# Phase 1: Core API Layer
# ---------------------------------------------------------------------------


def parse_think_block(text: str) -> tuple[str, str]:
    """Split R1 output into (reasoning, answer).

    Splits on the first </think> occurrence:
    - Everything before is reasoning (with leading <think> stripped).
    - Everything after is the answer (leading whitespace stripped).

    Returns ("", text) if no </think> tag is found.
    """
    if "</think>" not in text:
        return ("", text)

    before, after = text.split("</think>", 1)

    # Strip the opening <think> tag from the reasoning part
    if before.startswith("<think>"):
        before = before[len("<think>"):]

    reasoning = before
    answer = after.strip()

    return (reasoning, answer)


# ---------------------------------------------------------------------------
# Phase 2: Parallel Dispatch
# ---------------------------------------------------------------------------


def _call_model(
    api_key: str,
    model_id: str,
    prompt: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict:
    """Call any model and return a result dict.

    Reasoning detection applies to all models:
    1. Prefer `message.reasoning` field (OpenRouter native reasoning field).
    2. Fall back to parsing <think>...</think> tags in `message.content`.
    """
    extra: dict = {}
    if temperature is not None:
        extra["temperature"] = temperature
    if max_tokens is not None:
        extra["max_tokens"] = max_tokens
    response = call_openrouter(api_key, model_id, prompt, **extra)
    message = response["choices"][0]["message"]
    content = message.get("content") or ""

    reasoning_field = message.get("reasoning") or ""
    if reasoning_field:
        reasoning, answer = reasoning_field, content
    else:
        reasoning, answer = parse_think_block(content)

    return {
        "reasoning": reasoning,
        "answer": answer,
        "usage": extract_usage(response),
    }


def run_comparison(
    api_key: str,
    question: str,
    model_a: str = MODEL_R1,
    model_b: str = MODEL_LLAMA,
    params_a: dict | None = None,
    params_b: dict | None = None,
) -> tuple[dict, dict]:
    """Run both models concurrently and return (result_a, result_b).

    Each result is an independent dict. If one model fails, the other
    result is still returned — the failed model gets {"error": str}.
    """
    params_a = params_a or {}
    params_b = params_b or {}

    result_a: dict = {}
    result_b: dict = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(_call_model, api_key, model_a, question, **params_a): "a",
            executor.submit(_call_model, api_key, model_b, question, **params_b): "b",
        }

        for future in as_completed(futures):
            label = futures[future]
            try:
                result = future.result()
                if label == "a":
                    result_a = result
                else:
                    result_b = result
            except Exception as exc:
                error_dict = {"error": str(exc)}
                if label == "a":
                    result_a = error_dict
                else:
                    result_b = error_dict

    return result_a, result_b


# ---------------------------------------------------------------------------
# Phase 3: Gradio UI
# ---------------------------------------------------------------------------


def _format_usage(usage: dict) -> str:
    """Render token usage as a Markdown string."""
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    reasoning = usage.get("reasoning_tokens", 0)
    answer_tokens = completion - reasoning if reasoning else completion

    lines = [
        f"**Prompt tokens:** {prompt}",
        f"**Completion tokens:** {completion}",
    ]
    if reasoning:
        lines.append(f"**Reasoning tokens:** {reasoning}")
        lines.append(f"**Answer tokens:** {answer_tokens}")

    return "  \n".join(lines)


def compare(api_key: str, preset: str, custom: str):
    """Gradio handler: pick question, call run_comparison, format outputs."""
    question = custom.strip() if custom.strip() else preset

    if not api_key.strip():
        return "", "No API key provided.", "", "No API key provided.", ""
    if not question:
        return "", "No question provided.", "", "No question provided.", ""

    r1_result, llama_result = run_comparison(api_key.strip(), question)

    # R1 outputs
    if "error" in r1_result:
        r1_reasoning = ""
        r1_answer = f"Error: {r1_result['error']}"
        r1_stats = ""
    else:
        r1_reasoning = r1_result.get("reasoning", "")
        r1_answer = r1_result.get("answer", "")
        r1_stats = _format_usage(r1_result.get("usage", {}))

    # Llama outputs
    if "error" in llama_result:
        llama_answer = f"Error: {llama_result['error']}"
        llama_stats = ""
    else:
        llama_answer = llama_result.get("answer", "")
        llama_stats = _format_usage(llama_result.get("usage", {}))

    return r1_reasoning, r1_answer, r1_stats, llama_answer, llama_stats


def _stats_to_html(stats_md: str) -> str:
    """Convert **Key:** Value markdown to inline HTML."""
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stats_md)
    return out.replace("  \n", "<br>").replace("\n", "<br>")


def _build_card(
    question: str,
    r1_reasoning: str,
    r1_answer: str,
    r1_stats_md: str,
    llama_answer: str,
    llama_stats_md: str,
    model_a_label: str = "Qwen 2.5 7B Instruct (Free)",
    model_b_label: str = "Llama 3.2 3B Instruct (Free)",
) -> str:
    """Render one comparison result as an HTML card."""
    q = _html.escape(question)
    r1_ans = _html.escape(r1_answer)
    r1_trace = _html.escape(r1_reasoning)
    llama_ans = _html.escape(llama_answer)
    label_a = _html.escape(model_a_label)
    label_b = _html.escape(model_b_label)

    return f"""
<div style="border:1px solid #ddd;border-radius:8px;padding:16px;margin-bottom:20px;background:#fff;">
  <p style="font-weight:bold;font-size:1.05em;margin:0 0 12px 0;">Q: {q}</p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
    <div>
      <strong>{label_a}</strong>
      <div style="background:#f5f5f5;padding:8px 12px;border-radius:4px;font-size:0.85em;margin:8px 0 10px 0;">{_stats_to_html(r1_stats_md)}</div>
      <p style="margin:0 0 10px 0;">{r1_ans}</p>
      <details>
        <summary style="cursor:pointer;color:#888;font-size:0.85em;">Show reasoning trace</summary>
        <pre style="white-space:pre-wrap;font-size:0.78em;background:#f9f9f9;padding:10px;border-radius:4px;max-height:300px;overflow-y:auto;margin-top:6px;">{r1_trace}</pre>
      </details>
    </div>
    <div>
      <strong>{label_b}</strong>
      <div style="background:#f5f5f5;padding:8px 12px;border-radius:4px;font-size:0.85em;margin:8px 0 10px 0;">{_stats_to_html(llama_stats_md)}</div>
      <p style="margin:0;">{llama_ans}</p>
    </div>
  </div>
</div>"""


def _comparison_status_markdown(lines: list[str]) -> str:
    """Render a compact runtime status panel for model comparison."""
    return "### Runtime Status\n" + "\n".join(f"- {line}" for line in lines)


def render_comparison_with_status(
    api_key_val: str,
    model_a_label: str,
    model_b_label: str,
    temp_a_val: float,
    temp_b_val: float,
    max_tokens_a_val,
    max_tokens_b_val,
    preset_val: str,
    custom_val: str,
    history: list,
    model_ids: dict[str, str],
    progress=gr.Progress(),
):
    """Return comparison history with a stable runtime status summary."""
    effective_key = SERVER_KEY if SERVER_KEY else api_key_val
    question = custom_val.strip() if custom_val.strip() else preset_val

    if not effective_key.strip():
        msg = "<p style='color:red'>No API key provided.</p>"
        return history, "".join(history) + msg, _comparison_status_markdown(["No API key provided."])
    if not question:
        msg = "<p style='color:red'>No question provided.</p>"
        return history, "".join(history) + msg, _comparison_status_markdown(["No question provided."])

    m_a_id = model_ids[model_a_label]
    m_b_id = model_ids[model_b_label]
    params_a = {"temperature": temp_a_val, "max_tokens": int(max_tokens_a_val) if max_tokens_a_val else None}
    params_b = {"temperature": temp_b_val, "max_tokens": int(max_tokens_b_val) if max_tokens_b_val else None}
    params_a = {k: v for k, v in params_a.items() if v is not None}
    params_b = {k: v for k, v in params_b.items() if v is not None}

    progress(0.15, desc=f"Comparing {model_a_label} vs {model_b_label}")
    start = perf_counter()
    result_a, result_b = run_comparison(effective_key, question, m_a_id, m_b_id, params_a, params_b)
    duration = perf_counter() - start
    progress(1.0, desc="Comparison complete")

    if "error" in result_a:
        a_reasoning, a_answer, a_stats = "", f"Error: {result_a['error']}", ""
    else:
        a_reasoning = result_a.get("reasoning", "")
        a_answer = result_a.get("answer", "")
        a_stats = _format_usage(result_a.get("usage", {}))

    if "error" in result_b:
        b_answer, b_stats = f"Error: {result_b['error']}", ""
    else:
        b_answer = result_b.get("answer", "")
        b_stats = _format_usage(result_b.get("usage", {}))

    card = _build_card(
        question, a_reasoning, a_answer, a_stats, b_answer, b_stats,
        model_a_label=model_a_label, model_b_label=model_b_label,
    )
    new_history = [card] + history
    status_lines = [
        f"Comparison completed in **{duration:.1f}s**.",
        f"Prompt length: **{len(question)}** characters.",
    ]
    if "error" in result_a or "error" in result_b:
        status_lines.append("At least one model returned an error; review the comparison card for details.")
    return new_history, "".join(new_history), _comparison_status_markdown(status_lines)


def _build_comparison_blocks() -> gr.Blocks:
    """Construct and return the Model Comparison Gradio Blocks."""
    model_choices = [label for label, _ in FREE_MODELS]
    model_ids = {label: m_id for label, m_id in FREE_MODELS}

    with gr.Blocks(title="Reasoning Model Comparison") as demo:
        gr.Markdown(
            "# Reasoning Model Comparison\n"
            "Compare any two explicit OpenRouter free-tier models via OpenRouter."
        )

        # Never serialize the server-side key into frontend component state.
        if SERVER_KEY:
            api_key = gr.State("")
            gr.Markdown(
                "This space is using a **hosted server-side OpenRouter key**. "
                "Your requests run against the host's quota; the key itself is never sent to the browser."
            )
        else:
            with gr.Accordion("OpenRouter API Key", open=False, visible=True):
                api_key = gr.Textbox(
                    label="OpenRouter API Key",
                    type="password",
                    placeholder="sk-or-... — get a free key at openrouter.ai",
                    value="",
                    elem_id="openrouter-api-key",
                )

        # Model selection dropdowns with per-model inference controls
        with gr.Row():
            with gr.Column():
                model_a_drop = gr.Dropdown(
                    choices=model_choices,
                    value=model_choices[0],
                    label="Model A",
                    info="First free OpenRouter model to compare on the same prompt.",
                )
                with gr.Accordion("Model A parameters", open=False):
                    temp_a = gr.Slider(
                        minimum=0.0, maximum=2.0, value=1.0, step=0.05,
                        label="Temperature",
                        info="Sampling temperature for Model A.",
                    )
                    max_tokens_a = gr.Number(
                        value=None, label="Max tokens (blank = no limit)", precision=0,
                        info="Optional maximum completion length for Model A.",
                    )
            with gr.Column():
                model_b_drop = gr.Dropdown(
                    choices=model_choices,
                    value=model_choices[1],
                    label="Model B",
                    info="Second free OpenRouter model to compare against Model A.",
                )
                with gr.Accordion("Model B parameters", open=False):
                    temp_b = gr.Slider(
                        minimum=0.0, maximum=2.0, value=1.0, step=0.05,
                        label="Temperature",
                        info="Sampling temperature for Model B.",
                    )
                    max_tokens_b = gr.Number(
                        value=None, label="Max tokens (blank = no limit)", precision=0,
                        info="Optional maximum completion length for Model B.",
                    )

        with gr.Accordion("Input Prompt", open=True):
            preset = gr.Radio(
                choices=PRESET_QUESTIONS,
                label="Input Prompt",
                value=PRESET_QUESTIONS[0],
                info="Preset prompt used for the comparison unless a custom prompt is provided.",
            )
            custom = gr.Textbox(
                label="Custom Prompt (optional, overrides selected input)",
                placeholder="Type your own question here...",
                elem_id="comparison-custom-prompt",
                info="Custom prompt to send to both models. If filled, this overrides the preset.",
            )

        submit_btn = gr.Button("Compare →", variant="primary")
        comparison_status = gr.Markdown(
            value=_comparison_status_markdown(
                ["Choose two free models and click **Compare** to run the hosted comparison."]
            )
        )

        history_state = gr.State([])
        history_html = gr.HTML()

        submit_btn.click(
            fn=lambda api_key_val, model_a_label, model_b_label, temp_a_val, temp_b_val, max_tokens_a_val, max_tokens_b_val, preset_val, custom_val, history: render_comparison_with_status(
                api_key_val,
                model_a_label,
                model_b_label,
                temp_a_val,
                temp_b_val,
                max_tokens_a_val,
                max_tokens_b_val,
                preset_val,
                custom_val,
                history,
                model_ids,
            ),
            inputs=[
                api_key, model_a_drop, model_b_drop,
                temp_a, temp_b, max_tokens_a, max_tokens_b,
                preset, custom, history_state,
            ],
            outputs=[history_state, history_html, comparison_status],
        )

    return demo


def build_ui() -> gr.Blocks:
    """Construct and return the full tabbed Gradio UI shell.

    Tabs:
      - Model Comparison: side-by-side reasoning model comparison.
      - Tokenizer Inspector: tokenization visualisation and analysis.

    Returns:
        gr.Blocks composing the tabbed app shell and child workbench blocks.
    """
    comparison_blocks = _build_comparison_blocks()
    tokenizer_blocks = build_tokenizer_ui()
    token_tax_blocks = build_token_tax_ui()

    with gr.Blocks(title="ML Workbench", fill_width=True) as demo:
        gr.HTML(
            """
            <div class="app-shell-header">
              <div class="app-shell-copy">
                <h1>ML Workbench</h1>
                <p>Tokenizer evidence, scenario modelling, and free-model comparisons in one place.</p>
              </div>
              <button id="theme-toggle" type="button">Switch to light mode</button>
            </div>
            """
        )
        with gr.Tabs():
            with gr.Tab("Token Tax Workbench"):
                token_tax_blocks.render()
            with gr.Tab("Tokenizer Inspector"):
                tokenizer_blocks.render()
            with gr.Tab("Model Comparison"):
                comparison_blocks.render()
    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("APP STARTING — building UI...", flush=True)
    app = build_ui()
    print("UI built — launching server...", flush=True)
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        ssr_mode=False,
        head=APP_HEAD,
    )
