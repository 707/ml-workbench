"""Token Tax Workbench — Gradio UI."""

from __future__ import annotations

import gradio as gr

from charts import (
    build_bubble_chart,
    build_context_chart,
    build_cost_waterfall,
    build_distribution_chart,
    build_heatmap,
    build_metric_scatter,
)
from corpora import DEFAULT_BENCHMARK_LANGUAGES, list_corpora
from diagnostics import clear_events, render_markdown
from model_registry import build_catalog_entries, list_tokenizer_families
from token_tax import (
    analyze_text_across_models,
    audit_markdown,
    benchmark_appendix,
    benchmark_corpus,
    benchmark_all,
    catalog_appendix,
    cost_projection,
    export_csv,
    export_json,
    generate_recommendations,
    parse_traffic_csv,
    portfolio_analysis,
    refresh_catalog,
    run_benchmark,
    scenario_analysis,
    scenario_appendix,
    serialize_table,
)


BENCHMARK_COLUMNS = [
    "language",
    "tokenizer_key",
    "rtc",
    "token_count",
    "bytes_per_token",
    "token_fertility",
    "sample_count",
    "provenance",
]

CATALOG_COLUMNS = [
    "label",
    "model_id",
    "tokenizer_key",
    "mapping_quality",
    "input_per_million",
    "output_per_million",
    "context_window",
    "provenance",
]

SCENARIO_COLUMNS = [
    "label",
    "language",
    "tokenizer_key",
    "rtc",
    "context_loss_pct",
    "monthly_input_tokens",
    "monthly_output_tokens",
    "monthly_cost",
    "provenance",
]


# ---------------------------------------------------------------------------
# Legacy handlers retained for compatibility and tests
# ---------------------------------------------------------------------------


def _handle_dashboard(
    text: str,
    english_text: str,
    selected_models: list[str],
    monthly_requests: int,
    avg_chars: int,
) -> tuple[dict, str, object, object, str]:
    headers = [
        "Model",
        "Tokens",
        "Fertility",
        "RTC",
        "Byte Premium",
        "Context %",
        "Risk",
        "$/1M Input",
        "Monthly Est.",
    ]
    empty_table = {"headers": headers, "data": []}
    if not selected_models:
        return empty_table, "", build_bubble_chart([]), build_context_chart([]), "No models selected."

    english = english_text.strip() if english_text else None
    try:
        results = analyze_text_across_models(text, english, selected_models)
    except Exception as exc:
        return empty_table, "", build_bubble_chart([]), build_context_chart([]), f"Error: {exc}"
    rows = []
    for result in results:
        projection = cost_projection(
            result["token_count"],
            result["cost_per_million"],
            monthly_requests,
            avg_chars,
        )
        rows.append([
            result["model"],
            result["token_count"],
            f"{result['token_fertility']:.2f}",
            f"{result['rtc']:.2f}x",
            f"{result['byte_premium']:.2f}x",
            f"{result['context_usage']:.4%}",
            result["risk_level"],
            f"${result['cost_per_million']:.4f}",
            f"${projection['monthly_cost']:.4f}",
        ])

    recs = generate_recommendations(results, "en" if not english else "x")
    recs_md = recs["executive_summary"]
    context_md = "\n".join(
        f"- {row['model']}: {row['token_count']} tokens" for row in results
    )
    return (
        {"headers": headers, "data": rows},
        context_md,
        build_bubble_chart(results),
        build_context_chart(results),
        recs_md,
    )


def _handle_traffic(csv_file, model_name: str) -> tuple[dict, object, str]:
    headers = [
        "Language",
        "Traffic Share %",
        "Token Count",
        "RTC",
        "Cost Share %",
        "Tax Ratio",
    ]
    empty_table = {"headers": headers, "data": []}
    if csv_file is None:
        return empty_table, build_cost_waterfall({"languages": []}), "Upload a CSV file to begin."

    file_path = csv_file if isinstance(csv_file, str) else csv_file.name
    try:
        traffic_data = parse_traffic_csv(file_path)
        if not traffic_data:
            return empty_table, build_cost_waterfall({"languages": []}), "CSV has no data rows."
        result = portfolio_analysis(traffic_data, model_name)
    except Exception as exc:
        message = f"{exc}"
        if message.startswith("CSV missing") or message.startswith("Row "):
            message = f"CSV error: {message}"
        else:
            message = f"Error: {message}"
        return empty_table, build_cost_waterfall({"languages": []}), message

    rows = [
        [
            entry["language"],
            f"{entry['traffic_share'] * 100:.1f}%",
            entry["token_count"],
            f"{entry['rtc']:.2f}x",
            f"{entry['cost_share'] * 100:.1f}%",
            f"{entry['tax_ratio']:.2f}x",
        ]
        for entry in result["languages"]
    ]
    summary_lines = [
        f"Total monthly cost: ${result['total_monthly_cost']:.4f}",
        f"Weighted token tax exposure: {result['token_tax_exposure']:.2f}x",
    ]
    if result["token_tax_exposure"] > 1.5:
        summary_lines.append("Your portfolio has significant token tax exposure.")
    summary = "\n\n".join(summary_lines)
    return {"headers": headers, "data": rows}, build_cost_waterfall(result), summary


def _handle_benchmark(selected_models: list[str]) -> tuple[dict, object, str]:
    if not selected_models:
        return {"headers": [], "data": []}, build_heatmap({}, [], []), "No models selected."
    languages = list(DEFAULT_BENCHMARK_LANGUAGES)
    benchmark_data = benchmark_all(languages, selected_models)
    benchmark_results = run_benchmark(languages, selected_models)
    headers = ["Language"] + selected_models
    rows = []
    for entry in benchmark_results:
        row = [entry["language"]]
        for model in entry["models"]:
            row.append(f"{model['rtc']:.2f}x")
        rows.append(row)
    summary = "**Demo benchmark uses bundled example phrases, not the strict corpus view.**"
    return {"headers": headers, "data": rows}, build_heatmap(benchmark_data, languages, selected_models), summary


def _handle_export_csv(text: str, english_text: str, selected_models: list[str]) -> str | None:
    if not selected_models or not text.strip():
        return None
    english = english_text.strip() if english_text else None
    results = analyze_text_across_models(text, english, selected_models)
    return export_csv(results)


def _handle_export_json(text: str, english_text: str, selected_models: list[str]) -> str | None:
    if not selected_models or not text.strip():
        return None
    english = english_text.strip() if english_text else None
    results = analyze_text_across_models(text, english, selected_models)
    return export_json(results)


# ---------------------------------------------------------------------------
# Workbench handlers
# ---------------------------------------------------------------------------


def _handle_benchmark_tab(
    corpus_key: str,
    languages: list[str],
    tokenizer_keys: list[str],
    metric_key: str,
    row_limit: int,
    include_estimates: bool,
    include_proxy: bool,
) -> tuple[dict, object, object, str, str]:
    if not tokenizer_keys:
        return (
            {"headers": BENCHMARK_COLUMNS, "data": []},
            build_heatmap({}, [], []),
            build_distribution_chart([], metric_key),
            "Select at least one tokenizer family.",
            render_markdown(),
        )

    try:
        clear_events()
        result = benchmark_corpus(
            corpus_key,
            languages,
            tokenizer_keys,
            row_limit=int(row_limit),
            include_estimates=include_estimates,
            include_proxy=include_proxy,
        )
    except Exception as exc:
        return (
            {"headers": BENCHMARK_COLUMNS, "data": []},
            build_heatmap({}, [], [], metric_key=metric_key),
            build_distribution_chart([], metric_key),
            f"{benchmark_appendix(corpus_key)}\n\n**Runtime error:** {exc}",
            render_markdown(),
        )

    table = serialize_table(result["rows"], BENCHMARK_COLUMNS)
    heatmap = build_heatmap(result["matrix"], result["languages"], result["tokenizers"], metric_key=metric_key)
    distribution = build_distribution_chart(result["rows"], metric_key)
    appendix = benchmark_appendix(corpus_key)
    return table, heatmap, distribution, appendix, render_markdown()


def _handle_catalog_tab(include_proxy: bool, refresh_live: bool) -> tuple[dict, str, str]:
    clear_events()
    if refresh_live:
        rows, _ = refresh_catalog()
    else:
        rows = build_catalog_entries(include_proxy=include_proxy, refresh_live=False)
    visible_rows = rows if include_proxy else [row for row in rows if row["mapping_quality"] != "proxy"]
    return serialize_table(visible_rows, CATALOG_COLUMNS), catalog_appendix(include_proxy), render_markdown()


def _handle_scenario_tab(
    corpus_key: str,
    languages: list[str],
    tokenizer_keys: list[str],
    model_ids: list[str],
    monthly_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    reasoning_share: float,
    x_key: str,
    y_key: str,
    size_key: str,
    include_estimates: bool,
    include_proxy: bool,
) -> tuple[dict, object, object, object, object, object, str, str]:
    if not model_ids:
        empty = serialize_table([], SCENARIO_COLUMNS)
        return (
            empty,
            build_metric_scatter([], x_key="rtc", y_key="monthly_cost"),
            build_metric_scatter([], x_key="latency_ms", y_key="monthly_cost"),
            build_metric_scatter([], x_key="throughput_tps", y_key="monthly_cost"),
            build_metric_scatter([], x_key="monthly_input_tokens", y_key="monthly_cost"),
            build_metric_scatter([], x_key=x_key, y_key=y_key),
            "Select at least one model.",
            render_markdown(),
        )

    try:
        clear_events()
        rows = scenario_analysis(
            corpus_key=corpus_key,
            languages=languages,
            tokenizer_keys=tokenizer_keys,
            model_ids=model_ids,
            row_limit=25,
            monthly_requests=int(monthly_requests),
            avg_input_tokens=int(avg_input_tokens),
            avg_output_tokens=int(avg_output_tokens),
            reasoning_share=float(reasoning_share),
            include_estimates=include_estimates,
            include_proxy=include_proxy,
        )
    except Exception as exc:
        empty = serialize_table([], SCENARIO_COLUMNS)
        return (
            empty,
            build_metric_scatter([], x_key="rtc", y_key="monthly_cost"),
            build_metric_scatter([], x_key="latency_ms", y_key="monthly_cost"),
            build_metric_scatter([], x_key="throughput_tps", y_key="monthly_cost"),
            build_metric_scatter([], x_key="monthly_input_tokens", y_key="monthly_cost"),
            build_metric_scatter([], x_key=x_key, y_key=y_key),
            f"{scenario_appendix()}\n\n**Runtime error:** {exc}",
            render_markdown(),
        )

    table = serialize_table(rows, SCENARIO_COLUMNS)
    cost_plot = build_metric_scatter(
        rows,
        x_key="rtc",
        y_key="monthly_cost",
        size_key="monthly_input_tokens",
        title="Cost",
        x_title="RTC",
        y_title="Monthly cost ($)",
    )
    latency_plot = build_metric_scatter(
        rows,
        x_key="latency_ms",
        y_key="monthly_cost",
        size_key="monthly_input_tokens",
        title="Latency",
        x_title="Latency (ms)",
        y_title="Monthly cost ($)",
    )
    throughput_plot = build_metric_scatter(
        rows,
        x_key="throughput_tps",
        y_key="monthly_cost",
        size_key="monthly_input_tokens",
        title="Throughput",
        x_title="Throughput (tokens/sec)",
        y_title="Monthly cost ($)",
    )
    scale_plot = build_metric_scatter(
        rows,
        x_key="monthly_input_tokens",
        y_key="monthly_cost",
        size_key="monthly_cost",
        title="Scale",
        x_title="Monthly input tokens",
        y_title="Monthly cost ($)",
    )
    custom_plot = build_metric_scatter(
        rows,
        x_key=x_key,
        y_key=y_key,
        size_key=size_key if size_key != "none" else None,
        title="Custom Slice",
        x_title=x_key,
        y_title=y_key,
    )
    return table, cost_plot, latency_plot, throughput_plot, scale_plot, custom_plot, scenario_appendix(), render_markdown()


def build_token_tax_ui() -> gr.Blocks:
    """Construct the Token Tax Workbench."""
    corpora = list_corpora()
    tokenizer_families = list_tokenizer_families(include_proxy=True)
    exact_tokenizers = [family["key"] for family in tokenizer_families if family["mapping_quality"] != "proxy"]
    proxy_tokenizers = [family["key"] for family in tokenizer_families if family["mapping_quality"] == "proxy"]
    catalog_rows = build_catalog_entries(include_proxy=False, refresh_live=False)
    model_choices = [(f"{row['label']} ({row['tokenizer_key']})", row["model_id"]) for row in catalog_rows]

    with gr.Blocks(title="Token Tax Workbench") as demo:
        gr.Markdown(
            "## Token Tax Workbench\n\n"
            "Strict verified corpus evidence is shown by default. "
            "Proxy mappings and estimated values stay hidden until you enable them."
        )

        with gr.Tabs():
            with gr.TabItem("Benchmark"):
                with gr.Row():
                    benchmark_corpus_drop = gr.Dropdown(
                        choices=[(corpus["label"], corpus["key"]) for corpus in corpora],
                        value="strict_parallel",
                        label="Corpus",
                    )
                    benchmark_metric = gr.Dropdown(
                        choices=["rtc", "token_count", "bytes_per_token", "token_fertility", "byte_premium"],
                        value="rtc",
                        label="Metric",
                    )
                    benchmark_limit = gr.Slider(5, 50, value=12, step=1, label="Rows per language")
                with gr.Row():
                    benchmark_languages = gr.Dropdown(
                        choices=DEFAULT_BENCHMARK_LANGUAGES,
                        value=DEFAULT_BENCHMARK_LANGUAGES,
                        multiselect=True,
                        label="Languages",
                    )
                    benchmark_tokenizers = gr.Dropdown(
                        choices=[(family["label"], family["key"]) for family in tokenizer_families],
                        value=exact_tokenizers,
                        multiselect=True,
                        label="Tokenizer Families",
                    )
                with gr.Row():
                    benchmark_include_estimates = gr.Checkbox(label="Include estimated values", value=False)
                    benchmark_include_proxy = gr.Checkbox(label="Include proxy mappings", value=False)
                    benchmark_run = gr.Button("Run Benchmark", variant="primary")

                with gr.Tabs():
                    with gr.TabItem("Heatmap"):
                        benchmark_heatmap = gr.Plot(label="Benchmark Heatmap")
                    with gr.TabItem("Distributions"):
                        benchmark_distribution = gr.Plot(label="Metric Distribution")
                    with gr.TabItem("Table"):
                        benchmark_table = gr.DataFrame(label="Benchmark Table", interactive=False)
                benchmark_appendix_md = gr.Markdown(label="Benchmark Appendix")
                with gr.Accordion("Diagnostics", open=False):
                    benchmark_diagnostics_md = gr.Markdown()

                benchmark_run.click(
                    fn=_handle_benchmark_tab,
                    inputs=[
                        benchmark_corpus_drop,
                        benchmark_languages,
                        benchmark_tokenizers,
                        benchmark_metric,
                        benchmark_limit,
                        benchmark_include_estimates,
                        benchmark_include_proxy,
                    ],
                    outputs=[
                        benchmark_table,
                        benchmark_heatmap,
                        benchmark_distribution,
                        benchmark_appendix_md,
                        benchmark_diagnostics_md,
                    ],
                )

            with gr.TabItem("Catalog"):
                with gr.Row():
                    catalog_include_proxy = gr.Checkbox(label="Include proxy mappings", value=False)
                    catalog_refresh_live = gr.Checkbox(label="Refresh live pricing cache", value=False)
                    catalog_run = gr.Button("Load Catalog", variant="primary")
                catalog_table = gr.DataFrame(label="Catalog", interactive=False)
                catalog_appendix_md = gr.Markdown(label="Catalog Appendix")
                with gr.Accordion("Diagnostics", open=False):
                    catalog_diagnostics_md = gr.Markdown()
                catalog_run.click(
                    fn=_handle_catalog_tab,
                    inputs=[catalog_include_proxy, catalog_refresh_live],
                    outputs=[catalog_table, catalog_appendix_md, catalog_diagnostics_md],
                )

            with gr.TabItem("Scenario Lab"):
                with gr.Row():
                    scenario_corpus = gr.Dropdown(
                        choices=[(corpus["label"], corpus["key"]) for corpus in corpora],
                        value="strict_parallel",
                        label="Benchmark Corpus",
                    )
                    scenario_languages = gr.Dropdown(
                        choices=DEFAULT_BENCHMARK_LANGUAGES,
                        value=["en", "ar", "hi", "ja"],
                        multiselect=True,
                        label="Languages",
                    )
                with gr.Row():
                    scenario_tokenizers = gr.Dropdown(
                        choices=[(family["label"], family["key"]) for family in tokenizer_families],
                        value=exact_tokenizers,
                        multiselect=True,
                        label="Benchmark Tokenizers",
                    )
                    scenario_models = gr.Dropdown(
                        choices=model_choices,
                        value=[row["model_id"] for row in catalog_rows[:4]],
                        multiselect=True,
                        label="Deployable Models",
                    )
                with gr.Row():
                    monthly_requests = gr.Slider(1_000, 1_000_000, value=100_000, step=1_000, label="Monthly Requests")
                    avg_input_tokens = gr.Slider(10, 10_000, value=600, step=10, label="Avg Input Tokens")
                    avg_output_tokens = gr.Slider(10, 10_000, value=250, step=10, label="Avg Output Tokens")
                    reasoning_share = gr.Slider(0.0, 2.0, value=0.1, step=0.05, label="Reasoning Share")
                with gr.Row():
                    slice_x = gr.Dropdown(
                        choices=["rtc", "monthly_cost", "monthly_input_tokens", "context_loss_pct", "latency_ms", "throughput_tps"],
                        value="rtc",
                        label="Custom X",
                    )
                    slice_y = gr.Dropdown(
                        choices=["monthly_cost", "rtc", "monthly_input_tokens", "context_loss_pct", "latency_ms", "throughput_tps"],
                        value="monthly_cost",
                        label="Custom Y",
                    )
                    slice_size = gr.Dropdown(
                        choices=["none", "monthly_cost", "monthly_input_tokens", "rtc"],
                        value="monthly_input_tokens",
                        label="Bubble Size",
                    )
                with gr.Row():
                    scenario_include_estimates = gr.Checkbox(label="Include estimated values", value=False)
                    scenario_include_proxy = gr.Checkbox(label="Include proxy mappings", value=False)
                    scenario_run = gr.Button("Run Scenario Lab", variant="primary")

                with gr.Tabs():
                    with gr.TabItem("Cost"):
                        scenario_cost_plot = gr.Plot(label="Cost")
                    with gr.TabItem("Latency"):
                        scenario_latency_plot = gr.Plot(label="Latency")
                    with gr.TabItem("Throughput"):
                        scenario_throughput_plot = gr.Plot(label="Throughput")
                    with gr.TabItem("Scale"):
                        scenario_scale_plot = gr.Plot(label="Scale")
                    with gr.TabItem("Custom Slice"):
                        scenario_custom_plot = gr.Plot(label="Custom Slice")
                scenario_table = gr.DataFrame(label="Scenario Rows", interactive=False)
                scenario_appendix_md = gr.Markdown(label="Scenario Appendix")
                with gr.Accordion("Diagnostics", open=False):
                    scenario_diagnostics_md = gr.Markdown()

                scenario_run.click(
                    fn=_handle_scenario_tab,
                    inputs=[
                        scenario_corpus,
                        scenario_languages,
                        scenario_tokenizers,
                        scenario_models,
                        monthly_requests,
                        avg_input_tokens,
                        avg_output_tokens,
                        reasoning_share,
                        slice_x,
                        slice_y,
                        slice_size,
                        scenario_include_estimates,
                        scenario_include_proxy,
                    ],
                    outputs=[
                        scenario_table,
                        scenario_cost_plot,
                        scenario_latency_plot,
                        scenario_throughput_plot,
                        scenario_scale_plot,
                        scenario_custom_plot,
                        scenario_appendix_md,
                        scenario_diagnostics_md,
                    ],
                )

            with gr.TabItem("Audit"):
                gr.Markdown(audit_markdown())

    return demo
