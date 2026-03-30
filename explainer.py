"""Plain-language explainer tab for non-technical users."""

from __future__ import annotations

import html

import gradio as gr
import plotly.graph_objects as go

from corpora import fetch_corpus_samples
from model_registry import list_tokenizer_families
from tokenizer import get_tokenizer, tokenize_text


LANGUAGE_LABELS = {
    "ar": "Arabic",
    "hi": "Hindi",
    "ja": "Japanese",
    "zh": "Mandarin Chinese",
}

DEFAULT_EXPLAINER_LANGUAGES = ["ar", "hi", "ja"]
DEFAULT_EXPLAINER_TOKENIZERS = ["gpt2", "llama-3", "qwen-2.5"]


def _language_label(code: str) -> str:
    return LANGUAGE_LABELS.get(code, code)


def _empty_figure(message: str):
    fig = go.Figure()
    fig.update_layout(
        template="plotly",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "var(--wb-text)"},
        annotations=[{
            "text": message,
            "xref": "paper",
            "yref": "paper",
            "x": 0.5,
            "y": 0.5,
            "showarrow": False,
            "font": {"size": 15},
        }],
    )
    return fig


def _single_series_bar(rows: list[dict], *, key: str, title: str, y_title: str):
    if not rows:
        return _empty_figure("Choose a language and tokenizer set to load an example.")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[row["tokenizer_label"] for row in rows],
        y=[row[key] for row in rows],
        marker_color=["#2563eb", "#06b6d4", "#f97316", "#22c55e", "#a855f7"][: len(rows)],
        text=[row.get("caption", "") for row in rows],
        textposition="outside",
    ))
    fig.update_layout(
        template="plotly",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "var(--wb-text)"},
        title=title,
        xaxis_title="Tokenizer family",
        yaxis_title=y_title,
        showlegend=False,
    )
    fig.update_xaxes(tickangle=-18)
    return fig


def _comparison_bar(rows: list[dict]):
    if not rows:
        return _empty_figure("Choose a language and tokenizer set to load an example.")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[row["tokenizer_label"] for row in rows],
        y=[row["english_tokens"] for row in rows],
        name="English",
        marker_color="#94a3b8",
    ))
    fig.add_trace(go.Bar(
        x=[row["tokenizer_label"] for row in rows],
        y=[row["target_tokens"] for row in rows],
        name=rows[0]["language_label"],
        marker_color="#2563eb",
    ))
    fig.update_layout(
        template="plotly",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "var(--wb-text)"},
        title="Same meaning, different token counts",
        xaxis_title="Tokenizer family",
        yaxis_title="Token count",
        barmode="group",
    )
    fig.update_xaxes(tickangle=-18)
    return fig


def _build_example_rows(language: str, tokenizer_keys: list[str]) -> tuple[list[dict], str, str]:
    samples = fetch_corpus_samples("strict_parallel", ["en", language], row_limit=1)
    target_samples = samples.get(language) or []
    english_samples = samples.get("en") or []
    if not target_samples:
        raise RuntimeError(f"No strict benchmark sample is bundled for {_language_label(language)}.")

    target_sample = target_samples[0]
    english_text = target_sample.english_text or (english_samples[0].text if english_samples else "")
    target_text = target_sample.text
    rows: list[dict] = []

    family_lookup = {row["key"]: row["label"] for row in list_tokenizer_families(include_proxy=False)}
    for tokenizer_key in tokenizer_keys:
        tokenizer = get_tokenizer(tokenizer_key)
        english_tokens = len(tokenize_text(english_text, tokenizer))
        target_tokens = len(tokenize_text(target_text, tokenizer))
        rtc = (target_tokens / english_tokens) if english_tokens else 1.0
        monthly_cost_index = round(100 * rtc, 1)
        context_window_words = int(128_000 / max(rtc * 1.33, 1e-9))
        rows.append({
            "tokenizer_key": tokenizer_key,
            "tokenizer_label": family_lookup.get(tokenizer_key, tokenizer_key),
            "language_label": _language_label(language),
            "english_tokens": english_tokens,
            "target_tokens": target_tokens,
            "rtc": round(rtc, 2),
            "monthly_cost_index": monthly_cost_index,
            "context_window_words": context_window_words,
            "caption": f"{round(rtc, 2)}x",
        })
    return rows, english_text, target_text


def _serialize_rows(rows: list[dict]) -> dict:
    headers = [
        "Tokenizer family",
        "English tokens",
        "Target-language tokens",
        "Relative Token Cost (vs English)",
        "Budget impact index",
        "Approx. usable context (words)",
    ]
    data = [
        [
            row["tokenizer_label"],
            row["english_tokens"],
            row["target_tokens"],
            f"{row['rtc']:.2f}x",
            f"{row['monthly_cost_index']:.1f}",
            f"{row['context_window_words']:,}",
        ]
        for row in rows
    ]
    return {"headers": headers, "data": data}


def _sample_card_html(english_text: str, target_text: str, language: str) -> str:
    return (
        '<section class="explainer-card">'
        "<h3>One sentence, two token counts</h3>"
        "<p>This uses the same benchmark sentence in English and one other language. The meaning stays stable, so the token-count difference mainly comes from the tokenizer.</p>"
        '<div class="preview-meta-grid">'
        '<div class="preview-meta"><span class="preview-meta-label">English</span>'
        f'<span class="preview-meta-value">{html.escape(english_text)}</span></div>'
        f'<div class="preview-meta"><span class="preview-meta-label">{html.escape(_language_label(language))}</span>'
        f'<span class="preview-meta-value">{html.escape(target_text)}</span></div>'
        "</div>"
        "</section>"
    )


def build_explainer_payload(language: str, tokenizer_keys: list[str]):
    rows, english_text, target_text = _build_example_rows(language, tokenizer_keys)
    explainer_md = (
        "## Why tokenizers matter\n"
        "A model does not read text as whole words. It reads **tokens**. "
        "If one language needs more tokens to say the same thing, that language usually costs more and burns through the context window faster.\n\n"
        "**Relative Token Cost (vs English)** means: if English takes 100 tokens and Arabic takes 180 tokens for the same sentence, the Arabic RTC is **1.8x**.\n\n"
        "**Tokens per word / character** means how chopped-up the text becomes. "
        "**Word split rate** means how often words get broken into multiple pieces."
    )
    scenario_md = (
        "### Why this matters in Scenario Lab\n"
        "- Higher relative token cost usually means higher input cost for the same work.\n"
        "- Higher token counts also leave less room inside the context window for chat history, retrieved documents, or tool outputs.\n"
        "- Scenario Lab takes this benchmark evidence and turns it into budget and context trade-offs for attached models."
    )
    return (
        explainer_md,
        _sample_card_html(english_text, target_text, language),
        _comparison_bar(rows),
        _single_series_bar(
            rows,
            key="monthly_cost_index",
            title="How extra tokens raise cost",
            y_title="Budget impact index (English baseline = 100)",
        ),
        _single_series_bar(
            rows,
            key="context_window_words",
            title="How extra tokens shrink usable context",
            y_title="Approximate usable words in a 128k window",
        ),
        _serialize_rows(rows),
        scenario_md,
    )


def build_explainer_ui() -> gr.Blocks:
    families = list_tokenizer_families(include_proxy=False)
    default_keys = [key for key in DEFAULT_EXPLAINER_TOKENIZERS if any(row["key"] == key for row in families)]
    language_choices = [(_language_label(code), code) for code in DEFAULT_EXPLAINER_LANGUAGES]

    with gr.Blocks(title="Why Tokenizers Matter") as demo:
        gr.HTML(
            '<section class="section-header">'
            "<h2>Why Tokenizers Matter</h2>"
            "<p>A plain-language guide to why the same idea can cost more in one language than another.</p>"
            "</section>"
        )
        gr.Markdown(
            "Think of a tokenizer as the model’s text slicer. "
            "Some slicers pack text neatly into a few pieces. Others break the same sentence into many smaller pieces. "
            "That difference is what this workbench calls the multilingual token tax."
        )
        with gr.Row(equal_height=False, elem_classes="filter-grid"):
            with gr.Column(elem_classes="filter-rail filter-rail--compact", min_width=280, scale=0):
                explainer_language = gr.Dropdown(
                    choices=language_choices,
                    value=DEFAULT_EXPLAINER_LANGUAGES[0],
                    label="Example language",
                    info="Pick one language to compare against the same English sentence.",
                )
                explainer_tokenizers = gr.Dropdown(
                    choices=[(row["label"], row["key"]) for row in families],
                    value=default_keys,
                    multiselect=True,
                    label="Tokenizer families",
                    info="Choose the tokenizers you want to compare in the explainer charts.",
                )
                explainer_run = gr.Button("Refresh explainer", variant="primary", size="sm", elem_classes="compact-action")
            with gr.Column(elem_classes="filter-rail filter-rail--wide", min_width=480, scale=1):
                explainer_intro = gr.Markdown(
                    "## Why tokenizers matter\nChoose a language and a few tokenizer families, then refresh the explainer."
                )
                explainer_sample = gr.HTML(
                    '<section class="explainer-card"><h3>Same meaning, different token counts</h3><p>Pick a language and refresh to load a live strict-benchmark example.</p></section>'
                )
        with gr.Tabs():
            with gr.Tab("Token counts"):
                explainer_token_plot = gr.Plot(label="Token counts")
            with gr.Tab("Cost impact"):
                explainer_cost_plot = gr.Plot(label="Cost impact")
            with gr.Tab("Context impact"):
                explainer_context_plot = gr.Plot(label="Context impact")
        explainer_table = gr.DataFrame(label="Explainer summary table", interactive=False)
        explainer_scenario = gr.Markdown(
            "### Why this matters in Scenario Lab\nThe benchmark tells you where token counts expand. Scenario Lab translates that into budget and context-window trade-offs."
        )

        explainer_run.click(
            fn=build_explainer_payload,
            inputs=[explainer_language, explainer_tokenizers],
            outputs=[
                explainer_intro,
                explainer_sample,
                explainer_token_plot,
                explainer_cost_plot,
                explainer_context_plot,
                explainer_table,
                explainer_scenario,
            ],
            queue=False,
        )
    return demo
