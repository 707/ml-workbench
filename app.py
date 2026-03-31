"""
ML Workbench — Gradio app for tokenizer analysis and free-model comparisons.
"""

from __future__ import annotations

import html as _html
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from typing import Any

import gradio as gr

from explainer import build_explainer_ui
from model_registry import list_free_runtime_choices
from openrouter import OPENROUTER_URL, call_openrouter, extract_usage  # noqa: F401
from token_tax_ui import build_token_tax_ui
from tokenizer import build_tokenizer_ui

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Set OPENROUTER_API_KEY as a server-side secret to run the comparison tab
# without exposing the key to the browser.
SERVER_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# ---------------------------------------------------------------------------
# Model IDs
# ---------------------------------------------------------------------------


def _free_model_choices() -> list[tuple[str, str]]:
    rows = list_free_runtime_choices(include_proxy=False)
    return [(row["label"], row["model_id"]) for row in rows]


FREE_MODELS: list[tuple[str, str]] = _free_model_choices()

MODEL_R1 = "qwen/qwen-2.5-7b-instruct:free"
MODEL_LLAMA = "meta-llama/llama-3.2-3b-instruct:free"

PRESET_QUESTIONS = [
    'How many r\'s are in "strawberry"?',
    "A bat and a ball cost $1.10. The bat costs $1 more than the ball. How much is the ball?",
    "Is 9677 a prime number?",
    "The Monty Hall problem: You pick door 1. Host opens door 3 (empty). Should you switch?",
    "If you fold a paper in half 42 times (paper = 0.1mm), how thick is it?",
]

APP_THEME = gr.themes.Default(
    primary_hue="orange",
    secondary_hue="slate",
    neutral_hue="slate",
)

APP_CSS = """
:root {
  --wb-bg: #f3f5fb;
  --wb-panel: #ffffff;
  --wb-panel-soft: #eef2f9;
  --wb-border: #d7dee9;
  --wb-text: #18212f;
  --wb-muted: #5b6b82;
  --wb-accent: #ea580c;
  --wb-accent-soft: rgba(234, 88, 12, 0.1);
  color-scheme: light;
}

@media (prefers-color-scheme: dark) {
  :root {
    --wb-bg: #0f1116;
    --wb-panel: #171b24;
    --wb-panel-soft: #1d2330;
    --wb-border: #2d3748;
    --wb-text: #e5e7eb;
    --wb-muted: #94a3b8;
    --wb-accent: #f97316;
    --wb-accent-soft: rgba(249, 115, 22, 0.16);
    color-scheme: dark;
  }
}

body {
  background: var(--wb-bg) !important;
  color: var(--wb-text) !important;
}

.gradio-container {
  background: var(--wb-bg) !important;
  color: var(--wb-text) !important;
}

.gradio-container .prose,
.gradio-container .prose *,
.gradio-container label,
.gradio-container h1,
.gradio-container h2,
.gradio-container h3,
.gradio-container h4,
.gradio-container p,
.gradio-container li,
.gradio-container small,
.gradio-container legend,
.gradio-container summary {
  color: var(--wb-text) !important;
  text-wrap: balance;
}

.gradio-container .prose p,
.gradio-container .prose li,
.gradio-container .hint,
.gradio-container .description,
.gradio-container .gradio-markdown p,
.app-shell-copy p,
.section-header p,
.chart-help p,
.compact-helper,
.preview-subtitle,
.benchmark-summary-empty,
.preview-empty {
  color: var(--wb-muted) !important;
}

.gradio-container input:not([type="range"]):not([type="checkbox"]):not([type="radio"]),
.gradio-container textarea,
.gradio-container select,
.gradio-container button,
.gradio-container [role="tab"] {
  color: var(--wb-text) !important;
}

.gradio-container input:not([type="range"]):not([type="checkbox"]):not([type="radio"]),
.gradio-container textarea,
.gradio-container select,
.gradio-container .form,
.gradio-container .block,
.gradio-container .wrap,
.gradio-container details,
.gradio-container summary {
  border-color: var(--wb-border) !important;
}

.gradio-container input:not([type="range"]):not([type="checkbox"]):not([type="radio"]),
.gradio-container textarea,
.gradio-container select,
.gradio-container details,
.gradio-container summary {
  background: var(--wb-panel-soft) !important;
}

.gradio-container [role="tab"][aria-selected="true"] {
  color: var(--wb-accent) !important;
}

.app-shell-header,
.workbench-box,
.benchmark-summary-box,
.preview-card,
.explainer-card {
  background: var(--wb-panel);
  border: 1px solid var(--wb-border);
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.app-shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.7rem 0.9rem;
  margin-bottom: 0.45rem;
}

.app-shell-copy h1 {
  margin: 0;
  font-size: 1rem;
  line-height: 1.2;
  color: var(--wb-text);
}

.app-shell-copy p {
  margin: 0.18rem 0 0 0;
  font-size: 0.88rem;
}

.gradio-container button:focus-visible,
.gradio-container [role="tab"]:focus-visible {
  outline: 2px solid var(--wb-accent);
  outline-offset: 2px;
}

.filter-grid {
  align-items: start;
  gap: 0.55rem;
}

.filter-rail {
  padding: 0.08rem 0;
  background: transparent;
  border: none;
  box-shadow: none;
  border-radius: 0;
}

.filter-rail .wrap {
  gap: 0.22rem;
}

.filter-rail--compact {
  max-width: 280px;
}

.filter-rail--wide {
  max-width: none;
}

.filter-rail--scenario-inputs {
  max-width: 360px;
}

.scenario-control-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem;
  margin-bottom: 0.35rem;
}

.scenario-custom-row {
  gap: 0.55rem;
  margin-top: 0.2rem;
}

.scenario-options-row {
  align-items: end;
  gap: 0.7rem;
  margin-top: 0.2rem;
  flex-wrap: wrap;
}

.scenario-control-block,
.scenario-control-stack,
.scenario-checkbox-group {
  gap: 0.25rem;
}

.scenario-control-block,
.scenario-control-stack {
  background: transparent;
  border: none;
  padding: 0;
}

.scenario-control-stack {
  margin-top: 0.1rem;
}

.scenario-checkbox-group {
  margin-top: 0.15rem;
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  align-items: end;
  gap: 0.7rem;
}

.catalog-utility-row {
  align-items: end;
  gap: 0.7rem;
  margin-bottom: 0.3rem;
  flex-wrap: wrap;
}

.checkbox-stack {
  gap: 0.25rem;
}

.section-header {
  margin: 0.05rem 0 0.45rem 0;
}

.section-header h2 {
  margin: 0;
  font-size: 1.2rem;
}

.section-header p {
  margin: 0.14rem 0 0 0;
  font-size: 0.88rem;
}

.chart-help {
  margin: 0 0 0.45rem 0;
  padding: 0;
}

.chart-help strong {
  color: var(--wb-text);
}

.metric-badge {
  display: inline-flex;
  align-items: center;
  margin-left: 0.45rem;
  padding: 0.12rem 0.42rem;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.16);
  border: 1px solid rgba(245, 158, 11, 0.32);
  color: #fbbf24;
  font-size: 0.72rem;
  font-weight: 600;
  vertical-align: middle;
  text-transform: none;
  letter-spacing: 0;
}

.chart-help p {
  margin: 0.18rem 0 0 0;
  line-height: 1.45;
}

.compact-helper {
  margin: 0.15rem 0 0.55rem 0;
  line-height: 1.45;
}

.benchmark-summary-box {
  padding: 0.55rem 0.65rem;
}

.benchmark-summary-box h3,
.preview-card h3,
.explainer-card h3 {
  margin: 0 0 0.18rem 0;
}

.summary-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.35rem;
}

.summary-pill {
  background: var(--wb-panel-soft);
  border: 1px solid var(--wb-border);
  border-radius: 999px;
  padding: 0.42rem 0.58rem;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  max-width: 100%;
}

.summary-pill-label {
  color: var(--wb-muted);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.summary-pill-value {
  color: var(--wb-text);
  font-size: 0.82rem;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-card {
  padding: 0.85rem 0.95rem;
}

.preview-subtitle,
.benchmark-summary-empty,
.preview-empty {
  color: var(--wb-muted);
  margin: 0.1rem 0 0.7rem 0;
}

.preview-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.55rem;
  margin-bottom: 0.75rem;
}

.preview-meta {
  background: var(--wb-panel-soft);
  border: 1px solid var(--wb-border);
  border-radius: 12px;
  padding: 0.7rem 0.8rem;
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
  padding: 0.8rem;
}

.preview-text-box {
  margin-bottom: 0.65rem;
}

.preview-text {
  color: var(--wb-text);
  line-height: 1.65;
}

.preview-token-box {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.compact-action {
  align-self: flex-start;
}

.compact-action button,
.compact-action {
  width: auto !important;
  min-width: 6.6rem;
  min-height: 2rem !important;
  padding-inline: 0.65rem !important;
  font-size: 0.88rem !important;
}

.app-shell-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.shell-link {
  display: inline-flex;
  align-items: center;
  gap: 0.42rem;
  color: var(--wb-text);
  text-decoration: none;
  border: 1px solid var(--wb-border);
  background: var(--wb-panel-soft);
  border-radius: 999px;
  padding: 0.42rem 0.68rem;
  font-size: 0.84rem;
}

.shell-link:hover {
  border-color: var(--wb-accent);
  background: rgba(249, 115, 22, 0.08);
}

.shell-link svg {
  width: 0.95rem;
  height: 0.95rem;
}

.raw-export-row {
  align-items: center;
  margin-bottom: 0.35rem;
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

.gradio-container table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-variant-numeric: tabular-nums;
  background: var(--wb-panel);
  color: var(--wb-text);
}

.gradio-container thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--wb-panel-soft) !important;
  color: var(--wb-muted) !important;
  border-bottom: 1px solid var(--wb-border) !important;
  font-weight: 600 !important;
}

.gradio-container tbody tr:nth-child(odd) td {
  background: color-mix(in srgb, var(--wb-panel) 88%, transparent);
}

.gradio-container tbody tr:nth-child(even) td {
  background: color-mix(in srgb, var(--wb-panel-soft) 72%, transparent);
}

.gradio-container td,
.gradio-container th {
  border-color: var(--wb-border) !important;
  padding: 0.55rem 0.65rem !important;
}

.gradio-container .wrap.svelte-1ipelgc,
.gradio-container .block {
  min-width: 0;
}

.explainer-card {
  padding: 0.95rem 1rem;
}

.explainer-callout {
  background: var(--wb-panel-soft);
  border: 1px solid var(--wb-border);
  border-radius: 14px;
  padding: 0.85rem 0.95rem;
  margin: 0.7rem 0;
}

.explainer-callout p {
  margin: 0.2rem 0 0 0;
  color: var(--wb-muted);
}

@media (max-width: 900px) {
  .summary-strip {
    display: grid;
    grid-template-columns: 1fr;
  }
}
"""

APP_JS = """
async () => {
  document.body.classList.add("mlwb-app");
}
"""

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
        api_key: Any
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
    explainer_blocks = build_explainer_ui()
    tokenizer_blocks = build_tokenizer_ui()
    token_tax_blocks = build_token_tax_ui()

    with gr.Blocks(title="ML Workbench", fill_width=True) as demo:
        gr.HTML(
            f"""
            <style>{APP_CSS}</style>
            <div class="app-shell-header">
              <div class="app-shell-copy">
                <h1>ML Workbench</h1>
                <p>Tokenizer evidence, scenario modelling, and free-model comparisons in one place.</p>
              </div>
              <div class="app-shell-actions">
                <a
                  class="shell-link"
                  href="https://github.com/707/ml-workbench"
                  target="_blank"
                  rel="noreferrer"
                  aria-label="Open GitHub repo"
                  title="GitHub repo"
                >
                  <svg viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
                    <path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 0 0 5.47 7.59c.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.5-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.54 7.54 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8 8 0 0 0 16 8c0-4.42-3.58-8-8-8Z"></path>
                  </svg>
                  <span>GitHub repo</span>
                </a>
              </div>
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
            with gr.Tab("Why Tokenizers Matter"):
                explainer_blocks.render()
        demo.load(None, None, None, js=APP_JS, queue=False)
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
        theme=APP_THEME,
    )
