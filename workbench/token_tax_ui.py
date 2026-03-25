"""Token Tax Dashboard — Gradio UI.

Provides `build_token_tax_ui()` which returns a gr.Blocks composing
the Token Tax Dashboard tab with cost analysis, charts, and recommendations.
"""

import gradio as gr

from pricing import available_models, LAST_UPDATED
from tokenizer import detect_language
from token_tax import (
    analyze_text_across_models,
    cost_projection,
    generate_recommendations,
)


def _handle_dashboard(
    text: str,
    english_text: str,
    selected_models: list[str],
    monthly_requests: int,
    avg_chars: int,
) -> tuple[dict, str, str]:
    """Handler logic for the Token Tax Dashboard — extracted for testability.

    Returns:
        (table_data, context_md, recommendations_md)
        table_data is a dict with 'headers' and 'data' keys for gr.DataFrame.
    """
    headers = [
        "Model", "Tokens", "RTC", "Byte Premium",
        "Context %", "Risk", "$/1M Input", "Monthly Est.",
    ]
    empty_table = {"headers": headers, "data": []}

    if not selected_models:
        return empty_table, "", "No models selected."

    eng = english_text.strip() if english_text else None

    try:
        results = analyze_text_across_models(text, eng, selected_models)
    except Exception as exc:
        return empty_table, "", f"Error: {exc}"

    lang = detect_language(text) if text.strip() else "en"

    # Build table rows (compute cost projections inline, no mutation)
    rows = []
    monthly_costs = {}
    for r in results:
        proj = cost_projection(
            r["token_count"],
            r["cost_per_million"],
            monthly_requests,
            avg_chars,
        )
        monthly_costs[r["model"]] = proj["monthly_cost"]
        rows.append([
            r["model"],
            r["token_count"],
            f"{r['rtc']:.2f}x",
            f"{r['byte_premium']:.2f}x",
            f"{r['context_usage']:.4%}",
            r["risk_level"],
            f"${r['cost_per_million']:.4f}",
            f"${proj['monthly_cost']:.4f}",
        ])

    table_data = {"headers": headers, "data": rows}

    # Context window summary
    context_lines = []
    for r in results:
        window_pct = r["context_usage"] * 100
        context_lines.append(
            f"**{r['model']}:** {r['token_count']} tokens "
            f"({window_pct:.2f}% of context window)"
        )
    if eng and any(r["rtc"] > 1.0 for r in results):
        worst = max(results, key=lambda r: r["rtc"])
        context_lines.append(
            f"\nThis text uses **{worst['rtc']:.1f}x** more tokens in "
            f"{worst['model']} than English equivalent."
        )
    context_md = "\n\n".join(context_lines)

    # Recommendations
    recs_md = generate_recommendations(results, lang)

    return table_data, context_md, recs_md


def build_token_tax_ui() -> gr.Blocks:
    """Construct and return the Token Tax Dashboard Gradio Blocks UI.

    Returns:
        gr.Blocks instance with text input, model selection,
        cost table, context summary, and recommendations.
    """
    model_names = available_models()

    with gr.Blocks(title="Token Tax Dashboard") as demo:
        gr.Markdown(
            "## Token Tax Dashboard\n"
            "Quantify how non-English text inflates token counts, costs, "
            "and context usage across models. "
            f"*(Pricing data last updated: {LAST_UPDATED})*"
        )

        with gr.Row():
            with gr.Column(scale=2):
                input_text = gr.Textbox(
                    label="Input Text",
                    placeholder="Paste text in any language...",
                    lines=4,
                )
            with gr.Column(scale=2):
                english_text = gr.Textbox(
                    label="English Equivalent (optional)",
                    placeholder="Paste English translation for RTC comparison, or leave empty...",
                    lines=4,
                )

        model_checkboxes = gr.CheckboxGroup(
            choices=model_names,
            value=model_names,
            label="Models to Compare",
        )

        with gr.Accordion("Traffic Projections", open=False):
            with gr.Row():
                monthly_req = gr.Slider(
                    minimum=0, maximum=1_000_000, value=10_000, step=1000,
                    label="Monthly Requests",
                )
                avg_chars = gr.Slider(
                    minimum=0, maximum=10_000, value=500, step=50,
                    label="Avg Tokens per Request",
                )

        analyze_btn = gr.Button("Analyze Token Tax", variant="primary")

        cost_table = gr.DataFrame(
            label="Cost Analysis",
            interactive=False,
        )
        context_md = gr.Markdown(label="Context Window Summary")
        recs_md = gr.Markdown(label="Recommendations")

        def _on_analyze(text, eng_text, models, requests, chars):
            table_data, ctx, recs = _handle_dashboard(
                text, eng_text, models, int(requests), int(chars),
            )
            return table_data, ctx, recs

        analyze_btn.click(
            fn=_on_analyze,
            inputs=[input_text, english_text, model_checkboxes, monthly_req, avg_chars],
            outputs=[cost_table, context_md, recs_md],
        )

    return demo
