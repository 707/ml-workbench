"""Token Tax Dashboard — Gradio UI.

Provides `build_token_tax_ui()` which returns a gr.Blocks composing
the Token Tax Dashboard tab with cost analysis, charts, and recommendations.
"""

import math

import gradio as gr

from pricing import available_models, LAST_UPDATED
from tokenizer import detect_language
from token_tax import (
    analyze_text_across_models,
    cost_projection,
    generate_recommendations,
    parse_traffic_csv,
    portfolio_analysis,
)


_RISK_COLORS = {
    "low": "#4CAF50",
    "moderate": "#FF9800",
    "high": "#F44336",
    "severe": "#9C27B0",
}


def build_bubble_chart(analysis_results: list[dict]):
    """Bubble chart: x=RTC, y=cost_per_million, size=token_count, color=risk_level.

    Args:
        analysis_results: List of dicts from analyze_text_across_models,
            each containing model, token_count, rtc, cost_per_million, risk_level.

    Returns:
        A Plotly Figure. Empty results yield an empty figure with annotation.
    """
    import plotly.graph_objects as go

    fig = go.Figure()

    if not analysis_results:
        fig.update_layout(
            annotations=[{
                "text": "No data — run an analysis first",
                "xref": "paper", "yref": "paper",
                "x": 0.5, "y": 0.5, "showarrow": False,
                "font": {"size": 16},
            }],
        )
        return fig

    for r in analysis_results:
        fig.add_trace(go.Scatter(
            x=[r["rtc"]],
            y=[r["cost_per_million"]],
            mode="markers",
            name=r["model"],
            marker={
                "size": max(math.sqrt(r["token_count"]) * 3, 10),
                "color": _RISK_COLORS.get(r["risk_level"], "#999999"),
                "opacity": 0.8,
                "line": {"width": 1, "color": "#333333"},
            },
            hovertemplate=(
                "<b>%{text}</b><br>"
                "RTC: %{x:.2f}x<br>"
                "Cost: $%{y:.4f}/1M tokens<br>"
                f"Tokens: {r['token_count']}<br>"
                f"Risk: {r['risk_level']}"
                "<extra></extra>"
            ),
            text=[r["model"]],
        ))

    fig.update_layout(
        xaxis_title="Relative Tokenization Cost (RTC)",
        yaxis_title="Cost per 1M Tokens ($)",
        showlegend=True,
        template="plotly_white",
    )

    return fig


def _handle_dashboard(
    text: str,
    english_text: str,
    selected_models: list[str],
    monthly_requests: int,
    avg_chars: int,
) -> tuple[dict, str, object, str]:
    """Handler logic for the Token Tax Dashboard — extracted for testability.

    Returns:
        (table_data, context_md, bubble_chart, recommendations_md)
        table_data is a dict with 'headers' and 'data' keys for gr.DataFrame.
        Return order matches Gradio output wiring.
    """
    headers = [
        "Model", "Tokens", "RTC", "Byte Premium",
        "Context %", "Risk", "$/1M Input", "Monthly Est.",
    ]
    empty_table = {"headers": headers, "data": []}
    empty_chart = build_bubble_chart([])

    if not selected_models:
        return empty_table, "", empty_chart, "No models selected."

    eng = english_text.strip() if english_text else None

    try:
        results = analyze_text_across_models(text, eng, selected_models)
    except Exception as exc:
        return empty_table, "", empty_chart, f"Error: {exc}"

    lang = detect_language(text) if text.strip() else "en"

    # Build table rows (compute cost projections inline, no mutation)
    rows = []
    for r in results:
        proj = cost_projection(
            r["token_count"],
            r["cost_per_million"],
            monthly_requests,
            avg_chars,
        )
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

    # Bubble chart
    chart = build_bubble_chart(results)

    return table_data, context_md, chart, recs_md


def _handle_traffic(csv_file, model_name: str) -> tuple[dict, str]:
    """Handler logic for the Traffic Analysis tab — extracted for testability.

    Returns:
        (table_data, summary_md)
    """
    headers = [
        "Language", "Traffic Share %", "Token Count",
        "RTC", "Cost Share %", "Tax Ratio",
    ]
    empty_table = {"headers": headers, "data": []}

    if csv_file is None:
        return empty_table, "Upload a CSV file to begin."

    file_path = csv_file if isinstance(csv_file, str) else csv_file.name

    try:
        traffic_data = parse_traffic_csv(file_path)
    except ValueError as exc:
        return empty_table, f"CSV error: {exc}"

    if not traffic_data:
        return empty_table, "CSV has no data rows."

    try:
        result = portfolio_analysis(traffic_data, model_name)
    except Exception as exc:
        return empty_table, f"Analysis error: {exc}"

    rows = []
    for entry in result["languages"]:
        rows.append([
            entry["language"],
            f"{entry['traffic_share'] * 100:.1f}%",
            entry["token_count"],
            f"{entry['rtc']:.2f}x",
            f"{entry['cost_share'] * 100:.1f}%",
            f"{entry['tax_ratio']:.2f}x",
        ])

    table_data = {"headers": headers, "data": rows}

    # Summary
    worst = max(result["languages"], key=lambda e: e["rtc"])
    summary_lines = [
        f"**Total monthly cost estimate:** ${result['total_monthly_cost']:.4f}",
        f"**Weighted token tax exposure:** {result['token_tax_exposure']:.2f}x vs English",
        f"**Worst-case language:** {worst['language']} ({worst['rtc']:.2f}x RTC)",
    ]
    if result["token_tax_exposure"] > 1.5:
        summary_lines.append(
            "\n*Your portfolio has significant token tax exposure. "
            "Consider model alternatives for high-RTC languages.*"
        )
    summary_lines.append(
        "\n*Estimates based on representative sample text per language. "
        "For exact analysis, use the Dashboard tab with your actual content.*"
    )

    return table_data, "\n\n".join(summary_lines)


def build_token_tax_ui() -> gr.Blocks:
    """Construct and return the Token Tax Dashboard Gradio Blocks UI.

    Returns:
        gr.Blocks instance with text input, model selection,
        cost table, context summary, and recommendations.
    """
    model_names = available_models()

    with gr.Blocks(title="Token Tax Dashboard") as demo:
        gr.Markdown(
            "## Token Tax Dashboard\n\n"
            "Non-English text often requires **2–10x more tokens** than English "
            "for the same content, inflating API costs and consuming context window "
            "capacity. This tool quantifies that hidden cost — the **token tax** — "
            "across models so you can make informed decisions.\n\n"
            f"*(Pricing data last updated: {LAST_UPDATED})*"
        )

        with gr.Tabs():
            # --- Single Text Analysis ---
            with gr.TabItem("Analyze Text"):
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
                            info="Provide an English translation to compute Relative Tokenization Cost (RTC).",
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
                bubble_plot = gr.Plot(label="Cost vs Quality Risk")
                recs_md = gr.Markdown(label="Recommendations")

                def _on_analyze(text, eng_text, models, requests, chars):
                    return _handle_dashboard(
                        text, eng_text, models, int(requests), int(chars),
                    )

                analyze_btn.click(
                    fn=_on_analyze,
                    inputs=[input_text, english_text, model_checkboxes, monthly_req, avg_chars],
                    outputs=[cost_table, context_md, bubble_plot, recs_md],
                )

            # --- Traffic Analysis (CSV upload) ---
            with gr.TabItem("Traffic Analysis"):
                gr.Markdown(
                    "### Portfolio Token Tax Analysis\n\n"
                    "Upload a CSV with your traffic data to see portfolio-level "
                    "token tax exposure. The **Tax Ratio** shows how much more each "
                    "language costs relative to its traffic share.\n\n"
                    "**Required columns:** `language`, `request_count`, `avg_chars`\n\n"
                    "```\nlanguage,request_count,avg_chars\n"
                    "en,50000,500\nar,20000,300\nhi,10000,400\n```"
                )
                traffic_csv = gr.File(
                    label="Upload Traffic CSV",
                    file_types=[".csv"],
                )
                traffic_model = gr.Dropdown(
                    choices=model_names,
                    value=model_names[0],
                    label="Model",
                )
                traffic_btn = gr.Button("Analyze Portfolio", variant="primary")
                traffic_table = gr.DataFrame(
                    label="Portfolio Analysis",
                    interactive=False,
                )
                traffic_summary = gr.Markdown(label="Summary")

                traffic_btn.click(
                    fn=_handle_traffic,
                    inputs=[traffic_csv, traffic_model],
                    outputs=[traffic_table, traffic_summary],
                )

    return demo
